"""
Node construction and lifecycle - the parts that do not need anything on the bus.
"""
import pytest

from artie_can import backends, enums, errors, node

from conftest import ALL_PROTOCOLS


@pytest.fixture
def backend(bus):
    """A transport for a node that is never opened, so nothing ever joins the group."""
    return backends.UdpMulticastBackend(**bus)


def test_address_must_be_one_a_node_can_have(bus):
    """0 is the broadcast address and 63 is BWACP's multicast address."""
    for address in (0, enums.MULTICAST_ADDRESS, 200):
        with pytest.raises(errors.InvalidArgument):
            node.Node(backends.UdpMulticastBackend(**bus), address=address, auto_open=False)


def test_a_node_must_take_part_in_something(backend):
    with pytest.raises(errors.InvalidArgument):
        node.Node(backend, address=0x01, protocols=enums.Protocol(0), auto_open=False)


def test_block_buffer_must_have_room_for_something(backend):
    with pytest.raises(errors.InvalidArgument):
        node.Node(backend, address=0x01, block_buffer_size=0, auto_open=False)


def test_name_defaults_to_the_address(backend):
    assert node.Node(backend, address=0x0A, auto_open=False).name == "artie-node-0x0a"


def test_auto_open_can_be_deferred(backend):
    deferred = node.Node(backend, address=0x01, auto_open=False)

    assert not deferred.is_open
    assert deferred.open() is deferred
    assert deferred.is_open
    deferred.close()


def test_open_and_close_are_both_idempotent(make_node):
    opened = make_node(0x01, protocols=enums.Protocol.RTACP)

    opened.open()
    assert opened.is_open
    opened.close()
    opened.close()
    assert not opened.is_open


def test_node_works_as_a_context_manager(backend):
    with node.Node(backend, address=0x01, auto_open=False) as opened:
        assert opened.is_open

    assert not opened.is_open


def test_repr_reports_the_address_and_whether_it_is_open(backend):
    closed = node.Node(backend, address=0x0B, auto_open=False)

    assert "0x0b" in repr(closed)
    assert "closed" in repr(closed)
    with closed:
        assert "open" in repr(closed)


def test_configuration_is_reported_back(bus, make_node):
    configured = make_node(
        0x02, protocols=ALL_PROTOCOLS, node_class=enums.NodeClass.SENSOR, name="left-eyebrow"
    )

    assert configured.address == 0x02
    assert configured.name == "left-eyebrow"
    assert configured.node_class == enums.NodeClass.SENSOR
    assert configured.protocols == ALL_PROTOCOLS
    assert configured.backend.group == bus["group"]


def test_methods_for_protocols_the_node_skipped_are_rejected(make_node):
    rtacp_only = make_node(0x01, protocols=enums.Protocol.RTACP)

    with pytest.raises(errors.InvalidArgument):
        rtacp_only.publish(0x0C, b"\x01")
    with pytest.raises(errors.InvalidArgument):
        rtacp_only.block_write(b"\x01")
    with pytest.raises(errors.InvalidArgument):
        rtacp_only.whoami(0x02)


def test_using_a_closed_node_raises_rather_than_hanging(make_node):
    closed = make_node(0x01, protocols=enums.Protocol.RTACP)
    closed.close()

    with pytest.raises(errors.NodeClosed):
        closed.rtacp_send(enums.BROADCAST_ADDRESS, b"\x01")


def test_block_buffer_is_the_size_that_was_asked_for(make_node):
    sized = make_node(0x01, protocols=enums.Protocol.BWACP, block_buffer_size=2048)

    assert len(sized.block_buffer) == 2048
    assert sized.block_bytes_received == 0


def test_a_quiet_node_reports_no_background_errors(make_node):
    quiet = make_node(0x01, protocols=enums.Protocol.RTACP)

    assert quiet.last_background_error == errors.ErrorFlag.NONE


def test_block_write_timeout_grows_with_the_payload():
    """The deadline covers the whole transfer and does not move as it progresses."""
    small = node.block_write_timeout(8)
    large = node.block_write_timeout(8 * 1000)

    assert large > small >= node.BLOCK_TIMEOUT_BASE
