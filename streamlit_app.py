"""Invasive Outreach Agent - Streamlit UI."""

import streamlit as st
from datetime import datetime, timezone, timedelta
from database.db import (
    init_db, create_lead, get_lead, list_leads, update_lead,
    check_duplicate, check_do_not_contact, check_company_name_duplicate,
    log_audit, get_audit_trail,
    add_do_not_contact, add_job_source, list_job_sources, remove_job_source,
    get_state, set_state
)
from agents.job_researcher import research_job
from agents.company_researcher import research_company
from agents.lead_qualifier import score_lead, explain_score
from agents.source_scraper import scrape_source, looks_like_design_job, fetch_structured_jobs
from mailer.generator import generate_email, clean_job_title
from mailer.sender import is_sending_enabled, send_email, sender_address

st.set_page_config(page_title="Invasive Outreach Agent", layout="wide")

IST = timezone(timedelta(hours=5, minutes=30))
DAILY_APPROVAL_LIMIT = 20
MAX_NEW_LEADS_PER_RUN = 20
MORNING_RUN_HOUR = 11  # Auto-run fires on the first visit at/after 11:00 AM IST

DEFAULT_SOURCES = [
    ('https://weworkremotely.com/categories/remote-design-jobs', 'We Work Remotely - Design'),
    ('https://remoteok.com/remote-design-jobs', 'RemoteOK - Design'),
    ('https://jobspresso.co/remote-design-jobs/', 'Jobspresso - Design'),
    ('https://remotive.com/remote-jobs/design', 'Remotive - Design'),
]

def ist_now():
    """Current time in India Standard Time."""
    return datetime.now(IST)

def ist_today():
    """Today's date (India time) as YYYY-MM-DD."""
    return ist_now().strftime('%Y-%m-%d')

def get_approved_today():
    """How many emails have been approved today (India time)."""
    return int(get_state(f'approved_count_{ist_today()}') or 0)

def add_approved_today(count):
    """Record newly approved emails against today's daily limit."""
    set_state(f'approved_count_{ist_today()}', str(get_approved_today() + count))

def initialize_session():
    """Initialize session state."""
    if 'initialized' not in st.session_state:
        init_db()
        if get_state('sources_seeded') is None:
            for url, label in DEFAULT_SOURCES:
                add_job_source(url, label)
            set_state('sources_seeded', '1')
        st.session_state.initialized = True

initialize_session()

