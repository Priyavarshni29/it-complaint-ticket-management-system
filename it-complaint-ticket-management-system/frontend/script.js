"use strict";

const state = {
  account: null,
  token: null,
  portal: "User",
  tickets: [],
  categories: [],
  staffProfile: null,
  currentTicket: null,
  currentView: "overview"
};

const $ = id => document.getElementById(id);

const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;"
}[ch]));

function showMessage(id, text, type = "") {
  const el = $(id);
  if (!el) return;
  el.textContent = text || "";
  el.className = "message" + (type ? ` ${type}` : "");
}

function show(id) { $(id)?.classList.remove("hidden"); }
function hide(id) { $(id)?.classList.add("hidden"); }
function isStaff() { return state.account?.role === "Staff"; }

function isLead() {
  return state.account?.role === "Admin" ||
    Boolean(state.staffProfile?.is_team_lead || state.account?.is_team_lead);
}

function isUser() { return state.account?.role === "User"; }

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, { ...options, headers });
  const raw = await response.text();
  let data = null;

  if (raw) {
    try { data = JSON.parse(raw); }
    catch { data = raw; }
  }

  if (!response.ok) {
    const detail = data && typeof data === "object" ? data.detail : data;
    throw new Error(detail || `Request failed (${response.status})`);
  }

  return data;
}

function button(label, action, extra = "") {
  return `<button type="button" class="btn ${extra}" data-action="${action}">${label}</button>`;
}

function statusBadge(status) {
  const key = String(status || "Open").toLowerCase().replace(/\s+/g, "-");
  return `<span class="badge status-${esc(key)}">${esc(status || "Open")}</span>`;
}

function priorityBadge(priority) {
  const key = String(priority || "Medium").toLowerCase();
  return `<span class="badge priority-${esc(key)}">${esc(priority || "Medium")}</span>`;
}

function slaBadge(breached) {
  return breached
    ? '<span class="badge sla-bad">Breached</span>'
    : '<span class="badge sla-good">Within SLA</span>';
}

function fmtDate(value) {
  if (!value) return "Not recorded";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? esc(value) : d.toLocaleString();
}

function duration(value) {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }

  const minutes = Math.max(0, Math.ceil(Number(value) / 60));
  if (!Number.isFinite(minutes)) return "Not available";

  if (minutes < 60) return `${minutes}m`;

  const days = Math.floor(minutes / 1440);
  const hours = Math.floor((minutes % 1440) / 60);
  const rest = minutes % 60;

  if (days > 0) return `${days}d ${hours}h ${rest}m`;
  return `${Math.floor(minutes / 60)}h ${rest}m`;
}

function deadlineText(deadline) {
  if (!deadline) return "Not set";

  const remaining = (new Date(deadline).getTime() - Date.now()) / 1000;
  if (!Number.isFinite(remaining)) return "Not set";
  if (remaining <= 0) return `Overdue by ${duration(Math.abs(remaining))}`;

  return `${duration(remaining)} remaining`;
}

function categoryName(ticket) {
  if (ticket.category && typeof ticket.category === "object") {
    return ticket.category.category_name ||
      ticket.category.name ||
      ticket.category_id ||
      "—";
  }

  const category = state.categories.find(
    c => String(c.category_id) === String(ticket.category_id)
  );

  return category?.category_name ||
    ticket.category_name ||
    ticket.category_id ||
    "—";
}

function setButtonLoading(buttonElement, loading, original) {
  if (!buttonElement) return;
  buttonElement.disabled = loading;
  buttonElement.textContent = loading ? "Please wait…" : original;
}

/* Authentication mode and role selection */
document.querySelectorAll("[data-role]").forEach(btn => {
  btn.addEventListener("click", () => {
    state.portal = btn.dataset.role;

    document.querySelectorAll("[data-role]").forEach(other =>
      other.classList.toggle("selected", other === btn)
    );

    $("authHeading").textContent = `Sign in as ${state.portal}`;
    $("authDescription").textContent = "Use your existing NexaDesk account.";
  });
});

document.querySelectorAll("[data-auth-mode]").forEach(btn => {
  btn.addEventListener("click", () => setAuthMode(btn.dataset.authMode));
});

function setAuthMode(mode) {
  document.querySelectorAll("[data-auth-mode]").forEach(btn =>
    btn.classList.toggle("active", btn.dataset.authMode === mode)
  );

  $("loginForm").classList.toggle("hidden", mode !== "login");
  $("signupForm").classList.toggle("hidden", mode !== "signup");

  $("authHeading").textContent =
    mode === "login" ? "Welcome back" : "Create your account";

  $("authDescription").textContent = mode === "login"
    ? "Sign in to continue to your NexaDesk workspace."
    : "Create a user account to submit and track complaints.";

  showMessage("loginMessage", "");
  showMessage("signupMessage", "");
}

