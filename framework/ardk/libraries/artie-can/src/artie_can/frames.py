"""
Frame and message types.

:class:`Frame` is the raw 29-bit-ID CAN frame the bus actually carries. :class:`RtacpMessage` and
:class:`PsacpMessage` are the parsed, protocol-level views of one - the same split the C library
makes between ``artie_can_frame_t`` and ``artie_can_frame_rtacp_t`` / ``artie_can_frame_psacp_t``.

Conversion in both directions goes through the C library's own pack/parse functions rather than
re-implementing the bit layout here, so the Python side cannot disagree with the wire format.
"""
from __future__ import annotations

import dataclasses

from ._artie_can import ffi, lib
from . import enums, errors

__all__ = ["Frame", "RtacpMessage", "PsacpMessage"]

_PROTOCOL_SHIFT = lib.ARTIE_CAN_FRAME_ID_PROTOCOL_LOCATION
_PROTOCOL_MASK = lib.ARTIE_CAN_FRAME_ID_PROTOCOL_MASK
_SENDER_SHIFT = lib.ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_LOCATION
_SENDER_MASK = lib.ARTIE_CAN_FRAME_ID_SENDER_ADDRESS_MASK
_TARGET_SHIFT = lib.ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_LOCATION
_TARGET_MASK = lib.ARTIE_CAN_FRAME_ID_TARGET_ADDRESS_MASK


@dataclasses.dataclass(frozen=True, slots=True)
class Frame:
    """A raw Artie CAN frame: a 29-bit identifier and up to 8 data bytes."""

    id: int
    data: bytes = b""

    def __post_init__(self):
        if len(self.data) > enums.MAX_FRAME_DATA_LENGTH:
            raise ValueError(f"a CAN frame carries at most {enums.MAX_FRAME_DATA_LENGTH} data bytes, got {len(self.data)}")

    @property
    def protocol_id(self) -> int:
        """The 3-bit protocol selector in the top of the CAN ID."""
        return (self.id & _PROTOCOL_MASK) >> _PROTOCOL_SHIFT

    @property
    def source_address(self) -> int:
        """The address of the node that sent this frame."""
        return (self.id & _SENDER_MASK) >> _SENDER_SHIFT

    @property
    def target_address(self) -> int:
        """The address this frame is aimed at.

        Not meaningful for every protocol - PSACP uses those bits for the topic instead.
        """
        return (self.id & _TARGET_MASK) >> _TARGET_SHIFT

    def __repr__(self) -> str:
        return f"Frame(id=0x{self.id:08X}, data={self.data.hex(' ') or '<empty>'})"

    def _to_c(self):
        """Build the ``artie_can_frame_t`` for this frame. Caller must keep the result alive."""
        cframe = ffi.new("artie_can_frame_t *")
        cframe.id = self.id
        cframe.dlc = len(self.data)
        ffi.memmove(cframe.data, self.data, len(self.data))
        return cframe

    @classmethod
    def _from_c(cls, cframe) -> "Frame":
        # dlc comes off the wire, so clamp it rather than trusting it to index our buffer.
        length = min(cframe.dlc, enums.MAX_FRAME_DATA_LENGTH)
        return cls(id=cframe.id, data=bytes(ffi.buffer(cframe.data, length)))


@dataclasses.dataclass(frozen=True, slots=True)
class RtacpMessage:
    """A Real Time Artie CAN Protocol message - a small, latency-sensitive payload.

    Unicast messages are ACK'd and retried by the library; broadcasts are not.
    """

    source_address: int
    target_address: int
    data: bytes = b""
    priority: enums.Priority = enums.Priority.MEDIUM
    ack: bool = False

    @property
    def is_broadcast(self) -> bool:
        """True if this message went to every node rather than one."""
        return self.target_address == enums.BROADCAST_ADDRESS

    def _to_frame(self) -> Frame:
        crtacp = ffi.new("artie_can_frame_rtacp_t *")
        crtacp.ack = self.ack
        crtacp.priority = int(self.priority)
        crtacp.source_address = self.source_address
        crtacp.target_address = self.target_address
        crtacp.nbytes = len(self.data)
        ffi.memmove(crtacp.data, self.data, len(self.data))

        cframe = ffi.new("artie_can_frame_t *")
        errors.check(lib.artie_can_rtacp_init_frame(cframe, crtacp), "artie_can_rtacp_init_frame")
        return Frame._from_c(cframe)

    @classmethod
    def _from_frame(cls, frame: Frame) -> "RtacpMessage":
        crtacp = ffi.new("artie_can_frame_rtacp_t *")
        errors.check(lib.artie_can_rtacp_parse_frame(frame._to_c(), crtacp), "artie_can_rtacp_parse_frame")
        return cls(
            source_address=crtacp.source_address,
            target_address=crtacp.target_address,
            data=bytes(ffi.buffer(crtacp.data, min(crtacp.nbytes, enums.MAX_FRAME_DATA_LENGTH))),
            priority=enums.Priority(crtacp.priority),
            ack=bool(crtacp.ack),
        )


@dataclasses.dataclass(frozen=True, slots=True)
class PsacpMessage:
    """A Pub/Sub Artie CAN Protocol message - published to a topic, fire-and-forget.

    Topic 0 (:data:`~artie_can.BROADCAST_TOPIC`) reaches every subscriber.
    """

    source_address: int
    topic: int
    data: bytes = b""
    priority: enums.Priority = enums.Priority.MEDIUM
    high_priority: bool = False
    """Selects the high-priority PSACP protocol ID, which wins arbitration against the low one."""

    def _to_frame(self) -> Frame:
        cpsacp = ffi.new("artie_can_frame_psacp_t *")
        cpsacp.high_priority = self.high_priority
        cpsacp.priority = int(self.priority)
        cpsacp.source_address = self.source_address
        cpsacp.topic = self.topic
        cpsacp.nbytes = len(self.data)
        ffi.memmove(cpsacp.data, self.data, len(self.data))

        cframe = ffi.new("artie_can_frame_t *")
        errors.check(lib.artie_can_psacp_init_frame(cframe, cpsacp), "artie_can_psacp_init_frame")
        return Frame._from_c(cframe)

    @classmethod
    def _from_frame(cls, frame: Frame) -> "PsacpMessage":
        cpsacp = ffi.new("artie_can_frame_psacp_t *")
        errors.check(lib.artie_can_psacp_parse_frame(frame._to_c(), cpsacp), "artie_can_psacp_parse_frame")
        return cls(
            source_address=cpsacp.source_address,
            topic=cpsacp.topic,
            data=bytes(ffi.buffer(cpsacp.data, min(cpsacp.nbytes, enums.MAX_FRAME_DATA_LENGTH))),
            priority=enums.Priority(cpsacp.priority),
            high_priority=frame.protocol_id == enums._PROTOCOL_ID_PSACP_HIGH,
        )