def discover_and_save(job_url, actor='SYSTEM', require_design_title=True, prefetched=None):
    """
    Research one job URL end-to-end: check duplicates, research the job and
    company, score the lead, draft the email, and save it as DRAFT_READY.

    If `prefetched` is given (from a board's structured data feed) it supplies the
    title, company name, and description directly instead of scraping the page.

    Returns a dict:
        lead_id     - new lead id, or None if the job was skipped
        skip_reason - why the job was skipped (None on success)
        job / company / score / email - research context when available
    """
    result = {'lead_id': None, 'skip_reason': None,
              'job': None, 'company': None, 'score': None, 'email': None}

    is_dup, dup_info = check_duplicate(job_url=job_url)
    if is_dup:
        result['skip_reason'] = f"Already researched (lead {dup_info['lead_id']})"
        return result

    if prefetched:
        job = {
            'status': 'SUCCESS',
            'job_title': prefetched.get('job_title'),
            'company_name': prefetched.get('company_name'),
            'company_domain': prefetched.get('company_domain'),
            'job_description': prefetched.get('job_description'),
            'warnings': [],
        }
    else:
        job = research_job(job_url)
    result['job'] = job
    if job['status'] == 'ERROR':
        result['skip_reason'] = f"Could not read job page: {job['error']}"
        return result

    raw_title = job.get('job_title') or ''
    job_title = clean_job_title(raw_title)
    job_description = job.get('job_description') or ''
    company_name = job.get('company_name')
    company_domain = job.get('company_domain')

    if require_design_title and not looks_like_design_job(raw_title):
        result['skip_reason'] = 'Not a design role'
        return result

    is_dup, dup_info = check_duplicate(company_domain=company_domain)
    if is_dup:
        result['skip_reason'] = f"Company already contacted (lead {dup_info['lead_id']})"
        return result

    is_dup, dup_info = check_company_name_duplicate(company_name)
    if is_dup:
        result['skip_reason'] = (f"Company already has a lead "
                                 f"({dup_info['lead_id']}, {dup_info['status']})")
        return result

    is_dnc, dnc_reason = check_do_not_contact(company_domain=company_domain)
    if is_dnc:
        result['skip_reason'] = f'On do-not-contact list: {dnc_reason}'
        return result

    company = research_company(company_name, company_domain, job_description)
    result['company'] = company

    score_result = score_lead(
        job_title=job_title,
        job_description=job_description,
        date_posted=None,
        company_website=company.get('company_website'),
        date_discovered=ist_now().isoformat()
    )
    result['score'] = score_result

    # Prefer an AI-written, job-specific email; fall back to the template.
    email_result = None
    try:
        from mailer.ai_writer import write_email
        email_result = write_email(
            job_title=job_title,
            job_description=job_description,
            company_name=company_name or '',
            recipient_email=None
        )
    except Exception:
        email_result = None
    if not email_result:
        email_result = generate_email(
            job_title=job_title,
            job_description=job_description,
            company_name=company_name or '',
            recipient_email=None
        )
    result['email'] = email_result

    lead_id = create_lead({
        'company_name': company_name,
        'company_domain': company_domain,
        'company_website': company.get('company_website'),
        'job_title': job_title,
        'job_url': job_url,
        'job_description': job_description,
        'date_discovered': ist_now().isoformat(),
        'outreach_subject': email_result['subject'],
        'outreach_email': email_result['body'],
        'lead_fit_score': score_result['score'],
        'fit_score_reasons': explain_score(score_result),
        'status': 'DRAFT_READY'
    })
    log_audit(lead_id, 'LEAD_DISCOVERED', actor=actor, details=f'Score: {score_result["score"]}')
    log_audit(lead_id, 'EMAIL_DRAFTED', actor='SYSTEM', details=f'Subject: {email_result["subject"]}')

    result['lead_id'] = lead_id
    return result

def run_daily_discovery(force=False):
    """
    Once per day, search every configured job source for new design jobs and
    draft outreach emails. The automatic run fires on the first time the app is
    opened at or after 11:00 AM India time each day; the Settings "Run now"
    button (force=True) bypasses both the once-a-day and the time-of-day guards.
    """
    today = ist_today()
    if not force:
        if get_state('last_run_date') == today:
            return
        if ist_now().hour < MORNING_RUN_HOUR:
            # Too early — wait until the morning run window.
            return

    sources = list_job_sources(enabled_only=True)
    if not sources:
        if force:
            st.warning("No job sources configured — add one in Settings first.")
        return

    set_state('last_run_date', today)

    created = 0
    skipped = 0
    failed_sources = 0

    with st.status(f"🌅 Morning run — searching {len(sources)} job source(s) for new design jobs...",
                   expanded=True) as status:
        for source in sources:
            name = source['label'] or source['url']
            st.write(f"🔎 Searching {name}...")

            # Prefer a structured data feed (real employer names) when the board
            # offers one; otherwise fall back to scraping links off the page.
            feed = None
            try:
                feed = fetch_structured_jobs(source['url'])
            except Exception as e:
                feed = {'status': 'ERROR', 'error': str(e), 'jobs': []}

            if feed is not None:
                if feed['status'] == 'ERROR':
                    failed_sources += 1
                    st.write(f"⚠️ Could not read {name}: {feed['error']}")
                    continue
                work_items = [(j['url'], j) for j in feed['jobs']]
            else:
                try:
                    scraped = scrape_source(source['url'])
                except Exception as e:
                    scraped = {'status': 'ERROR', 'error': str(e), 'job_urls': []}
                if scraped['status'] == 'ERROR':
                    failed_sources += 1
                    st.write(f"⚠️ Could not read {name}: {scraped['error']}")
                    continue
                work_items = [(u, None) for u in scraped['job_urls']]

            if not work_items:
                st.write("No design job links found on this source.")
                continue

            for job_url, prefetched in work_items:
                if created >= MAX_NEW_LEADS_PER_RUN:
                    break
                # One bad job page must never kill the whole morning run.
                try:
                    r = discover_and_save(job_url, actor='SYSTEM', prefetched=prefetched)
                except Exception:
                    skipped += 1
                    continue
                if r['lead_id']:
                    created += 1
                    job = r['job'] or {}
                    st.write(f"✉️ Drafted: {job.get('company_name') or 'Unknown company'} — "
                             f"{job.get('job_title') or 'Unknown role'} (score {r['score']['score']}/100)")
                else:
                    skipped += 1

            if created >= MAX_NEW_LEADS_PER_RUN:
                st.write(f"Reached today's cap of {MAX_NEW_LEADS_PER_RUN} new drafts.")
                break

        summary = f"{created} new emails drafted, {skipped} jobs skipped"
        if failed_sources:
            summary += f", {failed_sources} source(s) unreachable"

        set_state('last_run_time', ist_now().strftime('%d %b %Y, %I:%M %p IST'))
        set_state('last_run_summary', summary)
        status.update(label=f"🌅 Morning run complete — {summary}", state="complete", expanded=False)

    if created:
        st.success(f"🌅 {created} new emails are waiting in **Pending Approvals**.")

