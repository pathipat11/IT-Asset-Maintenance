# IT Asset & Maintenance System (IT AMS)

A web-based **IT Asset & Maintenance Management System** built with **Django**.
This system is designed for internal IT teams to manage assets, maintenance tickets, spare parts stock, and notifications with role-based access control.

---

## ✨ Features

### 🔐 Authentication & Roles

* Login / Logout (Django auth)
* Role-based access using **Groups**:

  * **ADMIN** – Full system access
  * **IT** – Handle tickets, assets, parts, stock
  * **MANAGER** – Monitor tickets and reports
  * **EMPLOYEE** – Create and track own tickets

---

### 🖥 Asset Management

* Create / Update / View / Delete IT assets
* Asset categories, departments, locations
* Asset assignment history (audit logs)
* Asset status tracking (In use, Repair, Retired, etc.)

---

### 🎫 Ticket (Maintenance Request) System

* Employees can create maintenance tickets
* Ticket lifecycle:

  * `NEW → ASSIGNED → IN_PROGRESS → DONE → CLOSED`
* SLA & due date calculation
* Assign tickets to IT staff
* Ticket comments & file attachments
* Audit log for all important actions

---

### 🧰 Parts & Stock Management

* Spare part master data (SKU, vendor, unit cost)
* Stock movement tracking:

  * Stock IN
  * Stock OUT (linked to tickets)
  * Adjustment
* Automatic stock balance validation
* Low-stock threshold alert
* Stock valuation report

---

### 🔔 Notification System

* Real-time-style notifications stored in database
* Notification types:

  * New Ticket
  * Ticket Update
  * Ticket Closed
  * Low Stock Alert
* Notifications are **scoped per user** (no data leakage)
* Mark single / all notifications as read

---

### 🌗 UI / UX

* Responsive UI using **Bootstrap 5**
* Custom modern theme (Light / Dark mode)
* Animated theme toggle (persistent via `localStorage`)
* Clean tables, pagination, badges, and status pills

---

## 🏗 Project Structure

```text
IT-Asset-Maintenance/
├── core/
│   ├── models.py          # Assets, Tickets, Parts, Notifications
│   ├── views.py           # Main views (CRUD, dashboards)
│   ├── notifications_views.py
│   ├── permissions.py     # Group-based permission helpers
│   ├── notify.py          # Notification utilities
│   ├── forms.py
│   ├── templates/
│   │   └── core/
│   └── static/
│       └── css/
├── templates/
│   └── registration/
├── manage.py
└── README.md
```

---

## ⚙️ Installation & Setup

### 1️⃣ Clone the repository

```bash
git clone https://github.com/your-username/IT-Asset-Maintenance.git
cd IT-Asset-Maintenance
```

### 2️⃣ Create virtual environment

```bash
python -m venv venv
source venv/bin/activate   # macOS / Linux
venv\Scripts\activate      # Windows
```

### 3️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 4️⃣ Database migration

```bash
python manage.py migrate
```

### 5️⃣ Create superuser

```bash
python manage.py createsuperuser
```

### 6️⃣ Run development server

```bash
python manage.py runserver
```

Open: `http://127.0.0.1:8000/`

---

## 👥 User Roles & Permissions

| Role     | Description                          |
| -------- | ------------------------------------ |
| ADMIN    | Full access to all modules           |
| IT       | Manage tickets, assets, parts, stock |
| MANAGER  | View dashboards & reports            |
| EMPLOYEE | Create & track own tickets           |

> Permissions are enforced using **GroupRequiredMixin** and query-level filtering.

---

## 🧠 Design Decisions

* **Employees cannot edit tickets once created**
  (prevents tampering and ensures auditability)
* Notifications are **user-specific** (`recipient=user`)
* Stock OUT is strictly validated against current balance
* UI is theme-driven using CSS variables

---

## 🚀 Future Improvements

* Email / WebSocket notifications
* Ticket approval workflow
* Asset depreciation calculation
* API (REST) for mobile integration
* Docker & production deployment configs

---

## 📄 License

This project is for **educational and internal use**.

---

## 🙌 Author

Developed by **Pathipat Mattra**
Django • Backend • System Design
