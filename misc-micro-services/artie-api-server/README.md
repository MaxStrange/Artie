# Artie API Server

The Artie API Server is the single point of ingress into the Artie cluster. Current clients
planned to make use of this server are the Artie CLI and the Artie workbench.

## Contents

- [Eyebrows](./docs/api-eyebrows.md) - also includes the servos for the eyes
- [Mouth](./docs/api-mouth.md)
- [Reset](./docs/api-reset.md)

## Common Objects

### MCU IDs

* `all`: *all* the MCUs.
* `all-head`: *all* the MCUs in the head.
* `eyebrows`: *Both* the right and left eyebrow MCU (they cannot be targeted individually).
* `mouth`: The mouth MCU.
* `sensors-head`: The MCU responsible for collecting sensor data in the head.
* `pump-control`: The MCU responsible for pump control.

### SBC IDs

SBC (single board computer) IDs:

* `all`: *all* the SBCs.
* `all-head`: *all* the SBCs in the head.
* `controller`: The controller SBC node.

### Common Responses

* *Response 200* or *Response 201*: The request has been successfully delivered to the appropriate cluster resource
  and as far as we can tell, it worked.
    * *Payload (JSON)*:
        ```json
        {
            "artie-id": "The Artie ID."
        }
        ```
    The payload may include additional information; generally it will include all supplied parameters.
* *Response 400*: This is given if the request contains problems, such as an unknown Artie ID,
  missing query parameters, or an invalid argument value.
    * *Payload (JSON)*:
        ```json
        {
            "artie-id": "The Artie ID.",
            "error": "A description of the error."
        }
        ```
* *Response 504*: The Artie API server has sent the request onto the appropriate cluster resource,
  but has not received a response in a reasonable amount of time. You can try again, but it probably
  means the resource is overloaded or down.
    * *Payload (JSON)*:
        ```json
        {
            "artie-id": "The Artie ID."
        }
        ```
    The payload may include additional information; generally it will include all supplied parameters.
