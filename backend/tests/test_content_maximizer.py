import os
import sys
import unittest
import json
from unittest.mock import MagicMock

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_processor import GeminiContentProcessor, create_processor


class _DummyResponse:
    def __init__(self, text):
        self.text = text


class TestContentProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = GeminiContentProcessor(api_key="test_key")

    def test_test_key_initialization_sets_safe_defaults(self):
        self.assertIsNone(self.processor.client)

    def test_generate_blog_post_without_client_fails_gracefully(self):
        result = self.processor.generate_blog_post("hello world", language="en")
        self.assertFalse(result["success"])
        self.assertIn("not initialized", result["error"].lower())

    def test_strip_markdown_json_fence(self):
        text = "```json\n{\"key\": \"value\"}\n```"
        cleaned = GeminiContentProcessor._strip_markdown_json_fence(text)
        self.assertEqual(cleaned, "{\"key\": \"value\"}")

        text = "```\n[1, 2]\n```"
        cleaned = GeminiContentProcessor._strip_markdown_json_fence(text)
        self.assertEqual(cleaned, "[1, 2]")

        text = "  {\"a\": 1}  "
        cleaned = GeminiContentProcessor._strip_markdown_json_fence(text)
        self.assertEqual(cleaned, "{\"a\": 1}")

    def test_analyze_transcript_respects_language_and_model(self):
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = _DummyResponse("[]")
        self.processor.client = fake_client

        result = self.processor.analyze_transcript(
            "sample transcript",
            [],
            language="en",
            model_name="gemini-3.5-flash"
        )

        self.assertTrue(result["success"])
        call_kwargs = fake_client.models.generate_content.call_args.kwargs
        self.assertEqual(call_kwargs["model"], "gemini-3.5-flash")
        self.assertIn("English", call_kwargs["contents"])
        self.assertNotIn("Analyze this Polish video transcript", call_kwargs["contents"])
        self.assertIn("ALL text fields MUST be written in English", call_kwargs["contents"])
        self.assertIn("exactly 18", call_kwargs["contents"])

    def test_analyze_transcript_prompt_enforces_polish_fields(self):
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = _DummyResponse("[]")
        self.processor.client = fake_client

        result = self.processor.analyze_transcript(
            "sample transcript",
            [],
            language="pl",
            model_name="gemini-3.5-flash"
        )

        self.assertTrue(result["success"])
        prompt = fake_client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("ALL text fields MUST be written in Polish", prompt)
        self.assertIn("content.yt_shorts.title", prompt)
        self.assertIn("content.twitter.tweet", prompt)

    def test_analyze_transcript_clamps_out_of_bounds_and_returns_six_clips(self):
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = _DummyResponse(
            '[{"title":"X","category":"Full Segments","start_time":1236,"end_time":1430,"viral_score":9,"best_platform":"X/Twitter","content":{"yt_shorts":{"title":"X","description":"Y"}}}]'
        )
        self.processor.client = fake_client

        segments = [
            {"start": 0, "duration": 10, "text": "a"},
            {"start": 1190, "duration": 10, "text": "b"},
        ]
        result = self.processor.analyze_transcript("sample transcript", segments, language="pl")

        self.assertTrue(result["success"])
        clips = result["clips"]
        self.assertEqual(len(clips), 6)
        self.assertEqual(clips[0]["category"], "Micro Hooks")
        self.assertEqual(clips[3]["category"], "Golden Nuggets")
        self.assertEqual(clips[-1]["category"], "Full Segments")
        for clip in clips:
            self.assertGreaterEqual(clip["start_time"], 0)
            self.assertLessEqual(clip["end_time"], 1200)
            self.assertGreater(clip["end_time"], clip["start_time"])

    def test_analyze_transcript_selects_best_candidate_per_category(self):
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = _DummyResponse(
            json.dumps([
                {
                    "title": "Micro edge",
                    "category": "Micro Hooks",
                    "start_time": 0,
                    "end_time": 15,
                    "viral_score": 6,
                    "content": {"yt_shorts": {"title": "A", "description": "B"}},
                },
                {
                    "title": "Micro center",
                    "category": "Micro Hooks",
                    "start_time": 10,
                    "end_time": 32.5,
                    "viral_score": 6,
                    "content": {"yt_shorts": {"title": "A", "description": "B"}},
                },
                {
                    "title": "Viral edge",
                    "category": "Viral Shorts",
                    "start_time": 50,
                    "end_time": 110,
                    "viral_score": 7,
                    "content": {"yt_shorts": {"title": "A", "description": "B"}},
                },
                {
                    "title": "Viral center",
                    "category": "Viral Shorts",
                    "start_time": 120,
                    "end_time": 187.5,
                    "viral_score": 7,
                    "content": {"yt_shorts": {"title": "A", "description": "B"}},
                },
                {
                    "title": "Extended center",
                    "category": "Extended Shorts",
                    "start_time": 200,
                    "end_time": 315,
                    "viral_score": 7,
                    "content": {"yt_shorts": {"title": "A", "description": "B"}},
                },
                {
                    "title": "Golden center",
                    "category": "Golden Nuggets",
                    "start_time": 320,
                    "end_time": 530,
                    "viral_score": 7,
                    "content": {"yt_shorts": {"title": "A", "description": "B"}},
                },
                {
                    "title": "Deep center",
                    "category": "Deep Dives",
                    "start_time": 540,
                    "end_time": 869.5,
                    "viral_score": 7,
                    "content": {"yt_shorts": {"title": "A", "description": "B"}},
                },
                {
                    "title": "Full center",
                    "category": "Full Segments",
                    "start_time": 100,
                    "end_time": 729.5,
                    "viral_score": 7,
                    "content": {"yt_shorts": {"title": "A", "description": "B"}},
                },
            ])
        )
        self.processor.client = fake_client

        segments = [
            {"start": 0, "duration": 10, "text": "a"},
            {"start": 1500, "duration": 10, "text": "b"},
        ]
        result = self.processor.analyze_transcript("sample transcript", segments, language="en")

        self.assertTrue(result["success"])
        clips = result["clips"]
        self.assertEqual(len(clips), 6)
        micro = next(c for c in clips if c["category"] == "Micro Hooks")
        viral = next(c for c in clips if c["category"] == "Viral Shorts")
        self.assertEqual(micro["title"], "Micro center")
        self.assertEqual(viral["title"], "Viral center")
        self.assertGreaterEqual(micro["candidate_count"], 2)
        self.assertIn("is_best_clip", micro)

    def test_analyze_transcript_long_video_prompt_uses_600_to_659_range(self):
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = _DummyResponse("[]")
        self.processor.client = fake_client

        long_segments = [
            {"start": 0, "duration": 10, "text": "a"},
            {"start": 1300, "duration": 10, "text": "b"},
        ]
        result = self.processor.analyze_transcript("sample transcript", long_segments, language="en")

        self.assertTrue(result["success"])
        prompt = fake_client.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("Full Segments (600-659s)", prompt)

    def test_analyze_transcript_json_decode_failure_returns_raw(self):
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = _DummyResponse("not-json")
        self.processor.client = fake_client

        result = self.processor.analyze_transcript("sample transcript", [], language="en")
        self.assertFalse(result["success"])
        self.assertIn("Failed to parse AI response", result["error"])
        self.assertEqual(result["raw"], "not-json")

    def test_generate_blog_post_repairs_newlines_in_json_strings(self):
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = _DummyResponse(
            '```json\n{"title":"T","meta_description":"M","intro":"Line 1\nLine 2","sections":[{"title":"S","content":"C"}],"keywords":["k"]}\n```'
        )
        self.processor.client = fake_client

        result = self.processor.generate_blog_post("sample transcript", language="en")
        self.assertTrue(result["success"])
        self.assertEqual(result["blog"]["title"], "T")
        self.assertIn("Line 1", result["blog"]["intro"])

    def test_generate_blog_post_repairs_truncated_json(self):
        fake_client = MagicMock()
        fake_client.models.generate_content.return_value = _DummyResponse(
            '{"title":"T","meta_description":"M","intro":"I","sections":[{"title":"S","content":"C"}],"keywords":["k"]'
        )
        self.processor.client = fake_client

        result = self.processor.generate_blog_post("sample transcript", language="en")
        self.assertTrue(result["success"])
        self.assertEqual(result["blog"]["keywords"], ["k"])

    def test_generate_blog_post_uses_model_repair_fallback(self):
        fake_client = MagicMock()
        fake_client.models.generate_content.side_effect = [
            _DummyResponse("not json"),
            _DummyResponse('{"title":"T","meta_description":"M","intro":"I","sections":[],"keywords":["k"]}')
        ]
        self.processor.client = fake_client

        result = self.processor.generate_blog_post("sample transcript", language="en")
        self.assertTrue(result["success"])
        self.assertEqual(result["blog"]["title"], "T")
        self.assertEqual(fake_client.models.generate_content.call_count, 2)

    def test_process_full_content_marks_errors(self):
        self.processor.analyze_transcript = MagicMock(return_value={
            "success": False,
            "error": "clips failed"
        })
        self.processor.generate_blog_post = MagicMock(return_value={
            "success": True,
            "blog": {"title": "Blog Title"}
        })
        self.processor.generate_social_posts = MagicMock(return_value={
            "success": False,
            "error": "social failed"
        })

        result = self.processor.process_full_content("text", [], language="en", model_name="gemini-3.5-flash")
        self.assertFalse(result["success"])
        self.assertEqual(result["clips"], [])
        self.assertEqual(result["blog"]["title"], "Blog Title")
        self.assertIsNone(result["social"])
        self.assertEqual(len(result["errors"]), 2)

    def test_create_processor_uses_env_key(self):
        original_env = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "test_key"
        try:
            processor = create_processor()
            self.assertIsInstance(processor, GeminiContentProcessor)
            self.assertIsNone(processor.client)
        finally:
            if original_env is None:
                del os.environ["GEMINI_API_KEY"]
            else:
                os.environ["GEMINI_API_KEY"] = original_env


if __name__ == "__main__":
    unittest.main()
