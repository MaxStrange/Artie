"""
Logic for handling mouth API.
"""
from . import eyebrows
from flask import request as r
from artie_util import artie_logging as alog
import flask

eyebrows_api = flask.Blueprint('eyebrows_api', __name__, url_prefix="/eyebrows")

@eyebrows_api.route("/lcd/<which>", methods=["POST"])
@alog.function_counter("set_eyebrows_display")
def set_eyebrows_display(which: str):
    """
    Change the eyebrow display to show the given state.

    * *POST*: `/eyebrows/lcd/<which>` where `<which>` is `left` or `right`.
        * *Parameters*:
            * `artie-id`: The Artie ID.
        * *Payload (JSON)*:
            ```json
            {
                "vertices": ["H/M/L", "H/M/L", "H/M/L"]
            }
            ```
    """
    which = which.lower()

    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "error": "Missing artie-id parameter."
        }
        return errbody, 400
    elif which not in ('left', 'right'):
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": "Need either 'left' or 'right'"
        }
        return errbody, 404

    # Double check body
    vertices = r.form.get('vertices', None)
    if not vertices:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": "Missing 'vertices' section from request body."
        }
        return errbody, 400

    # Double check type of 'vertices'
    try:
        len_of_verts = len(vertices)
    except TypeError:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": "Vertices section in request body is not a list, but should be a list of exactly three strings."
        }
        return errbody, 400

    # Check length of 'vertices'
    if len_of_verts != 3:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": f"Vertices section in request body should be a list of exactly three strings, but has length {len_of_verts}"
        }
        return errbody, 400

    # Check that the type of the subitems is correct
    for item in vertices:
        if item not in ("H", "M", "L"):
            errbody = {
                "artie-id": r.args['artie-id'],
                "error": f"Vertices section in request body should be a list of exactly three strings, each of which should be one of 'H', 'L', or 'M'."
            }
            return errbody, 400

    # Run the command
    err, errmsg = eyebrows.display(vertices, which, artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": f"{errmsg}"
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id'],
            "eyebrow-side": which,
            "vertices": r.form['vertices']
        }

@eyebrows_api.route("/lcd/<which>", methods=["GET"])
@alog.function_counter("get_eyebrows_display")
def get_eyebrows_display(which: str):
    """
    * *GET*: `/eyebrows/lcd/<which>` where `<which>` is `left` or `right`.
        * *Parameters*:
            * `artie-id`: The Artie ID.
    * *Response 200*:
        * *Payload (JSON)*:
            ```json
            {
                "artie-id": "The Artie ID.",
                "eyebrow-side": "left or right",
                "vertices": ["H/M/L", "H/M/L", "H/M/L"] OR "test" OR "clear"
            }
            ```
    """
    which = which.lower()

    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "error": "Missing artie-id parameter."
        }
        return errbody, 400
    elif which not in ('left', 'right'):
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": "Need either 'left' or 'right'"
        }
        return errbody, 404

    err, display_or_errmsg = eyebrows.get_display(which, artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": display_or_errmsg
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id'],
            "eyebrow-side": which,
            "vertices": display_or_errmsg
        }

@eyebrows_api.route("/lcd/<which>/test", methods=["POST"])
@alog.function_counter("test_mouth_display")
def test_eyebrows_display(which: str):
    """
    Draw a test image on the eyebrow LCD.

    * *POST*: `/eyebrows/lcd/<which>/test` where `<which>` is `left` or `right`
        * *Parameters*:
            * `artie-id`: The Artie ID.
        * *Payload*: None
    """
    which = which.lower()

    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "error": "Missing artie-id parameter."
        }
        return errbody, 400
    elif which not in ('left', 'right'):
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": "Need either 'left' or 'right'"
        }
        return errbody, 404

    err, errmsg = eyebrows.test(which, artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": errmsg
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id'],
            "eyebrow-side": which
        }

