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

### 🏢 Department Analytics
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
- Record ticket and assignment events.
- Track archive and restore activities.
- Provide administrators with filtering and pagination for audit records.

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
pip install Django==4.2.30 djangorestframework==3.16.1 django-cors-headers==4.9.0 requests==2.32.5
```

**Note:** These are the versions observed in the development environment. A pinned backend dependency manifest is not yet included in the repository.

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
| Departments | GET | `/api/departments/` |
| Employees | GET | `/api/employees/` |
| Employee Details | GET, PATCH | `/api/employees/{id}/` |
| Assignments | GET | `/api/assignments/` |
| Create Assignment | POST | `/api/tickets/{id}/assignments/` |
| Update Assignment | PATCH | `/api/assignments/{id}/` |
| Department Analytics | GET | `/api/analytics/departments/` |
| AI Ticket Analysis | POST | `/api/ai/analyze/{id}/` |
| Audit Logs | GET | `/api/audit-logs/` |

API responses use standardized data/meta and error envelopes. Pagination is one-based, with a default page size of 20 and a maximum of 100.

---

## Environment Variables

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Required Django secret key |
| `VITE_API_BASE_URL` | Optional frontend API base URL |
| `SMARTDESK_TEST_AI_PASSWORD` | Used by the manual AI integration script |

The `.env.example` file contains placeholders. Django does not automatically load `.env` files in the current implementation, so environment variables must be supplied by the runtime environment.

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
| Audit Logging | Implemented |
| External AI Integration | Not Implemented |
| Runbook Automation | Not Implemented |
| Notifications API | Not Implemented |

### Known Limitations

- AI analysis currently relies on keyword-based rules.
- External AI provider and telemetry integrations are not configured.
- Runbook dispatch is unavailable.
- Reliable resolution-time, SLA, and MTTR metrics are not supported by the available stored data.
- Settings preferences are currently local browser preferences or demo controls.
- Complete archive and restore workflows are not exposed in the frontend.
- Backend dependency versions still need a dedicated dependency manifest.

---

## Future Improvements

Potential areas for further development include:

- Integration with an external AI service or trained ML model.
- Automated runbook execution.
- Notification management and persistence.
- SLA monitoring and resolution-time analytics.
- Improved administrative settings and role management.
- Reproducible backend dependency management.
- Automated testing and deployment workflows.

---

## Author

**Omkar Bobde**

GitHub: [@OMKARbobde](https://github.com/OMKARbobde)

Project Repository: [SmartDesk](https://github.com/OMKARbobde/SmartDesk)

---

*SmartDesk – Simplifying IT support operations through centralized ticket management, workforce coordination, and intelligent ticket analysis.*