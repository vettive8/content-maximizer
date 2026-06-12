
import unittest
import json
import os
import sys
import io
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server import app
from business_growth_strategy_processor import BusinessGrowthStrategyProcessor

class TestGamePlanFlow(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('server.BusinessGrowthStrategyProcessor')
    @patch('server.scrape_website_text')
    def test_generate_business_growth_strategy_stream(self, mock_scrape, MockProcessor):
        # Setup Mocks
        mock_scrape.return_value = "Mock website content"
        
        # Mock Processor instance
        processor_instance = MockProcessor.return_value
        
        # Mock the stream generator
        def mock_stream(*args, **kwargs):
            yield json.dumps({"type": "progress", "stage": "init", "percent": 5, "message": "Init"}) + "\n"
            yield json.dumps({"type": "progress", "stage": "market_research", "percent": 20, "message": "Market"}) + "\n"
            yield json.dumps({"type": "complete", "percent": 100, "business_growth_strategy": {"result": "ok"}}) + "\n"
            
        processor_instance.run_full_pipeline_stream.side_effect = mock_stream

        response = self.app.post('/api/generate_business_growth_strategy', data={
            'context': 'Test Context',
            'website': 'https://example.com',
            'language': 'en',
            'transcripts': (io.BytesIO(b'test transcript'), 'test.txt')
        }, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.is_streamed)

        # Consume stream
        lines = [line.decode('utf-8').strip() for line in response.response]
        lines = [l for l in lines if l] # Filter empty

        # Check events
        # Note: Server yields its own init event first
        # yield json.dumps({"type": "progress", "stage": "init", "percent": 1, ...})
        
        first_event = json.loads(lines[0])
        self.assertEqual(first_event['type'], 'progress')
        self.assertEqual(first_event['stage'], 'init')
        self.assertEqual(first_event['percent'], 1)

        # Check scraping event
        # yield json.dumps({"type": "progress", "stage": "scraping", ...})
        second_event = json.loads(lines[1])
        self.assertEqual(second_event['stage'], 'scraping')

        processor_instance.run_full_pipeline_stream.assert_called_once()
        call_kwargs = processor_instance.run_full_pipeline_stream.call_args.kwargs
        self.assertEqual(call_kwargs['language'], 'en')

    @patch('server.BusinessGrowthStrategyProcessor')
    def test_generate_business_growth_strategy_stream_normalizes_invalid_language_to_polish(self, MockProcessor):
        processor_instance = MockProcessor.return_value
        processor_instance.run_full_pipeline_stream.return_value = iter([
            json.dumps({"type": "complete", "percent": 100, "business_growth_strategy": {"result": "ok"}}) + "\n"
        ])

        response = self.app.post('/api/generate_business_growth_strategy', data={
            'context': 'Test Context',
            'website': '',
            'language': 'de',
            'transcripts': (io.BytesIO(b'test transcript'), 'test.txt')
        }, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 200)
        list(response.response)
        processor_instance.run_full_pipeline_stream.assert_called_once()
        call_kwargs = processor_instance.run_full_pipeline_stream.call_args.kwargs
        self.assertEqual(call_kwargs['language'], 'pl')
        
        # Check processor events
        # We might have scraping_done before processor
        # ...

    def test_processor_stream_logic(self):
        """Test the logic inside BusinessGrowthStrategyProcessor.run_full_pipeline_stream (mocking external AI calls)"""
        p = BusinessGrowthStrategyProcessor("test_key")
        
        # Mock internal methods to avoid real API
        p._get_cm_transcripts = MagicMock(return_value="CM Transcripts")
        p.generate_market_research = MagicMock(return_value={"res": "mr"})
        p.generate_psychoanalysis = MagicMock(return_value={"res": "pa"})
        p.generate_creative_brief = MagicMock(return_value={"res": "cb"})
        
        # Run stream
        events = list(p.run_full_pipeline_stream("ctx", "web", "sales"))
        
        # Check we got events
        self.assertTrue(len(events) > 5)
        
        # Convert first to json to check
        first = json.loads(events[0])
        self.assertEqual(first['type'], 'progress')
        
        # Check final event
        last = json.loads(events[-1])
        self.assertEqual(last['type'], 'complete')
        self.assertIn('business_growth_strategy', last)

    def test_processor_stream_forwards_language_to_sections(self):
        p = BusinessGrowthStrategyProcessor("test_key")
        p._get_cm_transcripts = MagicMock(return_value="CM Transcripts")
        p.generate_market_research = MagicMock(return_value={"res": "mr"})
        p.generate_psychoanalysis = MagicMock(return_value={"res": "pa"})
        p.generate_creative_brief = MagicMock(return_value={"res": "cb"})

        list(p.run_full_pipeline_stream("ctx", "web", "sales", language="en"))

        self.assertEqual(p.generate_market_research.call_args.kwargs["language"], "en")
        self.assertEqual(p.generate_psychoanalysis.call_args.kwargs["language"], "en")
        self.assertEqual(p.generate_creative_brief.call_args.kwargs["language"], "en")

if __name__ == '__main__':
    unittest.main()
