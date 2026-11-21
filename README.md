# Taskwell - To-do List Manager

A responsive task dashboard with a simple FastAPI/MySQL authentication system. The frontend uses HTML, CSS, JavaScript, jQuery, and Bootstrap.

**Implemented:** signup, login, logout, current-user lookup, forgot password, and password reset. Authentication persists in MySQL. **Tasks still use browser localStorage**, scoped by user ID; there is no task API or database task table yet. Authentication protects API sessions; browser task data is not encrypted or suitable for sensitive information on shared devices.

## Features

- Signup with name, email, password, and password confirmation.
- Login with an expiring, HttpOnly session cookie; logout revokes the session in MySQL.
- Reset links expire after 30 minutes, can be used once, and revoke all sessions and reset links for that user after a successful password change.
- Frontend and server-side validation; passwords require 8-128 characters with at least one ASCII letter and number. Passwords are never trimmed.
- Argon2 password hashing; only SHA-256 hashes of random session and reset tokens are stored in MySQL.
- Exact-origin checks on POST requests, restricted CORS, JSON-only requests, request-size limits, and simple per-IP rate limits.
- Dashboard with task creation, editing, completion, deletion, notes, priorities, due dates, search, filters, and sorting.

## Local requirements and ports

- Python 3.10+ and MySQL Server (8.0+ recommended).
- A modern browser and internet access for the Bootstrap/jQuery/Google Fonts CDNs.
- Frontend: **http://localhost:5500** (explicit local static-server port).
- FastAPI: **http://localhost:8000** (Uvicorn default).
- MySQL: **127.0.0.1:3306** (default database port).

Use the same hostname for frontend and API cookies. The frontend automatically uses its own hostname for port 8000. When `FRONTEND_ORIGIN` uses `localhost` or `127.0.0.1`, the backend accepts both loopback aliases on that configured port. Other origins stay restricted. Browser task storage and cookies remain separate for each hostname.

## Setup

Clone this repository and open a terminal in the project root.

### 1. Prepare the backend

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
# Only if .env does not already exist:
Copy-Item .env.example .env
```

Keep an existing `.env`; do not replace your own credentials with the example. If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` instead of `python` for each backend command.

macOS/Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
# Only if .env does not already exist:
cp .env.example .env
```

### 2. Configure MySQL

Start MySQL and create a database if needed. For example, connect using `mysql -u root -p`, then run the following with your own password:

```sql
CREATE DATABASE todo_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'todo_user'@'127.0.0.1' IDENTIFIED BY 'replace_with_your_password';
GRANT ALL PRIVILEGES ON todo_manager.* TO 'todo_user'@'127.0.0.1';
```

Edit `backend/.env` to match your existing database credentials:

```dotenv
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=todo_manager
DB_USER=todo_user
DB_PASSWORD=replace_with_your_password
FRONTEND_ORIGIN=http://localhost:5500
COOKIE_SECURE=false
RESET_DELIVERY=local
```

The backend reads `.env` relative to its own folder. Credentials never go into frontend files, and `.env` is ignored by Git. The database must already exist; missing tables are created automatically on API startup. Existing tables are not altered or dropped. If you change models later, use a migration rather than expecting startup to modify an existing table.

### 3. Start FastAPI

In the backend terminal, with its virtual environment active:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1
```

