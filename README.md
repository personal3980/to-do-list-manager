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

Use `localhost` for both browser URLs. Mixing `localhost` and `127.0.0.1` can break cookies and origin checks. The database host can still be `127.0.0.1`.

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

POST requests require `Origin: http://localhost:5500` and `Content-Type: application/json`. Use the frontend for interactive testing; Swagger's built-in POST requests originate on port 8000 and will be rejected by the exact-origin protection. CLI/API clients must explicitly set the configured frontend Origin header.

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

Task lists are scoped to the user's database ID in localStorage, remain after logout, and do not synchronize between browsers/devices. Old anonymous demo tasks are not automatically imported. A dashboard already open in another tab is not immediately hidden on logout/reset; its server-side session is nevertheless revoked. Reloading performs a fresh session check.

## Password reset delivery

### Local development (works without SMTP)

`RESET_DELIVERY=local` is the default when the setting is absent. For a registered email, the backend saves a private `.eml` email preview under `backend/reset-emails/`. Open the newest file in an email client or text editor, copy its full reset URL, and open it in your browser. This is a development mailbox on disk; **no email is sent**. Unknown emails produce the same API message and no preview file.

The reset token lives in the URL fragment to keep it out of static-server request logs. The reset page removes it from the address bar after reading it. If you reload that page, reopen the original email link or request another one. Reset links are not returned in API responses. The preview folder is ignored by Git; delete old previews when no longer needed.

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

From `backend/`, using the virtual environment:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests use an isolated in-memory SQLite database and capture email delivery; they do not read/write real users, start production MySQL startup hooks, or send email. They cover validation without the frontend, password hashing, login/logout, expired sessions and reset links, single-use reset, session revocation, generic recovery messages, delivery failure, origin checks, size limits, and throttling. MySQL-specific locking should also be checked when modifying reset transactions.

## Troubleshooting

| Problem | Check |
| --- | --- |
| Cannot reach API | Start Uvicorn from `backend/`, check MySQL is running and port 8000 is free. |
| Untrusted request origin or cookie failure | Use `http://localhost:5500`; match `FRONTEND_ORIGIN` exactly and restart the backend after changes. |
| MySQL access denied / unknown database | Check `.env`, database existence, user host/grants, and port 3306. |
| No reset email in inbox | Local mode writes `.eml` files instead of sending email. For SMTP, check configuration and the server warning log. |
| Expired/invalid reset link | Request a new link; previously used links and links older than 30 minutes will fail. |
| Too many attempts | Wait 15 minutes; development limits are per IP. |
| Styles or buttons fail to load | Check CDN access and the browser console. |
| Tasks disappear | Use the same account, browser profile, hostname, and port; browser data may have been cleared. |

## License

See [LICENSE](LICENSE).
