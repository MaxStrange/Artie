"""
Artie API Server client for communicating with the Artie API Server
"""
import requests
import json
from typing import Optional, Dict, Any, List
from model import artie_profile


class ArtieApiClient:
    """Client for communicating with the Artie API Server"""
    
    def __init__(self, profile: artie_profile.ArtieProfile):
        """
        Initialize the API client.
        
        Args:
            profile: The Artie profile containing connection information
        """
        # TODO: The controller_node_ip isn't what we use for ArtieApiClient. We need to use the IP of the node that
        #       is running the API server, which may be the controller node, but may not be, particularly in the future.
        #       Not sure how we do that with Kubernetes. Presumably there is some way of doing DNS.
        # TODO: Get rid of the hard-coded port on the self.base_url below. It should be stored in the ArtieProfile.
        #       Additionally, we should update the settings dialog to allow users to change the API server port if needed,
        #       which means adding a tab for settings that are specific to particular Artie installations.
        # TODO: During Artie installation, we already ask for a username and password for the controller node.
        #       We save those credentials in the Artie profile (using Windows Credential Manager / macOS Keychain / Linux
        #       Secret Service or whatever).
        #       We should use those credentials here to authenticate with the API server.
        #       We should also support token-based authentication for programmatic access to the cluster,
        #       such as if we ever want to set up CI/CD pipelines that interact with a self-hosted Artie.
        # TODO: We need to handle certificate verification properly. During the installation procedure,
        #       we need to retrieve the self-signed certificate from the API server and store it securely.
        #       We need to make sure we use it here and that we make sure (presumably using the requests library) it is the only one that we trust.
        self.profile = profile
        self.base_url = f"https://{profile.controller_node_ip}:8782"
        self.session = requests.Session()
        self.session.verify = False
        
    def _make_request(self, method: str, endpoint: str, **kwargs) -> tuple[Optional[Exception], Optional[Dict]]:
        """
        Make an HTTP request to the API server.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Tuple of (error, response_data)
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.request(method, url, **kwargs)
            
            if response.status_code >= 400:
                return Exception(f"HTTP {response.status_code}: {response.text}"), None
            
            try:
                data = response.json()
                return None, data
            except json.JSONDecodeError:
                return None, {'raw': response.text}
                
        except requests.exceptions.RequestException as e:
            return e, None
    
    # ========== Logs API ==========
    
    def get_live_logs(self, seconds: int = 60, level: Optional[str] = None, 
                     service: Optional[str] = None) -> tuple[Optional[Exception], Optional[Dict]]:
        """
        Get live logs from the last N seconds.
        
        Args:
            seconds: Number of seconds to look back
            level: Filter by log level
            service: Filter by service name
            
        Returns:
            Tuple of (error, response_data)
        """
        params = {'seconds': seconds}
        if level:
            params['level'] = level
        if service:
            params['service'] = service
            
        return self._make_request('GET', '/logs/live', params=params)
    
    def query_logs(self, start_time: Optional[str] = None, end_time: Optional[str] = None,
                   level: Optional[str] = None, service: Optional[str] = None,
                   message_contains: Optional[str] = None, 
                   limit: int = 1000) -> tuple[Optional[Exception], Optional[Dict]]:
        """
        Query logs with various filters.
        
        Args:
            start_time: ISO 8601 timestamp
            end_time: ISO 8601 timestamp
            level: Log level filter
            service: Service name filter
            message_contains: Search string in message
            limit: Maximum number of results
            
        Returns:
            Tuple of (error, response_data)
        """
        data = {'limit': limit}
        if start_time:
            data['start_time'] = start_time
        if end_time:
            data['end_time'] = end_time
        if level:
            data['level'] = level
        if service:
            data['service'] = service
        if message_contains:
            data['message_contains'] = message_contains
            
        return self._make_request('POST', '/logs/query', json=data)
    
    def get_log_services(self) -> tuple[Optional[Exception], Optional[List[str]]]:
        """
        Get list of all services that have logged data.
        
        Returns:
            Tuple of (error, list_of_services)
        """
        err, data = self._make_request('GET', '/logs/services')
        if err:
            return err, None
        return None, data.get('services', []) if data.get('success') else []
    
    # ========== Metrics API ==========
    
    def query_metrics(self, query: str, time: Optional[str] = None) -> tuple[Optional[Exception], Optional[Dict]]:
        """
        Query Prometheus for instant metrics values.
        
        Args:
            query: PromQL query string
            time: Evaluation timestamp
            
        Returns:
            Tuple of (error, response_data)
        """
        params = {'query': query}
        if time:
            params['time'] = time
            
        return self._make_request('GET', '/metrics/query', params=params)
    
    def query_range_metrics(self, query: str, start: str, end: str, 
                           step: str = '15s') -> tuple[Optional[Exception], Optional[Dict]]:
        """
        Query Prometheus for range metrics values.
        
        Args:
            query: PromQL query string
            start: Start timestamp
            end: End timestamp
            step: Query resolution step width
            
        Returns:
            Tuple of (error, response_data)
        """
        params = {
            'query': query,
            'start': start,
            'end': end,
            'step': step
        }
        
        return self._make_request('GET', '/metrics/query_range', params=params)
    
    def get_metric_labels(self, matches: Optional[List[str]] = None,
                         start: Optional[str] = None, 
                         end: Optional[str] = None) -> tuple[Optional[Exception], Optional[List[str]]]:
        """
        Get list of label names.
        
        Args:
            matches: Series selectors to match
            start: Start timestamp
            end: End timestamp
            
        Returns:
            Tuple of (error, list_of_labels)
        """
        params = {}
        if matches:
            params['match[]'] = matches
        if start:
            params['start'] = start
        if end:
            params['end'] = end
            
        err, data = self._make_request('GET', '/metrics/labels', params=params)
        if err:
            return err, None
        
        # Extract labels from Prometheus response format
        if data.get('success') and 'data' in data:
            prometheus_data = data['data']
            if isinstance(prometheus_data, dict) and 'data' in prometheus_data:
                return None, prometheus_data['data']
        return None, []
    
    def get_label_values(self, label_name: str, matches: Optional[List[str]] = None,
                        start: Optional[str] = None, 
                        end: Optional[str] = None) -> tuple[Optional[Exception], Optional[List[str]]]:
        """
        Get list of label values for a specific label name.
        
        Args:
            label_name: Label name to get values for
            matches: Series selectors to match
            start: Start timestamp
            end: End timestamp
            
        Returns:
            Tuple of (error, list_of_values)
        """
        params = {}
        if matches:
            params['match[]'] = matches
        if start:
            params['start'] = start
        if end:
            params['end'] = end
            
        err, data = self._make_request('GET', f'/metrics/label/{label_name}/values', params=params)
        if err:
            return err, None
        
        # Extract values from Prometheus response format
        if data.get('success') and 'data' in data:
            prometheus_data = data['data']
            if isinstance(prometheus_data, dict) and 'data' in prometheus_data:
                return None, prometheus_data['data']
        return None, []
    
    def get_metric_series(self, matches: List[str], start: Optional[str] = None,
                         end: Optional[str] = None) -> tuple[Optional[Exception], Optional[List[Dict]]]:
        """
        Get list of time series that match a label set.
        
        Args:
            matches: Series selectors to match (required)
            start: Start timestamp
            end: End timestamp
            
        Returns:
            Tuple of (error, list_of_series)
        """
        params = {'match[]': matches}
        if start:
            params['start'] = start
        if end:
            params['end'] = end
            
        err, data = self._make_request('GET', '/metrics/series', params=params)
        if err:
            return err, None
        
        # Extract series from Prometheus response format
        if data.get('success') and 'data' in data:
            prometheus_data = data['data']
            if isinstance(prometheus_data, dict) and 'data' in prometheus_data:
                return None, prometheus_data['data']
        return None, []
    
    def get_metric_targets(self) -> tuple[Optional[Exception], Optional[Dict]]:
        """
        Get current state of target discovery.
        
        Returns:
            Tuple of (error, targets_data)
        """
        return self._make_request('GET', '/metrics/targets')
