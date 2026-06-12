import os
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database


class TestDatabasePersistence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_paths = {
            "DATA_FILE": database.DATA_FILE,
            "TRANSCRIPTS_INDEX": database.TRANSCRIPTS_INDEX,
            "TRANSCRIPTS_DIR": database.TRANSCRIPTS_DIR,
            "SCRIPTS_FILE": database.SCRIPTS_FILE,
        }

        database.DATA_FILE = os.path.join(self.temp_dir.name, "projects.json")
        database.TRANSCRIPTS_INDEX = os.path.join(self.temp_dir.name, "transcripts.json")
        database.TRANSCRIPTS_DIR = os.path.join(self.temp_dir.name, "transcripts")
        database.SCRIPTS_FILE = os.path.join(self.temp_dir.name, "scripts.json")
        database.ensure_data_dir()

    def tearDown(self):
        database.DATA_FILE = self.original_paths["DATA_FILE"]
        database.TRANSCRIPTS_INDEX = self.original_paths["TRANSCRIPTS_INDEX"]
        database.TRANSCRIPTS_DIR = self.original_paths["TRANSCRIPTS_DIR"]
        database.SCRIPTS_FILE = self.original_paths["SCRIPTS_FILE"]
        self.temp_dir.cleanup()

    def test_save_project_updates_existing_project_when_id_provided(self):
        created = database.save_project({
            "type": "content-maximizer",
            "title": "Project A",
            "video_id": "video-1"
        })
        project_id = created["id"]

        updated = database.save_project({
            "id": project_id,
            "type": "content-maximizer",
            "title": "Project A Updated",
            "video_id": "video-1"
        })

        self.assertEqual(updated["id"], project_id)
        projects = database.get_all_projects()
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0]["title"], "CM - Project A Updated")

        details = database.get_project_details(project_id)
        self.assertEqual(details["title"], "CM - Project A Updated")
        self.assertEqual(details["id"], project_id)

    def test_project_storage_rejects_invalid_project_ids(self):
        invalid_ids = [
            "../outside",
            "nested/path",
            "nested\\path",
            "",
            " bad-id",
            "bad-id ",
            "bad$id",
        ]

        for invalid_id in invalid_ids:
            with self.subTest(invalid_id=invalid_id):
                with self.assertRaises(database.InvalidIdentifierError):
                    database.save_project({
                        "id": invalid_id,
                        "type": "content-maximizer",
                        "title": "Unsafe Project"
                    })

                with self.assertRaises(database.InvalidIdentifierError):
                    database.get_project_details(invalid_id)

                with self.assertRaises(database.InvalidIdentifierError):
                    database.delete_project(invalid_id)

        self.assertEqual(database.get_all_projects(), [])

    def test_save_project_normalizes_legacy_history_prefixes(self):
        content_project = database.save_project({
            "type": "content-maximizer",
            "title": "MT - Old Content Project",
            "video_id": "video-1"
        })
        growth_project = database.save_project({
            "type": "business-growth-strategy",
            "title": "SWB - Old Strategy Project"
        })

        projects = database.get_all_projects()
        self.assertEqual(projects[1]["title"], "CM - Old Content Project")
        self.assertEqual(projects[0]["title"], "BGS - Old Strategy Project")
        self.assertEqual(database.get_project_details(content_project["id"])["title"], "CM - Old Content Project")
        self.assertEqual(database.get_project_details(growth_project["id"])["title"], "BGS - Old Strategy Project")

    def test_concurrent_script_writes_do_not_lose_entries(self):
        worker_count = 20
        start_barrier = threading.Barrier(worker_count)

        def save_script(index):
            start_barrier.wait()
            database.save_script({
                "project_id": f"project-{index}",
                "title": f"Script {index}",
                "status": "written",
                "chapters": [{"title": "Intro", "script": "Hello"}]
            })

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            list(executor.map(save_script, range(worker_count)))

        saved = database.get_all_scripts()
        self.assertEqual(len(saved), worker_count)

    def test_update_and_delete_script(self):
        script = database.save_script({
            "project_id": "project-1",
            "title": "Initial Title",
            "status": "written",
            "chapters": [{"title": "Intro", "script": "Hello"}]
        })

        updated = database.update_script(script["id"], {
            "status": "scheduled",
            "scheduled_date": "2026-02-10",
            "chapters": [{"title": "Intro", "script": "Updated"}],
            "title": "Updated Title"
        })

        self.assertTrue(updated)
        scripts = database.get_all_scripts()
        stored = next((s for s in scripts if s["id"] == script["id"]), None)
        self.assertIsNotNone(stored)
        self.assertEqual(stored["status"], "scheduled")
        self.assertEqual(stored["scheduled_date"], "2026-02-10")
        self.assertEqual(stored["title"], "Updated Title")
        self.assertEqual(stored["chapters"][0]["script"], "Updated")

        deleted = database.delete_script(script["id"])
        self.assertTrue(deleted)
        deleted_again = database.delete_script(script["id"])
        self.assertFalse(deleted_again)

    def test_save_transcript_independently_creates_index_and_file(self):
        data = {
            "video_id": "abc123def45",
            "line_count": 2,
            "language": "en",
            "transcript": "hello",
            "raw_data": []
        }

        saved = database.save_transcript_independently(data)
        self.assertTrue(saved)

        index = database._read_json(database.TRANSCRIPTS_INDEX, [])
        self.assertEqual(len(index), 1)
        self.assertEqual(index[0]["video_id"], "abc123def45")

        transcript_file = os.path.join(database.TRANSCRIPTS_DIR, "abc123def45.json")
        self.assertTrue(os.path.exists(transcript_file))

        saved_again = database.save_transcript_independently(data)
        self.assertTrue(saved_again)
        index_again = database._read_json(database.TRANSCRIPTS_INDEX, [])
        self.assertEqual(len(index_again), 1)


if __name__ == "__main__":
    unittest.main()
