# INVASIVE OUTREACH AGENT

AI-powered business development system for Invasive Design.

Discovers UX/UI design job opportunities, qualifies leads, and generates personalized outreach emails.

## Phase 1: Core Lead Management

- Lead discovery and research
- Company qualification (0-100 score)
- Personalized email generation
- Approval workflow
- Gmail integration via Google Workspace
- Lead tracking and audit trail

## Setup

1. Clone the repository
2. Create a `.env` file (see `.env.example`)
3. Configure Google Workspace OAuth
4. Run: `streamlit run app.py`

## Architecture

- **Database**: SQLite
- **UI**: Streamlit
- **Email**: Google Workspace (OAuth)
- **Research**: Web research & job analysis

## Status

Phase 1 in development.
