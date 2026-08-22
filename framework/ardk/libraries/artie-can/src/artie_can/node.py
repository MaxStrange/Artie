"""
:class:`Node` - one participant on an Artie CAN bus.

The C library is explicit that every
non-ISR entry point must be called from a single thread, the same one that drives
``artie_can_tick()``, and that ticking must happen constantly for anything to make progress. So a
node owns two threads:

* a *worker*, which is the only thread that ever calls into the library. It runs the tick loop
  and executes queued operations, polling each one's ``is_busy()`` until it finishes. Public
  methods hand it work and block on a :class:`~concurrent.futures.Future`, which is what makes
  them look synchronous from the outside.
* a *dispatcher*, which turns received frames into messages and hands them to your callbacks or
  queues. The library's own receive callback fires on its internal receiver thread (an interrupt
  handler on real hardware), so all it does here is copy the frame and hand it over - no user code
  runs in that context.

None of that leaks into the API: you construct a node, call methods on it, and close it.
"""
from __future__ import annotations

import concurrent.futures
import queue
import threading
import time
from typing import Any, Callable

from ._artie_can import ffi, lib
from .backends import Backend
from .enums import (
    BROADCAST_ADDRESS,
    MAX_BLOCK_SIZE,
    MAX_FRAME_DATA_LENGTH,
    MAX_NODES,
    MULTICAST_ADDRESS,
    NodeClass,
    Priority,
    Protocol,
    RPC_LIST_PAGE_SIZE,
    RpcErrno,
    StandardProcedure,
    _PROTOCOL_ID_PSACP_HIGH,
    _PROTOCOL_ID_PSACP_LOW,
    _PROTOCOL_ID_RTACP,
)
from .errors import (
    ArtieCanError,
    Busy,
    ErrorFlag,
    InvalidArgument,
    NodeClosed,
    RemoteError,
    Timeout,
    check,
    to_exception,
)
from .frames import Frame, PsacpMessage, RtacpMessage
from .rpc import NodeStatus, ProcedureInfo, RpcParam, RpcSignature, WhoAmI, _SignatureBinding

__all__ = ["Node"]

#: Longest the worker will go without ticking while the node is idle.
#:
#: An arriving RTACP or PSACP frame wakes the worker immediately, but those are the only two
#: protocols whose receive path invokes the library's rx callback - RPCACP and BWACP frames are
#: consumed entirely inside the library, and the state machines that own them make progress only
#: when ticked. So this interval, not the wake-up, is what paces an inbound RPC exchange or block
#: write, and it has to stay small enough to keep their per-frame ACK budgets comfortable.
DEFAULT_TICK_INTERVAL = 0.001

#: How long the worker pauses between ticks while an operation is in flight. Some outcomes -
#: an RTACP ACK above all - are only visible by ticking and are not announced by a callback, and
#: RTACP's ACK budget is 10 ms end to end, so an operation that is being actively waited on polls
#: far harder than an idle node does.
DEFAULT_ACTIVE_TICK_INTERVAL = 0.0002

#: Wall-clock ceiling on an RTACP send. The library gives up on an unacknowledged frame far
#: sooner than this; it is a backstop against a wedged bus, not the protocol's own timeout.
DEFAULT_RTACP_TIMEOUT = 5.0

#: Wall-clock ceiling on a BWACP block write, which can be 64 KB moved 8 bytes at a time.
DEFAULT_BLOCK_TIMEOUT = 120.0

#: Wall-clock ceiling on an RPC call, including the remote's execution time.
DEFAULT_RPC_TIMEOUT = 30.0

#: Received frames held per protocol before the oldest are dropped.
DEFAULT_RECEIVE_QUEUE_SIZE = 1024

#: How long to back off before retrying an operation the far end turned away as busy. The node
#: keeps ticking through the pause, which is what lets the far end finish and become ready.
DEFAULT_RETRY_DELAY = 0.005

_SHUTDOWN = object()

# The standard procedures every node answers internally. These are module-level singletons rather
# than built per call so that a node's cache of bound C signatures stays bounded.
_WHOAMI = RpcSignature(int(StandardProcedure.WHOAMI), "WHOAMI")
_STATUS = RpcSignature(int(StandardProcedure.STATUS), "STATUS")
_LIST = RpcSignature(int(StandardProcedure.LIST), "LIST", params=(RpcParam("uint8_t"),))


def _offer(destination: queue.Queue, item: Any) -> None:
    """Put an item on a bounded queue, discarding the oldest entries to make room.

    Frames arrive whether or not anyone is reading them, and stale ones are worth less than fresh
    ones, so a full queue drops from the front rather than blocking the receive path.
    """
    while True:
        try:
            destination.put_nowait(item)
            return
        except queue.Full:
            try:
                destination.get_nowait()
            except queue.Empty:
                pass


