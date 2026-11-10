# Tournament Matchup Generator – Multi-Sport Knockout Management System

A beginner-friendly Flask application for organizing multi-sport knockout tournaments from registration through champion determination. It stores tournaments, teams, players, fixtures, scores, progression, and champions in SQLite through SQLAlchemy. The interface uses server-rendered HTML, CSS, and vanilla JavaScript without browser localStorage or paid APIs.

## Problem statement

Tournament organizers often manage registrations, rosters, fixtures, scores, and advancement across separate spreadsheets or manual notes. That makes duplicate records, inconsistent brackets, unresolved ties, and accidental result changes difficult to control. This project provides one small, maintainable system for managing those workflows with persistent database records and a clear visual knockout bracket.

## Project objectives

- Provide a clean Flask foundation suitable for beginners.
- Persist tournament-management data in SQLite instead of browser storage.
- Support tournament, team, and player registration with validation.
- Generate randomized single-elimination brackets for 2–64 teams.
- Handle BYEs, score entry, ties, winner progression, and champions safely.
- Keep destructive operations POST-only and transactional.
- Offer readable dashboards, forms, tables, empty states, and responsive bracket views.
- Keep future enhancements possible without replacing the current architecture.

## Technology stack

- Python 3.10+
- Flask
- Flask-SQLAlchemy / SQLAlchemy ORM
- SQLite with foreign-key enforcement enabled
- PostgreSQL with Psycopg 3 for hosted production deployments
- HTML and Jinja templates
- CSS
- Vanilla JavaScript
- pytest

No paid APIs are used. The browser is not used as the database.

## Completed modules and features

### Module 1 — Foundation

- Flask application factory
- SQLite and SQLAlchemy configuration
- Tournament, Team, Player, and Match models
- Foreign keys and relationships
- Safe additive schema compatibility for older databases
- Home route and database initialization command

### Module 2 — Dashboard and UI

- Database-backed dashboard statistics
- Recent tournaments
- Sidebar navigation
- Responsive layouts
- Empty database states
- Shared visual language for forms, tables, cards, badges, and actions

### Module 3 — Tournament management

- Create, edit, view, and delete tournaments
- Required-field and date validation
- Sport and status selection
- Search by tournament name
- Sport and status filters
- Dashboard synchronization
- Transaction-safe deletion of associated records

### Module 4 — Team and player management

- Team registration and editing
- Team captain and optional logo URL
- Player registration and editing
- Scoped duplicate team-name validation
- Scoped duplicate jersey-number validation
- Team/player detail pages
- Safe deletion and relationship cleanup

### Module 5 — Knockout fixture engine

- Randomized single-elimination bracket generation
- 2–64 team support
- Next-power-of-two bracket sizing
- Balanced BYE distribution across bracket halves
- Automatic BYE advancement
- Persistent round and match metadata
- Duplicate-generation protection
- Responsive, scrollable bracket visualization

### Module 6 — Match scoring and progression

- Match detail pages
- Non-negative whole-number score validation
- Automatic winner determination
- Manual tiebreaker selection for tied scores
- Correct home/away downstream slot assignment
- Scheduled, Ready, In Progress, and Completed statuses
- Transactional winner progression
- Completed-result correction protection
- Final champion determination
- Champion display on tournament details and dashboard

### Module 7 — Final QA and preparation

- Expanded regression and edge-case tests
- SQLite foreign-key enforcement
- Environment-provided secret key support
- Production-safe default debug configuration
- Safe 404, 405, and 500 user-facing error pages
- Safe external logo URL validation
- HTML escaping verification
- Final documentation and isolated demonstration workflow

Authentication and administrator roles are not implemented. The current interface is not an authenticated administrative system.

## Project architecture

```text
.
├── app/
│   ├── __init__.py       # Application factory, error handlers, schema upgrades
│   ├── extensions.py     # SQLAlchemy extension and SQLite foreign-key pragma
│   ├── fixture_engine.py # Randomized single-elimination bracket generation
│   ├── models.py         # Tournament, Team, Player, and Match models
│   ├── result_engine.py  # Score validation and transactional progression
│   ├── routes.py         # Dashboard, CRUD, fixture, result, and error workflows
│   ├── static/
│   │   ├── css/style.css # Responsive application styling
│   │   └── js/main.js    # Small responsive-navigation behavior
│   └── templates/        # Shared layout, forms, details, bracket, and error views
├── public/static/        # Vercel CDN mirrors of the unchanged CSS and JavaScript assets
├── instance/             # Local SQLite database directory
├── tests/test_app.py     # Full regression and edge-case suite
├── config.py             # Environment-aware configuration
├── pyproject.toml         # Vercel Python entrypoint and runtime metadata
├── requirements.txt      # Python dependencies
└── run.py                # Development entry point
```

