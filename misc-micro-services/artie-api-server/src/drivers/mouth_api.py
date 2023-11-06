"""
Logic for handling mouth API.
"""
from . import mouth
from flask import request as r
from artie_util import artie_logging as alog
import flask

mouth_api = flask.Blueprint('mouth_api', __name__, url_prefix="/mouth")

@mouth_api.route("/lcd", methods=["POST"])
@alog.function_counter("set_mouth_display")
def set_mouth_display():
    """
    Change the mouth display to show the given state.

    * *POST*: `/mouth/lcd`
        * *Parameters*:
            * `artie-id`: The Artie ID.
            * `display`: One of the available mouth display values.
        * *Payload*: None

    """
    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "display": r.args.get('display', 'Unknown'),
            "error": "Missing artie-id parameter."
        }
        return errbody, 400
    elif 'display' not in r.args:
        errbody = {
            "artie-id": r.args['artie-id'],
            "display": "Unknown",
            "error": "Missing display parameter."
        }
        return errbody, 400

    err = None
    match r.args['display']:
        case mouth.MouthValues.SMILE:
            err, errmsg = mouth.display(r.args['display'], artie_id=r.args['artie-id'])
        case mouth.MouthValues.FROWN:
            err, errmsg = mouth.display(r.args['display'], artie_id=r.args['artie-id'])
        case mouth.MouthValues.LINE:
            err, errmsg = mouth.display(r.args['display'], artie_id=r.args['artie-id'])
        case mouth.MouthValues.SMIRK:
            err, errmsg = mouth.display(r.args['display'], artie_id=r.args['artie-id'])
        case mouth.MouthValues.OPEN:
            err, errmsg = mouth.display(r.args['display'], artie_id=r.args['artie-id'])
        case mouth.MouthValues.OPEN_SMILE:
            err, errmsg = mouth.display(r.args['display'], artie_id=r.args['artie-id'])
        case mouth.MouthValues.ZIG_ZAG:
            err, errmsg = mouth.display(r.args['display'], artie_id=r.args['artie-id'])
        case mouth.MouthValues.TALKING:
            err, errmsg = mouth.display(r.args['display'], artie_id=r.args['artie-id'])
        case _:
            errbody = {
                "artie-id": r.args['artie-id'],
                "display": r.args['display'],
                "error": "Invalid display value."
            }
            return errbody, 400

    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "display": r.args['display'],
            "error": f"{errmsg}"
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id'],
            "display": r.args['display']
        }

@mouth_api.route("/lcd", methods=["GET"])
@alog.function_counter("get_mouth_display")
def get_mouth_display():
    """
    Get the mouth display state, as far as we know.

    * *GET*: `/mouth/lcd`
        * *Parameters*:
            * `artie-id`: The Artie ID.
    * *Response 200*:
        * *Payload (JSON)*:
            ```json
            {
                "artie-id": "The Artie ID.",
                "display": "One of the available display values"
            }
            ```
    """
    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "error": "Missing artie-id parameter."
        }
        return errbody, 400

    err, display_or_errmsg = mouth.get_display(artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": display_or_errmsg
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id'],
            "display": display_or_errmsg
        }

@mouth_api.route("/lcd/test", methods=["POST"])
@alog.function_counter("test_mouth_display")
def test_mouth_display():
    """
    Draw a test image on the mouth LCD.

    * *POST*: `/mouth/lcd/test`
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

    err, errmsg = mouth.test(artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": errmsg
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id']
        }

@mouth_api.route("/lcd/off", methods=["POST"])
@alog.function_counter("clear_mouth_display")
def clear_mouth_display():
    """
    Erase the contents on the mouth LCD.

    * *POST*: `/mouth/lcd/off`
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

    err, errmsg = mouth.clear(artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": errmsg
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id']
        }

@mouth_api.route("/led", methods=["POST"])
@alog.function_counter("set_mouth_led")
def set_mouth_led():
    """
    * *POST*: `/mouth/led`
        * *Parameters*:
            * `artie-id`: The Artie ID.
            * `state`: One of `on`, `off`, or `heartbeat`
        * *Payload*: None

    """
    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "state": r.args.get('state', 'Unknown'),
            "error": "Missing artie-id parameter."
        }
        return errbody, 400
    elif 'state' not in r.args:
        errbody = {
            "artie-id": r.args['artie-id'],
            "state": "Unknown",
            "error": "Missing state parameter."
        }
        return errbody, 400

    err = None
    match state := r.args['state'].lower():
        case mouth.LEDStates.ON:
            err, errmsg = mouth.led(state, artie_id=r.args['artie-id'])
        case mouth.LEDStates.OFF:
            err, errmsg = mouth.led(state, artie_id=r.args['artie-id'])
        case mouth.LEDStates.HEARTBEAT:
            err, errmsg = mouth.led(state, artie_id=r.args['artie-id'])
        case _:
            errbody = {
                "artie-id": r.args['artie-id'],
                "state": r.args['state'],
                "error": "Invalid state value."
            }
            return errbody, 400

    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "state": r.args['state'],
            "error": f"{errmsg}"
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id'],
            "state": r.args['state'].lower()
        }

@mouth_api.route("/led", methods=["GET"])
@alog.function_counter("get_mouth_led")
def get_mouth_led():
    """
    * *GET*: `/mouth/led`
        * *Parameters*:
            * `artie-id`: The Artie ID.
    * *Response 200*:
        * *Payload (JSON)*:
            ```json
            {
                "artie-id": "The Artie ID.",
                "state": "on, off, or heartbeat"
            }
            ```

    """
    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "error": "Missing artie-id parameter."
        }
        return errbody, 400

    err, state_or_errmsg = mouth.get_led(artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": f"{state_or_errmsg}"
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id'],
            "state": r.args['state'].lower()
        }

@mouth_api.route("/fw", methods=["POST"])
@alog.function_counter("reload_mouth_firmware")
def reload_mouth_firmware():
    """
    Reload MCU firmware.

    * *POST*: `/mouth/fw`
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

    err, errmsg = mouth.reload_firmware(artie_id=r.args['artie-id'])
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

@mouth_api.route("/status", methods=["GET"])
@alog.function_counter("get_mouth_status")
def get_mouth_status():
    """
    Get the mouth submodules' statuses.

    * *GET*: `/mouth/status`
        * *Parameters*:
            * `artie-id`: The Artie ID.
    * *Response 200*:
        * *Payload (JSON)*:
            ```json
            {
                "artie-id": "The Artie ID.",
                "FW": "<Status>",
                "LED": "<Status>",
                "LCD": "<Status>"
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

    err, status_or_errmsg = mouth.get_status(artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": f"{status_or_errmsg}"
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id']
        }

@mouth_api.route("/self-test", methods=["POST"])
@alog.function_counter("mouth_self_test")
def mouth_self_test():
    """
    Initiate a self-test.

    * *POST*: `/mouth/self-test`
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

    err, errmsg = mouth.self_test(artie_id=r.args['artie-id'])
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
