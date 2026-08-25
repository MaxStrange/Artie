"""
Shared fixtures for the Artie CAN Python unit tests.

Every test that needs a bus gets its own UDP multicast port, so suites never see each other's
frames even though they all run in one process. The nodes themselves are real ``Node`` objects
running the real C library - what these tests do not cover is frames crossing a machine boundary,
which is what the container-based integration tests in ``itest/`` are for.
"""
import itertools
import time

import pytest

from artie_can import backends, enums, errors, node

#: Multicast group the Python unit tests run on. Deliberately different from the group the C
#: Unity suite uses and from the integration tests' group, so a run of one can never be mistaken
#: for bus traffic belonging to another.
MULTICAST_GROUP = "239.0.0.21"

#: A fresh port per bus. Nodes only ever hear each other when the group *and* port match, so this
#: is what isolates one test's nodes from the next's.
_PORTS = itertools.count(7200)

#: How long to let a freshly opened node settle before using it. Joining a multicast group is not
#: instantaneous, and a frame sent before the join lands is simply not delivered.
SETTLE_S = 0.15

#: Every protocol at once, which is what most tests want - a node only answers for the protocols
#: it was configured with.
ALL_PROTOCOLS = enums.Protocol.RTACP | enums.Protocol.PSACP | enums.Protocol.BWACP | enums.Protocol.RPCACP


@pytest.fixture
def bus():
    """Connection details for a multicast bus nobody else in this run is using."""
    return {"group": MULTICAST_GROUP, "port": next(_PORTS)}


@pytest.fixture
def make_node(bus):
    """Factory for nodes on this test's bus. Everything it hands out is closed afterwards."""
    created = []

    def factory(address: int, protocols: enums.Protocol = ALL_PROTOCOLS, **kwargs) -> node.Node:
        created.append(node.Node(
            backends.UdpMulticastBackend(**bus), address=address, protocols=protocols, **kwargs
        ))
        time.sleep(SETTLE_S)
        return created[-1]

    yield factory

    for created_node in reversed(created):
        created_node.close()


def send_rtacp(sender: node.Node, target: int, data: bytes, attempts: int = 5, **kwargs) -> None:
    """Send a unicast RTACP message, tolerating an ACK that arrives after the protocol's budget.

    RTACP acknowledges within 10 ms end to end, which is tight for a state machine driven from a
    scheduled userspace thread: a send whose ACK misses that window raises ``Timeout`` even though
    the frame itself was delivered. Retrying is safe for the tests that use this because each of
    them looks for one matching message rather than counting them, so a duplicate changes nothing.
    """
    for attempt in range(attempts):
        try:
            sender.rtacp_send(target, data, **kwargs)
            return
        except errors.Timeout:
            if attempt == attempts - 1:
                raise


def call_rpc(call, *args, attempts: int = 3, **kwargs):
    """Make an RPC call, trying again if the answer does not come back in time.

    An RPCACP exchange is a run of frames that each have to be acknowledged inside 100 ms, and the
    whole call inside 5 seconds. Both ends drive that from a scheduled userspace thread rather than
    an interrupt, and an inbound request does not even wake the answering node - the library
    consumes those frames itself, so the far end only notices on its next tick. That makes a
    late-running host enough to blow the budget, which surfaces as ``Timeout``.

    Only used here for procedures that can be run twice without it mattering: the standard WHOAMI,
    STATUS and LIST, and the test procedures that are pure functions of their arguments. Anything
    that records what it was called with is left alone, because a repeat would change the answer.
    """
    for attempt in range(attempts):
        try:
            return call(*args, **kwargs)
        except errors.Timeout:
            if attempt == attempts - 1:
                raise


def receive_matching(receive, predicate, timeout: float = 5.0):
    """Read messages until one satisfies ``predicate``, or ``timeout`` runs out.

    Nodes hear everything on the bus, including traffic a test did not send - a peer's RTACP ACK,
    a retry's duplicate - so tests that care about one particular message filter rather than
    assuming the first thing to arrive is theirs.
    """
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise errors.Timeout(f"nothing matching arrived within {timeout:g}s")
        message = receive(timeout=remaining)
        if predicate(message):
            return message
