
from pathlib import Path

from logger_config import get_logger
from storage import EventStore
from pipeline.adapter import SSHLogAdapter
from serving.dashboard import generate_dashboard


# Chemin principal du projet
BASE_DIR = Path(__file__).resolve().parent

# Chemins des fichiers
DATA_DIR = BASE_DIR / "data"
DB_PATH = BASE_DIR / "storage" / "events.db"
GRAPHS_DIR = BASE_DIR / "serving" / "graphs"

logger = get_logger(__name__)


def main():
    logger.info("Demarrage du projet Log Analyser")

    # 1. Initialiser la base de donnees
    store = EventStore(DB_PATH)

    # 2. Analyser les fichiers uniquement si la base est vide
    if store.get_event_count() == 0:
        adapter = SSHLogAdapter(
            data_dir=DATA_DIR,
            event_store=store
        )

        summary = adapter.run(geolocate=False)

        logger.info("Resultat du pipeline : %s", summary)
    else:
        logger.warning(
            "La base contient deja %d evenements. "
            "Analyse ignoree pour eviter les doublons.",
            store.get_event_count()
        )

    # 3. Generer les graphiques
    generate_dashboard(
        db_path=DB_PATH,
        output_dir=GRAPHS_DIR
    )

    logger.info("Projet termine avec succes")


if __name__ == "__main__":
    main()
