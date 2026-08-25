"""
CLI code for the Artie CAN bus.

Unlike the other modules, this one does not talk to an Artie micro service - it joins the bus
itself, as an ordinary node, using the `artie_can` Python bindings. That makes it a debugging tool
for the bus rather than a control surface for Artie: send a message and see who answers, watch what
is being published, ask another node who it is.

Every command brings a node up, does one thing, and takes it down again, so nothing here holds an
address for longer than the command lasts. Pick a `--node-address` no real node on the bus is
using; two nodes sharing an address silently discard each other's frames.

Only the UDP multicast transport is offered. The other backend the library supports drives an
MCP2515 over SPI, which needs the caller to supply the SPI transfer functions - something a CLI
process has no way to do.
"""
from .. import common
import argparse
import json

#: Bus the commands join unless told otherwise. Matches the library's own defaults.
DEFAULT_GROUP = "239.0.0.1"
DEFAULT_PORT = 5000


def _open_node(args):
    """Join the bus as a node taking part in every protocol.

    Imported lazily, and per command rather than at module import, because artie_can is a compiled
    extension that is not present in every environment artie-cli runs in - and only these commands
    need it.
    """
    from artie_can import backends, enums, node

    return node.Node(
        backends.UdpMulticastBackend(group=args.group, port=args.port),
        address=args.node_address,
        protocols=(
            enums.Protocol.RTACP | enums.Protocol.PSACP
            | enums.Protocol.BWACP | enums.Protocol.RPCACP
        ),
        name=args.name,
    )


def _priority(name: str):
    from artie_can import enums

    return enums.Priority[name.upper()]


def _report(args, cmd: str, message):
    common.format_print_result(message, "can", cmd, args.artie_id)


def _cmd_can_info(args):
    """Report what this node would be on the bus, and whether it can actually join it."""
    from artie_can import enums

    info = {
        "transport": "udp-multicast",
        "group": args.group,
        "port": args.port,
        "node_address": f"0x{args.node_address:02X}",
        "node_name": args.name,
        "max_nodes": enums.MAX_NODES,
        "max_frame_data_length": enums.MAX_FRAME_DATA_LENGTH,
    }
    try:
        with _open_node(args) as bus_node:
            info["status"] = "joined"
            info["protocols"] = [protocol.name for protocol in bus_node.protocols]
    except Exception as e:
        info["status"] = f"unavailable ({e})"

    _report(args, "info", json.dumps(info, indent=2))


def _cmd_can_rtacp_send(args):
    """Send one small real-time message, to a single node or to every node."""
    from artie_can import enums

    data = bytes.fromhex(args.data) if args.data else b""
    target = enums.BROADCAST_ADDRESS if args.broadcast else args.target
    with _open_node(args) as bus_node:
        bus_node.rtacp_send(target, data, priority=_priority(args.priority))

    # A unicast send does not return until the target acknowledges it, so reaching this line means
    # more than "the frame went out" - see the note about Timeout in the library's README.
    _report(args, "rtacp-send", f"sent {len(data)} bytes to 0x{target:02X}")


def _cmd_can_rtacp_receive(args):
    """Wait for the next real-time message addressed to this node."""
    with _open_node(args) as bus_node:
        message = bus_node.receive_rtacp(timeout=args.timeout_s)

    _report(args, "rtacp-receive",
            f"from 0x{message.source_address:02X} to 0x{message.target_address:02X}: "
            f"{message.data.hex()}")


def _cmd_can_publish(args):
    """Publish one message to a topic. Fire and forget: nobody acknowledges it."""
    data = bytes.fromhex(args.data) if args.data else b""
    with _open_node(args) as bus_node:
        bus_node.publish(args.topic, data, priority=_priority(args.priority),
                         high_priority=args.high_priority)

    _report(args, "publish", f"published {len(data)} bytes to topic 0x{args.topic:02X}")


