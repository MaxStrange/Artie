"""
Enumerations and protocol constants, taken from the C headers at build time.

Every value here is read out of the compiled extension rather than hard-coded, so these stay
correct if the C definitions move.
"""
from __future__ import annotations

import enum

from ._artie_can import lib

__all__ = [
    "BackendType",
    "Protocol",
    "Priority",
    "NodeClass",
    "Mcp2515Mode",
    "RpcErrno",
    "StandardProcedure",
    "BROADCAST_ADDRESS",
    "MULTICAST_ADDRESS",
    "BROADCAST_TOPIC",
    "MAX_FRAME_DATA_LENGTH",
    "MAX_NODES",
    "DEFAULT_BLOCK_BUFFER_SIZE",
    "MAX_SUBSCRIPTIONS",
    "MAX_PSACP_MESSAGE_SIZE",
    "PSACP_REASSEMBLY_SLOTS",
    "MAX_RPC_PARAMS",
    "MAX_RPC_NAME_LENGTH",
    "MAX_REGISTERED_PROCEDURES",
    "RPC_LIST_PAGE_SIZE",
    "RPC_LIST_PAGE_COUNT",
    "FIRST_DEVICE_PROCEDURE_ID",
]


class BackendType(enum.IntEnum):
    """Which transport a :class:`~artie_can.Node` puts its frames on."""

    MCP2515 = lib.ARTIE_CAN_BACKEND_MCP2515
    UDP_MULTICAST = lib.ARTIE_CAN_BACKEND_UDP_MCAST


class Protocol(enum.IntFlag):
    """The Artie CAN sub-protocols a node can take part in.

    A node opts into one or more of these; they share the bus and can all be active at once.
    """

    RTACP = lib.ARTIE_CAN_PROTOCOL_FLAG_RTACP
    RPCACP = lib.ARTIE_CAN_PROTOCOL_FLAG_RPCACP
    PSACP = lib.ARTIE_CAN_PROTOCOL_FLAG_PSACP
    BWACP = lib.ARTIE_CAN_PROTOCOL_FLAG_BWACP


class Priority(enum.IntEnum):
    """User-assigned priority within a protocol. Lower numbers win arbitration.

    The C headers give each protocol its own priority enum, but all four use the same two-bit
    field with the same ordering, so one enum covers them here. ``MED_HIGH``/``MED_LOW`` are
    aliases matching the PSACP and RPCACP spellings.
    """

    HIGHEST = lib.ARTIE_CAN_FRAME_PRIORITY_RTACP_HIGHEST
    HIGH = lib.ARTIE_CAN_FRAME_PRIORITY_RTACP_HIGH
    MEDIUM = lib.ARTIE_CAN_FRAME_PRIORITY_RTACP_MEDIUM
    LOW = lib.ARTIE_CAN_FRAME_PRIORITY_RTACP_LOW

    MED_HIGH = HIGH
    MED_LOW = MEDIUM


class NodeClass(enum.IntFlag):
    """What kind of device a node is, as a bitmask.

    BWACP block writes can be addressed to every node whose class overlaps a given mask, and
    RPCACP records the class as part of a node's identity.
    """

    SBC = lib.ARTIE_CAN_BWACP_CLASS_SBC
    MCU = lib.ARTIE_CAN_BWACP_CLASS_MCU
    SENSOR = lib.ARTIE_CAN_BWACP_CLASS_SENSOR
    MOTOR = lib.ARTIE_CAN_BWACP_CLASS_MOTOR


class Mcp2515Mode(enum.IntEnum):
    """Operating modes of the MCP2515 CAN controller."""

    NORMAL = lib.MCP2515_MODE_NORMAL
    SLEEP = lib.MCP2515_MODE_SLEEP
    LOOPBACK = lib.MCP2515_MODE_LOOPBACK
    LISTEN_ONLY = lib.MCP2515_MODE_LISTEN_ONLY
    CONFIGURATION = lib.MCP2515_MODE_CONFIGURATION


class RpcErrno(enum.IntEnum):
    """Errno-style reasons a node can NACK an RPC request."""

    TRANSMISSION = lib.ARTIE_CAN_RPCACP_ERRNO_TRANSMISSION
    EPERM = lib.ARTIE_CAN_RPCACP_ERRNO_EPERM
    E2BIG = lib.ARTIE_CAN_RPCACP_ERRNO_E2BIG
    ENOEXEC = lib.ARTIE_CAN_RPCACP_ERRNO_ENOEXEC
    EAGAIN = lib.ARTIE_CAN_RPCACP_ERRNO_EAGAIN
    EINVAL = lib.ARTIE_CAN_RPCACP_ERRNO_EINVAL
    EALREADY = lib.ARTIE_CAN_RPCACP_ERRNO_EALREADY


