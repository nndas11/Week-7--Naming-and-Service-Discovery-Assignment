import argparse
import json
import random
import time
from typing import Optional

import requests

from registry_client import RegistryClient


def call_random_instance(
    client: RegistryClient,
    service: str,
    path: str,
    method: str,
    payload: Optional[dict],
    headers: Optional[dict],
    retries: int,
) -> Optional[requests.Response]:
    for attempt in range(retries):
        instances = client.discover(service)
        if not instances:
            time.sleep(1 + attempt)
            continue

        random.shuffle(instances)
        for instance in instances:
            base = instance.get("address", "").rstrip("/")
            if not base:
                continue
            url = f"{base}{path}"
            try:
                response = requests.request(method, url, json=payload, headers=headers, timeout=3)
                if response.status_code < 500:
                    return response
            except requests.exceptions.RequestException:
                continue

        time.sleep(1 + attempt)
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Client that discovers and calls a random instance")
    parser.add_argument("service", help="Service name to discover")
    parser.add_argument("path", help="Path to call, e.g. /cart/user-1")
    parser.add_argument("--method", default="GET")
    parser.add_argument("--json", default=None, help="JSON payload for POST/PUT")
    parser.add_argument("--registry", default="http://localhost:5001")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--idempotency-key", default=None)
    args = parser.parse_args()

    payload = None
    if args.json:
        payload = json.loads(args.json)

    headers = None
    if args.idempotency_key:
        headers = {"Idempotency-Key": args.idempotency_key}

    client = RegistryClient(registry_url=args.registry)
    response = call_random_instance(
        client=client,
        service=args.service,
        path=args.path,
        method=args.method.upper(),
        payload=payload,
        headers=headers,
        retries=args.retries,
    )

    if not response:
        print("No healthy instances available after retries.")
        raise SystemExit(1)

    print(f"Called {response.url} -> {response.status_code}")
    print(response.text)


if __name__ == "__main__":
    main()
