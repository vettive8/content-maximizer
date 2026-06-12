
import os
import sys
import time
from website_scraper import scrape_website_text
from transcript_fetcher import fetch_transcript
from business_growth_strategy_processor import BusinessGrowthStrategyProcessor

def test_scraper():
    print("\n=== Testing Website Scraper ===")
    url = "https://sellwise.pl"
    start = time.time()
    try:
        text = scrape_website_text(url)
        print(f"Scraped {len(text)} chars in {time.time() - start:.2f}s")
        if text:
            print(f"Sample: {text[:200]}...")
        else:
            print("Failed to scrape text (empty result).")
    except Exception as e:
        print(f"Scraper Error: {e}")

def test_youtube():
    print("\n=== Testing YouTube Transcript ===")
    url = "https://www.youtube.com/watch?v=lsuOUJQ-0iQ"
    start = time.time()
    try:
        result = fetch_transcript(url)
        print(f"Fetch result: {result['success']} in {time.time() - start:.2f}s")
        if result['success']:
            print(f"Transcript length: {len(result['transcript'])}")
        else:
            print(f"Error: {result['error']}")
    except Exception as e:
        print(f"YouTube Error: {e}")

def check_docs():
    print("\n=== Checking Docs Transcripts ===")
    docs_dir = os.path.join(os.path.dirname(__file__), 'docs')
    files = ["Marcin and Szymon.txt", "Piotr and Szymon.txt", "Tomasz and Szymon.txt"]
    for f in files:
        path = os.path.join(docs_dir, f)
        exists = os.path.exists(path)
        print(f"{f}: {'EXISTS' if exists else 'MISSING'}")
        if exists:
            size = os.path.getsize(path)
            print(f"  Size: {size} bytes")

def test_processor_init():
    print("\n=== Testing BusinessGrowthStrategyProcessor Init ===")
    try:
        # Use test_key to avoid actual API call but test import/init
        p = BusinessGrowthStrategyProcessor("test_key")
        print("Successfully initialized BusinessGrowthStrategyProcessor with test_key")
    except Exception as e:
        print(f"Processor Init Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_processor_init()
    check_docs()
    test_scraper()
    test_youtube()
