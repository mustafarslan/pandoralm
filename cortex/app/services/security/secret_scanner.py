
import logging
from typing import List, Dict, Any
from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings
from detect_secrets.core.potential_secret import PotentialSecret

logger = logging.getLogger(__name__)

class SecretScanner:
    """
    Scans content for potential secrets (API keys, passwords, tokens)
    using Yelp's detect-secrets library.
    """
    
    def __init__(self):
        # Initialize with default plugins
        from detect_secrets.settings import get_plugins, default_settings
        with default_settings():
            self.plugins = get_plugins()
        logger.info(f"[SecretScanner] Initialized with {len(self.plugins)} plugins")

    def scan(self, content: str, filename: str = "memory") -> List[Dict[str, Any]]:
        """
        Scan string content for secrets.
        
        Args:
            content: The text content to scan.
            filename: Virtual filename for reporting (default: "memory")
            
        Returns:
            List of detected secrets.
        """
        if not content:
            return []
            
        secrets = SecretsCollection()
        
        # detect-secrets works best with files, but we can scan lines
        # We simulate file scanning by iterating lines
        lines = content.splitlines()
        
        # Manually run plugins on lines
        # Note: detect-secrets usually expects a file scan loop.
        # We can implement a simplified scanner using the plugins directly
        # or use SecretsCollection.
        
        # A simpler way using SecretsCollection involves creating a temporary file,
        # but that's IO heavy. Let's iterate plugins manually if possible.
        # Actually, SecretsCollection.scan_file is standard.
        # But we have in-memory content.
        
        detected_secrets = []
        
        # Iterate over lines and plugins
        for line_num, line in enumerate(lines, start=1):
            for plugin in self.plugins:
                try:
                    # Analyze line
                    # Most plugins have verify(line) or analyze(line)
                    # Use analyze_string method if available or analyze_line
                    # secret = plugin.analyze_string(line) # Varies by version
                    # For detect-secrets 1.5.0, standard flow is:
                    
                    param_gen = plugin.analyze_string(line)
                    for found_secret in param_gen:
                        # Convert to dict
                        secret_dict = {
                            "type": plugin.__class__.__name__,
                            "line_number": line_num,
                            "secret_hash": getattr(found_secret, "secret_hash", "unknown"), # Safely get hash
                            "is_verified": getattr(found_secret, "is_verified", False),
                             # Obfuscate strictly for logs/returns
                            "snippet": self._obfuscate(line)
                        }
                        detected_secrets.append(secret_dict)
                        # We found a secret on this line with this plugin.
                        # Do we continue to other plugins? Yes, maybe.
                        # Do we break? Maybe not.
                        
                except Exception as e:
                    # Ignore scan errors
                    logger.debug(f"Plugin {plugin.__class__.__name__} failed: {e}")
                    continue
                    
        return detected_secrets
        
    def _obfuscate(self, text: str) -> str:
        """Obfuscate potentially sensitive line."""
        if len(text) <= 8:
            return "*" * len(text)
        return text[:4] + "*" * (len(text) - 8) + text[-4:]

# Singleton
_scanner = None

def get_secret_scanner() -> SecretScanner:
    global _scanner
    if _scanner is None:
        _scanner = SecretScanner()
    return _scanner
