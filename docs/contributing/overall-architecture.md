## Overall Architecture

[Back to Pull Request Process](./pull-request-process.md) | [Forward to Development Environment](./development-environment.md)

TODO: This document should describe the overall architecture of the Artie system,
including hardware, software, networking, and data flow, but only at a high level.

Here are a few links to architectural discussions:

### Overviews

* [Architecture Overview for the whole System](../architecture/overview.md)
* [Architecture Overview for the Robot Itself](../architecture/artie-overview.md)
* [Security Overview](../architecture/security.md)

### Telemetry

* [Telemetry Architecture](../architecture/telemetry-architecture.md)
* [Data Collection Architecture](../architecture/data-collection-architecture.md)

### Low-Level

* [CAN Protocols](https://github.com/ArtieBots/ArDK/blob/main/docs/specifications/CANProtocol.md) - We overlay several protocols on top of CAN. This document describes them in detail.
* [MsgPack Schema](https://github.com/ArtieBots/ArDK/blob/main/docs/specifications/MsgPackSchema.md) - We use [MsgPack](https://msgpack.org/) for some of the serialization/deserialization.

TODO: Look into ElasticSearch for logging data.
TODO: Look into PostgreSQL for logging debug logs.

[Back to Pull Request Process](./pull-request-process.md) | [Forward to Development Environment](./development-environment.md)
