# Tournament Matchup Generator – Multi-Sport Knockout Management System

A beginner-friendly Flask application for managing multi-sport knockout tournaments. Modules 1 and 2 provide the Flask/SQLite foundation and responsive dashboard. Module 3 adds tournament CRUD. Module 4 adds team registration and roster management. Module 5 adds randomized, persistent single-elimination fixture generation with BYEs and a visual bracket. Module 6 adds score entry, tie resolution, automatic winner progression, match statuses, and tournament champions.

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
│   ├── result_engine.py  # Score validation and transactional progression
│   ├── routes.py         # Dashboard, CRUD, fixture, result, and placeholder routes
│   ├── static/           # Responsive CSS and vanilla JavaScript
│   └── templates/        # Management, detail, form, dashboard, and bracket templates
├── instance/             # Local SQLite database (created at runtime)
├── tests/                # Full application and fixture/result tests
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

The database is stored at `instance/tournament.db`. It is intentionally not browser localStorage. The application applies safe additive upgrades to older databases by adding new columns when needed. Module 5 adds bracket metadata to `matches`; Module 6 adds `matches.decided_by_tiebreaker` and `tournaments.champion_id` without recreating or erasing existing data.

## Run the application

```bash
flask --app run.py run --debug
```

Open <http://127.0.0.1:5000/> in a browser. The home route is the dashboard. Alternatively, run `python run.py`.

## Fixture generation

Open **Match Fixtures** in the sidebar and select an existing tournament. The application displays its registered team count and allows generation only when there are 2–64 teams and no existing fixtures. Generation uses Python's `random` module, shuffles teams, chooses the next power-of-two bracket size, distributes required BYEs across randomized first-round slots, and stores every round in SQLite. BYE winners are assigned immediately and automatically marked completed. Every match has a `next_match_id` progression reference. Generation is protected by a confirmation dialog and cannot silently overwrite an existing bracket.

The bracket is horizontally scrollable on smaller screens and renders actual database Match records in round columns. Match cards link to their detail pages.

## Match scoring and progression

Open a match card to enter non-negative whole-number scores. A higher score automatically determines the winner and advances that team into the correct slot in the next match. Matches waiting for teams are **Scheduled**; matches with both teams available are **Ready**; administrators can mark available matches **In Progress**; and a match becomes **Completed** only after a winner is confirmed.

Tied scores are never resolved randomly. The match remains unresolved and displays a tiebreaker interface where an administrator selects one of the two participating teams. The selection is recorded with `decided_by_tiebreaker`. BYE matches cannot receive scores. Completed results are locked to prevent downstream bracket corruption, and all result/progression updates run inside a database transaction.

When the final match is completed, the winner is stored as the tournament champion, the tournament status changes to **Completed**, and the champion appears on the tournament detail page and dashboard.

## Run tests

```bash
pytest
```
