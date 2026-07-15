"""Lead database schema for Invasive Outreach Agent."""

LEAD_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    lead_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    company_domain TEXT,
    company_website TEXT,
    country TEXT,
    job_title TEXT NOT NULL,
    job_location TEXT,
    job_url TEXT UNIQUE,
    job_source TEXT,
    date_posted TEXT,
    date_discovered TEXT NOT NULL,
    job_description TEXT,
    remote_status TEXT,
    seniority_level TEXT,

    lead_fit_score INTEGER,
    fit_score_reasons TEXT,

    contact_name TEXT,
    contact_title TEXT,
    contact_email TEXT,
    contact_email_verified BOOLEAN DEFAULT 0,
    contact_source TEXT,

    outreach_subject TEXT,
    outreach_email TEXT,

    status TEXT DEFAULT 'DISCOVERED',
    date_approved TEXT,
    date_contacted TEXT,
    last_follow_up_date TEXT,
    next_follow_up_date TEXT,

    notes TEXT,

    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

LEAD_STATUSES = [
    'DISCOVERED',
    'RESEARCHING',
    'QUALIFIED',
    'NOT_QUALIFIED',
    'ALREADY_RESEARCHED',
    'PREVIOUSLY_CONTACTED',
    'CONTACT_NOT_FOUND',
    'DRAFT_READY',
    'AWAITING_APPROVAL',
    'APPROVED',
    'CONTACTED',
    'FOLLOW_UP_DUE',
    'REPLIED',
    'MEETING_BOOKED',
    'CLOSED',
    'DO_NOT_CONTACT'
]

AUDIT_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    log_id TEXT PRIMARY KEY,
    lead_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT,
    timestamp TEXT NOT NULL,
    details TEXT,
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id)
)
"""

DO_NOT_CONTACT_SCHEMA = """
CREATE TABLE IF NOT EXISTS do_not_contact (
    dnc_id TEXT PRIMARY KEY,
    contact_type TEXT NOT NULL,
    contact_value TEXT NOT NULL,
    reason TEXT,
    created_at TEXT NOT NULL
)
"""