def page_discover_lead():
    """Page: Manually discover and research a new lead."""
    st.header("🔍 Discover Lead")
    st.write("Paste a job URL to research it and draft an outreach email. "
             "New design jobs are also discovered automatically every morning.")

    job_url = st.text_input("Job URL", placeholder="https://jobs.company.com/job/123")

    if st.button("Research & Draft Email", type="primary") and job_url:
        with st.spinner("Researching job and drafting email..."):
            # Persist so the result survives reruns (expander taps etc.).
            st.session_state.last_discover_result = discover_and_save(
                job_url, actor='USER', require_design_title=False)

    result = st.session_state.get('last_discover_result')
    if not result:
        return

    if result['skip_reason']:
        st.warning(f"Skipped: {result['skip_reason']}")
        return

    job = result['job']
    score = result['score']
    email = result['email']

    st.success("✅ Email drafted and added to Pending Approvals")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Job Title:** {job.get('job_title') or 'Unknown'}")
        st.write(f"**Company:** {job.get('company_name') or 'Unknown'}")
    with col2:
        st.metric("Lead Fit Score", f"{score['score']}/100", score['recommendation'])

    with st.expander("Scoring details"):
        st.write(explain_score(score))

    if job.get('job_description'):
        with st.expander("Job description"):
            st.text(job['job_description'][:3000])

    st.text_input("Subject", value=email['subject'], disabled=True)
    st.text_area("Email Body", value=email['body'], height=280, disabled=True)

    st.info("Go to **Pending Approvals** in the sidebar to approve it.")

