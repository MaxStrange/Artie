"""
RPCACP signatures, parameter types, and standard-procedure responses.

An RPC signature is the contract both ends of a call agree on out of band: which procedure ID,
what its parameters look like on the wire, and what it returns. :class:`RpcSignature` is the
Python spelling of ``artie_can_rpc_signature_t``, and it is what you hand to both
``Node.call`` (to invoke a procedure elsewhere) and ``Node.register_procedure`` (to answer one
here).

Parameter types are named with the same strings the C library matches on ("uint8_t", "float",
"array<uint8_t, 4>", ...). The primitives are marshalled to and from Python objects
automatically; anything else is passed through as raw ``bytes`` of a size you declare.
"""
from __future__ import annotations

import dataclasses
import struct
from typing import Any, Callable, Sequence

from ._artie_can import ffi
from .enums import MAX_RPC_PARAMS
from .errors import InvalidArgument

__all__ = [
    "RpcParam",
    "RpcSignature",
    "WhoAmI",
    "NodeStatus",
    "ProcedureInfo",
    "VOID",
]

#: Type name the protocol uses for "no value here".
VOID = "NULL"

# Primitive type name -> (struct format for the native representation, size on the wire).
#
# Integers are copied to the wire in their native representation, so the struct formats use "="
# (native order, standard sizes). float and double are the exceptions: the protocol narrows them
# to 16 and 32 bits respectively, which the library does itself - Python still hands over, and
# receives back, a native 4-byte float or 8-byte double.
_PRIMITIVES: dict[str, tuple[str, int]] = {
    "bool": ("=?", 1),
    "int8_t": ("=b", 1),
    "uint8_t": ("=B", 1),
    "int16_t": ("=h", 2),
    "uint16_t": ("=H", 2),
    "int32_t": ("=i", 4),
    "uint32_t": ("=I", 4),
    "int64_t": ("=q", 8),
    "uint64_t": ("=Q", 8),
    "float": ("=f", 2),
    "double": ("=d", 4),
}


@dataclasses.dataclass(frozen=True, slots=True)
class RpcParam:
    """One parameter (or the return value) of an RPC signature.

    :param type_name: The type as both ends spell it, e.g. ``"uint32_t"``. Names in
        :data:`_PRIMITIVES` are marshalled to and from Python numbers and bools; any other name
        (``"array<uint8_t, 4>"``, ``"struct pose"``, ...) is passed through as raw bytes and
        requires ``size``.
    :param optional: Whether the caller may leave this parameter off the end of the argument list.
        A registered procedure receives ``None`` for an optional parameter that was omitted.
    :param size: Size in bytes of the value's native, in-memory representation. Required for
        non-primitive types; ignored (and inferred) for primitives.
    """

    type_name: str
    optional: bool = False
    size: int | None = None

    def __post_init__(self):
        if self.type_name != VOID and self.type_name not in _PRIMITIVES and self.size is None:
            raise InvalidArgument(
                f"type_name {self.type_name!r} is not a known primitive, so its native size must "
                f"be given explicitly, e.g. RpcParam({self.type_name!r}, size=4)"
            )

    @property
    def is_primitive(self) -> bool:
        """True if this parameter marshals to and from a Python number or bool."""
        return self.type_name in _PRIMITIVES

    @property
    def native_size(self) -> int:
        """Size of the value as it is represented in memory on this node."""
        if self.is_primitive:
            return struct.calcsize(_PRIMITIVES[self.type_name][0])
        return 0 if self.type_name == VOID else int(self.size)

    @property
    def wire_size(self) -> int:
        """Size of the value as the protocol encodes it, which narrows float and double."""
        if self.is_primitive:
            return _PRIMITIVES[self.type_name][1]
        return 0 if self.type_name == VOID else int(self.size)

    def encode(self, value: Any) -> bytes:
        """Turn a Python value into this parameter's native byte representation."""
        if self.type_name == VOID:
            return b""
        if self.is_primitive:
            try:
                return struct.pack(_PRIMITIVES[self.type_name][0], value)
            except struct.error as exc:
                raise InvalidArgument(f"{value!r} is not a valid {self.type_name}: {exc}") from exc
        raw = bytes(value)
        if len(raw) != self.native_size:
            raise InvalidArgument(
                f"{self.type_name} expects exactly {self.native_size} bytes, got {len(raw)}"
            )
        return raw

    def decode(self, raw: bytes) -> Any:
        """Turn this parameter's native byte representation back into a Python value."""
        if self.type_name == VOID:
            return None
        if self.is_primitive:
            return struct.unpack(_PRIMITIVES[self.type_name][0], raw[: self.native_size])[0]
        return bytes(raw[: self.native_size])

    def _decode_pointer(self, pointer) -> Any:
        """Decode from a ``const void *`` the library handed a dispatched procedure."""
        if pointer == ffi.NULL:
            return None
        return self.decode(bytes(ffi.buffer(ffi.cast("char *", pointer), self.native_size)))