class _Operation:
    """One library call, started on the worker thread and driven to completion by later ticks.

    Most of the library's interesting entry points only *begin* something: ``artie_can_rtacp_send``
    hands a frame to the RTACP state machine and returns, and the ACK it is waiting for only
    arrives across subsequent ticks. This models that as start / poll-until-not-busy / collect.
    """

    __slots__ = ("description", "future", "attempts", "_start", "_busy", "_collect", "_timeout",
                 "_check_tick_errors", "_keepalive", "_deadline", "_tick_error", "_retry_if",
                 "_retry_delay", "_retry_at", "_last_error")

    def __init__(self, description, start, *, busy=None, collect=None, timeout=None,
                 check_tick_errors=True, keepalive=None, retry_if=None,
                 retry_delay=DEFAULT_RETRY_DELAY):
        self.description = description
        self.future: concurrent.futures.Future = concurrent.futures.Future()
        self.attempts = 0
        self._start = start
        self._busy = busy
        self._collect = collect
        self._timeout = timeout
        self._check_tick_errors = check_tick_errors
        # Anything the library will keep dereferencing until this operation finishes.
        self._keepalive = keepalive
        # Given the exception an attempt failed with, says whether starting over is worthwhile.
        self._retry_if = retry_if
        self._retry_delay = retry_delay
        self._retry_at = None
        self._deadline = None
        self._tick_error = ErrorFlag.NONE
        self._last_error = None

    @property
    def timeout(self) -> float | None:
        return self._timeout

    def begin(self) -> bool:
        """Start the operation. Returns True if it still needs ticks to finish."""
        if not self.future.set_running_or_notify_cancel():
            return False
        self._deadline = time.monotonic() + self._timeout if self._timeout else None
        return self._attempt()

    def advance(self, tick_error: ErrorFlag) -> bool:
        """Fold in one tick's result. Returns True if the operation is still pending."""
        # Only the latest tick's errors are kept, not the union of every tick this operation
        # lived through. A protocol state machine reports a terminal failure on the same tick
        # that it gives up and goes idle - RTACP's ACK timeout does exactly that - so the tick
        # that ends the operation is the one that explains it. Errors from earlier ticks were
        # recovered from, and holding on to them would fail transfers that in fact succeeded.
        self._tick_error = tick_error
        try:
            if self._retry_at is not None:
                if time.monotonic() < self._retry_at:
                    # Still backing off. Ticking continues meanwhile, which is what lets the
                    # remote finish whatever made it turn us away.
                    return self._still_within_deadline()
                self._retry_at = None
                return self._attempt()
            if not self._busy():
                return self._finish()
            return self._still_within_deadline()
        except BaseException as exc:  # noqa: BLE001 - relayed to the caller through the future
            self.future.set_exception(exc)
            return False

    def abandon(self, exc: BaseException) -> None:
        """Fail this operation because the node is going away."""
        if not self.future.done():
            self.future.set_running_or_notify_cancel()
            self.future.set_exception(exc)

    def _attempt(self) -> bool:
        """Run the starting call once. True if the operation now needs ticks."""
        self.attempts += 1
        try:
            self._start()
            if self._busy is None or not self._busy():
                return self._finish()
        except BaseException as exc:  # noqa: BLE001
            # The starting call can be turned away for the same reason a whole exchange can - this
            # node's own state machine is mid-exchange, because it is answering someone else - and
            # a rejected start put nothing on the bus, so it retries on the same terms.
            return self._schedule_retry_or_fail(exc)
        return True

    def _finish(self) -> bool:
        """Resolve the operation, or schedule another attempt. True if still pending."""
        # An error on the finishing tick belongs to this operation: it was the only thing in
        # flight, and a tick is how the state machines report outcomes that the starting call
        # could not know yet - an RTACP ACK timeout never comes back from the send itself.
        if self._check_tick_errors:
            error = to_exception(self._tick_error, self.description)
            if error is not None:
                self.future.set_exception(error)
                return False
        try:
            result = self._collect() if self._collect is not None else None
        except BaseException as exc:  # noqa: BLE001
            return self._schedule_retry_or_fail(exc)
        self.future.set_result(result)
        return False

    def _schedule_retry_or_fail(self, exc: BaseException) -> bool:
        """Back off and try again if this failure is one worth repeating. True if still pending."""
        self._last_error = exc
        if self._retry_if is not None and self._retry_if(exc) and self._time_left():
            self._retry_at = time.monotonic() + self._retry_delay
            return True
        self.future.set_exception(exc)
        return False

    def _time_left(self) -> bool:
        return self._deadline is None or time.monotonic() < self._deadline

    def _still_within_deadline(self) -> bool:
        if self._time_left():
            return True
        # Prefer the reason the last attempt actually failed over a bare "timed out", which says
        # nothing about why a retried operation never got anywhere.
        self.future.set_exception(
            self._last_error
            or Timeout(f"did not finish within {self._timeout:g}s", self._tick_error, self.description)
        )
        return False


