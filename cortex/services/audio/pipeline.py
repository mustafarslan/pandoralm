import os
import logging
from faster_whisper import WhisperModel
from pyannote.audio import Pipeline
import torch

logger = logging.getLogger(__name__)

class AudioPipeline:
    def __init__(self, use_gpu=True):
        device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        
        logger.info(f"Initializing AudioPipeline on {device} ({compute_type})")

        # Initialize Whisper
        self.whisper = WhisperModel("large-v3", device=device, compute_type=compute_type)

        # Initialize Pyannote (Requires generic loading or HF token if using protected models)
        # Note: In a real env, we'd pass use_auth_token=os.getenv("HF_TOKEN")
        try:
             self.diarization = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=os.getenv("HF_TOKEN")
            )
             if self.diarization:
                 self.diarization.to(torch.device(device))
        except Exception as e:
            logger.warning(f"Could not load Pyannote pipeline: {e}. Diarization will be disabled.")
            self.diarization = None

    def process(self, audio_path: str):
        """
        Runs the full pipeline: Transcribe -> Diarize -> Align
        """
        logger.info(f"Starting transcription for {audio_path}")
        segments, info = self.whisper.transcribe(audio_path, beam_size=5)
        
        transcription_result = []
        for segment in segments:
            transcription_result.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })

        diarization_result = None
        if self.diarization:
             logger.info(f"Starting diarization for {audio_path}")
             diarization = self.diarization(audio_path)
             diarization_result = []
             for turn, _, speaker in diarization.itertracks(yield_label=True):
                 diarization_result.append({
                     "start": turn.start,
                     "end": turn.end,
                     "speaker": speaker
                 })

        return self.align(transcription_result, diarization_result)

    def align(self, transcription, diarization):
        """
        Merges Whisper segments with Pyannote speaker labels.
        Simple linear scan alignment.
        """
        if not diarization:
             return [{"speaker": "Unknown", **seg} for seg in transcription]

        aligned_segments = []
        
        for seg in transcription:
            # Find the speaker who spoke the most during this segment
            seg_start = seg["start"]
            seg_end = seg["end"]
            
            best_speaker = "Unknown"
            max_overlap = 0
            
            for dia in diarization:
                # Calculate overlap
                start = max(seg_start, dia["start"])
                end = min(seg_end, dia["end"])
                overlap = max(0, end - start)
                
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = dia["speaker"]
            
            aligned_segments.append({
                "speaker": best_speaker,
                "start": seg_start,
                "end": seg_end,
                "text": seg["text"]
            })
            
        return aligned_segments
