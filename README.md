# SchemePro — Kenya Scheme of Work Generator

AI-free, database-driven scheme of work generator for Kenya's **8-4-4** and **CBC** curriculum systems.
All content comes from the curriculum database. No external API dependencies.

---

## Architecture — MVC + Service Layer

```
schemepro/
├── run.py                          # Entry point: python run.py
├── requirements.txt
├── pytest.ini
├── .env.example
│
├── app/
│   ├── __init__.py                 # Flask factory + full curriculum seed
│   │
│   ├── models/                     # M — Data Layer (SQLAlchemy)
│   │   ├── role.py                 # Role + permissions map
│   │   ├── user.py                 # User, UserHistory (feature tracking)
│   │   ├── level.py                # Level, SubLevel
│   │   ├── subject.py              # Subject (curriculum_system: 844|CBC)
│   │   ├── curriculum.py           # Topic → SubTopic → Content
│   │   ├── wallet.py               # Wallet, WalletTransaction, Payment,
│   │   │                           #   TransactionHistory (unified ledger)
│   │   └── pricing.py              # DocumentPricing, GeneratedDocument
│   │
│   ├── services/                   # Business Logic (no external APIs)
│   │   └── scheme_engine.py        # SchemeGenerator — pure Python algorithm
│   │                               #   reads topics/subtopics from DB,
│   │                               #   distributes lessons across weeks,
│   │                               #   handles breaks, double lessons,
│   │                               #   generates default 844 & CBC text
│   │
│   ├── controllers/                # C — Route Handlers
│   │   ├── auth_controller.py      # /auth/*
│   │   ├── main_controller.py      # Page routes
│   │   ├── api_controller.py       # /api/v1/*
│   │   ├── scheme_controller.py    # /scheme/generate + /scheme/download
│   │   ├── wallet_controller.py    # /wallet/*
│   │   └── admin_controller.py     # /admin-panel/*
│   │
│   └── templates/                  # V — Jinja2 Views
│       ├── base.html
│       ├── index.html              # Landing page (subjects from DB via API)
│       ├── about.html
│       ├── spa.html                # 4-step scheme generator SPA
│       ├── admin.html              # Admin dashboard SPA
│       └── partials/
│
└── tests/
    └── test_app.py                 # 107 TDD tests
```

---

## Database Schema

| Table | Purpose |
|---|---|
| `roles` | 4 roles: superuser, admin, support, client |
| `users` | Accounts — name, email, bcrypt password, role, region, last_login, last_logout, last_active |
| `user_history` | Per-user feature visit tracking (feature + visit_count) |
| `levels` | Education levels (Upper Primary, Junior School CBC, Senior School) |
| `sublevels` | Std 4–8, Grade 7–9, Form 1–4 |
| `subjects` | 20 subjects across levels and systems |
| `topics` | Topics (844) / Strands (CBC) — seeded with full KICD content |
| `subtopics` | Sub-topics / Sub-strands |
| `content` | Per-subtopic: aids, num_lessons, KIQ, outcomes, activities, references |
| `wallets` | One wallet per user — running balance |
| `wallet_transactions` | Every top-up (M-Pesa, Pesapal, Card, Bank) |
| `payments` | Every document download debit |
| `transaction_history` | Unified in/out ledger for admin revenue reporting |
| `generated_documents` | Log of every generation + download |
| `document_pricing` | Admin-configurable price per format (pdf/docx/zip) |

---

## Scheme Engine Algorithm

`SchemeGenerator.generate()` — no AI, pure Python:

1. Fetch all SubTopics (with Content) between start_subtopic and end_subtopic from DB
2. For each teaching week from start_week to start_week+weeks-1:
   - If whole-week break → insert BREAK row, skip
   - If partial break (from_lesson N) → available_lessons = N-1
   - Consume subtopics until available_lessons exhausted (each subtopic uses content.num_lessons)
   - Insert partial BREAK row after content if applicable
3. When subtopics exhausted → insert Revision rows for remaining weeks
4. Build row dicts with all correct keys for 844 or CBC format
5. Fill missing content fields with rule-based default text

Default text uses templates like:
- **844 objectives**: "By end of lesson learner should be able to: (a) Define {subtopic}. (b) Explain..."
- **CBC outcomes**: "By end of lesson, the learner should be able to: (a) Describe {substrand}..."
- **CBC inquiry**: falls back to "What do we know about {substrand}?"

