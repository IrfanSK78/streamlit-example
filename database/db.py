"""Database operations for Invasive Outreach Agent."""

import sqlite3
import uuid
from database.schema import create_tables
import csv

DB_PATH = 'leads.db'

def init_db():
    """Initialize database."""
    create_tables(DB_PATH)

def create_lead(data):
    """Create a new lead."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    lead_id = str(uuid.uuid4())[:8]
    cursor.execute('''
        INSERT INTO leads (
            lead_id, company_name, company_domain, company_website,
            job_title, job_url, job_description, date_discovered, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (lead_id, data.get('company_name'), data.get('company_domain'),
          data.get('company_website'), data.get('job_title'), data.get('job_url'),
          data.get('job_description'), data.get('date_discovered'), 'DISCOVERED'))
    conn.commit()
    conn.close()
    return lead_id

def get_lead(lead_id):
    """Get a lead by ID."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM leads WHERE lead_id = ?', (lead_id,))
    lead = cursor.fetchone()
    conn.close()
    return dict(lead) if lead else None

def list_leads(status=None, limit=100):
    """List leads with optional status filter."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if status:
        cursor.execute('SELECT * FROM leads WHERE status = ? ORDER BY created_at DESC LIMIT ?', (status, limit))
    else:
        cursor.execute('SELECT * FROM leads ORDER BY created_at DESC LIMIT ?', (limit,))
    leads = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return leads

def update_lead(lead_id, data):
    """Update a lead."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    set_clause = ', '.join([f'{k} = ?' for k in data.keys()])
    values = list(data.values()) + [lead_id]
    cursor.execute(f'UPDATE leads SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE lead_id = ?', values)
    conn.commit()
    conn.close()

def check_duplicate(job_url=None, company_domain=None):
    """Check for duplicate leads."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    if company_domain:
        cursor.execute('SELECT * FROM leads WHERE company_domain = ? AND status IN (?, ?)', (company_domain, 'CONTACTED', 'PREVIOUSLY_CONTACTED'))
        lead = cursor.fetchone()
        if lead:
            conn.close()
            return True, {'type': 'COMPANY_CONTACTED', 'lead_id': lead['lead_id'], 'status': lead['status']}
    if job_url:
        cursor.execute('SELECT * FROM leads WHERE job_url = ?', (job_url,))
        lead = cursor.fetchone()
        if lead:
            conn.close()
            return True, {'type': 'JOB_ALREADY_RESEARCHED', 'lead_id': lead['lead_id']}
    conn.close()
    return False, None

def check_do_not_contact(company_domain):
    """Check if company is on DNC list."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM do_not_contact WHERE company_domain = ?', (company_domain,))
    dnc = cursor.fetchone()
    conn.close()
    if dnc:
        return True, dnc['reason']
    return False, None

def add_do_not_contact(company_domain, reason):
    """Add company to DNC list."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO do_not_contact (company_domain, reason) VALUES (?, ?)', (company_domain, reason))
    conn.commit()
    conn.close()

def log_audit(lead_id, action, actor='SYSTEM', details=None):
    """Log an audit entry."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO audit_log (lead_id, action, actor, details) VALUES (?, ?, ?, ?)',
                   (lead_id, action, actor, details))
    conn.commit()
    conn.close()

def get_audit_trail(lead_id):
    """Get audit trail for a lead."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM audit_log WHERE lead_id = ? ORDER BY timestamp DESC', (lead_id,))
    entries = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return entries

def export_to_csv(filepath='leads_export.csv'):
    """Export leads to CSV."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM leads ORDER BY created_at DESC')
    leads = cursor.fetchall()
    if leads:
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([description[0] for description in cursor.description])
            writer.writerows(leads)
        conn.close()
        return filepath
    conn.close()
    return None
