# Seva Mitra — सेवा मित्र

### Smart & Efficient Virtual Assistant for Multilingual Integrated Transparent Resource Access

> A unified, multilingual, offline-first digital kiosk for citizen–government interactions.  
> Built for SUVIDHA 2026 — organised by C-DAC under MeitY | Smart City 2.0 Initiative.

---

## 🎬 Demo

[![Watch Demo](https://img.shields.io/badge/%E2%96%B6%20Watch%20Demo-YouTube-red?style=for-the-badge&logo=youtube)](https://your-demo-link-here)
[![Live Preview](https://img.shields.io/badge/%F0%9F%8C%90%20Live%20Preview-Click%20Here-blue?style=for-the-badge)](https://your-live-link-here)

---

## What is Seva Mitra?

Seva Mitra is a public-facing, touch-based kiosk platform designed for civic utility offices across India. It brings together Electricity, Water, Gas, and Municipal services into a single accessible interface — built for every Indian citizen, including those the system has traditionally left behind.

Whether it's an elderly resident in a rural municipality, a Manipuri-speaking citizen in the Northeast, or someone in a low-connectivity area — Seva Mitra works for them.

---

## ✨ Key Features

### 🌐 Multilingual First — 8 Indian Languages

- **Meitei-Mayek (Manipuri script)** — the only civic kiosk platform in India with native Meitei-Mayek rendering
- Hindi · Tamil · Telugu · Kannada · Marathi · Odia · English
- Powered by `react-i18next` with full Unicode support
- Language files in `UI_UX/src/modules/language/locales/`

### ♿ Designed for Senior Citizens

- Large, high-contrast tap targets optimised for kiosk touchscreens
- Minimal text per screen — one action at a time
- Virtual keyboard via `KeyboardContext` for kiosk-mode input
- Simple, linear navigation — no hidden menus or nested flows

### 📡 Offline-First Architecture

- Service requests queued in **IndexedDB** (v3 schema) when internet is unavailable
- Automatic sync on reconnect via the Orchestrator module
- PWA-ready manifest for kiosk deployment
- `localDB.js` manages: users, sessions, bills, payments, requests, syncQueue

### 🔒 Secure by Design

- **JWT + bcrypt** authentication (cost factor 12)
- Role-based access control: `super_admin` / `department_admin`
- Admin endpoints restricted to **localhost only** via middleware
- **Razorpay** payment gateway — PCI-DSS compliant, per-department keys
- Pydantic v2 strict validation on all API inputs
- CORS restricted to configured origins

### 🏗️ Production-Grade Backend

- Modular **FastAPI** architecture — 8 domain routers, 40+ endpoints
- `src/api/` structure with app factory (`main.py`) and shared dependency injection
- SQLite for development, PostgreSQL / MySQL / MSSQL for production (see Database section)
- Docker + docker-compose for reproducible deployments

---

## 🏛️ Departments Supported

| Department | Services |
|---|---|
| ⚡ Electricity | Bill payment, new connection, meter change, service transfer |
| 💧 Water Supply | Bill payment, leak reporting, new connection |
| 🔥 Gas | Bill payment, new connection |
| 🏙️ Municipal | Waste management, civic complaints, property tax |

---

## 🛠️ Tech Stack

**Frontend** (`UI_UX/`)
- React 18 + Vite 7
- Tailwind CSS 3
- react-i18next (i18n)
- Zustand (auth + payment state)
- Axios + IndexedDB (`idb`) offline queue

**Backend** (`src/`)
- FastAPI + Uvicorn
- SQLAlchemy 2.0 ORM
- SQLite (dev) / PostgreSQL / MySQL / MSSQL (prod)
- bcrypt + JWT via `python-jose`
- Pydantic v2
- Razorpay SDK (mock payment engine included)

**Infrastructure**
- Docker + docker-compose
- Nginx (TLS reverse proxy)
- GitHub CI

---

## 🚀 Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- pip + virtualenv
- PostgreSQL 15+ (production) or SQLite (development — no setup needed)
- Docker (optional but recommended)

### Quick Start with Docker

```bash
git clone https://github.com/premananda-cloud/seva_mitra.git
cd seva_mitra
cp src/api/.env.example .env        # fill in your secrets
docker-compose up --build
```

Frontend: `http://localhost:5173`  
API: `http://localhost:8000`  
API Docs: `http://localhost:8000/docs`

### Manual Setup

**Backend** (from project root)

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install 'pydantic[email]'     # required for email validation

# Copy and configure environment
cp src/api/.env.example .env      # edit as needed

# Start the server
uvicorn main:app --reload --port 8000
```

The database (`koisk.db`) is created automatically on first startup. A default super admin is seeded:

| Field    | Value        |
|----------|-------------|
| Username | `admin`      |
| Password | `Admin@1234` (or set `ADMIN_DEFAULT_PASSWORD` in `.env`) |
| Role     | `super_admin` |

> **Change the default password immediately in any non-development environment.**

**Frontend**

```bash
cd UI_UX
npm install
npm run dev         # starts on http://localhost:5173
```

> The frontend Orchestrator probes `http://127.0.0.1:8000/health` on startup. If the backend is unreachable it silently switches to **mock mode** — all flows still work offline using IndexedDB and the mock payment engine.

---

## 🗄️ Database

The database is created automatically when the app starts for the first time (`Base.metadata.create_all` is called inside `init_db()` which fires on FastAPI startup). You do not need to run any migrations manually for a fresh install.

### Switching Databases

Set the `DATABASE_URL` environment variable and install the relevant driver. No other code changes are needed — SQLAlchemy handles the rest.

| Database | DATABASE_URL format | Driver |
|---|---|---|
| **SQLite** (default/dev) | `sqlite:///./koisk.db` | none |
| **PostgreSQL** (recommended prod) | `postgresql://user:pass@host:5432/dbname` | `pip install psycopg2-binary` |
| **MySQL / MariaDB** | `mysql+pymysql://user:pass@host:3306/dbname` | `pip install PyMySQL` |
| **MS SQL Server** | `mssql+pyodbc://user:pass@host/dbname?driver=ODBC+Driver+17+for+SQL+Server` | `pip install pyodbc` |

> For PostgreSQL/MySQL/MSSQL the database itself must be created first (e.g. `createdb koisk_db`). The app only creates tables, not the database container.

### Optional DB Tuning (env vars)

| Variable | Default | Description |
|---|---|---|
| `DB_POOL_SIZE` | `10` | SQLAlchemy connection pool size (ignored for SQLite) |
| `DB_MAX_OVERFLOW` | `20` | Extra connections beyond pool |
| `SQL_ECHO` | `false` | Set `true` to log all SQL queries |

---

## 🔐 Admin System

Admin accounts are stored in the `admins` table in the database. There are two roles:

| Role | Access |
|---|---|
| `super_admin` | Full access — manage all departments, all admins, kiosk config |
| `department_admin` | Scoped to their assigned department only |

All `/admin/*` endpoints are **localhost-only** — blocked at the middleware level for any external IP.

### Admin API

```bash
# Login — get JWT token
curl -X POST http://localhost:8000/admin/login \
  -d "username=admin&password=Admin@1234"

# List all admins (super_admin only)
curl http://localhost:8000/admin/users \
  -H "Authorization: Bearer <token>"

# Register a new admin (super_admin only)
curl -X POST http://localhost:8000/admin/register \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "elec_admin",
    "email": "elec@koisk.local",
    "full_name": "Electricity Admin",
    "password": "SecurePass1",
    "role": "department_admin",
    "department": "electricity"
  }'
```

### Viewing Super Admins Directly

```bash
# Via sqlite3
sqlite3 koisk.db \
  "SELECT id, username, email, is_active FROM admins WHERE role='super_admin';"

# Via Python (run from project root with venv active)
python3 - <<'EOF'
from src.department.database.database import SessionLocal
from src.department.database.models import Admin
db = SessionLocal()
for a in db.query(Admin).filter(Admin.role == "super_admin").all():
    print(f"{a.id}  {a.username}  {a.email}  active={a.is_active}")
db.close()
EOF
```

> Passwords are stored as bcrypt hashes — they cannot be read from the database. To reset a password use `PATCH /admin/users/{id}/password`.

---

## 🧪 Running Tests

```bash
# From project root — no pytest needed, uses Python stdlib + httpx
python test_backend.py
```

The test runner:
1. Wipes and re-creates a clean test database
2. Spins up FastAPI on port 8877 in a background thread
3. Walks every real scenario with fixture data
4. Prints coloured PASS / FAIL per check
5. Exits `0` (all pass) or `1` (any failure)

For the pytest integration suite:

```bash
cd tests && pytest
```

---

## 🌍 Adding a New Language

Language files live in `UI_UX/src/modules/language/locales/`.

1. Create `UI_UX/src/modules/language/locales/{code}.json` (copy `en.json` as a template)
2. Add the locale entry in `UI_UX/src/modules/language/i18n.js`
3. Add the language option in `LanguageSelect.jsx`

Current locales: `en`, `hi`, `ta`, `te`, `kn`, `mr`, `od`, `ma` (Meitei-Mayek)

---

## ⚙️ Environment Variables

Copy `src/api/.env.example` to `.env` in the project root and fill in your values.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./koisk.db` | Database connection string |
| `SECRET_KEY` | `koisk-dev-secret-...` | JWT signing key — **change in production** |
| `ADMIN_DEFAULT_PASSWORD` | `Admin@1234` | Password for the seeded default super admin |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed frontend origins |
| `MOCK_PAYMENT` | `true` | Use mock payment engine instead of real gateway |
| `SQL_ECHO` | `false` | Log all SQL queries to console |

---

## 📁 Project Structure

```
seva_mitra/
│
├── main.py                          # FastAPI app factory — mounts all routers
├── requirements.txt
│
├── src/
│   ├── api/
│   │   ├── admin/
│   │   │   ├── router.py            # Auth, admin CRUD, merchant + kiosk config
│   │   │   └── ui.py                # Admin UI
│   │   ├── electricity/router.py
│   │   ├── water/router.py
│   │   ├── gas/router.py
│   │   ├── municipal/router.py
│   │   ├── kiosk/router.py          # OTP flow, session management, dept catalogue
│   │   ├── payments/router.py
│   │   ├── complaints/router.py
│   │   └── shared/
│   │       ├── deps.py              # JWT helpers, get_current_admin, hash_password
│   │       ├── schemas.py           # Shared Pydantic response models
│   │       └── utils.py             # save_request, to_response helpers
│   │
│   ├── database/
│   │   └── models.py                # Single source of truth for all ORM models
│   │
│   ├── department/
│   │   ├── database/
│   │   │   ├── database.py          # SQLAlchemy engine + session + init_db
│   │   │   └── models.py            # Re-exports from src/database/models.py
│   │   ├── electricity/Electricity_Services.py
│   │   ├── water/Water_Services.py
│   │   ├── gas/Gas_Services.py
│   │   └── municipal/municipal_services.py
│   │
│   ├── payment/
│   │   ├── payment_handler.py       # Razorpay integration
│   │   └── mock_payment_engine.py   # Offline/test payment simulation
│   │
│   └── security/
│       ├── auth.py                  # JWT + bcrypt core
│       └── auth_routes.py
│
├── UI_UX/
│   ├── index.html
│   └── src/
│       ├── App.jsx                  # Routes + auth guards
│       ├── context/
│       │   └── KeyboardContext.jsx  # Virtual keyboard state
│       ├── components/
│       │   ├── kiosk/               # Dashboard, Login, Register, IdleOverlay
│       │   ├── departments/         # Per-department screens
│       │   └── payment/             # PaymentFlow, CardInput, UPIInput, Receipt
│       └── modules/
│           ├── auth/                # Zustand auth store
│           ├── language/            # i18n config + locale JSON files
│           ├── localdb/             # IndexedDB v3 wrapper
│           ├── orchestrator/        # Backend probe + mock fallback
│           └── payment/             # Gateway adapters, offline queue
│
└── koisk.db                         # SQLite database (created on first startup)
```

---

## 🔒 Security Notes

- Passwords are hashed with bcrypt — never stored in plaintext
- JWT tokens expire after 8 hours (configurable), kiosk sessions after 30 minutes
- All payments processed via Razorpay — card data never touches this server
- SQL injection prevented via SQLAlchemy ORM parameterisation
- `/admin/*` routes are blocked for all non-localhost IPs at middleware level
- For production: use PostgreSQL (not SQLite), set a strong `SECRET_KEY`, and restrict filesystem permissions on the server

---

## 📊 Service Request Status Flow

```
SUBMITTED → ACKNOWLEDGED → IN_PROGRESS → DELIVERED
                                        ↘ FAILED
                                        ↘ CANCELLED
```

Citizens can track their request status in real time from any kiosk terminal.

---

## 🤝 Team Praxis

Built with care for SUVIDHA 2026 — C-DAC National Hackathon under MeitY Smart City 2.0 Initiative.

---

## 📄 License

Developed for the SUVIDHA 2026 Hackathon. All rights reserved by Team Praxis.

---

> *Seva Mitra — One kiosk. Every utility. Every language. Everywhere.*
