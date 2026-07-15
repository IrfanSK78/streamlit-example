"""Database operations for Invasive Outreach Agent."""

import sqlite3
import os
from datetime import datetime
from database.schema import LEAD_SCHEMA, AUDIT_LOG_SCHEMA, DO_NOT_CONTACT_SCHEMA, LEAD_STATUSES

DB_PATH = 'lead_tracker.db'

def get_connection():
    """Get database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(LEAD_SCHEMA)
    cursor.execute(AUDIT_LOG_SCHEMA)
    cursor.execute(DO_NOT_CONTACT_SCHEMA)

    conn.commit()
    conn.close()

def generate_lead_id():
    """Generate unique lead ID: INV-0001, INV-0002, etc."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as count FROM leads")
    count = cursor.fetchone()['count']
    conn.close()

    return f"INV-{count + 1:04d}"

def check_duplicate(job_url=None, company_name=None, company_domain=None):
    """
    Check if lead already exists by job URL, company, or domain.
    Returns: (is_duplicate, duplicate_info)
    """
    conn = get_connection()
    cursor = conn.cursor()

    if job_url:
        cursor.execute("SELECT lead_id, status FROM leads WHERE job_url = ?", (job_url,))
        result = cursor.fetchone()
        if result:
            conn.close()
            return True, {
                'type': 'URL_MATCH',
                'lead_id': result['lead_id'],
                'status': result['status']
            }

    if company_domain:
        cursor.execute(
            "SELECT lead_id, status FROM leads WHERE company_domain = ? ORDER BY date_discovered DESC LIMIT 1",
            (company_domain,)
        )
        result = cursor.fetchone()
        if result:
            if result['status'] == 'CONTACTED' or result['status'] == 'PREVIOUSLY_CONTACTED':
                conn.close()
                return True, {
                    'type': 'COMPANY_CONTACTED',
                    'lead_id': result['lead_id'],
                    'status': result['status']
                }

    conn.close()
    return False, None

def check_do_not_contact(company_domain=None, contact_email=None):
    """Check if company or contact is marked DO NOT CONTACT."""
    conn = get_connection()
    cursor = conn.cursor()

    if company_domain:
        cursor.execute(
            "SELECT dnc_id, reason FROM do_not_contact WHERE contact_type = 'COMPANY' AND contact_value = ?",
            (company_domain,)
        )
        result = cursor.fetchone()
        if result:
            conn.close()
            return True, result['reason']

    if contact_email:
        cursor.execute(
            "SELECT dnc_id, reason FROM do_not_contact WHERE contact_type = 'EMAIL' AND contact_value = ?",
            (contact_email,)
        )
        result = cursor.fetchone()
        if result:
            conn.close()
            return True, result['reason']

    conn.close()
    return False, None

def create_lead(lead_data):
    """Create a new lead."""
    conn = get_connection()
    cursor = conn.cursor()

    lead_id = generate_lead_id()
    now = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO leads (
            lead_id, company_name, company_domain, company_website,
            country, job_title, job_location, job_url, job_source,
            date_posted, date_discovered, job_description, remote_status,
            seniority_level, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        lead_id,
        lead_data.get('company_name'),
        lead_data.get('company_domain'),
        lead_data.get('company_website'),
        lead_data.get('country'),
        lead_data.get('job_title'),
        lead_data.get('job_location'),
        lead_data.get('job_url'),
        lead_data.get('job_source', 'MANUAL'),
        lead_data.get('date_posted'),
        lead_data.get('date_discovered', now),
        lead_data.get('job_description'),
        lead_data.get('remote_status'),
        lead_data.get('seniority_level'),
        'DISCOVERED',
        now,
        now
    ))

    conn.commit()
    conn.close()

    log_audit(lead_id, 'LEAD_CREATED', actor='SYSTEM', details='Lead created from job URL')

    return lead_id

def update_lead(lead_id, updates):
    """Update lead fields."""
    conn = get_connection()
    cursor = conn.cursor()

    updates['updated_at'] = datetime.now().isoformat()

    set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [lead_id]

    cursor.execute(f"UPDATE leads SET {set_clause} WHERE lead_id = ?", values)
    conn.commit()
    conn.close()

def get_lead(lead_id):
    """Retrieve a lead by ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM leads WHERE lead_id = ?", (lead_id,))
    result = cursor.fetchone()
    conn.close()

    return dict(result) if result else None

def list_leads(status=None, country=None, limit=50):
    """List leads with optional filters."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM leads WHERE 1=1"
    params = []

    if status:
        query += " AND status = ?"
        params.append(status)

    if country:
        query += " AND country = ?"
        params.append(country)

    query += " ORDER BY date_discovered DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]

def log_audit(lead_id, action, actor='SYSTEM', details=None):
    """Log an action in the audit trail."""
    import uuid

    conn = get_connection()
    cursor = conn.cursor()

    log_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO audit_log (log_id, lead_id, action, actor, timestamp, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (log_id, lead_id, action, actor, timestamp, details))

    conn.commit()
    conn.close()

def get_audit_trail(lead_id):
    """Retrieve audit trail for a lead."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM audit_log WHERE lead_id = ? ORDER BY timestamp DESC",
        (lead_id,)
    )
    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]

def add_do_not_contact(contact_type, contact_value, reason=None):
    """Add a company or email to do-not-contact list."""
    import uuid

    conn = get_connection()
    cursor = conn.cursor()

    dnc_id = str(uuid.uuid4())
    created_at = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO do_not_contact (dnc_id, contact_type, contact_value, reason, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (dnc_id, contact_type, contact_value, reason, created_at))

    conn.commit()
    conn.close()

def remove_do_not_contact(contact_type, contact_value):
    """Remove from do-not-contact list."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM do_not_contact WHERE contact_type = ? AND contact_value = ?",
        (contact_type, contact_value)
    )

    conn.commit()
    conn.close()

def export_to_csv(filepath='leads_export.csv'):
    """Export all leads to CSV."""
    import csv

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM leads ORDER BY date_discovered DESC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return None

    fieldnames = [description[0] for description in cursor.description]

    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))

    return filepath
