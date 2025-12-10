"""
Logs API for querying Artie logs from Fluent Bit

# TODO: There needs to be a database (probably PostgreSQL).
#       Fluentbit pushes logs into the database.
#       A dedicated database server allows this file to query logs from the database.
#       In the future, we will be using Kafka to pub/sub. The database server will subscribe and ingest sensor data
#       and serve that data via a similar API to the one we use for the logs.
"""
from artie_util import artie_logging as alog
import flask
import requests
import os
import json
import glob
from datetime import datetime, timedelta

logs_api = flask.Blueprint('logs', __name__, url_prefix='/logs')

# Configuration
LOG_COLLECTOR_HOST = os.environ.get('LOG_COLLECTOR_HOST', 'log-collector')
LOG_COLLECTOR_PORT = int(os.environ.get('LOG_COLLECTOR_PORT', '2020'))
LOG_FILE_PATH = os.environ.get('LOG_FILE_PATH', '/data/logs')


@logs_api.route('/live', methods=['GET'])
def get_live_logs():
    """
    Get live logs from the last N seconds.
    Query parameters:
        - seconds: Number of seconds to look back (default: 60)
        - level: Filter by log level (optional)
        - service: Filter by service name (optional)
    """
    try:
        seconds = int(flask.request.args.get('seconds', 60))
        level = flask.request.args.get('level')
        service = flask.request.args.get('service')
        
        # Read log files from the past N seconds
        cutoff_time = datetime.now() - timedelta(seconds=seconds)
        logs = []
        
        # Find all log files
        log_files = sorted(glob.glob(f"{LOG_FILE_PATH}/*.log"))
        
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line.strip())
                            
                            # Parse timestamp
                            timestamp_str = log_entry.get('timestamp', log_entry.get('date'))
                            if timestamp_str:
                                log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                if log_time < cutoff_time:
                                    continue
                            
                            # Apply filters
                            if level and log_entry.get('level') != level:
                                continue
                            if service and log_entry.get('service') != service:
                                continue
                            
                            logs.append(log_entry)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                alog.warning(f"Error reading log file {log_file}: {e}")
                continue
        
        # Sort by timestamp
        logs.sort(key=lambda x: x.get('timestamp', x.get('date', '')))
        
        return flask.jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs)
        }), 200
        
    except Exception as e:
        alog.error(f"Error retrieving live logs: {e}")
        return flask.jsonify({
            'success': False,
            'error': str(e)
        }), 500


@logs_api.route('/query', methods=['POST'])
def query_logs():
    """
    Query logs with various filters.
    JSON body parameters:
        - start_time: ISO 8601 timestamp (optional)
        - end_time: ISO 8601 timestamp (optional)
        - level: Log level filter (optional)
        - service: Service name filter (optional)
        - message_contains: Search string in message (optional)
        - limit: Maximum number of results (default: 1000)
    """
    try:
        data = flask.request.get_json()
        
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        level = data.get('level')
        service = data.get('service')
        message_contains = data.get('message_contains')
        limit = int(data.get('limit', 1000))
        
        # Parse timestamps
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00')) if start_time else None
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00')) if end_time else None
        
        logs = []
        log_files = sorted(glob.glob(f"{LOG_FILE_PATH}/*.log"))
        
        for log_file in log_files:
            if len(logs) >= limit:
                break
                
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        if len(logs) >= limit:
                            break
                            
                        try:
                            log_entry = json.loads(line.strip())
                            
                            # Apply timestamp filters
                            timestamp_str = log_entry.get('timestamp', log_entry.get('date'))
                            if timestamp_str:
                                log_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                                if start_dt and log_time < start_dt:
                                    continue
                                if end_dt and log_time > end_dt:
                                    continue
                            
                            # Apply other filters
                            if level and log_entry.get('level') != level:
                                continue
                            if service and log_entry.get('service') != service:
                                continue
                            if message_contains and message_contains not in log_entry.get('message', ''):
                                continue
                            
                            logs.append(log_entry)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                alog.warning(f"Error reading log file {log_file}: {e}")
                continue
        
        # Sort by timestamp
        logs.sort(key=lambda x: x.get('timestamp', x.get('date', '')))
        
        return flask.jsonify({
            'success': True,
            'logs': logs,
            'count': len(logs),
            'truncated': len(logs) >= limit
        }), 200
        
    except Exception as e:
        alog.error(f"Error querying logs: {e}")
        return flask.jsonify({
            'success': False,
            'error': str(e)
        }), 500


@logs_api.route('/services', methods=['GET'])
def get_services():
    """Get list of all services that have logged data."""
    try:
        services = set()
        log_files = glob.glob(f"{LOG_FILE_PATH}/*.log")
        
        for log_file in log_files:
            try:
                with open(log_file, 'r') as f:
                    for line in f:
                        try:
                            log_entry = json.loads(line.strip())
                            if 'service' in log_entry:
                                services.add(log_entry['service'])
                        except json.JSONDecodeError:
                            continue
            except Exception:
                continue
        
        return flask.jsonify({
            'success': True,
            'services': sorted(list(services))
        }), 200
        
    except Exception as e:
        alog.error(f"Error getting services: {e}")
        return flask.jsonify({
            'success': False,
            'error': str(e)
        }), 500
