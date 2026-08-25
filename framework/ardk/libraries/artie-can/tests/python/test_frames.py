"""
Frame packing and parsing.

Conversion runs through the C library's own pack/parse functions, so what these check is that a
message survives the trip out to the wire format and back with every field intact.
"""
import pytest

from artie_can import enums, frames


def test_frame_rejects_more_data_than_fits():
    with pytest.raises(ValueError):
        frames.Frame(id=0, data=bytes(enums.MAX_FRAME_DATA_LENGTH + 1))


def test_frame_decodes_the_fields_packed_into_its_id():
    message = frames.RtacpMessage(source_address=0x05, target_address=0x2A, data=b"\x01")

    frame = message._to_frame()

    assert frame.source_address == 0x05
    assert frame.target_address == 0x2A
    assert frame.protocol_id == enums._PROTOCOL_ID_RTACP


def test_frame_repr_shows_its_id_and_payload():
    text = repr(frames.Frame(id=0x1234ABCD, data=b"\xde\xad"))

    assert "0x1234ABCD" in text
    assert "de ad" in text


def test_rtacp_message_survives_the_round_trip():
    original = frames.RtacpMessage(
        source_address=0x07,
        target_address=0x11,
        data=b"\xde\xad\xbe\xef",
        priority=enums.Priority.HIGH,
    )

    restored = frames.RtacpMessage._from_frame(original._to_frame())

    assert restored.source_address == original.source_address
    assert restored.target_address == original.target_address
    assert restored.data == original.data
    assert restored.priority == original.priority


def test_rtacp_empty_payload_survives_the_round_trip():
    original = frames.RtacpMessage(source_address=0x01, target_address=0x02)

    assert frames.RtacpMessage._from_frame(original._to_frame()).data == b""


def test_rtacp_message_knows_when_it_is_a_broadcast():
    to_everyone = frames.RtacpMessage(source_address=1, target_address=enums.BROADCAST_ADDRESS)
    to_one_node = frames.RtacpMessage(source_address=1, target_address=0x02)

    assert to_everyone.is_broadcast
    assert not to_one_node.is_broadcast


def test_psacp_message_survives_the_round_trip():
    original = frames.PsacpMessage(
        source_address=0x03, topic=0x0C, data=b"\xa5\x5a", priority=enums.Priority.LOW
    )

    restored = frames.PsacpMessage._from_frame(original._to_frame())

    assert restored.source_address == original.source_address
    assert restored.topic == original.topic
    assert restored.data == original.data
    assert restored.priority == original.priority
    assert not restored.high_priority


def test_psacp_high_priority_uses_its_own_protocol_id():
    """The two PSACP priorities are separate protocol IDs, not a flag in the payload."""
    original = frames.PsacpMessage(source_address=0x03, topic=0x0C, data=b"\x01", high_priority=True)

    frame = original._to_frame()

    assert frame.protocol_id == enums._PROTOCOL_ID_PSACP_HIGH
    assert frames.PsacpMessage._from_frame(frame).high_priority


def test_block_write_reports_its_size():
    block = frames.BlockWrite(source_address=0x02, offset=64, data=b"\x00" * 128)

    assert len(block) == 128
    assert "0x02" in repr(block)
    assert "128 bytes" in repr(block)
