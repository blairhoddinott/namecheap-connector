import json
import redis
import requests
import sys
import xml.etree.ElementTree as ET

from structlog import get_logger


log = get_logger()


class Namecheap():
    VALID_RECORD_TYPES = [
        "A",
        "AAAA",
        "CNAME",
        "MX",
        "TXT"
    ]
    NAMESPACE = "{http://api.namecheap.com/xml.response}"
    URL = "https://api.namecheap.com/xml.response"

    def __init__(self, api_user, api_key, client_ip, redis_host, redis_port, domain):
        self.API_USER = api_user
        self.API_KEY = api_key
        self.CLIENT_IP = client_ip
        self.REDIS_HOST = redis_host
        self.REDIS_PORT = redis_port
        self.REDIS_KEY = "dns_update"
        self.REDIS_VALIDATION_KEY = "validation_complete"
        self.SLD, self.TLD = domain.split(".")

    def _is_redis_key_set(self, record):
        r = redis.Redis(self.REDIS_HOST, self.REDIS_PORT, db=4)
        if r.exists(self.REDIS_KEY):
            try:
                redis_record = json.loads(r.get(self.REDIS_KEY))
                if redis_record == record:
                    log.debug("redis key already set", redis_record=redis_record, record=record)
                    return True
                else:
                    log.debug(
                        "redis key differs from provided record",
                        redis_record=redis_record,
                        record=record
                    )
                    return False
            except Exception as e:
                log.critical("Unable to get record from redis", exception=e)
                return False
        else:
            log.info("Redis key does not exist")
            return False

    def _get_record_from_redis(self):
        r = redis.Redis(self.REDIS_HOST, self.REDIS_PORT, db=4)
        if r.exists(self.REDIS_KEY):
            return r.get(self.REDIS_KEY)
        else:
            return None

    def get_records_by_type(self, record_type):
        if record_type not in self.VALID_RECORD_TYPES:
            log.critical("Invalid record type to search")
            sys.exit(1)

        params = {
            "ApiUser": self.API_USER,
            "ApiKey": self.API_KEY,
            "UserName": self.API_USER,
            "Command": "namecheap.domains.dns.getHosts",
            "SLD": self.SLD,
            "TLD": self.TLD,
            "ClientIP": self.CLIENT_IP
        }

        response = requests.get(self.URL, params=params)

        if response.status_code == 200:
            root = ET.fromstring(response.content)
            found_records = []
            for host in root.findall(f".//{self.NAMESPACE}host"):
                if host.attrib["Type"] == record_type:
                    record = {
                        "name": host.attrib["Name"],
                        "value": host.attrib["Address"],
                        "type": host.attrib["Type"]
                    }
                    found_records.append(record)
            if found_records is None:
                log.warn(f"No {record_type} records were found")
            else:
                for record in found_records:
                    log.info("Found record", record=record)
        else:
            log.warn(f"Failed to retrieve DNS records: {response.status_code} - {response.text}")

        record_dict = {
            "records": []
        }
        record_dict["records"].append(found_records)
        return record_dict

    def get_all_records(self):
        params = {
            "ApiUser": self.API_USER,
            "ApiKey": self.API_KEY,
            "UserName": self.API_USER,
            "Command": "namecheap.domains.dns.getHosts",
            "SLD": self.SLD,
            "TLD": self.TLD,
            "ClientIP": self.CLIENT_IP
        }

        response = requests.get(self.URL, params=params)

        if response.status_code == 200:
            root = ET.fromstring(response.content)
            found_records = []
            for host in root.findall(f".//{self.NAMESPACE}host"):
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
        else:
            log.warn(f"Failed to retrieve DNS records: {response.status_code} - {response.text}")

        record_dict = {
            "records": []
        }
        record_dict["records"].append(found_records)
        return record_dict

    def send_to_redis(self, record_dict):
        if record_dict["records"][0]:
            r = redis.Redis(host=self.REDIS_HOST, port=self.REDIS_PORT, db=4)
            existing_record = self._get_record_from_redis()
            if existing_record:
                if self._is_redis_key_set(record_dict):
                    log.debug("Redis key is already set")
                    return True

            json_string = json.dumps(record_dict)
            try:
                r.set(self.REDIS_KEY, json_string)
            except Exception as e:
                log.critical("Unable to send record to redis", exception=e)
                sys.exit(1)
            log.info("Sent records to Redis")

    def check_validation_status(self):
        r = redis.Redis(host=self.REDIS_HOST, port=self.REDIS_PORT, db=4)
        record = self._get_record_from_redis()
        if record:
            dns_records = self.get_records_by_type("TXT")
            if not dns_records["records"][0]:
                log.info("record still in redis, validation has completed")
                r.set(self.REDIS_VALIDATION_KEY, 1)
        else:
            log.debug(f"Redis key {self.REDIS_KEY} is not set")
