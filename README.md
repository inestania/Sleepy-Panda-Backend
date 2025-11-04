## Sleepy Panda Backend

Sleepy Panda now runs as a collection of lightweight FastAPI microservices that expose authentication, user management, prediction, sleep tracking, and feedback capabilities. Each service owns a focused slice of the domain while sharing core infrastructure (database models, configuration, and security helpers) through the `backend/common` package.

### 🧱 Service layout

```
backend/
	common/               # shared config, database engine, SQLAlchemy models, JWT helpers
	services/
		auth/               # login/register, OTP, token issuance, password reset
		users/              # profile updates, metrics, work metadata
		predictions/        # ML inference, weekly/monthly summaries, persistence
		sleep/              # sleep record ingestion + weekly/monthly analytics
		feedback/           # simple user feedback collector
	main.py               # application gateway that mounts all routers
```

All routers are mounted under their own prefixes (`/auth`, `/users`, `/predictions`, `/sleep`, `/feedback`) so they can be deployed independently if desired. The shared SQLAlchemy models allow you to keep a single database for now; moving to service-specific databases only requires copying the needed models into a dedicated service later on.

### 🔧 Prerequisites

- Python 3.12+
- PostgreSQL (or the database configured via `DATABASE_URL`)
- Poetry or pip for dependency management

Create a `.env` file in the repository root with at least:

```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/sleepy_panda
EMAIL_SENDER=your@email.com
EMAIL_PASSWORD=app-specific-password
SECRET_KEY=super-secret-key
```

### ▶️ Run locally

Install dependencies and start the API gateway (which mounts every microservice router):

```bash
pip install -r requirements.txt  # or poetry install
uvicorn backend.main:app --reload
```

Each service can also be mounted in isolation by creating a small launcher that imports the desired router and exposes it via FastAPI.

### � Run with Docker

1. Copy the sample environment file and adjust secrets/credentials:

   ```bash
   cp .env.example .env
   ```

2. Start the stack (FastAPI + PostgreSQL + pgAdmin):

   ```bash
   docker compose up --build
   ```

   The API will be available at <http://localhost:8000> and pgAdmin at <http://localhost:8080>. Use the credentials defined in `.env` to sign in to pgAdmin, then register a server pointing to host `db`, port `5432`.

3. To stop the containers, press `Ctrl+C` or run:

   ```bash
   docker compose down
   ```

### �📡 High-level API map

- **Auth**: `/auth/register`, `/auth/login`, `/auth/token`, `/auth/logout`, `/auth/request-otp`, `/auth/verify-otp`, `/auth/reset-password`
- **Users**: `/users/basic`, `/users/{email}`, `/users/{email}/work`, `/users/{email}` (PATCH), `/users/{email}/metrics`, `/users/me`, `/users/me/profile`
- **Predictions**: `/predictions/run`, `/predictions/save`, `/predictions/weekly`, `/predictions/weekly/save`, `/predictions/monthly`, `/predictions/monthly/save`
- **Sleep**: `/sleep/records`, `/sleep/records/{email}`, `/sleep/weekly/{email}`, `/sleep/monthly/{email}`
- **Feedback**: `/feedback`

Refer to the individual router modules under `backend/services/*/router.py` for full request/response models and domain logic.

### ✅ Database migrations

`Base.metadata.create_all` still runs on startup. For production deployments, migrate to Alembic or another migration tool as you solidify the schema boundaries for each microservice.

### 🧪 Testing & next steps

- Add service-level tests under `tests/<service_name>` to validate critical flows (auth/token lifecycle, prediction edges, sleep analytics math).
- Containerise each service (`Dockerfile` per service) or switch to separate FastAPI apps for full microservice isolation when you are ready to scale.
