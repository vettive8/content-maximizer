import json
import unittest
import sys
import os
from unittest.mock import MagicMock

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from business_growth_strategy_processor import BusinessGrowthStrategyProcessor

class TestBusinessGrowthStrategyProcessor(unittest.TestCase):
    def setUp(self):
        # We don't need a real API key for testing _extract_json
        self.processor = BusinessGrowthStrategyProcessor(api_key="test_key")

    def test_extract_json_valid(self):
        """Test extraction from a standard markdown code block."""
        text = 'Here is the data: ```json\n{"key": "value"}\n``` Hope it helps!'
        result = self.processor._extract_json(text)
        self.assertEqual(result, {"key": "value"})

    def test_extract_json_no_blocks(self):
        """Test extraction when there are no markdown blocks."""
        text = '{"key": "value"}'
        result = self.processor._extract_json(text)
        self.assertEqual(result, {"key": "value"})

    def test_extract_json_early_closure(self):
        """Test healing of the specific early closure bug."""
        text = '{"positioning_statement": "Strategic promise"}\n},\n"market_trends": {"trend": "AI"}}'
        result = self.processor._extract_json(text)
        self.assertEqual(result["positioning_statement"], "Strategic promise")
        self.assertEqual(result["market_trends"]["trend"], "AI")

    def test_extract_json_control_characters(self):
        """Test escaping of control characters inside strings."""
        # \x03 is a control character that crashes raw JSON parsers
        text = '{"key": "Value with \x03 control char"}'
        result = self.processor._extract_json(text)
        # It should be escaped to \u0003 during healing
        self.assertEqual(result["key"], "Value with \u0003 control char")

    def test_extract_json_complex_healing(self):
        """Test combination of unescaped newlines and early closure."""
        text = """{
            "positioning_statement": "Line 1
            Line 2"
        },
        "market_trends": {
            "name": "Market"
        }"""
        result = self.processor._extract_json(text + "\n}")
        self.assertIn("Line 1", result["positioning_statement"])
        self.assertEqual(result["market_trends"]["name"], "Market")

    def test_extract_json_truncated(self):
        """Test healing of truncated JSON (missing closing braces)."""
        # Missing final brace
        truncated_json = '{"key": "value", "list": [1, 2]'
        result = self.processor._extract_json(truncated_json)
        self.assertTrue(result)
        self.assertEqual(result.get('key'), 'value')
        self.assertEqual(result.get('list'), [1, 2])
        
        # Missing multiple braces/brackets
        truncated_deep = '{"level1": {"level2": [1, 2'
        result = self.processor._extract_json(truncated_deep)
        self.assertTrue(result)
        self.assertEqual(result['level1']['level2'], [1, 2])

    def test_extract_json_malformed_phrases_list_items(self):
        """Test healing of malformed string items in arrays."""
        text = """{
            "tone_and_style": {
                "phrases_to_avoid": [
                    "Rynek jest trudny/ciezki\\\\" (bez natychmiastowego korygowania),
                    "Klienci wolniej podejmuja decyzje" (bez natychmiastowego korygowania),
                    "Po prostu domknij sprzedaz" (sugeruje brak procesu)
                ]
            }
        }"""
        result = self.processor._extract_json(text)
        self.assertIn("tone_and_style", result)
        phrases = result["tone_and_style"]["phrases_to_avoid"]
        self.assertEqual(len(phrases), 3)
        self.assertIn("bez natychmiastowego korygowania", phrases[0])
        self.assertIn("sugeruje brak procesu", phrases[2])

    def test_generate_similar_title_wraps_dict_result(self):
        """Ensure generate_similar_title always returns a list."""
        self.processor.client = MagicMock()
        self.processor.client.models.generate_content.return_value = MagicMock(text="{}")
        self.processor._extract_json = MagicMock(return_value={"title": "Sample"})

        result = self.processor.generate_similar_title("Original", {}, language="en", count=1)
        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["title"], "Sample")

    def test_generate_market_research_prompt_uses_requested_language(self):
        self.processor.client = MagicMock()
        self.processor.client.models.generate_content.return_value = MagicMock(text="{}")

        self.processor.generate_market_research(
            website_content="site",
            sales_transcripts="sales",
            cm_transcripts="cm",
            manual_context="ctx",
            language="en",
        )

        prompt = self.processor.client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("written in English", prompt)

    def test_generate_market_research_prompt_normalizes_invalid_language_to_polish(self):
        self.processor.client = MagicMock()
        self.processor.client.models.generate_content.return_value = MagicMock(text="{}")

        self.processor.generate_market_research(
            website_content="site",
            sales_transcripts="sales",
            cm_transcripts="cm",
            manual_context="ctx",
            language="de",
        )

        prompt = self.processor.client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("written in Polish", prompt)

    def test_generate_psychoanalysis_prompt_uses_requested_language(self):
        self.processor.client = MagicMock()
        self.processor.client.models.generate_content.return_value = MagicMock(text="{}")

        self.processor.generate_psychoanalysis(
            sales_transcripts="enough transcript text " * 20,
            language="en",
        )

        prompt = self.processor.client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("written in English", prompt)

    def test_generate_creative_brief_prompt_uses_requested_language(self):
        self.processor.client = MagicMock()
        self.processor.client.models.generate_content.return_value = MagicMock(text="{}")

        self.processor.generate_creative_brief(
            market_research={},
            psychoanalysis={},
            website_content="site",
            manual_context="ctx",
            language="en",
        )

        prompt = self.processor.client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("written in English", prompt)

    def test_generate_script_chapter_prompt_enforces_continuous_script(self):
        self.processor.client = MagicMock()
        self.processor.client.models.generate_content.return_value = MagicMock(text='{"option_a":{"script":"A"},"option_b":{"script":"B"}}')

        self.processor.generate_script_chapter(
            title="Test Title",
            chapter={
                "number": 2,
                "title": "Wycena i decyzja",
                "duration_minutes": 3,
                "purpose": "Purpose",
                "key_points": ["k1", "k2"]
            },
            context_data={"market_research": {}},
            language="pl",
            previous_chapter_script="Poprzedni tekst"
        )

        prompt = self.processor.client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("one cohesive long YouTube script", prompt)
        self.assertIn('Never open with recap/meta phrases', prompt)
        self.assertIn('Do NOT mention chapter numbers, chapter names, episode labels, or "this chapter"', prompt)

    def test_generate_script_chapter_strips_recap_openers(self):
        self.processor.client = MagicMock()
        self.processor.client.models.generate_content.return_value = MagicMock(text="{}")
        self.processor._extract_json = MagicMock(return_value={
            "chapter_number": 2,
            "chapter_title": "Test",
            "option_a": {
                "style": "Direct/Educational",
                "script": "W poprzednim rozdziale omówiliśmy problem. Teraz pokażę, jak go wycenić.",
                "word_count": 12
            },
            "option_b": {
                "style": "Storytelling/Emotional",
                "script": "In previous chapter we covered the basics. Now let's quantify the cost of delay.",
                "word_count": 13
            }
        })

        result = self.processor.generate_script_chapter(
            title="Test Title",
            chapter={
                "number": 2,
                "title": "Wycena i decyzja",
                "duration_minutes": 3,
                "purpose": "Purpose",
                "key_points": ["k1", "k2"]
            },
            context_data={"market_research": {}},
            language="pl",
        )

        self.assertNotIn("w poprzednim rozdziale", result["option_a"]["script"].lower())
        self.assertNotIn("in previous chapter", result["option_b"]["script"].lower())
        self.assertTrue(result["option_a"]["script"].startswith("Teraz"))
        self.assertTrue(result["option_b"]["script"].startswith("Now"))

if __name__ == '__main__':
    unittest.main()
