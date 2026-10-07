import argparse
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import (
    HTTPCookieProcessor,
    Request,
    build_opener,
)


def main():
    parser = argparse.ArgumentParser(
        description="Measure concurrent POST latency for the SafeSend risk API."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL of a running SafeSend instance.",
    )
    parser.add_argument(
        "--requests",
        nargs="+",
        type=int,
        default=[100, 500, 1000],
        help="Request counts to run (default: 100 500 1000).",
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args()

    if args.workers < 1 or args.timeout <= 0:
        parser.error("--workers and --timeout must be positive.")
    if any(count < 1 for count in args.requests):
        parser.error("Request counts must be positive integers.")

    opener = build_opener(HTTPCookieProcessor(CookieJar()))
    with opener.open(args.base_url.rstrip("/") + "/", timeout=args.timeout) as response:
        wallet_page = response.read().decode("utf-8")
    csrf_match = re.search(
        r'name="csrfmiddlewaretoken"\s+value="([^"]+)"',
        wallet_page,
    )
    if not csrf_match:
        raise RuntimeError("The wallet page did not provide a CSRF token.")
    csrf_token = csrf_match.group(1)

    def send_request(_index):
        payload = json.dumps(
            {
                "user_id": "U0001",
                "recipient_id": "01711223344",
                "amount": "1500.00",
                "hour": 14,
            }
        ).encode("utf-8")
        request = Request(
            args.base_url.rstrip("/") + "/api/risk/send-money/",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-CSRFToken": csrf_token,
            },
            method="POST",
        )
        started = time.perf_counter()
        try:
            with opener.open(request, timeout=args.timeout) as response:
                response.read()
                return response.status, time.perf_counter() - started
        except HTTPError as error:
            error.read()
            return error.code, time.perf_counter() - started
        except (URLError, TimeoutError):
            return 0, time.perf_counter() - started

    summaries = []
    for request_count in args.requests:
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            results = list(executor.map(send_request, range(request_count)))
        wall_time = time.perf_counter() - started
        successful = sum(code == 200 for code, _latency in results)
        latencies = [latency for _code, latency in results]
        summaries.append(
            {
                "requests": request_count,
                "workers": args.workers,
                "successful_requests": successful,
                "errors": request_count - successful,
                "average_response_ms": round(
                    sum(latencies) / len(latencies) * 1000,
                    2,
                ),
                "wall_time_seconds": round(wall_time, 2),
            }
        )

    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
