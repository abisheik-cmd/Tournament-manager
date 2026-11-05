# Tournament Matchup Generator – Multi-Sport Knockout Management System

A beginner-friendly Flask foundation for managing multi-sport knockout tournaments. The current version focuses on the application structure, SQLite persistence, and core data models; matchup generation and full management workflows will be added later.

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
│   ├── __init__.py       # Application factory and database CLI command
│   ├── extensions.py     # Shared SQLAlchemy extension
│   ├── models.py         # Tournament, Team, Player, and Match models
│   ├── routes.py         # Web routes
│   ├── static/           # CSS and vanilla JavaScript
│   └── templates/        # Jinja templates
├── instance/             # Local SQLite database (created at runtime)
├── tests/                # Foundation tests
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

The database is stored at `instance/tournament.db`. It is intentionally not browser localStorage.

## Run the application

```bash
flask --app run.py run --debug
```

Open <http://127.0.0.1:5000/> in a browser. Alternatively, run `python run.py`.

## Run tests

```bash
pytest
```
