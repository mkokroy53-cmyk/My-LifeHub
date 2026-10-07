# My-LifeHub

A private, single-person life-management workspace. This repository is being built in phases; Phase 1 provides Django authentication and local configuration, while Phase 2 adds real, user-owned dashboard captures and schedule data.

## Phase 1 foundation

- Django 5.2 with Django's session authentication, password hashing, CSRF protection, and password validators.
- Sign-in, sign-out, and password-reset pages. Reset emails are printed to the development terminal until an email provider is configured.
- A login-protected dashboard with responsive desktop and mobile navigation.
- SQLite by default, with environment-based PostgreSQL configuration.
- Separate static and media roots. Media URLs are intentionally not served publicly.
- Environment-based secrets and settings. The local `.env` file is excluded from Git.

The dashboard captures now have dedicated private archive modules, full record editing/deletion, private PDF storage, and a personal data export.

## Phase 2 dashboard

- Per-account counts for diary entries, notes, learning resources, projects, goals, achievements, memories, and ideas.
- Quick capture for text entries, goals, and quotes, with a direct link to private PDF uploads.
- Recent activity and active-goal progress from saved records.
- Personal quote of the day, recurring weekly timetable, and upcoming events, deadlines, and reminders.
- Schedule forms validate time ranges and distinguish recurring weekday entries from dated events.
- Dashboard records are associated with their owner; dashboard queries and creation flows are scoped to the signed-in account.
- Responsive dashboard layout and capture forms for mobile and desktop.

## Phase 3 life archive

- Private archive overview with counts and recently updated records by type.
- Dedicated module lists for diary entries, notes, resources, projects, goals, achievements, memories, entertainment, and ideas.
- Search and detail views for individual records; all reads are scoped to the signed-in account.

## Phase 4 search and calendar

- Cross-module search across archive records, schedule items, finance transactions, and private PDF names.
- Month calendar for dated events, deadlines, and reminders, with previous/next month navigation.
- Weekly timetable commitments shown alongside the dated calendar; calendar queries are owner-scoped.

## Phase 5 finances

- Private income and expense ledger with categories, dates, notes, and editable records.
- Monthly totals and net balances are grouped by currency and never combine unlike currencies.
- Transaction queries and edit/delete actions are scoped to the signed-in account.

## Phase 6 files and portability

- Life archive records can be edited and deleted with owner checks and explicit delete confirmation.
- PDF uploads are limited to 15 MB, checked for a PDF signature, stored under a per-user private path, and downloaded only through an authenticated owner-checked view.
- Personal ZIP export includes the signed-in user's life records, schedule, quotes, finance transactions, and uploaded PDF bytes; responses are marked private and non-cacheable.

## Phase 7 immersive navigation

- Floating section navigator replaces the persistent sidebar, with staged section menus and direct Django-backed destinations.
- Includes account settings and an Entertainment archive; navigation is keyboard-operable and has a no-JavaScript details fallback.
- Short page transitions and section reveals honor reduced-motion preferences.
- Galaxy-inspired midnight theme with CSS-rendered twinkling stars; Light mode remains available and the star animation stops for reduced-motion users.

## Technology

- Python 3.13 (Python 3.11 or later recommended)
- Django 5.2
- SQLite for local development; PostgreSQL supported through configuration
- HTML, CSS, and a small amount of JavaScript

## Local setup

From the project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The workspace has a local `.env` file already. For a fresh checkout, copy `.env.example` to `.env` and replace `SECRET_KEY` with a newly generated value:

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(56))"
```

Put the generated value after `SECRET_KEY=` in `.env`. Never commit `.env` or use `DEBUG=True` in production.

Apply Django's built-in authentication and admin migrations:

```powershell
python manage.py migrate
```

Create the first login account:

```powershell
python manage.py createsuperuser
```

Start the development server:

```powershell
python manage.py runserver
```

Open <http://127.0.0.1:8000/> and sign in with the account created above. The admin is at <http://127.0.0.1:8000/admin/>.

## PostgreSQL

The PostgreSQL driver is installed with the project requirements. Create a database and update `.env`:

```dotenv
DB_ENGINE=postgresql
DB_NAME=mydigitallife
DB_USER=postgres
DB_PASSWORD=your-local-database-password
DB_HOST=localhost
DB_PORT=5432
```

Then run `python manage.py migrate`. Database credentials belong only in `.env` or a production secret store.

## Project layout

```text
config/          Django settings and root URL configuration
accounts/        Django authentication routes
dashboard/       Protected dashboard, archive CRUD, schedule, private files, export, and tests
finance/         Private income/expense ledger, transaction forms, and tests
templates/       Shared app shell and authentication screens
static/css/      Responsive visual system
static/js/       Mobile navigation behavior
media/           Private local upload storage; not served through public URLs
```

## Checks

```powershell
python manage.py check
python manage.py test
```

## Adding a module

Create a focused Django app, define its data model and migrations, add validated forms and login-protected views, then register URLs and templates. Any private file download must pass an authenticated ownership check; do not expose the media directory as a public URL.

## Roadmap

The planned core modules are implemented through Phase 6. Production deployment still requires a private production file store, managed secrets, HTTPS, configured email, and operational database backups.

## Production note

This is a local development foundation, not a production deployment configuration. Before deployment, configure HTTPS, secure hosts and trusted origins, a production email backend, PostgreSQL credentials, static-file hosting, backups, and private authenticated file delivery. Run Django's deployment checks after those settings are in place, and recheck export and file-access controls in the production environment.
