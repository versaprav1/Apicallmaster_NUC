import sys
import time
import argparse
from typing import Optional
import requests
import os


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call local LLM generate endpoint")
    default_host = os.environ.get("OLLAMA_HOST", "http://192.168.2.64:11434")
    default_url = f"{default_host.rstrip('/')}/api/generate"
    parser.add_argument("--url", default=default_url, help="Full generate endpoint URL")
    parser.add_argument(
        "--model",
        default="llama3.2",
        help="Model to use",
    )
    parser.add_argument(
        "--prompt",
        default="Why is the sky blue?",
        help="Prompt text (use quotes)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Request timeout in seconds",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="Number of retry attempts on failure",
    )
    return parser.parse_args()


def post_with_retries(
    url: str, json_payload: dict, timeout_s: float, retries: int
) -> Optional[requests.Response]:
    last_exc: Optional[Exception] = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            response = requests.post(url, json=json_payload, timeout=timeout_s)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                backoff = min(5.0, 0.5 * (2 ** (attempt - 1)))
                print(
                    f"Attempt {attempt} failed: {exc}. Retrying in {backoff:.1f}s...",
                    file=sys.stderr,
                )
                time.sleep(backoff)
    if last_exc is not None:
        print(f"Request failed: {last_exc}", file=sys.stderr)
    return None


def main() -> None:
    args = parse_args()
    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "stream": False,
    }

    response = post_with_retries(
        url=args.url, json_payload=payload, timeout_s=args.timeout, retries=args.retries
    )
    if response is None:
        sys.exit(1)

    try:
        data = response.json()
    except ValueError:
        print(response.text)
        return

    output = data.get("response", data)
    print(output)


if __name__ == "__main__":
    main()