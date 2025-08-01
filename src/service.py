import argparse
import logging
import os
import structlog
import sys
import time

from dotenv import load_dotenv
from namecheap import Namecheap
from structlog import get_logger


structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ]
)
log = get_logger()
load_dotenv()

API_USER = os.getenv("API_USER")
API_KEY = os.getenv("API_KEY")
CLIENT_IP = os.getenv("CLIENT_IP")
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")


def validate_environment():
    if API_USER is None or API_KEY is None or CLIENT_IP is None:
        log.critical(
            "Confirm the .env file has been populated.",
            API_USER=API_USER,
            API_KEY=API_KEY,
            CLIENT_IP=CLIENT_IP
        )
        sys.exit(1)


def run():
    validate_environment()
    namecheap = Namecheap(API_USER, API_KEY, CLIENT_IP, REDIS_HOST, REDIS_PORT, args.domain)

    while True:
        records = namecheap.get_records_by_type("TXT")
        namecheap.send_to_redis(records)
        namecheap.check_validation_status()
        time.sleep(300)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A utility for interacting with the Namecheap API service"
    )
    parser.add_argument(
        "-d",
        "--domain",
        action="store",
        required=True,
        help="The domain you wish to query within Namecheap"
    )
    parser.add_argument(
        "-v",
        "--debug",
        action="store_true",
        help="Enables debug logging"
    )
    args = parser.parse_args()
    if args.debug:
        structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),)
    else:
        structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),)

    log.info(f"Querying Namecheap for {args.domain}")
    run()
