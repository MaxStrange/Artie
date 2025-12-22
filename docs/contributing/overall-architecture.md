## Overall Architecture

Here are a few links to architectural discussions:

### Overviews

* [Architecture Overview for the whole System](../architecture/overview.md)
* [Architecture Overview for the Robot Itself](../architecture/artie-overview.md)
* [Security Overview](../architecture/security.md)

### Telemetry

* [Telemetry Architecture](../architecture/telemetry-architecture.md)
* [Data Collection Architecture](../architecture/data-collection-architecture.md)

### Low-Level

* [CAN Protocols](../sdk/CANProtocol.md) - We overlay several protocols on top of CAN. This document describes them in detail.
* [MsgPack Schema](../sdk/MsgPackSchema.md) - We use [MsgPack](https://msgpack.org/) for some of the serialization/deserialization.

TODO: Look into ElasticSearch for logging data.
TODO: Look into PostgreSQL for logging debug logs.