@eyebrows_api.route("/lcd/<which>/off", methods=["POST"])
@alog.function_counter("clear_eyebrows_display")
def clear_eyebrows_display(which: str):
    """
    Erase the contents on an eyebrow LCD.

    * *POST*: `/eyebrows/lcd/<which>/off` where `<which>` is `left` or `right`
        * *Parameters*:
            * `artie-id`: The Artie ID.
        * *Payload*: None
    """
    which = which.lower()

    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "error": "Missing artie-id parameter."
        }
        return errbody, 400
    elif which not in ('left', 'right'):
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": "Need either 'left' or 'right'"
        }
        return errbody, 404

    err, errmsg = eyebrows.clear(which, artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": errmsg
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id'],
            "eyebrow-side": which
        }

@eyebrows_api.route("/led/<which>", methods=["POST"])
@alog.function_counter("set_eyebrows_led")
def set_eyebrows_led(which: str):
    """
    * *POST*: `/eyebrows/led/<which>` where `<which>` is `left` or `right`.
        * *Parameters*:
            * `artie-id`: The Artie ID.
            * `state`: One of `on`, `off`, or `heartbeat`
        * *Payload*: None
    """
    which = which.lower()

    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "state": r.args.get('state', 'Unknown'),
            "error": "Missing artie-id parameter."
        }
        return errbody, 400
    elif which not in ('left', 'right'):
        errbody = {
            "artie-id": r.args['artie-id'],
            "state": r.args.get('state', 'Unknown'),
            "error": "Need either 'left' or 'right'"
        }
        return errbody, 404
    elif 'state' not in r.args:
        errbody = {
            "artie-id": r.args['artie-id'],
            "state": "Unknown",
            "error": "Missing state parameter."
        }
        return errbody, 400

    err = None
    match state := r.args['state'].lower():
        case eyebrows.LEDStates.ON:
            err, errmsg = eyebrows.led(which, state, artie_id=r.args['artie-id'])
        case eyebrows.LEDStates.OFF:
            err, errmsg = eyebrows.led(which, state, artie_id=r.args['artie-id'])
        case eyebrows.LEDStates.HEARTBEAT:
            err, errmsg = eyebrows.led(which, state, artie_id=r.args['artie-id'])
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
            "eyebrow-side": which,
            "state": r.args['state'].lower()
        }

@eyebrows_api.route("/led/<which>", methods=["GET"])
@alog.function_counter("get_eyebrows_led")
def get_eyebrows_led(which: str):
    """
    * *GET*: `/eyebrows/led/<which>` where `<which>` is `left` or `right`.
        * *Parameters*:
            * `artie-id`: The Artie ID.
    * *Response 200*:
        * *Payload (JSON)*:
            ```json
            {
                "artie-id": "The Artie ID.",
                "eyebrow-side": "left or right",
                "state": "on, off, or heartbeat"
            }
            ```
    """
    which = which.lower()

    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "error": "Missing artie-id parameter."
        }
        return errbody, 400
    elif which not in ('left', 'right'):
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": "Need either 'left' or 'right'"
        }
        return errbody, 404

    err, state_or_errmsg = eyebrows.get_led(which, artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": f"{state_or_errmsg}"
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id'],
            "eyebrow-side": which,
            "state": r.args['state'].lower()
        }

@eyebrows_api.route("/servo/<which>", methods=["POST"])
@alog.function_counter("set_eyebrows_servo")
def set_eyebrows_servo(which: str):
    """
    * *POST*: `/eyebrows/servo/<which>` where `<which>` is `left` or `right`.
        * *Parameters*:
            * `artie-id`: The Artie ID.
            * `degrees`: The position to go to. Should be a degree (float) value within the closed range [0, 180]. 0 degrees is left. 180 degrees is right. 90 degrees is center.
        * *Payload*: None
    """
    which = which.lower()

    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "degrees": r.args.get('degrees', 'Unknown'),
            "error": "Missing artie-id parameter."
        }
        return errbody, 400
    elif which not in ('left', 'right'):
        errbody = {
            "artie-id": r.args['artie-id'],
            "degrees": r.args.get('degrees', 'Unknown'),
            "error": "Need either 'left' or 'right'"
        }
        return errbody, 404
    elif 'degrees' not in r.args:
        errbody = {
            "artie-id": r.args['artie-id'],
            "degrees": "Unknown",
            "error": "Missing 'degrees' parameter."
        }
        return errbody, 400

    try:
        degrees = float(r.args['degrees'])
    except TypeError:
        errbody = {
            "artie-id": r.args['artie-id'],
            "degrees": r.args['degrees'],
            "error": "Cannot interpret 'degrees' parameter as a float."
        }
        return errbody, 400

    if degrees < 0.0 or degrees > 180.0:
        errbody = {
            "artie-id": r.args['artie-id'],
            "degrees": r.args['degrees'],
            "error": "'degrees' must be in the range [0, 180]."
        }
        return errbody, 400

    err, errmsg = eyebrows.set_servo(which, degrees, artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "degrees": r.args['degrees'],
            "error": f"{errmsg}"
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id'],
            "eyebrow-side": which,
            "degrees": r.args['degrees']
        }