class Node:
    """One node on an Artie CAN bus.

    A node owns a transport, whichever protocols you enable, and the threads that keep them
    running. Use it as a context manager, or call :meth:`open` and :meth:`close` yourself::

        with Node(UdpMulticastBackend("239.0.0.1", 5000), address=0x01) as node:
            node.rtacp_send(0x02, b"\\xde\\xad\\xbe\\xef")

    :param backend: The transport to run on. A backend belongs to exactly one node.
    :param address: This node's address on the bus, 1 to 62. Address 0 is the broadcast address
        and 63 is BWACP's multicast address, so neither can belong to a node.
    :param protocols: Which sub-protocols to take part in. Only the enabled ones can be used; the
        matching methods raise :class:`~artie_can.InvalidArgument` otherwise.
    :param node_class: What kind of device this is. BWACP multicasts are addressed by class, and
        RPCACP reports it as part of this node's identity.
    :param name: Human-readable name reported by the standard WHOAMI procedure.
    :param firmware_version: Firmware version reported by the standard WHOAMI procedure.
    :param block_buffer_size: Size of the buffer incoming BWACP block writes land in. Senders
        choose the offset they write at, so this needs to cover the largest offset you expect.
    :param on_rtacp: ``on_rtacp(message)``, called for each received :class:`RtacpMessage`. If
        given, RTACP messages go here instead of to :meth:`receive_rtacp`.
    :param on_psacp: ``on_psacp(message)``, called for each received :class:`PsacpMessage`. If
        given, PSACP messages go here instead of to :meth:`receive_psacp`.
    :param on_frame: ``on_frame(frame)``, called for each received frame that is neither RTACP nor
        PSACP. If given, those frames go here instead of to :meth:`receive_frame`.
    :param tick_interval: Longest the worker goes without ticking while idle. This is what paces
        inbound RPCACP exchanges and BWACP transfers, so raising it slows those down.
    :param active_tick_interval: Seconds between ticks while an operation is in flight. Lower
        means lower latency and more CPU; RTACP's 10 ms ACK budget is what sets the default.
    :param receive_queue_size: How many messages to hold per protocol before dropping the oldest.
    :param auto_open: Whether to join the bus immediately. Set False to construct now and
        :meth:`open` later.

    Callbacks run on the node's dispatcher thread, one at a time and in arrival order. They must
    not call back into the same node, which would deadlock.
    """

    def __init__(
        self,
        backend: Backend,
        *,
        address: int,
        protocols: Protocol = Protocol.RTACP,
        node_class: NodeClass = NodeClass.SBC,
        name: str | None = None,
        firmware_version: str = "0.0.0",
        block_buffer_size: int = MAX_BLOCK_SIZE,
        on_rtacp: Callable[[RtacpMessage], None] | None = None,
        on_psacp: Callable[[PsacpMessage], None] | None = None,
        on_frame: Callable[[Frame], None] | None = None,
        tick_interval: float = DEFAULT_TICK_INTERVAL,
        active_tick_interval: float = DEFAULT_ACTIVE_TICK_INTERVAL,
        receive_queue_size: int = DEFAULT_RECEIVE_QUEUE_SIZE,
        auto_open: bool = True,
    ):
        if not 1 <= address <= MAX_NODES:
            raise InvalidArgument(
                f"node address must be between 1 and {MAX_NODES}; 0 is the broadcast address and "
                f"{MULTICAST_ADDRESS} is BWACP's multicast address"
            )
        if not protocols:
            raise InvalidArgument("a node must take part in at least one protocol")
        if not 0 < block_buffer_size <= MAX_BLOCK_SIZE:
            raise InvalidArgument(f"block_buffer_size must be between 1 and {MAX_BLOCK_SIZE}")

        self._backend = backend
        self._address = address
        self._protocols = Protocol(protocols)
        self._node_class = NodeClass(node_class)
        self._name = name if name is not None else f"artie-node-{address:#04x}"
        self._firmware_version = firmware_version
        self._block_buffer_size = block_buffer_size
        self._tick_interval = tick_interval
        self._active_tick_interval = min(active_tick_interval, tick_interval)

        self._on_rtacp = on_rtacp
        self._on_psacp = on_psacp
        self._on_frame = on_frame

        # Owned cdata. Every one of these must outlive the library's use of it.
        self._context = None
        self._handle = None
        self._block_buffer = None
        self._rx_callback = None
        self._busy_checks: tuple = ()
        self._signatures: dict[int, _SignatureBinding] = {}

        self._pending: queue.Queue[_Operation] = queue.Queue()
        self._current: _Operation | None = None
        self._worker: threading.Thread | None = None
        self._dispatcher: threading.Thread | None = None
        self._running = False
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._last_background_error = ErrorFlag.NONE

        self._inbox: queue.Queue = queue.Queue(receive_queue_size)
        self._rtacp_inbox: queue.Queue[RtacpMessage] = queue.Queue(receive_queue_size)
        self._psacp_inbox: queue.Queue[PsacpMessage] = queue.Queue(receive_queue_size)
        self._frame_inbox: queue.Queue[Frame] = queue.Queue(receive_queue_size)

        if auto_open:
            self.open()

    # ------------------------------------------------------------------ properties

    @property
    def address(self) -> int:
        """This node's address on the bus."""
        return self._address

    @property
    def name(self) -> str:
        """The name this node reports through WHOAMI."""
        return self._name

    @property
    def node_class(self) -> NodeClass:
        """The class bitmask this node reports and is addressed by."""
        return self._node_class

    @property
    def protocols(self) -> Protocol:
        """The protocols this node takes part in."""
        return self._protocols

    @property
    def backend(self) -> Backend:
        """The transport this node runs on."""
        return self._backend

    @property
    def is_open(self) -> bool:
        """True between a successful :meth:`open` and :meth:`close`."""
        return self._running

    @property
    def last_background_error(self) -> ErrorFlag:
        """Errors reported by ticks that had no operation to attribute them to.

        A node that is only receiving still ticks, and a protocol state machine can report a
        problem there - a failed ACK send, say. Those have nowhere to be raised, so they land here.
        """
        return self._last_background_error

    @property
    def block_buffer(self) -> memoryview:
        """The buffer incoming BWACP block writes are written into.

        Senders choose the offset within it. The view stays valid for the life of the node and is
        written by the worker thread, so read it when you know a transfer has finished.
        """
        self._require(Protocol.BWACP, "block_buffer")
        return memoryview(ffi.buffer(self._block_buffer, self._block_buffer_size))

    @property
    def block_bytes_received(self) -> int:
        """Bytes written into :attr:`block_buffer` by the block write currently in progress."""
        self._require(Protocol.BWACP, "block_bytes_received")
        return self._context.bwacp_context.receive_bytes_written

    # ------------------------------------------------------------------ lifecycle

    def open(self) -> "Node":
        """Bring the node up: configure the library, join the bus, and start the threads."""
        with self._lock:
            if self._running:
                return self
            self._build_context()
            self._running = True
            self._worker = threading.Thread(
                target=self._worker_loop, name=f"artie-can-worker-{self._address:#04x}", daemon=True
            )
            self._dispatcher = threading.Thread(
                target=self._dispatch_loop, name=f"artie-can-rx-{self._address:#04x}", daemon=True
            )
            self._worker.start()
            self._dispatcher.start()
        return self

    def close(self) -> None:
        """Shut the node down and leave the bus. Safe to call more than once.

        Pending operations fail with :class:`~artie_can.NodeClosed`. The library's own close runs
        on the worker thread as its last act, so it happens on the same thread as every other
        library call, as the library requires.
        """
        with self._lock:
            if not self._running:
                return
            self._running = False
            worker, dispatcher = self._worker, self._dispatcher
            self._worker = self._dispatcher = None
            self._wake.set()

        if worker is not None:
            worker.join()
        _offer(self._inbox, _SHUTDOWN)
        if dispatcher is not None:
            dispatcher.join()

    def __enter__(self) -> "Node":
        return self.open()

    def __exit__(self, *_exc_info) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "open" if self._running else "closed"
        return (
            f"Node(address={self._address:#04x}, protocols={self._protocols!r}, "
            f"backend={self._backend!r}, {state})"
        )

    # ------------------------------------------------------------------ RTACP

    def rtacp_send(
        self,
        target_address: int,
        data: bytes = b"",
        *,
        priority: Priority = Priority.MEDIUM,
        timeout: float = DEFAULT_RTACP_TIMEOUT,
        wait: bool = True,
    ):
        """Send a small real-time message to one node, or to every node.

        Unicast sends are acknowledged: this does not return until the target ACKs. Broadcasts
        (``target_address=``:data:`~artie_can.BROADCAST_ADDRESS`) are not acknowledged and return
        as soon as the frame is on the bus.

        A :class:`~artie_can.Timeout` here means the ACK did not arrive inside RTACP's budget,
        which is 10 ms end to end - **not** that the message failed to arrive. The frame is
        usually delivered and it is the ACK that came back late, so treat this as "delivery
        unconfirmed" rather than "delivery failed", and only retry if the receiver can tolerate a
        duplicate. Driving the protocol from a scheduled userspace thread makes that budget tight;
        expect a small fraction of unicast sends to report it under load.

        :param target_address: The node to send to, or :data:`~artie_can.BROADCAST_ADDRESS`.
        :param data: Up to 8 bytes of payload.
        :param priority: Bus arbitration priority for this frame.
        :param timeout: Wall-clock ceiling, in seconds.
        :param wait: Set False to get a :class:`~concurrent.futures.Future` instead of blocking.
        """
        self._require(Protocol.RTACP, "rtacp_send")
        if len(data) > MAX_FRAME_DATA_LENGTH:
            raise InvalidArgument(
                f"an RTACP message carries at most {MAX_FRAME_DATA_LENGTH} bytes, got {len(data)}"
            )
        message = RtacpMessage(
            source_address=self._address,
            target_address=target_address,
            data=bytes(data),
            priority=Priority(priority),
        )
        cframe = message._to_frame()._to_c()
        handle = self._handle

        operation = _Operation(
            "artie_can_rtacp_send",
            lambda: check(lib.artie_can_rtacp_send(handle, cframe), "artie_can_rtacp_send"),
            busy=lambda: lib.artie_can_rtacp_is_busy(handle),
            timeout=timeout,
            keepalive=cframe,
        )
        return self._submit(operation, wait)

    def receive_rtacp(self, timeout: float | None = None) -> RtacpMessage:
        """Wait for the next RTACP message addressed to this node.

        Only available when no ``on_rtacp`` callback was given; the two are alternatives.

        :param timeout: Seconds to wait, or None to wait indefinitely.
        :raises Timeout: If nothing arrives in time.
        """
        self._require(Protocol.RTACP, "receive_rtacp")
        return self._receive(self._rtacp_inbox, timeout, "RTACP message", self._on_rtacp, "on_rtacp")

    # ------------------------------------------------------------------ PSACP

    def subscribe(self, topic: int, *, wait: bool = True):
        """Subscribe this node to a PSACP topic, so publishes to it are delivered here."""
        self._require(Protocol.PSACP, "subscribe")
        context = self._context
        return self._submit(
            _Operation(
                "artie_can_psacp_subscribe",
                lambda: check(lib.artie_can_psacp_subscribe(context, topic), "artie_can_psacp_subscribe"),
            ),
            wait,
        )

    def unsubscribe(self, topic: int, *, wait: bool = True):
        """Stop delivering publishes on a PSACP topic to this node."""
        self._require(Protocol.PSACP, "unsubscribe")
        context = self._context
        return self._submit(
            _Operation(
                "artie_can_psacp_unsubscribe",
                lambda: check(
                    lib.artie_can_psacp_unsubscribe(context, topic), "artie_can_psacp_unsubscribe"
                ),
            ),
            wait,
        )

    def publish(
        self,
        topic: int,
        data: bytes = b"",
        *,
        priority: Priority = Priority.MEDIUM,
        high_priority: bool = False,
        wait: bool = True,
    ):
        """Publish a message to a PSACP topic.

        Fire and forget: every subscriber to the topic receives it, nobody acknowledges it, and
        nothing is retried. Use :meth:`rtacp_send` or :meth:`block_write` if delivery has to be
        guaranteed. Publishing to :data:`~artie_can.BROADCAST_TOPIC` reaches every subscriber
        whatever they subscribed to, and this node receives its own publish if it is subscribed.

        :param topic: The topic to publish on.
        :param data: Up to 8 bytes of payload.
        :param priority: Bus arbitration priority within the chosen PSACP protocol.
        :param high_priority: Use the high-priority PSACP protocol ID, which beats the low-priority
            one during arbitration regardless of ``priority``.
        :param wait: Set False to get a :class:`~concurrent.futures.Future` instead of blocking.
        """
        self._require(Protocol.PSACP, "publish")
        if len(data) > MAX_FRAME_DATA_LENGTH:
            raise InvalidArgument(
                f"a PSACP message carries at most {MAX_FRAME_DATA_LENGTH} bytes, got {len(data)}"
            )
        message = PsacpMessage(
            source_address=self._address,
            topic=topic,
            data=bytes(data),
            priority=Priority(priority),
            high_priority=high_priority,
        )
        cframe = message._to_frame()._to_c()
        handle = self._handle

        return self._submit(
            _Operation(
                "artie_can_psacp_publish",
                lambda: check(lib.artie_can_psacp_publish(handle, cframe), "artie_can_psacp_publish"),
                keepalive=cframe,
            ),
            wait,
        )

    def receive_psacp(self, timeout: float | None = None) -> PsacpMessage:
        """Wait for the next PSACP message on a topic this node subscribes to.

        Only available when no ``on_psacp`` callback was given; the two are alternatives.

        :param timeout: Seconds to wait, or None to wait indefinitely.
        :raises Timeout: If nothing arrives in time.
        """
        self._require(Protocol.PSACP, "receive_psacp")
        return self._receive(self._psacp_inbox, timeout, "PSACP message", self._on_psacp, "on_psacp")

    # ------------------------------------------------------------------ BWACP

    def block_write(
        self,
        data: bytes,
        *,
        offset: int = 0,
        target_address: int = MULTICAST_ADDRESS,
        target_class: NodeClass = NodeClass.SBC,
        priority: Priority = Priority.MEDIUM,
        timeout: float = DEFAULT_BLOCK_TIMEOUT,
        wait: bool = True,
    ):
        """Write a block of data into one or more remote nodes' block buffers.

        This is the bulk transfer protocol: up to 64 KB, chunked across frames, CRC-checked, and
        retried per frame. It does not return until every participating receiver has acknowledged
        the whole transfer.

        Receivers must have BWACP enabled - their :attr:`block_buffer` is where the data lands,
        starting at ``offset``.

        :param data: The payload, up to :data:`~artie_can.MAX_BLOCK_SIZE` bytes.
        :param offset: Where in each receiver's block buffer to write.
        :param target_address: A single node's address, or :data:`~artie_can.MULTICAST_ADDRESS` to
            address every node whose class overlaps ``target_class``.
        :param target_class: Which classes of node to write to. Ignored unless ``target_address``
            is the multicast address.
        :param priority: Bus arbitration priority for the transfer's frames.
        :param timeout: Wall-clock ceiling, in seconds.
        :param wait: Set False to get a :class:`~concurrent.futures.Future` instead of blocking.
        """
        self._require(Protocol.BWACP, "block_write")
        payload = bytes(data)
        if not 0 < len(payload) <= MAX_BLOCK_SIZE:
            raise InvalidArgument(
                f"a block write carries between 1 and {MAX_BLOCK_SIZE} bytes, got {len(payload)}"
            )
        # The library reads the payload straight out of this buffer across the whole transfer, so
        # it has to stay alive until the operation completes.
        buffer = ffi.new("uint8_t[]", payload)
        handle = self._handle

        operation = _Operation(
            "artie_can_bwacp_send",
            lambda: check(
                lib.artie_can_bwacp_send(
                    handle, buffer, len(payload), offset, target_address,
                    int(target_class), int(Priority(priority)),
                ),
                "artie_can_bwacp_send",
            ),
            busy=lambda: lib.artie_can_bwacp_is_busy(handle),
            timeout=timeout,
            keepalive=buffer,
        )
        return self._submit(operation, wait)

    # ------------------------------------------------------------------ RPCACP

    def register_procedure(self, signature: RpcSignature, *, wait: bool = True):
        """Make a procedure callable on this node by other nodes.

        The signature's ``function`` runs on this node's worker thread when a request arrives, so
        it must not call back into this node. Procedure IDs 0x00-0x0F are reserved for the
        standard procedures the library answers itself.

        :param signature: The procedure to register. Its ``function`` must not be None.
        :param wait: Set False to get a :class:`~concurrent.futures.Future` instead of blocking.
        """
        self._require(Protocol.RPCACP, "register_procedure")
        if signature.function is None:
            raise InvalidArgument(
                f"cannot register {signature.name!r} without a function to run when it is called"
            )
        binding = self._bind(signature)
        handle = self._handle
        return self._submit(
            _Operation(
                "artie_can_rpcacp_register_procedure",
                lambda: check(
                    lib.artie_can_rpcacp_register_procedure(handle, binding.c_signature),
                    "artie_can_rpcacp_register_procedure",
                ),
            ),
            wait,
        )

    def call(
        self,
        target_address: int,
        signature: RpcSignature,
        *args: Any,
        timeout: float = DEFAULT_RPC_TIMEOUT,
        retry_if_busy: bool = True,
        wait: bool = True,
    ):
        """Call a procedure on a remote node.

        For a synchronous signature this returns the decoded return value (or None if the
        signature declares no return). For an asynchronous one it returns once the remote has
        accepted the request; the remote goes on running it, and
        :meth:`is_remote_busy` tracks that.

        :param target_address: The node to call. There is no broadcast in RPCACP.
        :param signature: The procedure's signature, which both nodes must agree on.
        :param args: One argument per parameter in the signature. Trailing optional parameters may
            be left off.
        :param timeout: Wall-clock ceiling, in seconds, covering the remote's execution time too.
        :param retry_if_busy: Whether to keep re-sending, until ``timeout``, while the remote node
            answers that it is busy. A node stays busy briefly after finishing an exchange, so
            back-to-back calls hit this routinely. Only that one rejection is retried, and it
            means the procedure definitely did not run, so this cannot double-execute anything.
            Set False to have such a rejection raise :class:`~artie_can.RemoteError` instead.
        :param wait: Set False to get a :class:`~concurrent.futures.Future` instead of blocking.
        :raises RemoteError: If the remote node rejects the request.
        """
        return self._call(target_address, signature, args, timeout, wait, None, retry_if_busy)

    def whoami(
        self, target_address: int, *, timeout: float = DEFAULT_RPC_TIMEOUT,
        retry_if_busy: bool = True,
    ) -> WhoAmI:
        """Ask a remote node to identify itself. Answered internally by every node."""
        return self._call(
            target_address, _WHOAMI, (), timeout, True, self._decode_whoami, retry_if_busy
        )

    def node_status(
        self, target_address: int, *, timeout: float = DEFAULT_RPC_TIMEOUT,
        retry_if_busy: bool = True,
    ) -> NodeStatus:
        """Ask a remote node for its uptime and error flags. Answered internally by every node."""
        return self._call(
            target_address, _STATUS, (), timeout, True, self._decode_status, retry_if_busy
        )

    def list_procedures(
        self, target_address: int, page: int = 0, *, timeout: float = DEFAULT_RPC_TIMEOUT,
        retry_if_busy: bool = True,
    ) -> list[ProcedureInfo]:
        """Ask a remote node which procedures it exposes.

        Results come a page at a time; each page describes
        :data:`~artie_can.RPC_LIST_PAGE_SIZE` consecutive procedure IDs starting at
        ``page * RPC_LIST_PAGE_SIZE``. Entries for IDs the node has not registered come back with
        :attr:`~artie_can.ProcedureInfo.registered` False.
        """
        return self._call(
            target_address, _LIST, (page,), timeout, True, self._decode_list, retry_if_busy
        )

    def _call(self, target_address, signature, args, timeout, wait, decode, retry_if_busy=True):
        """Shared body of every RPC call.

        Starting the call and reading its result have to be one operation, not two: the library
        keeps a single result slot per node, so anything else reaching the worker in between -
        another thread's call, or a request this node is answering - would overwrite it.
        """
        self._require(Protocol.RPCACP, "call")
        if target_address == BROADCAST_ADDRESS:
            raise InvalidArgument("RPCACP has no broadcast; call one node at a time")

        binding = self._bind(signature)
        encoded = signature.encode_args(args)
        buffers = [ffi.new("char[]", raw) if raw else ffi.NULL for raw in encoded]
        values = ffi.new("artie_can_rpc_value_t[]", max(len(encoded), 1))
        for index, (buffer, raw) in enumerate(zip(buffers, encoded)):
            values[index].data = buffer
            values[index].size = len(raw)

        handle = self._handle

        def start():
            check(
                lib.artie_can_rpcacp_call(
                    handle, target_address, binding.c_signature,
                    values if encoded else ffi.NULL, len(encoded),
                ),
                "artie_can_rpcacp_call",
            )

        def collect():
            self._raise_rpc_error(signature)
            if decode is not None:
                return decode()
            return self._decode_result(signature, binding)

        operation = _Operation(
            "artie_can_rpcacp_call",
            start,
            busy=lambda: lib.artie_can_rpcacp_is_busy(handle),
            collect=collect,
            timeout=timeout,
            # The outcome comes from artie_can_rpcacp_get_last_error(), which says more than the
            # tick mask can - a NACK carries an errno byte that has no bit in ErrorFlag.
            check_tick_errors=False,
            keepalive=(values, buffers),
            retry_if=_rejected_as_busy if retry_if_busy else None,
        )
        return self._submit(operation, wait)

    def is_remote_busy(self, node_address: int) -> bool:
        """Whether a remote node is believed to still be running an async RPC we started.

        Best effort and locally tracked: set when that node accepts an asynchronous call from
        here, cleared the next time it accepts or definitively rejects another one.
        """
        self._require(Protocol.RPCACP, "is_remote_busy")
        handle = self._handle
        return self._submit(
            _Operation(
                "artie_can_rpcacp_is_node_busy",
                lambda: None,
                collect=lambda: bool(lib.artie_can_rpcacp_is_node_busy(handle, node_address)),
            ),
            True,
        )

    def set_status_error_flags(self, flags: int, *, wait: bool = True):
        """Set the device-specific error bits this node reports through the STATUS procedure."""
        self._require(Protocol.RPCACP, "set_status_error_flags")
        context = self._context
        return self._submit(
            _Operation(
                "artie_can_rpcacp_set_status_err_flags",
                lambda: check(
                    lib.artie_can_rpcacp_set_status_err_flags(context, flags),
                    "artie_can_rpcacp_set_status_err_flags",
                ),
            ),
            wait,
        )

    # ------------------------------------------------------------------ raw frames

    def receive_frame(self, timeout: float | None = None) -> Frame:
        """Wait for the next received frame that is neither RTACP nor PSACP.

        Frames the higher-level protocols handle themselves do not appear here. Only available
        when no ``on_frame`` callback was given.
        """
        return self._receive(self._frame_inbox, timeout, "frame", self._on_frame, "on_frame")

    # ------------------------------------------------------------------ setup

    def _build_context(self) -> None:
        """Allocate and configure everything the library needs, in the order it needs it.

        The backend goes first (it only sets ``backend_context``), then each protocol, which is
        what sets the protocol flags ``artie_can_init()`` insists on seeing.
        """
        self._context = ffi.new("artie_can_context_t *")
        self._handle = ffi.new("artie_can_backend_t *")

        # Consulted every tick to decide how hard to poll, so it is resolved once here rather than
        # rebuilt each time round the loop.
        self._busy_checks = (
            (Protocol.RTACP, lib.artie_can_rtacp_is_busy),
            (Protocol.RPCACP, lib.artie_can_rpcacp_is_busy),
            (Protocol.BWACP, lib.artie_can_bwacp_is_busy),
        )

        self._backend._configure(self._context)

        if Protocol.RTACP in self._protocols:
            check(
                lib.artie_can_init_context_rtacp(self._context, self._address),
                "artie_can_init_context_rtacp",
            )
        if Protocol.PSACP in self._protocols:
            check(
                lib.artie_can_init_context_psacp(self._context, self._address),
                "artie_can_init_context_psacp",
            )
        if Protocol.BWACP in self._protocols:
            check(
                lib.artie_can_init_context_bwacp(self._context, self._address, int(self._node_class)),
                "artie_can_init_context_bwacp",
            )
            self._block_buffer = ffi.new("uint8_t[]", self._block_buffer_size)
            check(
                lib.artie_can_bwacp_set_receive_buffer(
                    self._context, self._block_buffer, self._block_buffer_size
                ),
                "artie_can_bwacp_set_receive_buffer",
            )
        if Protocol.RPCACP in self._protocols:
            check(
                lib.artie_can_init_context_rpcacp(
                    self._context,
                    self._address,
                    int(self._node_class),
                    self._name.encode("utf-8"),
                    self._firmware_version.encode("utf-8"),
                ),
                "artie_can_init_context_rpcacp",
            )

        self._rx_callback = ffi.callback("artie_can_rx_callback_t", self._on_frame_received)
        check(
            lib.artie_can_init(
                self._context,
                self._handle,
                int(self._backend.backend_type),
                self._rx_callback,
                ffi.addressof(lib, "artie_can_py_monotonic_ms"),
            ),
            "artie_can_init",
        )

    def _require(self, protocol: Protocol, what: str) -> None:
        """Reject a call the node was not configured for, or is no longer able to serve."""
        if protocol not in self._protocols:
            raise InvalidArgument(
                f"{what} needs Protocol.{protocol.name}, but this node was configured with "
                f"{self._protocols!r}"
            )
        if not self._running:
            raise NodeClosed("node is not open", operation=what)

    def _bind(self, signature: RpcSignature) -> _SignatureBinding:
        """Get (or build) the long-lived C signature for an :class:`RpcSignature`.

        The library keeps the ``char *`` fields of a registered or in-flight signature, so these
        are cached for the life of the node rather than rebuilt per call.
        """
        key = id(signature)
        binding = self._signatures.get(key)
        if binding is None or binding.signature != signature:
            binding = _SignatureBinding(signature)
            self._signatures[key] = binding
        return binding

    # ------------------------------------------------------------------ worker thread

    def _submit(self, operation: _Operation, wait: bool):
        """Hand an operation to the worker thread, optionally waiting for its result."""
        if not self._running:
            raise NodeClosed("node is not open", operation=operation.description)
        self._pending.put(operation)
        self._wake.set()
        if not wait:
            return operation.future
        # The operation enforces its own deadline on the worker; this is only here so a wedged or
        # dead worker surfaces as an error instead of hanging the caller forever. Waiting is split
        # from collecting deliberately: Future.result(timeout=...) signals its own expiry by
        # raising TimeoutError, which our Timeout is a subclass of, so catching that would swallow
        # and reword the operation's real failure.
        grace = (operation.timeout or DEFAULT_RPC_TIMEOUT) + 10.0
        concurrent.futures.wait([operation.future], timeout=grace)
        if not operation.future.done():
            raise Timeout(
                "the node's worker thread did not finish this operation",
                operation=operation.description,
            )
        return operation.future.result()

    def _worker_loop(self) -> None:
        """The only thread that calls into the library. Ticks constantly, runs one operation at a time."""
        try:
            while self._running:
                self._pump()
                self._wait()
        finally:
            self._teardown()

    def _library_busy(self) -> bool:
        """Whether any protocol state machine is mid-exchange.

        This is not the same question as "does Python have an operation in flight". A node
        answering someone else's RPC, or receiving a block write, is deep in a multi-frame
        exchange that nothing on this side asked for, and it needs to tick just as fast as the
        node that started it - each frame is acknowledged before the next is sent, so every tick
        it skips is added latency for both ends, and enough of them breach the protocol's
        per-frame ACK timeout.
        """
        for protocol, is_busy in self._busy_checks:
            if protocol in self._protocols and is_busy(self._handle):
                return True
        return False

    def _wait(self) -> None:
        """Pause between ticks, using whichever primitive fits what we are waiting for."""
        if self._current is not None or self._library_busy():
            # An exchange is under way. Its progress may only be visible by ticking - an arriving
            # RTACP ACK sets a flag without raising the callback - so poll, and poll with sleep():
            # Event.wait() rounds sub-millisecond waits up to the OS timer granularity on Windows,
            # which would eat most of RTACP's 10 ms ACK budget on its own.
            time.sleep(self._active_tick_interval)
        else:
            # Idle, so wait cheaply, but cut the wait short when an RTACP or PSACP frame arrives:
            # the receiver thread sets the event, so the tick that acts on it - sending the ACK
            # RTACP owes, say - happens right away instead of at the end of the interval. RPCACP
            # and BWACP frames do not raise the callback and so cannot wake us; they rely on the
            # interval itself, which is why it stays short.
            self._wake.wait(self._tick_interval)
            self._wake.clear()

    def _pump(self) -> None:
        # Operations that finish inside begin() - a subscribe, a publish - do not need to wait a
        # tick each, so keep taking work until one is genuinely in flight or the queue runs dry.
        while self._current is None:
            try:
                candidate = self._pending.get_nowait()
            except queue.Empty:
                break
            if candidate.begin():
                self._current = candidate

        error = ErrorFlag(lib.artie_can_tick(self._handle))
        if self._current is not None:
            if not self._current.advance(error):
                self._current = None
        elif error:
            self._last_background_error = error

    def _teardown(self) -> None:
        """Fail anything still outstanding, then close the library from this same thread."""
        closed = NodeClosed("node was closed while this operation was in flight")
        if self._current is not None:
            self._current.abandon(closed)
            self._current = None
        while True:
            try:
                self._pending.get_nowait().abandon(closed)
            except queue.Empty:
                break
        try:
            check(lib.artie_can_close(self._handle), "artie_can_close")
        except ArtieCanError as exc:
            self._last_background_error = exc.flags

    # ------------------------------------------------------------------ receive path

    def _on_frame_received(self, cframe) -> None:
        """Called by the library's receiver thread, which stands in for an interrupt handler.

        Copy the frame and get out; parsing and user code happen on the dispatcher thread.
        """
        try:
            _offer(self._inbox, Frame._from_c(cframe))
            # The library has already staged whatever this frame obliges us to do - an ACK to
            # send, a block to write - behind a flag that only a tick acts on. Wake the worker so
            # that happens now rather than at the end of its idle interval.
            self._wake.set()
        except Exception:  # noqa: BLE001 - an exception must never propagate into C
            import traceback

            traceback.print_exc()

    def _dispatch_loop(self) -> None:
        while True:
            frame = self._inbox.get()
            if frame is _SHUTDOWN:
                return
            try:
                self._dispatch(frame)
            except Exception:  # noqa: BLE001 - one bad frame or callback must not stop delivery
                import traceback

                traceback.print_exc()

    def _dispatch(self, frame: Frame) -> None:
        protocol_id = frame.protocol_id
        if protocol_id == _PROTOCOL_ID_RTACP:
            self._deliver(RtacpMessage._from_frame(frame), self._on_rtacp, self._rtacp_inbox)
        elif protocol_id in (_PROTOCOL_ID_PSACP_HIGH, _PROTOCOL_ID_PSACP_LOW):
            self._deliver(PsacpMessage._from_frame(frame), self._on_psacp, self._psacp_inbox)
        else:
            self._deliver(frame, self._on_frame, self._frame_inbox)

    @staticmethod
    def _deliver(message: Any, handler: Callable[[Any], None] | None, inbox: queue.Queue) -> None:
        if handler is not None:
            handler(message)
        else:
            _offer(inbox, message)

    @staticmethod
    def _receive(inbox: queue.Queue, timeout: float | None, what: str,
                 handler: Callable[[Any], None] | None, handler_name: str) -> Any:
        if handler is not None:
            raise InvalidArgument(
                f"this node delivers each {what} to its {handler_name} callback, so there is "
                "nothing to receive here; use one or the other"
            )
        # queue.Empty only comes back when a timeout was actually given, so formatting it is safe.
        try:
            return inbox.get(timeout=timeout)
        except queue.Empty:
            raise Timeout(f"no {what} arrived within {timeout:g}s") from None

    # ------------------------------------------------------------------ RPC result decoding

    def _raise_rpc_error(self, signature: RpcSignature) -> None:
        """Turn the just-completed call's recorded outcome into an exception, if it failed."""
        errno_out = ffi.new("uint8_t *")
        code = ErrorFlag(lib.artie_can_rpcacp_get_last_error(self._handle, errno_out))
        if not code:
            return
        # A NACK from the remote is recorded as INVALID_ARG plus the errno byte it sent;
        # everything else is a local or transport failure with no errno to report.
        if code == ErrorFlag.INVALID_ARG:
            raise RemoteError(
                f"node rejected {signature.name}", errno_out[0], code, "artie_can_rpcacp_call"
            )
        check(int(code), "artie_can_rpcacp_call")

    def _decode_result(self, signature: RpcSignature, binding: _SignatureBinding) -> Any:
        if signature.returns is None:
            return None

        size = signature.returns.native_size
        out = ffi.new("char[]", max(size, 1))
        check(
            lib.artie_can_rpcacp_get_result(self._handle, binding.c_signature, out, size),
            "artie_can_rpcacp_get_result",
        )
        return signature.returns.decode(bytes(ffi.buffer(out, size)))

    def _decode_whoami(self) -> WhoAmI:
        response = ffi.new("artie_can_whoami_response_t *")
        check(
            lib.artie_can_rpcacp_get_whoami_result(self._handle, response),
            "artie_can_rpcacp_get_whoami_result",
        )
        # node_name and fw_version point into library storage that the next call overwrites, so
        # copy them out now, while we are still the operation that produced them.
        return WhoAmI(
            node_address=response.node_address,
            node_name=_as_str(response.node_name),
            firmware_version=_as_str(response.fw_version),
        )

    def _decode_status(self) -> NodeStatus:
        response = ffi.new("artie_can_status_response_t *")
        check(
            lib.artie_can_rpcacp_get_status_result(self._handle, response),
            "artie_can_rpcacp_get_status_result",
        )
        return NodeStatus(uptime_ms=response.uptime_ms, error_flags=response.err_flags)

    def _decode_list(self) -> list[ProcedureInfo]:
        entries = ffi.new("artie_can_rpc_signature_t[]", RPC_LIST_PAGE_SIZE)
        check(
            lib.artie_can_rpcacp_get_list_result(self._handle, entries),
            "artie_can_rpcacp_get_list_result",
        )
        return [
            ProcedureInfo(
                procedure_id=entry.procedure_id,
                name=_as_str(entry.name),
                synchronous=bool(entry.synchronous),
                param_type_names=tuple(
                    _as_str(entry.params[index].type_name) for index in range(entry.param_count)
                ),
            )
            for entry in entries
        ]


def _rejected_as_busy(exc: BaseException) -> bool:
    """Whether a failed RPC attempt is one that is worth simply making again.

    Two failures qualify, and they are the two that mean the request was definitely not carried
    out and the obstacle is temporary, so repeating it cannot double-execute anything:

    * an EAGAIN NACK - the remote is mid-exchange and turned us away. This is routine, not
      exceptional: a node stays busy for a short while after the caller already has its result,
      long enough to finish acknowledging the exchange, and rejects whatever arrives in that
      window. Back-to-back calls hit it constantly.
    * a local :class:`~artie_can.Busy` - *this* node's state machine is mid-exchange, typically
      because it is answering a request of its own, so the call never left.

    Nothing else is retried, least of all a timeout, which leaves it genuinely unknown whether the
    remote ran the procedure.
    """
    return isinstance(exc, Busy) or (
        isinstance(exc, RemoteError) and exc.errno == RpcErrno.EAGAIN
    )


def _as_str(pointer) -> str:
    """Copy a library-owned C string into a Python string."""
    if pointer == ffi.NULL:
        return ""
    return ffi.string(pointer).decode("utf-8", errors="replace")
