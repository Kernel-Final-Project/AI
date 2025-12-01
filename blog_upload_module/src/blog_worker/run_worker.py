"""
CLI entrypoint to start the RabbitMQ consumer.
"""
from __future__ import annotations

import argparse

from .rabbit_consumer import run_consumer


def main() -> None:
    parser = argparse.ArgumentParser(description="Blog upload RabbitMQ worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Reserved for future use (currently runs continuous consumer).",
    )
    parser.parse_args()
    run_consumer()


if __name__ == "__main__":
    main()
