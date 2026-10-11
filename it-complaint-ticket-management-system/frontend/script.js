
const form = document.getElementById("ticketForm");
const submitButton = document.getElementById("submitButton");
const formMessage = document.getElementById("formMessage");
const ticketTable = document.getElementById("ticketTable");
const dashboardMessage = document.getElementById("dashboardMessage");

const historySection = document.getElementById("historySection");
const historyTitle = document.getElementById("historyTitle");
const historyTable = document.getElementById("historyTable");
const closeHistoryButton = document.getElementById("closeHistoryButton");

const STATUSES = ["Open", "In Progress", "Resolved", "Closed"];

// API helper
async function apiRequest(url, options = {}) {
    const response = await fetch(url, options);

    if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(
            error.detail || `Request failed: ${response.status}`
        );
    }

    return response.json();
}

// Load users and categories
async function loadOptions() {
    const [users, categories] = await Promise.all([
        apiRequest("/api/tickets/users"),
        apiRequest("/api/tickets/categories")
    ]);

    const userSelect = document.getElementById("userId");
    const categorySelect = document.getElementById("categoryId");

    userSelect.replaceChildren(
        new Option("Select your name", "")
    );

    categorySelect.replaceChildren(
        new Option("Select category", "")
    );

    users.forEach(user => {
        userSelect.add(
            new Option(
                `${user.name} — ${user.department}`,
                user.user_id
            )
        );
    });

    categories.forEach(category => {
        categorySelect.add(
            new Option(
                category.category_name,
                category.category_id
            )
        );
    });
}

// Create a priority or status badge
function makeBadge(value, type) {
    const badge = document.createElement("span");

    badge.className =
        `badge ${type}-${value.replaceAll(" ", "-")}`;

    badge.textContent = value;

    return badge;
}

// Add content safely to a table cell
function addCell(row, content) {
    const cell = document.createElement("td");

    if (content instanceof Node) {
        cell.appendChild(content);
    } else {
        cell.textContent = content ?? "—";
    }

    row.appendChild(cell);
    return cell;
}

// Update dashboard statistics
function updateStatistics(tickets) {
    document.getElementById("totalTickets").textContent =
        tickets.length;

    document.getElementById("openTickets").textContent =
        tickets.filter(ticket => ticket.status === "Open").length;

    document.getElementById("progressTickets").textContent =
        tickets.filter(
            ticket => ticket.status === "In Progress"
        ).length;

    document.getElementById("resolvedTickets").textContent =
        tickets.filter(ticket =>
            ["Resolved", "Closed"].includes(ticket.status)
        ).length;
}

// Show a message on the dashboard
function showDashboardMessage(message, type = "") {
    dashboardMessage.className = "dashboard-message";

    if (type) {
        dashboardMessage.classList.add(type);
    }

    dashboardMessage.textContent = message;
}

// Format a date safely
function formatDate(value) {
    if (!value) {
        return "—";
    }

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleString();
}

// View the status history for one ticket
async function viewTicketHistory(ticket) {
    historySection.hidden = false;
    historyTitle.textContent =
        `Status History — Ticket #${ticket.ticket_id}`;

    historyTable.replaceChildren();

    const loadingRow = historyTable.insertRow();
    const loadingCell = loadingRow.insertCell();

    loadingCell.colSpan = 4;
    loadingCell.textContent = "Loading status history...";

    try {
        const history = await apiRequest(
            `/api/tickets/${ticket.ticket_id}/history`
        );

        historyTable.replaceChildren();

        if (!Array.isArray(history) || history.length === 0) {
            const row = historyTable.insertRow();
            const cell = row.insertCell();

            cell.colSpan = 4;
            cell.textContent =
                "No status changes have been recorded for this ticket.";

            historySection.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

            return;
        }

        history.forEach(item => {
            const row = historyTable.insertRow();

            addCell(row, item.old_status || "—");
            addCell(row, item.new_status);
            addCell(row, formatDate(item.changed_at));
            addCell(row, item.remarks || "—");
        });

        historySection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    } catch (error) {
        historyTable.replaceChildren();

        const row = historyTable.insertRow();
        const cell = row.insertCell();

        cell.colSpan = 4;
        cell.textContent =
            `Could not load history: ${error.message}`;
    }
}

