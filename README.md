# Seva Mitra  — सेवा मित्र

### Smart & Efficient Virtual Assistant for Multilingual Integrated Transparent Resource Access

> A unified, multilingual, offline-first digital kiosk for citizen–government interactions.  
> Built for SUVIDHA 2026 — organized by C-DAC under MeitY | Smart City 2.0 Initiative.

---

## 🎬 Demo

[![Watch Demo](https://img.shields.io/badge/%E2%96%B6%20Watch%20Demo-YouTube-red?style=for-the-badge&logo=youtube)](https://your-demo-link-here)
[![Live Preview](https://img.shields.io/badge/%F0%9F%8C%90%20Live%20Preview-Click%20Here-blue?style=for-the-badge)](https://your-live-link-here)

---

## What is Seva Mitra II?

Seva Mitra II is a public-facing, touch-based kiosk platform designed for civic utility offices across India. It brings together Electricity, Water, Gas, and Municipal services into a single, accessible interface — built for every Indian citizen, including those the system has traditionally left behind.

Whether it's an elderly resident in a rural municipality, a Manipuri-speaking citizen in the Northeast, or someone in a low-connectivity area — Seva Mitra II works for them.

---

## ✨ Key Features

### 🌐 Multilingual First — 8 Indian Languages

- **Meitei-Mayek (Manipuri script)** — the only civic kiosk platform in India with native Meitei-Mayek rendering
- Hindi · Tamil · Telugu · Kannada · Marathi · Odia
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
- Role-based access: citizen / admin / department
- **Razorpay** payment gateway — PCI-DSS compliant, per-department keys
- Pydantic v2 strict validation on all API inputs
- HTTPS enforced via Nginx TLS in production

### 🏗️ Production-Grade Backend

- Modular **FastAPI** architecture — 6 domain routers, 40+ endpoints
- `src/api/` structure with app factory (`main.py`) and shared dependency injection
- **Full smoke test suite** in `test_backend.py` — spins up server on port 8877, 102 checks across 15 API domains
- SQLite for development, PostgreSQL for production
- Docker + docker-compose for reproducible deployments

---

## 🏛️ Departments Supported

| Department | Services |
|---|---|
| ⚡ Electricity | Bill payment, new connection, meter change, service transfer |
| 💧 Water Supply | Bill payment, leak reporting, new connection |
| 🔥 Gas | Bill payment, new connection |
| 🏙️ Municipal | Waste management, civic complaints |

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
- SQLAlchemy 2.0 + SQLite (dev) / PostgreSQL (prod)
- bcrypt + JWT (OAuth2 via `python-jose`)
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
- PostgreSQL 15+ (production) or SQLite (development/testing)
- Docker (recommended)

### Quick Start with Docker

```bash
git clone https://github.com/premananda-cloud/seva_mitra.git
cd seva_mitra
cp src/api/.env.example .env        # fill in your DB and Razorpay credentials
docker-compose up --build
```

Frontend: `http://localhost:5173`  
API: `http://localhost:8000`  
API Docs: `http://localhost:8000/docs`

### Manual Setup

**Backend** (from project root)

```bash
pip install -r requirements.txt
python test_backend.py     # spins up on port 8877, runs all 102 smoke checks
# or to run the live server:
uvicorn main:app --reload --port 8000
```

**Frontend**

```bash
cd UI_UX
npm install
npm run dev         # starts on http://localhost:5173
```

> **Note:** The frontend Orchestrator probes `http://127.0.0.1:8877/health` on startup. If the backend is unreachable, it silently switches to **mock mode** — all flows still work offline.

---

## 🧪 Running Tests

```bash
# From project root — no pytest needed, pure Python stdlib + httpx
python test_backend.py
```

The test runner:
1. Wipes and re-creates `database/koisk_test.db` (clean slate every run)
2. Spins up FastAPI on port 8877 in a background thread
3. Walks every real scenario with Manipur-based fixture data
4. Prints coloured PASS / FAIL per check
5. Exits `0` (all pass) or `1` (any failure)

For the full pytest integration suite:

```bash
cd tests
pytest
```

---

## 🌍 Language Configuration

Language files live in `UI_UX/src/modules/language/locales/`. To add a new language:

1. Create `UI_UX/src/modules/language/locales/{code}.json`
2. Add the locale entry in `UI_UX/src/modules/language/i18n.js`
3. Add the language option in `LanguageSelect.jsx`

Current locales: `en`, `hi`, `ta`, `te`, `kn`, `mr`, `od`, `ma` (Meitei-Mayek)

---

## 📁 Project Structure

```
seva_mitra/
│
├── main.py                         # API orchestrator — mounts all routers
├── test_backend.py                 # Smoke test suite (102 checks, no pytest)
├── requirements.txt
│
├── src/                            # Backend source
│   ├── api/                        # 6 FastAPI domain routers
│   │   ├── admin/router.py
│   │   ├── electricity/router.py
│   │   ├── water/router.py
│   │   ├── municipal/router.py
│   │   ├── kiosk/router.py         # OTP, session management, dept catalogue
│   │   ├── payments/router.py
│   │   └── shared/                 # deps.py, schemas.py, utils.py
│   ├── department/                 # Department business logic
│   │   ├── electricity/Electricity_Services.py
│   │   ├── water/Water_Services.py
│   │   ├── municipal/municipal_services.py
│   │   └── database/               # SQLAlchemy engine + session
│   ├── payment/
│   │   ├── payment_handler.py      # Razorpay integration
│   │   └── mock_payment_engine.py  # Offline/test payment simulation
│   └── security/
│       ├── auth.py                 # JWT + bcrypt
│       └── auth_routes.py
│
├── UI_UX/                          # Frontend (React + Vite)
│   ├── index.html                  # Entry point (Seva Mitra II splash)
│   ├── vite.config.js
│   └── src/
│       ├── main.jsx                # React root, BrowserRouter, KeyboardProvider
│       ├── App.jsx                 # Route definitions + Protected/PublicOnly wrappers
│       ├── context/
│       │   └── KeyboardContext.jsx # Virtual keyboard state
│       ├── components/
│       │   ├── kiosk/              # Dashboard, LoginPage, RegisterPage, IdleOverlay
│       │   ├── departments/        # ElectricityScreen, WaterScreen, GasScreen, MunicipalScreen
│       │   └── payment/            # PaymentFlow, CardInput, UPIInput, ReceiptScreen
│       └── modules/
│           ├── auth/               # authStore.js (Zustand), LoginPage.jsx, RegisterPage.jsx
│           ├── language/           # i18n.js, LanguageSelect.jsx, locales/
│           ├── localdb/            # localDB.js (IndexedDB v3 — users, sessions, bills, payments, requests)
│           ├── orchestrator/       # orchestrator.js (backend probe + mock fallback)
│           └── payment/            # paymentService.js, offlineQueue.js, gatewayAdapters.js
│
├── database/                       # SQLite files (dev/test)
├── docs/                           # Architecture docs, technical spec
├── tests/                          # pytest integration + unit tests
└── UI_UX/KOISK_PPT_Demo.html       # Presentation demo file
```

---

## 🔒 Security

- Passwords hashed with bcrypt (never stored in plaintext)
- JWT tokens with configurable expiry + auto-logout after 30 min (kiosk mode)
- All payments processed via Razorpay — card data never touches our servers
- SQL injection prevention via SQLAlchemy ORM parameterisation
- CORS restricted to allowed origins (configurable via `CORS_ORIGINS` env var)

---

## 📊 Request Status Flow

```
DRAFT → SUBMITTED → PROCESSING → APPROVED → COMPLETED
                                           ↘ REJECTED
```

Citizens can track their request status in real time from any kiosk.

---

## 🔌 Orchestrator — Offline / Online Bridging

The frontend `orchestrator.js` probes the backend `/health` endpoint on startup:

- **Backend reachable** → all API calls routed to FastAPI over HTTP
- **Backend unreachable** → mock mode — IndexedDB + mock payment engine handle everything locally, syncing when connectivity returns

---

## 🤝 Team Praxis

Built with care for SUVIDHA 2026 — C-DAC National Hackathon under MeitY Smart City 2.0 Initiative.

---

## 📄 License

This project was developed for the SUVIDHA 2026 Hackathon. All rights reserved by Team Praxis.

---

> *Seva Mitra II — One kiosk. Every utility. Every language. Everywhere.*
