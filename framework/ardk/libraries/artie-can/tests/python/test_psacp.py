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


def test_publish_rejects_more_than_a_whole_message(make_node):
    publisher = make_node(0x01, protocols=PSACP_ONLY)

    with pytest.raises(errors.InvalidArgument):
        publisher.publish(TOPIC, bytes(enums.MAX_PSACP_MESSAGE_SIZE + 1))


# Sizes chosen around the boundaries the fragmentation arithmetic turns on: the last payload that
# fits in a single PUB frame, the first that does not, the last that PUB_START and PUB_END can carry
# between them with no PUB_MORE at all, the first that needs one, and the largest the protocol
# allows.
@pytest.mark.parametrize("size", [8, 9, 15, 16, 100, 526, 527])
def test_message_of_any_size_survives_the_round_trip(make_node, size):
    publisher = make_node(0x01, protocols=PSACP_ONLY)
    subscriber = make_node(0x02, protocols=PSACP_ONLY)
    subscriber.subscribe(TOPIC)

    # Varied bytes rather than a repeated one, so a fragment delivered out of order or duplicated
    # shows up as a mismatch rather than passing by luck.
    payload = bytes((index * 7 + size) % 256 for index in range(size))
    publisher.publish(TOPIC, payload)

    message = receive_matching(subscriber.receive_psacp, lambda m: len(m.data) == size)
    assert message.data == payload
    assert message.topic == TOPIC
    assert message.source_address == 0x01
    assert subscriber.psacp_messages_dropped == 0


def test_multi_frame_message_is_handed_to_the_callback(make_node):
    arrived = threading.Event()
    seen = []

    def on_psacp(message):
        seen.append(message)
        arrived.set()

    publisher = make_node(0x01, protocols=PSACP_ONLY)
    subscriber = make_node(0x02, protocols=PSACP_ONLY, on_psacp=on_psacp)
    subscriber.subscribe(TOPIC)

    payload = bytes(range(200))
    publisher.publish(TOPIC, payload)

    assert arrived.wait(10.0), "the callback was never called"
    assert seen[0].data == payload


def test_multi_frame_publish_is_rejected_at_high_priority(make_node):
    """High-priority PSACP arbitrates above BWACP, so long bursts are not allowed there."""
    publisher = make_node(0x01, protocols=PSACP_ONLY)

    # The single-frame case is unaffected, which is what makes this a size limit rather than a ban.
    publisher.publish(TOPIC, bytes(enums.MAX_FRAME_DATA_LENGTH), high_priority=True)

    with pytest.raises(errors.InvalidArgument):
        publisher.publish(TOPIC, bytes(enums.MAX_FRAME_DATA_LENGTH + 1), high_priority=True)


def test_concurrent_publishers_on_one_topic_are_not_spliced(make_node):
    """Reassembly is keyed on (sender, topic), not topic alone.

    CAN arbitration interleaves two publishers' fragments, so keying on the topic alone would
    stitch them into one corrupt message rather than delivering two intact ones.
    """
    first = make_node(0x01, protocols=PSACP_ONLY)
    second = make_node(0x02, protocols=PSACP_ONLY)
    subscriber = make_node(0x03, protocols=PSACP_ONLY)
    subscriber.subscribe(TOPIC)

    from_first = bytes([0xA1]) * 120
    from_second = bytes([0xB2]) * 200

    # Overlap the two transfers: neither publish returns until its own frames are away, so they are
    # started from separate threads to get both on the bus at once.
    threads = [
        threading.Thread(target=first.publish, args=(TOPIC, from_first)),
        threading.Thread(target=second.publish, args=(TOPIC, from_second)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    received = {}
    for _ in range(2):
        message = receive_matching(
            subscriber.receive_psacp, lambda m: m.source_address not in received, timeout=15.0
        )
        received[message.source_address] = message.data

    assert received[0x01] == from_first
    assert received[0x02] == from_second


def test_publisher_subscribed_to_its_own_topic_receives_its_message(make_node):
    """Nothing echoes a node's own frames back to it, so self-delivery is handled in the library."""
    publisher = make_node(0x01, protocols=PSACP_ONLY)
    publisher.subscribe(TOPIC)

    payload = bytes(range(150))
    publisher.publish(TOPIC, payload)

    message = receive_matching(publisher.receive_psacp, lambda m: len(m.data) == len(payload))
    assert message.data == payload
    assert message.source_address == 0x01
