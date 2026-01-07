from typing import List, Optional
from presidio_analyzer import AnalyzerEngine, RecognizerResult

class PIIDetector:
    """
    Service for detecting PII in text using Microsoft Presidio.
    """
    
    def __init__(self, language: str = "en"):
        self.analyzer = AnalyzerEngine()
        self.language = language

    def detect(self, text: str) -> List[RecognizerResult]:
        """
        Analyze text for PII entities.
        """
        results = self.analyzer.analyze(text=text, language=self.language)
        return results
