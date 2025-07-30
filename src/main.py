import argparse
import os
import requests
import structlog
import sys
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
from structlog import get_logger

# Configure structlog for basic logging (optional)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ]
)

log = get_logger()


load_dotenv()

API_USER = os.getenv("API_USER")
API_KEY = os.getenv("API_KEY")
CLIENT_IP = os.getenv("CLIENT_IP")
NAMESPACE = "{http://api.namecheap.com/xml.response}"
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
URL = "https://api.namecheap.com/xml.response"
VALID_RECORD_TYPES = [
    "A",
    "AAAA",
    "CNAME",
    "MX",
    "TXT"
]


def get_records_by_type(record_type):
    if record_type not in VALID_RECORD_TYPES:
        log.critical("Invalid record type to search")
        sys.exit(1)

    params = {
        "ApiUser": API_USER,
        "ApiKey": API_KEY,
        "UserName": API_USER,
        "Command": "namecheap.domains.dns.getHosts",
        "SLD": SLD,
        "TLD": TLD,
        "ClientIP": CLIENT_IP
    }

    response = requests.get(URL, params=params)

    if response.status_code == 200:
        root = ET.fromstring(response.content)
        found_records = []
        for host in root.findall(f".//{NAMESPACE}host"):
            if host.attrib["Type"] == record_type:
                record = {
                    "name": host.attrib["Name"],
                    "value": host.attrib["Address"]
                }
                found_records.append(record)
        if found_records is None:
            log.warn(f"No {record_type} records were found")
        else:
            for record in found_records:
                log.info("Found record", record=record)
            return found_records
    else:
        log.warn(f"Failed to retrieve DNS records: {response.status_code} - {response.text}")

    return None


def get_all_records():
    params = {
        "ApiUser": API_USER,
        "ApiKey": API_KEY,
        "UserName": API_USER,
        "Command": "namecheap.domains.dns.getHosts",
        "SLD": SLD,
        "TLD": TLD,
        "ClientIP": CLIENT_IP
    }

    response = requests.get(URL, params=params)

    if response.status_code == 200:
        root = ET.fromstring(response.content)
        found_records = []
        for host in root.findall(f".//{NAMESPACE}host"):
            record = {
                "name": host.attrib["Name"],
                "value": host.attrib["Address"],
                "type": host.attrib["Type"]
            }
            found_records.append(record)
        if found_records is None:
            log.warn("No records were found")
        else:
            for record in found_records:
                log.info("Found record", record=record)
            return found_records
    else:
        log.warn(f"Failed to retrieve DNS records: {response.status_code} - {response.text}")

    return None


def run():
    if args.record_type:
        get_records_by_type(args.record_type)
    else:
        get_all_records()
    log.info("Execution complete")


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
        "-r",
        "--use_redis",
        action="store_true",
        help="If you wish to store the results of a query in Redis, use this flag. "
             "Redis info is populated from the .env file"
    )
    parser.add_argument(
        "-t",
        "--record_type",
        action="store",
        help="Type of record to query the zone for. "
             "If this is not set, all record types will be returned"
    )

    args = parser.parse_args()
    SLD = args.domain.split(".")[0]
    TLD = args.domain.split(".")[1]
    log.info(f"Querying Namecheap for {args.domain}")
    run()
