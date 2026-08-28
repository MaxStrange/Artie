"""
A single Artie CAN node, driven through the Python bindings, in its own process.

The Python unit tests in ``tests/python`` put every node in one process, so frames never leave it
and what they really cover is the bindings on top of the protocol state machines. This script
exists to put each node in its own container instead, so that the UDP multicast backend, the wire
format and the receive path all get exercised across a real network boundary - the same job
``itest_node.c`` does for the C API.

Two roles, matching the C node's:

* ``peer``   Long-lived. Enables all four protocols, then answers whatever it is sent: it echoes
             RTACP payloads back to their sender, acknowledges PSACP publishes and completed BWACP
             block writes with an RTACP marker, and services the ECHO RPC. Logs one line per event,
             which is what the artie-tool task greps for.
* ``driver`` One-shot. Runs a single scenario against the peers, decides pass/fail itself, prints
             ``PYITEST <scenario>:PASS`` (or ``:FAIL <reason>``), and exits.

Every node on the bus needs a unique address: the UDP multicast backend filters out its own traffic
by comparing each frame's source address against its own, so two nodes sharing an address silently
discard each other's frames.
"""
import argparse
import signal
import sys
import time

from artie_can import backends, enums, errors, node, rpc

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: Multicast group this bus lives on. Deliberately different from the C integration node's group
#: (239.0.0.10) and from the Python unit tests' (239.0.0.21), so no run can be mistaken for another.
DEFAULT_GROUP = "239.0.0.11"

#: Multicast port for this bus.
DEFAULT_PORT = 7101

#: PSACP topic the peers subscribe to. Must be within the protocol's valid 0x0B-0xF4 range.
TOPIC = 0x10

#: Device-specific RPC procedure ID the peers register. 0x00-0x0F are reserved by the library.
ECHO_PROCEDURE_ID = 0x10

#: Argument the driver passes to ECHO; the peer returns this + 1.
ECHO_ARG = 0x41

#: Size of each peer's BWACP receive buffer.
BLOCK_BUFFER_SIZE = 4096

#: Size of the block the BWACP scenario transfers. Small enough to keep the suite quick.
BLOCK_PAYLOAD_SIZE = 1024

#: How long the driver keeps retrying a scenario before giving up.
DEFAULT_DRIVER_TIMEOUT_S = 20.0

#: How long the driver waits for peer responses within a single attempt.
ATTEMPT_WAIT_S = 2.0

#: How long the driver listens, after a unicast has been answered, to prove nobody else answered.
NEGATIVE_CHECK_S = 0.5

#: How long a freshly opened node is left alone before it is used, so the multicast join settles.
SETTLE_S = 0.5

#: Addresses of the long-lived peers that docker compose hosts.
PEERS = (0x02, 0x03)

# Markers exchanged on the wire. RTACP and PSACP carry at most 8 data bytes, so these stay short.
# Each scenario uses its own, because the peers outlive every individual test while the task
# streams their logs from container start - a marker reused across scenarios could match the wrong
# test's line.
MARKER_PING = b"PYPING01"
MARKER_RTACP_UNICAST = b"PYRTU01"
MARKER_RTACP_BROADCAST = b"PYRTB01"
MARKER_PSACP = b"PYPS01"
MARKER_PSACP_ACK = b"PYPSOK1"
MARKER_PSACP_LARGE_ACK = b"PYPSL01"
MARKER_BWACP_ACK = b"PYBW01"

#: Size of the multi-frame PSACP message the large-message scenario publishes. Big enough to need
#: a long run of PUB_MORE frames (300 bytes is 38 frames) while keeping the suite quick.
PSACP_LARGE_PAYLOAD_SIZE = 300

ALL_PROTOCOLS = (
    enums.Protocol.RTACP | enums.Protocol.PSACP | enums.Protocol.BWACP | enums.Protocol.RPCACP
)

_should_stop = False


def log(message: str) -> None:
    """Print a line the test task can grep for. Flushed, because the task reads container logs."""
    print(message, flush=True)