def page_research_lead():
    """Page: Paste a job (e.g. LinkedIn), research the company + founder, draft an email."""
    st.header("🔎 Research a Job")
    st.write("Paste a job posting — a LinkedIn link works best with the job text pasted below it. "
             "The AI researches the company, finds the founder or decision-maker and a contact email, "
             "and drafts an outreach email addressed to them.")

    try:
        from mailer.lead_researcher import research_and_write
        from mailer.ai_writer import is_ai_available
        ai_on = is_ai_available()
    except Exception:
        ai_on = False

    if not ai_on:
        st.warning("This page needs AI. Add an Anthropic API key in **Settings → (how to turn on AI writing)** "
                   "first, then come back.")
        return

    job_input = st.text_area(
        "Job link and/or pasted job description",
        height=180,
        placeholder="https://www.linkedin.com/jobs/view/1234567890/\n\n(Optional but recommended: paste the "
                    "job description text here too for the most accurate result.)"
    )

    if st.button("🔎 Research & Draft Email", type="primary") and job_input.strip():
        with st.spinner("Researching the company, finding the decision-maker, and drafting the email… "
                        "this can take up to a minute."):
            st.session_state.last_research = research_and_write(job_input)

    data = st.session_state.get('last_research')
    if not data:
        return

    if data.get('error'):
        st.error(data['error'])
        return

    st.success("✅ Research complete — review below, then save it to Pending Approvals.")

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Company:** {data.get('company') or 'Unknown'}")
        st.write(f"**Role:** {data.get('role') or 'Unknown'}")
        st.write(f"**Location:** {data.get('location') or 'Unknown'}")
    with col2:
        st.write(f"**Contact:** {data.get('contact_name') or 'Unknown'}")
        st.write(f"**Title:** {data.get('contact_title') or 'Unknown'}")

    if data.get('role_summary'):
        with st.expander("What the role focuses on"):
            st.write(data['role_summary'])

    # Contact email — always flag for verification.
    email_addr = (data.get('contact_email') or '').strip()
    confidence = (data.get('email_confidence') or 'unknown').lower()
    st.subheader("📇 Contact email")
    if email_addr:
        badge = {'published': '🟢 published on a public source',
                 'inferred': '🟡 inferred from the company email pattern',
                 'unknown': '⚪ uncertain'}.get(confidence, '⚪ uncertain')
        st.write(f"**{email_addr}**  —  {badge}")
        if data.get('email_source'):
            st.caption(f"Source: {data['email_source']}")
        st.warning("⚠️ Always verify this address before sending — AI-found emails can be wrong.")
    else:
        st.warning("No contact email found. You can add one yourself before sending.")

    if data.get('notes'):
        st.info(f"**Worth checking:** {data['notes']}")

    st.subheader("📧 Drafted email")
    st.text_input("Subject", value=data.get('subject', ''), disabled=True, key="research_subj")
    st.text_area("Email", value=data.get('body', ''), height=320, disabled=True, key="research_body")

    if st.button("💾 Save to Pending Approvals", type="primary"):
        lead_id = create_lead({
            'company_name': data.get('company'),
            'company_domain': None,
            'company_website': None,
            'job_title': data.get('role'),
            'job_url': job_input.strip()[:500],
            'job_description': data.get('role_summary'),
            'date_discovered': ist_now().isoformat(),
            'outreach_subject': data.get('subject'),
            'outreach_email': data.get('body'),
            'lead_fit_score': None,
            'fit_score_reasons': None,
            'status': 'DRAFT_READY',
        })
        update_lead(lead_id, {
            'contact_name': data.get('contact_name'),
            'contact_title': data.get('contact_title'),
            'contact_email': email_addr or None,
        })
        log_audit(lead_id, 'LEAD_RESEARCHED', actor='USER',
                  details=f"Contact: {data.get('contact_name')} <{email_addr}> ({confidence})")
        log_audit(lead_id, 'EMAIL_DRAFTED', actor='SYSTEM', details='AI web research')
        st.session_state.last_research = None
        st.session_state.flash = "✅ Saved to Pending Approvals — review and approve it there."
        st.session_state.current_page = "approvals"
        st.rerun()