class StandardProcedure(enum.IntEnum):
    """RPC procedure IDs every compliant node answers internally."""

    WHOAMI = lib.ARTIE_CAN_RPC_ID_WHOAMI
    STATUS = lib.ARTIE_CAN_RPC_ID_STATUS
    LIST = lib.ARTIE_CAN_RPC_ID_LIST


#: RTACP target address that reaches every node on the bus.
BROADCAST_ADDRESS: int = lib.ARTIE_CAN_RTACP_TARGET_ADDRESS_BROADCAST

#: BWACP target address that turns a block write into a class-addressed multicast.
MULTICAST_ADDRESS: int = lib.ARTIE_CAN_BWACP_MULTICAST_ADDRESS

#: PSACP topic that reaches every subscriber regardless of what they subscribed to.
BROADCAST_TOPIC: int = lib.ARTIE_CAN_PSACP_TOPIC_BROADCAST

#: Data bytes that fit in a single CAN frame.
MAX_FRAME_DATA_LENGTH: int = lib.ARTIE_CAN_FRAME_MAX_DATA_LENGTH

#: Addressable nodes on one bus (the broadcast address is not one of them).
MAX_NODES: int = lib.ARTIE_CAN_MAX_NODES

#: Size of the BWACP receive buffer a :class:`~artie_can.Node` allocates by default. BWACP itself
#: sets no ceiling on how much a block write can carry - this is a starting allocation, not a limit.
DEFAULT_BLOCK_BUFFER_SIZE: int = lib.ARTIE_CAN_BWACP_DEFAULT_BUFFER_SIZE

#: PSACP topics a single node can be subscribed to at once.
MAX_SUBSCRIPTIONS: int = lib.ARTIE_CAN_PSACP_MAX_SUBSCRIPTIONS

#: Largest payload a single PSACP publish can carry. Anything over
#: :data:`MAX_FRAME_DATA_LENGTH` is fragmented across frames and reassembled by the receiver.
MAX_PSACP_MESSAGE_SIZE: int = lib.ARTIE_CAN_PSACP_MAX_MESSAGE_SIZE

#: Multi-frame PSACP messages a node can be reassembling at once, one per (publisher, topic) pair.
#: A message arriving when all of them are busy is dropped and counted.
PSACP_REASSEMBLY_SLOTS: int = lib.ARTIE_CAN_PSACP_REASSEMBLY_SLOTS

#: Parameters allowed in one RPC signature.
MAX_RPC_PARAMS: int = lib.ARTIE_CAN_RPCACP_MAX_PARAMS

#: Longest node name / firmware version / procedure name the protocol carries.
MAX_RPC_NAME_LENGTH: int = lib.ARTIE_CAN_RPCACP_MAX_NAME_LENGTH

#: Device-specific procedures a single node can register.
MAX_REGISTERED_PROCEDURES: int = lib.ARTIE_CAN_RPCACP_MAX_REGISTERED_PROCEDURES

#: Signatures returned by one page of the standard LIST procedure.
RPC_LIST_PAGE_SIZE: int = lib.ARTIE_CAN_RPCACP_LIST_PAGE_SIZE

#: Pages the standard LIST procedure can walk through.
RPC_LIST_PAGE_COUNT: int = lib.ARTIE_CAN_RPCACP_LIST_PAGE_COUNT

#: Lowest procedure ID available for device-specific procedures; below this is reserved.
FIRST_DEVICE_PROCEDURE_ID: int = lib.ARTIE_CAN_RPCACP_RESERVED_ID_MAX + 1

# Protocol IDs as they appear in the top bits of a frame's CAN ID. Used to route received frames
# to the right parser; not part of the public API.
_PROTOCOL_ID_RTACP: int = lib.ARTIE_CAN_RTACP_PROTOCOL_ID
_PROTOCOL_ID_RPCACP: int = lib.ARTIE_CAN_RPCACP_PROTOCOL_ID
_PROTOCOL_ID_PSACP_HIGH: int = lib.ARTIE_CAN_PSACP_HIGH_PROTOCOL_ID
_PROTOCOL_ID_PSACP_LOW: int = lib.ARTIE_CAN_PSACP_LOW_PROTOCOL_ID
_PROTOCOL_ID_BWACP: int = lib.ARTIE_CAN_BWACP_PROTOCOL_ID
