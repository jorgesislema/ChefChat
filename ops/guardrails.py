"""
Guardrails y Seguridad para ChefChat Pro

Defensas contra:
- Inyección de prompts
- Inputs maliciosos o excesivos
- Límites de uso (rate limiting)
- Validación de contenido
"""

import re
import time
import logging
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum


class ThreatLevel(Enum):
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


@dataclass
class ValidationResult:
    is_valid: bool
    threat_level: ThreatLevel
    sanitized_input: str
    warnings: List[str] = field(default_factory=list)
    blocked_reason: Optional[str] = None


class PromptInjectionDetector:
    """Detecta intentos de inyección de prompts."""

    INJECTION_PATTERNS = [
        r"ignore\s+(previous|all|above)\s+(instructions?|prompts?|rules?)",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"forget\s+(everything|all|previous)",
        r"new\s+instructions?:",
        r"system\s*:\s*",
        r"<\|system\|>",
        r"<\|im_start\|>",
        r"INST\s*\]",
        r"\[\/INST\]",
        r"Human:\s*",
        r"Assistant:\s*",
        r"act\s+as\s+(a|an)\s+",
        r"pretend\s+(you|to)\s+(are|be)",
        r"roleplay\s+as",
        r"jailbreak",
        r"DAN\s+mode",
        r"developer\s+mode",
        r"bypass\s+(safety|filters?|restrictions?)",
        r"override\s+(safety|system)",
        r"disregard\s+(previous|all|safety)",
    ]

    SUSPICIOUS_PATTERNS = [
        r"repeat\s+(after\s+me|this|the\s+following)",
        r"say\s+(exactly|precisely|the\s+following)",
        r"output\s+(the\s+following|this\s+exact)",
        r"translate\s+(to|into)\s+(base64|hex|binary|rot13)",
        r"encode\s+(this|the\s+following)\s+(as|in)",
        r"decode\s+(this|the\s+following)",
        r"execute\s+(this|the\s+following|code)",
        r"run\s+(this|the\s+following)\s+(command|code|script)",
        r"eval\s*\(",
        r"exec\s*\(",
        r"__import__",
        r"subprocess",
        r"os\.system",
        r"shell\s*=\s*True",
    ]

    def detect(self, text: str) -> ThreatLevel:
        text_lower = text.lower()

        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logging.warning("INJECTION DETECTED: pattern=%s, text=%s", pattern, text[:100])
                return ThreatLevel.BLOCKED

        for pattern in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logging.warning("SUSPICIOUS PATTERN: pattern=%s, text=%s", pattern, text[:100])
                return ThreatLevel.SUSPICIOUS

        return ThreatLevel.SAFE


class InputValidator:
    """Valida y sanitiza inputs del usuario."""

    MAX_INPUT_LENGTH = 5000
    MAX_WORD_COUNT = 500

    def validate(self, text: str) -> ValidationResult:
        warnings = []

        if not text or not text.strip():
            return ValidationResult(
                is_valid=False,
                threat_level=ThreatLevel.SAFE,
                sanitized_input="",
                blocked_reason="Input vacío"
            )

        if len(text) > self.MAX_INPUT_LENGTH:
            text = text[:self.MAX_INPUT_LENGTH]
            warnings.append(f"Input truncado a {self.MAX_INPUT_LENGTH} caracteres")

        word_count = len(text.split())
        if word_count > self.MAX_WORD_COUNT:
            words = text.split()[:self.MAX_WORD_COUNT]
            text = " ".join(words)
            warnings.append(f"Input truncado a {self.MAX_WORD_COUNT} palabras")

        sanitized = self._sanitize(text)

        return ValidationResult(
            is_valid=True,
            threat_level=ThreatLevel.SAFE,
            sanitized_input=sanitized,
            warnings=warnings
        )

    def _sanitize(self, text: str) -> str:
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
        return text.strip()


class RateLimiter:
    """Limita la frecuencia de peticiones por usuario."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[float]] = {}

    def check_limit(self, user_id: str = "default") -> bool:
        now = time.time()
        if user_id not in self.requests:
            self.requests[user_id] = []

        self.requests[user_id] = [
            t for t in self.requests[user_id]
            if now - t < self.window_seconds
        ]

        if len(self.requests[user_id]) >= self.max_requests:
            logging.warning("RATE LIMIT: user=%s, requests=%d", user_id, len(self.requests[user_id]))
            return False

        self.requests[user_id].append(now)
        return True

    def get_remaining(self, user_id: str = "default") -> int:
        now = time.time()
        if user_id not in self.requests:
            return self.max_requests
        recent = [t for t in self.requests[user_id] if now - t < self.window_seconds]
        return max(0, self.max_requests - len(recent))


class ContentFilter:
    """Filtra contenido sensible en respuestas."""

    SENSITIVE_PATTERNS = [
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
    ]

    def filter_response(self, text: str) -> str:
        for pattern in self.SENSITIVE_PATTERNS:
            text = re.sub(pattern, "[FILTRADO]", text)
        return text


class Guardrails:
    """Sistema principal de guardrails para ChefChat Pro."""

    def __init__(self, rate_limit: int = 30, rate_window: int = 60):
        self.injection_detector = PromptInjectionDetector()
        self.input_validator = InputValidator()
        self.rate_limiter = RateLimiter(max_requests=rate_limit, window_seconds=rate_window)
        self.content_filter = ContentFilter()

    def validate_input(self, text: str, user_id: str = "default") -> ValidationResult:
        """Valida completo del input del usuario."""

        injection_result = self.injection_detector.detect(text)
        if injection_result == ThreatLevel.BLOCKED:
            return ValidationResult(
                is_valid=False,
                threat_level=ThreatLevel.BLOCKED,
                sanitized_input="",
                blocked_reason="Input bloqueado: posible inyección de prompt detectada"
            )

        if not self.rate_limiter.check_limit(user_id):
            remaining = self.rate_limiter.get_remaining(user_id)
            return ValidationResult(
                is_valid=False,
                threat_level=ThreatLevel.BLOCKED,
                sanitized_input="",
                blocked_reason=f"Límite de peticiones alcanzado. Intenta en {self.rate_limiter.window_seconds} segundos. Restantes: {remaining}"
            )

        validation = self.input_validator.validate(text)
        if not validation.is_valid:
            return validation

        if injection_result == ThreatLevel.SUSPICIOUS:
            validation.warnings.append("Input sospechoso: monitoreado")

        return validation

    def filter_response(self, text: str) -> str:
        """Filtra contenido sensible de la respuesta."""
        return self.content_filter.filter_response(text)