def page_approval_queue():
    """Page: Review and approve pending emails (max 20 per day)."""
    st.header("⏳ Pending Approvals")

    sending_on = is_sending_enabled()
    verb = "Sent" if sending_on else "Approved"

    approved_today = get_approved_today()
    remaining_today = max(0, DAILY_APPROVAL_LIMIT - approved_today)

    pending = list_leads(status='DRAFT_READY', limit=100)

    col1, col2, col3 = st.columns(3)
    col1.metric("Waiting for approval", len(pending))
    col2.metric(f"{verb} today", f"{approved_today}/{DAILY_APPROVAL_LIMIT}")
    col3.metric("Left today", remaining_today)

    if sending_on:
        st.success(f"📤 Sending is ON — approving sends the email from **{sender_address()}** "
                   "(up to 20/day). Recipients without an email address are skipped.")
    else:
        st.info("📮 Sending is off — approving marks emails ready to copy into Gmail. "
                "Turn on automatic sending in **Settings**.")

    if not pending:
        st.info("✅ No pending emails. All caught up!")
        return

    if remaining_today == 0:
        st.error(f"🚫 Daily limit of {DAILY_APPROVAL_LIMIT} reached. "
                 "More unlock tomorrow (India time).")

    st.divider()

    approval_states = {}

    for lead in pending:
        score_txt = f" (Score: {lead['lead_fit_score']}/100)" if lead['lead_fit_score'] is not None else ""
        header = (f"{lead['company_name'] or 'Unknown company'} — "
                  f"{lead['job_title'] or 'Unknown role'}{score_txt}")
        with st.expander(header):
            col1, col2 = st.columns([1, 3])

            with col1:
                if lead['lead_fit_score'] is not None:
                    st.metric("Score", f"{lead['lead_fit_score']}/100")
                approval_states[lead['lead_id']] = st.checkbox(
                    "Approve",
                    key=f"approve_{lead['lead_id']}"
                )

            with col2:
                if lead['contact_name'] or lead['contact_email']:
                    to_line = lead['contact_name'] or ''
                    if lead['contact_email']:
                        to_line += f" <{lead['contact_email']}>"
                    st.write(f"**To:** {to_line.strip()}")
                st.text_input("Subject", value=lead['outreach_subject'] or '',
                              disabled=True, key=f"subj_{lead['lead_id']}")
                st.text_area("Email", value=lead['outreach_email'] or '',
                             height=200, disabled=True, key=f"body_{lead['lead_id']}")

    st.divider()

    def approve_leads(lead_ids):
        selected = lead_ids[:remaining_today]
        sent = 0
        approved = 0
        errors = []
        for lead_id in selected:
            lead = get_lead(lead_id)
            if not lead:
                continue
            if sending_on:
                to_email = (lead['contact_email'] or '').strip()
                if not to_email:
                    # Nothing to send to — mark ready for manual sending instead.
                    update_lead(lead_id, {'status': 'APPROVED'})
                    log_audit(lead_id, 'EMAIL_APPROVED', actor='USER',
                              details='Approved (no recipient email — manual send)')
                    approved += 1
                    continue
                result = send_email(to_email, lead['outreach_subject'], lead['outreach_email'])
                if result['ok']:
                    update_lead(lead_id, {'status': 'CONTACTED',
                                          'date_contacted': ist_now().isoformat()})
                    log_audit(lead_id, 'EMAIL_SENT', actor='USER',
                              details=f'Sent to {to_email} via SMTP')
                    sent += 1
                else:
                    log_audit(lead_id, 'SEND_FAILED', actor='SYSTEM', details=result['error'])
                    errors.append(f"{lead['company_name'] or 'lead'}: {result['error']}")
            else:
                update_lead(lead_id, {'status': 'APPROVED'})
                log_audit(lead_id, 'EMAIL_APPROVED', actor='USER', details='Approved for sending')
                approved += 1

        # Only count what actually completed against the daily limit.
        add_approved_today(sent + approved)

        parts = []
        if sent:
            parts.append(f"📤 {sent} email(s) sent")
        if approved:
            parts.append(f"✅ {approved} approved (no email address — send manually)")
        st.session_state.flash = " · ".join(parts) if parts else "Nothing to do."
        if errors:
            st.session_state.flash_warning = "Some did not send: " + "; ".join(errors[:5])
        overflow = len(lead_ids) - len(selected)
        if overflow > 0:
            prev = st.session_state.get('flash_warning', '')
            st.session_state.flash_warning = (prev + " " if prev else "") + \
                f"Daily limit of {DAILY_APPROVAL_LIMIT} reached: {overflow} stay pending until tomorrow."
        st.rerun()

    action = "Approve & Send" if sending_on else "Approve"
    col1, col2 = st.columns(2)

    with col1:
        if st.button(f"✅ {action} Selected", type="primary", disabled=remaining_today == 0):
            selected = [lead_id for lead_id, approved in approval_states.items() if approved]
            if not selected:
                st.warning("Tick 'Approve' on the emails you want first.")
            else:
                approve_leads(selected)

    with col2:
        approvable = min(len(pending), remaining_today)
        if st.button(f"✅ {action} All ({approvable})", disabled=remaining_today == 0):
            approve_leads([lead['lead_id'] for lead in pending])

