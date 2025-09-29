"""
DBLP Profile Scraper - Extract BibTeX data from DBLP profile URLs.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from typing import Optional, List, Dict, Tuple
import time
from pathlib import Path
import tempfile


class DBLPScraper:
    """Scraper for DBLP (Database Systems and Logic Programming) profiles."""
    
    def __init__(self, delay: float = 1.0):
        """Initialize DBLP scraper.
        
        Args:
            delay: Delay between requests to be respectful to DBLP servers
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (BibTeX-to-Manubot Converter; Academic Research Tool)'
        })
    
    def is_dblp_url(self, url: str) -> bool:
        """Check if URL is a valid DBLP profile URL.
        
        Args:
            url: URL to check
            
        Returns:
            True if valid DBLP profile URL
        """
        parsed = urlparse(url)
        return (parsed.netloc == 'dblp.org' or parsed.netloc == 'dblp.uni-trier.de') and '/pid/' in parsed.path
    
    def extract_pid_from_url(self, url: str) -> Optional[str]:
        """Extract person ID (PID) from DBLP profile URL.
        
        Args:
            url: DBLP profile URL
            
        Returns:
            Person ID or None if not found
        """
        # Match patterns like /pid/154/4313.html or /pid/154/4313
        match = re.search(r'/pid/([^/]+/[^/.]+)', url)
        return match.group(1) if match else None
    
    def get_bibtex_download_url(self, profile_url: str) -> Optional[str]:
        """Get BibTeX download URL from DBLP profile page.
        
        Args:
            profile_url: DBLP profile URL
            
        Returns:
            BibTeX download URL or None if not found
        """
        if not self.is_dblp_url(profile_url):
            raise ValueError(f"Invalid DBLP URL: {profile_url}")
        
        # Method 1: Construct BibTeX URL from PID (most reliable)
        pid = self.extract_pid_from_url(profile_url)
        if pid:
            # DBLP BibTeX format: https://dblp.org/pid/PID.bib
            return f"https://dblp.org/pid/{pid}.bib"
        
        # Method 2: Try to find BibTeX link on profile page
        try:
            response = self.session.get(profile_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for BibTeX download link
            for link in soup.find_all('a', href=True):
                href = link['href']
                link_text = link.get_text().lower()
                
                if 'bib' in href.lower() or 'bibtex' in link_text or 'view=bibtex' in href:
                    return urljoin(profile_url, href)
            
            # Method 3: Try adding view=bibtex parameter
            return f"{profile_url}?view=bibtex"
            
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to fetch DBLP profile: {e}")
        except Exception as e:
            raise RuntimeError(f"Error parsing DBLP profile: {e}")
    
    def download_bibtex(self, bibtex_url: str) -> str:
        """Download BibTeX content from DBLP.
        
        Args:
            bibtex_url: URL to BibTeX file
            
        Returns:
            BibTeX content as string
        """
        try:
            if self.delay > 0:
                time.sleep(self.delay)
            
            response = self.session.get(bibtex_url, timeout=30)
            response.raise_for_status()
            
            # Get content
            content = response.text.strip()
            if not content:
                raise ValueError("Downloaded content is empty")
            
            # Check if response contains BibTeX content
            # Look for @article, @inproceedings, etc. anywhere in content
            if not re.search(r'@\w+\s*\{', content):
                # If it's HTML, try to extract BibTeX from it
                if content.lower().startswith('<!doctype html') or content.lower().startswith('<html'):
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Look for BibTeX content in <pre> or <code> tags
                    for tag in soup.find_all(['pre', 'code']):
                        tag_content = tag.get_text().strip()
                        if re.search(r'@\w+\s*\{', tag_content):
                            content = tag_content
                            break
                    else:
                        raise ValueError("Downloaded HTML does not contain BibTeX content")
                else:
                    raise ValueError("Downloaded content does not appear to be BibTeX format")
            
            return content
            
        except requests.RequestException as e:
            raise ConnectionError(f"Failed to download BibTeX: {e}")
    
    def scrape_profile_to_bibtex(self, profile_url: str) -> str:
        """Scrape DBLP profile and return BibTeX content.
        
        Args:
            profile_url: DBLP profile URL (e.g., https://dblp.org/pid/154/4313.html)
            
        Returns:
            BibTeX content as string
        """
        print(f"Fetching DBLP profile: {profile_url}")
        
        # Get BibTeX download URL
        bibtex_url = self.get_bibtex_download_url(profile_url)
        if not bibtex_url:
            raise RuntimeError("Could not find BibTeX download link on DBLP profile")
        
        print(f"Downloading BibTeX from: {bibtex_url}")
        
        # Download BibTeX content
        bibtex_content = self.download_bibtex(bibtex_url)
        
        # Count entries for user feedback
        entry_count = len(re.findall(r'^@\w+\s*{', bibtex_content, re.MULTILINE))
        print(f"Downloaded {entry_count} BibTeX entries")
        
        return bibtex_content
    
    def scrape_profile_to_file(self, profile_url: str, output_path: Optional[str] = None) -> str:
        """Scrape DBLP profile and save BibTeX to file.
        
        Args:
            profile_url: DBLP profile URL
            output_path: Output file path (default: temporary file)
            
        Returns:
            Path to saved BibTeX file
        """
        bibtex_content = self.scrape_profile_to_bibtex(profile_url)
        
        # Create output file
        if output_path is None:
            # Create temporary file
            temp_dir = Path(tempfile.gettempdir())
            pid = self.extract_pid_from_url(profile_url)
            if pid:
                filename = f"dblp_{pid.replace('/', '_')}.bib"
            else:
                filename = "dblp_profile.bib"
            output_path = str(temp_dir / filename)
        
        # Write BibTeX content to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(bibtex_content)
        
        print(f"BibTeX saved to: {output_path}")
        return output_path
    
    def get_profile_info(self, profile_url: str) -> Dict[str, str]:
        """Extract basic profile information from DBLP page.
        
        Args:
            profile_url: DBLP profile URL
            
        Returns:
            Dictionary with profile information
        """
        try:
            response = self.session.get(profile_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            info = {
                'url': profile_url,
                'pid': self.extract_pid_from_url(profile_url),
                'name': '',
                'affiliations': [],
                'publication_count': 0
            }
            
            # Extract author name
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
                # DBLP titles are typically "Author Name - DBLP"
                if ' - ' in title:
                    info['name'] = title.split(' - ')[0].strip()
            
            # Count publications (approximate from @inproceedings, @article tags in page)
            pub_indicators = soup.find_all(string=re.compile(r'@(article|inproceedings|book)'))
            info['publication_count'] = len(pub_indicators)
            
            return info
            
        except Exception as e:
            return {
                'url': profile_url,
                'pid': self.extract_pid_from_url(profile_url),
                'name': 'Unknown',
                'affiliations': [],
                'publication_count': 0,
                'error': str(e)
            }


def validate_dblp_url(url: str) -> Tuple[bool, str]:
    """Validate and normalize DBLP profile URL.
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, normalized_url_or_error_message)
    """
    try:
        scraper = DBLPScraper()
        if not scraper.is_dblp_url(url):
            return False, "URL is not a valid DBLP profile URL. Expected format: https://dblp.org/pid/X/Y.html"
        
        # Normalize URL
        parsed = urlparse(url)
        if not parsed.scheme:
            url = f"https://{url}"
        
        # Ensure .html extension for profile URLs
        if '/pid/' in url and not url.endswith('.html') and not url.endswith('.bib'):
            if not re.search(r'/pid/[^/]+/[^/]+$', url):
                return False, "Invalid DBLP PID format"
            url = url + '.html'
        
        return True, url
        
    except Exception as e:
        return False, f"Error validating URL: {e}"


if __name__ == '__main__':
    # Example usage
    scraper = DBLPScraper()
    
    # Test URL
    test_url = "https://dblp.org/pid/154/4313.html"
    
    try:
        # Get profile info
        info = scraper.get_profile_info(test_url)
        print(f"Profile: {info}")
        
        # Download BibTeX
        bibtex_file = scraper.scrape_profile_to_file(test_url)
        print(f"BibTeX downloaded to: {bibtex_file}")
        
    except Exception as e:
        print(f"Error: {e}")