@dataclasses.dataclass(frozen=True, slots=True)
class RpcSignature:
    """The full description of one remote procedure.

    Both ends of a call must agree on this. Use the same signature object (or an identical one) to
    register a procedure on the answering node and to call it from the requesting node.

    :param procedure_id: 0x10-0x7F for device-specific procedures; 0x00-0x0F is reserved for the
        standard procedures the library answers internally.
    :param name: Human-readable name, reported by the standard LIST procedure.
    :param params: Parameters, in argument order.
    :param returns: What the procedure returns, or ``None`` for a void procedure.
    :param synchronous: Whether the caller waits for a return value. Asynchronous procedures are
        acknowledged and then run without the caller blocking on a result.
    :param function: For a procedure this node answers, the Python callable to run. It receives
        one argument per entry in ``params`` (``None`` for omitted optional ones) and returns a
        value matching ``returns``. Raising from it reports EINVAL back to the caller.
    """

    procedure_id: int
    name: str
    params: tuple[RpcParam, ...] = ()
    returns: RpcParam | None = None
    synchronous: bool = True
    function: Callable[..., Any] | None = None

    def __post_init__(self):
        if len(self.params) > MAX_RPC_PARAMS:
            raise InvalidArgument(
                f"an RPC signature carries at most {MAX_RPC_PARAMS} parameters, got {len(self.params)}"
            )
        # Everything after a variable-length parameter would be unaddressable: the library reads
        # such a parameter as "from my offset to the end of the payload".
        for index, param in enumerate(self.params[:-1]):
            if not param.is_primitive and param.type_name != VOID:
                raise InvalidArgument(
                    f"parameter {index} ({param.type_name}) has no fixed wire size, so it must be "
                    "the last parameter in the signature"
                )

    @property
    def offsets(self) -> tuple[int, ...]:
        """Byte offset of each parameter within the encoded payload.

        Parameters are laid out back to back in declaration order, which is what both
        ``Node.call`` and a registered procedure's dispatch assume.
        """
        offsets = []
        cursor = 0
        for param in self.params:
            offsets.append(cursor)
            cursor += param.wire_size
        return tuple(offsets)

    def encode_args(self, args: Sequence[Any]) -> list[bytes]:
        """Encode call arguments, checking arity against the signature."""
        if len(args) > len(self.params):
            raise InvalidArgument(
                f"{self.name} takes at most {len(self.params)} arguments, got {len(args)}"
            )
        for index, param in enumerate(self.params[len(args):], start=len(args)):
            if not param.optional:
                raise InvalidArgument(
                    f"{self.name} requires argument {index} ({param.type_name}); only optional "
                    "trailing parameters may be omitted"
                )
        return [param.encode(value) for param, value in zip(self.params, args)]


