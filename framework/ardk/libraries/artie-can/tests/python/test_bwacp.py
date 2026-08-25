"""
BWACP - bulk block writes into a receiver's block buffer.

A transfer spans many frames and is acknowledged frame by frame, so it is only ever reported once
the whole thing has landed and its CRC checks out.
"""
import threading

import pytest

from artie_can import enums, errors

BWACP_ONLY = enums.Protocol.BWACP

#: Big enough to span many DATA frames (8 payload bytes each), small enough to stay quick.
PAYLOAD = bytes(range(256)) * 4

#: Room for PAYLOAD at every offset the tests use.
BUFFER_SIZE = 8192


def test_block_write_lands_in_the_receivers_buffer(make_node):
    sender = make_node(0x01, protocols=BWACP_ONLY)
    receiver = make_node(0x02, protocols=BWACP_ONLY, block_buffer_size=BUFFER_SIZE)

    sender.block_write(PAYLOAD, target_address=0x02)

    block = receiver.receive_block(timeout=30.0)
    assert bytes(receiver.block_buffer[:len(PAYLOAD)]) == PAYLOAD
    assert block.source_address == 0x01
    assert receiver.block_bytes_received == len(PAYLOAD)


def test_completed_transfer_is_reported_with_its_payload(make_node):
    sender = make_node(0x01, protocols=BWACP_ONLY)
    receiver = make_node(0x02, protocols=BWACP_ONLY, block_buffer_size=BUFFER_SIZE)

    sender.block_write(PAYLOAD, target_address=0x02)

    block = receiver.receive_block(timeout=30.0)
    assert block.data == PAYLOAD
    assert block.offset == 0
    assert len(block) == len(PAYLOAD)


def test_block_write_honours_the_offset_it_was_given(make_node):
    sender = make_node(0x01, protocols=BWACP_ONLY)
    receiver = make_node(0x02, protocols=BWACP_ONLY, block_buffer_size=BUFFER_SIZE)

    sender.block_write(PAYLOAD, offset=4096, target_address=0x02)

    block = receiver.receive_block(timeout=30.0)
    assert block.offset == 4096
    assert block.data == PAYLOAD
    assert bytes(receiver.block_buffer[4096:4096 + len(PAYLOAD)]) == PAYLOAD
    # Nothing was written where the transfer did not ask for it.
    assert bytes(receiver.block_buffer[:4096]) == bytes(4096)


def test_multicast_block_write_reaches_only_the_addressed_class(make_node):
    sender = make_node(0x01, protocols=BWACP_ONLY)
    sensor = make_node(
        0x02, protocols=BWACP_ONLY, node_class=enums.NodeClass.SENSOR, block_buffer_size=BUFFER_SIZE
    )
    motor = make_node(
        0x03, protocols=BWACP_ONLY, node_class=enums.NodeClass.MOTOR, block_buffer_size=BUFFER_SIZE
    )

    sender.block_write(
        PAYLOAD, target_address=enums.MULTICAST_ADDRESS, target_class=enums.NodeClass.SENSOR
    )

    assert sensor.receive_block(timeout=30.0).data == PAYLOAD
    with pytest.raises(errors.Timeout):
        motor.receive_block(timeout=1.0)


def test_completed_transfer_is_handed_to_the_callback(make_node):
    arrived = threading.Event()
    seen = []

    def on_block_write(block):
        seen.append(block)
        arrived.set()

    sender = make_node(0x01, protocols=BWACP_ONLY)
    make_node(
        0x02, protocols=BWACP_ONLY, block_buffer_size=BUFFER_SIZE, on_block_write=on_block_write
    )

    sender.block_write(PAYLOAD, target_address=0x02)

    assert arrived.wait(30.0), "the callback was never called"
    assert seen[0].data == PAYLOAD


def test_receive_block_and_callback_are_alternatives(make_node):
    with_callback = make_node(0x01, protocols=BWACP_ONLY, on_block_write=lambda block: None)

    with pytest.raises(errors.InvalidArgument):
        with_callback.receive_block(timeout=0.1)


def test_block_write_must_carry_something(make_node):
    sender = make_node(0x01, protocols=BWACP_ONLY)

    with pytest.raises(errors.InvalidArgument):
        sender.block_write(b"", target_address=0x02)
