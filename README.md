# AI Matchmaking Tool

Version: 1.0  
Repository: https://github.com/Jedaiah-Hudson/DCD-6132/tree/Maya

## Customer Delivery Documents

- [Installation Guide](INSTALLATION.md)
- [Detailed Design Document PDF](docs/detailed-design-document.pdf)
- [Editable Detailed Design Document](docs/detailed-design-document.md)

## Project Overview

The AI Matchmaking Tool is a customer delivery and contract discovery application for organizations that need to find, review, and manage government contracting opportunities. The system combines a Django REST backend with a React/Vite frontend. Users can create accounts, build company capability profiles, browse procurement opportunities, receive AI-assisted matches, track pursuit progress, connect mailboxes, and generate draft RFP responses.

The source code is available in this repository for browsing. Backend code is organized under `accounts/`, `contracts/`, `core/`, and `config/`. Frontend code is organized under `frontend/frontend/src/`.

## Release Notes

### Version 1.0

This is the first customer delivery release.

#### New Features

- User account creation, login, token authentication, logout, and password reset flow.
- Capability profile management for company details, capabilities, NAICS codes, certifications, past performance, contact information, services, target industries, opportunity types, tags, and geography.
- Capability document extraction from PDF, PNG, JPG, and JPEG files using OCR and parsing logic.
- Contract opportunity browsing with search, status filtering, NAICS filtering, agency filtering, partner filtering, and opportunity detail pages.
- SAM.gov opportunity ingestion through a backend sync endpoint and management command.
- AI matchmaking that scores opportunities against a user's capability profile using rule-based signals and optional OpenAI embeddings.
- Match caching so users can refresh or reuse generated recommendations.
- Contract progress tracking for pursuit outcome, workflow stage, relationship label, and private notes.
- Dismissal flow that removes unwanted opportunities from a user's recommendations.
- Contract notifications for approaching deadlines, status changes, progress changes, and workflow changes.
- Notification page with unread counts and bulk read/unread/delete actions.
- Gmail and Outlook OAuth mailbox connection support for reading opportunity-related emails.
- Mailbox sync support that records matched messages and links mailbox opportunities to contracts.
- AI RFP response draft generation using the selected contract and the user's capability profile.
- React frontend screens for login, account creation, password reset, dashboard, AI matchmaking, my contracts, contract details, RFP generator, profile, and notifications.
- Django admin support for backend data inspection and maintenance.

#### Bugs Fixed During Development

- Added unique email constraints to prevent duplicate linked email records.
- Added validation for invalid linked email input.
- Added OAuth state validation for Gmail and Outlook callbacks to reject missing, invalid, or expired state values.
- Added error handling for expired mailbox provider tokens.
- Added supported-file validation for capability document uploads.
- Added graceful handling when Tesseract OCR is not installed.
- Added SAM.gov API error handling for HTTP and rate limit failures.
- Added dismissal cleanup so dismissed contracts no longer keep user progress or notifications.
- Added notification cleanup for inactive or expired deadline conditions.
- Added CORS settings for the local frontend development ports used by the React app.

#### Known Issues and Defects

- This release is configured for local/development deployment. `DEBUG=True` and the development `SECRET_KEY` should be changed before any production deployment.
- SQLite is currently configured in `config/settings.py`; the older README mentioned MySQL environment variables, but the current checked-in settings use `db.sqlite3`.
- Gmail and Outlook mailbox OAuth require valid Google Cloud and Microsoft Entra application credentials. Without those credentials, mailbox connection features cannot be completed.
- OpenAI-powered embeddings and RFP draft generation require `OPENAI_API_KEY`. If it is missing, matchmaking falls back to rule-based scoring and RFP generation may use mock/error behavior depending on the service path.
- SAM.gov sync requires `SAM_API_KEY`. Without it, procurement ingestion cannot fetch live opportunities.
- OCR for image-based capability statements requires Tesseract to be installed on the host machine.
- OAuth tokens are signed to prevent silent tampering, but they are not encrypted at rest. Production use should replace this with encrypted fields or a managed secret store.
- Password reset currently returns a development reset-link placeholder in the API response to help local testing. This should be removed before production release.
- The app does not include a production deployment pipeline, hosted domain configuration, or HTTPS setup in this release.
- Automated test coverage exists for important backend flows, but full end-to-end browser testing is not included in this release.

## Quick Start

Use the full [Installation Guide](INSTALLATION.md) for setup. The short version is:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

In a second terminal:

```bash
npm install
npm run dev
```

Then open the frontend at `http://localhost:5173`.

## Support and Handoff Notes

The customer should review the known issues before using the application with live mailbox, OpenAI, or SAM.gov credentials. Future maintainers should prioritize production security hardening, encrypted token storage, deployment configuration, and end-to-end testing before public launch.
