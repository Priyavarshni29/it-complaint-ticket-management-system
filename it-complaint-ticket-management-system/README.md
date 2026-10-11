# IT Complaint & Ticket Management System

A DBMS mini-project built with MySQL to register IT complaints, assign them to support staff, track ticket status, maintain status history, and generate basic support reports.

## Features

- Register users and IT support staff
- Categorize complaints (Hardware, Software, Network, Access)
- Create tickets with priority and status
- Allow tickets to remain unassigned until staff is allocated
- Maintain a history of ticket status changes
- Report ticket counts, pending high-priority work, and staff workload
- Demonstrate primary keys, foreign keys, uniqueness, constraints, joins, aggregation, subqueries, and transactions

## Technology

- MySQL 8.0.16 or later
- MySQL Workbench or MySQL command-line client

## Database design

The database contains five tables:

| Table | Purpose |
|---|---|
| `users` | Employees who report IT issues |
| `staff` | IT support staff |
| `categories` | Complaint categories |
| `tickets` | Main complaint/ticket records |
| `ticket_history` | Ticket status-change history |

### Relationships

- One user can create many tickets.
- One staff member can be assigned many tickets.
- One category can contain many tickets.
- One ticket can have many history records.
- `tickets.staff_id` is nullable, so a new ticket can be created before staff assignment.

## Repository structure

```text
it-complaint-ticket-management-system/
├── README.md
├── .gitignore
└── sql/
    └── schema_and_queries.sql
```

## Setup

1. Install MySQL 8.0.16+ and open MySQL Workbench.
2. Open `sql/schema_and_queries.sql`.
3. Execute the script.
4. Refresh the Schemas panel and select `it_complaint_system`.
5. Run the example queries at the end of the script.

**Note:** The script drops and recreates the five project tables so it can be rerun cleanly. Do not run it against a database containing data you need to keep.

## Concepts demonstrated

- **DDL:** `CREATE DATABASE`, `CREATE TABLE`
- **DML:** `INSERT`, `UPDATE`
- **Constraints:** primary keys, foreign keys, `NOT NULL`, `UNIQUE`, `ENUM`
- **Queries:** `JOIN`, `LEFT JOIN`, `GROUP BY`, aggregate functions, `CASE`, subquery
- **Transactions:** status update and history insert are committed together
- **Referential integrity:** foreign keys define valid relationships between records

## Future improvements

- Add a web interface for users and support staff
- Add login and role-based access
- Record assignment changes in an audit log
- Add response-time and resolution-time analytics
- Add automated tests and deployment documentation

## Project status

Database-first starter implementation. A frontend and application backend are not included yet.


## Testing

The database was tested successfully using MySQL 8.0.

- Created and verified all five database tables.
- Inserted sample users, support staff, categories, tickets, and ticket history.
- Executed SQL queries using JOINs, aggregate functions, GROUP BY, and subqueries.
- Tested ticket status updates and transaction-based history recording.
- Verified ticket analytics and staff workload reports.
