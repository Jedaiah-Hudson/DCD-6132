# Installation Guide

Repository: https://github.com/Jedaiah-Hudson/DCD-6132/tree/Maya

This guide explains how to acquire, install, configure, and run the AI Matchmaking Tool for local development or customer evaluation.

## Prerequisites

Install the following software before starting:

- Python 3.12 or newer: https://www.python.org/downloads/
- Node.js 20 or newer and npm: https://nodejs.org/
- Git: https://git-scm.com/downloads
- Tesseract OCR, required for image/PDF capability statement extraction:
  - macOS: `brew install tesseract`
  - Windows: https://github.com/UB-Mannheim/tesseract/wiki
  - Linux: `sudo apt install tesseract-ocr`

Optional external service accounts:

- SAM.gov API key: https://open.gsa.gov/api/get-started/
- OpenAI API key: https://platform.openai.com/
- Google Cloud OAuth web client for Gmail API: https://console.cloud.google.com/
- Microsoft Entra application registration for Microsoft Graph mail access: https://entra.microsoft.com/

## Dependent Libraries

Backend dependencies are listed in `requirements.txt`. Major backend libraries include:

- Django
- Django REST Framework
- django-cors-headers
- python-dotenv
- requests and httpx
- OpenAI Python SDK
- Pillow, pypdfium2, and pytesseract
- msal

Frontend dependencies are listed in `package.json` and `frontend/frontend/package.json`. Major frontend libraries include:

- React
- React DOM
- React Router
- React Select
- Vite
- ESLint

## Download Instructions

Clone the repository:

```bash
git clone https://github.com/Jedaiah-Hudson/DCD-6132.git
cd DCD-6132
git checkout Maya
```

If the repository is private, the customer must be added as a GitHub collaborator or use an access token with permission to clone it.

## Backend Setup

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install backend dependencies:

```bash
pip install -r requirements.txt
```

Create a local `.env` file from the example:

```bash
cp .env.example .env
```

Update `.env` with any credentials needed for the features you plan to use:

```bash
SAM_API_KEY=your_sam_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_CLIENT_ID=your_google_oauth_client_id_here
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret_here
GOOGLE_GMAIL_REDIRECT_URI=http://127.0.0.1:8000/accounts/gmail/callback/
MSAL_CLIENT_ID=your_microsoft_oauth_client_id_here
MSAL_CLIENT_SECRET=your_microsoft_oauth_client_secret_here
MSAL_REDIRECT_URI=http://127.0.0.1:8000/accounts/outlook/callback/
EMAIL_HOST_USER=your_email_address
EMAIL_HOST_PASSWORD=your_email_app_password
DEFAULT_FROM_EMAIL=your_email_address
FRONTEND_BASE_URL=http://localhost:5173
```

The current checked-in Django settings use SQLite at `db.sqlite3`, so no separate database server is required for local setup.

Apply database migrations:

```bash
python manage.py migrate
```

Optional: create an admin user:

```bash
python manage.py createsuperuser
```

Optional: load NAICS data if the project data source is available:

```bash
python manage.py load_naics
```

## Frontend Setup

Install frontend dependencies from the repository root:

```bash
npm install
```

This root command installs the root dependencies and uses the nested frontend project for the Vite application. If needed, install inside the frontend folder too:

```bash
cd frontend/frontend
npm install
cd ../..
```

## Build Instructions

For local development, a production build is not required.

To build the frontend:

```bash
npm run build
```

The generated frontend build output is created by Vite under `frontend/frontend/dist/`.

## Run Instructions

Start the Django backend:

```bash
source .venv/bin/activate
python manage.py runserver
```

The backend runs at `http://127.0.0.1:8000`.

Start the React frontend in a second terminal:

```bash
npm run dev
```

The frontend usually runs at `http://localhost:5173`. If that port is busy, Vite may choose another local port. The Django CORS configuration currently allows ports `5173`, `5174`, and `5175`.

## Optional Data Sync Commands

Sync a small number of SAM.gov opportunities:

```bash
python manage.py ingest_sam_opportunities --limit 5
```

Clean up contracts if using the cleanup command:

```bash
python manage.py cleanup_contracts
```

## Troubleshooting

### Backend will not start

Confirm the virtual environment is active and dependencies are installed:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Then run migrations:

```bash
python manage.py migrate
```

### Frontend cannot reach the backend

Confirm the backend is running at `http://127.0.0.1:8000` and the frontend is running on one of the allowed Vite ports: `5173`, `5174`, or `5175`.

### SAM.gov sync fails

Confirm `SAM_API_KEY` is set in `.env`. Also check whether the SAM.gov API is rate limiting requests.

### AI matchmaking or RFP generation does not use OpenAI

Confirm `OPENAI_API_KEY` is set in `.env`. Matchmaking can still run with rule-based scoring when the key is missing.

### Capability document upload fails with a Tesseract error

Install Tesseract OCR and confirm the `tesseract` executable is available in your system path.

### Gmail or Outlook connection fails

Confirm the OAuth client credentials and redirect URIs match exactly:

- Gmail: `http://127.0.0.1:8000/accounts/gmail/callback/`
- Outlook: `http://127.0.0.1:8000/accounts/outlook/callback/`

### Password reset email does not send

Confirm `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, and `DEFAULT_FROM_EMAIL` are set in `.env`. For Gmail SMTP, use an app password rather than a normal account password.
