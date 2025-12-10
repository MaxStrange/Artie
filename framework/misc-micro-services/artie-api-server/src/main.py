from artie_util import artie_logging as alog
from artie_util import util
from drivers import reset_api
from drivers import mouth_api
from drivers import eyebrows_api
from telemetry import logs_api
from telemetry import metrics_api
import argparse
import flask

# Set up logging
parser = argparse.ArgumentParser()
parser.add_argument("--ipv6", action='store_true', help="Use IPv6 if given, otherwise IPv4.")
parser.add_argument("-l", "--loglevel", type=str, default="info", choices=["debug", "info", "warning", "error"], help="The log level.")
args, _ = parser.parse_known_args()
alog.init("artie-api-server", args)

# Generate our self-signed certificate (if not already present)
certfpath = "/etc/cert.pem"
keyfpath = "/etc/pkey.pem"
util.generate_self_signed_cert(certfpath, keyfpath, days=None, force=True)

# Initialization
app = flask.Flask(__name__)
app.register_blueprint(reset_api.reset_api)
app.register_blueprint(mouth_api.mouth_api)
app.register_blueprint(eyebrows_api.eyebrows_api)
app.register_blueprint(logs_api.logs_api)
app.register_blueprint(metrics_api.metrics_api)