API documentation: [http://localhost:8000/docs](http://localhost:8000/docs).

POST requests require `Content-Type: application/json`. Browser requests must originate from the configured `FRONTEND_ORIGIN` or the API itself (so Swagger at `/docs` works). Native CLI/API clients such as curl and Postman may omit `Origin`. Explicit untrusted origins, `Origin: null`, and originless requests marked cross-site by the browser are rejected.

### 4. Start the frontend

Open a second terminal in the project root:

```powershell
cd frontend
python -m http.server 5500 --bind 127.0.0.1
```

Open [http://localhost:5500/login.html](http://localhost:5500/login.html). Use `python3` on macOS/Linux or `py` on Windows if necessary. Keep both terminals and MySQL running; press `Ctrl+C` to stop a server.

Serve **only the frontend folder**, never the repository root or backend folder: backend configuration and local reset-email previews are private.

## Account usage

1. Choose **Create an account**, enter a name and email, and confirm your password.
2. Log in with that email and password. Signup does not automatically log you in.
3. Use the dashboard; the header shows your name and a **Log out** button.
4. A session lasts 24 hours. Expired sessions cannot authenticate API requests; refresh the dashboard to check its session again.
5. To recover access, choose **Forgot password?**, enter your email, and follow the reset link.
6. Enter and confirm a new password, then log in again. Previous sessions and other reset links stop working.

Task lists are scoped to the user's database ID in localStorage, remain after logout, and do not synchronize between browsers/devices. Old anonymous demo tasks are not automatically imported. The dashboard checks its session on focus, visibility changes, browser-history restoration, and every minute while visible. Revoked sessions return to login; a different logged-in account reloads the dashboard with that account’s data.

Tasks refresh their date views across local midnight. Due dates support calendar dates from `0001-01-01` to `9999-12-31`, including past dates; incomplete past tasks are marked overdue. Undated tasks sort last. Changes synchronize between tabs for the same user and origin; simultaneous edits to the same task still use the last saved value. If stored task data cannot be read, editing is disabled to avoid overwriting it.

## Password reset delivery

### Local development (works without SMTP)

`RESET_DELIVERY=local` is the default when the setting is absent. For a registered email, the backend saves a private `.eml` email preview under `backend/reset-emails/`. Open the newest file in an email client or text editor, copy its full reset URL, and open it in your browser. This is a development mailbox on disk; **no email is sent**. Unknown emails produce the same API message and no preview file.

The reset token lives in the URL fragment to keep it out of static-server request logs. The reset page removes it from the address bar after reading it. If you reload that page, reopen the original email link or request another one. Opening a new reset link in the same tab also works. Reset links are not returned in API responses. The preview folder is ignored by Git; delete old previews when no longer needed.

### Real email with SMTP

Set the following in `backend/.env`, then restart the backend:

```dotenv
RESET_DELIVERY=smtp
SMTP_HOST=smtp.your-provider.example
SMTP_PORT=587
SMTP_USER=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_FROM=you@your-domain.example
```

This implementation uses authenticated SMTP with STARTTLS (commonly port 587). Use credentials/app passwords required by your provider. If delivery fails, the API retains its generic response and logs a configuration warning without disclosing account existence or credentials.

Before public deployment, use HTTPS, set `COOKIE_SECURE=true`, configure real SMTP and the exact frontend origin, and replace the in-memory rate limiter with shared storage if using multiple workers. The current defaults are intended for one local development process. There is no email-ownership verification or MFA in this version.

## Database schema

[backend/schema.sql](backend/schema.sql) documents the MySQL DDL and can be imported manually into the database selected by `DB_NAME`. Normally startup creates these tables for you.

| Table | Columns and purpose |
| --- | --- |
| `users` | Integer primary key, name, unique normalized email, Argon2 password hash, UTC creation time. |
| `auth_sessions` | Hashed token primary key, user foreign key, indexed UTC expiry. Sessions expire after 24 hours. |
| `password_reset_tokens` | Hashed token primary key, user foreign key, indexed UTC expiry. Reset links expire after 30 minutes. |

Foreign keys cascade on user deletion. Password reset deletes all that user's sessions and reset tokens in the same transaction. Reset processing locks the user row to serialize concurrent reset attempts on MySQL. Expired rows are rejected during authentication/reset and are cleaned during subsequent login/reset-link requests.

## API reference

All endpoints are under `/api/auth`. Send cookies with requests (`xhrFields: { withCredentials: true }` in jQuery). Authentication tokens are not stored in browser localStorage.

| Method | Endpoint | JSON body / result |
| --- | --- | --- |
| POST | `/signup` | `name`, `email`, `password`, `confirm_password`; returns public user fields (201). |
| POST | `/login` | `email`, `password`; sets session cookie and returns public user fields. |
| GET | `/me` | Returns `id`, `name`, `email`; 401 without a valid session. |
| POST | `/logout` | `{}`; revokes current session and clears cookie. |
| POST | `/forgot-password` | `email`; always returns a generic delivery message for valid input. |
| POST | `/reset-password` | `token`, `password`, `confirm_password`; changes password and revokes sessions. |

Invalid fields return 422 with an `errors` array; invalid credentials/session return 401; invalid/expired reset links return 400; duplicate signup returns 409. Throttled requests return 429. Limits per client IP per 15 minutes: signup 10, login 20, reset-link requests 5, password resets 10. These counters reset when the server restarts.

## Project structure

```text
to-do-list-manager/
|-- frontend/
|   |-- index.html                 # Task dashboard (session check)
|   |-- login.html
|   |-- signup.html
|   |-- forgot-password.html
|   |-- reset-password.html
|   |-- css/
|   |   |-- style.css
|   |   `-- auth.css
|   `-- js/
|       |-- config.js              # Local API URL
|       |-- auth.js                # Account forms and frontend validation
|       |-- session.js             # Current-user check and logout
|       `-- app.js                 # Browser-based task operations
|-- backend/
|   |-- .env.example
|   |-- requirements.txt
|   |-- requirements-dev.txt
|   |-- schema.sql
|   |-- app/
|   |   |-- __init__.py
|   |   |-- config.py
|   |   |-- database.py
|   |   |-- main.py
|   |   |-- models.py
|   |   |-- schemas.py
|   |   |-- security.py
|   |   |-- mail.py
|   |   `-- routes/
|   |       |-- __init__.py
|   |       |-- auth.py
|   |       `-- tasks.py            # Reserved, still empty
|   `-- tests/
|       `-- test_auth.py
|-- .gitattributes
|-- .gitignore
|-- LICENSE
`-- README.md
```

## Tests

Install development dependencies and Chromium once, from the project root:

```powershell
.\backend\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\backend\.venv\Scripts\python.exe -m playwright install chromium
.\backend\.venv\Scripts\python.exe -m pytest -q
```

On macOS/Linux, use `backend/.venv/bin/python` instead. Pytest works from the root or backend folder. The default suite runs API and browser tests, skipping the real-MySQL check unless explicitly enabled. For API tests alone, use `python -m pytest backend/tests -q` from the root with the virtual environment active.

API tests use isolated SQLite and captured email delivery. Browser tests launch Chromium with isolated storage, a temporary frontend server, controlled dates, and mocked authentication transport. They download the same jQuery/Bootstrap versions used by the app into ignored `.qa-cache/` once and reuse them; internet access is needed on the first run. Font requests are suppressed for repeatable browser tests. If a corporate TLS proxy prevents Python from downloading the assets, populate `.qa-cache/jquery.js`, `bootstrap.css`, and `bootstrap.js` from the CDN URLs in `frontend/tests/support.py` using your trusted system downloader.

Coverage includes past/present/future dates in three time zones, midnight refresh, leap days, year boundaries, invalid dates, task CRUD, search/filter/sort, persistence, browser-tab updates, storage failures, text escaping, authentication forms, session revocation, reset links, and responsive layouts at 320/375/768/1366 pixels. Screenshots are generated in ignored `test-results/`.

To include an actual browser/API/MySQL check using your existing `.env`, in PowerShell:

```powershell
$env:TASKWELL_TEST_MYSQL = '1'
.\backend\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:TASKWELL_TEST_MYSQL
```

This creates one uniquely named QA account and removes it and its reset-email previews afterward. It checks real signup/login/reset/logout, unique-email and cascade constraints, session invalidation, reset replay, and concurrent reset attempts using MySQL row locks. It starts a separate API on a temporary port, forces local email previews, and leaves your `.env` and existing users unchanged. The configured database and authentication tables must already exist (start the normal API once first).

See [QA.md](QA.md) for the review findings, fixes, evidence, and limitations.

## Troubleshooting

| Problem | Check |
| --- | --- |
| Cannot reach API | Start Uvicorn from `backend/`, check MySQL is running and port 8000 is free. |
| Untrusted request origin or cookie failure | Use localhost or 127.0.0.1 consistently; match the frontend port in `FRONTEND_ORIGIN` and restart after configuration changes. |
| MySQL access denied / unknown database | Check `.env`, database existence, user host/grants, and port 3306. |
| No reset email in inbox | Local mode writes `.eml` files instead of sending email. For SMTP, check configuration and the server warning log. |
| Expired/invalid reset link | Request a new link; previously used links and links older than 30 minutes will fail. |
| Too many attempts | Wait 15 minutes; development limits are per IP. |
| Styles or buttons fail to load | Check CDN access and the browser console. |
| Tasks disappear | Use the same account, browser profile, hostname, and port; browser data may have been cleared. |

## License

See [LICENSE](LICENSE).
