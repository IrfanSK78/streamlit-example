"""Invasive Outreach Agent - Streamlit UI."""

import streamlit as st
import os
from datetime import datetime
from database.db import (
    init_db, create_lead, get_lead, list_leads, update_lead,
    check_duplicate, check_do_not_contact, log_audit, get_audit_trail, add_do_not_contact
)
from agents.job_researcher import research_job
from agents.company_researcher import research_company
from agents.lead_qualifier import score_lead, explain_score
from mailer.generator import generate_email, extract_key_themes
from mailer.gmail_service import send_email, test_connection

st.set_page_config(page_title="Invasive Outreach Agent", layout="wide")

def initialize_session():
    """Initialize session state."""
    if 'initialized' not in st.session_state:
        init_db()
        st.session_state.initialized = True

initialize_session()

def page_discover_lead():
    """Page: Discover and research a new lead."""
    st.header("🔍 Discover Lead")
    st.write("Paste a job URL to research and qualify a potential lead.")

    col1, col2 = st.columns([3, 1])

    with col1:
        job_url = st.text_input("Job URL", placeholder="https://jobs.company.com/job/123")

    with col2:
        search_button = st.button("Research", type="primary")

    if search_button and job_url:
        st.info("Researching job posting...")

        job_research = research_job(job_url)

        if job_research['status'] == 'ERROR':
            st.error(f"Error: {job_research['error']}")
            return

        if job_research['warnings']:
            with st.warning("Warnings during research"):
                for warning in job_research['warnings']:
                    st.write(f"⚠ {warning}")

        st.success("Job research complete")

        company_name = job_research.get('company_name')
        company_domain = job_research.get('company_domain')

        st.subheader("Job Information")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Job Title:** {job_research['job_title'] or 'Unknown'}")
            st.write(f"**Company:** {company_name or 'Unknown'}")
        with col2:
            st.write(f"**Domain:** {company_domain or 'Unknown'}")
            st.write(f"**URL:** {job_url}")

        if job_research['job_description']:
            with st.expander("View job description"):
                st.text_area("Job Description", job_research['job_description'], height=200, disabled=True)

        st.subheader("Company Research")

        company_research = research_company(company_name, company_domain, job_research['job_description'])

        if company_research['status'] == 'ERROR':
            st.warning(f"Could not research company: {company_research['error']}")
        else:
            st.write(f"**Website:** {company_research['company_website']}")

            if company_research['complexity_observations']:
                st.write("**Website Observations:**")
                for obs in company_research['complexity_observations']:
                    st.write(f"  • {obs}")

        st.subheader("Lead Qualification")

        score_result = score_lead(
            job_title=job_research['job_title'] or '',
            job_description=job_research['job_description'] or '',
            date_posted=None,
            company_website=company_research.get('company_website'),
            date_discovered=datetime.now().isoformat()
        )

        st.metric("Lead Fit Score", score_result['score'], f"{score_result['recommendation']}")

        with st.expander("Scoring Details"):
            st.write(explain_score(score_result))

        if score_result['score'] >= 70:
            st.success("✅ This lead qualifies for outreach")

            if st.button("Create Lead & Generate Email", type="primary"):
                is_dup, dup_info = check_duplicate(
                    job_url=job_url,
                    company_domain=company_domain
                )

                if is_dup:
                    if dup_info['type'] == 'COMPANY_CONTACTED':
                        st.error(f"Company already contacted: {dup_info['lead_id']} (Status: {dup_info['status']})")
                        st.stop()
                    else:
                        st.warning(f"This job was already researched: {dup_info['lead_id']}")

                is_dnc, dnc_reason = check_do_not_contact(company_domain=company_domain)
                if is_dnc:
                    st.error(f"Company is on do-not-contact list: {dnc_reason}")
                    st.stop()

                lead_data = {
                    'company_name': company_name,
                    'company_domain': company_domain,
                    'company_website': company_research.get('company_website'),
                    'job_title': job_research['job_title'],
                    'job_url': job_url,
                    'job_description': job_research['job_description'],
                    'date_discovered': datetime.now().isoformat()
                }

                lead_id = create_lead(lead_data)
                log_audit(lead_id, 'LEAD_QUALIFIED', actor='USER', details=f'Score: {score_result["score"]}')

                update_lead(lead_id, {
                    'lead_fit_score': score_result['score'],
                    'fit_score_reasons': str(score_result['factors'])
                })

                st.success(f"Lead created: {lead_id}")
                st.session_state.current_lead_id = lead_id
                st.rerun()
        else:
            st.warning(f"Lead score {score_result['score']}/100 - Below threshold of 70")

