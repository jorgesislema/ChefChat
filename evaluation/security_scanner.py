"""
Security Scanner Module

Escaneo de seguridad para prevenir:
- Inyección de código
- Filtración de datos (PII, API keys, secrets)
- Prompt injection
- Jailbreak attempts
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re
import hashlib


@dataclass
class SecurityAlert:
    """Alerta de seguridad."""
    severity: str  # critical, high, medium, low
    alert_type: str  # code_injection, data_leak, prompt_injection, jailbreak
    description: str
    detected_content: str
    position: Optional[Tuple[int, int]] = None
    recommendation: str = ""


class SecurityScanner:
    """Escáner de seguridad para ChefChat Pro."""
    
    # Patrones de inyección de código
    CODE_INJECTION_PATTERNS = [
        (r"__import__\s*\(", "Python import injection"),
        (r"eval\s*\(", "Python eval injection"),
        (r"exec\s*\(", "Python exec injection"),
        (r"compile\s*\(", "Python compile injection"),
        (r"os\.system\s*\(", "OS command injection"),
        (r"subprocess\.", "Subprocess injection"),
        (r"shell\s*=", "Shell injection"),
        (r"<script[^>]*>", "XSS script injection"),
        (r"javascript:", "JavaScript injection"),
        (r"{{.*}}", "Template injection"),
        (r"\$\{.*\}", "Expression injection"),
        (r";\s*DROP\s+TABLE", "SQL injection"),
        (r";\s*DELETE\s+FROM", "SQL injection"),
        (r"UNION\s+SELECT", "SQL injection"),
        (r"'\s*OR\s+'1'\s*=\s*'1", "SQL injection"),
    ]
    
    # Patrones de filtración de datos
    DATA_LEAK_PATTERNS = [
        (r"api[_-]?key['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}", "API Key"),
        (r"sk-[A-Za-z0-9]{20,}", "OpenAI API Key"),
        (r"ghp_[A-Za-z0-9]{36}", "GitHub Personal Access Token"),
        (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "Private Key"),
        (r"-----BEGIN\s+CERTIFICATE-----", "Certificate"),
        (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}", "Email (PII)"),
        (r"\b\d{3}-\d{2}-\d{4}\b", "SSN (PII)"),
        (r"\b\d{16}\b", "Credit Card Number (PII)"),
        (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "Credit Card (PII)"),
        (r"password['\"]?\s*[:=]\s*['\"]?[^\s'\"]{6,}", "Password"),
        (r"secret['\"]?\s*[:=]\s*['\"]?[^\s'\"]{8,}", "Secret"),
        (r"token['\"]?\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}", "Token"),
        (r"bearer\s+[A-Za-z0-9_\-\.]+", "Bearer Token"),
    ]
    
    # Patrones de prompt injection
    PROMPT_INJECTION_PATTERNS = [
        (r"ignore\s+(previous|all)\s+(instructions|rules)", "Prompt injection: ignore rules"),
        (r"forget\s+(previous|all)\s+(instructions|rules)", "Prompt injection: forget rules"),
        (r"you\s+are\s+now\s+(in\s+)?(developer|debug|test)\s+mode", "Jailbreak: mode switch"),
        (r"act\s+as\s+(another\s+)?(ai|assistant|model)", "Jailbreak: role play"),
        (r"bypass\s+(security|filters|restrictions)", "Security bypass attempt"),
        (r"what\s+(would|if)\s+you\s+do\s+if", "Hypothetical jailbreak"),
        (r"print\s+your\s+(system|prompt)\s+(message|instruction)", "System prompt extraction"),
        (r"show\s+me\s+your\s+(initial|system)\s+(prompt|instructions)", "System prompt extraction"),
        (r"repeat\s+the\s+words\s+above", "Prompt extraction"),
        (r"output\s+your\s+(configuration|settings|prompt)", "Configuration extraction"),
    ]
    
    def __init__(self):
        self.alerts: List[SecurityAlert] = []
        self.compiled_code_patterns = [
            (re.compile(pattern, re.IGNORECASE), desc)
            for pattern, desc in self.CODE_INJECTION_PATTERNS
        ]
        self.compiled_leak_patterns = [
            (re.compile(pattern, re.IGNORECASE), desc)
            for pattern, desc in self.DATA_LEAK_PATTERNS
        ]
        self.compiled_prompt_patterns = [
            (re.compile(pattern, re.IGNORECASE), desc)
            for pattern, desc in self.PROMPT_INJECTION_PATTERNS
        ]
    
    def scan_input(self, user_input: str) -> List[SecurityAlert]:
        """
        Escanea entrada de usuario en busca de amenazas.
        
        Args:
            user_input: Texto de entrada del usuario
            
        Returns:
            Lista de alertas de seguridad encontradas
        """
        self.alerts = []
        
        # Escanear inyección de código
        self._scan_for_pattern(
            user_input,
            self.compiled_code_patterns,
            "code_injection",
            "critical",
        )
        
        # Escanear prompt injection
        self._scan_for_pattern(
            user_input,
            self.compiled_prompt_patterns,
            "prompt_injection",
            "high",
        )
        
        return self.alerts
    
    def scan_output(self, output: str) -> List[SecurityAlert]:
        """
        Escanea salida del modelo en busca de filtración de datos.
        
        Args:
            output: Texto de salida del modelo
            
        Returns:
            Lista de alertas de seguridad encontradas
        """
        self.alerts = []
        
        # Escanear filtración de datos
        self._scan_for_pattern(
            output,
            self.compiled_leak_patterns,
            "data_leak",
            "critical",
        )
        
        return self.alerts
    
    def scan_full_interaction(
        self,
        user_input: str,
        model_output: str,
    ) -> Dict[str, Any]:
        """
        Escanea interacción completa (input + output).
        
        Args:
            user_input: Entrada del usuario
            model_output: Salida del modelo
            
        Returns:
            Diccionario con resultados del escaneo
        """
        input_alerts = self.scan_input(user_input)
        output_alerts = self.scan_output(model_output)
        
        all_alerts = input_alerts + output_alerts
        
        risk_score = self._calculate_risk_score(all_alerts)
        
        return {
            "safe": len(all_alerts) == 0,
            "risk_score": risk_score,  # 0-100
            "total_alerts": len(all_alerts),
            "input_alerts": [self._alert_to_dict(a) for a in input_alerts],
            "output_alerts": [self._alert_to_dict(a) for a in output_alerts],
            "recommendation": self._get_recommendation(all_alerts),
        }
    
    def _scan_for_pattern(
        self,
        text: str,
        patterns: List[Tuple[re.Pattern, str]],
        alert_type: str,
        default_severity: str,
    ) -> None:
        """Escanea texto buscando patrones específicos."""
        for pattern, description in patterns:
            matches = pattern.finditer(text)
            for match in matches:
                severity = default_severity
                
                # Ajustar severidad basada en el tipo de patrón
                if "SQL" in description:
                    severity = "critical"
                elif "API Key" in description or "Password" in description:
                    severity = "critical"
                elif "XSS" in description:
                    severity = "high"
                
                alert = SecurityAlert(
                    severity=severity,
                    alert_type=alert_type,
                    description=description,
                    detected_content=match.group()[:100],  # Truncar
                    position=(match.start(), match.end()),
                    recommendation=self._get_recommendation_for_type(alert_type),
                )
                self.alerts.append(alert)
    
    def _calculate_risk_score(self, alerts: List[SecurityAlert]) -> int:
        """Calcula score de riesgo 0-100 basado en alertas."""
        if not alerts:
            return 0
        
        severity_weights = {
            "critical": 40,
            "high": 25,
            "medium": 10,
            "low": 5,
        }
        
        total_score = sum(
            severity_weights.get(alert.severity, 5)
            for alert in alerts
        )
        
        return min(100, total_score)
    
    def _get_recommendation_for_type(self, alert_type: str) -> str:
        """Obtiene recomendación basada en tipo de alerta."""
        recommendations = {
            "code_injection": "Bloquear entrada y registrar intento de inyección. Revisar logs de seguridad.",
            "data_leak": "Enmascarar datos sensibles antes de mostrar. Revisar política de privacidad.",
            "prompt_injection": "Rechazar entrada y recordar al usuario las políticas de uso. Monitorear patrón.",
            "jailbreak": "Rechazar entrada firmemente. Registrar intento y considerar bloqueo temporal.",
        }
        return recommendations.get(alert_type, "Revisar manualmente y tomar acción apropiada.")
    
    def _get_recommendation(self, alerts: List[SecurityAlert]) -> str:
        """Obtiene recomendación general basada en alertas."""
        if not alerts:
            return "No se detectaron amenazas. Interacción segura."
        
        critical_alerts = [a for a in alerts if a.severity == "critical"]
        high_alerts = [a for a in alerts if a.severity == "high"]
        
        if critical_alerts:
            return "⚠️ AMENAZA CRÍTICA DETECTADA. Bloquear interacción inmediatamente."
        elif high_alerts:
            return "⚠️ AMENAZA ALTA DETECTADA. Revisar y validar antes de continuar."
        else:
            return "⚠️ AMENAZAS MENORES DETECTADAS. Monitorear interacción."
    
    def _alert_to_dict(self, alert: SecurityAlert) -> Dict[str, Any]:
        """Convierte alerta a diccionario."""
        return {
            "severity": alert.severity,
            "alert_type": alert.alert_type,
            "description": alert.description,
            "detected_content": alert.detected_content,
            "recommendation": alert.recommendation,
        }
    
    def redact_sensitive_data(self, text: str) -> str:
        """
        Enmascara datos sensibles en texto.
        
        Args:
            text: Texto que puede contener datos sensibles
            
        Returns:
            Texto con datos sensibles enmascarados
        """
        result = text
        
        # Enmascarar API keys
        result = re.sub(
            r"(api[_-]?key['\"]?\s*[:=]\s*['\"]?)[A-Za-z0-9_\-]{20,}",
            r"\1[REDACTED]",
            result,
            flags=re.IGNORECASE,
        )
        
        # Enmascarar emails
        result = re.sub(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}",
            "[EMAIL_REDACTED]",
            result,
        )
        
        # Enmascarar números de tarjeta
        result = re.sub(
            r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
            "XXXX-XXXX-XXXX-XXXX",
            result,
        )
        
        # Enmascarar contraseñas
        result = re.sub(
            r"(password['\"]?\s*[:=]\s*['\"]?)[^\s'\"]{6,}",
            r"\1[REDACTED]",
            result,
            flags=re.IGNORECASE,
        )
        
        return result
    
    def get_security_report(self) -> Dict[str, Any]:
        """Genera reporte de seguridad."""
        if not self.alerts:
            return {
                "status": "clean",
                "total_alerts": 0,
                "alerts_by_type": {},
                "alerts_by_severity": {},
            }
        
        alerts_by_type: Dict[str, int] = {}
        alerts_by_severity: Dict[str, int] = {}
        
        for alert in self.alerts:
            alerts_by_type[alert.alert_type] = alerts_by_type.get(alert.alert_type, 0) + 1
            alerts_by_severity[alert.severity] = alerts_by_severity.get(alert.severity, 0) + 1
        
        return {
            "status": "alerts_found",
            "total_alerts": len(self.alerts),
            "alerts_by_type": alerts_by_type,
            "alerts_by_severity": alerts_by_severity,
            "risk_score": self._calculate_risk_score(self.alerts),
            "details": [self._alert_to_dict(a) for a in self.alerts],
        }
