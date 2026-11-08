# Taskwell · To-do List Manager

A clean, responsive task manager built with HTML, CSS, JavaScript, jQuery, and Bootstrap. A minimal FastAPI folder structure is included for building a Python backend with MySQL.

**Current status:** the frontend is functional and saves tasks in your browser’s `localStorage`. The Python files are deliberately empty. There is no running API, MySQL connection, authentication, or frontend/API integration yet. You can use the frontend without setting up the backend.

## Features

- Create, edit, complete, reopen, and delete tasks.
- Add notes, a priority (low, medium, high), and an optional due date.
- Browse all tasks, today’s tasks, upcoming tasks, and completed tasks.
- Search titles and notes; filter by status; sort by creation date, due date, or priority.
- See task totals, completion progress, and overdue dates.
- Clear completed tasks after confirmation.
- Responsive layout for desktop and mobile; labeled controls and keyboard-accessible forms.

Three example tasks appear on first use. Delete or edit them to get started. Once saved, even an empty task list stays empty after a refresh.

## Technology and local ports

| Component | Technology | Local address |
| --- | --- | --- |
| Frontend | HTML, CSS, JavaScript, jQuery 3.7.1, Bootstrap 5.3.3 | `http://localhost:5500` |
| Backend (to implement) | Python / FastAPI / Uvicorn | `http://localhost:8000` |
| Database (to configure) | MySQL | `127.0.0.1:3306` |

Uvicorn uses port **8000** by default and MySQL typically uses **3306**. The frontend instructions explicitly choose **5500**, a common local development port; Python’s HTTP server otherwise defaults to 8000 and would conflict with the API. No production hosting configuration is included.

## Project structure

```text
to-do-list-manager/
├── frontend/
│   ├── index.html           # Dashboard and task form
│   ├── css/
│   │   └── style.css        # Responsive styles
│   └── js/
│       └── app.js           # jQuery interactions and localStorage
├── backend/
│   ├── .env.example         # Example local configuration (no real secrets)
│   ├── requirements.txt     # Suggested backend dependencies
│   └── app/
│       ├── __init__.py      # Empty package marker
│       ├── main.py          # TODO: FastAPI app, CORS, router registration
│       ├── database.py      # TODO: Environment loading, engine, sessions
│       ├── models.py        # TODO: SQLAlchemy task model
│       ├── schemas.py       # TODO: Pydantic request/response models
│       └── routes/
│           ├── __init__.py  # Empty package marker
│           └── tasks.py     # TODO: Task API endpoints
├── .gitignore
├── LICENSE
└── README.md
```

All `.py` files are empty scaffolding for you to implement; the comments above describe their intended responsibilities.

## Run the frontend

### Prerequisites

- Python 3.10 or newer (for the local static server and future backend).
- A modern browser.
- An internet connection to load Bootstrap, jQuery, and Google Fonts from their CDNs. For offline use, download those assets and update the references in `index.html` and `style.css`.

Clone your GitHub repository and open its project directory. Then run:

```powershell
cd frontend
python -m http.server 5500 --bind 127.0.0.1
```

Open **[http://localhost:5500](http://localhost:5500)**. Keep the terminal open while using the app. Press `Ctrl+C` to stop the server. On Windows, use `py` instead of `python` if needed; on macOS/Linux, use `python3`.

You can also use VS Code Live Server with its port set to 5500. Keep the same hostname and port when reopening the app: browser storage belongs to each origin, so `localhost` and `127.0.0.1` have separate saved lists.

### Usage

1. Click **New task**, enter a title, optionally add notes, priority, and a due date, then choose **Save task**.
2. Check a task to complete it; uncheck it to reopen it.
3. Use the pencil to edit or the × button to delete a task.
4. Use the sidebar views, search, status tabs, and sorting to organize your list. **Today** includes tasks due today; **Upcoming** shows unfinished tasks due after today. Filters combine with the selected view.
5. Use **Clear completed** to delete all completed tasks, including ones hidden by a filter. Summary cards always describe the entire list; the list count describes the filtered results.

Tasks stay in the current browser profile after refresh. They are not stored in MySQL or synchronized across browsers/devices. Clearing site data removes them; private browsing may discard them when closed. A visible warning appears if browser storage cannot load or save data.

## Prepare the backend (optional, implementation required)

The steps below prepare your environment. They do not create a working API from the empty scaffold.

### 1. Create a Python environment

From the project root, on Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

If PowerShell prevents activation, use the virtual environment’s Python directly, without changing execution policy:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

On macOS/Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Dependency ranges are a starting point, not a locked environment. Pin versions after implementing and testing the backend.

### 2. Prepare MySQL

Install MySQL Server and start its local service on port 3306. Connect with an administrator account:

```bash
mysql -u root -p
```

Create a development database and a dedicated local user. Replace the example password before running this SQL:

```sql
CREATE DATABASE todo_manager CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'todo_user'@'127.0.0.1' IDENTIFIED BY 'replace_with_your_local_password';
GRANT ALL PRIVILEGES ON todo_manager.* TO 'todo_user'@'127.0.0.1';
```

Edit `backend/.env` to match your database, user, and password. `.env` is ignored by Git; never commit credentials. These variables do nothing until your implementation reads them (for example, with `python-dotenv`). Use SQLAlchemy’s URL builder to handle passwords containing special characters.

### 3. Implement the empty Python files

- `database.py`: load configuration, connect to MySQL with SQLAlchemy/PyMySQL, and provide database sessions.
- `models.py`: define a task table, including an ID, title, notes, priority, optional due date, completed flag, and creation timestamp.
- `schemas.py`: define request and response validation, including a required trimmed title and allowed priorities.
- `routes/tasks.py`: implement task creation, listing, updates, and deletion with database persistence and appropriate error responses.
- `main.py`: create the FastAPI instance named `app`, register the task router, configure CORS for `http://localhost:5500`, and implement your table-creation or migration strategy.

An optional starting API contract (not implemented):

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/api/tasks` | List tasks |
| POST | `/api/tasks` | Create a task |
| PATCH | `/api/tasks/{id}` | Edit fields or completion status |
| DELETE | `/api/tasks/{id}` | Delete a task |

### 4. Start the API after implementing it

From `backend/`, with the virtual environment active:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1
```

The API will use **[http://localhost:8000](http://localhost:8000)** and generated API documentation will be available at **[http://localhost:8000/docs](http://localhost:8000/docs)**. This command will fail with an app-not-found error until you create the FastAPI `app` in `app/main.py`.

### 5. Connect the frontend

Replace the localStorage read/write logic in `frontend/js/app.js` with jQuery AJAX requests to `http://localhost:8000/api/tasks`. Handle loading states, validation errors, and failed requests. Agree on the ID and timestamp formats returned by the API; the demo currently uses string IDs and numeric creation timestamps. Do not put database credentials in frontend code. Existing demo tasks will not move to MySQL automatically.

Run the frontend server and API in separate terminals, with MySQL running in the background. Because ports 5500 and 8000 are different origins, configure the backend’s CORS middleware for the exact frontend origin you use.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| The design or task buttons do not load | Check the internet connection and browser console for blocked CDN requests. |
| Port already in use | Stop the other local server or choose another port; update URLs and CORS to match. |
| Tasks appear missing | Use the same browser profile, hostname, and port as before. |
| API command reports a missing `app` | The scaffold is empty; implement `app/main.py` first. |
| MySQL access denied | Check the service, TCP host, database user grants, and `.env` credentials. |
| Browser reports a CORS error | Allow the frontend’s exact origin in FastAPI and restart the API. |

## License

See [LICENSE](LICENSE).