// Create status controls and history button for each ticket
function createTicketControls(ticket) {
    const controls = document.createElement("div");
    controls.className = "ticket-management";

    // Status dropdown
    const select = document.createElement("select");

    select.setAttribute(
        "aria-label",
        `Status for ticket ${ticket.ticket_id}`
    );

    STATUSES.forEach(status => {
        const option = new Option(status, status);
        option.selected = status === ticket.status;
        select.add(option);
    });

    // Update status button
    const updateButton = document.createElement("button");

    updateButton.type = "button";
    updateButton.className = "update-status-button";
    updateButton.textContent = "Update";
    updateButton.disabled = true;

    select.addEventListener("change", () => {
        updateButton.disabled = select.value === ticket.status;
    });

    updateButton.addEventListener("click", async () => {
        const newStatus = select.value;

        if (newStatus === ticket.status) {
            return;
        }

        select.disabled = true;
        updateButton.disabled = true;
        updateButton.textContent = "Saving...";

        try {
            const result = await apiRequest(
                `/api/tickets/${ticket.ticket_id}/status?new_status=${
                    encodeURIComponent(newStatus)
                }`,
                { method: "PATCH" }
            );

            showDashboardMessage(result.message, "success");

            // Refresh statuses and dashboard counts
            await loadTickets();

            // Reopen history to show the latest recorded change
            await viewTicketHistory({
                ...ticket,
                status: newStatus
            });

        } catch (error) {
            showDashboardMessage(
                `Could not update ticket #${ticket.ticket_id}: ${error.message}`,
                "error"
            );

            select.disabled = false;
            updateButton.textContent = "Update";
            updateButton.disabled = select.value === ticket.status;
        }
    });

    // View History button
    const historyButton = document.createElement("button");

    historyButton.type = "button";
    historyButton.className = "history-button";
    historyButton.textContent = "View History";

    historyButton.addEventListener("click", () => {
        viewTicketHistory(ticket);
    });

    controls.append(select, updateButton, historyButton);

    return controls;
}

// Load and render tickets
async function loadTickets() {
    const tickets = await apiRequest("/api/tickets/");

    updateStatistics(tickets);
    ticketTable.replaceChildren();

    if (tickets.length === 0) {
        const row = ticketTable.insertRow();
        const cell = row.insertCell();

        cell.colSpan = 6;
        cell.textContent = "No complaints have been submitted yet.";
        return;
    }

    tickets.forEach(ticket => {
        const row = ticketTable.insertRow();

        addCell(row, `#${ticket.ticket_id}`);
        addCell(row, ticket.title);
        addCell(row, makeBadge(ticket.priority, "priority"));
        addCell(row, makeBadge(ticket.status, "status"));
        addCell(row, formatDate(ticket.created_at));

        const manageCell = row.insertCell();
        manageCell.appendChild(createTicketControls(ticket));
    });
}

// Submit a new complaint
form.addEventListener("submit", async event => {
    event.preventDefault();

    submitButton.disabled = true;
    formMessage.className = "";
    formMessage.textContent = "Submitting complaint...";

    const payload = {
        user_id: Number(
            document.getElementById("userId").value
        ),
        category_id: Number(
            document.getElementById("categoryId").value
        ),
        title: document.getElementById("title").value.trim(),
        description: document.getElementById("description").value.trim(),
        priority: document.getElementById("priority").value
    };

    try {
        const ticket = await apiRequest("/api/tickets/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        formMessage.className = "success";
        formMessage.textContent =
            `Complaint submitted successfully! Ticket #${ticket.ticket_id}`;

        form.reset();
        document.getElementById("priority").value = "Medium";

        await loadTickets();

    } catch (error) {
        formMessage.className = "error";
        formMessage.textContent = `Error: ${error.message}`;

    } finally {
        submitButton.disabled = false;
    }
});

// Refresh dashboard
document.getElementById("refreshButton").addEventListener(
    "click",
    async () => {
        showDashboardMessage("Refreshing tickets...");

        try {
            await loadTickets();
            showDashboardMessage(
                "Tickets refreshed successfully.",
                "success"
            );

        } catch (error) {
            showDashboardMessage(
                `Could not load tickets: ${error.message}`,
                "error"
            );
        }
    }
);

// Close ticket history
closeHistoryButton.addEventListener("click", () => {
    historySection.hidden = true;
    historyTable.replaceChildren();
});

// Initialize application
async function initializeApp() {
    try {
        await Promise.all([
            loadOptions(),
            loadTickets()
        ]);

    } catch (error) {
        formMessage.className = "error";
        formMessage.textContent =
            `Could not load application data: ${error.message}`;

        ticketTable.replaceChildren();

        const row = ticketTable.insertRow();
        const cell = row.insertCell();

        cell.colSpan = 6;
        cell.textContent =
            "Unable to load tickets. Check the backend.";
    }
}

initializeApp();