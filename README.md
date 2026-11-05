# Tournament Matchup Generator – Multi-Sport Knockout Management System

A beginner-friendly Flask foundation for managing multi-sport knockout tournaments. Module 2 adds a responsive dashboard with database-backed statistics, recent tournaments, quick actions, and navigation placeholders. Full matchup generation and management workflows will be added later.

## Technology

- Python 3.10+
- Flask
- Flask-SQLAlchemy / SQLAlchemy ORM
- SQLite
- HTML, CSS, and vanilla JavaScript

## Project structure

```text
.
├── app/
│   ├── __init__.py       # Application factory, schema compatibility, and CLI command
│   ├── extensions.py     # Shared SQLAlchemy extension
│   ├── models.py         # Tournament, Team, Player, and Match models
│   ├── routes.py         # Dashboard, tournament, and placeholder routes
│   ├── static/           # Responsive CSS and vanilla JavaScript
│   └── templates/        # Dashboard and page templates
├── instance/             # Local SQLite database (created at runtime)
├── tests/                # Foundation and dashboard tests
├── config.py             # Application configuration
├── requirements.txt      # Python dependencies
└── run.py                # Development entry point
```

## Setup

```bash
cd tournament-matchup-generator
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Initialize the database

The application creates the SQLite database and tables when the app is created. You can also run the explicit initialization command:

```bash
flask --app run.py init-db
```

The database is stored at `instance/tournament.db`. It is intentionally not browser localStorage. The application applies a safe additive upgrade to older Module 1 databases by adding the Tournament `status` column when needed.

## Run the application

```bash
flask --app run.py run --debug
```

Open <http://127.0.0.1:5000/> in a browser. The home route is the dashboard. Alternatively, run `python run.py`.

## Dashboard

The dashboard reads all statistics and recent tournament rows from SQLite through SQLAlchemy. It includes total, active, and completed tournament counts, total team count, a recent tournaments table, empty states, quick actions, responsive sidebar navigation, and clear placeholder pages for features planned for later modules.

## Run tests

```bash
pytest
```