$("loginForm").addEventListener("submit", async event => {
  event.preventDefault();

  const btn = $("loginButton");
  setButtonLoading(btn, true, "Sign in securely");
  showMessage("loginMessage", "");

  try {
    const form = new URLSearchParams();
    form.set("username", $("loginEmail").value.trim());
    form.set("password", $("loginPassword").value);

    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Login failed");

    state.token = data.access_token;
    const account = await api("/api/auth/me");
    state.account = account;

    if (
      state.portal === "Team Lead" &&
      account.role !== "Staff" &&
      account.role !== "Admin"
    ) {
      throw new Error("This account is not a Team Lead account.");
    }

    if (state.portal === "Staff" && account.role !== "Staff") {
      throw new Error("Please choose the correct portal for this account.");
    }

    await openDashboard();
  } catch (error) {
    state.token = null;
    state.account = null;
    showMessage("loginMessage", error.message, "error");
  } finally {
    setButtonLoading(btn, false, "Sign in securely");
  }
});

$("signupForm").addEventListener("submit", async event => {
  event.preventDefault();

  const btn = $("signupButton");
  setButtonLoading(btn, true, "Create account");

  try {
    await api("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        name: $("signupName").value.trim(),
        email: $("signupEmail").value.trim(),
        department: $("signupDepartment").value.trim(),
        password: $("signupPassword").value
      })
    });

    showMessage("signupMessage", "Account created. You can now sign in.", "success");
    $("signupForm").reset();
    setAuthMode("login");
  } catch (error) {
    showMessage("signupMessage", error.message, "error");
  } finally {
    setButtonLoading(btn, false, "Create account");
  }
});

async function openDashboard() {
  hide("welcomeSection");
  show("dashboardSection");
  show("topbarUser");
  show("topbarLogout");

  const name = state.account?.name || state.account?.email || "User";

  $("topbarUser").textContent = name;
  $("sidebarName").textContent = name;
  $("profileAvatar").textContent = name.charAt(0).toUpperCase();
  $("sidebarRole").textContent = state.account.role;
  $("roleBadge").textContent = state.account.role;
  $("welcomeMessage").textContent = `Welcome back, ${name}`;

  const staffRole = isStaff();
  const leadRole = isLead();

  $("navNewTicket").classList.toggle("hidden", !isUser());
  $("navAvailability").classList.toggle("hidden", !staffRole);
  $("navQueue").classList.toggle("hidden", !staffRole && !leadRole);
  $("navStaff").classList.toggle("hidden", !leadRole);
  $("navStaffChat").classList.toggle(
    "hidden",
    !staffRole && state.account.role !== "Admin"
  );

  $("overviewCardTitle").textContent =
    isUser() ? "Welcome to NexaDesk" : "Support workspace";

  $("overviewCardText").textContent = isUser()
    ? "Submit a complaint and track updates from your dashboard."
    : "Review tickets, deadlines, notifications and team messages.";

  $("overviewAction").textContent =
    isUser() ? "Submit complaint" : "View tickets";

  if (staffRole) {
    try {
      state.staffProfile = await api("/api/staff/me");

      $("sidebarRole").textContent =
        state.staffProfile.is_team_lead ? "Team Lead" : "Staff";

      $("roleBadge").textContent =
        state.staffProfile.is_team_lead ? "Team Lead" : "Staff";

      $("navQueue").classList.remove("hidden");
      $("navStaffChat").classList.remove("hidden");
      $("navStaff").classList.toggle(
        "hidden",
        !state.staffProfile.is_team_lead
      );
    } catch (error) {
      console.warn("Staff profile could not be loaded:", error);
    }
  }

  await loadCategories();
  await loadTickets();
  await loadNotificationCount();
  showView("overview");
}

function logout() {
  state.account = null;
  state.token = null;
  state.tickets = [];
  state.categories = [];
  state.staffProfile = null;
  state.currentTicket = null;

  $("dashboardSection").classList.add("hidden");
  $("welcomeSection").classList.remove("hidden");
  $("topbarUser").classList.add("hidden");
  $("topbarLogout").classList.add("hidden");

  $("loginForm").reset();
  $("signupForm").reset();
  setAuthMode("login");
}

function flashLogout(btn) {
  btn.classList.add("clicked", "btn-danger");

  setTimeout(() => {
    btn.classList.remove("clicked", "btn-danger");
    logout();
  }, 180);
}

