# IT Complaint & Ticket Management System

A web-based DBMS mini-project for registering IT complaints, tracking ticket status, maintaining status-change history, and managing IT support operations. The application uses **FastAPI** for the backend, **MySQL** for persistent storage, and a simple web frontend built with HTML, CSS, and JavaScript.

## Features

- Register IT complaints with a user, category, priority, and description.
- View and track submitted tickets.
- Categorize complaints as Hardware, Software, Network, or Access.
- Update ticket status through the web portal.
- Record ticket status changes in a history table.
- Display ticket statistics and support information through the portal.
- Store ticket, user, staff, category, and history data in MySQL.
- Expose REST API endpoints through FastAPI.
- Provide a database health-check endpoint.
- Explore and test API endpoints through interactive Swagger documentation.

## Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | MySQL 8.0 |
| ORM and database access | SQLAlchemy, PyMySQL |
| Configuration | python-dotenv |
| Frontend | HTML, CSS, JavaScript |
| API documentation | FastAPI / Swagger UI |
| Database GUI | MySQL Workbench |

## Application Architecture

The application follows a simple three-layer architecture:

1. **Frontend:** Provides the web interface for submitting complaints and viewing ticket information.
2. **Backend:** FastAPI processes API requests, applies ticket-management logic, and communicates with MySQL through SQLAlchemy.
3. **Database:** MySQL stores application data and ticket status history.

```text
User
 |
 v
Web Frontend (HTML, CSS, JavaScript)
 |
 v
FastAPI Backend
 |
 v
SQLAlchemy + PyMySQL
 |
 v
MySQL Database
 |
 +-- users
 +-- staff
 +-- categories
 +-- tickets
 +-- ticket_history
```

## Database Design

The database is named `it_complaint_system` and contains five main tables.

| Table | Purpose |
|---|---|
| `users` | Stores employees who report IT issues. |
| `staff` | Stores IT support staff information. |
| `categories` | Stores complaint categories. |
| `tickets` | Stores complaint details, priority, assignment, and status. |
| `ticket_history` | Records ticket status changes and related history information. |

### Relationships

- One user can create multiple tickets.
- One staff member can be assigned multiple tickets.
- One category can be associated with multiple tickets.
- One ticket can have multiple history records.
- A ticket can remain unassigned until support staff are allocated.

### DBMS Concepts Demonstrated

- Primary keys and foreign keys
- `NOT NULL`, `UNIQUE`, and other integrity constraints
- One-to-many relationships
- SQL `JOIN` and `LEFT JOIN`
- Aggregate functions and `GROUP BY`
- Subqueries and conditional expressions
- Transactions and status-history recording
- Data retrieval, insertion, and updates

## Project Structure

```text
it-complaint-ticket-management-system/
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── routes/
│       ├── __init__.py
│       └── tickets.py
├── frontend/
│   ├── index.html
│   ├── script.js
│   └── style.css
├── sql/
│   └── schema_and_queries.sql
├── .env.example
├── .gitignore
└── README.md
```

## Prerequisites

Install the following before running the application:

- Python 3.10 or later
- MySQL Server 8.0
- Git
- A web browser

MySQL Workbench is optional and can be used to view tables and execute SQL queries.

## Setup and Installation

### 1. Clone the repository

```bash
git clone https://github.com/Priyavarshni29/it-complaint-ticket-management-system.git
cd it-complaint-ticket-management-system
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks script execution, activate the environment using an appropriate local policy or use Command Prompt:

```bat
venv\Scripts\activate.bat
```

### 3. Install dependencies

```bash
pip install fastapi "uvicorn[standard]" sqlalchemy pymysql python-dotenv
```

### 4. Configure environment variables

Create a local `.env` file in the project root using `.env.example` as a template.

Configure the following variables with your own local MySQL credentials:

```dotenv
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=it_complaint_system
```

Do not commit your actual `.env` file or database password to GitHub.

### 5. Create the database

Open MySQL Workbench or the MySQL command-line client and execute the SQL script:

```text
sql/schema_and_queries.sql
```

**Important:** Review the script before running it. It drops and recreates project tables, so do not execute it against a database containing data you need to preserve.

Ensure that the database and tables are created successfully before starting the application.

### 6. Start the application

Run this command from the project root:

```bash
uvicorn app.main:app --reload
```

Open the application in your browser:

- **Web portal:** http://127.0.0.1:8000/
- **Swagger API documentation:** http://127.0.0.1:8000/docs
- **Database health check:** http://127.0.0.1:8000/health/db

The database health-check endpoint verifies the connection and returns the database name when the connection succeeds.

## API Overview

The ticket API includes endpoints for creating, listing, and retrieving tickets, updating ticket status, and viewing ticket history. Additional endpoints provide user and category information.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/tickets/` | Create a ticket |
| `GET` | `/api/tickets/` | List tickets |
| `GET` | `/api/tickets/{ticket_id}` | Retrieve a ticket |
| `GET` | `/api/tickets/users` | Retrieve users |
| `GET` | `/api/tickets/categories` | Retrieve categories |
| `PATCH` | `/api/tickets/{ticket_id}/status` | Update ticket status |
| `GET` | `/api/tickets/{ticket_id}/history` | Retrieve ticket history |

Refer to `/docs` for request parameters, schemas, and interactive API testing.

## Testing and Verification

The project has been tested locally with MySQL and MySQL Workbench.

- Verified the five database tables and their records.
- Tested ticket creation and retrieval through the application.
- Updated ticket status through the web portal.
- Verified the updated ticket status in MySQL Workbench.
- Checked ticket status-history records in the database.
- Verified that the frontend, backend, and database work together.

## Future Improvements

- Add user authentication and role-based access control.
- Introduce staff assignment workflows.
- Add automated backend and API tests.
- Improve ticket filtering and reporting.
- Add deployment documentation for hosting the application.

## Project Status

The project includes a FastAPI backend, a browser-based frontend, a MySQL database schema, and ticket status-history tracking. It has been tested locally using MySQL Workbench.

This project was developed as a DBMS mini-project to demonstrate relational database design, SQL operations, backend integration, and a working web interface.

## Author 
Priyavarshni R