def readable(payload: bytes) -> str:
    """Render a payload the way the C node's log lines do, so both suites read the same."""
    return "".join(chr(byte) if 0x20 <= byte < 0x7F else "." for byte in payload)


def large_psacp_payload() -> bytes:
    """The payload the large-message scenario publishes, built the same way on both sides.

    Varied rather than a repeated byte, so a fragment that arrives at the wrong offset or gets
    duplicated shows up as a mismatch instead of passing by luck. The C node builds the identical
    pattern, so either language's driver can be checked against either language's peer.
    """
    return bytes(((index * 7) + 3) % 256 for index in range(PSACP_LARGE_PAYLOAD_SIZE))


def open_node(address: int, group: str, port: int) -> node.Node:
    """Bring up a node on the integration-test bus and give its multicast join time to settle."""
    opened = node.Node(
        backends.UdpMulticastBackend(group=group, port=port),
        address=address,
        protocols=ALL_PROTOCOLS,
        node_class=enums.NodeClass.SBC,
        name=f"pyitest-node-{address:#04x}",
        firmware_version="1.0.0",
        block_buffer_size=BLOCK_BUFFER_SIZE,
    )
    time.sleep(SETTLE_S)
    return opened


# ---------------------------------------------------------------------------
# Peer role
# ---------------------------------------------------------------------------

def _echo_signature(address: int) -> rpc.RpcSignature:
    """The one device-specific procedure a peer exposes: returns its argument plus one."""
    def echo(value: int) -> int:
        result = (value + 1) & 0xFF
        log(f"NODE {address:#04x} RPC ECHO({value:#04x}) -> {result:#04x}")
        return result

    return rpc.RpcSignature(
        procedure_id=ECHO_PROCEDURE_ID,
        name="ECHO",
        params=(rpc.RpcParam("uint8_t"),),
        returns=rpc.RpcParam("uint8_t"),
        function=echo,
    )


def _reply(peer: node.Node, address: int, target: int, marker: bytes) -> None:
    """Answer a peer's sender over RTACP.

    A Timeout here means the driver's ACK missed RTACP's 10 ms budget, not that the reply was
    lost - it usually arrives - so it is swallowed rather than logged. Whether the driver really
    got it is the scenario's verdict to reach, not this node's.
    """
    try:
        peer.rtacp_send(target, marker)
    except errors.Timeout:
        pass
    except errors.ArtieCanError as exc:
        log(f"NODE {address:#04x} failed to reply to {target:#04x}: {exc}")


def run_peer(address: int, group: str, port: int) -> int:
    """Answer whatever arrives, for as long as the container lives."""
    peer = open_node(address, group, port)
    try:
        peer.register_procedure(_echo_signature(address))
        peer.subscribe(TOPIC)
        log(f"NODE {address:#04x} ready")

        # Everything is read off the node's queues on this thread rather than through the on_*
        # callbacks, because a callback runs on the node's dispatcher thread and must not call back
        # into the same node - and calling back into it is the whole job here.
        while not _should_stop:
            try:
                message = peer.receive_rtacp(timeout=0.05)
            except errors.Timeout:
                pass
            else:
                log(f"NODE {address:#04x} RTACP RX from {message.source_address:#04x}: "
                    f"{readable(message.data)}")
                _reply(peer, address, message.source_address, message.data)

            try:
                message = peer.receive_psacp(timeout=0.01)
            except errors.Timeout:
                pass
            else:
                if len(message.data) > enums.MAX_FRAME_DATA_LENGTH:
                    # A multi-frame message. Checking the content matters as much as the length:
                    # the length alone would pass even if fragments landed at the wrong offsets.
                    intact = message.data == large_psacp_payload()
                    log(f"NODE {address:#04x} PSACP RX topic {message.topic:#04x} from "
                        f"{message.source_address:#04x}: {len(message.data)} bytes, "
                        f"{'intact' if intact else 'CORRUPT'}")
                    if intact:
                        _reply(peer, address, message.source_address, MARKER_PSACP_LARGE_ACK)
                else:
                    log(f"NODE {address:#04x} PSACP RX topic {message.topic:#04x} from "
                        f"{message.source_address:#04x}: {readable(message.data)}")
                    _reply(peer, address, message.source_address, MARKER_PSACP_ACK)

            try:
                block = peer.receive_block(timeout=0.01)
            except errors.Timeout:
                pass
            else:
                log(f"NODE {address:#04x} BWACP RX {len(block)} bytes from "
                    f"{block.source_address:#04x} at offset {block.offset}")
                _reply(peer, address, block.source_address, MARKER_BWACP_ACK)
    finally:
        log(f"NODE {address:#04x} shutting down")
        peer.close()
    return 0


