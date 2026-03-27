# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start MinIO (S3-compatible storage) — required for file operations
cd docker && docker-compose up -d && cd ..

# Run Flask development server
python main.py
```

The app runs on `http://localhost:5000` by default. There are no test or lint configurations.

## Environment Configuration

Copy and fill the following variables in a `.env` file at the project root:

```
ENV=DEV                          # DEV or PROD
DEV_MONGO_HOST=localhost:27017
DEV_MONGO_DATABASE=AhcDB
PROD_MONGO_URI=...
PROD_MONGO_DATABASE=AhcDB
SECRET_KEY=...                   # Flask session secret
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_ENDPOINT_URL=http://localhost:9000
AWS_BUCKET_NAME=client-documents
AWS_REGION=us-east-1
ONLYOFFICE_URL=https://docs.ahc-digital.com
ONLYOFFICE_JWT_SECRET=...
```

In DEV mode, MongoDB connects via `mongodb://{DEV_MONGO_HOST}/{DEV_MONGO_DATABASE}`.
In PROD mode, it uses `PROD_MONGO_URI` directly.

## Architecture

This is a **Flask + MongoDB + MinIO** backoffice for a pest control / facility management company (AHC). The codebase is in French.

### Entry Point & Blueprints

`main.py` is the central file (~750 lines). It:
- Initializes Flask and MongoDB connection
- Registers three blueprints: `onlyoffice_bp`, `downloads_bp`, `ingest_bp`
- Contains all core routes (auth, clients, users, documents, traps, floor plans)
- Exposes `db` via `app.config['MONGO_DB']` so blueprints can access it via `current_app.config["MONGO_DB"]`

| Blueprint | File | Purpose |
|-----------|------|---------|
| `onlyoffice_bp` | `routes/onlyoffice_routes.py` | View/edit documents via OnlyOffice (JWT-authenticated) |
| `downloads_bp` | `routes/downloads.py` | File download routes with MinIO presigned URLs |
| `ingest_bp` | `routes/ingest.py` | Bulk PDF ingestion with QR code parsing and OCR date extraction |

### MongoDB Collections

| Collection | Purpose |
|------------|---------|
| `userInternet` | Admin users (bcrypt passwords) |
| `clients` | Client records |
| `clientUsers` | Client portal users |
| `clientDocuments` | Document metadata (MinIO object paths) |
| `interventions` | Service intervention dates |
| `floorPlans` | Floor plan images metadata |
| `traps` | Trap/monitoring points with coordinates |

### File Storage (MinIO)

Documents are stored in MinIO under `client-documents` bucket with paths:
- `documents/<clientId>/interventions/scans/<timestamp>_<filename>` — assigned scans
- `documents/unassigned/<timestamp>_<filename>` — scans without a recognized QR code

Access is always via presigned URLs (10-minute expiry). The MinIO client is initialized at module level in each route file using `.env` variables.

### Authentication

- Admin: Flask session (`session["user_id"]`), `@login_required` decorator in `main.py`
- Client portal: separate session key `session["client_id"]`, guarded by `@client_login_required`
- OnlyOffice: JWT tokens signed with `ONLYOFFICE_JWT_SECRET`

### PDF Ingestion Flow (`routes/ingest.py`)

`POST /api/ingest_docs` processes scanned PDFs:
1. Extracts QR code from first page using OpenCV (`cv2.QRCodeDetector`)
2. Parses `client_ref` from QR URL or raw ID
3. Runs date extraction: first via native PDF text, then OCR (`pytesseract`, lang=`fra`) if no text found
4. Stores in MinIO and inserts metadata into `clientDocuments`
5. Files without a valid QR go to `unassigned/`; `PATCH /api/assign_doc` can reassign them

### Key Models

- `models/client.py` — `Client` class wrapping MongoDB operations
- `models/ClientDocumentManager.py` — document CRUD and MinIO upload
- `models/floorplan_model.py` — floor plan CRUD
- `models/trap_model.py` — trap/monitoring point CRUD with coordinate storage
- `models/utils/word_utils.py` — Word document generation helpers
- `controllers/client_management.py` — business logic for client and client-user creation
- `controllers/user_management.py` — admin user creation logic
- `initialize_project.py` — first-run admin user bootstrap and login/verify helpers

### Frontend

Jinja2 templates with Bootstrap 5. Client edit page uses a tabbed layout with partials in `templates/tabs/`. No JavaScript build pipeline — assets are inline or loaded via CDN.
