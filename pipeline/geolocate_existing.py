import os
import sys
import sqlite3
import ipaddress
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

import requests
from dotenv import load_dotenv

from logger_config import get_logger
from storage.event_store import EventStore


PROJECT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_DIR / "storage" / "events.db"

load_dotenv(PROJECT_DIR / ".env")

TOKEN = os.getenv("IPINFO_TOKEN")

logger = get_logger(__name__)


def get_unknown_ips():
    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.execute(
            "SELECT DISTINCT ip FROM events WHERE country = 'Unknown'"
        )
        return [row[0] for row in cursor.fetchall()]
    finally:
        connection.close()


def get_country(ip):
    try:
        address = ipaddress.ip_address(ip)

        if not address.is_global:
            if address.is_private or address.is_loopback:
                return ip, "Private/Local"
            return ip, "Unknown"

        response = requests.get(
    "https://api.ipinfo.io/lite/" + ip,
    headers={"Authorization": "Bearer " + TOKEN},
    timeout=15
)

        response.raise_for_status()

        data = response.json()
        country = data.get("country")

        if country:
            return ip, country

        return ip, "Unknown"

    except (requests.RequestException, ValueError):
        logger.exception("Erreur de geolocalisation pour %s", ip)
        return ip, "Unknown"


def main():
    if not TOKEN:
        logger.error("Token IPINFO_TOKEN absent du fichier .env")
        return

    store = EventStore(DB_PATH)
    ips = get_unknown_ips()

    logger.info("%d adresses IP a geolocaliser", len(ips))

    countries = {}

    with ThreadPoolExecutor(max_workers=10) as executor:
        for index, (ip, country) in enumerate(
            executor.map(get_country, ips),
            start=1
        ):
            if country != "Unknown":
                countries[ip] = country

            if index % 100 == 0:
                logger.info("%d/%d adresses traitees", index, len(ips))

    updated = store.update_countries(countries)

    logger.info(
        "Geolocalisation terminee : %d IP avec pays, %d evenements mis a jour",
        len(countries),
        updated
    )


if __name__ == "__main__":
    main()
