"""Extract job information from URLs and job postings."""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_job_page(job_url):
    """
    Fetch job posting page content.
    Returns: (html_content, error_message)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(job_url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text, None
    except requests.exceptions.Timeout:
        return None, "Timeout: Job page took too long to load"
    except requests.exceptions.ConnectionError:
        return None, "Connection error: Could not reach job URL"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None, "Job posting not found (404) - may be expired"
        return None, f"HTTP error: {e.response.status_code}"
    except Exception as e:
        return None, f"Error fetching page: {str(e)}"

def extract_text_sections(html):
    """Extract main text content from HTML."""
    soup = BeautifulSoup(html, 'html.parser')

    for script in soup(["script", "style"]):
        script.decompose()

    text = soup.get_text(separator='\n', strip=True)
    return text

def guess_job_title_from_page(html, job_url):
    """
    Try to extract job title from page.
    Returns: job_title or None
    """
    soup = BeautifulSoup(html, 'html.parser')

    title_tag = soup.find('h1')
    if title_tag:
        return title_tag.get_text(strip=True)

    og_title = soup.find('meta', property='og:title')
    if og_title and og_title.get('content'):
        return og_title.get('content')

    page_title = soup.find('title')
    if page_title:
        return page_title.get_text(strip=True)

    return None

def guess_company_from_url(job_url):
    """
    Try to extract company name from job URL.
    Returns: company_name or None

    Examples:
    - https://jobs.lever.co/acme/... -> acme
    - https://greenhouse.io/...acme... -> acme (if extractable)
    - https://careers.acme.com/... -> acme
    """
    parsed = urlparse(job_url)
    domain = parsed.netloc.lower()

    # careers.acme.com -> acme
    if 'careers.' in domain:
        return domain.replace('careers.', '').split('.')[0]

    # jobs.acme.com -> acme
    if 'jobs.' in domain:
        return domain.replace('jobs.', '').split('.')[0]

    # acme.com (generic) -> harder to extract reliably
    if domain.count('.') >= 1:
        parts = domain.split('.')
        if parts[0] not in ['www', 'jobs', 'careers']:
            return parts[0]

    return None

def research_job(job_url):
    """
    Research a job posting.

    Returns: {
        'job_url': job_url,
        'job_title': extracted or guessed,
        'job_description': full text,
        'company_name': extracted or guessed,
        'company_domain': extracted from URL,
        'status': 'SUCCESS' | 'PARTIAL' | 'ERROR',
        'error': error_message if any,
        'warnings': [list of warnings]
    }
    """
    warnings = []
    html, fetch_error = fetch_job_page(job_url)

    if fetch_error:
        return {
            'job_url': job_url,
            'job_title': None,
            'job_description': None,
            'company_name': None,
            'company_domain': None,
            'status': 'ERROR',
            'error': fetch_error,
            'warnings': []
        }

    job_title = guess_job_title_from_page(html, job_url)
    if not job_title:
        warnings.append('Could not extract job title from page')

    job_description = extract_text_sections(html)
    if not job_description or len(job_description) < 100:
        warnings.append('Job description is very short or empty')

    company_name = guess_company_from_url(job_url)
    if not company_name:
        warnings.append('Could not extract company name from URL')

    company_domain = urlparse(job_url).netloc.lower()

    return {
        'job_url': job_url,
        'job_title': job_title,
        'job_description': job_description,
        'company_name': company_name,
        'company_domain': company_domain,
        'status': 'PARTIAL' if warnings else 'SUCCESS',
        'error': None,
        'warnings': warnings
    }
