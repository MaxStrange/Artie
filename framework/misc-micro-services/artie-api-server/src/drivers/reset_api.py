"""
Logic for handling reset API.
"""
from . import reset
from flask import request as r
from artie_util import artie_logging as alog
import flask

reset_api = flask.Blueprint('reset_api', __name__, url_prefix="/reset")


@reset_api.route("/mcu", methods=["POST"])
@alog.function_counter("reset_mcu", alog.MetricSWCodePathAPIOrder.CALLS)
def reset_mcu():
    """
    Reset the given MCU. Please note that resetting an MCU may degrade Artie's abilities
    for a short period of time.

    * *POST*: `/reset/mcu`
        * *Parameters*:
            * `artie-id`: The Artie ID.
            * `id`: The MCU ID.
        * *Payload*: None

    """
    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "id": r.args.get('id', 'Unknown'),
            "error": "Missing artie-id parameter."
        }
        return errbody, 400
    elif 'id' not in r.args:
        errbody = {
            "artie-id": r.args['artie-id'],
            "id": "Unknown",
            "error": "Missing id parameter."
        }
        return errbody, 400

    worked = True
    match r.args['id']:
        case reset.MCU_IDS.ALL:
            worked = reset.reset_mcu(r.args['id'], artie_id=r.args['artie-id'])
        case reset.MCU_IDS.ALL_HEAD:
            worked = reset.reset_mcu(r.args['id'], artie_id=r.args['artie-id'])
        case reset.MCU_IDS.EYEBROWS:
            worked = reset.reset_mcu(r.args['id'], artie_id=r.args['artie-id'])
        case reset.MCU_IDS.MOUTH:
            worked = reset.reset_mcu(r.args['id'], artie_id=r.args['artie-id'])
        case reset.MCU_IDS.SENSORS_HEAD:
            worked = reset.reset_mcu(r.args['id'], artie_id=r.args['artie-id'])
        case reset.MCU_IDS.PUMP_CONTROL:
            worked = reset.reset_mcu(r.args['id'], artie_id=r.args['artie-id'])
        case _:
            errbody = {
                "artie-id": r.args['artie-id'],
                "id": r.args['id'],
                "error": "Invalid MCU ID."
            }
            return errbody, 400

    if not worked:
        errbody = {
            "artie-id": r.args['artie-id'],
            "id": r.args['id'],
            "error": "At least one MCU could not be reset."
        }
        return errbody, 500

    return {
        "artie-id": r.args['artie-id'],
        "id": r.args['id']
    }

@reset_api.route("/sbc", methods=["POST"])
@alog.function_counter("reset_sbc", alog.MetricSWCodePathAPIOrder.CALLS)
def reset_sbc():
    """
    Reset the given SBC. Please note that SBCs may take several minutes to completely reboot,
    and Artie service will be interrupted or degraded during that time.

    * *POST*: `/reset/sbc`
        * *Parameters*:
            * `artie-id`: The Artie ID.
            * `id`: The SBC ID. See [above](#api) for the list of available SBC IDs.
        * *Payload*: None

    """
    # TODO
    return {
        "error": "Not implemented"
    }

@reset_api.route("/status")
@alog.function_counter("get_reset_status", alog.MetricSWCodePathAPIOrder.CALLS)
def get_reset_status():
    """
    Get the reset service's submodules' statuses.

    * *GET*: `/reset/status`
        * *Parameters*:
            * `artie-id`: The Artie ID.
    * *Response 200*:
        * *Payload (JSON)*:
            ```json
            {
                "artie-id": "The Artie ID.",
                "submodule-statuses":
                    {
                        "MCU": "<Status>"
                    }
            }
            ```
        where `<Status>` is one of the available
        status values as [found in the top-level API README](../README.md#statuses)
    """
    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "error": "Missing artie-id parameter."
        }
        return errbody, 400

    err, status_or_errmsg = reset.get_status(artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": f"{status_or_errmsg}"
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id'],
            "submodule-statuses": status_or_errmsg
        }

@reset_api.route("/self-test")
@alog.function_counter("reset_self_test", alog.MetricSWCodePathAPIOrder.CALLS)
def reset_self_test():
    """
    Initiate a self-test.

    * *POST*: `/reset/self-test`
        * *Parameters*:
            * `artie-id`: The Artie ID.
        * *Payload*: None
    """
    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "error": "Missing artie-id parameter."
        }
        return errbody, 400

    err, errmsg = reset.self_test(artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": f"{errmsg}"
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id']
        }