def page_leads_list():
    """Page: View all leads."""
    st.header("📋 Lead History")

    status_filter = st.selectbox("Filter by status", ["ALL"] + [
        'DISCOVERED', 'RESEARCHING', 'QUALIFIED', 'NOT_QUALIFIED',
        'DRAFT_READY', 'AWAITING_APPROVAL', 'CONTACTED', 'REPLIED'
    ])

    leads = list_leads(status=None if status_filter == "ALL" else status_filter, limit=100)

    if not leads:
        st.info("No leads found")
        return

    for lead in leads:
        with st.expander(f"{lead['company_name']} - {lead['job_title']} ({lead['lead_id']})"):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Status:** {lead['status']}")
                st.write(f"**Score:** {lead['lead_fit_score'] or 'N/A'}/100")
                st.write(f"**Country:** {lead['country'] or 'Unknown'}")

            with col2:
                st.write(f"**URL:** {lead['job_url']}")
                st.write(f"**Discovered:** {lead['date_discovered']}")

            if lead['contact_name']:
                st.write(f"**Contact:** {lead['contact_name']} ({lead['contact_title']})")

            if lead['status'] == 'DRAFT_READY' or lead['status'] == 'AWAITING_APPROVAL':
                if st.button(f"Review Email - {lead['lead_id']}", key=f"review_{lead['lead_id']}"):
                    st.session_state.current_lead_id = lead['lead_id']
                    st.session_state.current_page = "review_email"
                    st.rerun()

            if lead['status'] == 'CONTACTED':
                st.write(f"**Contacted:** {lead['date_contacted']}")

def page_review_email():
    """Page: Review and approve email."""
    st.header("📧 Review & Approve Email")

    lead_id = st.session_state.get('current_lead_id')
    if not lead_id:
        st.error("No lead selected")
        return

    lead = get_lead(lead_id)
    if not lead:
        st.error(f"Lead not found: {lead_id}")
        return

    st.subheader(f"{lead['company_name']} - {lead['contact_name'] or 'Contact'}")

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Lead ID", lead_id)
        st.metric("Fit Score", lead['lead_fit_score'])
    with col2:
        st.write(f"**Company:** {lead['company_name']}")
        st.write(f"**Job:** {lead['job_title']}")

    if lead['status'] != 'DRAFT_READY' and lead['status'] != 'AWAITING_APPROVAL':
        if lead['status'] == 'CONTACTED':
            st.info(f"✅ Email already sent on {lead['date_contacted']}")
            return
        else:
            st.warning(f"Lead status: {lead['status']} - Generate email first")
            return

    st.subheader("Email Details")

    col1, col2 = st.columns([1, 3])
    with col1:
        st.write("**To:** ")
    with col2:
        st.text_input("Recipient Email", value=lead['contact_email'] or '', disabled=True)

    st.text_input("Subject", value=lead['outreach_subject'] or '', disabled=True)

    st.text_area("Email Body", value=lead['outreach_email'] or '', height=400, disabled=True)

    audit_trail = get_audit_trail(lead_id)
    if audit_trail:
        with st.expander("Audit Trail"):
            for entry in audit_trail:
                st.write(f"**{entry['action']}** ({entry['timestamp']})")
                if entry['details']:
                    st.write(f"  {entry['details']}")

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ APPROVE & SEND", type="primary"):
            if not lead['contact_email']:
                st.error("Contact email is required to send")
                st.stop()

            with st.spinner("Sending email..."):
                result = send_email(
                    recipient_email=lead['contact_email'],
                    subject_line=lead['outreach_subject'],
                    email_body=lead['outreach_email'],
                    sender_email="sonia.baig@invasived.com"
                )

                if result['success']:
                    update_lead(lead_id, {
                        'status': 'CONTACTED',
                        'date_contacted': datetime.now().isoformat()
                    })

                    log_audit(
                        lead_id,
                        'EMAIL_SENT',
                        actor='USER',
                        details=f"To: {lead['contact_email']}, Message ID: {result['message_id']}"
                    )

                    st.success("✅ Email sent successfully!")
                    st.session_state.current_lead_id = None
                    st.rerun()
                else:
                    st.error(f"Failed to send: {result['error']}")

    with col2:
        if st.button("✏ Edit Email"):
            st.session_state.editing_email = True
            st.rerun()

    with col3:
        if st.button("❌ Reject Lead"):
            update_lead(lead_id, {'status': 'NOT_QUALIFIED'})
            log_audit(lead_id, 'REJECTED_BY_USER', actor='USER')
            st.success("Lead rejected")
            st.session_state.current_lead_id = None
            st.rerun()

def page_settings():
    """Page: Settings and configuration."""
    st.header("⚙️ Settings")

    st.subheader("Gmail Configuration")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Test Gmail Connection"):
            with st.spinner("Testing connection..."):
                is_connected, message = test_connection()
                if is_connected:
                    st.success(message)
                else:
                    st.error(message)

    with col2:
        st.write("Need to set up Gmail OAuth? See README for instructions.")

    st.subheader("Database")

    if st.button("Export Leads to CSV"):
        from database.db import export_to_csv

        filepath = export_to_csv()
        if filepath:
            with open(filepath, 'r') as f:
                csv_data = f.read()

            st.download_button(
                label="Download CSV",
                data=csv_data,
                file_name="leads_export.csv",
                mime="text/csv"
            )

def main():
    """Main app."""
    st.sidebar.title("Invasive Outreach Agent")

    if 'current_page' not in st.session_state:
        st.session_state.current_page = "discover"

    page = st.sidebar.radio(
        "Navigation",
        ["Discover Lead", "Lead History", "Settings"],
        index=0 if st.session_state.current_page == "discover" else (1 if st.session_state.current_page == "leads" else 2)
    )

    if page == "Discover Lead":
        page_discover_lead()
    elif page == "Lead History":
        page_leads_list()
    elif page == "Settings":
        page_settings()

if __name__ == "__main__":
    main()
