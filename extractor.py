import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import trafilatura
import tldextract
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


class AsyncPageExtractor:
    def __init__(self, session: aiohttp.ClientSession, timeout: int = 10, max_retries: int = 2):
        self.session = session
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries

    async def fetch_with_retry(self, url: str) -> Tuple[Optional[str], int, Optional[str]]:
        """Fetch HTML with retry for network errors"""
        last_error = None
        status_code = -1

        for attempt in range(self.max_retries + 1):
            try:
                async with self.session.get(url, timeout=self.timeout) as response:
                    status_code = response.status
                    if status_code == 200:
                        return (await response.text(), status_code, None)
                    return (None, status_code, f"HTTP status {status_code}")
            except asyncio.TimeoutError as e:
                last_error = f"Timeout (attempt {attempt + 1})"
                if attempt == self.max_retries:
                    return (None, -1, last_error)
            except aiohttp.ClientError as e:
                last_error = f"Client error: {str(e)} (attempt {attempt + 1})"
                if attempt == self.max_retries:
                    return (None, -1, last_error)
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                return (None, -1, last_error)

            await asyncio.sleep(1 * (attempt + 1))  # Exponential backoff

        return (None, -1, last_error)

    @staticmethod
    def extract_body_and_text(html: str, url: str) -> Tuple[str, str, BeautifulSoup]:
        """Extract body HTML, clean text and BeautifulSoup object"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            body_tag = soup.body
            body_html = str(body_tag) if body_tag else ''

            downloaded = trafilatura.fetch_url(url)
            text = trafilatura.extract(downloaded, include_links=False, include_tables=False) if downloaded else ''

            return body_html, text, soup
        except Exception as e:
            logger.error(f"Error parsing content from {url}: {str(e)}")
            return ("", "", BeautifulSoup("", 'html.parser'))

    @staticmethod
    def extract_links(soup: BeautifulSoup, base_url: str) -> Tuple[List[str], List[str]]:
        """Extract internal and external links from page"""
        try:
            base_domain = tldextract.extract(base_url).registered_domain
            list_url_in = set()
            list_url_out = set()

            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                try:
                    full_url = urljoin(base_url, href)
                    link_domain = tldextract.extract(full_url).registered_domain

                    if link_domain == base_domain:
                        list_url_in.add(full_url)
                    else:
                        list_url_out.add(full_url)
                except Exception:
                    continue

            return list(list_url_in), list(list_url_out)
        except Exception as e:
            logger.error(f"Error extracting links: {str(e)}")
            return [], []

    @staticmethod
    def extract_home(url: str) -> str:
        """Extract homepage URL from given URL"""
        try:
            parsed = urlparse(url)
            domain_parts = parsed.netloc.split('.')
            if len(domain_parts) >= 2:
                main_domain = '.'.join(domain_parts[-2:])
            else:
                main_domain = parsed.netloc
            return f"{parsed.scheme}://{main_domain}/"
        except Exception:
            return url

    async def extract_page_data(self, url: str) -> Dict[str, Any]:
        """Main extraction method with enhanced error handling"""
        start_time = datetime.now()
        result = {
            'original_url': url,
            'home_url': None,
            'page_data': {
                'url': url,
                'status_code': None,
                'error': None,
                'body': None,
                'text': None,
                'success': False
            },
            'home_data': {
                'url': None,
                'status_code': None,
                'error': None,
                'body': None,
                'text': None,
                'success': False,
                'links': {
                    'internal': [],
                    'external': []
                }
            },
            'timing': {
                'processing_time_seconds': None,
                'timestamp': datetime.now().isoformat()
            }
        }

        try:
            # Process original URL
            html, status, error = await self.fetch_with_retry(url)
            result['page_data']['status_code'] = status
            result['page_data']['error'] = error

            if html:
                body_html, text, _ = self.extract_body_and_text(html, url)
                result['page_data'].update({
                    'body': body_html,
                    'text': text,
                    'success': True
                })
        except Exception as e:
            result['page_data']['error'] = str(e)

        # Always process home page
        try:
            home_url = self.extract_home(url)
            result['home_url'] = home_url
            result['home_data']['url'] = home_url

            html_home, home_status, home_error = await self.fetch_with_retry(home_url)
            result['home_data']['status_code'] = home_status
            result['home_data']['error'] = home_error

            if html_home:
                body_home_html, text_home, soup_home = self.extract_body_and_text(html_home, home_url)
                list_url_in, list_url_out = self.extract_links(soup_home, home_url)

                result['home_data'].update({
                    'body': body_home_html,
                    'text': text_home,
                    'links': {
                        'internal': list_url_in,
                        'external': list_url_out
                    },
                    'success': True
                })
        except Exception as e:
            result['home_data']['error'] = str(e)

        result['timing']['processing_time_seconds'] = (datetime.now() - start_time).total_seconds()
        return result