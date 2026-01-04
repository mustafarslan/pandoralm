import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys

# Mock missing dependencies
sys.modules["boto3"] = MagicMock()
sys.modules["redis"] = MagicMock()
sys.modules["faster_whisper"] = MagicMock()
sys.modules["pyannote.audio"] = MagicMock()
sys.modules["torch"] = MagicMock()
sys.modules["celery"] = MagicMock()
sys.modules["cortex.services.vector.store"] = MagicMock() # Mock the module containing VectorStore

# Mock environment variables before importing worker
os.environ["REDIS_URL"] = "redis://mock:6379"
os.environ["S3_ENDPOINT"] = "http://mock:9000"

try:
    from cortex.workers.audio_gpu import process_single_job
except ImportError:
    pass

class TestAudioPipeline(unittest.TestCase):
    
    @patch('cortex.workers.audio_gpu.s3')
    @patch('cortex.workers.audio_gpu.pipeline')
    @patch('cortex.services.vector.store.VectorStore') # Patch the class where it is defined/imported from
    @patch('os.remove')
    def test_process_single_job(self, mock_remove, mock_vector_store_cls, mock_pipeline, mock_s3):
        # Setup mocks
        mock_pipeline.process.return_value = [
            {"speaker": "SPEAKER_00", "start": 0.0, "end": 2.0, "text": "Hello world."},
            {"speaker": "SPEAKER_01", "start": 2.5, "end": 4.0, "text": "Hi there."}
        ]
        
        mock_vector_store_instance = mock_vector_store_cls.return_value
        
        # Test Payload
        payload = {
            "s3_key": "layer_123/meeting_456.webm",
            "layer_id": "layer_123",
            "meeting_meta": {
                "id": "meeting_456",
                "date": "2023-11-01"
            }
        }
        
        job_data = json.dumps(payload)
        
        # Execute
        process_single_job(job_data)
        
        # Verify S3 Download
        mock_s3.download_file.assert_called_once_with(
            "pandora-audio", 
            "layer_123/meeting_456.webm", 
            "/tmp/meeting_456.webm"
        )
        
        # Verify Pipeline Processing
        mock_pipeline.process.assert_called_once_with("/tmp/meeting_456.webm")
        
        # Verify Vector Store Ingestion
        # The dynamic import inside process_single_job will return our mocked class
        mock_vector_store_instance.ingest_transcript_segments.assert_called_once()
        args, _ = mock_vector_store_instance.ingest_transcript_segments.call_args
        self.assertEqual(len(args[0]), 2) # 2 segments
        self.assertEqual(args[1], "layer_123")
        
        # Verify Cleanup
        mock_remove.assert_called_once_with("/tmp/meeting_456.webm")

if __name__ == '__main__':
    unittest.main()
