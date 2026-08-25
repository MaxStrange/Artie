"""
RTACP - small, latency-sensitive messages, unicast or broadcast.
"""
import threading

import pytest

from artie_can import enums, errors

from conftest import receive_matching, send_rtacp

RTACP_ONLY = enums.Protocol.RTACP


def test_rtacp_unicast_reaches_its_target(make_node):
    sender = make_node(0x01, protocols=RTACP_ONLY)
    receiver = make_node(0x02, protocols=RTACP_ONLY)

    send_rtacp(sender, 0x02, b"\xde\xad\xbe\xef")

    message = receive_matching(receiver.receive_rtacp, lambda m: m.data == b"\xde\xad\xbe\xef")
    assert message.source_address == 0x01
    assert message.target_address == 0x02


def test_rtacp_broadcast_reaches_every_node(make_node):
    sender = make_node(0x01, protocols=RTACP_ONLY)
    first = make_node(0x02, protocols=RTACP_ONLY)
    second = make_node(0x03, protocols=RTACP_ONLY)

    # Broadcasts are not acknowledged, so this returns as soon as the frame is on the bus.
    sender.rtacp_send(enums.BROADCAST_ADDRESS, b"\x11\x22")

    for receiver in (first, second):
        message = receive_matching(receiver.receive_rtacp, lambda m: m.data == b"\x11\x22")
        assert message.source_address == 0x01
        assert message.is_broadcast


def test_rtacp_priority_survives_the_wire(make_node):
    sender = make_node(0x01, protocols=RTACP_ONLY)
    receiver = make_node(0x02, protocols=RTACP_ONLY)

    sender.rtacp_send(enums.BROADCAST_ADDRESS, b"\x77", priority=enums.Priority.HIGHEST)

    message = receive_matching(receiver.receive_rtacp, lambda m: m.data == b"\x77")
    assert message.priority == enums.Priority.HIGHEST


def test_rtacp_message_is_handed_to_the_callback(make_node):
    arrived = threading.Event()
    seen = []

    def on_rtacp(message):
        seen.append(message)
        arrived.set()

    sender = make_node(0x01, protocols=RTACP_ONLY)
    make_node(0x02, protocols=RTACP_ONLY, on_rtacp=on_rtacp)

    sender.rtacp_send(enums.BROADCAST_ADDRESS, b"\xa5")

    assert arrived.wait(5.0), "the callback was never called"
    assert seen[0].data == b"\xa5"


def test_rtacp_receive_and_callback_are_alternatives(make_node):
    with_callback = make_node(0x01, protocols=RTACP_ONLY, on_rtacp=lambda message: None)

    with pytest.raises(errors.InvalidArgument):
        with_callback.receive_rtacp(timeout=0.1)


def test_rtacp_receive_times_out_on_a_silent_bus(make_node):
    listener = make_node(0x01, protocols=RTACP_ONLY)

    with pytest.raises(errors.Timeout):
        listener.receive_rtacp(timeout=0.2)


def test_rtacp_rejects_more_than_one_frame_of_data(make_node):
    sender = make_node(0x01, protocols=RTACP_ONLY)

    with pytest.raises(errors.InvalidArgument):
        sender.rtacp_send(0x02, bytes(enums.MAX_FRAME_DATA_LENGTH + 1))
