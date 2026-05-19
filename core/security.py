import re
from typing import Optional


class SecurityValidator:
    @staticmethod
    def sanitize_log_message(message: str) -> str:
        patterns_to_redact = [
            r"(api[_-]?key['\"]?\s*[:=]\s*)['\"]?[A-Za-z0-9_\-]{20,}['\"]?",
            r"(bearer\s+)[A-Za-z0-9_\-\.]+",
            r"(sk\-)[A-Za-z0-9_\-]{20,}",
        ]
        result = message
        for pattern in patterns_to_redact:
            result = re.sub(pattern, r"\1[REDACTED]", result, flags=re.IGNORECASE)
        return result

    @staticmethod
    def validate_no_pii(text: str) -> bool:
        email_pattern = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}"
        if re.search(email_pattern, text):
            return False
        return True