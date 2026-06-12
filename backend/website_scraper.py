import requests
from bs4 import BeautifulSoup
import re

def scrape_website_text(url):
    """
    Scrapes visible text content from a given URL.
    Returns a cleaned string of text or empty string on failure.
    """
    if not url:
        print("[SCRAPER] No URL provided")
        return ""
    
    # Normalize URL
    url = url.strip()
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url
    
    print(f"[SCRAPER] Scraping: {url}")
    
    try:
        # Add headers to mimic a browser and avoid some bot blocks
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }
        
        response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        response.raise_for_status()
        
        print(f"[SCRAPER] Status: {response.status_code}, Content-Type: {response.headers.get('content-type', 'unknown')}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script, style, nav, footer, header elements
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'noscript']):
            element.decompose()
        
        # Try to get main content areas first
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|body', re.I))
        
        if main_content:
            text = main_content.get_text()
        else:
            text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Limit length
        result = text[:15000]
        print(f"[SCRAPER] Successfully scraped {len(result)} characters")
        return result
        
    except requests.exceptions.SSLError:
        # Try without SSL verification or with http
        print(f"[SCRAPER] SSL error, trying http://{url.replace('https://', '')}")
        try:
            http_url = url.replace('https://', 'http://')
            response = requests.get(http_url, headers=headers, timeout=15, allow_redirects=True)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            for element in soup(['script', 'style', 'nav', 'footer']):
                element.decompose()
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            return text[:15000]
        except Exception as e2:
            print(f"[SCRAPER] HTTP fallback also failed: {e2}")
            return ""
            
    except Exception as e:
        print(f"[SCRAPER] Error scraping {url}: {e}")
        return ""