# ---------------------------------------------------------------------------
# Driver role
# ---------------------------------------------------------------------------

def _collect_replies(driver: node.Node, marker: bytes, expect, wait_s: float = ATTEMPT_WAIT_S) -> set:
    """Gather the addresses that answered with ``marker``, returning early once all of ``expect`` have.

    The driver hears everything addressed to it, including a previous attempt's leftovers, so
    replies are matched on their marker rather than on being the next thing to arrive.
    """
    seen = set()
    deadline = time.monotonic() + wait_s
    while not set(expect) <= seen:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            message = driver.receive_rtacp(timeout=remaining)
        except errors.Timeout:
            break
        if message.data == marker:
            seen.add(message.source_address)
    return seen


def _missing(seen, expect) -> str | None:
    absent = [f"{address:#04x}" for address in expect if address not in seen]
    return ", ".join(absent) if absent else None


def _send_rtacp(driver: node.Node, target: int, marker: bytes) -> None:
    """Send an RTACP message, treating a late ACK as delivered.

    A unicast is acknowledged inside RTACP's 10 ms budget or not at all, and missing that budget
    raises Timeout even though the frame itself went out. Whether it really arrived is what the
    peer's reply tells us, so that is what each scenario waits on.
    """
    try:
        driver.rtacp_send(target, marker)
    except errors.Timeout:
        pass


def _scenario_ping(driver: node.Node) -> str | None:
    """Prove both peers are on the bus. Retried by the caller, so it absorbs a slow multicast join."""
    _send_rtacp(driver, enums.BROADCAST_ADDRESS, MARKER_PING)
    absent = _missing(_collect_replies(driver, MARKER_PING, PEERS), PEERS)
    return f"no echo from {absent}" if absent else None


def _scenario_rtacp_broadcast(driver: node.Node) -> str | None:
    _send_rtacp(driver, enums.BROADCAST_ADDRESS, MARKER_RTACP_BROADCAST)
    absent = _missing(_collect_replies(driver, MARKER_RTACP_BROADCAST, PEERS), PEERS)
    return f"no echo from {absent}" if absent else None


def _scenario_rtacp_unicast(driver: node.Node) -> str | None:
    """A unicast must reach its target and nobody else.

    The negative half is checked here rather than in the task, because artie-tool has no way to
    assert that a string is *absent* from one particular container's logs.
    """
    _send_rtacp(driver, 0x02, MARKER_RTACP_UNICAST)
    if 0x02 not in _collect_replies(driver, MARKER_RTACP_UNICAST, (0x02,)):
        return "no echo from 0x02"

    strays = _collect_replies(driver, MARKER_RTACP_UNICAST, (0x03,), wait_s=NEGATIVE_CHECK_S)
    if 0x03 in strays:
        return "0x03 answered a message addressed to 0x02"
    return None


def _scenario_psacp(driver: node.Node) -> str | None:
    driver.publish(TOPIC, MARKER_PSACP)
    absent = _missing(_collect_replies(driver, MARKER_PSACP_ACK, PEERS), PEERS)
    return f"no ack from {absent}" if absent else None


def _scenario_psacp_large(driver: node.Node) -> str | None:
    """A message far larger than one CAN frame, fragmented out and reassembled by each peer.

    The peers only answer once they have checked the payload byte for byte, so a reply here means
    the whole message survived the trip across the container boundary intact - not merely that
    something of the right length arrived.
    """
    driver.publish(TOPIC, large_psacp_payload())
    absent = _missing(_collect_replies(driver, MARKER_PSACP_LARGE_ACK, PEERS), PEERS)
    return f"no intact-message ack from {absent}" if absent else None


