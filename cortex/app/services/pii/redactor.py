from typing import List
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_analyzer import RecognizerResult

class PIIRedactor:
    """
    Service for redacting detected PII using Microsoft Presidio.
    """
    
    def __init__(self):
        self.anonymizer = AnonymizerEngine()

    def redact(self, text: str, analysis_results: List[RecognizerResult]) -> str:
        """
        Redact PII entities in the text based on analysis results.
        Replaces PII with <ENTITY_TYPE>.
        """
        anonymized_result = self.anonymizer.anonymize(
            text=text,
            analyzer_results=analysis_results,
            operators={
                "DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"}),
                "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "<PHONE_NUMBER>"}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL_ADDRESS>"}),
                "IBAN_CODE": OperatorConfig("replace", {"new_value": "<IBAN>"}),
                "CREDIT_CARD": OperatorConfig("replace", {"new_value": "<CREDIT_CARD>"}),
                "CRYPTO": OperatorConfig("replace", {"new_value": "<CRYPTO_WALLET>"}),
                "IP_ADDRESS": OperatorConfig("replace", {"new_value": "<IP_ADDRESS>"}),
            }
        )
        return anonymized_result.text
