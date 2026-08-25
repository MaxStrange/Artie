"""
PSACP - fire-and-forget publish/subscribe on numbered topics.
"""
import threading

import pytest

from artie_can import enums, errors

from conftest import receive_matching

PSACP_ONLY = enums.Protocol.PSACP

#: Two topics inside the protocol's valid 0x0B-0xF4 range.
TOPIC = 0x0C
OTHER_TOPIC = 0x20


def test_publish_reaches_a_subscriber(make_node):
    publisher = make_node(0x01, protocols=PSACP_ONLY)
    subscriber = make_node(0x02, protocols=PSACP_ONLY)
    subscriber.subscribe(TOPIC)

    publisher.publish(TOPIC, b"\x01\x02\x03")

    message = receive_matching(subscriber.receive_psacp, lambda m: m.data == b"\x01\x02\x03")
    assert message.topic == TOPIC
    assert message.source_address == 0x01


def test_publish_on_an_unsubscribed_topic_is_not_delivered(make_node):
    publisher = make_node(0x01, protocols=PSACP_ONLY)
    subscriber = make_node(0x02, protocols=PSACP_ONLY)
    subscriber.subscribe(TOPIC)

    publisher.publish(OTHER_TOPIC, b"\xff")

    with pytest.raises(errors.Timeout):
        subscriber.receive_psacp(timeout=0.5)


def test_broadcast_topic_reaches_every_subscriber(make_node):
    publisher = make_node(0x01, protocols=PSACP_ONLY)
    first = make_node(0x02, protocols=PSACP_ONLY)
    second = make_node(0x03, protocols=PSACP_ONLY)
    first.subscribe(TOPIC)
    second.subscribe(OTHER_TOPIC)

    publisher.publish(enums.BROADCAST_TOPIC, b"\xbe\xef")

    for subscriber in (first, second):
        message = receive_matching(subscriber.receive_psacp, lambda m: m.data == b"\xbe\xef")
        assert message.topic == enums.BROADCAST_TOPIC


def test_high_priority_publish_arrives_marked_as_such(make_node):
    publisher = make_node(0x01, protocols=PSACP_ONLY)
    subscriber = make_node(0x02, protocols=PSACP_ONLY)
    subscriber.subscribe(TOPIC)

    publisher.publish(TOPIC, b"\x5a", high_priority=True)

    message = receive_matching(subscriber.receive_psacp, lambda m: m.data == b"\x5a")
    assert message.high_priority


def test_publish_is_handed_to_the_callback(make_node):
    arrived = threading.Event()
    seen = []

    def on_psacp(message):
        seen.append(message)
        arrived.set()

    publisher = make_node(0x01, protocols=PSACP_ONLY)
    subscriber = make_node(0x02, protocols=PSACP_ONLY, on_psacp=on_psacp)
    subscriber.subscribe(TOPIC)

    publisher.publish(TOPIC, b"\x42")

    assert arrived.wait(5.0), "the callback was never called"
    assert seen[0].data == b"\x42"


def test_publish_rejects_more_than_one_frame_of_data(make_node):
    publisher = make_node(0x01, protocols=PSACP_ONLY)

    with pytest.raises(errors.InvalidArgument):
        publisher.publish(TOPIC, bytes(enums.MAX_FRAME_DATA_LENGTH + 1))