The database models are related as follows:

- A `Tournament` owns teams and matches.
- A `Team` belongs to one tournament and owns players.
- A `Player` belongs to one team.
- A `Match` belongs to one tournament and references home, away, and winner teams.
- A `Match` may reference the next match in the bracket through `next_match_id`.
- A completed tournament may reference its champion through `champion_id`.

## Installation

```bash
cd tournament-matchup-generator
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Configuration

The default local database is stored at `instance/tournament.db`. The directory is tracked through `.gitkeep`, while runtime database files are ignored by Git. Local development continues to use SQLite.

For a deployment or controlled environment, provide a secret key through the environment:

```bash
export SECRET_KEY="replace-with-a-long-random-value"
```

An alternate SQLAlchemy database URL can be supplied through `DATABASE_URL`. PostgreSQL URLs using `postgres://` or plain `postgresql://` are normalized automatically to the Psycopg 3 dialect:

```bash
export DATABASE_URL="sqlite:////absolute/path/to/tournament.db"
# Hosted example:
export DATABASE_URL="postgresql://user:password@host:5432/tournament_db?sslmode=require"
```

The base configuration has `DEBUG = False`. Development debug mode should be explicitly requested with Flask's command-line option rather than being enabled automatically by `run.py`. When Vercel or another production environment is detected, `SECRET_KEY` and `DATABASE_URL` are required; the local development fallback secret and SQLite path are never used there.

## Database initialization

The application creates tables and applies safe additive upgrades during startup. The explicit initialization command is:

```bash
flask --app run.py init-db
```

The command does not recreate or erase existing data. Module 5 and Module 6 upgrades add bracket and result metadata, including `matches.decided_by_tiebreaker` and `tournaments.champion_id`.

## Start the application

For a normal local run:

```bash
flask --app run.py run
```

For local development with Flask's debugger explicitly enabled:

```bash
flask --app run.py run --debug
```

Alternatively:

```bash
python run.py
```

Open <http://127.0.0.1:5000/>. The home route is the dashboard.

## Deploy to Vercel

The repository includes a root `pyproject.toml` with the Vercel entrypoint:

```toml
[tool.vercel]
entrypoint = "run:app"
```

The entrypoint loads the existing `app` object exported by `run.py`; no Flask routes, models, templates, or business logic are replaced.

The existing `app/static/` directory remains the local Flask source of truth. Identical copies are also stored under `public/static/` so Vercel can serve them through its CDN as recommended for Python deployments.

### 1. Create a managed PostgreSQL database

Vercel's function filesystem is temporary, so do not use the local SQLite database for permanent hosted tournament data. Create a managed PostgreSQL database through a provider such as Vercel Postgres, Neon, Supabase, or another PostgreSQL-compatible service. Copy its connection URL. The URL may begin with `postgres://`, `postgresql://`, or `postgresql+psycopg://`.

The application creates missing tables and applies only additive compatibility upgrades during startup. It does not drop, recreate, or erase existing records. Existing SQLite data is not automatically migrated to PostgreSQL; export and migrate it separately if needed before switching production traffic.

### 2. Import the GitHub repository

In Vercel, choose **Add New Project**, import `abisheik-cmd/Tournament-manager`, and select the `main` branch. Use the repository root as the project root. No build command is required for this Flask function.

### 3. Add production environment variables

Add these variables for the Production environment before deploying:

```text
SECRET_KEY=<long-random-production-secret>
DATABASE_URL=<managed-postgresql-connection-url>
```

Do not commit either value to the repository. A deployment without either variable fails fast instead of silently using a development secret or a non-persistent SQLite file.

### 4. Deploy and verify

Deploy from the Vercel dashboard or with the current Vercel CLI:

```bash
npx vercel@latest login
npx vercel@latest link
npx vercel@latest deploy --prod
```

