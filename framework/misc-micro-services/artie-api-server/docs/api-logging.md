# API for Logging Module

## Common Parameters

Most logging API methods require the following parameters:

* `level`: Must be one of:
  - `"DEBUG"`: All logs are returned.
  - `"INFO"`: All logs except for DEBUG logs are returned.
  - `"WARNING"`: All logs except DEBUG and INFO are returned.
  - `"ERROR"`: All logs except DEBUG, INFO, and WARNING are returned.
  - `"UNKNOWN"`: Logs are given this tag when their log level name is unable to be processed for some reason.
* `process`: The name of the generating process. Can be '*' for all. Might be 'Unknown' when returned.
* `thread`: The name of the generating thread. Can be '*' for all. Might be 'Unknown' when returned.
* `service`: The name of the generating Artie service. Can be '*' for all.

## Get Recent Logs

Get logs from the last N seconds.

Note that when N is small enough, this can give the feeling of 'live'
logs, but this is not the preferred way of streaming logs.

TODO: We have a REST server for ingress/egress to/from the cluster,
      which is useful for almost everything we could want to do with Artie.
      However, live streaming of telemetry and sensor data (including
      video and audio, which must be encrypted) is not feasible over a REST
      server. Instead, we need to determine a way to egress realtime data
      appropriately.

* *GET*: `/logs/recent`
    * *Parameters*:
        * `artie-id`: The Artie ID.
        * `seconds`: Integer value. We get logs from the last this many seconds.
        * `level`: Only return logs of this level or higher in importance. See [Common Parameters](#common-parameters).
        * `process`: Only return logs coming from the given process. See [Common Parameters](#common-parameters).
        * `thread`: Only return logs coming from the given thread. See [Common Parameters](#common-parameters).
        * `service`: Only return logs coming from the given Artie service. See [Common Parameters](#common-parameters).
* *Response 200*:
    * *Payload (JSON)*:
        ```json
        {
            "artie_id": "The Artie ID",
            "seconds": "Integer. The number of seconds queried",
            "level": "Log level. See Common Parameters",
            "process": "The process name. See Common Parameters",
            "thread": "The thread name. See Common Parameters",
            "service": "The Artie service. See Common Parameters",
            "logs": [
                {
                    "level": "Log level. See Common Parameters",
                    "message": "The actual log message.",
                    "processname": "The name of the process.",
                    "threadname": "The name of the thread.",
                    "timestamp": "Timestamp in artie logging's date format",
                    "servicename": "The Artie service.",
                    "artieid": "The artie ID"
                }
            ]
        }
        ```

## Query Logs

Get a list of logs queried by means of a set of parameters.

* *GET*: `/logs/query`
    * *Parameters*:
        * `artie-id`: The Artie ID.
        * `limit`: An integer maximum number of logs to receive. If -1, we accept all logs.
        * `starttime`: Receive logs generated after this time. Format is artie logging's date format. Set to '*' for unset.
        * `endtime`: Receive logs generated before this time. Format is artie logging's date format. Set to '*' for unset.
        * `messagecontains`: A Python regular expression that must match any message returned. Can be '*' for unset.
        * `level`: Only return logs of this level or higher in importance. See [Common Parameters](#common-parameters).
        * `process`: Only return logs coming from the given process. See [Common Parameters](#common-parameters).
        * `thread`: Only return logs coming from the given thread. See [Common Parameters](#common-parameters).
        * `service`: Only return logs coming from the given Artie service. See [Common Parameters](#common-parameters).
* *Response 200*:
    * *Payload (JSON)*:
        ```json
        {
            "logs": [
                {
                    "level": "Log level. See Common Parameters",
                    "message": "The actual log message.",
                    "processname": "The name of the process.",
                    "threadname": "The name of the thread.",
                    "timestamp": "Timestamp in artie logging's date format",
                    "servicename": "The Artie service.",
                    "artieid": "The artie ID"
                }
            ]
        }
        ```

## List Services

List the logging services that are available. Values returned
from this request are valid for inputs as `service` into the parameters
of other requests in this API.

* *GET*: `/logs/services`
    * *Parameters*:
        * `artie-id`: The Artie ID.
* *Response 200*:
    * *Payload (JSON)*:
        ```json
        {
            "services": [
                "service1",
                "service2",
                "etc."
            ]
        }
        ```
