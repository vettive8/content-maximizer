from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get('GEMINI_API_KEY')
print(f"API Key found: {bool(api_key)}")

if api_key:
    client = genai.Client(api_key=api_key)
    
    try:
        print("\nTesting generation with gemini-3.1-flash-lite-preview...")
        response_lite = client.models.generate_content(
            model='gemini-3.1-flash-lite-preview',
            contents="Hello, are you Gemini 3.1 Flash-Lite?"
        )
        print(f"Response 3.1 Flash-Lite: {response_lite.text}")

        print("\nTesting generation with gemini-3.1-pro-preview...")
        response_pro = client.models.generate_content(
            model='gemini-3.1-pro-preview',
            contents="Hello, are you Gemini 3.1 Pro?"
        )
        print(f"Response 3.1 Pro: {response_pro.text}")
        
    except Exception as e:
        print(f"\nError: {e}")
