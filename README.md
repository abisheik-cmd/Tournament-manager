# Tournament Matchup Generator – Multi-Sport Knockout Management System

A beginner-friendly Flask application for managing multi-sport knockout tournaments. Modules 1 and 2 provide the Flask/SQLite foundation and responsive dashboard. Module 3 adds tournament CRUD. Module 4 adds team registration and roster management. Module 5 adds randomized, persistent single-elimination fixture generation with BYEs and a visual bracket.

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
│   ├── __init__.py       # Application factory and safe additive schema upgrades
│   ├── extensions.py     # Shared SQLAlchemy extension
│   ├── fixture_engine.py # Randomized single-elimination bracket generation
│   ├── models.py         # Tournament, Team, Player, and Match models
│   ├── routes.py         # Dashboard, CRUD, fixture, and placeholder routes
│   ├── static/           # Responsive CSS and vanilla JavaScript
│   └── templates/        # Management, detail, form, dashboard, and bracket templates
├── instance/             # Local SQLite database (created at runtime)
├── tests/                # Full application and fixture-engine tests
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

The database is stored at `instance/tournament.db`. It is intentionally not browser localStorage. The application applies safe additive upgrades to older databases by adding new columns when needed. Module 5 adds round metadata, status, BYE, and next-match fields to the existing `matches` table without recreating or erasing data.

## Run the application

```bash
flask --app run.py run --debug
```

Open <http://127.0.0.1:5000/> in a browser. The home route is the dashboard. Alternatively, run `python run.py`.

## Fixture generation

Open **Match Fixtures** in the sidebar and select an existing tournament. The application displays its registered team count and allows generation only when there are 2–64 teams and no existing fixtures. Generation uses Python's `random` module, shuffles teams, chooses the next power-of-two bracket size, distributes required BYEs across randomized first-round slots, and stores every round in SQLite. BYE winners are assigned immediately and every match has a `next_match_id` progression reference. Generation is protected by a confirmation dialog and cannot silently overwrite an existing bracket.

The bracket is horizontally scrollable on smaller screens and renders actual database Match records in round columns.

## Run tests

```bash
pytest
```
