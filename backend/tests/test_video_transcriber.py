import os
import sys
import unittest


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from video_transcriber import _is_low_quality_transcript, _segments_from_payload


class TestVideoTranscriberQuality(unittest.TestCase):
    def test_segments_from_payload_uses_transcript_lines(self):
        payload = {
            "language": "en",
            "transcript": "[00:03] Hello world\n[00:07] This is a test",
        }
        segments, detected_language = _segments_from_payload(payload, "pl", "")
        self.assertEqual(detected_language, "en")
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["start"], 3.0)
        self.assertEqual(segments[0]["text"], "Hello world")

    def test_low_quality_detects_timestamp_only_output(self):
        segments = []
        for idx in range(30):
            seconds = idx
            mm = seconds // 60
            ss = seconds % 60
            segments.append(
                {
                    "start": float(idx),
                    "duration": 0.66,
                    "text": f"{mm:02d}:{ss:02d}",
                }
            )
        self.assertTrue(_is_low_quality_transcript(segments))

    def test_low_quality_detects_jsonish_segments(self):
        segments = [
            {"start": 0.0, "duration": 2.5, "text": "{"},
            {"start": 2.5, "duration": 2.5, "text": '"language": "en",'},
            {"start": 5.0, "duration": 2.5, "text": '"segments": ['},
            {"start": 7.5, "duration": 2.5, "text": '{"start": 0.0, "end": 0.5, "text": "00:00"},'},
        ] * 8
        self.assertTrue(_is_low_quality_transcript(segments))

    def test_low_quality_allows_readable_transcript(self):
        segments = [
            {"start": 3.2, "duration": 6.2, "text": "All right. Welcome to the blueprint."},
            {"start": 9.4, "duration": 8.1, "text": "Today we will cover the full roadmap for scaling."},
            {"start": 17.5, "duration": 7.5, "text": "First we focus on getting clients consistently."},
            {"start": 25.0, "duration": 7.2, "text": "Then we improve retention with clear systems."},
            {"start": 32.2, "duration": 8.0, "text": "This process helps you grow without burning out."},
        ]
        self.assertFalse(_is_low_quality_transcript(segments))


if __name__ == "__main__":
    unittest.main()
