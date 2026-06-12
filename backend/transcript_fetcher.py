"""
Content Maximizer Backend - Transcript Fetcher
Fetches timestamped transcripts from YouTube videos with clickable links.
Compatible with youtube-transcript-api v1.2+
"""

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import re
import json
from typing import Optional
import sys


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'  # Direct video ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def seconds_to_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS or HH:MM:SS format."""
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_transcript_line(video_id: str, start: float, text: str) -> str:
    """Format a single transcript line with timestamp and clickable link."""
    timestamp = seconds_to_timestamp(start)
    seconds = int(start)
    link = f"https://youtu.be/{video_id}?t={seconds}"
    return f"[{timestamp}]({link}) {text}"


def fetch_transcript(video_url: str, language: str = 'pl') -> dict:
    """
    Fetch transcript from YouTube video.
    
    Args:
        video_url: YouTube URL or video ID
        language: Language code (default 'pl' for Polish, 'en' for English)
    
    Returns:
        dict with 'success', 'transcript', 'raw_data', 'video_id', 'language'
    """
    video_id = extract_video_id(video_url)
    
    if not video_id:
        return {
            'success': False,
            'error': 'Invalid YouTube URL or video ID',
            'video_id': None
        }
    
    try:
        # v1.2+ API: instantiate then use .list() to get available transcripts
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        
        # Try to find transcript in requested language
        transcript = None
        actual_language = language
        is_generated = False
        
        # Build list of languages to try
        languages_to_try = [language]
        if language == 'pl':
            languages_to_try.extend(['en', 'en-US', 'en-GB'])
        else:
            languages_to_try.extend(['pl', 'en', 'en-US'])
        
        for lang in languages_to_try:
            try:
                transcript = transcript_list.find_transcript([lang])
                actual_language = lang
                is_generated = transcript.is_generated
                break
            except NoTranscriptFound:
                continue
        
        if not transcript:
            # Try to get any available transcript
            try:
                for t in transcript_list:
                    transcript = t
                    actual_language = t.language_code
                    is_generated = t.is_generated
                    break
            except:
                pass
        
        if not transcript:
            return {
                'success': False,
                'error': f'No transcript available for video {video_id}',
                'video_id': video_id
            }
        
        # Fetch the actual transcript data
        raw_data = transcript.fetch()
        
        # Format each line with timestamp and link
        # v1.2+ returns FetchedTranscriptSnippet objects with .text, .start, .duration attributes
        formatted_lines = []
        raw_data_dicts = []  # Store as dicts for JSON export
        for entry in raw_data:
            start = entry.start  # Attribute access, not dict
            text = entry.text.replace('\n', ' ').strip()
            raw_data_dicts.append({
                'start': entry.start,
                'duration': entry.duration,
                'text': entry.text
            })
            if text:  # Skip empty lines
                formatted_lines.append(format_transcript_line(video_id, start, text))
        
        formatted_transcript = '\n'.join(formatted_lines)
        
        return {
            'success': True,
            'transcript': formatted_transcript,
            'raw_data': raw_data_dicts,
            'video_id': video_id,
            'language': actual_language,
            'is_generated': is_generated,
            'line_count': len(formatted_lines)
        }
        
    except TranscriptsDisabled:
        return {
            'success': False,
            'error': 'Transcripts are disabled for this video',
            'video_id': video_id
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'video_id': video_id
        }


def main():
    """CLI entry point for testing."""
    if len(sys.argv) < 2:
        print("Usage: python transcript_fetcher.py <youtube_url> [language]")
        print("Example: python transcript_fetcher.py https://www.youtube.com/watch?v=46dhfNne8fI pl")
        sys.exit(1)
    
    video_url = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) > 2 else 'pl'
    
    print(f"Fetching transcript for: {video_url}")
    print(f"Language: {language}")
    print("-" * 50)
    
    result = fetch_transcript(video_url, language)
    
    if result['success']:
        print(f"[OK] Success! Video ID: {result['video_id']}")
        print(f"Language: {result['language']} ({'auto-generated' if result['is_generated'] else 'manual'})")
        print(f"Lines: {result['line_count']}")
        print("-" * 50)
        print("\nTRANSCRIPT:\n")
        print(result['transcript'])
        
        # Save to file
        output_file = f"transcript_{result['video_id']}.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result['transcript'])
        print(f"\nSaved to: {output_file}")
        
        # Also save raw JSON for debugging
        json_file = f"transcript_{result['video_id']}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                'video_id': result['video_id'],
                'language': result['language'],
                'is_generated': result['is_generated'],
                'raw_data': result['raw_data']
            }, f, ensure_ascii=False, indent=2)
        print(f"Raw data saved to: {json_file}")
    else:
        print(f"[ERROR] {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()
