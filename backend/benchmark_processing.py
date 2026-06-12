
import os
import json
import time
import sys
from dotenv import load_dotenv

# Add current directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from content_processor import create_processor

# Load environment variables
load_dotenv()

def run_benchmark():
    print("="*60)
    print("BACKEND PROCESSING BENCHMARK")
    print("="*60)

    # 1. Load Test Data
    transcript_file = os.path.join(os.path.dirname(__file__), 'data', 'transcripts', 'lsuOUJQ-0iQ.json')
    if not os.path.exists(transcript_file):
        print(f"Test file not found: {transcript_file}")
        # Try to find any json file in data/transcripts
        data_dir = os.path.join(os.path.dirname(__file__), 'data', 'transcripts')
        files = [f for f in os.listdir(data_dir) if f.endswith('.json')]
        if files:
            transcript_file = os.path.join(data_dir, files[0])
            print(f"Using alternative file: {transcript_file}")
        else:
            print("No transcript files found. Please fetch a transcript first.")
            return

    try:
        with open(transcript_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle different formats (some save as {transcript: ...}, some as raw list)
            if 'transcript' in data:
                transcript = data['transcript']
                segments = data.get('segments', []) or data.get('raw_data', [])
            else:
                transcript = data.get('transcript', '')
                segments = data.get('raw_data', [])
                
            if not transcript:
                print("No transcript text found in file.")
                return
                
            print(f"Loaded transcript: {len(transcript)} chars")
            print(f"   Segments: {len(segments)}")
            
    except Exception as e:
        print(f"Error loading file: {e}")
        return

    # 2. Initialize Processor
    try:
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            print("GEMINI_API_KEY not found in environment")
            return
            
        print(f"API Key found: {api_key[:5]}...{api_key[-5:]}")
        processor = create_processor(api_key)
        print("Processor initialized")
    except Exception as e:
        print(f"Error initializing processor: {e}")
        return

    print("\n" + "-"*60)
    print("STARTING TIMING TESTS")
    print("-" * 60)

    results = {}

    # 3. Test Clips Generation
    print("\n[1/3] Testing Clip Generation...")
    start_time = time.time()
    try:
        clips_result = processor.analyze_transcript(transcript, segments)
        duration = time.time() - start_time
        results['clips'] = duration
        
        if clips_result['success']:
            print(f"   Success! Generated {len(clips_result.get('clips', []))} clips")
            print(f"   Time: {duration:.2f} seconds")
        else:
            print(f"   Failed: {clips_result.get('error')}")
            print(f"   Time: {duration:.2f} seconds (Failed run)")
            
    except Exception as e:
        print(f"   Exception: {e}")
        results['clips'] = time.time() - start_time

    # 4. Test Blog Generation
    print("\n[2/3] Testing Blog Generation...")
    start_time = time.time()
    try:
        blog_result = processor.generate_blog_post(transcript, 'pl')
        duration = time.time() - start_time
        results['blog'] = duration
        
        if blog_result['success']:
            print(f"   Success! Generated blog post")
            print(f"   Time: {duration:.2f} seconds")
        else:
            print(f"   Failed: {blog_result.get('error')}")
    except Exception as e:
        print(f"   Exception: {e}")
        results['blog'] = time.time() - start_time

    # 5. Test Social Generation
    print("\n[3/3] Testing Social Posts Generation...")
    start_time = time.time()
    try:
        social_result = processor.generate_social_posts(transcript, 'pl')
        duration = time.time() - start_time
        results['social'] = duration
        
        if social_result['success']:
            print(f"   Success! Generated social posts")
            print(f"   Time: {duration:.2f} seconds")
        else:
            print(f"   Failed: {social_result.get('error')}")
    except Exception as e:
        print(f"   Exception: {e}")
        results['social'] = time.time() - start_time

    # Summary
    print("\n" + "="*60)
    print("BENCHMARK RESULTS")
    print("="*60)
    total_time = sum(results.values())
    
    print(f"Clips:  {results.get('clips', 0):.2f}s  ({(results.get('clips', 0)/total_time)*100:.1f}%)")
    print(f"Blog:   {results.get('blog', 0):.2f}s   ({(results.get('blog', 0)/total_time)*100:.1f}%)")
    print(f"Social: {results.get('social', 0):.2f}s ({(results.get('social', 0)/total_time)*100:.1f}%)")
    print("-" * 60)
    print(f"TOTAL:  {total_time:.2f}s")
    print("="*60)
    
    # Recommendation for Progress Bar
    print("\n💡 RECOMMENDED PROGRESS STEPS:")
    print(f"1. Clips:  0% -> {int((results.get('clips', 0)/total_time)*100)}% (Est. {int(results.get('clips', 0))}s)")
    print(f"2. Blog:   -> {int(((results.get('clips', 0) + results.get('blog', 0))/total_time)*100)}% (Est. {int(results.get('blog', 0))}s)")
    print(f"3. Social: -> 100% (Est. {int(results.get('social', 0))}s)")

if __name__ == "__main__":
    run_benchmark()
