
"""Generation des graphiques du dashboard SSH."""

from logger_config import get_logger
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from storage import EventStore


logger = get_logger(__name__)


def generate_dashboard(
    db_path="storage/pipeline_test.db",
    output_dir="serving/graphs",
    top_n=10,
):
    """Genere les trois graphiques a partir des evenements SQLite."""

    store = EventStore(db_path)
    events = store.get_all_events()

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 1. Tentatives echouees par pays
    failed_countries = Counter(
        event["country"]
        for event in events
        if event["status"] in ("Failed", "Invalid")
    )

    fig, ax = plt.subplots(figsize=(10, 6))

    if failed_countries:
        countries = failed_countries.most_common()
        names = [item[0] for item in countries]
        values = [item[1] for item in countries]

        ax.bar(names, values)
        ax.set_title("Failed attempts by country")
        ax.set_xlabel("Country")
        ax.set_ylabel("Number of attempts")
        ax.tick_params(axis="x", rotation=45)
    else:
        ax.text(0.5, 0.5, "No failed attempts", ha="center")

    fig.tight_layout()
    fig.savefig(output_path / "failed_by_country.png")
    plt.close(fig)

    # 2. Connexions reussies par utilisateur
    successful_users = Counter(
        event["username"]
        for event in events
        if event["status"] == "Success"
    )

    fig, ax = plt.subplots(figsize=(10, 6))

    if successful_users:
        users = successful_users.most_common()
        names = [item[0] for item in users]
        values = [item[1] for item in users]

        ax.bar(names, values)
        ax.set_title("Successful attempts by username")
        ax.set_xlabel("Username")
        ax.set_ylabel("Number of successful connections")
    else:
        ax.text(0.5, 0.5, "No successful connections", ha="center")

    fig.tight_layout()
    fig.savefig(output_path / "successful_by_username.png")
    plt.close(fig)

    # 3. Top N des utilisateurs invalides
    invalid_users = Counter(
        event["username"]
        for event in events
        if event["status"] == "Invalid"
    )

    fig, ax = plt.subplots(figsize=(10, 6))

    if invalid_users:
        users = invalid_users.most_common(top_n)
        names = [item[0] for item in users]
        values = [item[1] for item in users]

        ax.bar(names, values)
        ax.set_title(f"Top {top_n} invalid usernames")
        ax.set_xlabel("Username")
        ax.set_ylabel("Number of attempts")
        ax.tick_params(axis="x", rotation=45)
    else:
        ax.text(0.5, 0.5, "No invalid users", ha="center")

    fig.tight_layout()
    fig.savefig(output_path / "invalid_users_top.png")
    plt.close(fig)

    logger.info("Les trois graphiques ont ete generes dans %s", output_path)

    return {
        "failed_by_country": output_path / "failed_by_country.png",
        "successful_by_username": output_path / "successful_by_username.png",
        "invalid_users_top": output_path / "invalid_users_top.png",
    }
