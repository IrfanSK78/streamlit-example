"""Research companies and their web presence."""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def build_company_website_url(company_name, company_domain=None):
    """
    Build likely company website URL from domain or company name.
    Returns: URL or None
    """
    if company_domain:
        if not company_domain.startswith('http'):
            return f'https://{company_domain}'
        return company_domain

    if company_name:
        company_slug = company_name.lower().replace(' ', '').replace(',', '')
        return f'https://{company_slug}.com'

    return None

def fetch_company_website(url):
    """
    Fetch company website content.
    Returns: (html_content, error_message)
    """
    if not url.startswith('http'):
        url = f'https://{url}'

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        response.raise_for_status()
        return response.text, None
    except requests.exceptions.Timeout:
        return None, "Timeout: Website took too long to load"
    except requests.exceptions.ConnectionError:
        return None, "Connection error: Could not reach website"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None, "Website not found (404)"
        return None, f"HTTP error: {e.response.status_code}"
    except Exception as e:
        return None, f"Error fetching website: {str(e)}"

def extract_website_text(html):
    """Extract clean text from website HTML."""
    soup = BeautifulSoup(html, 'html.parser')

    for script in soup(["script", "style", "nav", "footer"]):
        script.decompose()

    text = soup.get_text(separator='\n', strip=True)
    return text[:5000]

def analyze_website_complexity(html):
    """
    Assess website complexity/maturity.
    Returns: (complexity_score 0-10, observations)
    """
    soup = BeautifulSoup(html, 'html.parser')

    observations = []
    score = 0

    interactive_elements = len(soup.find_all(['canvas', 'svg', 'video']))
    if interactive_elements > 5:
        score += 3
        observations.append('Rich interactive elements detected')

    forms = len(soup.find_all('form'))
    if forms > 2:
        score += 2
        observations.append('Multiple form elements')

    is_responsive = False
    meta_viewport = soup.find('meta', attrs={'name': 'viewport'})
    if meta_viewport:
        is_responsive = True
        score += 2
        observations.append('Mobile-responsive design')

    product_sections = len(soup.find_all(['article', 'section']))
    if product_sections > 10:
        score += 2
        observations.append('Substantial content organization')

    return min(10, score), observations

def research_company(company_name, company_domain, job_description=None):
    """
    Research a company.

    Returns: {
        'company_name': company_name,
        'company_domain': company_domain,
        'company_website': website URL,
        'website_summary': brief summary of site,
        'website_complexity': 0-10 score,
        'complexity_observations': [list],
        'status': 'SUCCESS' | 'PARTIAL' | 'ERROR',
        'error': error_message if any,
        'warnings': [list]
    }
    """
    if not company_name and not company_domain:
        return {
            'company_name': None,
            'company_domain': None,
            'company_website': None,
            'website_summary': None,
            'website_complexity': 0,
            'complexity_observations': [],
            'status': 'ERROR',
            'error': 'No company name or domain provided',
            'warnings': []
        }

    website_url = build_company_website_url(company_name, company_domain)
    warnings = []

    if not website_url:
        return {
            'company_name': company_name,
            'company_domain': company_domain,
            'company_website': None,
            'website_summary': None,
            'website_complexity': 0,
            'complexity_observations': [],
            'status': 'ERROR',
            'error': 'Could not build website URL',
            'warnings': []
        }

    html, fetch_error = fetch_company_website(website_url)

    if fetch_error:
        return {
            'company_name': company_name,
            'company_domain': company_domain,
            'company_website': website_url,
            'website_summary': None,
            'website_complexity': 0,
            'complexity_observations': [],
            'status': 'ERROR',
            'error': fetch_error,
            'warnings': ['Company website could not be verified']
        }

    website_text = extract_website_text(html)
    if not website_text or len(website_text) < 100:
        warnings.append('Website content is minimal or empty')

    complexity_score, complexity_obs = analyze_website_complexity(html)

    summary = website_text[:500] if website_text else None

    return {
        'company_name': company_name,
        'company_domain': company_domain,
        'company_website': website_url,
        'website_summary': summary,
        'website_complexity': complexity_score,
        'complexity_observations': complexity_obs,
        'status': 'PARTIAL' if warnings else 'SUCCESS',
        'error': None,
        'warnings': warnings
    }
