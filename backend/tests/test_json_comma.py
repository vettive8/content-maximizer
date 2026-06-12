import unittest
import sys
import os

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_growth_strategy_processor import BusinessGrowthStrategyProcessor

class TestBusinessGrowthStrategyProcessorMissingComma(unittest.TestCase):
    def setUp(self):
        self.processor = BusinessGrowthStrategyProcessor(api_key="test_key")

    def test_extract_json_orphan_video_ideas(self):
        """Test healing of orphan video idea objects (missing key)."""
        # Simulating the structure: Valid object, then orphan objects { "title": ... }
        text = """
        {
            "problem": { "core": "issue" },
            {
                "title": "Video 1"
            },
            {
                "title": "Video 2"
            }
        }
        """
        # This is invalid because { "title": ... } has no key in the root object.
        # We expect the processor to wrap these in "video_ideas": [ ... ]
        
        result = self.processor._extract_json(text)
        self.assertIn("video_ideas", result)
        self.assertEqual(len(result["video_ideas"]), 2)
        self.assertEqual(result["video_ideas"][0]["title"], "Video 1")

if __name__ == '__main__':
    unittest.main()
