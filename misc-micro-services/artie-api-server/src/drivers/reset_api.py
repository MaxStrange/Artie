"""
Logic for handling reset API.
"""
from . import reset
from flask import request as r
from artie_util import artie_logging as alog
import flask

reset_api = flask.Blueprint('reset_api', __name__, url_prefix="/reset")


@reset_api.route("/mcu", methods=["POST"])
@alog.function_counter("reset_mcu")
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

    match r.args['id']:
        case reset.MCU_IDS.ALL:
            reset.reset_mcu(r.args['id'], artie_id=r.args['artie-id'])
        case reset.MCU_IDS.ALL_HEAD:
            reset.reset_mcu(r.args['id'], artie_id=r.args['artie-id'])
        case reset.MCU_IDS.EYEBROWS:
            reset.reset_mcu(r.args['id'], artie_id=r.args['artie-id'])
        case reset.MCU_IDS.MOUTH:
            reset.reset_mcu(r.args['id'], artie_id=r.args['artie-id'])
        case reset.MCU_IDS.SENSORS_HEAD:
            reset.reset_mcu(r.args['id'], artie_id=r.args['artie-id'])
        case reset.MCU_IDS.PUMP_CONTROL:
            reset.reset_mcu(r.args['id'], artie_id=r.args['artie-id'])
        case _:
            errbody = {
                "artie-id": r.args['artie-id'],
                "id": r.args['id'],
                "error": "Invalid MCU ID."
            }
            return errbody, 400

    return {
        "artie-id": r.args['artie-id'],
        "id": r.args['id']
    }

@reset_api.route("/sbc", methods=["POST"])
@alog.function_counter("reset_sbc")
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
