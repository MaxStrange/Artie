# Remote Procedure Calls over CAN Bus in Artie

This document describes the API for RPCs in the C programming language
for use with [RCPACP](./CANProtocol.md#remote-procedure-call-artie-can-protocol-rpcacp).

The API allows:

* Any C data type to be sent except for pointers and unions
* Blocking (synchronous) RPCs (which may have return values)
* Non-blocking (asynchronous) RPCs
* In the case of synchronous RPCs, return values which may be multi-valued
