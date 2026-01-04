"""
Text Chunking Service
Configurable document chunking with multiple strategies
"""
import re
import uuid
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import tiktoken


class SplitterType(str, Enum):
    """Type of text splitter."""
    RECURSIVE = "recursive"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"
    FIXED = "fixed"


@dataclass
class ChunkConfig:
    """Configuration for text chunking."""
    chunk_size: int = 1000  # Characters
    chunk_overlap: int = 200  # Characters
    splitter: SplitterType = SplitterType.RECURSIVE
    min_chunk_size: int = 100  # Minimum characters per chunk
    
    def validate(self) -> None:
        """Validate configuration."""
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        if self.chunk_size < self.min_chunk_size:
            raise ValueError(f"chunk_size must be at least {self.min_chunk_size}")


@dataclass
class ChunkPreview:
    """Preview of a text chunk."""
    index: int
    content: str
    char_count: int
    token_count: int
    start_offset: int
    end_offset: int
    
    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "content": self.content,
            "char_count": self.char_count,
            "token_count": self.token_count,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }


class TextChunker:
    """
    Configurable text chunking service.
    
    Supports multiple splitting strategies:
    - RECURSIVE: Split by paragraphs, then sentences, then characters
    - SENTENCE: Split by sentences only
    - PARAGRAPH: Split by paragraphs only
    - FIXED: Fixed character-based splitting
    """
    
    # Separators for recursive splitting (in order of preference)
    RECURSIVE_SEPARATORS = [
        "\n\n",  # Paragraphs
        "\n",    # Lines
        ". ",    # Sentences
        "! ",
        "? ",
        "; ",
        ", ",    # Clauses
        " ",     # Words
        "",      # Characters
    ]
    
    # Sentence boundary pattern
    SENTENCE_PATTERN = re.compile(r'(?<=[.!?])\s+')
    
    # Paragraph boundary pattern
    PARAGRAPH_PATTERN = re.compile(r'\n\s*\n')
    
    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Initialize the chunker.
        
        Args:
            encoding_name: tiktoken encoding name for token counting
        """
        try:
            self._encoding = tiktoken.get_encoding(encoding_name)
        except Exception:
            # Fallback if tiktoken not available or encoding not found
            self._encoding = None
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        if self._encoding:
            return len(self._encoding.encode(text))
        # Fallback: estimate ~4 chars per token
        return len(text) // 4
    
    def chunk_text(
        self,
        text: str,
        config: ChunkConfig = None,
    ) -> List[ChunkPreview]:
        """
        Chunk text according to configuration.
        
        Args:
            text: Text to chunk
            config: Chunking configuration
            
        Returns:
            List of chunk previews
        """
        config = config or ChunkConfig()
        config.validate()
        
        # Select splitter
        if config.splitter == SplitterType.RECURSIVE:
            chunks = self._recursive_split(text, config)
        elif config.splitter == SplitterType.SENTENCE:
            chunks = self._sentence_split(text, config)
        elif config.splitter == SplitterType.PARAGRAPH:
            chunks = self._paragraph_split(text, config)
        else:  # FIXED
            chunks = self._fixed_split(text, config)
        
        # Create previews with metadata
        previews = []
        offset = 0
        
        for i, chunk_text in enumerate(chunks):
            # Find actual offset in original text
            start = text.find(chunk_text, offset)
            if start == -1:
                start = offset
            end = start + len(chunk_text)
            
            previews.append(ChunkPreview(
                index=i,
                content=chunk_text,
                char_count=len(chunk_text),
                token_count=self.count_tokens(chunk_text),
                start_offset=start,
                end_offset=end,
            ))
            
            # Move offset past overlap
            offset = max(start + 1, end - config.chunk_overlap)
        
        return previews
    
    def _recursive_split(self, text: str, config: ChunkConfig) -> List[str]:
        """Recursively split text using multiple separators."""
        return self._split_recursive(
            text,
            self.RECURSIVE_SEPARATORS,
            config.chunk_size,
            config.chunk_overlap,
        )
    
    def _split_recursive(
        self,
        text: str,
        separators: List[str],
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[str]:
        """Internal recursive split implementation."""
        final_chunks = []
        
        # Find the best separator
        separator = separators[-1]
        new_separators = []
        
        for i, s in enumerate(separators):
            if s == "":
                separator = s
                break
            if s in text:
                separator = s
                new_separators = separators[i + 1:]
                break
        
        # Split by separator
        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)
        
        # Merge small splits
        good_splits = []
        current = ""
        
        for split in splits:
            piece = split if not separator else split + separator
            
            if len(current) + len(piece) <= chunk_size:
                current += piece
            else:
                if current:
                    good_splits.append(current.rstrip(separator))
                
                if len(piece) > chunk_size and new_separators:
                    # Recurse with next separator
                    sub_chunks = self._split_recursive(
                        piece, new_separators, chunk_size, chunk_overlap
                    )
                    good_splits.extend(sub_chunks)
                    current = ""
                else:
                    current = piece
        
        if current:
            good_splits.append(current.rstrip(separator))
        
        # Merge with overlap
        return self._merge_with_overlap(good_splits, chunk_size, chunk_overlap)
    
    def _merge_with_overlap(
        self,
        splits: List[str],
        chunk_size: int,
        chunk_overlap: int,
    ) -> List[str]:
        """Merge splits with overlap between consecutive chunks."""
        if not splits:
            return []
        
        merged = []
        current = splits[0]
        
        for next_split in splits[1:]:
            if len(current) + len(next_split) <= chunk_size:
                current = current + " " + next_split
            else:
                merged.append(current)
                # Add overlap from end of current
                overlap_text = current[-chunk_overlap:] if len(current) > chunk_overlap else current
                current = overlap_text + " " + next_split
                
                # Trim if too long
                if len(current) > chunk_size:
                    current = next_split
        
        if current:
            merged.append(current)
        
        return merged
    
    def _sentence_split(self, text: str, config: ChunkConfig) -> List[str]:
        """Split text by sentences."""
        sentences = self.SENTENCE_PATTERN.split(text)
        return self._merge_with_overlap(sentences, config.chunk_size, config.chunk_overlap)
    
    def _paragraph_split(self, text: str, config: ChunkConfig) -> List[str]:
        """Split text by paragraphs."""
        paragraphs = self.PARAGRAPH_PATTERN.split(text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        return self._merge_with_overlap(paragraphs, config.chunk_size, config.chunk_overlap)
    
    def _fixed_split(self, text: str, config: ChunkConfig) -> List[str]:
        """Fixed-size character splitting."""
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + config.chunk_size, len(text))
            chunks.append(text[start:end])
            start = end - config.chunk_overlap
        
        return chunks


# Singleton instance
_chunker: Optional[TextChunker] = None



def get_chunker() -> TextChunker:
    """Get or create the text chunker instance."""
    global _chunker
    if _chunker is None:
        _chunker = TextChunker()
    return _chunker


# =============================================================================
# Process Pool for CPU-bound Chunking
# =============================================================================

import os
import asyncio
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app.core.config import settings

_process_pool: Optional[ThreadPoolExecutor] = None

def get_process_pool() -> ThreadPoolExecutor:
    """Get or create the thread pool for CPU-bound tasks."""
    global _process_pool
    if _process_pool is None:
        # Determine worker count
        max_workers = settings.PANDORA_WORKER_PROCESSES
        if max_workers == 0:
            # Default to CPU count - 1 (leave one for main process/IO)
            # or usage os.cpu_count() directly
            cpu_count = os.cpu_count() or 4
            max_workers = max(1, cpu_count - 1)
            
        _process_pool = ThreadPoolExecutor(
            max_workers=max_workers,
        )
    return _process_pool

def _init_worker():
    """Initialize worker process (e.g. signal handlers)."""
    # Important: Avoid inheriting signals like SIGINT from parent if running in some environments
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def _chunk_text_wrapper(text: str, config_dict: dict) -> List[dict]:
    """
    Wrapper for chunk_text to run in process pool.
    We pass config as dict (pydantic/dataclass pickling can be tricky sometimes, 
    but dataclass is usually fine. Dict is safest).
    """
    # Reconstruct config
    config = ChunkConfig(**config_dict)
    chunker = get_chunker() # Logic inside worker process
    previews = chunker.chunk_text(text, config)
    
    return [
        {
            "content": p.content,
            "metadata": {
                "index": p.index,
                "char_count": p.char_count,
                "token_count": p.token_count,
                "start_offset": p.start_offset,
                "end_offset": p.end_offset,
            }
        }
        for p in previews
    ]

# Public synchronous helper (kept for backward compatibility)
def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[dict]:
    """helper function for simple chunking (runs in current thread)."""
    chunker = get_chunker()
    config = ChunkConfig(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    previews = chunker.chunk_text(text, config)
    
    return [
        {
            "content": p.content,
            "metadata": {
                "index": p.index,
                "char_count": p.char_count,
                "token_count": p.token_count,
                "start_offset": p.start_offset,
                "end_offset": p.end_offset,
            }
        }
        for p in previews
    ]

async def chunk_text_parallel(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[dict]:
    """
    Async wrapper to run chunking in a separate process.
    Prevents blocking the event loop during heavy regex/tokenization.
    """
    pool = get_process_pool()
    loop = asyncio.get_running_loop()
    
    config_dict = {
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "splitter": "recursive", # default
        "min_chunk_size": 100
    }
    
    # Run in process pool
    return await loop.run_in_executor(
        pool,
        _chunk_text_wrapper,
        text,
        config_dict
    )
