# Detailed Design Document

Project: AI Matchmaking Tool  
Version: 1.0  
Repository: https://github.com/Jedaiah-Hudson/DCD-6132/tree/Maya

## Purpose

The AI Matchmaking Tool helps customers discover government contracting opportunities that align with their capabilities. The application supports account management, capability profile creation, opportunity ingestion, opportunity browsing, AI-assisted matching, pursuit tracking, notifications, mailbox syncing, and RFP response draft generation.

## Stakeholders and Users

Primary users are customer organizations that want to identify and manage contract opportunities. Secondary users include instructors, project evaluators, administrators, and future maintainers who need to understand the system architecture and delivery status.

## System Architecture

The project uses a two-part architecture:

- Backend: Django, Django REST Framework, SQLite, and service modules for procurement ingestion, mailbox integration, OCR, matchmaking, and RFP generation.
- Frontend: React, React Router, React Select, and Vite.

The backend exposes JSON APIs for authentication, profile data, opportunities, contract progress, notifications, mailbox connections, and AI generation. The frontend consumes those APIs and provides the user-facing workflow.

## Backend Components

### `accounts`

The `accounts` app owns user identity and mailbox connection data. It includes:

- Custom email-based `User` model.
- Additional linked email records.
- Gmail and Outlook mailbox connection models.
- Capability profiles connected to users.
- OAuth callback handling for Gmail and Outlook.
- Password reset request and confirmation endpoints.

### `contracts`

The `contracts` app owns contract opportunity records and pursuit workflow data. It includes:

- Contract records from procurement portals, Gmail, or Outlook.
- NAICS code records.
- User contract progress records.
- Dismissed contracts.
- Contract notifications.
- Email ingestion records.
- RFP draft generation endpoint.
- SAM.gov ingestion command and sync API.

### `core`

The `core` app owns dashboard-oriented views and profile/matchmaking APIs. It includes:

- Capability profile save and retrieval APIs.
- Capability document extraction API.
- Opportunity list API.
- Matched contract APIs.
- Matchmaking cache model.
- Rule-based and optional embedding-based scoring logic.

### `config`

The `config` package owns Django settings, URL routing, WSGI, and ASGI configuration.

## Frontend Components

The React frontend is located in `frontend/frontend/src/`.

Major pages include:

- `LoginPage.jsx`
- `CreateAccountPage.jsx`
- `ResetPasswordPage.jsx`
- `DashboardPage.jsx`
- `AiMatchmakingPage.jsx`
- `MyContractsPage.jsx`
- `ContractDetailPage.jsx`
- `RfpGeneratorPage.jsx`
- `ProfilePage.jsx`
- `NotificationsPage.jsx`

Shared UI and contract display logic is handled by components such as `ContractsDisplayPage.jsx` and `NaicsMultiSelect.jsx`.

## Data Design

Important data models include:

- `User`: email-based authentication model.
- `CapabilityProfile`: company capabilities, NAICS codes, certifications, past performance, contact data, matchmaking tags, and OCR text.
- `AdditionalEmail`: extra customer email addresses.
- `MailboxConnection`: Gmail/Outlook OAuth connection metadata and signed tokens.
- `Contract`: opportunity data including source, portal, title, summary, agency, NAICS, deadline, link, status, and partner.
- `UserContractProgress`: per-user pursuit status, workflow status, relationship label, and notes.
- `DismissedContract`: opportunities hidden by a user.
- `ContractNotification`: deadline, status, progress, and workflow notifications.
- `EmailIngestionMessage`: mailbox messages processed during sync.
- `MailboxContract`: relationships between mailbox messages and contract records.
- `UserMatchmakingCache`: cached AI/rule-based match results for a user.

## Major Workflows

### Account and Profile Workflow

1. User creates an account or logs in.
2. User creates or edits a capability profile.
3. User may upload a capability statement document for OCR extraction.
4. User selects NAICS codes and matchmaking preferences.
5. Profile data becomes available for contract matching and RFP generation.

### Opportunity Discovery Workflow

1. Procurement opportunities are added through SAM.gov ingestion or existing data.
2. Authenticated users can browse opportunities.
3. Users can filter and search by NAICS, agency, status, partner, and keywords.
4. Users can open contract detail pages for richer review.

### Matchmaking Workflow

1. The backend reads the user's capability profile.
2. The backend compares profile fields, NAICS codes, keywords, certifications, timeline data, and optional embeddings against visible contracts.
3. The system returns match scores, percentages, strongest alignment, weak alignment, and match reasons.
4. Results are cached for reuse until the user refreshes matches.

### Contract Management Workflow

1. User marks progress for a contract.
2. User updates workflow stage and relationship label.
3. User adds notes.
4. User can dismiss opportunities that are not relevant.
5. Notifications are created for progress changes, workflow changes, status changes, and approaching deadlines.

### Mailbox Workflow

1. User connects Gmail or Outlook using OAuth.
2. Backend stores mailbox connection metadata.
3. User triggers mailbox sync.
4. Emails are filtered for opportunity-like content.
5. Matching messages are recorded and can be associated with contract records.

### RFP Draft Workflow

1. User selects a contract.
2. Backend loads the user's latest capability profile.
3. Backend builds a prompt from contract data and capability profile data.
4. OpenAI service returns a draft response.
5. Frontend displays the generated draft for user review.

## External Integrations

- SAM.gov API for procurement opportunity ingestion.
- OpenAI API for embeddings and RFP response generation.
- Google Gmail API for mailbox read access.
- Microsoft Graph API for Outlook mailbox read access.
- SMTP email service for password reset email.
- Tesseract OCR for extracting text from image-based documents.

## Security Design

The system uses Django authentication, token authentication for API access, OAuth state validation for mailbox callbacks, and signed mailbox tokens to detect tampering. Production hardening is still required before public deployment. Recommended production improvements include:

- Move `SECRET_KEY` to environment variables.
- Set `DEBUG=False`.
- Configure `ALLOWED_HOSTS`.
- Use HTTPS.
- Encrypt OAuth tokens at rest.
- Remove development reset-link placeholders.
- Rotate all credentials used during testing.

## Known Design Constraints

- The current delivery is intended for local/development use.
- SQLite is used by default.
- External integrations require customer-managed API credentials.
- OCR quality depends on document quality and local Tesseract installation.
- RFP draft output must be reviewed by a human before use.
- End-to-end browser automation is not included in this release.

## Testing Strategy

Backend unit tests exist for account, profile, matchmaking, SAM.gov, OAuth, and contract-related behavior. Frontend linting is configured through ESLint. Future releases should add full end-to-end workflow tests for authentication, profile creation, matching, contract tracking, mailbox sync, and RFP generation.

## Deployment Notes

For this release, the recommended customer evaluation mode is local execution:

- Django backend at `http://127.0.0.1:8000`.
- React frontend at `http://localhost:5173`.

Before production deployment, the customer or maintainer should add a production settings file, configure a production database, configure static asset hosting, configure HTTPS, and set all secrets through a secure environment or secret manager.

## Maintenance Priorities

1. Production security hardening.
2. Encrypted OAuth token storage.
3. Deployment documentation for the customer's target hosting environment.
4. End-to-end test coverage.
5. Better admin tools for reviewing ingested mailbox messages.
6. Improved error reporting for external service failures.
