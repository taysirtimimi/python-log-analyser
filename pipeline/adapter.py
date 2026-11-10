"""Adaptateur de lecture, parsing et enrichissement des logs SSH.

Les modules ingestion/ et process/ restent inchanges. Cet adaptateur lit les
fichiers individuellement pour pouvoir journaliser une erreur et continuer
avec les autres fichiers.
"""

import gzip
import ipaddress
import logging
import re
import zlib
from pathlib import Path
from typing import Iterator

from process import geolocation

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False

# Le logger central est configure au moment de l'import du module.
try:
    from logger_config import get_logger

    logger = get_logger(__name__)
except (ImportError, OSError, RuntimeError):
    # Le fallback garde le module utilisable pour les tests isoles.
    logger = logging.getLogger(__name__)


TIMESTAMP_PATTERN = re.compile(
    r"^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+"
)
REPEATED_PATTERN = re.compile(
    r"message repeated\s+(\d+)\s+times:\s*\[\s*(.*?)\s*\]\s*$",
    re.IGNORECASE,
)
ACCEPTED_PATTERN = re.compile(
    r"Accepted\s+(?:password|publickey)\s+for\s+(\S+)\s+from\s+([0-9a-fA-F:.]+)",
    re.IGNORECASE,
)
FAILED_PATTERN = re.compile(
    r"Failed\s+(?:password|publickey|keyboard-interactive(?:/pam)?)\s+for\s+"
    r"(?:(?:invalid)\s+user\s+)?(\S+)\s+from\s+([0-9a-fA-F:.]+)",
    re.IGNORECASE,
)
INVALID_USER_PATTERN = re.compile(
    r"Invalid\s+user\s*(.*?)\s+from\s+([0-9a-fA-F:.]+)",
    re.IGNORECASE,
)
INVALID_CONNECTION_PATTERN = re.compile(
    r"(?:Connection\s+closed\s+by|Disconnected\s+from)\s+invalid\s+user\s*"
    r"(.*?)\s+([0-9a-fA-F:.]+)\s+port\s+\d+",
    re.IGNORECASE,
)


