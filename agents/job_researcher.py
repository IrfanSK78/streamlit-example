"""Research job postings from URLs."""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
}

# Domains that host jobs for OTHER companies. The page domain is not the
# hiring company's domain, so company info must come from the page content.
KNOWN_JOB_BOARDS = {
    'weworkremotely.com', 'remoteok.com', 'remoteok.io', 'remote.co',
    'indeed.com', 'linkedin.com', 'glassdoor.com', 'wellfound.com',
    'dribbble.com', 'behance.net', 'monster.com', 'ziprecruiter.com',
    'workingnomads.com', 'jobspresso.co', 'dynamitejobs.com',
}

def is_job_board(domain):
    """True if the domain is a job board rather than a company site."""
    if not domain:
        return False
    return any(domain == board or domain.endswith('.' + board) for board in KNOWN_JOB_BOARDS)

def research_job(job_url):
    """Research a job posting from URL."""
    try:
        response = requests.get(job_url, timeout=10, headers=HEADERS)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return {'status': 'ERROR', 'error': 'Request timed out', 'warnings': []}
    except requests.exceptions.ConnectionError:
        return {'status': 'ERROR', 'error': 'Connection failed', 'warnings': []}
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return {'status': 'ERROR', 'error': 'Page not found (404)', 'warnings': []}
        return {'status': 'ERROR', 'error': f'HTTP error: {e.response.status_code}', 'warnings': []}
    except Exception as e:
        return {'status': 'ERROR', 'error': str(e), 'warnings': []}

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator=' ')
        job_title = extract_job_title(soup, text)
        company_name = extract_company_name(soup, job_url)
        company_domain = extract_domain_from_url(job_url)
        if is_job_board(company_domain):
            # Job board domain is not the hiring company's domain.
            company_domain = None
        job_description = text[:5000] if text else None
        return {
            'status': 'SUCCESS',
            'job_title': job_title,
            'company_name': company_name,
            'company_domain': company_domain,
            'job_description': job_description,
            'warnings': []
        }
    except Exception as e:
        logger.error(f"Error parsing job: {str(e)}")
        return {
            'status': 'PARTIAL',
            'error': str(e),
            'job_title': None,
            'company_name': None,
            'company_domain': extract_domain_from_url(job_url),
            'job_description': None,
            'warnings': ['Could not parse all job details']
        }

def extract_job_title(soup, text):
    """Extract job title from page."""
    h1 = soup.find('h1')
    if h1:
        return h1.get_text(strip=True)
    title_tag = soup.find('title')
    if title_tag:
        return title_tag.get_text(strip=True)
    return 'Job Position'

def extract_company_from_text(text):
    """Pull a company name out of text like 'Senior Designer at Acme - Remote OK'."""
    if not text:
        return None
    chunk = re.split(r'\s+[-|–—•]\s+', text)[0]
    match = re.search(r'\bat\s+([A-Z][A-Za-z0-9&.\' ]{1,40})', chunk)
    if match:
        name = match.group(1).strip(' .')
        if 2 <= len(name) <= 60:
            return name
    match = re.match(r'\s*([A-Z][A-Za-z0-9&.\' ]{1,40})\s+is hiring', text)
    if match:
        name = match.group(1).strip(' .')
        if 2 <= len(name) <= 60:
            return name
    return None

def extract_company_name(soup, job_url):
    """Extract company name from page or URL."""
    domain = extract_domain_from_url(job_url)

    if is_job_board(domain):
        # On job boards the site name is the board, not the employer.
        title_tag = soup.find('title')
        title_text = title_tag.get_text(strip=True) if title_tag else ''
        h1 = soup.find('h1')
        h1_text = h1.get_text(' ', strip=True) if h1 else ''

        company = extract_company_from_text(title_text) or extract_company_from_text(h1_text)
        if company:
            return company

        for cls in ['company', 'company-name', 'companyName', 'company_name', 'company-card']:
            element = soup.find(class_=cls)
            if element:
                name = element.get_text(' ', strip=True)
                if name and 2 <= len(name) <= 60:
                    return name
        return None

    meta = soup.find('meta', property='og:site_name')
    if meta and meta.get('content'):
        return meta.get('content')
    if domain:
        return domain.split('.')[0].title()
    return 'Unknown Company'

def extract_domain_from_url(url):
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        if domain:
            return domain.split('/')[0]
    except:
        pass
    return None
