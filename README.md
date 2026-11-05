# Tournament Matchup Generator – Multi-Sport Knockout Management System

A beginner-friendly Flask application for managing multi-sport knockout tournaments. Modules 1 and 2 provide the Flask/SQLite foundation and responsive dashboard. Module 3 adds tournament CRUD. Module 4 adds team registration, roster management, scoped duplicate protection, and team/player detail views.

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
│   ├── models.py         # Tournament, Team, Player, and Match models
│   ├── routes.py         # Dashboard, tournament, team, player, and placeholder routes
│   ├── static/           # Responsive CSS and vanilla JavaScript
│   └── templates/        # Management, detail, form, and dashboard templates
├── instance/             # Local SQLite database (created at runtime)
├── tests/                # Foundation, dashboard, tournament, team, and player tests
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

The database is stored at `instance/tournament.db`. It is intentionally not browser localStorage. The application applies safe additive upgrades to older databases by adding new columns when needed. Module 4 adds `teams.captain_name`, `teams.logo_url`, and `players.position` without recreating or erasing existing data.

## Run the application

```bash
flask --app run.py run --debug
```

Open <http://127.0.0.1:5000/> in a browser. The home route is the dashboard. Alternatively, run `python run.py`.

## Team and player management

Use **Teams** in the sidebar to register teams under existing tournaments, search by team name, filter by tournament, edit team details, and delete teams with confirmation. Team names are unique within a tournament but can be reused in another tournament.

Use **Players** to register players under teams, optionally assign jersey numbers and positions, edit or delete players, and view team/tournament associations. Jersey numbers are unique within each team when provided. Team deletion cascades to its players; existing matches retain their tournament record with deleted team references cleared.

## Run tests

```bash
pytest
```
