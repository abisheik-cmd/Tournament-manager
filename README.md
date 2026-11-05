# Tournament Matchup Generator – Multi-Sport Knockout Management System

A beginner-friendly Flask application for managing multi-sport knockout tournaments. Modules 1 and 2 provide the Flask/SQLite foundation and responsive dashboard. Module 3 adds tournament creation, search/filter listing, editing, deletion, and detailed views.

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
│   ├── routes.py         # Dashboard, tournament CRUD, filters, and placeholders
│   ├── static/           # Responsive CSS and vanilla JavaScript
│   └── templates/        # Dashboard, management, detail, and form templates
├── instance/             # Local SQLite database (created at runtime)
├── tests/                # Foundation, dashboard, and CRUD tests
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

The database is stored at `instance/tournament.db`. It is intentionally not browser localStorage. The application applies safe additive upgrades to older databases by adding new columns when needed.

## Run the application

```bash
flask --app run.py run --debug
```

Open <http://127.0.0.1:5000/> in a browser. The home route is the dashboard. Alternatively, run `python run.py`.

## Tournament management

Use **Tournaments** in the sidebar to create and manage records. Creation and editing validate the tournament name, sport, venue, date, and status on the backend; the HTML form also marks required fields for browser validation. Tournament listing supports name search plus sport and status filters. Deletion requires a browser confirmation and removes associated teams, players, and matches through SQLAlchemy cascade relationships inside a database transaction.

Supported sports are Football, Cricket, Basketball, Volleyball, Badminton, Tennis, and Other. Supported statuses are Upcoming, Active, and Completed.

## Run tests

```bash
pytest
```
