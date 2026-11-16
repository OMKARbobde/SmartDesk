# SmartDesk – IT Service Management System

**SmartDesk** is a web-based IT Service Management (ITSM) application designed to streamline support ticket management, employee assignments, department workload monitoring, ticket analysis, and audit tracking.

Built with **Django REST Framework** and **React**, SmartDesk provides a centralized interface for managing IT support operations with role-based access control and department-level analytics.

---

## Key Features

### 🎫 Ticket Management
- Create, view, search, filter, and sort support tickets.
- Update ticket details and perform bulk status or priority updates.
- Archive and restore tickets.
- Prevent stale updates using `updated_at` validation.
- Server-side ticket visibility based on user roles.

### 👥 Workforce & Assignment Management
- Search and view employee profiles.
- Manage ticket assignments and reassign employees.
- Allow employees to accept or complete their own assignments.
- Enforce role-based assignment permissions.

### 🏢 Department Management & Analytics
- Allow ADMIN users to create, edit, activate and deactivate departments.
- Keep deactivated departments and their ticket/employee references intact.
- Monitor ticket distribution across departments.
- Analyze ticket status, priority, and workload.
- Filter analytics by department and date.

### 🤖 AI-Based Ticket Analysis
- Analyze ticket titles and descriptions using keyword-based heuristics.
- Predict ticket category, priority, and sentiment.
- Generate heuristic confidence scores.
- Suggest responses to support agents.
- Store analysis results for each ticket.

*Note: The current implementation uses local rule-based heuristics, not a trained machine-learning model or external AI service.*

### 📋 Audit Logs
- Record ticket, assignment, department, archive and restore events.
- Track archive and restore activities.
- Provide administrators with filtering and pagination for audit records.

### 🔔 In-App Notifications
- Persist notifications for relevant ticket and assignment events.
- Show recipient-scoped notifications and unread counts.
- Mark individual or all notifications as read.

### 🔐 Authentication & Authorization
- Session-based authentication.
- Login using username or email.
- CSRF protection for unsafe API requests.
- Three application roles:
  - **ADMIN** – Administrative access.
  - **AGENT** – Support ticket and workforce management.
  - **EMPLOYEE** – Access to permitted tickets and assignments.

---

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React 18, React Router DOM |
| Build Tool | Vite 5 |
| Styling | Tailwind CSS |
| Icons | Lucide React |
| Backend | Python, Django 4.2 |
| API | Django REST Framework |
| Database | SQLite |
| Authentication | Django Session Authentication |
| Integration | REST API, CSRF Protection |

---

## Project Structure

```text
SmartDesk/
│
├── backend/
│   ├── accounts/          # User authentication and profiles
│   ├── ai_engine/         # Heuristic ticket analysis
│   ├── assignment/        # Assignment management
│   ├── auditlog/          # Audit event tracking
│   ├── departments/       # Department APIs and analytics
│   ├── notifications/     # Persistent in-app notifications
│   ├── smartdesk/         # Django settings and URLs
│   ├── tickets/           # Ticket management
│   └── manage.py
│
├── SmartDesk_React_Starter_Extracted/
│   └── SmartDesk_React_Starter/
│       ├── src/
│       │   ├── api/       # API client and adapters
│       │   ├── components/# Shared UI components
│       │   ├── context/   # Authentication context
│       │   └── pages/     # Application screens
│       ├── package.json
│       └── vite.config.js
│
├── .env.example
└── .gitignore
```

The `SmartDesk_React_Starter_Extracted/SmartDesk_React_Starter/` directory contains the active SmartDesk frontend.

---

## Installation & Setup

### Prerequisites