@eyebrows_api.route("/servo/<which>", methods=["GET"])
@alog.function_counter("get_eyebrows_servo")
def get_eyebrows_servo(which: str):
    """
    Note: there is no way to get a *true* servo position for the eyeballs
    (at least in this version of Artie). The servos do not have
    encoders that can be accessed. Instead, eye position should be
    inferred by a higher layer that makes use of field of view
    changes. This GET request simply returns the value that
    the eyebrow driver *believes* the servo is currently at,
    which will typically be the value that it was last set to (or its starting value).

    * *GET*: `/eyebrows/servo/<which>` where `<which>` is `left` or `right`.
        * *Parameters*:
            * `artie-id`: The Artie ID.
    * *Response 200*:
        * *Payload (JSON)*:
            ```json
            {
                "artie-id": "The Artie ID.",
                "eyebrow-side": "left or right",
                "degrees": "floating point value between 0 (left) and 180 (right)"
            }
            ```
    """
    which = which.lower()

    # Double check params
    if 'artie-id' not in r.args:
        errbody = {
            "artie-id": "Unknown",
            "error": "Missing artie-id parameter."
        }
        return errbody, 400
    elif which not in ('left', 'right'):
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": "Need either 'left' or 'right'"
        }
        return errbody, 404

    err, errmsg_or_degrees = eyebrows.get_servo(which, artie_id=r.args['artie-id'])
    if err:
        errbody = {
            "artie-id": r.args['artie-id'],
            "error": f"{errmsg_or_degrees}"
        }
        return errbody, err
    else:
        return {
            "artie-id": r.args['artie-id'],
            "eyebrow-side": which,
            "degrees": f"{errmsg_or_degrees}"
        }

@eyebrows_api.route("/fw", methods=["POST"])
@alog.function_counter("reload_eyebrows_firmware")
def reload_eyebrows_firmware():
    """
    Reload both eyebrow MCU firmwares (you cannot target them individually).

    * *POST*: `/eyebrows/fw`
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

    err, errmsg = eyebrows.reload_firmware(artie_id=r.args['artie-id'])
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

@eyebrows_api.route("/status", methods=["GET"])
@alog.function_counter("get_eyebrows_status")
def get_eyebrows_status():
    """
    Get the eyebrows' submodules' statuses.

    * *GET*: `/eyebrows/status`
        * *Parameters*:
            * `artie-id`: The Artie ID.
    * *Response 200*:
        * *Payload (JSON)*:
            ```json
            {
                "artie-id": "The Artie ID.",
                "FW": "<Status>",
                "LED-LEFT": "<Status>",
                "LED-RIGHT": "<Status>",
                "LCD-LEFT": "<Status>",
                "LCD-RIGHT": "<Status>",
                "LEFT-SERVO": "<Status>",
                "RIGHT-SERVO": "<Status>"
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

    err, status_or_errmsg = eyebrows.get_status(artie_id=r.args['artie-id'])
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

@eyebrows_api.route("/self-test", methods=["POST"])
@alog.function_counter("eyebrows_self_test")
def mouth_self_test():
    """
    Initiate a self-test.

    * *POST*: `/eyebrows/self-test`
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

    err, errmsg = eyebrows.self_test(artie_id=r.args['artie-id'])
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
