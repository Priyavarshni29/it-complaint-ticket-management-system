# NexaDesk — IT Complaint & Ticket Management System

NexaDesk is a web-based IT Complaint & Ticket Management System developed as a DBMS mini-project. It helps users report IT issues, track ticket progress, communicate about complaints, and manage support operations through a web interface.

The application uses **FastAPI** for the backend, **MySQL** for persistent data storage, **SQLAlchemy** for database interaction, and HTML, CSS, and JavaScript for the frontend.

## Features

### Ticket Management
- Register and manage IT complaint tickets.
- Categorize complaints by type, priority, and description.
- View tickets and track their current status.
- Update ticket status and maintain ticket history.
- Support ticket assignment and staff-related workflows.

### Authentication and Access
- User registration and login endpoints.
- JWT-based authentication.
- User-related data management.
- Environment-based configuration for sensitive application settings.

### Communication and Notifications
- Ticket-related communication functionality.
- Notification services for relevant ticket events.
- Dedicated backend routes for communication and notifications.

### Service-Level Agreement (SLA) Management
- SLA-related ticket management functionality.
- Dedicated SLA routes and service logic.
- A backfill utility for processing existing SLA-related data.

### Database and Backend
- MySQL integration using SQLAlchemy and PyMySQL.
- Relational data storage with primary and foreign keys.
- Database schema migrations managed using Alembic.
- REST API endpoints built with FastAPI.
- Interactive API documentation through Swagger UI.

### Web Interface
- Browser-based frontend using HTML, CSS, and JavaScript.
- Ticket management through frontend-to-backend API requests.
- Ticket information and support workflow interaction.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | MySQL 8.0 |
| ORM | SQLAlchemy |
| Database driver | PyMySQL |
| Authentication | JWT |
| Configuration | python-dotenv |
| Database migrations | Alembic |
| Frontend | HTML, CSS, JavaScript |
| API documentation | Swagger UI |
| Database GUI | MySQL Workbench |

## Application Architecture

NexaDesk follows a layered architecture in which the frontend communicates with the FastAPI backend, which processes requests and interacts with the MySQL database.

```text
User
  |
  v
Web Frontend
(HTML, CSS, JavaScript)
  |
  v
FastAPI Backend
  |
  +-- Authentication Routes
  +-- Ticket Routes
  +-- Staff Routes
  +-- Communication Routes
  +-- Notification Routes
  +-- SLA Routes
  |
  v
SQLAlchemy + PyMySQL
  |
  v
MySQL Database
```

## Project Structure

```text
it-complaint-ticket-management-system/
├── app/
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   ├── routes/
│   │   ├── tickets.py
│   │   ├── auth_routes.py
│   │   ├── communications.py
│   │   ├── notifications.py
│   │   ├── sla.py
│   │   └── staff.py
│   └── services/
│       ├── __init__.py
│       ├── notifications.py
│       └── sla.py
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── migrations/
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/
├── alembic.ini
├── backfill_sla.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

*Note: The tree lists the files expected from the current project updates. Retain any additional existing files, such as SQL scripts and package initializers, in the actual repository.*

## Database Design

The database is named `it_complaint_system`.

The core application data includes users, IT support staff, complaint categories, tickets, and ticket history. Additional authentication, communication, notification, and SLA functionality may use further tables depending on the configured models and migrations.

| Entity | Purpose |
|---|---|
| Users | Stores user-related information. |
| Staff | Stores IT support staff information. |
| Categories | Organizes complaints into categories. |
| Tickets | Stores complaint details, priority, status, and assignment information. |
| Ticket History | Records ticket status changes and related history. |
| Communication and notification data | Supports ticket-related communication and notification functionality where configured. |
| SLA-related data | Supports service-level agreement tracking where configured. |

### Relationships

- One user can create multiple tickets.
- One staff member may be assigned multiple tickets.
- One category can be associated with multiple tickets.
- One ticket can have multiple history records.
- Tickets can remain unassigned until support staff are allocated.

The exact relationships depend on the foreign keys defined in the SQLAlchemy models and database migrations.

## DBMS Concepts Demonstrated

- Relational database design.
- Primary keys and foreign keys.
- Entity relationships and referential integrity.
- Integrity constraints such as `NOT NULL` and `UNIQUE`, where defined.
- SQL `JOIN` and `LEFT JOIN`.
- Aggregate functions and `GROUP BY`.
- Subqueries and conditional expressions.
- Data insertion, retrieval, and updates.
- Ticket status-history management.
- Database schema evolution through migrations.
- Transaction management where implemented.

## Prerequisites

Install the following before running the application:

- Python 3.10 or later.
- MySQL Server 8.0.
- Git.
- A web browser.

MySQL Workbench is optional but useful for inspecting tables and executing SQL queries.

## Setup and Installation

### 1. Clone the repository

```bash
git clone https://github.com/Priyavarshni29/it-complaint-ticket-management-system.git
cd it-complaint-ticket-management-system/it-complaint-ticket-management-system
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use Command Prompt:

