# INVASIVE OUTREACH AGENT

AI-powered business development system for Invasive Design.

Discovers UX/UI design job opportunities, qualifies leads, and drafts personalized outreach emails.

## How it works

1. **Morning run** — the first time the app is opened each day (India time), it automatically
   searches the configured job sources for new design jobs, researches each one, scores it
   (0-100), and drafts a personalized outreach email (up to 20 new drafts per run).
2. **Pending Approvals** — all drafted emails wait in the approval queue. Up to 20 emails
   can be approved per day.
3. **Send manually** — each approved email is opened, copied, and sent from Gmail, then
   marked as sent so the company is never contacted twice.

## Features

- Automatic daily job discovery from configurable job board sources
- Manual lead discovery from any job URL
- Company qualification score (0-100)
- Personalized email generation based on job description themes
- Approval queue with a 20-per-day sending limit
- Company-level duplicate prevention and do-not-contact list
- Full audit trail and CSV export

## Setup

1. Clone the repository
2. Run: `streamlit run streamlit_app.py`
3. Manage job sources in the Settings page

## Architecture

- **Database**: SQLite (`leads.db`)
- **UI**: Streamlit (deployed on Streamlit Community Cloud)
- **Research**: Web scraping and job description analysis
- **Email**: Drafted by the app, sent manually from Gmail
