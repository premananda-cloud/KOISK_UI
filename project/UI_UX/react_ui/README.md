# KOISK_UI — React Frontend

Touch-based civic utility kiosk | SUVIDHA 2026 Hackathon

## Quick Start

```bash
npm install
npm run dev
# Open http://localhost:5173
```

## Architecture

```
src/
├── modules/
│   ├── auth/           # Module 1 — Register, Login, Session
│   ├── language/       # Module 2 — i18n, LanguageSelect UI
│   ├── localdb/        # Module 3 — IndexedDB local storage
│   └── orchestrator/   # Module 4 — Backend connection seam (stub)
├── components/
│   └── kiosk/          # Shared UI: Dashboard, etc.
├── config/
│   └── languages.js    # Single source of truth for supported languages
└── index.css           # Tailwind + component classes
```

## Demo Account

Pre-loaded citizen profile for demos:
- **Phone:** 9876543210  
- **PIN:** 1234  
- Includes realistic service history (electricity bill, water complaint, gas connection)

## Adding a New Language (3 steps)

1. Create `src/modules/language/locales/[code].json` (copy `en.json` as template)
2. Import it in `src/modules/language/i18n.js` and add to `resources`
3. Add entry to `src/config/languages.js` `SUPPORTED_LANGUAGES` array

Zero component changes needed.

## Connecting the Real Backend

All backend calls will eventually route through the Orchestrator:

```js
// src/modules/orchestrator/orchestrator.js
orchestrator.connect('http://localhost:8000')
```

Once connected, the orchestrator flushes the local sync queue to FastAPI.

## Supported Languages

| Code | Language | Script      |
|------|----------|-------------|
| en   | English  | Latin       |
| hi   | Hindi    | Devanagari  |
| od   | Odia     | Odia        |
| te   | Telugu   | Telugu      |
| ta   | Tamil    | Tamil       |
| kn   | Kannada  | Kannada     |
| mr   | Marathi  | Devanagari  |

## Tech Stack

- React 18 + Vite 5
- Tailwind CSS 3
- Zustand (auth state)
- i18next (multilingual)
- idb / IndexedDB (local persistence)
- React Router 6
