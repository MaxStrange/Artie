"""
Logging API client for communicating with the API Server's logging endpoints.

Each `*Response` object corresponds to the response from a specific API endpoint.

See [API documentation](../../../../../misc-micro-services/artie-api-server/README.md) for more details.
"""
from . import api_client
from .. import errors
import dataclasses
import datetime
import enum

class LogLevel(enum.StrEnum):
    """Log levels supported by the API."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

class LogEntry:
    """A single log entry."""
    timestamp: str
    """The timestamp of the log entry."""

    level: LogLevel
    """The log level (e.g., DEBUG, INFO, WARNING, ERROR)."""

    service: str
    """The service that generated the log."""

    process: str
    """The process name."""

    thread: str
    """The thread name."""

    message: str
    """The log message."""

@dataclasses.dataclass
class RecentLogsResponse:
    """Response object for recent logs API call."""
    artie_id: str
    """The Artie ID."""

    seconds: int
    """Number of seconds the logs cover."""

    level: LogLevel|None
    """Log level filter applied."""

    process: str|None
    """Process name filter applied."""

    thread: str|None
    """Thread name filter applied."""

    service: str|None
    """Service name filter applied."""

    logs: list[LogEntry]
    """List of log entries."""

@dataclasses.dataclass
class QueryLogsResponse:
    """Response object for query logs API call."""
    artie_id: str
    """The Artie ID."""

    limit: int|None
    """Maximum number of log entries returned."""

    starttime: datetime.datetime|None
    """Start time filter applied."""

    endtime: datetime.datetime|None
    """End time filter applied."""

    message_contains: str|None
    """Message substring filter applied."""

    level: LogLevel|None
    """Log level filter applied."""

    process: str|None
    """Process name filter applied."""

    thread: str|None
    """Thread name filter applied."""

    service: str|None
    """Service name filter applied."""

@dataclasses.dataclass
class ListServicesResponse:
    """Response object for listing services API call."""
    artie_id: str
    """The Artie ID."""

    services: list[str]
    """List of service names."""


class LoggingClient(api_client.APIClient):
    """Client for interacting with the Logging API endpoints."""

    def get_recent_logs(self, seconds: int, level: LogLevel|None = None, process: str|None = None, thread: str|None = None, service: str|None = None) -> errors.HTTPError|RecentLogsResponse:
        """
        Get recent logs from the API server.

        Args:
            seconds: Number of seconds to look back for logs.
            level: Optional log level filter.
            process: Optional process name filter.
            thread: Optional thread name filter.
            service: Optional service name filter.

        Returns:
            RecentLogsResponse object containing the logs.
        """
        params = {
            'artie-id': self.artie.artie_name,
            'seconds': seconds,
            'level': level.value if level is not None else LogLevel.DEBUG.value,
            'process': process if process is not None else '*',
            'thread': thread if thread is not None else '*',
            'service': service if service is not None else '*'
        }

        response = self.get('/logs/recent', params=params)
        if response.status_code == 200:
            data = response.json()
            logs = []
            for log_entry in data.get('logs', []):
                logs.append(LogEntry(
                    timestamp=datetime.datetime.strptime(log_entry['timestamp'], "%Y-%m-%d %H:%M:%S"),
                    level=LogLevel(log_entry['level']),
                    service=log_entry['service'] if log_entry['service'] != "*" else None,
                    process=log_entry['process'] if log_entry['process'] != "*" else None,
                    thread=log_entry['thread'] if log_entry['thread'] != "*" else None,
                    message=log_entry['message']
                ))

            return RecentLogsResponse(
                artie_id=data['artie_id'],
                seconds=data['seconds'],
                level=LogLevel(data['level']) if data.get('level') else None,
                process=data.get('process') if data.get('process') != "*" else None,
                thread=data.get('thread') if data.get('thread') != "*" else None,
                service=data.get('service') if data.get('service') != "*" else None,
                logs=logs
            )
        else:
            return errors.APIClientError(f"Failed to get recent logs: {response.status_code} {response.text}")

    def query_logs(self, limit: int|None = None, starttime: datetime.datetime|None = None, endtime: datetime.datetime|None = None, message_contains: str|None = None, level: LogLevel|None = None, process: str|None = None, thread: str|None = None, service: str|None = None) -> errors.HTTPError|QueryLogsResponse:
        """
        Query logs from the API server with various filters.

        Args:
            limit: Maximum number of log entries to return.
            starttime: Start time filter.
            endtime: End time filter.
            message_contains: Substring that must be in the log message.
            level: Log level filter.
            process: Process name filter.
            thread: Thread name filter.
            service: Service name filter.

        Returns:
            QueryLogsResponse object containing the logs.

        """
        params = {
            'artie-id': self.artie.artie_name,
            'limit': limit if limit is not None else -1,
            'starttime': starttime.strftime("%Y-%m-%d %H:%M:%S") if starttime is not None else '*',
            'endtime': endtime.strftime("%Y-%m-%d %H:%M:%S") if endtime is not None else '*',
            'messagecontains': message_contains if message_contains is not None else '.*',
            'level': level.value if level is not None else '*',
            'process': process if process is not None else '*',
            'thread': thread if thread is not None else '*',
            'service': service if service is not None else '*'
        }

        response = self.get('/logs/query', params=params)
        if response.status_code == 200:
            data = response.json()
            logs = []
            for log_entry in data.get('logs', []):
                logs.append(LogEntry(
                    timestamp=datetime.datetime.strptime(log_entry['timestamp'], "%Y-%m-%d %H:%M:%S"),
                    level=LogLevel(log_entry['level']),
                    service=log_entry['service'] if log_entry['service'] != "*" else None,
                    process=log_entry['process'] if log_entry['process'] != "*" else None,
                    thread=log_entry['thread'] if log_entry['thread'] != "*" else None,
                    message=log_entry['message']
                ))

            return QueryLogsResponse(
                artie_id=data['artie_id'],
                limit=data.get('limit') if data.get('limit') != -1 else None,
                starttime=datetime.datetime.strptime(data['start_time'], "%Y-%m-%d %H:%M:%S") if data.get('start_time') else None,
                endtime=datetime.datetime.strptime(data['end_time'], "%Y-%m-%d %H:%M:%S") if data.get('end_time') else None,
                message_contains=data.get('message_contains') if data.get('message_contains') != ".*" else None,
                level=LogLevel(data['level']) if data.get('level') else None,
                process=data.get('process') if data.get('process') != "*" else None,
                thread=data.get('thread') if data.get('thread') != "*" else None,
                service=data.get('service') if data.get('service') != "*" else None,
                logs=logs
            )
        else:
            return errors.APIClientError(f"Failed to query logs: {response.status_code} {response.text}")

    def list_services(self) -> errors.HTTPError|ListServicesResponse:
        """
        List all services that have logged messages.

        Returns:
            ListServicesResponse object containing the service names.
        """
        params = {
            'artie-id': self.artie.artie_name
        }

        response = self.get('/logs/services', params=params)
        if response.status_code == 200:
            data = response.json()
            return ListServicesResponse(
                artie_id=data['artie_id'],
                services=data.get('services', [])
            )
        else:
            return errors.APIClientError(f"Failed to list services: {response.status_code} {response.text}")
