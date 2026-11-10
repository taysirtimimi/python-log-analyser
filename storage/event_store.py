"""Stockage SQLite des evenements d'authentification SSH."""

import sqlite3
from pathlib import Path

from logger_config import get_logger


logger = get_logger(__name__)


class EventStore:
    """Enregistre et lit les evenements SSH dans une base SQLite."""

    def __init__(self, db_path: str | Path = "storage/events.db") -> None:
        self.db_path = Path(db_path)

        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.create_table()
            logger.info("EventStore initialise: %s", self.db_path)
        except (OSError, sqlite3.Error):
            logger.exception("Impossible d'initialiser le stockage SQLite")
            raise

    def create_table(self) -> None:
        """Cree la table des evenements si elle n'existe pas."""
        connection = None

        try:
            connection = sqlite3.connect(self.db_path)
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        ip TEXT NOT NULL,
                        username TEXT NOT NULL,
                        status TEXT NOT NULL
                            CHECK (status IN ('Success', 'Failed', 'Invalid')),
                        country TEXT NOT NULL DEFAULT 'Unknown',
                        message TEXT NOT NULL DEFAULT ''
                    )
                    """
                )
            logger.info("Table events verifiee ou creee")
        except sqlite3.Error:
            logger.exception("Erreur lors de la creation de la table events")
            raise
        finally:
            if connection is not None:
                connection.close()

    def insert_event(
        self,
        timestamp: str,
        ip: str,
        username: str,
        status: str,
        country: str = "Unknown",
        message: str = "",
    ) -> None:
        """Insere un evenement d'authentification."""
        connection = None

        try:
            connection = sqlite3.connect(self.db_path)
            with connection:
                connection.execute(
                    """
                    INSERT INTO events
                    (timestamp, ip, username, status, country, message)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (timestamp, ip, username, status, country, message),
                )
            logger.info("Evenement enregistre: status=%s, ip=%s", status, ip)
        except sqlite3.Error:
            logger.exception("Erreur SQLite pendant l'insertion d'un evenement")
            raise
        finally:
            if connection is not None:
                connection.close()

    def insert_events(self, events: list[dict[str, str]]) -> int:
        """Insere plusieurs evenements et retourne le nombre insere."""
        connection = None

        try:
            values = [
                (
                    event["timestamp"],
                    event["ip"],
                    event["username"],
                    event["status"],
                    event.get("country", "Unknown"),
                    event.get("message", ""),
                )
                for event in events
            ]

            connection = sqlite3.connect(self.db_path)
            with connection:
                connection.executemany(
                    """
                    INSERT INTO events
                    (timestamp, ip, username, status, country, message)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )

            inserted_count = len(values)
            logger.info("%d evenement(s) enregistre(s)", inserted_count)
            return inserted_count
        except (sqlite3.Error, KeyError, TypeError):
            logger.exception("Erreur pendant l'insertion de plusieurs evenements")
            raise
        finally:
            if connection is not None:
                connection.close()

    def get_all_events(self) -> list[dict[str, object]]:
        """Retourne tous les evenements sous forme de dictionnaires."""
        connection = None

        try:
            connection = sqlite3.connect(self.db_path)
            connection.row_factory = sqlite3.Row
            cursor = connection.execute(
                """
                SELECT id, timestamp, ip, username, status, country, message
                FROM events
                ORDER BY id
                """
            )
            events = [dict(row) for row in cursor.fetchall()]
            logger.info("%d evenement(s) recupere(s)", len(events))
            return events
        except sqlite3.Error:
            logger.exception("Erreur SQLite pendant la lecture des evenements")
            raise
        finally:
            if connection is not None:
                connection.close()
    def update_countries(self, countries: dict[str, str]) -> int:
        """Met a jour le pays des evenements a partir de leur adresse IP."""
        connection = None

        try:
            values = [
                (country, ip)
                for ip, country in countries.items()
                if country and country != "Unknown"
            ]

            connection = sqlite3.connect(self.db_path)

            with connection:
                cursor = connection.executemany(
                    """
                    UPDATE events
                    SET country = ?
                    WHERE ip = ? AND country = 'Unknown'
                    """,
                    values,
                )

            updated_count = cursor.rowcount
            logger.info("%d evenement(s) enrichi(s) avec leur pays", updated_count)
            return updated_count

        except sqlite3.Error:
            logger.exception("Erreur SQLite pendant la mise a jour des pays")
            raise

        finally:
            if connection is not None:
                connection.close()
    def get_event_count(self) -> int:
        """Retourne le nombre total d'evenements stockes."""
        connection = None

        try:
            connection = sqlite3.connect(self.db_path)
            cursor = connection.execute("SELECT COUNT(*) FROM events")
            result = cursor.fetchone()
            return int(result[0]) if result is not None else 0
        except sqlite3.Error:
            logger.exception("Erreur SQLite pendant le comptage des evenements")
            raise
        finally:
            if connection is not None:
                connection.close()