class SSHLogAdapter:
    """Lit les logs, extrait les authentifications et enrichit les IP.

    Args:
        data_dir: Dossier contenant auth.log et ses rotations.
        event_store: Instance de storage.EventStore.
        batch_size: Nombre d'evenements inseres par lot.
    """

    def __init__(self, data_dir: str | Path, event_store, batch_size: int = 1000) -> None:
        self.data_dir = Path(data_dir)
        self.event_store = event_store
        self.batch_size = batch_size
        self.geo_cache: dict[str, str] = {}

        if self.batch_size < 1:
            raise ValueError("batch_size doit etre superieur a zero")

    def _read_file(self, file_path: Path) -> Iterator[tuple[str, str]]:
        """Lit un fichier texte ou gzip sans interrompre les autres fichiers."""
        opener = gzip.open if file_path.suffix == ".gz" else open

        try:
            with opener(file_path, mode="rt", encoding="utf-8") as file:
                for line_number, line in enumerate(file, start=1):
                    yield line.rstrip("\r\n"), f"{file_path.name}:{line_number}"
        except FileNotFoundError:
            logger.exception("Fichier introuvable: %s", file_path)
        except PermissionError:
            logger.exception("Permission refusee pour le fichier: %s", file_path)
        except (gzip.BadGzipFile, EOFError, zlib.error):
            logger.exception("Fichier gzip corrompu: %s", file_path)
        except UnicodeDecodeError:
            logger.exception("Encodage UTF-8 invalide dans: %s", file_path)
        except OSError:
            logger.exception("Erreur de lecture du fichier: %s", file_path)

    def read_all_rows(self) -> Iterator[tuple[str, str]]:
        """Parcourt tous les fichiers du dossier data, y compris les .gz."""
        try:
            if not self.data_dir.exists():
                raise FileNotFoundError(f"Dossier de logs introuvable: {self.data_dir}")
            if not self.data_dir.is_dir():
                raise NotADirectoryError(f"Le chemin n'est pas un dossier: {self.data_dir}")

            files = sorted(path for path in self.data_dir.iterdir() if path.is_file())
            if not files:
                logger.warning("Aucun fichier de log dans %s", self.data_dir)

            for file_path in files:
                yield from self._read_file(file_path)
        except PermissionError:
            logger.exception("Permission refusee pour le dossier: %s", self.data_dir)
            raise
        except (FileNotFoundError, NotADirectoryError):
            logger.exception("Dossier de logs inaccessible: %s", self.data_dir)
            raise
        except OSError:
            logger.exception("Impossible de parcourir le dossier: %s", self.data_dir)
            raise

    @staticmethod
    def _make_event(timestamp: str, message: str) -> dict[str, str] | None:
        """Convertit un message SSH d'authentification en evenement."""
        accepted = ACCEPTED_PATTERN.search(message)
        if accepted:
            return {
                "timestamp": timestamp,
                "ip": accepted.group(2),
                "username": accepted.group(1),
                "status": "Success",
                "country": "Unknown",
                "message": message.strip(),
            }

        invalid_connection = INVALID_CONNECTION_PATTERN.search(message)
        if invalid_connection:
            username = invalid_connection.group(1).strip() or "Unknown"
            return {
                "timestamp": timestamp,
                "ip": invalid_connection.group(2),
                "username": username,
                "status": "Invalid",
                "country": "Unknown",
                "message": message.strip(),
            }

        invalid_user = INVALID_USER_PATTERN.search(message)
        if invalid_user:
            username = invalid_user.group(1).strip() or "Unknown"
            return {
                "timestamp": timestamp,
                "ip": invalid_user.group(2),
                "username": username,
                "status": "Invalid",
                "country": "Unknown",
                "message": message.strip(),
            }

        failed = FAILED_PATTERN.search(message)
        if failed:
            username = failed.group(1)
            status = "Invalid" if "invalid user" in message.lower() else "Failed"
            return {
                "timestamp": timestamp,
                "ip": failed.group(2),
                "username": username,
                "status": status,
                "country": "Unknown",
                "message": message.strip(),
            }

        return None

    def parse_row(self, row: str, source: str = "unknown") -> list[dict[str, str]]:
        """Parse une ligne; une ligne repetee produit N evenements."""
        timestamp_match = TIMESTAMP_PATTERN.search(row)
        if not timestamp_match:
            if "sshd" in row.lower() and any(
                word in row.lower()
                for word in ("failed password", "invalid user", "accepted password", "accepted publickey", "message repeated")
            ):
                logger.warning("Ligne SSH non parsable (%s): %s", source, row[:250])
            return []

        timestamp = timestamp_match.group(1)
        repeated_match = REPEATED_PATTERN.search(row)
        if repeated_match:
            repeat_count = int(repeated_match.group(1))
            repeated_message = repeated_match.group(2)
            event = self._make_event(timestamp, repeated_message)
            if event is None:
                logger.warning("Message repete non reconnu (%s): %s", source, row[:250])
                return []
            logger.info("Message SSH repete %d fois (%s)", repeat_count, source)
            return [event.copy() for _ in range(repeat_count)]

        message_start = row.find(":", timestamp_match.end())
        message = row[message_start + 1:].strip() if message_start >= 0 else row[timestamp_match.end():].strip()
        event = self._make_event(timestamp, message)

        if event is None and "sshd" in row.lower() and any(
            word in row.lower()
            for word in ("failed password", "invalid user", "accepted password", "accepted publickey")
        ):
            logger.warning("Ligne SSH non reconnue (%s): %s", source, row[:250])
            return []

        return [event] if event else []

    def _get_country(self, ip: str) -> str:
        """Retourne le pays d'une IP avec cache et gestion des IP non publiques."""
        if ip in self.geo_cache:
            return self.geo_cache[ip]

        try:
            address = ipaddress.ip_address(ip)
        except ValueError:
            logger.warning("Adresse IP invalide: %s", ip)
            self.geo_cache[ip] = "Unknown"
            return "Unknown"

        if address.is_private or address.is_loopback or address.is_link_local:
            self.geo_cache[ip] = "Private/Local"
            return "Private/Local"

        if not address.is_global:
            logger.warning("Adresse IP non publique ou reservee: %s", ip)
            self.geo_cache[ip] = "Unknown"
            return "Unknown"

        try:
            result = geolocation.get_location(ip)
            if not result:
                logger.error("ipinfo n'a retourne aucun resultat pour %s (HTTP non-200 ou reponse vide)", ip)
                country = "Unknown"
            elif not isinstance(result, dict) or not result.get("country"):
                logger.warning("Pays absent de la reponse ipinfo pour %s", ip)
                country = "Unknown"
            else:
                country = str(result["country"])
        except Exception:
            # Le module existant peut lever plusieurs exceptions requests/json.
            # On les journalise ici sans modifier process/geolocation.py.
            logger.exception("Erreur ipinfo pendant la geolocalisation de %s", ip)
            country = "Unknown"

        self.geo_cache[ip] = country
        return country

    def run(self, geolocate: bool = True) -> dict[str, int]:
        """Analyse tous les fichiers et insere les evenements dans SQLite.

        geolocate=False est utile pour les tests hors ligne.
        """
        logger.info("Demarrage du pipeline; dossier=%s", self.data_dir)
        parsed_count = 0
        inserted_count = 0
        batch: list[dict[str, str]] = []
        unique_ips: set[str] = set()

        for row, source in self.read_all_rows():
            events = self.parse_row(row, source)
            for event in events:
                ip = event["ip"]
                unique_ips.add(ip)
                if geolocate:
                    event["country"] = self._get_country(ip)
                else:
                    event["country"] = "Unknown"

                batch.append(event)
                parsed_count += 1

                if len(batch) >= self.batch_size:
                    inserted_count += self.event_store.insert_events(batch)
                    batch = []

        if batch:
            inserted_count += self.event_store.insert_events(batch)

        summary = {
            "parsed_events": parsed_count,
            "inserted_events": inserted_count,
            "unique_ips": len(unique_ips),
            "geolocated_ips": len(self.geo_cache),
        }
        logger.info(
            "Pipeline termine: parsed=%d inserted=%d unique_ips=%d cache_ips=%d",
            parsed_count,
            inserted_count,
            len(unique_ips),
            len(self.geo_cache),
        )
        return summary