- Python 3.9+
- Node.js and npm
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/OMKARbobde/SmartDesk.git
cd SmartDesk
```

### 2. Backend Setup

Navigate to the backend:

```bash
cd backend
```

Create and activate a virtual environment:

```bash
python -m venv llm_env_25
```

Windows PowerShell:

```powershell
.\llm_env_25\Scripts\Activate.ps1
```

Install the backend packages:

```bash
python -m pip install -r requirements.txt
```

**Note:** The repository includes the full pinned backend requirements manifest as UTF-8 text. Its 151 dependency entries are preserved. Pip parsed the converted manifest without installing packages; a clean deployment environment has not yet been tested against it.

### 3. Configure Environment Variables

Set the Django secret key in PowerShell:

```powershell
$env:DJANGO_SECRET_KEY="your-generated-secret-key"
```

The frontend API URL can optionally be configured using:

```powershell
$env:VITE_API_BASE_URL="http://localhost:8000/api"
```

Do not commit real secret keys or passwords.

### 4. Run Database Migrations

From the `backend` directory:

```bash
python manage.py migrate
```

Create a Django administrator:

```bash
python manage.py createsuperuser
```

The SmartDesk application has its own `ADMIN`, `AGENT`, and `EMPLOYEE` roles. Configure the administrator's SmartDesk role as `ADMIN` to access administrator-only API features.

Department and employee profile records must also be provisioned.

### 5. Start the Backend Server

```bash
python manage.py runserver
```

Backend:

```text
http://localhost:8000/
```

### 6. Frontend Setup

Open a new terminal and navigate to the active frontend:

```bash
cd SmartDesk_React_Starter_Extracted/SmartDesk_React_Starter
```

Install dependencies:

```bash
npm ci
```

Start the development server:

```bash
npm run dev
```

Frontend:

```text
http://localhost:5173/
```

---

## API Endpoints

The backend exposes REST APIs for authentication, ticket management, workforce, analytics, and audit tracking.

| Module | Method | Endpoint |
|---|---|---|
| CSRF | GET | `/api/auth/csrf/` |
| Login | POST | `/api/auth/login/` |
| Logout | POST | `/api/auth/logout/` |
| Current User | GET | `/api/auth/me/` |
| User Profile | GET, PATCH | `/api/users/me/` |
| Tickets | GET, POST | `/api/tickets/` |
| Ticket Details | GET, PATCH | `/api/tickets/{pk}/` |
| Bulk Updates | POST | `/api/tickets/bulk/` |
| Archived Tickets | GET | `/api/tickets/archived/` |
| Archive Ticket | POST | `/api/tickets/{pk}/archive/` |
| Restore Ticket | POST | `/api/tickets/{pk}/restore/` |
| Departments | GET, POST | `/api/departments/` |
| Department Details | PATCH | `/api/departments/{id}/` |
| Employees | GET | `/api/employees/` |
| Employee Details | GET, PATCH | `/api/employees/{id}/` |
| Assignments | GET | `/api/assignments/` |
| Create Assignment | POST | `/api/tickets/{id}/assignments/` |
| Update Assignment | PATCH | `/api/assignments/{id}/` |
| Department Analytics | GET | `/api/analytics/departments/` |
| AI Ticket Analysis | POST | `/api/ai/analyze/{id}/` |
| Audit Logs | GET | `/api/audit-logs/` |
| Notifications | GET | `/api/notifications/` |
| Unread Notification Count | GET | `/api/notifications/unread-count/` |
| Mark Notification Read | POST | `/api/notifications/{id}/read/` |
| Mark All Notifications Read | POST | `/api/notifications/mark-all-read/` |

API responses use standardized data/meta and error envelopes. Pagination is one-based, with a default page size of 20 and a maximum of 100.

---

## Environment Variables

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Required Django secret key |
| `VITE_API_BASE_URL` | Optional frontend API base URL |
| `SMARTDESK_TEST_AI_PASSWORD` | Used by the manual AI integration script |

The `.env.example` file contains placeholders. Django does not automatically load `.env` files in the current implementation, so environment variables must be supplied by the runtime environment.

## Verification

Backend checks and tests:

```bash
cd backend
python manage.py check
python manage.py test
```

Frontend tests use Node's built-in test runner (there is no `npm test` script):

```bash
cd SmartDesk_React_Starter_Extracted/SmartDesk_React_Starter
node --test src/api/client.test.js src/api/resources.test.js src/pages/settings/auditLogFormatters.test.js
npm run build
```

---

## Current Implementation Status

| Feature | Status |
|---|---|
| Session Authentication & CSRF | Implemented |
| Ticket Management | Implemented |
| Employee & Department APIs | Implemented |
| Assignment Management | Implemented |
| AI Ticket Analysis | Heuristic-based |
| Department Analytics | Implemented |
| Audit Logging, including department events | Implemented |
| External AI Integration | Not Implemented |
| Runbook Automation | Not Implemented |
| Notifications API and header panel | Implemented |
| Department Management | Implemented; ADMIN only |

### Known Limitations

- AI analysis currently relies on keyword-based rules.
- External AI provider and telemetry integrations are not configured.
- Runbook dispatch is unavailable.
- Reliable resolution-time, SLA, and MTTR metrics are not supported by the available stored data.
- Settings preferences are currently local browser preferences or demo controls.
- The full pinned backend requirements file is preserved, but it is a broad environment snapshot rather than a reviewed minimal deployment set. Clean-environment installation has not been verified.
- Production-specific Django settings are not configured: `DEBUG` is enabled, `ALLOWED_HOSTS` is empty, HTTPS/HSTS and secure cookie flags are unset, and `STATIC_ROOT` is not configured.
- SQLite is suitable for development and small single-writer deployments; higher write concurrency should use a production database such as PostgreSQL after a separately tested migration plan.

---

## Future Improvements

Potential areas for further development include:

- Integration with an external AI service or trained ML model.
- Automated runbook execution.
- SLA monitoring and resolution-time analytics.
- Improved administrative settings and role management.
- Reproducible backend dependency management.
- Automated testing and deployment workflows.

### Release Configuration

Before deploying, provide production values for `DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, the CORS and CSRF trusted origins, and `VITE_API_BASE_URL`. Configure HTTPS redirects, HSTS, secure session/CSRF cookies, and a static-file serving strategy for the hosting platform. Django does not load `.env` automatically; inject variables through the deployment environment.

### SQLite Backup and Recovery

Create backups outside the repository with SQLite's online backup API and unique filenames. Stop application writes before a planned restore. Verify backups with `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, and critical table counts. For recovery, restore the backup to a separate candidate file first, verify it, and only then perform an approved maintenance-window cutover while retaining the previous database file. Do not delete migration history or roll back by removing migration records.

---

## Author

**Omkar Bobde**

GitHub: [@OMKARbobde](https://github.com/OMKARbobde)

Project Repository: [SmartDesk](https://github.com/OMKARbobde/SmartDesk)

---

*SmartDesk – Simplifying IT support operations through centralized ticket management, workforce coordination, and intelligent ticket analysis.*