@dataclasses.dataclass(frozen=True, slots=True)
class WhoAmI:
    """The response to the standard WHOAMI procedure."""

    node_address: int
    node_name: str
    firmware_version: str


@dataclasses.dataclass(frozen=True, slots=True)
class NodeStatus:
    """The response to the standard STATUS procedure."""

    uptime_ms: int
    error_flags: int
    """Device-specific error bits; their meaning is up to the node reporting them."""


@dataclasses.dataclass(frozen=True, slots=True)
class ProcedureInfo:
    """One entry from the standard LIST procedure: what a remote node says it can do."""

    procedure_id: int
    name: str
    synchronous: bool
    param_type_names: tuple[str, ...]

    @property
    def registered(self) -> bool:
        """False for procedure IDs the remote node reports as unassigned."""
        return self.name != "UNASSIGNED"


class _SignatureBinding:
    """Owns the ``artie_can_rpc_signature_t`` for one :class:`RpcSignature`.

    The C struct holds bare ``char *`` pointers into Python-owned buffers and, for a registered
    procedure, a C function pointer wrapping a Python callable. The library keeps referring to all
    of those after the call that introduced them returns, so this object has to outlive them - the
    node keeps one of these per signature it has seen.
    """

    __slots__ = ("signature", "_c_signature", "_keepalive", "_callback")

    def __init__(self, signature: RpcSignature):
        self.signature = signature
        self._keepalive: list[Any] = []
        self._callback = None

        c_signature = ffi.new("artie_can_rpc_signature_t *")
        c_signature.procedure_id = signature.procedure_id
        c_signature.name = self._cstring(signature.name)
        c_signature.synchronous = signature.synchronous
        c_signature.param_count = len(signature.params)

        for index, (param, offset) in enumerate(zip(signature.params, signature.offsets)):
            c_signature.params[index].type_name = self._cstring(param.type_name)
            c_signature.params[index].offset_in_msgpack = offset
            c_signature.params[index].optional = param.optional

        if signature.returns is not None:
            descriptor = ffi.new("artie_can_rpc_param_descriptor_t *")
            descriptor.type_name = self._cstring(signature.returns.type_name)
            descriptor.offset_in_msgpack = 0
            descriptor.optional = False
            self._keepalive.append(descriptor)
            c_signature.return_descriptor = descriptor
            c_signature.return_size = signature.returns.native_size

        if signature.function is not None:
            self._callback = _make_dispatch_callback(signature)
            c_signature.function = self._callback

        self._c_signature = c_signature

    @property
    def c_signature(self):
        """The ``artie_can_rpc_signature_t *`` to hand to the library."""
        return self._c_signature

    def _cstring(self, text: str):
        buffer = ffi.new("char[]", text.encode("utf-8"))
        self._keepalive.append(buffer)
        return buffer


def _make_dispatch_callback(signature: RpcSignature):
    """Wrap a signature's Python function in the C callback the library dispatches to.

    The library calls this from whichever thread drives ``artie_can_tick()`` - for these bindings
    that is the node's worker thread - so the wrapped function must not call back into the same
    node, which would deadlock waiting for a tick that cannot happen.
    """
    params = signature.params
    returns = signature.returns

    def dispatch(param_pointers, param_count, return_buffer, return_buffer_size):
        try:
            args = [
                param._decode_pointer(param_pointers[index])
                for index, param in enumerate(params[:param_count])
            ]
            value = signature.function(*args)
            if returns is not None:
                encoded = returns.encode(value)
                if len(encoded) > return_buffer_size:
                    return ffi.NULL
                ffi.memmove(return_buffer, encoded, len(encoded))
            # Non-NULL means "serviced"; NULL tells the caller EINVAL.
            return return_buffer
        except Exception:
            import traceback

            traceback.print_exc()
            return ffi.NULL

    return ffi.callback("artie_can_rpc_function_t", dispatch, error=ffi.NULL)
