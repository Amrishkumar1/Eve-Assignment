# EVE Healthcare — Diagnostic Booking API

FastAPI + PostgreSQL + SQLAlchemy + JWT implementation for the SDE Intern backend assignment.

## Features
- Signup/login with bcrypt password hashing and JWT access tokens.
- Diagnostic centres and centre-specific test prices.
- Authenticated booking, booking ownership checks, and cancellation of pending bookings.
- Mock payment endpoint (no real gateway).
- Shared-secret payment webhook with unique event IDs for idempotent processing.
- Input validation, pagination, centre search, Swagger docs and pytest tests.

## Requirements
Python 3.11+, PostgreSQL 14+, Git.

## Local setup
1. Create a virtual environment and install dependencies:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
   If PowerShell activation is blocked, run `.\.venv\Scripts\python.exe -m pip install -r requirements.txt`.
2. Create a PostgreSQL database:
   ```sql
   CREATE DATABASE eve_healthcare;
   ```
3. Copy `.env.example` to `.env`, then set a strong `JWT_SECRET_KEY` and your PostgreSQL credentials.
   ```powershell
   Copy-Item .env.example .env
   ```
4. Start the API:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Open `http://127.0.0.1:8000/docs` for interactive Swagger UI. Health check: `/health`.

For local development `AUTO_CREATE_TABLES=true` creates tables at startup. For production, use Alembic migrations and set this to false.

## Endpoints

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/signup` | No | Register |
| POST | `/auth/login` | No | Get JWT |
| GET | `/centres/` | No | List centres (`search`, `limit`, `offset`) |
| GET | `/centres/{centre_id}` | No | Centre and tests |
| POST | `/centres/` | No* | Create centre and tests |
| POST | `/bookings/` | JWT | Create booking |
| GET | `/bookings/` | JWT | List own bookings |
| GET | `/bookings/{booking_id}` | JWT | Get own booking |
| POST | `/bookings/{booking_id}/cancel` | JWT | Cancel pending booking |
| POST | `/payments/` | JWT | Simulate payment |
| POST | `/payments/webhook/` | Shared secret | Provider event |
| GET | `/health` | No | Health check |

`*` Centre creation is intentionally a demo/admin endpoint; add role-based authorization before production.

## Example workflow

Register:
```bash
curl -X POST http://127.0.0.1:8000/auth/signup -H "Content-Type: application/json" -d '{"name":"Amrish Kumar","email":"amrish@example.com","password":"StrongPass123"}'
```

Login:
```bash
curl -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" -d '{"email":"amrish@example.com","password":"StrongPass123"}'
```
Copy the returned access token. In Swagger, click **Authorize** and provide `Bearer YOUR_TOKEN`.

Create centre:
```bash
curl -X POST http://127.0.0.1:8000/centres/ -H "Content-Type: application/json" -d '{"name":"City Diagnostic Centre","location":"Kurukshetra, Haryana","tests":[{"test_name":"CBC","description":"Complete blood count","price":"450.00"}]}'
```

Create booking (use IDs returned by your API and a future timezone-aware datetime):
```bash
curl -X POST http://127.0.0.1:8000/bookings/ -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d '{"centre_id":1,"test_id":1,"appointment_at":"2027-01-15T10:30:00+05:30"}'
```

Mock payment:
```bash
curl -X POST http://127.0.0.1:8000/payments/ -H "Authorization: Bearer YOUR_TOKEN" -H "Content-Type: application/json" -d '{"booking_id":1,"simulate_status":"SUCCESS"}'
```

Webhook (header value must match `JWT_SECRET_KEY` in `.env`):
```bash
curl -X POST http://127.0.0.1:8000/payments/webhook/ -H "X-Webhook-Secret: replace-this-with-a-long-random-secret" -H "Content-Type: application/json" -d '{"event_id":"provider-event-0001","booking_id":1,"status":"SUCCESS","amount":"450.00"}'
```
Send the same event again to verify it returns the existing payment. Reusing an event ID with different data returns `409 Conflict`.

## Database design
- `users`: unique email, password hash.
- `diagnostic_centres`: centre name and location.
- `diagnostic_tests`: reusable test catalogue.
- `centre_tests`: many-to-many centre/test association; price is specific to that centre; centre/test pair is unique.
- `bookings`: user, centre-test, appointment, amount snapshot and status.
- `payments`: booking, status, amount and unique provider event ID.

Money uses `NUMERIC(10,2)` and Python `Decimal`. The booking stores the price at booking time, so catalogue price changes do not change an existing booking.

## State flow
`PENDING → CONFIRMED` on successful payment; `PENDING → FAILED` on failed payment; `PENDING → CANCELLED` when the user cancels. Cancelled and final-state bookings cannot be paid again.

## Tests
```bash
pytest -q
```
Tests use an isolated in-memory SQLite database; PostgreSQL is used by the application when configured in `.env`.

## Assumptions and future improvements
- The webhook secret is a simulation, not a real provider signature. Production should verify provider HMAC signatures, timestamps and replay protection.
- Add an admin role for centre management, Alembic migrations, appointment slot capacity, concurrent booking safeguards, structured logs, rate limiting, CI, and PostgreSQL integration tests.
- This demo does not store real patient medical records.

## GitHub submission
Create a repository such as `eve-healthcare-diagnostic-booking`. Never commit `.env`, credentials, tokens or real patient data.

```bash
git init
git add .
git commit -m "Build EVE Healthcare diagnostic booking API"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/eve-healthcare-diagnostic-booking.git
git push -u origin main
```
