
import json
import sys
import os

# Add parent directory to path so we can import backend modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from business_growth_strategy_processor import BusinessGrowthStrategyProcessor

def test_fix():
    print("--- Testing Real BusinessGrowthStrategyProcessor Fix ---")
    try:
        # Read the failure content
        with open('debug_json_failure.txt', 'r', encoding='utf-8') as f:
            content = f.read().split('-'*50 + '\n')[1]
            
        print(f"Content length: {len(content)}")
        
        # Instantiate processor (API key irrelevant for _extract_json)
        processor = BusinessGrowthStrategyProcessor("test_key")
        
        # Call _extract_json
        result = processor._extract_json(content)
        
        if result:
            print("SUCCESS! JSON parsed correctly.")
            print(f"Keys found: {list(result.keys())}")
            if "market_trends" in result:
                print("market_trends found.")
                if "threats" in result["market_trends"]:
                    print(f"threats count: {len(result['market_trends']['threats'])}")
        else:
            print("FAILURE: returned None")
            
    except Exception as e:
        print(f"TEST FAILED with error: {e}")

if __name__ == "__main__":
    test_fix()