def page_leads_list():
    """Page: View all leads."""
    st.header("📋 Lead History")

    status_filter = st.selectbox("Filter by status", ["ALL"] + [
        'DRAFT_READY', 'APPROVED', 'CONTACTED', 'NOT_QUALIFIED'
    ])

    leads = list_leads(status=None if status_filter == "ALL" else status_filter, limit=100)

    if not leads:
        st.info("No leads found")
        return

    for lead in leads:
        header = (f"{lead['company_name'] or 'Unknown company'} — "
                  f"{lead['job_title'] or 'Unknown role'} · {lead['status']}")
        with st.expander(header):
            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Status:** {lead['status']}")
                st.write(f"**Score:** {lead['lead_fit_score'] or 'N/A'}/100")

            with col2:
                st.write(f"**URL:** {lead['job_url']}")
                st.write(f"**Discovered:** {lead['date_discovered']}")

            if lead['contact_email']:
                st.write(f"**Contact:** {lead['contact_email']}")

            if lead['status'] == 'CONTACTED':
                st.write(f"**Sent:** {lead['date_contacted']}")

            if st.button(f"Open email", key=f"open_{lead['lead_id']}"):
                st.session_state.current_lead_id = lead['lead_id']
                st.session_state.current_page = "review_email"
                st.rerun()

def page_review_email():
    """Page: View one email, copy it, and mark it as sent."""
    st.header("📧 Email Review")

    lead_id = st.session_state.get('current_lead_id')
    if not lead_id:
        st.error("No lead selected")
        return

    lead = get_lead(lead_id)
    if not lead:
        st.error(f"Lead not found: {lead_id}")
        return

    st.subheader(f"{lead['company_name'] or 'Unknown company'} — {lead['job_title'] or 'Unknown role'}")

    col1, col2 = st.columns(2)
    with col1:
        if lead['lead_fit_score'] is not None:
            st.metric("Fit Score", f"{lead['lead_fit_score']}/100")
        st.write(f"**Status:** {lead['status']}")
    with col2:
        if lead['contact_name'] or lead['contact_email']:
            st.write(f"**Contact:** {lead['contact_name'] or '—'}"
                     f"{' (' + lead['contact_title'] + ')' if lead['contact_title'] else ''}")
            if lead['contact_email']:
                st.write(f"**Email:** {lead['contact_email']}")
                st.caption("⚠️ Verify this address before sending.")
        st.write(f"**Job URL:** {lead['job_url']}")

    if lead['status'] in ('DRAFT_READY', 'APPROVED'):
        st.subheader("Copy & send from your Gmail")
        st.caption("Tap the copy icon in the corner of each box, paste into a new Gmail message, "
                   "then come back and mark it as sent.")

        st.write("**Subject:**")
        st.code(lead['outreach_subject'] or '', language=None)
        st.write("**Email body:**")
        st.code(lead['outreach_email'] or '', language=None)

        col1, col2 = st.columns(2)

        if lead['status'] == 'DRAFT_READY':
            # Sending goes through approval so the 20/day limit always applies.
            remaining_today = max(0, DAILY_APPROVAL_LIMIT - get_approved_today())
            st.info("This email is not approved yet — approve it before sending.")
            with col1:
                if st.button("✅ Approve this email", type="primary",
                             disabled=remaining_today == 0):
                    update_lead(lead_id, {'status': 'APPROVED'})
                    log_audit(lead_id, 'EMAIL_APPROVED', actor='USER',
                              details='Approved from review page')
                    add_approved_today(1)
                    st.session_state.flash = "✅ Approved — now copy it into Gmail and mark it as sent."
                    st.rerun()
                if remaining_today == 0:
                    st.caption(f"Daily limit of {DAILY_APPROVAL_LIMIT} approvals reached — "
                               "try again tomorrow.")
        else:
            contact_email = st.text_input("Recipient email (verify before sending)",
                                          value=lead['contact_email'] or '',
                                          placeholder="name@company.com")
            with col1:
                if st.button("✅ Mark as Sent", type="primary"):
                    updates = {'status': 'CONTACTED', 'date_contacted': ist_now().isoformat()}
                    if contact_email:
                        updates['contact_email'] = contact_email
                    update_lead(lead_id, updates)
                    details = 'Sent manually from Gmail'
                    if contact_email:
                        details += f' to {contact_email}'
                    log_audit(lead_id, 'EMAIL_SENT', actor='USER', details=details)
                    st.session_state.flash = "✅ Marked as sent."
                    st.session_state.current_page = "leads"
                    st.session_state.current_lead_id = None
                    st.rerun()

        with col2:
            if st.button("❌ Mark as Not Qualified"):
                update_lead(lead_id, {'status': 'NOT_QUALIFIED'})
                log_audit(lead_id, 'REJECTED_BY_USER', actor='USER')
                st.session_state.flash = "Lead marked as not qualified."
                st.session_state.current_page = "leads"
                st.session_state.current_lead_id = None
                st.rerun()

    elif lead['status'] == 'CONTACTED':
        st.info(f"✅ Sent on {lead['date_contacted']}")
        st.write("**Subject:**")
        st.code(lead['outreach_subject'] or '', language=None)
        st.write("**Email body:**")
        st.code(lead['outreach_email'] or '', language=None)

    else:
        st.text_input("Subject", value=lead['outreach_subject'] or '', disabled=True)
        st.text_area("Email Body", value=lead['outreach_email'] or '', height=300, disabled=True)

    audit_trail = get_audit_trail(lead_id)
    if audit_trail:
        with st.expander("Audit Trail"):
            for entry in audit_trail:
                st.write(f"**{entry['action']}** ({entry['timestamp']})")
                if entry['details']:
                    st.write(f"  {entry['details']}")

