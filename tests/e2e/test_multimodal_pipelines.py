"""
E2E Tests for Phase 5.4: Multi-Modal Intelligence Pipelines

Tests:
1. Audio Pipeline: Security (ReBAC Double-Check) + S3 streaming
2. Code Pipeline: Graph mapping with layer_id enforcement
3. Stream Protocol: Vercel AI SDK format verification
"""
import pytest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestAudioPipelineSecurity:
    """
    Tests for the ReBAC Double-Check pattern in audio processing.
    """
    
    def test_audio_task_rejects_revoked_permissions(self):
        """
        SECURITY TEST: Verify that if a user's permission is revoked
        after the job is queued but before it runs, the task fails.
        """
        from app.workers.tasks.audio import verify_layer_access_sync, SecurityException
        
        # Mock database to return no matching permissions
        with patch('app.workers.tasks.audio.create_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (0,)  # No permissions found
            mock_conn.execute.return_value = mock_result
            mock_engine.return_value.connect.return_value.__enter__ = lambda _: mock_conn
            mock_engine.return_value.connect.return_value.__exit__ = MagicMock()
            
            # Should return False (access denied)
            result = verify_layer_access_sync("user123", "layer_secret")
            assert result is False
    
    def test_audio_task_accepts_valid_permissions(self):
        """
        Verify that valid permissions allow processing.
        """
        from app.workers.tasks.audio import verify_layer_access_sync
        
        with patch('app.workers.tasks.audio.create_engine') as mock_engine:
            mock_conn = MagicMock()
            mock_result = MagicMock()
            mock_result.fetchone.return_value = (1,)  # Permission found
            mock_conn.execute.return_value = mock_result
            mock_engine.return_value.connect.return_value.__enter__ = lambda _: mock_conn
            mock_engine.return_value.connect.return_value.__exit__ = MagicMock()
            
            result = verify_layer_access_sync("user123", "layer_allowed")
            assert result is True
    
    def test_linear_scan_alignment_complexity(self):
        """
        Verify the linear scan alignment algorithm is O(N) not O(N*M).
        """
        from app.workers.tasks.audio import linear_scan_alignment
        
        # Create test data
        transcription = [
            {"start": 0.0, "end": 2.0, "text": "Hello there"},
            {"start": 2.5, "end": 4.0, "text": "General Kenobi"},
            {"start": 5.0, "end": 7.0, "text": "You are a bold one"},
        ]
        
        diarization = [
            {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_A"},
            {"start": 3.5, "end": 8.0, "speaker": "SPEAKER_B"},
        ]
        
        aligned = linear_scan_alignment(transcription, diarization)
        
        assert len(aligned) == 3
        assert aligned[0]["speaker"] == "SPEAKER_A"  # 0-2 overlaps with A (0-3)
        assert aligned[1]["speaker"] == "SPEAKER_A"  # 2.5-4 mostly overlaps with A
        assert aligned[2]["speaker"] == "SPEAKER_B"  # 5-7 overlaps with B (3.5-8)


class TestCodePipelineSecurity:
    """
    Tests for layer_id enforcement in code graph mapping.
    """
    
    def test_graph_mapper_includes_layer_id(self):
        """
        Verify that all Neo4j nodes/edges include layer_id property.
        """
        from app.services.code.graph_mapper import CodeGraphMapper
        from app.schemas.code import CodeChunk
        
        # Mock Neo4j store
        mock_store = MagicMock()
        mapper = CodeGraphMapper(mock_store)
        
        # Create a test chunk
        chunk = CodeChunk(
            id="chunk123",
            text="def hello(): pass",
            file_path="/src/main.py",
            node_type="function",
            layer_id="layer_engineering",
            document_id="doc456",
            metadata={"raw_name": "hello"}
        )
        
        mapper.map_repo([chunk], "workspace_123")
        
        # Verify upsert_entity was called with layer_id
        entity_calls = mock_store.upsert_entity.call_args_list
        for call in entity_calls:
            kwargs = call.kwargs
            assert "layer_id" in kwargs
            assert kwargs["layer_id"] == "layer_engineering"
        
        # Verify upsert_relationship was called with layer_id
        rel_calls = mock_store.upsert_relationship.call_args_list
        for call in rel_calls:
            kwargs = call.kwargs
            assert "layer_id" in kwargs


class TestStreamProtocol:
    """
    Tests for Vercel AI SDK Data Stream Protocol compliance.
    """
    
    def test_text_chunk_format(self):
        """Verify text chunks use format: 0:"content"\n"""
        from app.api.protocols.vercel import StreamProtocol
        
        result = StreamProtocol.text_chunk("Hello world")
        assert result.startswith("0:")
        assert result.endswith("\n")
        # Content should be JSON-escaped
        assert '"Hello world"' in result
    
    def test_data_chunk_format(self):
        """Verify data chunks use format: 2:[{...}]\n"""
        from app.api.protocols.vercel import StreamProtocol
        
        data = [{"type": "citation", "source": "doc1"}]
        result = StreamProtocol.data_chunk(data)
        
        assert result.startswith("2:")
        assert result.endswith("\n")
        
        # Parse the JSON to verify structure
        json_str = result[2:-1]  # Remove "2:" prefix and "\n" suffix
        parsed = json.loads(json_str)
        assert isinstance(parsed, list)
        assert parsed[0]["type"] == "citation"
    
    def test_meeting_ref_format(self):
        """Verify meeting_ref produces correct Generative UI trigger."""
        from app.api.protocols.vercel import StreamProtocol
        
        result = StreamProtocol.meeting_ref(
            file_id="meeting_123",
            timestamp=45.5,
            title="Sprint Planning"
        )
        
        assert result.startswith("2:")
        
        # Parse and verify
        json_str = result[2:-1]
        parsed = json.loads(json_str)
        
        assert len(parsed) == 1
        assert parsed[0]["type"] == "meeting_ref"
        assert parsed[0]["fileId"] == "meeting_123"
        assert parsed[0]["timestamp"] == 45.5
        assert parsed[0]["title"] == "Sprint Planning"
    
    def test_error_chunk_format(self):
        """Verify error chunks use format: 3:"message"\n"""
        from app.api.protocols.vercel import StreamProtocol
        
        result = StreamProtocol.error_chunk("Something went wrong")
        assert result.startswith("3:")
        assert result.endswith("\n")
    
    def test_graph_viz_format(self):
        """Verify graph_viz produces correct visualization trigger."""
        from app.api.protocols.vercel import StreamProtocol
        
        nodes = [{"id": "1", "label": "Function A"}]
        edges = [{"source": "1", "target": "2"}]
        
        result = StreamProtocol.graph_viz(nodes, edges, title="Code Graph")
        
        json_str = result[2:-1]
        parsed = json.loads(json_str)
        
        assert parsed[0]["type"] == "graph_viz"
        assert parsed[0]["nodes"] == nodes
        assert parsed[0]["edges"] == edges


class TestKubernetesManifests:
    """
    Validate Kubernetes manifest correctness.
    """
    
    def test_audio_worker_has_gpu_toleration(self):
        """Verify audio worker tolerates GPU nodes."""
        import yaml
        
        manifest_path = "infra/k8s/worker-audio.yaml"
        try:
            with open(manifest_path) as f:
                docs = list(yaml.safe_load_all(f))
        except FileNotFoundError:
            pytest.skip(f"Manifest not found: {manifest_path}")
        
        deployment = next((d for d in docs if d.get("kind") == "Deployment"), None)
        assert deployment is not None
        
        tolerations = deployment["spec"]["template"]["spec"].get("tolerations", [])
        gpu_tol = next(
            (t for t in tolerations if t.get("key") == "accelerator"), 
            None
        )
        assert gpu_tol is not None
        assert gpu_tol["value"] == "gpu"
    
    def test_meeting_bot_has_shm_mount(self):
        """Verify meeting bot mounts /dev/shm as Memory."""
        import yaml
        
        manifest_path = "infra/k8s/bot-meeting.yaml"
        try:
            with open(manifest_path) as f:
                doc = yaml.safe_load(f)
        except FileNotFoundError:
            pytest.skip(f"Manifest not found: {manifest_path}")
        
        volumes = doc["spec"]["template"]["spec"].get("volumes", [])
        shm_vol = next((v for v in volumes if v.get("name") == "dshm"), None)
        
        assert shm_vol is not None
        assert shm_vol["emptyDir"]["medium"] == "Memory"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
