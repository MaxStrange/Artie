from artie_util import artie_logging as alog
from artie_util import constants
from artie_util import util
import argparse
import flask
import os
import blueprints.api_server_api as api_server_api
import blueprints.logs_api as logs_api
import blueprints.metrics_api as metrics_api
import blueprints.api_interface_mcu as api_interface_mcu
import blueprints.api_interface_display as api_interface_display
import blueprints.api_interface_driver as api_interface_driver
import blueprints.api_interface_servo as api_interface_servo
import blueprints.api_interface_statusled as api_interface_statusled
import blueprints.api_interface_service as api_interface_service
import blueprints.api_interface_imu as api_interface_imu

# Initialization (must be at the top level for gunicorn to see it)
app = flask.Flask(__name__)
app.register_blueprint(api_server_api.api_server_api)
app.register_blueprint(logs_api.logs_api)
app.register_blueprint(metrics_api.metrics_api)
app.register_blueprint(api_interface_mcu.mcu_api)
app.register_blueprint(api_interface_display.display_api)
app.register_blueprint(api_interface_driver.driver_api)
app.register_blueprint(api_interface_servo.servo_api)
app.register_blueprint(api_interface_statusled.statusled_api)
app.register_blueprint(api_interface_service.service_api)
app.register_blueprint(api_interface_imu.imu_api)

# For local development/testing
if __name__ == "__main__":
    # Set up logging
    parser = argparse.ArgumentParser()
    parser.add_argument("--ipv6", action='store_true', help="Use IPv6 if given, otherwise IPv4.")
    parser.add_argument("-p", "--port", type=int, default=int(os.environ.get("PORT", 8782)), help="The port to run the server on.")
    parser.add_argument("--host", type=str, default=os.environ.get("HOST", "0.0.0.0"), help="The host to run the server on.")
    parser.add_argument("-l", "--loglevel", type=str, default=None, choices=["debug", "info", "warning", "error"], help="The log level.")
    args, _ = parser.parse_known_args()
    alog.init("artie-api-server", args)

    # We also have a cert for the API server itself to use for HTTPS.
    server_certfpath = "/etc/artie-api-server/certs/tls.crt"
    server_keyfpath = "/etc/artie-api-server/certs/tls.key"
    if util.mode() != constants.ArtieRunModes.PRODUCTION:
        util.generate_self_signed_cert(server_certfpath, server_keyfpath, days=None, force=True)

    # Run the server
    if args.ipv6:
        alog.info(f"Starting Artie API Server on IPv6 {args.host}:{args.port}")
        app.run(host=args.host, port=args.port, ssl_context=(server_certfpath, server_keyfpath), debug=(args.loglevel == "debug"), threaded=True)
    else:
        alog.info(f"Starting Artie API Server on IPv4 {args.host}:{args.port}")
        app.run(host=args.host, port=args.port, ssl_context=(server_certfpath, server_keyfpath), debug=(args.loglevel == "debug"), threaded=True)