def _scenario_bwacp(driver: node.Node) -> str | None:
    """A 1 KB block spans many frames, so this covers READY/DATA/COMPLETE and the CRC over the wire."""
    payload = bytes(index & 0xFF for index in range(BLOCK_PAYLOAD_SIZE))
    try:
        driver.block_write(payload, offset=0, target_address=0x02)
    except errors.ArtieCanError as exc:
        return f"block write failed: {exc}"

    if 0x02 not in _collect_replies(driver, MARKER_BWACP_ACK, (0x02,)):
        return "no ack from 0x02"
    return None


def _scenario_rpcacp(driver: node.Node) -> str | None:
    """The peer's ECHO returns its argument plus one, so this covers the whole request/return trip."""
    signature = rpc.RpcSignature(
        procedure_id=ECHO_PROCEDURE_ID,
        name="ECHO",
        params=(rpc.RpcParam("uint8_t"),),
        returns=rpc.RpcParam("uint8_t"),
    )
    try:
        result = driver.call(0x02, signature, ECHO_ARG, timeout=ATTEMPT_WAIT_S * 2)
    except errors.ArtieCanError as exc:
        return f"call failed: {exc}"

    expected = (ECHO_ARG + 1) & 0xFF
    return None if result == expected else f"expected {expected:#04x}, got {result:#04x}"


def _scenario_whoami(driver: node.Node) -> str | None:
    """The standard procedures are answered inside the library, so this proves it across the wire."""
    try:
        identity = driver.whoami(0x02, timeout=ATTEMPT_WAIT_S * 2)
    except errors.ArtieCanError as exc:
        return f"whoami failed: {exc}"

    if identity.node_address != 0x02:
        return f"expected address 0x02, got {identity.node_address:#04x}"
    if identity.node_name != "pyitest-node-0x02":
        return f"unexpected node name {identity.node_name!r}"
    return None


SCENARIOS = {
    "ping": _scenario_ping,
    "rtacp-unicast": _scenario_rtacp_unicast,
    "rtacp-broadcast": _scenario_rtacp_broadcast,
    "bwacp-block-transfer": _scenario_bwacp,
    "psacp-publish-subscribe": _scenario_psacp,
    "psacp-large-message": _scenario_psacp_large,
    "rpcacp-call": _scenario_rpcacp,
    "rpcacp-whoami": _scenario_whoami,
}


def run_driver(address: int, group: str, port: int, scenario_name: str, timeout_s: float) -> int:
    """Run one scenario until it passes or the deadline runs out, then report its verdict."""
    scenario = SCENARIOS[scenario_name]
    driver = open_node(address, group, port)
    try:
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                reason = scenario(driver)
            except errors.ArtieCanError as exc:
                reason = str(exc)
            if reason is None:
                log(f"PYITEST {scenario_name}:PASS")
                return 0
            if time.monotonic() >= deadline:
                log(f"PYITEST {scenario_name}:FAIL {reason}")
                return 1
    finally:
        driver.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _stop(_signum, _frame) -> None:
    global _should_stop
    _should_stop = True


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="One Artie CAN node, for the integration tests.")
    parser.add_argument("--role", choices=("peer", "driver"), required=True)
    parser.add_argument("--address", required=True, type=lambda value: int(value, 0),
                        help="This node's address on the bus, e.g. 0x02. Must be unique.")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), help="Driver role only.")
    parser.add_argument("--group", default=DEFAULT_GROUP)
    parser.add_argument("--port", default=DEFAULT_PORT, type=int)
    parser.add_argument("--timeout-s", default=DEFAULT_DRIVER_TIMEOUT_S, type=float,
                        help="How long the driver retries its scenario before failing.")
    args = parser.parse_args(argv)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    if args.role == "peer":
        return run_peer(args.address, args.group, args.port)

    if args.scenario is None:
        parser.error("--scenario is required for the driver role")
    return run_driver(args.address, args.group, args.port, args.scenario, args.timeout_s)


if __name__ == "__main__":
    sys.exit(main())
