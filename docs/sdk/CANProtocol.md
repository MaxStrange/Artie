# CAN Protocols

Most of the single board computers (SBCs) and the microcontroller units (MCUs) in
Artie are connected by means of a CAN bus. Since CAN provides only the bottom-most layers
of the OSI model, it is up to us to define the network and transport layers
for CAN communication to be particularly useful.

To this end, we have four different protocols all running over the same CAN bus. In
order of priority on the CAN bus, these protocols are:

* [Real Time Artie CAN Protocol](#real-time-artie-can-protocol) - for strict real time message delivery
* [Remote Procedure Call Artie CAN Protocol](#remote-procedure-call-artie-can-protocol) - for RPCs (synchronous and asynchronous)
* [Pub/Sub Artie CAN Protocol](#pubsub-artie-can-protocol-psacp) - for pub/sub
* [Block Write Artie CAN Protocol](#block-write-artie-can-protocol-bwacp) - for large data transfers, such as FW updates


## Real Time Artie CAN Protocol (RTACP)

RTACP's purpose is to enable small messages that can meet hard real time requirements. The general features
of this protocol are:

* Strict real time: assuming reliable CAN wiring, any given single message using this protocol should reach
  at least one target within 150 microseconds of transmit.
* Can broadcast or send to a single remote address.
* In case of sending to a remote address (instead of a broadcast), we can guarantee receipt.
* At most one CAN's frame worth of data payload (8 bytes maximum).

### RTACP Specification

The detailed specification for RTACP follows.

RTACP uses extended CAN frames. An extended CAN frame looks like this
(from [Wikipedia](https://en.wikipedia.org/wiki/CAN_bus#Frames)):

```
[1 bit SOF]
[11 bits ID A]          -- We care about this
[1 bit SRR]
[1 bit IDE]
[18 bits ID B]          -- We also care about this
[1 bit RTR]
[2 bits reserved]
[4 bits DLC]            -- We care about this
[0-64 bits Data]        -- And we care about this
[15 bits CRC]
[1 bit CRC delimeter]
[1 bit ACK slot]
[1 bit ACK delimeter]
[7 bits EOF]
```

(Total overhead bits per CAN frame: 64; this accounts for all bits but the Data field)

For RTACP (and all Artie CAN protocols), we only care about the following four fields:

1. ID A (Identifier part A)
1. ID B (Identifier part B)
1. DLC (Data Length Code)
1. Data (Data field)

For this specification, we refer to the combination of ID A and ID B as just 'ID', and we
consider it to be 29 bits (even though they are not consecutive).

All other fields in a CAN frame are handled by the CAN protocol itself.

#### ID and Frames

The 29 ID bits in RTACP are assigned like this:

```
[000] - specifies RTACP and prioritizes above all other protocols
[000x] - x can be 0, in which case this is an ACK frame or else 1, in which case it is a MSG frame.
[pp] - 2 bits of user-assigned priority: LOW (11), MED-LOW (10), MED-HIGH (01), HIGH (00)
[ssssss] - 6 bits of sender address, which must be unique among all nodes on the CAN bus
[tttttt] - 6 bits of target address, 0x00 specifies broadcast
1 for rest of ID field (8 bits)
```

* *ACK 000x=0000*: If the MSG frame that generates this ACK was targeted to a specific node
  (i.e., not a broadcast), then the targeted node should send back an ACK frame.
  If the ACK is not received by the MSG-sending node within 1 ms, the MSG should be resent.
* *MSG 000x=0001*: No specific notes. See Data below.

#### DLC

The data length code field should specify the number of bytes in the data field (0 to 8 bytes).

#### Data

*MSG frame*:
The data field is application-defined with a maximum of 8 bytes. There is no specification at this
layer for sending larger than 8-byte data.

*ACK frame*:
The data field should be identical to the ACK'ed MSG frame. If it is not, the sender should assume
an error in transmission and retransmit the original MSG frame. If the ACK is not received
by the MSG-sending node... what happens? I wrote this 2 years ago and apparently never finished my sentence...

## Remote Procedure Call Artie CAN Protocol (RPCACP)

RPCACP's purpose is to enable a remote procedure call (RPC) mechanism on the CAN bus. This allows
a requesting node to synchronously or asynchronously fire off a function on a remote node.
If synchronous, a return value is given. Here are the general features:

* Blocking or asynchronous
* If blocking, the requesting node will wait until an ACK + return data, which may be any
  C datatype (except for pointers or unions, which wouldn't make much sense).
* The requesting node can send over any C datatypes as function arguments (again, except for
  pointers and unions).
* Guaranteed delivery both ways.
* Point-to-point - there is no multi- or broadcast.

### RPCACP Specification

The detailed specification for RPCACP follows.

As in [RTACP](#rtacp-specification), we only care about ID, DLC, and Data fields of the CAN frame.

#### ID and Frames

```
[010] - specifies RPCACP
[0xxx] - type of frame: 0x00: ACK, 0x01: NACK, 0x02: StartRPC, 0x03: StartReturn, 0x04: TxData, 0x05: RxData
[pp] - 2 bits of user-assigned priority: LOW (11), MED-LOW (10), MED-HIGH (01), HIGH (00)
[ssssss] - 6 bits of sender address, which must be unique among all nodes on the CAN bus
[tttttt] - 6 bits of target address, 0x00 not allowed, as this is reserved for broadcast, which does not exist in this protocol
[rrrr rrrr] - 8 bits of random value (explained in Data section below)
```

* *Requesting Node*: The node that is originating an RPC request
* *Remote Node*: The node that is the target fo the RPC request
* *Multi-Frame RPC*: An RPC that requires a StartRPC frame and one or more TxData frames.
* *Single-Frame RPC*: An RPC that requires only a StartRPC frame.
* *Multi-Frame Return*: A return value (in response to a synchronous RPC request) that requires a StartReturn and one ore more RxData frames.
* *Single-Frame Return*: A return value (in response to a synchronous RPC request) that requires only a StartReturn frame.

NOTE that the sender address is always the sender of the message - specifically,
in the case of ACK, NACK, StartReturn, and RxData frames, 'sender address' refers to the remote node,
while in the case of StartRPC and TxData frames, 'sender address' is the requesting node.

* *ACK 0xxx=0000*: A single ACK frame is sent from the remote node to the requesting node at the end of
  a complete request (see StartRPC and TxData, below) if the remote node has successfully
  received all parts of the RPC request and it can service the request. If
  an ACK is not received within 30ms, or if a NACK is received, the entire RPC request should be resent.
* *NACK 0xxx=0001*: A single NACK frame should be sent from the remote node to the requesting node
  at the end of a complete request (see StartRPC and TxData, below) if the remote node
  did not successfully receive all parts of the RPC request or if it cannot service the request for some
  reason.
* *StartRPC 0xxx=0010*: A single StartRPC frame is sent from the requesting node to the remote node
  in order to start an RPC request. This frame may contain the entire request, in the case of simple
  RPCs (a single-frame RPC), or it may contain a part of the request along with metadata (multi-frame RPC).
  In the case of a partial request, the requesting node will start sending out TxData frames until the RPC request is completed.
  The ACK/NACK frame should be sent from the remote node only once, at the end of the final TxData
  frame (in the case of a multi-frame RPC) or after the StartRPC frame (in the case of a single-frame RPC).
* *StartReturn 0xxx=0011*: In the case of synchronous RPCs, a single StartReturn frame is sent from the remote
  node to the requesting node as soon as possible after the remote procedure call is finished.
  This frame may contain an entire return value, in the case of a single-frame return, or it may
  contain part of the return data along with metadata (in the case of a multi-frame return).
  In the case of asynchronous RPCs, no return value is sent back, and as such, no StartReturn frame is sent.
* *TxData 0xxx=0100*: Already described above in *StartRPC*
* *RxData 0xxx=0101*: Already described above in *StartReturn*

#### DLC

The data length code field should specify the number of bytes in the data field (0 to 8 bytes).

#### Data

The data field depends on the type of frame:

*ACK frame*:
An ACK frame should have its random bits (in the ID field) set to the same value as the message it is ACK'ing.
Note that the message being ACK'ed is the last frame in the RPC request. The data field should be zero bytes.

*NACK frame*:
A NACK frame should have its random bits (in the ID field) set to the same value as the message it is NACK'ing.
Note that the message being NACK'ed is the last frame in the RPC request.
The data field contains 1 byte, which should be an error code. Allowable error codes any Linux errno value,
but in particular, the following values have specific meanings in this context:

* 0x00:            Something went wrong in transmission. Send whole request again.
* 0x01: EPERM:     I can't complete this request because I do not have this capability. This is likely a programmer error
                   and sending another request will do no good.
* 0x07: E2BIG:     Argument list is too long. This NACK originates from the RPC library and indicates that you have attempted
                   to call an RPC with too many args (i.e., the RPC signatures in the requesting node and the remote node do not match).
                   This is definitely a programmer error and sending again will only result in the same error.
* 0x08: ENOEXEC:   We could not unpack the RPC correctly. It's possible, but unlikely that this is a transmission error. Most likely,
                   it is a bug in the serialization/deserialization of the RPC.
* 0x0b: EAGAIN:    Something transient went wrong, such as being overloaded with requests or just not able to get to it right now,
                   try again.
* 0x16: EINVAL:    At least one of the RPC arguments is invalid. The arguments were unpacked correctly, but there is a RPC
                   signature mismatch. This is a programmer error. Sending again will result in the same error.
* 0x72: EALREADY:  We are already working on this RPC. This should only be sent if the RPC is identical and already being worked on.
                   "Identical" in this context includes the node addresses, but does *not* include the random values.

*StartRPC frame*:
A StartRPC frame is sent from a requesting node to a remote node, as specified in the addressing bits in the ID field.
The data bits are as follows:

```
[1 bit synchronous/asynchronous] - A zero here indicates an asynchronous request. A 1 indicates a synchronous (blocking) request.
[7 bit procedure ID] - 7 bits that determine what RPC to execute. The allowable values here are part of the RPC signature,
                       and are defined per device, as each device may have different capabilities.
[16 bits] - CRC16 over the following data: [1 bit a/synch][7 bit procedure ID][all RPC payload over the whole series of frames, including byte stuffing]
[Remaining data] - RPC data, which may be continued by subsequent TxData frames.
```

*StartReturn frame*:
A StartReturn frame is sent from a remote node to a requesting node once a synchronous RPC has been completed.
The data field looks like this:

```
[1 bit, always value = 1]
[7 bit procedure ID] - the ID of the RPC that was executed.
[16 bits] - CRC16 over the following data: [1st bit (always 1)][7 bit procedure ID][all return value payload over the whole series of frames, including byte stuffing]
[Remaining data] - Return value data, which may be continued by subsequent RxData frames.
```

*TxData frame*:
The data field of a TxData frame is comprised entirely of [byte-stuffed](./ByteStuffing.md) [MsgPack](./MsgPackSchema.md) data.

*RxData frame*:
The data field of a RxData frame is comprised entirely of [byte-stuffed](./ByteStuffing.md) [MsgPack](./MsgPackSchema.md) data.

#### Some Guidance on the RPC Protocol

The RPC frames are a little complicated in terms of the protocol stack. Here is some guidance:

```
RPC method signatures
---------
MsgPack or similar (for serialization/deserialization of C data types with an agreed upon schema)
---------
RPCACP (including CRC and byte stuffing)
---------
CAN
```

When a requesting node wants to request an RPC from a remote node, it interacts with the [Artie RPC library](./RPCSchema.md)
to call one of the remote node's available RPCs. This library interacts with [MsgPack](./MsgPackSchema.md)
to pack up the function's arguments into a binary format that we then hand over to the
RPCACP stack. This stack first assembles the RPC payload (the async/sync bit, the procedure ID, and the MsgPack data),
then it [stuffs](./ByteStuffing.md) the payload. Next it computes a CRC16 over the stuffed payload. Finally, it shards it
into a StartRPC frame and subsequent TxData frames and handles the interaction with the CAN driver
to send out the RPC request.

On the other side, the remote node's CAN hardware assembles each CAN frame into ID and data fields,
which are then handed over to the RPCACP stack upon reading the first three bits of the CAN ID field.
The RPCACP stack accepts first the StartRPC frame, and then (if applicable), the subsequent TxData frames.
Once all frames have been received (as decoded by [byte stuffing](./ByteStuffing.md)), the CRC bits are removed and
the resulting payload is checked against that CRC. If it is invalid, a NACK with 0x00 errno is sent.
Otherwise, the payload is decoded using [MsgPack](./MsgPackSchema.md) and fed to the remote node's [RPC stack](./RPCSchema.md).
If MsgPack fails to decode the payload, a NACK is generated with 0x08 (ENOEXEC) errno. Otherwise, the RPC stack
attempts to handle the request. If it can, it sends back an ACK. Otherwise, it will send a NACK with
the appropriate errno byte.

If the request is a blocking one, the remote node's RPC stack will send back the return values,
per the RPC signature, in a way that is analogous to the requesting node's RPC request, except
that a StartReturn frame and subsequent RxData frames are sent instead of StartRPC and TxData frames.

Due to the fact that these RPCs may be blocking and may have multiple frames of data,
nodes are not expected to be able to handle more than one RPC request at a time.


## Pub/Sub Artie CAN Protocol (PSACP)

The purpose of PSACP is to provide a pub/sub protocol over CAN bus. This allows a decoupled
approach to things like logging, heart beats, or sensor data reading, where a node can publish its data
as it becomes available, without worrying about who is listening for it. The general features
of this protocol are:

* Up to 234 topics currently.
* Topics are static - they are agreed upon implicitly via a predefined schema.
* A node can listen on many topics.
* A single message is sent to a single topic at a time.
* High priority topics and low priority topics split the CAN priority space around BWACP
  so that logging doesn't drown out large data transfers like firmware upgrades.
* No ACK, missed data is simply lost.
* A published message can be of any data length.

### PSACP Specification

The detailed specification for PSACP follows.

#### ID and Frames

The ID field looks like this:

```
[100 OR 110] - specifies PSACP. When 100, it is High Priority Pub/Sub, when 110, it is Low Priority Pub/Sub.
[00x1] - x can be 0, in which case this is a PUB frame, or 1, in which case this is a DATA frame.
[pp] - 2 bits of user-assigned priority: LOW (11), MED-LOW (10), MED-HIGH (01), HIGH (00)
[ssssss] - 6 bits of sender address, which must be unique among all nodes on the CAN bus
[tttttttt] - 8 bits of topic, see below for reserved topic values
1 for rest of ID field (6 bits)
```

* *PUB frame 00x1=0001*: This frame is sent to start a publish sequence, and may be the entire sequence
                         if the data we are publishing is small enough.
* *DATA frame 00x1=0011*: These frames are sent one after another until all the data in a single publish sequence has been sent.

Reserved topic values:

* 0x00: Broadcast to all topics
* 0x01 - 0x0A: Reserved for future use
* 0x0B - 0xF4: Currently usable topic space
* 0xF5 - 0xFF: Reserved for future use

#### DLC

The data length code field should specify the number of bytes in the data field (0 to 8 bytes).

#### Data

The data field depends on the type of frame:

*PUB frame*:
A PUB frame's data field consists of the following:

```
[16 bits] - CRC16 computed over the byte-stuffed entire payload (before sharding across PUB and DATA frames)
Rest of the data is byte-stuffed payload, which may be continued by DATA frames.
```

*DATA frame*:
A DATA frame's data field is entirely [byte-stuffed](./ByteStuffing.md) payload data.

## Block Write Artie CAN Protocol (BWACP)

The purpose of BWACP is to provide a means to transfer large blocks of data
at a low priority over CAN bus. This is useful mostly for firmware updates,
but can be used for anything that requires a large data transfer to one or
multiple addresses. The general features of BWACP are:

* Single address or multicast
* Ensure data integrity
* Ensure entire message is received

### BWACP Specification

The detailed specification for BWACP follows.

#### ID and Frames

The ID field looks like this:

```
[101] - specifies BWACP.
[0xx1] - 0001: REPEAT, 0011: READY, 0111: DATA
[pp] - 2 bits of user-assigned priority: LOW (11), MED-LOW (10), MED-HIGH (01), HIGH (00)
[ssssss] - 6 bits of sender address, which must be unique among all nodes on the CAN bus
[tttttt] - 6 bits of target address
[cccccc] - if DATA or READY: 6 bits of target class; if REPEAT: all 0s
[1 bit] - if DATA, 0 means I am not a repeat; 1 means I am a repeat of the last frame;
          if READY, 1 means interrupt the currently ongoing data write and start over
          using this frame;
          if REPEAT, 1 means repeat the last frame, 0 means repeat the whole sequence.
[1 bit] - if DATA, parity bit to indicate relative ordering of frames, otherwise should be 1.
```

* *REPEAT frame 0xx1=0001*: This frame is sent at any time during a data transfer from any remote node
  to indicate that either the last frame should be repeated or that the entire sequence should be repeated/restarted.
* *READY frame 0xx1=0011*: This frame is sent from a writing node to a single device (tttttt != 0x3F)
  or to a class of devices (tttttt = 0x3F, cccccc = Bit mask, see below) to initiate a data transfer.
  If this is sent with its interrupt bit set, it means all target nodes should discard the current block
  transfer and restart on this frame.
* *DATA frame 0xx1=0111*: This frame is sent from a writing node to a single device or to a class of
  devices and contains up to 8 data bytes. If the repeat bit is set, it means this frame is a repeat
  of the last frame and should be discarded by any devices that did not send back a REPEAT on the last
  DATA frame. The parity bit should be set to 0 for the first DATA frame, then to 1, then back to 0,
  etc., and should be used by remote devices to determine if they have missed a frame.

Multicasting:

The 6 class bits in the ID field determine the class of devices in the case of a multicast,
and are a bit mask.

To multicast, the sender should set the 6 bit target address to the special multicast address
(0x3F) and then set one or more bits in the 6 bit class mask according to the following table:

```
          0              1         2            3           4          5
Single Board Computer | MCU | Sensor Node | Motor Node | Reserved | Reserved
```

#### DLC

The data length code field should specify the number of bytes in the data field (0 to 8 bytes).

#### Data

*REPEAT frame*:
The data field of the REPEAT frame should be empty (0 bytes).

*READY frame*:
The data field of the READY frame is composed of a 3 byte CRC24 (which is composed over all following
bytes, including the address, but excluding any stuffing bytes), followed by a 4 byte address
(which is application-specific), and then the first stuffing byte.

*DATA frame*:
The entire data field of each DATA frame is composed of [byte-stuffed](./ByteStuffing.md) payload data.
