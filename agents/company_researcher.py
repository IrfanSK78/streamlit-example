"""Research companies and their websites."""

import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def research_company(company_name, company_domain, job_description):
    """Research company website."""
    if not company_domain:
        return {
            'status': 'ERROR',
            'error': 'No company domain provided',
            'company_website': None,
            'complexity_observations': []
        }

    website_url = f'https://{company_domain}' if not company_domain.startswith('http') else company_domain

    try:
        response = requests.get(website_url, timeout=10, verify=False)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        return {
            'status': 'PARTIAL',
            'error': 'Website request timed out',
            'company_website': website_url,
            'complexity_observations': []
        }
    except requests.exceptions.ConnectionError:
        return {
            'status': 'ERROR',
            'error': 'Could not connect to website',
            'company_website': website_url,
            'complexity_observations': []
        }
    except Exception as e:
        logger.warning(f"Error researching company {company_domain}: {str(e)}")
        return {
            'status': 'ERROR',
            'error': str(e),
            'company_website': website_url,
            'complexity_observations': []
        }

    try:
        soup = BeautifulSoup(response.content, 'html.parser')
        observations = analyze_website_complexity(soup)
        return {
            'status': 'SUCCESS',
            'company_website': website_url,
            'complexity_observations': observations
        }
    except Exception as e:
        logger.error(f"Error analyzing company website: {str(e)}")
        return {
            'status': 'PARTIAL',
            'error': str(e),
            'company_website': website_url,
            'complexity_observations': []
        }

def analyze_website_complexity(soup):
    """Analyze website for complexity indicators."""
    observations = []
    forms = soup.find_all('form')
    if forms:
        observations.append(f"Website has {len(forms)} forms")
    nav = soup.find('nav')
    if nav:
        nav_items = nav.find_all(['a', 'li'])
        if nav_items:
            observations.append(f"Navigation menu with {len(nav_items)} items")
    scripts = soup.find_all('script')
    if len(scripts) > 10:
        observations.append("Heavy JavaScript implementation")
    if soup.find('video') or soup.find('iframe'):
        observations.append("Rich media content (video/embeds)")
    headings = soup.find_all(['h1', 'h2', 'h3'])
    if len(headings) > 5:
        observations.append("Complex content hierarchy")
    return observations if observations else ["Standard website structure"]