After deployment, open the generated URL and verify the dashboard, tournament CRUD, team/player management, fixture generation, and match scoring workflows. Review Vercel Function logs if the database provider rejects the connection or requires a provider-specific SSL option.

## Testing and QA

Run the complete suite:

```bash
pytest -q
```

Run compilation and whitespace checks:

```bash
python -m compileall -q app config.py run.py
git diff --check
```

The final Module 7 verification passed **44 tests**. The suite covers foundation behavior, dashboard statistics, tournament CRUD, team/player relationships, bracket generation, BYEs, scoring, ties, progression, champions, persistence, edge cases, invalid methods, HTML escaping, unsafe logo URLs, and deletion integrity.

## Normal tournament workflow

1. Open **Tournaments** and select **Create tournament**.
2. Enter the name, sport, venue, date, description, and status.
3. Open the tournament details page and select **Add team**.
4. Register at least two teams with captain names.
5. Open each team and add players if a roster is needed.
6. Open **Match Fixtures**, select the tournament, and choose **Generate fixtures**.
7. Confirm the one-time randomized generation action.
8. Open a match card from the bracket.
9. Enter non-negative whole-number scores.
10. For a tie, save the tied score and select one of the two participating teams as the tiebreaker winner.
11. Continue through subsequent rounds as winners are advanced automatically.
12. When the final is completed, the winner is stored as the tournament champion and displayed on the tournament details page and dashboard.

Completed results are locked to protect downstream fixtures. Automatic bracket regeneration is intentionally disabled.

## Isolated demonstration workflow

Use a temporary database so demonstration records do not pollute the main project database:

```bash
python3 -m venv /tmp/tournament-demo-venv
source /tmp/tournament-demo-venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="sqlite:////tmp/tournament-matchup-demo.db"
export SECRET_KEY="demo-only-secret"
flask --app run.py init-db
flask --app run.py run
```

Then demonstrate:

1. Create a tournament.
2. Register three teams to show a BYE.
3. Add one or more players to each team.
4. Generate fixtures and show the automatic BYE advancement.
5. Enter a tied score for a regular match.
6. Select the tiebreaker winner.
7. Enter subsequent-round scores.
8. Complete the final and show the champion on the tournament detail page and dashboard.

Stop the server and remove the isolated database afterward if desired:

```bash
rm -f /tmp/tournament-matchup-demo.db
```

No fabricated screenshots are included. The repository contains no claim of a deployed production service.

## Security and data-integrity review

- SQLAlchemy ORM queries are used instead of string-built SQL for application data access.
- Server-side validation is applied to tournament, team, player, score, and tiebreaker inputs.
- Jinja autoescaping protects rendered user text from HTML injection.
- External team logo URLs are restricted to absolute HTTP(S) URLs.
- SQLite foreign-key enforcement is enabled on every SQLite connection.
- Destructive operations use POST routes and confirmation dialogs in the UI.
- Database mutations use commits with rollback handling on SQLAlchemy errors.
- Completed match results cannot be silently overwritten.
- Missing records and unsupported HTTP methods return clear user-facing pages.
- Secret keys may be provided through `SECRET_KEY` and are not stored in the repository.
- Runtime SQLite files and Python caches are excluded through `.gitignore`.
- Authentication, authorization, and administrator roles are not implemented and must be added before exposing the application to untrusted users.

## Known limitations

- There is no authentication or role-based access control.
- Completed match correction is blocked rather than recalculating downstream matches.
- Match scheduling dates, referee assignment, and live notifications are not implemented.
- Logo images are referenced by URL and are not uploaded or scanned by the application.
- SQLite remains appropriate for local development and tests, but permanent Vercel deployments require managed PostgreSQL because Vercel function storage is temporary.
- The repository contains Vercel deployment configuration, but a live production deployment still depends on the user's Vercel project, environment variables, and managed database.

## Future enhancements

- Authentication and organizer/admin permissions
- CSRF protection for production forms
- Match scheduling, venues, referees, and notifications
- Exportable brackets and tournament reports
- Richer sport-specific scoring rules
- Audit history for result changes
- PostgreSQL migrations and production observability
- Optional genuine screenshots or a hosted demonstration environment

## Delivery status

Module 7 is the final development stage requested for this project. No additional development module was started during this QA pass.