$("sidebarLogout").addEventListener("click", event =>
  flashLogout(event.currentTarget)
);

$("topbarLogout").addEventListener("click", event =>
  flashLogout(event.currentTarget)
);

/* Navigation */
const views = [
  "overview", "tickets", "newTicket", "history", "details",
  "availability", "queue", "staff", "notifications", "sla",
  "staffChat", "about", "contact"
];

const titles = {
  overview: "Overview",
  tickets: "Tickets",
  newTicket: "Submit Complaint",
  history: "Ticket History",
  details: "Ticket Details",
  availability: "My Availability",
  queue: "Unassigned Queue",
  staff: "Staff Management",
  notifications: "Notifications",
  sla: "SLA Monitor",
  staffChat: "Team Chat",
  about: "About NexaDesk",
  contact: "Contact"
};

function showView(view) {
  if (!state.account) return;
  if (view === "newTicket" && !isUser()) return;
  if (view === "availability" && !isStaff()) return;
  if (view === "staff" && !isLead()) return;
  if (view === "queue" && !isStaff() && !isLead()) return;
  if (view === "staffChat" && !isStaff() && state.account.role !== "Admin") return;

  views.forEach(name => {
    const section = $(name + "View");
    if (section) section.classList.toggle("hidden", name !== view);
  });

  document.querySelectorAll("[data-view]").forEach(btn =>
    btn.classList.toggle("active", btn.dataset.view === view)
  );

  state.currentView = view;
  $("dashboardTitle").textContent = titles[view] || "Dashboard";

  if (view === "tickets") loadTickets();
  if (view === "history") populateHistory();
  if (view === "availability") loadAvailability();
  if (view === "queue") loadQueue();
  if (view === "staff") loadStaffDirectory();
  if (view === "notifications") loadNotifications();
  if (view === "sla") loadSla();
  if (view === "staffChat") loadStaffChat();

  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.querySelectorAll("[data-view]").forEach(btn =>
  btn.addEventListener("click", () => showView(btn.dataset.view))
);

$("overviewAction").addEventListener("click", () =>
  showView(isUser() ? "newTicket" : "tickets")
);

document.querySelectorAll("[data-refresh]").forEach(btn =>
  btn.addEventListener("click", loadTickets)
);

/* Categories and tickets */
async function loadCategories() {
  try {
    const data = await api("/api/tickets/categories");
    state.categories = Array.isArray(data) ? data : [];

    $("categoryId").innerHTML =
      '<option value="">Choose a category</option>';

    state.categories.forEach(category => {
      const option = document.createElement("option");
      option.value = category.category_id;
      option.textContent = category.category_name;
      $("categoryId").appendChild(option);
    });
  } catch (error) {
    showMessage("formMessage", `Could not load categories: ${error.message}`, "error");
  }
}

async function loadTickets() {
  if (!state.token) return;

  try {
    const data = await api("/api/tickets/");
    state.tickets = Array.isArray(data) ? data : [];

    updateStats();
    renderTickets("overviewTable");
    renderTickets("ticketTable");
    populateHistory();
  } catch (error) {
    showMessage("ticketMessage", error.message, "error");

    ["overviewTable", "ticketTable"].forEach(id => {
      if ($(id)) {
        $(id).innerHTML =
          `<tr><td colspan="6">${esc(error.message)}</td></tr>`;
      }
    });
  }
}

function updateStats() {
  $("totalTickets").textContent = state.tickets.length;
  $("openTickets").textContent =
    state.tickets.filter(t => t.status === "Open").length;
  $("progressTickets").textContent =
    state.tickets.filter(t => t.status === "In Progress").length;
  $("resolvedTickets").textContent =
    state.tickets.filter(t => ["Resolved", "Closed"].includes(t.status)).length;
}

function renderTickets(targetId) {
  const target = $(targetId);
  if (!target) return;

  if (!state.tickets.length) {
    target.innerHTML =
      '<tr><td colspan="6" class="empty-state">No tickets found.</td></tr>';
    return;
  }

  target.innerHTML = state.tickets.map(ticket => {
    const id = ticket.ticket_id;
    const status = statusBadge(ticket.status);
    const priority = priorityBadge(ticket.priority);
    const category = esc(categoryName(ticket));

    let actions =
      `<div class="table-actions">
        ${button("Details", `details:${id}`, "btn-primary")}
        ${button("History", `history:${id}`, "btn-light")}
      </div>`;

    if (isStaff() || isLead() || state.account.role === "Admin") {
      actions =
        `<div class="table-actions">
          ${button("Details", `details:${id}`, "btn-primary")}
          ${button("History", `history:${id}`, "btn-light")}
          <select aria-label="New status for ticket ${id}"
                  data-status-select="${id}"
                  class="inline-status">
            ${["Open", "In Progress", "Resolved", "Closed"].map(s =>
              `<option ${s === ticket.status ? "selected" : ""}>${s}</option>`
            ).join("")}
          </select>
        </div>`;
    }

    return `<tr>
      <td>#${esc(id)}</td>
      <td>${esc(ticket.title)}</td>
      <td>${category}</td>
      <td>${priority}</td>
      <td>${status}</td>
      <td>${actions}</td>
    </tr>`;
  }).join("");
}

$("ticketForm").addEventListener("submit", async event => {
  event.preventDefault();

  const btn = $("submitButton");
  setButtonLoading(btn, true, "Submit complaint");

  try {
    const result = await api("/api/tickets/", {
      method: "POST",
      body: JSON.stringify({
        title: $("ticketTitle").value.trim(),
        category_id: Number($("categoryId").value),
        priority: $("priority").value,
        description: $("ticketDescription").value.trim()
      })
    });

    $("ticketForm").reset();
    await loadCategories();
    await loadTickets();

    showMessage(
      "formMessage",
      `Complaint submitted successfully${result.ticket_id ? ` (Ticket #${result.ticket_id})` : ""}.`,
      "success"
    );

    showView("tickets");
  } catch (error) {
    showMessage("formMessage", error.message, "error");
  } finally {
    setButtonLoading(btn, false, "Submit complaint");
  }
});
/* Ticket details */
async function openDetails(id) {
  state.currentTicket = id;
  showView("details");

  $("detailsHeading").textContent = `Ticket #${id}`;
  $("ticketDetailsContent").innerHTML =
    '<p class="muted">Loading ticket details…</p>';

  hide("statusActions");
  hide("ticketConversation");

  try {
    const ticket = await api(`/api/tickets/${id}`);
    state.currentTicket = id;

    $("detailsHeading").textContent =
      `Ticket #${id}: ${ticket.title || ""}`;

    const assignedStaff =
      ticket.assigned_staff?.name ||
      ticket.staff?.name ||
      ticket.assigned_staff_name ||
      ticket.staff_name ||
      (ticket.staff_id ? `Staff #${ticket.staff_id}` : "Not assigned");

    const details = [
      ["Title", ticket.title, true],
      ["Description", ticket.description, true],
      ["Category", categoryName(ticket)],
      ["Priority", priorityBadge(ticket.priority), false, true],
      ["Status", statusBadge(ticket.status), false, true],
      ["Assigned staff", assignedStaff],
      ["Created", fmtDate(ticket.created_at)],
      ["Response deadline", fmtDate(ticket.response_due_at)],
      ["Resolution deadline", fmtDate(ticket.resolution_due_at)],
      ["First response", fmtDate(ticket.first_response_at)],
      ["Response SLA", slaBadge(Boolean(ticket.response_sla_breached)), false, true],
      ["Resolution SLA", slaBadge(Boolean(ticket.resolution_sla_breached)), false, true]
    ];

    $("ticketDetailsContent").innerHTML =
      `<div class="detail-grid">${
        details.map(([label, value, full, html]) =>
          `<div class="detail-card ${full ? "full" : ""}">
            <label>${esc(label)}</label>
            <div class="detail-value">${html ? value : esc(value)}</div>
          </div>`
        ).join("")
      }</div>`;

    if (isStaff() || isLead() || state.account.role === "Admin") {
      show("statusActions");
      $("newStatus").value = ticket.status || "Open";
    }

    show("ticketConversation");

    const visibilitySelect = $("ticketMessageVisibility");
    if (visibilitySelect) {
      visibilitySelect.classList.toggle("hidden", isUser());
      visibilitySelect.value = "Public";
    }

    const messageLabel = document.querySelector(
      'label[for="ticketMessageText"]'
    );

    if (messageLabel) {
      messageLabel.textContent = isUser()
        ? "Write a reply to IT Support"
        : "Write a reply or internal note";
    }

    await loadTicketMessages(id);
  } catch (error) {
    $("ticketDetailsContent").innerHTML =
      `<p class="message error">${esc(error.message)}</p>`;
  }
}

$("closeDetailsButton").addEventListener("click", () => showView("tickets"));

$("updateStatusButton").addEventListener("click", async () => {
  if (!state.currentTicket) return;

  try {
    await api(
      `/api/tickets/${state.currentTicket}/status?new_status=${encodeURIComponent($("newStatus").value)}`,
      { method: "PATCH" }
    );

    showMessage("statusMessage", "Ticket status updated.", "success");

    const id = state.currentTicket;
    await loadTickets();
    await openDetails(id);
  } catch (error) {
    showMessage("statusMessage", error.message, "error");
  }
});

/* Ticket history */
function populateHistory() {
  const select = $("historyTicketId");
  if (!select) return;

  const current = select.value;
  select.innerHTML = '<option value="">Select a ticket</option>';

  state.tickets.forEach(t => {
    const option = document.createElement("option");
    option.value = t.ticket_id;
    option.textContent = `#${t.ticket_id} — ${t.title}`;
    select.appendChild(option);
  });

  if (current) select.value = current;
}

$("loadHistoryButton").addEventListener("click", () =>
  loadHistory($("historyTicketId").value)
);

async function loadHistory(id) {
  if (!id) {
    showMessage("historyMessage", "Choose a ticket first.", "error");
    return;
  }

  try {
    const rows = await api(`/api/tickets/${id}/history`);

    $("historyTable").innerHTML = rows.length
      ? rows.map(row =>
          `<tr>
            <td>${statusBadge(row.old_status || "—")}</td>
            <td>${statusBadge(row.new_status || "—")}</td>
            <td>${esc(row.remarks || "—")}</td>
            <td>${fmtDate(row.changed_at)}</td>
          </tr>`
        ).join("")
      : '<tr><td colspan="4" class="empty-state">No history recorded.</td></tr>';

    showMessage("historyMessage", `History for ticket #${id}`, "success");
  } catch (error) {
    showMessage("historyMessage", error.message, "error");
  }
}

document.addEventListener("click", event => {
  const btn = event.target.closest("[data-action]");
  if (!btn) return;

  const [action, id] = btn.dataset.action.split(":");

  if (action === "details") openDetails(id);

  if (action === "history") {
    showView("history");
    $("historyTicketId").value = id;
    loadHistory(id);
  }
});

/* Status dropdown updates immediately without a separate Save button */
document.addEventListener("change", async event => {
  const select = event.target.closest("[data-status-select]");
  if (!select) return;

  const id = select.dataset.statusSelect;
  const chosen = select.value;

  select.disabled = true;

  try {
    await api(
      `/api/tickets/${id}/status?new_status=${encodeURIComponent(chosen)}`,
      { method: "PATCH" }
    );

    await loadTickets();
  } catch (error) {
    alert(`Could not update status: ${error.message}`);
    await loadTickets();
  } finally {
    select.disabled = false;
  }
});

/* Staff availability */
async function loadAvailability() {
  try {
    const profile = await api("/api/staff/me");
    state.staffProfile = profile;

    const available = Boolean(profile.is_available);

    $("myAvailabilityLabel").textContent =
      available ? "You are available" : "You are unavailable";

    $("myAvailabilityDescription").textContent = available
      ? "You can receive new ticket assignments."
      : "You will not receive new ticket assignments.";

    $("availabilityToggle").textContent =
      available ? "Set unavailable" : "Set available";

    /* Both availability actions remain blue */
    $("availabilityToggle").className = "btn btn-primary";
    $("availabilityToggle").disabled = false;
    $("myActiveTickets").textContent = profile.active_tickets ?? 0;
  } catch (error) {
    showMessage("availabilityMessage", error.message, "error");
  }
}

$("availabilityToggle").addEventListener("click", async () => {
  const btn = $("availabilityToggle");
  const next = !state.staffProfile?.is_available;

  btn.disabled = true;

  try {
    await api("/api/staff/me/availability", {
      method: "PATCH",
      body: JSON.stringify({ is_available: next })
    });

    showMessage("availabilityMessage", "Availability updated.", "success");
    await loadAvailability();
  } catch (error) {
    showMessage("availabilityMessage", error.message, "error");
    btn.disabled = false;
  }
});

/* Unassigned ticket queue */
async function loadQueue() {
  try {
    const rows = await api("/api/tickets/unassigned");

    $("queueTable").innerHTML = rows.length
      ? rows.map(t =>
          `<tr>
            <td>#${esc(t.ticket_id)}</td>
            <td>${esc(t.title)}</td>
            <td>${esc(categoryName(t))}</td>
            <td>${priorityBadge(t.priority)}</td>
            <td>${statusBadge(t.status)}</td>
            <td>${button("Claim", `claim:${t.ticket_id}`, "btn-primary")}</td>
          </tr>`
        ).join("")
      : '<tr><td colspan="6" class="empty-state">No unassigned tickets.</td></tr>';

    showMessage("queueMessage", `${rows.length} unassigned ticket(s).`, "success");
  } catch (error) {
    showMessage("queueMessage", error.message, "error");
  }
}

$("refreshQueueButton").addEventListener("click", loadQueue);

document.addEventListener("click", async event => {
  const btn = event.target.closest('[data-action^="claim:"]');
  if (!btn) return;

  const id = btn.dataset.action.split(":")[1];
  btn.disabled = true;

  try {
    await api(`/api/tickets/${id}/claim`, { method: "POST" });

    showMessage("queueMessage", `Ticket #${id} claimed successfully.`, "success");

    await loadQueue();
    await loadTickets();
  } catch (error) {
    showMessage("queueMessage", error.message, "error");
    btn.disabled = false;
  }
});

/* Staff directory and availability administration */
async function loadStaffDirectory() {
  try {
    const rows = await api("/api/staff/");

    $("staffDirectoryTable").innerHTML = rows.length
      ? rows.map(s => {
          const available = Boolean(s.is_available);

          return `<tr>
            <td>${esc(s.staff_id)}</td>
            <td>${esc(s.name)}</td>
            <td>${esc(s.email)}</td>
            <td>${esc(s.specialization)}</td>
            <td>${esc(s.support_level)}</td>
            <td>${
              available
                ? '<span class="badge sla-good">Available</span>'
                : '<span class="badge sla-bad">Unavailable</span>'
            }</td>
            <td>${esc(s.active_tickets ?? 0)}</td>
            <td>${button(
              available ? "Set unavailable" : "Set available",
              `availability:${s.staff_id}:${!available}`,
              "btn-primary"
            )}</td>
          </tr>`;
        }).join("")
      : '<tr><td colspan="8" class="empty-state">No staff records found.</td></tr>';

    showMessage("staffDirectoryMessage", "Staff directory loaded.", "success");
  } catch (error) {
    showMessage("staffDirectoryMessage", error.message, "error");
  }
}

$("refreshStaffButton").addEventListener("click", loadStaffDirectory);

document.addEventListener("click", async event => {
  const btn = event.target.closest('[data-action^="availability:"]');
  if (!btn) return;

  const [, id, value] = btn.dataset.action.split(":");
  btn.disabled = true;

  try {
    await api(`/api/staff/${id}/availability`, {
      method: "PATCH",
      body: JSON.stringify({ is_available: value === "true" })
    });

    await loadStaffDirectory();
  } catch (error) {
    showMessage("staffDirectoryMessage", error.message, "error");
    btn.disabled = false;
  }
});

/* Staff account creation */
$("staffForm").addEventListener("submit", async event => {
  event.preventDefault();

  const btn = $("staffSubmitButton");
  setButtonLoading(btn, true, "Create staff login");

  try {
    await api("/api/auth/staff-register", {
      method: "POST",
      body: JSON.stringify({
        staff_id: Number($("staffId").value),
        email: $("staffEmail").value.trim(),
        password: $("staffPassword").value
      })
    });

    $("staffForm").reset();
    showMessage("staffMessage", "Staff login created.", "success");
  } catch (error) {
    showMessage("staffMessage", error.message, "error");
  } finally {
    setButtonLoading(btn, false, "Create staff login");
  }
});

/* Notifications */
async function loadNotificationCount() {
  try {
    const result = await api("/api/notifications/unread-count");
    const count = Number(result.unread_count ?? result.count ?? 0);

    $("notificationBadge").textContent = count;
    $("notificationBadge").classList.toggle("hidden", count === 0);
  } catch {
    /* Keep the dashboard usable if the count endpoint fails. */
  }
}

async function loadNotifications() {
  try {
    const rows = await api("/api/notifications/");

    $("notificationList").innerHTML = rows.length
      ? rows.map(n =>
          `<article class="notification-item ${n.is_read ? "" : "unread"}">
            <div class="notification-title">${esc(n.title)}</div>
            <div class="notification-body">${esc(n.message)}</div>
            <div class="notification-meta">${fmtDate(n.created_at)}</div>
            ${n.is_read ? "" : button("Mark read", `read:${n.notification_id}`, "btn-light")}
          </article>`
        ).join("")
      : '<p class="empty-state">No notifications yet.</p>';

    await loadNotificationCount();
    showMessage("notificationsMessage", `${rows.length} notification(s).`, "success");
  } catch (error) {
    showMessage("notificationsMessage", error.message, "error");
  }
}

$("refreshNotificationsButton").addEventListener("click", loadNotifications);

$("markAllReadButton").addEventListener("click", async () => {
  try {
    await api("/api/notifications/read-all", { method: "PATCH" });
    await loadNotifications();
  } catch (error) {
    showMessage("notificationsMessage", error.message, "error");
  }
});

document.addEventListener("click", async event => {
  const btn = event.target.closest('[data-action^="read:"]');
  if (!btn) return;

  const id = btn.dataset.action.split(":")[1];

  try {
    await api(`/api/notifications/${id}/read`, { method: "PATCH" });
    await loadNotifications();
  } catch (error) {
    showMessage("notificationsMessage", error.message, "error");
  }
});
/* SLA monitor */
async function loadSlaTargets() {
  const target = $("slaTargets");
  if (!target) return;

  const defaults = [
    { priority: "Critical", response: "15m", resolution: "4h", tone: "critical" },
    { priority: "High", response: "1h", resolution: "8h", tone: "high" },
    { priority: "Medium", response: "4h", resolution: "24h", tone: "medium" },
    { priority: "Low", response: "8h", resolution: "72h", tone: "low" }
  ];

  let values = defaults;

  try {
    const data = await api("/api/sla/targets");
    const rows = Array.isArray(data) ? data : (data?.targets || []);

    if (rows.length) {
      values = rows.map(row => {
        const priority = row.priority || row.name || "Medium";

        const mins = value => {
          if (value == null) return null;
          const n = Number(value);
          return Number.isFinite(n) ? (n > 1000 ? n / 60 : n) : null;
        };

        const fmt = n => n == null ? "—" : duration(n * 60);

        return {
          priority,
          tone: priority.toLowerCase(),
          response: fmt(mins(
            row.response_minutes ??
            row.response_target_minutes ??
            row.response_time_minutes ??
            row.response_target
          )),
          resolution: fmt(mins(
            row.resolution_minutes ??
            row.resolution_target_minutes ??
            row.resolution_time_minutes ??
            row.resolution_target
          ))
        };
      });
    }
  } catch {
    /* Use default targets if the endpoint is unavailable. */
  }

  target.innerHTML = values.map(item =>
    `<article class="sla-target-card">
      <div class="sla-target-title">
        <span class="badge priority-${esc(item.tone)}">${esc(item.priority)}</span>
        <small>SLA target</small>
      </div>
      <div class="sla-target-times">
        <div>
          <small>First response</small>
          <strong>${esc(item.response)}</strong>
        </div>
        <div>
          <small>Resolution</small>
          <strong>${esc(item.resolution)}</strong>
        </div>
      </div>
    </article>`
  ).join("");
}

async function loadSla() {
  try {
    await loadSlaTargets();

    const rows = await api("/api/sla/tickets");

    $("slaTable").innerHTML = rows.length
      ? rows.map(item => {
          const t = item.ticket || item;
          const responseDue = t.response_due_at || item.response_due_at;
          const resolutionDue = t.resolution_due_at || item.resolution_due_at;
          const responseRemaining = item.response_remaining_seconds;
          const resolutionRemaining = item.resolution_remaining_seconds;

          const responseBreached =
            Boolean(t.response_sla_breached) ||
            (responseRemaining != null && Number(responseRemaining) < 0);

          const resolutionBreached =
            Boolean(t.resolution_sla_breached) ||
            (resolutionRemaining != null && Number(resolutionRemaining) < 0);

          const actions = isLead() || state.account.role === "Admin"
            ? button("Escalate", `escalate:${t.ticket_id}`, "btn-primary")
            : "—";

          return `<tr>
            <td>#${esc(t.ticket_id)}</td>
            <td>${esc(t.title)}</td>
            <td>${priorityBadge(t.priority)}</td>
            <td>${statusBadge(t.status)}</td>
            <td>
              <strong>${fmtDate(responseDue)}</strong><br>
              <small>${deadlineText(responseDue)}</small>
            </td>
            <td>${slaBadge(responseBreached)}</td>
            <td>
              <strong>${fmtDate(resolutionDue)}</strong><br>
              <small>${deadlineText(resolutionDue)}</small>
            </td>
            <td>${slaBadge(resolutionBreached)}</td>
            <td>${actions}</td>
          </tr>`;
        }).join("")
      : '<tr><td colspan="9" class="empty-state">No tickets available for SLA monitoring.</td></tr>';

    await loadEscalations();
    showMessage("slaMessage", "SLA data refreshed.", "success");
  } catch (error) {
    showMessage("slaMessage", error.message, "error");
  }
}

async function loadEscalations() {
  const section = $("escalationHistorySection");
  const allowed = isLead() || state.account?.role === "Admin";

  if (section) section.classList.toggle("hidden", !allowed);
  if (!allowed) return;

  try {
    const rows = await api("/api/sla/escalations");

    $("escalationsTable").innerHTML = rows.length
      ? rows.map(e =>
          `<tr>
            <td>#${esc(e.ticket_id)}</td>
            <td>${esc(e.escalation_type)}</td>
            <td>${esc(e.reason || "—")}</td>
            <td>${fmtDate(e.created_at)}</td>
          </tr>`
        ).join("")
      : '<tr><td colspan="4" class="empty-state">No escalation records.</td></tr>';
  } catch (error) {
    $("escalationsTable").innerHTML =
      `<tr><td colspan="4">${esc(error.message)}</td></tr>`;
  }
}

$("refreshSlaButton").addEventListener("click", loadSla);

document.addEventListener("click", async event => {
  const btn = event.target.closest('[data-action^="escalate:"]');
  if (!btn) return;

  const id = btn.dataset.action.split(":")[1];
  if (!confirm(`Escalate ticket #${id}?`)) return;

  btn.disabled = true;

  try {
    await api(`/api/sla/tickets/${id}/escalate`, { method: "POST" });
    showMessage("slaMessage", `Ticket #${id} escalated.`, "success");
    await loadSla();
  } catch (error) {
    showMessage("slaMessage", error.message, "error");
  } finally {
    btn.disabled = false;
  }
});

/* Staff team chat */
async function loadStaffChat() {
  try {
    const rows = await api("/api/communications/staff-chat");

    $("staffChatMessages").innerHTML = rows.length
      ? rows.map(m =>
          `<article class="chat-message">
            <div class="chat-message-head">
              <strong>${esc(m.sender_name || m.sender_email || "Team member")}</strong>
              <small>${fmtDate(m.created_at)}</small>
            </div>
            <div class="chat-message-body">${esc(m.message)}</div>
          </article>`
        ).join("")
      : '<p class="empty-state">No team messages yet. Start the conversation.</p>';

    $("staffChatMessages").scrollTop = $("staffChatMessages").scrollHeight;
  } catch (error) {
    showMessage("staffChatMessage", error.message, "error");
  }
}

$("refreshStaffChatButton").addEventListener("click", loadStaffChat);

$("staffChatForm").addEventListener("submit", async event => {
  event.preventDefault();

  const text = $("staffChatText").value.trim();
  if (!text) return;

  try {
    await api("/api/communications/staff-chat", {
      method: "POST",
      body: JSON.stringify({ message: text })
    });

    $("staffChatText").value = "";
    showMessage("staffChatMessage", "Message sent.", "success");
    await loadStaffChat();
  } catch (error) {
    showMessage("staffChatMessage", error.message, "error");
  }
});

/* Ticket conversation */
async function loadTicketMessages(id) {
  try {
    const rows = await api(`/api/communications/tickets/${id}/messages`);

    /* Users must never see internal notes in the rendered conversation. */
    const visibleRows = isUser()
      ? rows.filter(m => m.visibility !== "Internal")
      : rows;

    $("ticketMessages").innerHTML = visibleRows.length
      ? visibleRows.map(m =>
          `<article class="chat-message ${m.visibility === "Internal" ? "internal" : ""}">
            <div class="chat-message-head">
              <strong>${esc(m.sender_name || m.sender_email || "Participant")}</strong>
              <small>${
                isUser()
                  ? "Public reply"
                  : `${esc(m.visibility || "Public")} · ${fmtDate(m.created_at)}`
              }</small>
            </div>
            <div class="chat-message-body">${esc(m.message)}</div>
          </article>`
        ).join("")
      : '<p class="empty-state">No public messages yet.</p>';
  } catch (error) {
    $("ticketMessages").innerHTML =
      `<p class="message error">${esc(error.message)}</p>`;
  }
}

$("ticketMessageForm").addEventListener("submit", async event => {
  event.preventDefault();
  if (!state.currentTicket) return;

  const message = $("ticketMessageText").value.trim();
  if (!message) {
    showMessage("ticketMessageStatus", "Enter a message first.", "error");
    return;
  }

  try {
    await api(
      `/api/communications/tickets/${state.currentTicket}/messages`,
      {
        method: "POST",
        body: JSON.stringify({
          message,
          visibility: isUser()
            ? "Public"
            : $("ticketMessageVisibility").value
        })
      }
    );

    $("ticketMessageText").value = "";
    showMessage("ticketMessageStatus", "Message sent.", "success");
    await loadTicketMessages(state.currentTicket);
  } catch (error) {
    showMessage("ticketMessageStatus", error.message, "error");
  }
});

/* Restore the session only through an explicit login. */