def page_settings():
    """Page: Settings and configuration."""
    st.header("⚙️ Settings")

    st.subheader("🌅 Morning Run — Job Sources")
    st.write("When you open the app in the morning (from 11:00 AM India time), it automatically "
             "searches these pages once a day for new design jobs and drafts outreach emails for "
             "your approval. Open it any time after 11 AM and the emails will be waiting.")

    last_run = get_state('last_run_time')
    last_summary = get_state('last_run_summary')
    if last_run:
        st.info(f"Last run: {last_run} — {last_summary or ''}")

    sources = list_job_sources()
    if not sources:
        st.warning("No job sources configured. Add one below to enable the morning run.")

    for source in sources:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(f"**{source['label'] or 'Job source'}**  \n{source['url']}")
        with col2:
            if st.button("Remove", key=f"rm_src_{source['source_id']}"):
                remove_job_source(source['source_id'])
                st.rerun()

    with st.form("add_source_form", clear_on_submit=True):
        new_label = st.text_input("Name (optional)", placeholder="e.g. Dribbble Jobs")
        new_url = st.text_input("Job board page URL", placeholder="https://...")
        if st.form_submit_button("➕ Add Source"):
            if new_url.strip():
                if add_job_source(new_url.strip(), new_label.strip() or None):
                    st.session_state.flash = "✅ Source added — it will be searched on the next run."
                else:
                    st.session_state.flash_warning = "That URL is already in the list."
                st.rerun()
            else:
                st.error("Please enter a URL.")

    if st.button("▶️ Run morning discovery now", type="primary"):
        st.session_state.force_run = True
        st.rerun()

    st.divider()

    st.subheader("✍️ Email Writing")
    try:
        from mailer.ai_writer import is_ai_available
        ai_on = is_ai_available()
    except Exception:
        ai_on = False
    if ai_on:
        st.success("AI writing is **active** — each email is written by Claude, tailored to the "
                   "specific job post.")
    else:
        st.warning("AI writing is **off** — emails use the built-in template. Add an Anthropic API "
                   "key in the app's Secrets to turn on job-specific AI writing.")
        with st.expander("How to turn on AI writing"):
            st.markdown(
                "1. Get an API key from **console.anthropic.com** (Settings → API Keys).\n"
                "2. In Streamlit Cloud, open **Manage app → Settings → Secrets**.\n"
                "3. Add this line and save:\n"
            )
            st.code('ANTHROPIC_API_KEY = "sk-ant-..."', language="toml")
            st.caption("The app restarts automatically and starts writing AI emails on the next run.")

    st.subheader("📤 Email Sending")
    send_on = is_sending_enabled()
    if send_on:
        st.success(f"Automatic sending is **on** — approved emails are sent from **{sender_address()}** "
                   f"(up to {DAILY_APPROVAL_LIMIT}/day).")
        test_to = st.text_input("Send a test email to yourself first",
                                placeholder="you@example.com")
        if st.button("✉️ Send test email"):
            if not test_to.strip():
                st.warning("Enter an address to send the test to.")
            else:
                with st.spinner("Sending test..."):
                    res = send_email(test_to.strip(), "Invasive Outreach Agent — test",
                                     "This is a test from your outreach app. If you received it, "
                                     "sending is working. — Sonia Baig, Invasive Design")
                if res['ok']:
                    st.success(f"✅ Test sent to {test_to.strip()}. Check the inbox (and spam folder).")
                else:
                    st.error(f"❌ Could not send: {res['error']}")
    else:
        st.warning("Automatic sending is **off** — approved emails are copied into Gmail by hand. "
                   "Turn on one-click sending below.")
        with st.expander("How to turn on automatic sending (about 5 minutes)"):
            st.markdown(
                "You'll send from your own Gmail / Google Workspace using an **App Password** "
                "(safer than your real password, and revocable anytime).\n\n"
                "1. Turn on **2-Step Verification** at **myaccount.google.com → Security** "
                "(required for App Passwords).\n"
                "2. Go to **myaccount.google.com/apppasswords**, create one named `outreach`, "
                "and copy the 16-character password it shows.\n"
                "3. In Streamlit Cloud: **Manage app → Settings → Secrets**, add these lines "
                "(keep your existing `ANTHROPIC_API_KEY` line too), and Save:"
            )
            st.code(
                'SMTP_EMAIL = "sonia.baig@invasived.com"\n'
                'SMTP_APP_PASSWORD = "your 16-char app password"\n'
                'SMTP_FROM_NAME = "Sonia Baig"',
                language="toml",
            )
            st.caption("Use the mailbox the emails should come from. The app restarts automatically; "
                       "then send yourself a test here before emailing real people.")

    st.subheader("💾 Database")
    st.caption("Streamlit Cloud storage can reset when the app restarts — "
               "export your leads to CSV regularly as a backup.")

    from database.db import export_to_csv

    filepath = export_to_csv()
    if filepath:
        with open(filepath, 'r') as f:
            csv_data = f.read()

        st.download_button(
            label="⬇️ Download all leads as CSV",
            data=csv_data,
            file_name="leads_export.csv",
            mime="text/csv"
        )
    else:
        st.caption("No leads to export yet.")

