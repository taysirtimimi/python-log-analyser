
# SSH Log Analyser

## 1. Présentation du projet

SSH Log Analyser est un projet Python qui permet d'analyser les fichiers de logs SSH afin de détecter les tentatives de connexion réussies et échouées.

Le projet traite les fichiers texte et compressés (.gz), extrait les événements SSH, les stocke dans une base de données SQLite et génère des graphiques statistiques.

## 2. Objectifs

- Lire plusieurs fichiers de logs SSH.
- Détecter les connexions réussies.
- Détecter les mots de passe incorrects.
- Détecter les utilisateurs invalides.
- Extraire les adresses IP et les noms d'utilisateurs.
- Géolocaliser les adresses IP publiques avec IPinfo.
- Stocker les événements dans SQLite.
- Générer des graphiques avec Matplotlib.
- Enregistrer les informations d'exécution dans des fichiers logs.

## 3. Architecture du projet

```text
python-log-analyser/
│
├── data/
│   └── Fichiers auth.log
│
├── ingestion/
│   └── raw.py
│
├── process/
│   ├── extract_transforme.py
│   ├── geolocation.py
│   └── main.py
│
├── pipeline/
│   └── adapter.py
│
├── storage/
│   └── event_store.py
│
├── serving/
│   ├── dashboard.py
│   └── graphs/
│
├── logs/
├── logger_config.py
├── main.py
├── pyproject.toml
├── uv.lock
├── .gitignore
└── README.md
```

## 4. Technologies utilisées

- Python
- SQLite
- Matplotlib
- Requests
- IPinfo
- uv

## 5. Fonctionnement

Le projet suit plusieurs étapes :

1. Lecture des fichiers SSH dans le dossier `data/`.
2. Extraction des informations importantes des lignes de logs.
3. Identification du type d'événement : Success, Failed ou Invalid.
4. Extraction de l'adresse IP et du nom d'utilisateur.
5. Géolocalisation des IP publiques avec IPinfo lorsque cette option est activée.
6. Enregistrement des événements dans SQLite.
7. Génération des graphiques statistiques.

## 6. Installation

Cloner le projet :

```bash
git clone https://github.com/taysirtimimi/python-log-analyser.git
cd python-log-analyser
```

Installer les dépendances :

```bash
uv sync
```

## 7. Exécution

Lancer le programme :

```bash
uv run python main.py
```

La base de données est créée dans :

```text
storage/events.db
```

Les graphiques sont générés dans :

```text
serving/graphs/
```

## 8. Graphiques générés

Trois graphiques sont produits :

- `failed_by_country.png` : tentatives échouées par pays.
- `successful_by_username.png` : connexions réussies par utilisateur.
- `invalid_users_top.png` : principaux utilisateurs invalides.

## 9. Journalisation

Le projet utilise le module `logging` de Python.

Chaque module dispose de son propre fichier de journalisation dans le dossier `logs/`.

Les fichiers utilisent une rotation afin de limiter leur taille.

Format :

```text
date|niveau|module|message
```

## 10. Stockage

Les événements sont enregistrés dans une base SQLite.

Chaque événement contient notamment :

- Timestamp
- Adresse IP
- Nom d'utilisateur
- Statut
- Pays
- Message SSH

## 11. Limites connues

- La géolocalisation dépend du service externe IPinfo.
- Les IP privées et locales ne peuvent pas être géolocalisées comme des IP publiques.
- La géolocalisation peut être désactivée pour éviter les appels externes.
- Les résultats dépendent du contenu et du format des fichiers SSH fournis.

## 12. Améliorations futures

- Ajouter un tableau de bord interactif.
- Ajouter des filtres par date et par adresse IP.
- Améliorer la détection des comportements suspects.
- Ajouter des alertes en cas d'activité inhabituelle.
