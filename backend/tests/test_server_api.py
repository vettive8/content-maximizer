import io
import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server
from server import app


class TestServerApi(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True
        self.original_max_content_length = app.config.get("MAX_CONTENT_LENGTH")
        with server._clip_download_lock:
            server._clip_download_jobs.clear()

    def tearDown(self):
        app.config["MAX_CONTENT_LENGTH"] = self.original_max_content_length

    def test_get_project_route_registered_once(self):
        matching_routes = [
            rule for rule in app.url_map.iter_rules()
            if rule.rule == "/api/get_project/<project_id>" and "GET" in rule.methods
        ]
        self.assertEqual(len(matching_routes), 1)

    def test_health_check(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("gemini", payload)

    def test_transcript_requires_url(self):
        response = self.client.post("/api/transcript", json={})
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])

    def test_process_requires_transcript(self):
        response = self.client.post("/api/process", json={})
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])

    def test_large_json_payload_returns_413(self):
        app.config["MAX_CONTENT_LENGTH"] = 128
        payload = json.dumps({"transcript": "x" * 512, "segments": []})

        response = self.client.post(
            "/api/process",
            data=payload,
            content_type="application/json"
        )

        self.assertEqual(response.status_code, 413)
        body = response.get_json()
        self.assertFalse(body["success"])
        self.assertIn("Request payload too large", body["error"])
        self.assertIn("128 bytes", body["error"])

    def test_large_upload_payload_returns_413(self):
        app.config["MAX_CONTENT_LENGTH"] = 256

        response = self.client.post(
            "/api/transcript/upload",
            data={
                "language": "en",
                "video": (io.BytesIO(b"x" * 1024), "large.mp4"),
            },
            content_type="multipart/form-data"
        )

        self.assertEqual(response.status_code, 413)
        body = response.get_json()
        self.assertFalse(body["success"])
        self.assertIn("Request payload too large", body["error"])

    @patch("server.save_project")
    def test_save_project_invalid_id_returns_400(self, mock_save_project):
        mock_save_project.side_effect = server.InvalidIdentifierError("Invalid project_id")

        response = self.client.post("/api/save_project", json={"id": "../outside", "title": "Unsafe"})

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"], "Invalid project_id")

    @patch("server.get_project_details")
    def test_get_project_invalid_id_returns_400(self, mock_get_project_details):
        mock_get_project_details.side_effect = server.InvalidIdentifierError("Invalid project_id")

        response = self.client.get("/api/get_project/bad$id")

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"], "Invalid project_id")

    @patch("server.delete_project")
    def test_delete_project_invalid_id_returns_400(self, mock_delete_project):
        mock_delete_project.side_effect = server.InvalidIdentifierError("Invalid project_id")

        response = self.client.post("/api/delete_project", json={"project_id": "../outside"})

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])
        self.assertEqual(payload["error"], "Invalid project_id")

    @patch("server.save_transcript_independently")
    @patch("server.fetch_transcript")
    def test_transcript_success_payload(self, mock_fetch, mock_save):
        mock_save.return_value = True
        mock_fetch.return_value = {
            "success": True,
            "video_id": "abc123def45",
            "language": "en",
            "is_generated": False,
            "line_count": 1,
            "transcript": "hello",
            "raw_data": [{"start": 0.0, "duration": 1.0, "text": "hello"}],
        }

        response = self.client.post("/api/transcript", json={"url": "https://youtu.be/abc123def45", "language": "en"})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["video_id"], "abc123def45")
        self.assertEqual(payload["language"], "en")
        mock_save.assert_called_once()

    @patch("server.get_processor")
    def test_process_uses_request_ai_config(self, mock_get_processor):
        processor = MagicMock()
        processor.analyze_transcript.return_value = {"success": True, "clips": []}
        mock_get_processor.return_value = processor

        response = self.client.post("/api/process", json={
            "transcript": "abc",
            "segments": [],
            "generate": ["clips"],
            "language": "en",
            "ai_config": {
                "api_key": "my-test-key",
                "model": "gemini-3.5-flash"
            }
        })

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["success"])
        mock_get_processor.assert_called_once_with(
            api_key="my-test-key",
            model_name="gemini-3.5-flash"
        )

    @patch("server.get_processor")
    def test_process_prefers_header_ai_config(self, mock_get_processor):
        processor = MagicMock()
        processor.analyze_transcript.return_value = {"success": True, "clips": []}
        mock_get_processor.return_value = processor

        response = self.client.post(
            "/api/process",
            json={
                "transcript": "abc",
                "segments": [],
                "generate": ["clips"],
                "language": "en",
                "ai_config": {"api_key": "payload-key", "model": "payload-model"}
            },
            headers={
                "X-Gemini-Api-Key": "header-key",
                "X-Gemini-Model": "header-model"
            }
        )

        self.assertEqual(response.status_code, 200)
        mock_get_processor.assert_called_once_with(
            api_key="header-key",
            model_name="header-model"
        )

    @patch("server.get_processor")
    def test_process_normalizes_invalid_language_to_polish(self, mock_get_processor):
        processor = MagicMock()
        processor.analyze_transcript.return_value = {"success": True, "clips": []}
        mock_get_processor.return_value = processor

        response = self.client.post("/api/process", json={
            "transcript": "abc",
            "segments": [],
            "generate": ["clips"],
            "language": "de"
        })

        self.assertEqual(response.status_code, 200)
        call_kwargs = processor.analyze_transcript.call_args.kwargs
        self.assertEqual(call_kwargs["language"], "pl")

    def test_ai_config_endpoints(self):
        set_response = self.client.post("/api/ai/config", json={
            "api_key": "abc123",
            "model": "gemini-3.5-flash"
        })
        self.assertEqual(set_response.status_code, 200)
        set_payload = set_response.get_json()
        self.assertTrue(set_payload["success"])
        self.assertEqual(set_payload["model"], "gemini-3.5-flash")
        self.assertTrue(set_payload["configured"])

        get_response = self.client.get("/api/ai/config")
        self.assertEqual(get_response.status_code, 200)
        get_payload = get_response.get_json()
        self.assertTrue(get_payload["success"])
        self.assertEqual(get_payload["model"], "gemini-3.5-flash")
        self.assertTrue(get_payload["configured"])

    @patch("server.get_processor")
    def test_process_stream_returns_progress_and_complete(self, mock_get_processor):
        processor = MagicMock()
        processor.analyze_transcript.return_value = {"success": True, "clips": []}
        processor.generate_blog_post.return_value = {"success": True, "blog": {}}
        processor.generate_social_posts.return_value = {"success": True, "posts": {}}
        mock_get_processor.return_value = processor

        response = self.client.post("/api/process_stream", json={
            "transcript": "abc",
            "segments": [],
            "generate": ["clips"],
            "language": "en"
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_streamed)

        lines = [line.decode("utf-8").strip() for line in response.response if line]
        self.assertTrue(lines)
        first_event = json.loads(lines[0])
        self.assertEqual(first_event["type"], "progress")
        self.assertEqual(first_event["stage"], "init")

        last_event = json.loads(lines[-1])
        self.assertEqual(last_event["type"], "complete")
        self.assertIn("result", last_event)

    def test_download_clip_start_requires_params(self):
        response = self.client.post("/api/download_clip/start", json={})
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["success"])

    @patch("server._launch_clip_download_job")
    @patch("download_clip.get_source_video_path")
    @patch("download_clip.get_clip_output_path")
    @patch("server.os.path.exists")
    def test_download_clip_start_and_status(self, mock_exists, mock_output_path, mock_source_path, mock_launch):
        mock_source_path.return_value = None
        mock_output_path.return_value = os.path.join("backend", "downloads", "clip_test.mp4")
        mock_exists.return_value = False
        mock_launch.return_value = None

        start_response = self.client.post("/api/download_clip/start", json={
            "video_id": "abc123def45",
            "start": 12,
            "end": 85,
            "title": "My Clip"
        })
        self.assertEqual(start_response.status_code, 200)
        start_payload = start_response.get_json()
        self.assertTrue(start_payload["success"])
        self.assertIn("job_id", start_payload)
        self.assertIn("estimated_seconds", start_payload)
        self.assertEqual(start_payload["status"], "queued")
        self.assertTrue(start_payload["first_download_for_video"])

        status_response = self.client.get(f"/api/download_clip/status/{start_payload['job_id']}")
        self.assertEqual(status_response.status_code, 200)
        status_payload = status_response.get_json()
        self.assertTrue(status_payload["success"])
        self.assertEqual(status_payload["job_id"], start_payload["job_id"])

    def test_download_clip_file_not_ready(self):
        with server._clip_download_lock:
            server._clip_download_jobs["job-1"] = {
                "job_id": "job-1",
                "status": "running",
                "stage": "slicing_clip",
                "message": "Slicing",
                "progress_percent": 50,
                "started_at": 0,
                "estimated_seconds": 30,
                "source_cached": True,
                "clip_cached": False,
            }

        response = self.client.get("/api/download_clip/file/job-1")
        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        self.assertFalse(payload["success"])


if __name__ == "__main__":
    unittest.main()