def _cmd_can_subscribe(args):
    """Subscribe to a topic and print the next message published to it."""
    with _open_node(args) as bus_node:
        bus_node.subscribe(args.topic)
        message = bus_node.receive_psacp(timeout=args.timeout_s)

    _report(args, "subscribe",
            f"from 0x{message.source_address:02X} on topic 0x{message.topic:02X}: "
            f"{message.data.hex()}")


def _cmd_can_block_write(args):
    """Write a block of arbitrary size into one or more nodes' block buffers."""
    from artie_can import enums

    with open(args.file, "rb") as f:
        payload = f.read()

    target = enums.MULTICAST_ADDRESS if args.target is None else args.target
    with _open_node(args) as bus_node:
        bus_node.block_write(
            payload,
            offset=args.offset,
            target_address=target,
            target_class=enums.NodeClass[args.target_class.upper()],
            priority=_priority(args.priority),
        )

    _report(args, "block-write",
            f"wrote {len(payload)} bytes to 0x{target:02X} at offset {args.offset}")


def _cmd_can_block_receive(args):
    """Wait for a block write to land here, and save what arrived."""
    with _open_node(args) as bus_node:
        block = bus_node.receive_block(timeout=args.timeout_s)

    with open(args.file, "wb") as f:
        f.write(block.data)

    _report(args, "block-receive",
            f"received {len(block)} bytes from 0x{block.source_address:02X} at offset "
            f"{block.offset} -> {args.file}")


def _cmd_can_whoami(args):
    """Ask a node to identify itself. Every node answers this one internally."""
    with _open_node(args) as bus_node:
        identity = bus_node.whoami(args.target)

    _report(args, "whoami",
            f"0x{identity.node_address:02X} is {identity.node_name!r} running firmware "
            f"{identity.firmware_version}")


def _cmd_can_status(args):
    """Ask a node for its uptime and error flags. Every node answers this one internally."""
    with _open_node(args) as bus_node:
        status = bus_node.node_status(args.target)

    _report(args, "status",
            f"0x{args.target:02X} up {status.uptime_ms} ms, error flags 0x{status.error_flags:08X}")


def _cmd_can_list_procedures(args):
    """Ask a node which procedures it exposes. Results come one page of IDs at a time."""
    with _open_node(args) as bus_node:
        listed = bus_node.list_procedures(args.target, page=args.page)

    described = [
        {
            "procedure_id": f"0x{entry.procedure_id:02X}",
            "name": entry.name,
            "synchronous": entry.synchronous,
            "params": list(entry.param_type_names),
        }
        for entry in listed if entry.registered
    ]
    _report(args, "list-procedures", json.dumps(described, indent=2))


def _cmd_can_rpc_call(args):
    """Call a device-specific procedure on another node.

    Both ends of an RPC agree on the procedure's signature out of band, so it has to be described
    here: --param is the type of each argument in order, and --returns the type of the result. The
    library's own type names are used ("uint8_t", "float", ...); a type it does not know as a
    primitive is passed through as raw bytes and needs its size, which is what --return-size is
    for.
    """
    from artie_can import rpc

    params = tuple(rpc.RpcParam(type_name) for type_name in args.param)
    returns = None
    if args.returns is not None:
        returns = rpc.RpcParam(args.returns, size=args.return_size)

    signature = rpc.RpcSignature(
        procedure_id=args.procedure_id,
        name=args.name_of_procedure,
        params=params,
        returns=returns,
        synchronous=args.synchronous,
    )

    # Arguments arrive as strings; the signature says how each should be read.
    arguments = [
        param.decode(bytes.fromhex(value)) if not param.is_primitive
        else (float(value) if param.type_name in ("float", "double") else int(value, 0))
        for param, value in zip(params, args.arg)
    ]

    with _open_node(args) as bus_node:
        result = bus_node.call(args.target, signature, *arguments)

    _report(args, "rpc-call",
            f"0x{args.target:02X} {args.name_of_procedure} -> {result}")


