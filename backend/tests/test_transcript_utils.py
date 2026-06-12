import os
import sys
import unittest

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transcript_fetcher import extract_video_id, seconds_to_timestamp


class TestTranscriptUtils(unittest.TestCase):
    def test_extract_video_id_from_common_formats(self):
        self.assertEqual(extract_video_id("https://www.youtube.com/watch?v=46dhfNne8fI"), "46dhfNne8fI")
        self.assertEqual(extract_video_id("https://youtu.be/46dhfNne8fI?t=5"), "46dhfNne8fI")
        self.assertEqual(extract_video_id("https://youtube.com/embed/46dhfNne8fI"), "46dhfNne8fI")
        self.assertEqual(extract_video_id("46dhfNne8fI"), "46dhfNne8fI")

    def test_extract_video_id_invalid(self):
        self.assertIsNone(extract_video_id("https://example.com/video"))
        self.assertIsNone(extract_video_id("not-a-video-id"))
        self.assertIsNone(extract_video_id(""))

    def test_seconds_to_timestamp(self):
        self.assertEqual(seconds_to_timestamp(5), "00:05")
        self.assertEqual(seconds_to_timestamp(65), "01:05")
        self.assertEqual(seconds_to_timestamp(3661), "1:01:01")


if __name__ == "__main__":
    unittest.main()
