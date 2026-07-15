"""Database schema for Invasive Outreach Agent."""

import sqlite3

def create_tables(db_path='leads.db'):
    """Create database tables."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            lead_id TEXT PRIMARY KEY,
            company_name TEXT,
            company_domain TEXT,
            company_website TEXT,
            job_title TEXT,
            job_url TEXT,
            job_description TEXT,
            contact_name TEXT,
            contact_title TEXT,
            contact_email TEXT,
            country TEXT,
            lead_fit_score INTEGER,
            fit_score_reasons TEXT,
            outreach_subject TEXT,
            outreach_email TEXT,
            status TEXT DEFAULT 'DISCOVERED',
            date_discovered TEXT,
            date_contacted TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_id TEXT,
            action TEXT,
            actor TEXT,
            details TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(lead_id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS do_not_contact (
            dnc_id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_domain TEXT UNIQUE,
            reason TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    conn.close()