```bat
venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a local `.env` file in the project root. Use `.env.example` as a template if it exists.

Configure the database connection values and the secret key required by the application. For example:

```dotenv
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=it_complaint_system
SECRET_KEY=replace_with_a_strong_random_secret
```

Use the exact environment-variable names expected by the project's configuration code. The example above must be adjusted if your implementation uses different names.

**Security:** Never commit your actual `.env` file, database password, or production JWT secret to GitHub.

### 5. Create and configure the database

Create the `it_complaint_system` database in MySQL Server if it does not already exist.

Use the project's existing SQL schema or database initialization process to create the required tables. If you use `sql/schema_and_queries.sql`, inspect the script first because it may drop and recreate tables.

For databases managed through Alembic, review the migration configuration and apply the appropriate migrations. For example:

```bash
alembic upgrade head
```

Run this only after configuring the database connection and confirming that the migrations are appropriate for your existing database. Do not apply a baseline migration blindly to a database that already contains tables or data.

### 6. Start the application

From the project root, run:

```bash
uvicorn app.main:app --reload
```

Open the following URLs in your browser:

- **Web portal:** http://127.0.0.1:8000/
- **Swagger API documentation:** http://127.0.0.1:8000/docs
- **ReDoc documentation:** http://127.0.0.1:8000/redoc

The endpoints available in Swagger depend on the routers registered in the current application.

## API Overview

The backend contains dedicated route modules for ticket management, authentication, staff, communications, notifications, and SLA functionality.

| Module | Responsibility |
|---|---|
| Ticket routes | Ticket creation, retrieval, and status-related operations. |
| Authentication routes | User registration and login. |
| Staff routes | Staff-related management operations. |
| Communication routes | Ticket-related communication. |
| Notification routes | Notification-related operations. |
| SLA routes | SLA-related ticket operations. |

For the exact HTTP methods, endpoint paths, required request fields, and authentication requirements, refer to the running application's Swagger documentation at `/docs`.

## Database Migrations

NexaDesk includes Alembic configuration and migration files to manage database schema changes.

Typical migration commands include:

```bash
alembic current
alembic history
alembic upgrade head
```

- `alembic current` displays the current migration revision.
- `alembic history` lists available migration revisions.
- `alembic upgrade head` applies pending migrations.

Always back up important database data before applying migrations, particularly when upgrading an existing installation.

## Testing and Verification

After starting the application, verify the following against the features enabled in your local configuration:

- The application starts without backend errors.
- The database connection succeeds.
- Users can register and log in.
- Ticket operations work through the API and web interface.
- Ticket status changes and history are recorded correctly.
- Staff, communication, and notification endpoints respond as expected.
- SLA-related functionality works with the configured database schema.
- Database migrations are consistent with the current schema.

Use Swagger UI and MySQL Workbench to inspect API responses and database records. These are verification steps; do not describe a test as passed until you have run it successfully.

## Future Improvements

Potential improvements include:

- Expanded role-based access control.
- More detailed ticket analytics and reporting.
- Automated unit and integration testing.
- Improved filtering and search.
- Deployment configuration and production monitoring.
- More comprehensive documentation for staff workflows and SLA policies.

## Project Status

NexaDesk is a DBMS mini-project combining relational data management with a web-based IT complaint workflow. Its current codebase includes FastAPI route modules for tickets, authentication, staff, communications, notifications, and SLA-related functionality, along with SQLAlchemy models, Alembic migrations, and a browser-based frontend.

The exact availability of individual features depends on the current database configuration and application implementation.

## Author

**Priyavarshni R**
