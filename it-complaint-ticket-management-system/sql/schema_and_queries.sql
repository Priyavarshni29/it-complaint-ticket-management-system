-- IT Complaint & Ticket Management System
-- DBMS mini-project | MySQL 8.0.16+
-- Run this script in MySQL Workbench or the MySQL command-line client.

CREATE DATABASE IF NOT EXISTS it_complaint_system;
USE it_complaint_system;

-- Drop tables in dependency order so the script can be rerun.
DROP TABLE IF EXISTS ticket_history;
DROP TABLE IF EXISTS tickets;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS staff;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    contact_no VARCHAR(20)
);

CREATE TABLE staff (
    staff_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    specialization VARCHAR(100) NOT NULL,
    contact_no VARCHAR(20)
);

CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(80) NOT NULL UNIQUE,
    description VARCHAR(255)
);

CREATE TABLE tickets (
    ticket_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    staff_id INT NULL,
    category_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    description TEXT NOT NULL,
    priority ENUM('Low', 'Medium', 'High', 'Critical') NOT NULL DEFAULT 'Medium',
    status ENUM('Open', 'In Progress', 'Resolved', 'Closed') NOT NULL DEFAULT 'Open',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME NULL,
    CONSTRAINT fk_tickets_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_tickets_staff
        FOREIGN KEY (staff_id) REFERENCES staff(staff_id)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT fk_tickets_category
        FOREIGN KEY (category_id) REFERENCES categories(category_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE ticket_history (
    history_id INT AUTO_INCREMENT PRIMARY KEY,
    ticket_id INT NOT NULL,
    old_status ENUM('Open', 'In Progress', 'Resolved', 'Closed') NULL,
    new_status ENUM('Open', 'In Progress', 'Resolved', 'Closed') NOT NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remarks VARCHAR(500),
    CONSTRAINT fk_history_ticket
        FOREIGN KEY (ticket_id) REFERENCES tickets(ticket_id)
        ON UPDATE CASCADE ON DELETE CASCADE
);

-- Starter/reference data
INSERT INTO users (name, email, department, contact_no) VALUES
('Arun Kumar', 'arun@example.com', 'Finance', '9000000001'),
('Meena Ravi', 'meena@example.com', 'Human Resources', '9000000002'),
('Karthik S', 'karthik@example.com', 'Engineering', '9000000003');

INSERT INTO staff (name, email, specialization, contact_no) VALUES
('Divya N', 'divya.it@example.com', 'Hardware', '9110000001'),
('Rahul P', 'rahul.it@example.com', 'Network', '9110000002'),
('Sneha M', 'sneha.it@example.com', 'Software', '9110000003');

INSERT INTO categories (category_name, description) VALUES
('Hardware', 'Computer, keyboard, mouse, printer, and device issues'),
('Software', 'Application, operating system, and software issues'),
('Network', 'Wi-Fi, LAN, VPN, and connectivity issues'),
('Access', 'Account, login, and permission issues');

INSERT INTO tickets
(user_id, staff_id, category_id, title, description, priority, status)
VALUES
(1, 1, 1, 'Keyboard not working', 'Some keyboard keys do not respond.', 'Medium', 'In Progress'),
(2, 2, 3, 'Wi-Fi disconnecting', 'Connection drops several times a day.', 'High', 'Open'),
(3, 3, 2, 'Application fails to launch', 'The internal application closes on startup.', 'Critical', 'Resolved');

-- Record initial status history for the sample tickets.
INSERT INTO ticket_history (ticket_id, old_status, new_status, remarks) VALUES
(1, NULL, 'Open', 'Ticket registered'),
(1, 'Open', 'In Progress', 'Assigned to hardware support'),
(2, NULL, 'Open', 'Ticket registered'),
(3, NULL, 'Open', 'Ticket registered'),
(3, 'Open', 'Resolved', 'Application issue fixed');

UPDATE tickets
SET resolved_at = CURRENT_TIMESTAMP
WHERE ticket_id = 3;

-- Useful demonstration queries

-- 1. View tickets with requester, category, and assigned staff.
SELECT
    t.ticket_id, t.title, u.name AS requester,
    c.category_name, s.name AS assigned_staff,
    t.priority, t.status, t.created_at
FROM tickets AS t
JOIN users AS u ON t.user_id = u.user_id
JOIN categories AS c ON t.category_id = c.category_id
LEFT JOIN staff AS s ON t.staff_id = s.staff_id
ORDER BY t.created_at DESC;

-- 2. Count tickets by status.
SELECT status, COUNT(*) AS ticket_count
FROM tickets
GROUP BY status;

-- 3. Count tickets handled by each staff member, including staff with zero tickets.
SELECT s.staff_id, s.name, COUNT(t.ticket_id) AS assigned_tickets
FROM staff AS s
LEFT JOIN tickets AS t ON s.staff_id = t.staff_id
GROUP BY s.staff_id, s.name
ORDER BY assigned_tickets DESC;

-- 4. Find open/high-priority work.
SELECT ticket_id, title, priority, status
FROM tickets
WHERE status IN ('Open', 'In Progress')
  AND priority IN ('High', 'Critical')
ORDER BY FIELD(priority, 'Critical', 'High');

-- 5. Find tickets whose priority is above the average priority ranking.
-- Map priority labels to numbers for a simple aggregate/subquery demonstration.
SELECT ticket_id, title, priority
FROM tickets
WHERE CASE priority
        WHEN 'Low' THEN 1
        WHEN 'Medium' THEN 2
        WHEN 'High' THEN 3
        WHEN 'Critical' THEN 4
      END >
      (SELECT AVG(
          CASE priority
            WHEN 'Low' THEN 1
            WHEN 'Medium' THEN 2
            WHEN 'High' THEN 3
            WHEN 'Critical' THEN 4
          END
       ) FROM tickets);

-- 6. View the history of a ticket.
SELECT h.history_id, h.ticket_id, h.old_status, h.new_status,
       h.changed_at, h.remarks
FROM ticket_history AS h
WHERE h.ticket_id = 1
ORDER BY h.changed_at;

-- 7. Analytics summary.
SELECT
    COUNT(*) AS total_tickets,
    SUM(status = 'Open') AS open_tickets,
    SUM(status = 'In Progress') AS in_progress_tickets,
    SUM(status = 'Resolved') AS resolved_tickets,
    SUM(status = 'Closed') AS closed_tickets
FROM tickets;

-- Transaction example: update a ticket status and write its history together.
-- Run as a separate transaction when demonstrating status changes.
START TRANSACTION;

SELECT status INTO @previous_status
FROM tickets
WHERE ticket_id = 2
FOR UPDATE;

UPDATE tickets
SET status = 'In Progress'
WHERE ticket_id = 2;

INSERT INTO ticket_history (ticket_id, old_status, new_status, remarks)
VALUES (2, @previous_status, 'In Progress', 'Work started by IT support');

COMMIT;

-- Verify the transaction.
SELECT ticket_id, status FROM tickets WHERE ticket_id = 2;
SELECT * FROM ticket_history WHERE ticket_id = 2 ORDER BY changed_at;
