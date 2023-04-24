import requests

if __name__ == "__main__":
    r = requests.get("http://localhost:9090/api/v1/query?query=reset_driver_reset_driver_functions_reset_target_calls_total")
    try:
        for metric in r.json()['data']['result']:
            if metric['value']:
                print("Test Passed", flush=True)
                exit(0)
    except KeyError:
        print(f"Invalid response: {r}", flush=True)
