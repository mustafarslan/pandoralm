"""
Audio Processing Tasks for Meeting Intelligence
Phase 5.4: Multi-Modal Intelligence

Implements:
- S3 Streaming Input (not local file paths)
- ReBAC "Double-Check" Security (validate permissions before processing)
- Whisper + Pyannote pipeline integration
- Linear Scan Alignment for speaker-text merge

Note: This module is designed to run in the audio-worker container which has
boto3 and audio processing dependencies. The regular celery workers include
this module but will fail gracefully if the dependencies aren't available.
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import tempfile

# Conditional imports for audio-worker specific dependencies
try:
    import boto3
    from botocore.exceptions import ClientError
    AUDIO_DEPS_AVAILABLE = True
except ImportError:
    boto3 = None
    ClientError = Exception  # Fallback
    AUDIO_DEPS_AVAILABLE = False

from app.workers.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityException(Exception):
    """Raised when ReBAC permission check fails."""
    pass


def verify_layer_access_sync(user_id: str, layer_id: str, access_level: str = "WRITE") -> bool:
    """
    Synchronous ReBAC Double-Check validation.
    
    Queries the LayerPermission table to verify the user still has access
    to the target layer. This prevents TOCTOU (Time-of-Check Time-of-Use)
    vulnerabilities where permissions may have been revoked between
    queue submission and task execution.
    
    Args:
        user_id: User ID from the original request
        layer_id: Target knowledge layer
        access_level: Required access level (READ, WRITE, ADMIN)
        
    Returns:
        True if user has access, False otherwise
    """
    # Import here to avoid circular dependencies and keep worker lightweight
    from sqlalchemy import create_engine, text
    
    engine = create_engine(settings.DATABASE_URL)
    
    # Query: Check if user's roles grant access to this layer
    # This is a simplified sync check - in production, you'd fetch user roles
    # from Keycloak/cache and match against LayerPermission patterns
    query = text("""
        SELECT COUNT(*) as cnt
        FROM layer_permission lp
        JOIN layers l ON l.id = lp.layer_id
        WHERE l.id = :layer_id
        AND lp.access_level IN ('WRITE', 'ADMIN')
        AND (
            lp.role_pattern = '*' 
            OR lp.role_pattern = :user_role
        )
    """)
    
    with engine.connect() as conn:
        # Construct a basic user role pattern
        user_role = f"user:{user_id}"
        result = conn.execute(query, {"layer_id": layer_id, "user_role": user_role})
        row = result.fetchone()
        return row[0] > 0 if row else False


def get_s3_client():
    """Initialize S3/MinIO client."""
    return boto3.client(
        "s3",
        endpoint_url=os.getenv("MINIO_ENDPOINT", settings.MINIO_ENDPOINT),
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", settings.MINIO_ACCESS_KEY),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", settings.MINIO_SECRET_KEY),
        region_name="us-east-1",
    )


def stream_audio_from_s3(s3_client, bucket: str, key: str) -> str:
    """
    Stream audio from S3 to a temporary file.
    
    We must use a temp file because faster-whisper requires file paths.
    The temp file is cleaned up after processing.
    
    Returns:
        Path to temporary file
    """
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    try:
        s3_client.download_fileobj(bucket, key, temp_file)
        temp_file.close()
        logger.info(f"Downloaded audio from s3://{bucket}/{key} to {temp_file.name}")
        return temp_file.name
    except ClientError as e:
        logger.error(f"Failed to download from S3: {e}")
        raise


def linear_scan_alignment(transcription: List[Dict], diarization: List[Dict]) -> List[Dict]:
    """
    Merge speaker labels with text segments using O(N) linear scan.
    
    Algorithm:
    - Sort both lists by start time (should already be sorted)
    - Use two pointers to find overlapping segments
    - Assign speaker with maximum overlap for each text segment
    
    This is more efficient than the O(N*M) nested loop approach.
    """
    if not diarization:
        return [{"speaker": "Unknown", **seg} for seg in transcription]
    
    # Sort by start time (should already be sorted, but ensure)
    transcription = sorted(transcription, key=lambda x: x["start"])
    diarization = sorted(diarization, key=lambda x: x["start"])
    
    aligned = []
    dia_idx = 0
    
    for seg in transcription:
        seg_start = seg["start"]
        seg_end = seg["end"]
        
        best_speaker = "Unknown"
        max_overlap = 0.0
        
        # Move diarization pointer forward if behind current segment
        while dia_idx < len(diarization) and diarization[dia_idx]["end"] < seg_start:
            dia_idx += 1
        
        # Check overlapping diarization segments
        check_idx = dia_idx
        while check_idx < len(diarization) and diarization[check_idx]["start"] < seg_end:
            dia = diarization[check_idx]
            overlap_start = max(seg_start, dia["start"])
            overlap_end = min(seg_end, dia["end"])
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > max_overlap:
                max_overlap = overlap
                best_speaker = dia["speaker"]
            
            check_idx += 1
        
        aligned.append({
            "speaker": best_speaker,
            "start": seg_start,
            "end": seg_end,
            "text": seg["text"]
        })
    
    return aligned


@celery_app.task(
    name="audio.process_audio",
    queue="audio_processing",
    bind=True,
    max_retries=2,
    rate_limit="5/m",  # Rate limit to prevent GPU overload
)
def process_audio_task(
    self,
    s3_object_key: str,
    layer_id: str,
    user_id: str,
    meeting_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process an audio file from S3 for Meeting Intelligence.
    
    This task implements the Phase 5.4 Meeting Pipeline:
    1. ReBAC Double-Check (verify permissions before processing)
    2. Stream audio from S3 (ephemeral storage pattern)
    3. Transcribe with faster-whisper
    4. Diarize with pyannote.audio
    5. Align using Linear Scan algorithm
    6. Persist to LanceDB with layer_id security
    
    Args:
        s3_object_key: S3 object key (NOT a file path)
        layer_id: Target knowledge layer for indexing
        user_id: Original requester's user ID
        meeting_metadata: Optional meeting info (id, date, participants)
        
    Returns:
        Processing result with segment count and status
        
    Raises:
        SecurityException: If user no longer has layer access
    """
    logger.info(f"Starting audio processing: {s3_object_key}")
    
    # === STEP 1: ReBAC Double-Check ===
    # CRITICAL: Verify user still has WRITE access to layer_id
    # This prevents TOCTOU vulnerabilities
    logger.info(f"Performing ReBAC Double-Check for user={user_id}, layer={layer_id}")
    
    if not verify_layer_access_sync(user_id, layer_id):
        logger.warning(
            f"SECURITY: Access revoked for user {user_id} to layer {layer_id}. "
            "Aborting audio processing."
        )
        raise SecurityException(
            f"User {user_id} no longer has WRITE access to layer {layer_id}"
        )
    
    logger.info("ReBAC Double-Check passed. Proceeding with processing.")
    
    # === STEP 2: Stream from S3 ===
    s3_client = get_s3_client()
    bucket = os.getenv("S3_AUDIO_BUCKET", "pandora-audio")
    
    try:
        temp_path = stream_audio_from_s3(s3_client, bucket, s3_object_key)
    except ClientError as e:
        logger.error(f"S3 download failed: {e}")
        raise self.retry(exc=e, countdown=60)
    
    try:
        # === STEP 3 & 4: Transcription + Diarization ===
        # Import audio pipeline (avoid loading models at worker startup for memory)
        from cortex.services.audio.pipeline import AudioPipeline
        
        pipeline = AudioPipeline(use_gpu=True)
        
        logger.info("Running Whisper transcription...")
        segments, _ = pipeline.whisper.transcribe(temp_path, beam_size=5)
        
        transcription = []
        for segment in segments:
            transcription.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip()
            })
        
        logger.info(f"Transcription complete: {len(transcription)} segments")
        
        # Diarization
        diarization = []
        if pipeline.diarization:
            logger.info("Running Pyannote diarization...")
            dia_result = pipeline.diarization(temp_path)
            for turn, _, speaker in dia_result.itertracks(yield_label=True):
                diarization.append({
                    "start": turn.start,
                    "end": turn.end,
                    "speaker": speaker
                })
            logger.info(f"Diarization complete: {len(diarization)} speaker turns")
        
        # === STEP 5: Linear Scan Alignment ===
        aligned_segments = linear_scan_alignment(transcription, diarization)
        
        logger.info(f"Alignment complete: {len(aligned_segments)} aligned segments")
        
        # === STEP 6: Persist to LanceDB ===
        from app.services.vector.store import VectorStore
        
        vector_store = VectorStore()
        meeting_id = meeting_metadata.get("id", s3_object_key) if meeting_metadata else s3_object_key
        
        # Prepare chunks with required metadata (layer_id for ReBAC)
        chunks = []
        for seg in aligned_segments:
            chunks.append({
                "text": seg["text"],
                "metadata": {
                    "layer_id": layer_id,  # CRITICAL: ReBAC security
                    "source_type": "meeting",
                    "source_id": meeting_id,
                    "timestamp": seg["start"],
                    "speaker_id": seg["speaker"],
                    "meeting_date": meeting_metadata.get("date") if meeting_metadata else datetime.utcnow().isoformat(),
                }
            })
        
        vector_store.add_chunks(chunks)
        logger.info(f"Persisted {len(chunks)} chunks to LanceDB with layer_id={layer_id}")
        
        return {
            "status": "success",
            "s3_key": s3_object_key,
            "layer_id": layer_id,
            "segment_count": len(aligned_segments),
            "meeting_id": meeting_id,
        }
        
    finally:
        # === CLEANUP ===
        if os.path.exists(temp_path):
            os.remove(temp_path)
            logger.info(f"Cleaned up temp file: {temp_path}")


@celery_app.task(name="audio.health_check", queue="audio_processing")
def audio_health_check() -> Dict[str, Any]:
    """Health check for audio worker."""
    return {
        "status": "healthy",
        "worker": "audio_processing",
        "timestamp": datetime.utcnow().isoformat()
    }
