"""
Python bindings for the Artie CAN library.

The Artie CAN protocol is really four protocols sharing one bus, and this package exposes all of
them through a single :class:`Node`:

* **RTACP** - small, latency-sensitive messages to one node or to everyone, ACK'd and retried
  (:meth:`Node.rtacp_send`, :meth:`Node.receive_rtacp`).
* **PSACP** - fire-and-forget publish/subscribe on numbered topics
  (:meth:`Node.publish`, :meth:`Node.subscribe`, :meth:`Node.receive_psacp`).
* **BWACP** - bulk block writes of up to 64 KB into a receiver's buffer
  (:meth:`Node.block_write`, :attr:`Node.block_buffer`).
* **RPCACP** - remote procedure calls, including the standard WHOAMI, STATUS and LIST that every
  node answers (:meth:`Node.call`, :meth:`Node.register_procedure`, :meth:`Node.whoami`).

A minimal two-node exchange over the UDP multicast transport, which simulates a CAN bus on
localhost::

    from artie_can import Node, Protocol, UdpMulticastBackend

    bus = dict(group="239.0.0.1", port=5000)
    with Node(UdpMulticastBackend(**bus), address=0x01) as sender, \\
         Node(UdpMulticastBackend(**bus), address=0x02) as receiver:
        sender.rtacp_send(0x02, b"\\xde\\xad\\xbe\\xef")
        print(receiver.receive_rtacp(timeout=1.0).data.hex())

The node runs the library's event loop for you on its own thread, so methods here are ordinary
blocking calls; see :mod:`artie_can.node` for how that works.
"""
from .backends import Backend, Mcp2515Backend, UdpMulticastBackend
from .enums import (
    BROADCAST_ADDRESS,
    BROADCAST_TOPIC,
    BackendType,
    FIRST_DEVICE_PROCEDURE_ID,
    MAX_BLOCK_SIZE,
    MAX_FRAME_DATA_LENGTH,
    MAX_NODES,
    MAX_REGISTERED_PROCEDURES,
    MAX_RPC_NAME_LENGTH,
    MAX_RPC_PARAMS,
    MAX_SUBSCRIPTIONS,
    MULTICAST_ADDRESS,
    Mcp2515Mode,
    NodeClass,
    Priority,
    Protocol,
    RPC_LIST_PAGE_COUNT,
    RPC_LIST_PAGE_SIZE,
    RpcErrno,
    StandardProcedure,
)
from .errors import (
    ArtieCanError,
    Busy,
    CloseFailed,
    DriverError,
    ErrorFlag,
    InitFailed,
    InternalError,
    InvalidArgument,
    NoData,
    NodeClosed,
    NoResponse,
    NoSpace,
    ReceiveFailed,
    RemoteError,
    SendFailed,
    Timeout,
)
from .frames import Frame, PsacpMessage, RtacpMessage
from .node import (
    DEFAULT_BLOCK_TIMEOUT,
    DEFAULT_RPC_TIMEOUT,
    DEFAULT_RTACP_TIMEOUT,
    DEFAULT_TICK_INTERVAL,
    Node,
)
from .rpc import VOID, NodeStatus, ProcedureInfo, RpcParam, RpcSignature, WhoAmI

__version__ = "0.1.0"

__all__ = [
    # Node and transports
    "Node",
    "Backend",
    "UdpMulticastBackend",
    "Mcp2515Backend",
    # Messages
    "Frame",
    "RtacpMessage",
    "PsacpMessage",
    # RPC
    "RpcParam",
    "RpcSignature",
    "WhoAmI",
    "NodeStatus",
    "ProcedureInfo",
    "VOID",
    # Enumerations
    "BackendType",
    "Protocol",
    "Priority",
    "NodeClass",
    "Mcp2515Mode",
    "RpcErrno",
    "StandardProcedure",
    "ErrorFlag",
    # Constants
    "BROADCAST_ADDRESS",
    "MULTICAST_ADDRESS",
    "BROADCAST_TOPIC",
    "MAX_FRAME_DATA_LENGTH",
    "MAX_NODES",
    "MAX_BLOCK_SIZE",
    "MAX_SUBSCRIPTIONS",
    "MAX_RPC_PARAMS",
    "MAX_RPC_NAME_LENGTH",
    "MAX_REGISTERED_PROCEDURES",
    "RPC_LIST_PAGE_SIZE",
    "RPC_LIST_PAGE_COUNT",
    "FIRST_DEVICE_PROCEDURE_ID",
    "DEFAULT_TICK_INTERVAL",
    "DEFAULT_RTACP_TIMEOUT",
    "DEFAULT_BLOCK_TIMEOUT",
    "DEFAULT_RPC_TIMEOUT",
    # Exceptions
    "ArtieCanError",
    "InvalidArgument",
    "Timeout",
    "NoData",
    "SendFailed",
    "ReceiveFailed",
    "InitFailed",
    "CloseFailed",
    "NodeClosed",
    "Busy",
    "NoSpace",
    "InternalError",
    "DriverError",
    "NoResponse",
    "RemoteError",
    "__version__",
]