def main():
    """Main app."""
    st.sidebar.title("Invasive Outreach Agent")

    if 'current_page' not in st.session_state:
        st.session_state.current_page = "discover"

    # Run discovery BEFORE rendering the sidebar badge so the counts are fresh.
    force_run = st.session_state.pop('force_run', False)
    run_daily_discovery(force=force_run)

    pending_count = len(list_leads(status='DRAFT_READY', limit=100))
    st.sidebar.caption(f"⏳ {pending_count} pending · "
                       f"✅ {get_approved_today()}/{DAILY_APPROVAL_LIMIT} approved today")
    last_run = get_state('last_run_time')
    if last_run:
        st.sidebar.caption(f"🌅 Last morning run: {last_run}")
    else:
        next_run = "today" if ist_now().hour < MORNING_RUN_HOUR else "tomorrow"
        st.sidebar.caption(f"🌅 Next morning run: {next_run} at 11:00 AM IST")

    flash = st.session_state.pop('flash', None)
    if flash:
        st.success(flash)
    flash_warning = st.session_state.pop('flash_warning', None)
    if flash_warning:
        st.warning(flash_warning)

    if st.session_state.current_page == "review_email" and st.session_state.get('current_lead_id'):
        if st.sidebar.button("⬅ Back to Lead History"):
            st.session_state.current_page = "leads"
            st.session_state.current_lead_id = None
            st.rerun()
        page_review_email()
        return

    page_options = ["Discover Lead", "Research a Job", "Pending Approvals", "Lead History", "Settings"]
    page_index = {
        "discover": 0,
        "research": 1,
        "approvals": 2,
        "leads": 3,
        "settings": 4
    }.get(st.session_state.current_page, 0)

    page = st.sidebar.radio("Navigation", page_options, index=page_index)

    if page == "Discover Lead":
        st.session_state.current_page = "discover"
        page_discover_lead()
    elif page == "Research a Job":
        st.session_state.current_page = "research"
        page_research_lead()
    elif page == "Pending Approvals":
        st.session_state.current_page = "approvals"
        page_approval_queue()
    elif page == "Lead History":
        st.session_state.current_page = "leads"
        page_leads_list()
    elif page == "Settings":
        st.session_state.current_page = "settings"
        page_settings()

if __name__ == "__main__":
    main()