---

## Seeded Curriculum (20 subjects, ~200 subtopics)

| Subject | Level | System | Topics |
|---|---|---|---|
| Physics | Senior | 844 | Measurements, Linear Motion, Newton's Laws, Work/Energy, Waves |
| Chemistry | Senior | 844 | Intro, Acids/Bases/Salts, Carbon |
| Biology | Senior | 844 | Cell Biology, Nutrition, Transport |
| Mathematics | Senior | 844 | Quadratics, Approximations, Trigonometry |
| History & Gov't | Senior | 844 | Evolution, Agricultural Dev't, Trade Contacts |
| Geography | Senior | 844 | Solar System, Volcanicity |
| English | Senior | 844 | (add via admin) |
| Integrated Science | Junior | CBC | Scientific Investigation, Matter, Living Things |
| Mathematics | Junior | CBC | Numbers, Algebra |
| Social Studies | Junior | CBC | Citizenship, Economic Activities |
| Mathematics | Primary | 844 | Numbers, Algebra |
| English | Primary | 844 | Reading, Grammar |
| Social Studies | Primary | 844 | Environment, East Africa |
| Science & Technology | Primary | 844 | Living Things, Matter |
| + 6 more subjects | | | Add content via admin |

---

## Setup

```bash
git clone <repo> && cd schemepro
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Set SECRET_KEY; ANTHROPIC_API_KEY not needed
python run.py               # http://localhost:5000
```

## Database migrations (Flask-Migrate)

Migrations are handled with Flask-Migrate (the `flask db ...` CLI).

### 1) Initialize migration environment (run once)
```bash
# from project root
flask --app manage.py db init
```

### 2) Create a migration from model changes
```bash
flask --app manage.py db migrate -m "Describe the change"
```

### 3) Apply migrations
```bash
flask --app manage.py db upgrade
```

### 4) (Optional) Check migration status
```bash
flask --app manage.py db current
```


DB, seed data, and default superuser created automatically on first run.

**Default admin:** `admin` / `Admin@1234` — change immediately in production.

---

## Running Tests

```bash
python -m pytest tests/ -v
# 107 tests: models, controllers, engine, auth, wallet, admin, downloads
```

---

## API Reference

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Create account |
| POST | `/auth/login` | — | Sign in |
| POST | `/auth/logout` | ✓ | Sign out |
| GET | `/auth/me` | ✓ | Current user |
| GET | `/api/v1/levels` | — | All levels + sublevels |
| GET | `/api/v1/subjects?level_id=X` | — | Subjects |
| GET | `/api/v1/topics?subject_id=X` | — | Topics |
| GET | `/api/v1/subtopics?topic_id=X` | — | Subtopics |
| GET | `/api/v1/pricing` | — | Download prices |
| PUT | `/api/v1/pricing` | Admin | Update prices |
| POST | `/api/v1/topics` | Admin | Add topic |
| POST | `/api/v1/subtopics` | Admin | Add subtopic + content |
| **POST** | **`/scheme/generate`** | ✓ | **Generate scheme from DB** |
| **POST** | **`/scheme/download`** | ✓ | **Download PDF/DOCX/ZIP** |
| GET | `/wallet/balance` | ✓ | Wallet balance |
| POST | `/wallet/topup` | ✓ | Top up (mpesa/pesapal/card/bank) |
| GET | `/wallet/history` | ✓ | Transaction history |
| GET | `/admin-panel/overview` | Admin | Stats overview |
| GET | `/admin-panel/users` | Admin | All users |
| POST | `/admin-panel/users/<id>/disable` | Admin | Disable user |
| GET | `/admin-panel/revenue/daily` | Admin | Revenue by day |
| GET | `/admin-panel/transactions` | Admin | All transactions |
| GET | `/admin-panel/doc-stats` | Admin | Generation stats |

---

## Production

- Replace SQLite: `DATABASE_URL=postgresql://user:pass@host/db`
- Run: `gunicorn -w 4 "app:create_app()"`
- Set `FLASK_ENV=production` and a strong `SECRET_KEY`
- Wire real M-Pesa Daraja / Pesapal callbacks in `wallet_controller.py`
- Enable HTTPS (nginx + certbot)