def fill_subparser(parser: argparse.ArgumentParser, parent: argparse.ArgumentParser):
    subparsers = parser.add_subparsers(title="Commands", description="The CAN module's commands")

    # Args that are useful for all CAN module commands
    option_parser = argparse.ArgumentParser(parents=[parent], add_help=False)
    group = option_parser.add_argument_group("CAN Module", "CAN Module Options")
    group.add_argument("--node-address", type=lambda x: int(x, 0), default=0x01, help="The address this CLI takes on the bus (0x01-0x3E). Must not clash with a node that is already there. Default: 0x01")
    group.add_argument("--name", type=str, default="artie-cli", help="The name this CLI reports through WHOAMI. Default: artie-cli")
    group.add_argument("--group", type=str, default=DEFAULT_GROUP, help=f"Multicast group the bus runs on. Default: {DEFAULT_GROUP}")
    group.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Multicast port the bus runs on. Default: {DEFAULT_PORT}")

    priorities = ["HIGHEST", "HIGH", "MEDIUM", "LOW"]

    # Info command
    info_parser = subparsers.add_parser("info", parents=[option_parser], help="Display CAN bus information")
    info_parser.set_defaults(cmd=_cmd_can_info)

    # RTACP send command
    rtacp_send_parser = subparsers.add_parser("rtacp-send", parents=[option_parser], help="Send a real-time message (up to 8 bytes)")
    rtacp_send_target = rtacp_send_parser.add_mutually_exclusive_group(required=True)
    rtacp_send_target.add_argument("--target", type=lambda x: int(x, 0), help="Address of the node to send to")
    rtacp_send_target.add_argument("--broadcast", action="store_true", help="Send to every node instead. Broadcasts are not acknowledged.")
    rtacp_send_parser.add_argument("--data", type=str, default="", help="Payload as a hex string, up to 8 bytes")
    rtacp_send_parser.add_argument("--priority", type=str, default="MEDIUM", choices=priorities, help="Bus arbitration priority")
    rtacp_send_parser.set_defaults(cmd=_cmd_can_rtacp_send)

    # RTACP receive command
    rtacp_recv_parser = subparsers.add_parser("rtacp-receive", parents=[option_parser], help="Wait for a real-time message addressed to this node")
    rtacp_recv_parser.add_argument("--timeout-s", type=float, default=5.0, help="How long to wait, in seconds. Default: 5")
    rtacp_recv_parser.set_defaults(cmd=_cmd_can_rtacp_receive)

    # Publish command
    publish_parser = subparsers.add_parser("publish", parents=[option_parser], help="Publish to a topic")
    publish_parser.add_argument("--topic", type=lambda x: int(x, 0), required=True, help="Topic ID (0x0B-0xF4, or 0x00 to reach every subscriber)")
    publish_parser.add_argument("--data", type=str, default="", help="Payload as a hex string, up to 8 bytes")
    publish_parser.add_argument("--priority", type=str, default="MEDIUM", choices=priorities, help="Bus arbitration priority within the chosen PSACP protocol")
    publish_parser.add_argument("--high-priority", action="store_true", help="Use the high-priority PSACP protocol, which wins arbitration against the low-priority one")
    publish_parser.set_defaults(cmd=_cmd_can_publish)

    # Subscribe command
    subscribe_parser = subparsers.add_parser("subscribe", parents=[option_parser], help="Subscribe to a topic and print the next message published to it")
    subscribe_parser.add_argument("--topic", type=lambda x: int(x, 0), required=True, help="Topic ID to subscribe to (0x0B-0xF4)")
    subscribe_parser.add_argument("--timeout-s", type=float, default=5.0, help="How long to wait, in seconds. Default: 5")
    subscribe_parser.set_defaults(cmd=_cmd_can_subscribe)

    # Block write command
    block_write_parser = subparsers.add_parser("block-write", parents=[option_parser], help="Write a file into other nodes' block buffers")
    block_write_parser.add_argument("file", type=str, help="File whose contents to send")
    block_write_parser.add_argument("--target", type=lambda x: int(x, 0), default=None, help="Address of the node to write to. If not given, every node whose class matches --target-class is written to.")
    block_write_parser.add_argument("--target-class", type=str, default="SBC", choices=["SBC", "MCU", "SENSOR", "MOTOR"], help="Which class of node to write to. Ignored when --target is given.")
    block_write_parser.add_argument("--offset", type=lambda x: int(x, 0), default=0, help="Where in each receiver's block buffer to write. Default: 0")
    block_write_parser.add_argument("--priority", type=str, default="MEDIUM", choices=priorities, help="Bus arbitration priority for the transfer's frames")
    block_write_parser.set_defaults(cmd=_cmd_can_block_write)

    # Block receive command
    block_receive_parser = subparsers.add_parser("block-receive", parents=[option_parser], help="Wait for a block write addressed to this node and save it")
    block_receive_parser.add_argument("file", type=str, help="Where to write what arrives")
    block_receive_parser.add_argument("--timeout-s", type=float, default=60.0, help="How long to wait, in seconds. Default: 60")
    block_receive_parser.set_defaults(cmd=_cmd_can_block_receive)

    # WHOAMI command
    whoami_parser = subparsers.add_parser("whoami", parents=[option_parser], help="Ask a node to identify itself")
    whoami_parser.add_argument("--target", type=lambda x: int(x, 0), required=True, help="Address of the node to ask")
    whoami_parser.set_defaults(cmd=_cmd_can_whoami)

    # STATUS command
    status_parser = subparsers.add_parser("status", parents=[option_parser], help="Ask a node for its uptime and error flags")
    status_parser.add_argument("--target", type=lambda x: int(x, 0), required=True, help="Address of the node to ask")
    status_parser.set_defaults(cmd=_cmd_can_status)

    # LIST command
    list_parser = subparsers.add_parser("list-procedures", parents=[option_parser], help="Ask a node which procedures it exposes")
    list_parser.add_argument("--target", type=lambda x: int(x, 0), required=True, help="Address of the node to ask")
    list_parser.add_argument("--page", type=int, default=0, help="Which page of procedure IDs to fetch. Default: 0")
    list_parser.set_defaults(cmd=_cmd_can_list_procedures)

    # RPC call command
    rpc_call_parser = subparsers.add_parser("rpc-call", parents=[option_parser], help="Call a device-specific procedure on another node")
    rpc_call_parser.add_argument("--target", type=lambda x: int(x, 0), required=True, help="Address of the node to call. There is no broadcast in RPCACP.")
    rpc_call_parser.add_argument("--procedure-id", type=lambda x: int(x, 0), required=True, help="Procedure ID to call (0x10-0x7F; below that is reserved for the standard procedures)")
    rpc_call_parser.add_argument("--name-of-procedure", type=str, default="PROCEDURE", help="The procedure's name. Only used in messages, so it need not match the remote's.")
    rpc_call_parser.add_argument("--param", type=str, action="append", default=[], help="Type of one parameter, in argument order, e.g. --param uint8_t. Repeatable.")
    rpc_call_parser.add_argument("--arg", type=str, action="append", default=[], help="Value of one argument, in order. Numbers for primitive parameters, a hex string for anything else. Repeatable.")
    rpc_call_parser.add_argument("--returns", type=str, default=None, help="Type of the return value. Leave off for a procedure that returns nothing.")
    rpc_call_parser.add_argument("--return-size", type=int, default=None, help="Size in bytes of the return value. Only needed when --returns is not one of the library's primitive types.")
    rpc_call_parser.add_argument("--asynchronous", action="store_false", dest="synchronous", default=True, help="Do not wait for a result; return once the remote has accepted the request.")
    rpc_call_parser.set_defaults(cmd=_cmd_can_rpc_call)
