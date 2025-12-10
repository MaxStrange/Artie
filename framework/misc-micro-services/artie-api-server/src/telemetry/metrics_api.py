"""
Metrics API for querying Prometheus metrics
"""
from artie_util import artie_logging as alog
import flask
import requests
import os

metrics_api = flask.Blueprint('metrics', __name__, url_prefix='/metrics')

# Configuration
METRICS_COLLECTOR_HOST = os.environ.get('METRICS_COLLECTOR_HOST', 'metrics-collector')
METRICS_COLLECTOR_PORT = int(os.environ.get('METRICS_COLLECTOR_PORT', '8090'))
PROMETHEUS_BASE_URL = f"http://{METRICS_COLLECTOR_HOST}:{METRICS_COLLECTOR_PORT}"


@metrics_api.route('/query', methods=['GET'])
def query_metrics():
    """
    Query Prometheus for instant metrics values.
    Query parameters:
        - query: PromQL query string (required)
        - time: Evaluation timestamp (optional, RFC3339 or Unix timestamp)
    """
    try:
        query = flask.request.args.get('query')
        if not query:
            return flask.jsonify({
                'success': False,
                'error': 'Query parameter is required'
            }), 400
        
        time = flask.request.args.get('time')
        
        params = {'query': query}
        if time:
            params['time'] = time
        
        response = requests.get(
            f"{PROMETHEUS_BASE_URL}/api/v1/query",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            return flask.jsonify({
                'success': True,
                'data': response.json()
            }), 200
        else:
            return flask.jsonify({
                'success': False,
                'error': f"Prometheus returned status {response.status_code}",
                'details': response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        alog.error(f"Error querying Prometheus: {e}")
        return flask.jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_api.route('/query_range', methods=['GET'])
def query_range_metrics():
    """
    Query Prometheus for range metrics values.
    Query parameters:
        - query: PromQL query string (required)
        - start: Start timestamp (required, RFC3339 or Unix timestamp)
        - end: End timestamp (required, RFC3339 or Unix timestamp)
        - step: Query resolution step width (optional, duration string or float seconds)
    """
    try:
        query = flask.request.args.get('query')
        start = flask.request.args.get('start')
        end = flask.request.args.get('end')
        
        if not query or not start or not end:
            return flask.jsonify({
                'success': False,
                'error': 'Query, start, and end parameters are required'
            }), 400
        
        step = flask.request.args.get('step', '15s')
        
        params = {
            'query': query,
            'start': start,
            'end': end,
            'step': step
        }
        
        response = requests.get(
            f"{PROMETHEUS_BASE_URL}/api/v1/query_range",
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return flask.jsonify({
                'success': True,
                'data': response.json()
            }), 200
        else:
            return flask.jsonify({
                'success': False,
                'error': f"Prometheus returned status {response.status_code}",
                'details': response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        alog.error(f"Error querying Prometheus range: {e}")
        return flask.jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_api.route('/labels', methods=['GET'])
def get_labels():
    """
    Get list of label names.
    Query parameters:
        - match[]: Series selector to match (optional, can be repeated)
        - start: Start timestamp (optional)
        - end: End timestamp (optional)
    """
    try:
        params = {}
        
        # Handle multiple match[] parameters
        matches = flask.request.args.getlist('match[]')
        if matches:
            params['match[]'] = matches
        
        start = flask.request.args.get('start')
        if start:
            params['start'] = start
            
        end = flask.request.args.get('end')
        if end:
            params['end'] = end
        
        response = requests.get(
            f"{PROMETHEUS_BASE_URL}/api/v1/labels",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            return flask.jsonify({
                'success': True,
                'data': response.json()
            }), 200
        else:
            return flask.jsonify({
                'success': False,
                'error': f"Prometheus returned status {response.status_code}",
                'details': response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        alog.error(f"Error getting labels: {e}")
        return flask.jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_api.route('/label/<label_name>/values', methods=['GET'])
def get_label_values(label_name):
    """
    Get list of label values for a specific label name.
    Query parameters:
        - match[]: Series selector to match (optional, can be repeated)
        - start: Start timestamp (optional)
        - end: End timestamp (optional)
    """
    try:
        params = {}
        
        matches = flask.request.args.getlist('match[]')
        if matches:
            params['match[]'] = matches
        
        start = flask.request.args.get('start')
        if start:
            params['start'] = start
            
        end = flask.request.args.get('end')
        if end:
            params['end'] = end
        
        response = requests.get(
            f"{PROMETHEUS_BASE_URL}/api/v1/label/{label_name}/values",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            return flask.jsonify({
                'success': True,
                'data': response.json()
            }), 200
        else:
            return flask.jsonify({
                'success': False,
                'error': f"Prometheus returned status {response.status_code}",
                'details': response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        alog.error(f"Error getting label values: {e}")
        return flask.jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_api.route('/series', methods=['GET'])
def get_series():
    """
    Get list of time series that match a label set.
    Query parameters:
        - match[]: Series selector to match (required, can be repeated)
        - start: Start timestamp (optional)
        - end: End timestamp (optional)
    """
    try:
        matches = flask.request.args.getlist('match[]')
        if not matches:
            return flask.jsonify({
                'success': False,
                'error': 'At least one match[] parameter is required'
            }), 400
        
        params = {'match[]': matches}
        
        start = flask.request.args.get('start')
        if start:
            params['start'] = start
            
        end = flask.request.args.get('end')
        if end:
            params['end'] = end
        
        response = requests.get(
            f"{PROMETHEUS_BASE_URL}/api/v1/series",
            params=params,
            timeout=10
        )
        
        if response.status_code == 200:
            return flask.jsonify({
                'success': True,
                'data': response.json()
            }), 200
        else:
            return flask.jsonify({
                'success': False,
                'error': f"Prometheus returned status {response.status_code}",
                'details': response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        alog.error(f"Error getting series: {e}")
        return flask.jsonify({
            'success': False,
            'error': str(e)
        }), 500


@metrics_api.route('/targets', methods=['GET'])
def get_targets():
    """Get current state of target discovery."""
    try:
        response = requests.get(
            f"{PROMETHEUS_BASE_URL}/api/v1/targets",
            timeout=10
        )
        
        if response.status_code == 200:
            return flask.jsonify({
                'success': True,
                'data': response.json()
            }), 200
        else:
            return flask.jsonify({
                'success': False,
                'error': f"Prometheus returned status {response.status_code}",
                'details': response.text
            }), response.status_code
            
    except requests.exceptions.RequestException as e:
        alog.error(f"Error getting targets: {e}")
        return flask.jsonify({
            'success': False,
            'error': str(e)
        }), 500
