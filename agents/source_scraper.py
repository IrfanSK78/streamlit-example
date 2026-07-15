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

def looks_like_design_job(text):
    """True if the text looks like a design role title."""
    return bool(text and _design_re.search(text))

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
