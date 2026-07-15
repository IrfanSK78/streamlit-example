"""Scrape job source pages (job boards) for design job posting links."""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'
}

DESIGN_LINK_PATTERNS = [
    r'\bux\b', r'\bui\b', r'ux/ui', r'ui/ux',
    r'user experience', r'product design', r'interaction design',
    r'visual design', r'experience design', r'design lead',
    r'head of design', r'design director', r'\bdesigner\b',
]
_design_re = re.compile('|'.join(DESIGN_LINK_PATTERNS), re.IGNORECASE)

# Matched against whole URL path segments (not substrings), so a job slug
# like 'designer-about-you-gmbh' is not wrongly skipped by 'about'.
SKIP_PATH_SEGMENTS = {
    'login', 'signup', 'sign-up', 'signin', 'sign-in', 'register',
    'privacy', 'terms', 'about', 'pricing', 'faq', 'advertise',
    'contact', 'contact-us', 'blog', 'newsletter', 'subscribe',
    'categories',
}

MAX_LINKS_PER_SOURCE = 15

REMOTIVE_API = "https://remotive.com/api/remote-jobs"

def looks_like_design_job(text):
    """True if the text looks like a design role title."""
    return bool(text and _design_re.search(text))

def fetch_structured_jobs(source_url):
    """Return fully-structured jobs from a board's official data feed when one
    exists (real company name, title, and description — no scraping guesswork),
    or None if this source has no supported feed (caller falls back to scraping).

    Returns a dict {'status', 'error', 'jobs': [ {url, job_title, company_name,
    company_domain, job_description}, ... ]} when a feed is used.
    """
    host = urlparse(source_url).netloc.lower()
    if 'remotive.com' in host:
        return _fetch_remotive()
    return None

def _strip_html(html):
    """Turn an HTML job description into readable plain text."""
    if not html:
        return ''
    try:
        return BeautifulSoup(html, 'html.parser').get_text(separator=' ').strip()
    except Exception:
        return html

def _fetch_remotive():
    """Fetch design jobs from Remotive's free public API (real employer names)."""
    try:
        response = requests.get(REMOTIVE_API, params={'category': 'design'},
                                timeout=15, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        return {'status': 'ERROR', 'error': 'Request timed out', 'jobs': []}
    except Exception as e:
        return {'status': 'ERROR', 'error': str(e), 'jobs': []}

    jobs = []
    for item in data.get('jobs', []):
        title = (item.get('title') or '').strip()
        if not looks_like_design_job(title):
            continue
        url = item.get('url')
        if not url:
            continue
        jobs.append({
            'url': url,
            'job_title': title,
            'company_name': (item.get('company_name') or '').strip() or None,
            'company_domain': None,  # the feed gives the employer name, not its domain
            'job_description': _strip_html(item.get('description') or '')[:5000],
        })
        if len(jobs) >= MAX_LINKS_PER_SOURCE:
            break
    return {'status': 'SUCCESS', 'error': None, 'jobs': jobs}

def scrape_source(source_url):
    """
    Fetch a job board page and extract links that look like design job postings.

    Returns: {
        'status': 'SUCCESS' | 'ERROR',
        'error': error message if failed,
        'job_urls': list of absolute URLs
    }
    """
    try:
        response = requests.get(source_url, timeout=15, headers=HEADERS)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return {'status': 'ERROR', 'error': 'Request timed out', 'job_urls': []}
    except requests.exceptions.ConnectionError:
        return {'status': 'ERROR', 'error': 'Connection failed', 'job_urls': []}
    except requests.exceptions.HTTPError as e:
        return {'status': 'ERROR', 'error': f'HTTP error: {e.response.status_code}', 'job_urls': []}
    except Exception as e:
        return {'status': 'ERROR', 'error': str(e), 'job_urls': []}

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        return {'status': 'ERROR', 'error': f'Could not parse page: {e}', 'job_urls': []}

    job_urls = []
    seen = set()

    for link in soup.find_all('a', href=True):
        href = link['href'].strip()
        if not href or href.startswith(('#', 'mailto:', 'javascript:', 'tel:')):
            continue

        link_text = link.get_text(separator=' ', strip=True)
        if not looks_like_design_job(link_text):
            continue

        full_url = urljoin(source_url, href).split('#')[0]
        if not full_url.startswith('http'):
            continue
        if full_url.rstrip('/') == source_url.rstrip('/'):
            continue

        path_segments = [seg.lower() for seg in urlparse(full_url).path.split('/') if seg]
        if any(seg in SKIP_PATH_SEGMENTS for seg in path_segments):
            continue

        if full_url in seen:
            continue

        seen.add(full_url)
        job_urls.append(full_url)

        if len(job_urls) >= MAX_LINKS_PER_SOURCE:
            break

    return {'status': 'SUCCESS', 'error': None, 'job_urls': job_urls}
