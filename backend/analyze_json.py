
import json
import re

def analyze_json_error():
    try:
        with open('debug_json_failure.txt', 'r', encoding='utf-8') as f:
            content = f.read().split('-'*50 + '\n')[1]
        
        print(f"Total length: {len(content)}")
        print(f"Last 100 chars: {repr(content[-100:])}")
        
        # Count braces
        open_braces = content.count('{')
        close_braces = content.count('}')
        open_brackets = content.count('[')
        close_brackets = content.count(']')
        
        print(f"Braces: {open_braces} open, {close_braces} close")
        print(f"Brackets: {open_brackets} open, {close_brackets} close")
        
        # Try to find the error position manually
        # The error says char 32052, which is len(content)
        # It expects a comma. This usually happens if we have "key": "value" "key2": ... (missing comma)
        # OR inside a list: ["item" "item"]
        # OR if the json is `{"a": 1} {` (extra data)
        
        try:
            json.loads(content)
            print("JSON valid!")
        except json.JSONDecodeError as e:
            print(f"JSON Error: {e}")
            print(f"Error at char: {e.pos}")
            start = max(0, e.pos - 50)
            end = min(len(content), e.pos + 50)
            print(f"Context: {content[start:end]}")
            
    except Exception as e:
        print(f"Script Error: {e}")

if __name__ == "__main__":
    analyze_json_error()
