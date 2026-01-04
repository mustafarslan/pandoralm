import lancedb
import os
import uuid
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self, uri="data/lancedb"):
        self.db = lancedb.connect(uri)
        self.table_name = os.getenv("LANCEDB_TABLE", "vectors")
        
    def ingest_transcript_segments(self, segments, layer_id, meeting_meta):
        """
        Ingest transcript segments into LanceDB.
        segments: List of dicts {text, start, end, speaker}
        """
        try:
            # Prepare data
            data = []
            for seg in segments:
                data.append({
                    "id": str(uuid.uuid4()),
                    "vector": [0.0] * 1536, # Placeholder for embedding. Real app needs OpenAI/Ollama call here.
                    "text": seg["text"],
                    "speaker": seg["speaker"],
                    "start": seg["start"],
                    "end": seg["end"],
                    "meeting_id": meeting_meta.get("id"),
                    "meeting_date": meeting_meta.get("date"),
                    "layer_id": layer_id,
                    "source": "meeting"
                })
            
            # Create table if not exists (with dummy data schema inference or explicit schema)
            # For MVP, using PyArrow inference by creating with first batch
            if self.table_name not in self.db.table_names():
                self.db.create_table(self.table_name, data)
            else:
                table = self.db.open_table(self.table_name)
                table.add(data)
                
            logger.info(f"Ingested {len(data)} segments into LanceDB table {self.table_name}")
            
        except Exception as e:
            logger.error(f"Failed to ingest into LanceDB: {e}")
            raise
