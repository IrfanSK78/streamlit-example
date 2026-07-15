"""Research job postings from URLs."""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)

def research_job(job_url):
    """Research a job posting from URL."""
    try:
        response = requests.get(job_url, timeout=10)
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

def extract_company_name(soup, job_url):
    """Extract company name from page or URL."""
    meta = soup.find('meta', property='og:site_name')
    if meta:
        return meta.get('content')
    domain = extract_domain_from_url(job_url)
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
