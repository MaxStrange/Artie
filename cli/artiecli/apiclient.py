"""
Base class for the various API clients.
"""
import kubernetes as k8s
import time
import requests


class APIClient:
    def __init__(self, args) -> None:
        # Determine Artie ID or error out
        self.artie_id = args.artie_id
        if self.artie_id is None:
            # We weren't given an ID. Check if we are in test mode.
            if args.integration_test or args.unit_test:
                # We are in test mode. We can use a dummy value.
                self.artie_id = 'test-artie'
            else:
                # We either aren't in test mode or we are in hardware test mode.
                # Either way, we need an Artie ID and we weren't given one.
                # Check if the cluster has only a single Artie. If so, we use that one.
                # Otherwise, error out.
                self.artie_id = self._get_artie_id_from_cluster(args)

        if args.integration_test or args.unit_test:
            # Determined by docker compose files
            self.ip_and_port = "artie-api-server:8782"
        else:
            # Determined by Helm chart
            self.ip_and_port = f"artie-api-server-{self.artie_id}:8782"

    def _get_artie_id_from_cluster(self, args) -> str:
        config_file = args.kube_config
        k8s.config.load_kube_config(config_file=config_file)
        v1 = k8s.client.CoreV1Api()
        pod_list = v1.list_namespaced_pod(namespace='artie').items
        ids = set([])
        for pod in pod_list:
            i = pod.metadata.labels.get('artie/artie-id', None)
            if i is not None:
                ids.add(i)
                if len(ids) > 1:
                    print(f"Error: Cannot infer Artie ID. Multiple IDs detected in cluster: {ids}. Please manually select an artie-id.")
                    exit(1)
        return ids.pop()

    def get(self, url: str, params=None, https=True):
        """
        Gets the content at the given URL (which should not include the IP or port)
        and returns it.
        """
        scheme = "https" if https else "http"
        uri = f"{scheme}://{self.ip_and_port}{url}"
        ntries = 3
        delay_s = 2
        for i in range(ntries):
            try:
                r = requests.get(uri, params=params, verify=False)
            except Exception as e:
                time.sleep(delay_s)
                if i == ntries - 1:
                    print(f"Error connecting: {e}")
                    raise e
        return r

    def post(self, url: str, body=None, params=None, https=True):
        """
        Post the given body to the given url with the given params.
        Does all the appropriate error handling and abstracts away
        boilerplate, which includes adding the appropriate IP and port
        to the URL (which should therefore not include that information).
        """
        scheme = "https" if https else "http"
        uri = f"{scheme}://{self.ip_and_port}{url}"
        ntries = 3
        delay_s = 2
        for i in range(ntries):
            try:
                r = requests.post(uri, json=body, params=params, verify=False)
            except Exception as e:
                time.sleep(delay_s)
                if i == ntries - 1:
                    print(f"Error connecting: {e}")
                    raise e
        return r
