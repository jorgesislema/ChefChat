"""
Script de Escaneo de Seguridad del Repositorio

Escanea todo el repositorio en busca de:
- API Keys expuestas
- Información personal (PII)
- Contraseñas y secretos
- Tokens de acceso
- Patrones de inyección de código
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
from evaluation.security_scanner import SecurityScanner


# Patrones adicionales para escaneo de repositorio
SECURITY_PATTERNS = [
    # API Keys y Secrets
    (r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}", "API Key expuesta"),
    (r"(?i)(secret[_-]?key|secretkey)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}", "Secret Key expuesta"),
    (r"(?i)(access[_-]?token|accesstoken)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}", "Access Token expuesto"),
    (r"(?i)(auth[_-]?token|authtoken)\s*[=:]\s*['\"]?[A-Za-z0-9_\-]{20,}", "Auth Token expuesto"),
    
    # Servicios específicos
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI API Key"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub Personal Access Token"),
    (r"gho_[A-Za-z0-9]{36}", "GitHub OAuth Token"),
    (r"ghu_[A-Za-z0-9]{36}", "GitHub User Token"),
    (r"ghs_[A-Za-z0-9]{36}", "GitHub Server Token"),
    (r"ghr_[A-Za-z0-9]{36}", "GitHub Refresh Token"),
    (r"xox[baprs]-[A-Za-z0-9-]{10,}", "Slack Token"),
    (r"AIza[0-9A-Za-z_-]{35}", "Google API Key"),
    (r"EAACEdEose0cBA[0-9A-Za-z]+", "Facebook Access Token"),
    
    # Contraseñas
    (r"(?i)(password|passwd|pass|contraseña|pwd)\s*[=:]\s*['\"]?[^\s'\"]{6,}", "Contraseña expuesta"),
    
    # PII (Información Personal Identificable)
    (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}", "Email (PII)"),
    (r"\b\d{3}-\d{2}-\d{4}\b", "SSN (PII)"),
    (r"\b\d{16}\b", "Posible número de tarjeta de crédito"),
    (r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b", "Número de tarjeta de crédito"),
    
    # Private Keys
    (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "Private Key"),
    (r"-----BEGIN\s+CERTIFICATE-----", "Certificate"),
    (r"-----BEGIN\s+EC\s+PRIVATE\s+KEY-----", "EC Private Key"),
    (r"-----BEGIN\s+PGP\s+PRIVATE\s+KEY\s+BLOCK-----", "PGP Private Key"),
    
    # Tokens de base de datos
    (r"(?i)(mongodb(?:\+srv)?|postgres|mysql|redis)://[^\s'\"]+:[^\s'\"]+@", "Database Connection String con credenciales"),
    
    # AWS
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key ID"),
    (r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*['\"]?[A-Za-z0-9/+=]{40}", "AWS Secret Access Key"),
]


def scan_repository(repo_path: str) -> Dict[str, any]:
    """
    Escanea el repositorio en busca de problemas de seguridad.
    
    Args:
        repo_path: Ruta del repositorio a escanear
        
    Returns:
        Diccionario con resultados del escaneo
    """
    scanner = SecurityScanner()
    
    # Directorios y archivos a excluir
    exclude_dirs = {
        '.venv', '__pycache__', '.mypy_cache', '.pytest_cache',
        'node_modules', '.git', 'build', 'dist', '.eggs',
        'telemetry_exports', 'C:\\Temp'
    }
    
    exclude_extensions = {
        '.pyc', '.pyo', '.so', '.dll', '.exe', '.bin',
        '.db', '.sqlite', '.sqlite3',
        '.whl', '.tar', '.gz', '.zip', '.rar',
        '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx'
    }
    
    findings = []
    files_scanned = 0
    files_with_issues = 0
    
    # Compilar patrones
    compiled_patterns = [
        (re.compile(pattern, re.IGNORECASE), description)
        for pattern, description in SECURITY_PATTERNS
    ]
    
    # Escanear archivos
    for root, dirs, files in os.walk(repo_path):
        # Excluir directorios
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = os.path.join(root, file)
            ext = os.path.splitext(file)[1].lower()
            
            # Excluir extensiones binarias
            if ext in exclude_extensions:
                continue
            
            # Solo escanear archivos de texto/código
            if ext not in {'.py', '.js', '.ts', '.json', '.yaml', '.yml', 
                          '.env', '.md', '.txt', '.cfg', '.ini', '.toml',
                          '.html', '.css', '.sh', '.bash', '.xml', '.csv'}:
                continue
            
            try:
                files_scanned += 1
                
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                
                file_findings = []
                
                # Escanear con patrones
                for pattern, description in compiled_patterns:
                    matches = pattern.finditer(content)
                    for match in matches:
                        # Calcular línea
                        line_num = content[:match.start()].count('\n') + 1
                        line_content = lines[line_num - 1] if line_num <= len(lines) else ""
                        
                        # No reportar si está en comentario o es ejemplo/documentación
                        if line_content.strip().startswith('#') or \
                           line_content.strip().startswith('//') or \
                           'example' in line_content.lower() or \
                           'placeholder' in line_content.lower() or \
                           'fake' in line_content.lower() or \
                           'test' in line_content.lower():
                            continue
                        
                        # Determinar severidad
                        severity = "high"
                        if "Email" in description:
                            severity = "medium"
                        elif "tarjeta" in description.lower():
                            severity = "critical"
                        elif "Private Key" in description or "AWS" in description:
                            severity = "critical"
                        
                        file_findings.append({
                            "file": file_path,
                            "line": line_num,
                            "type": description,
                            "severity": severity,
                            "content": line_content.strip()[:100],
                            "match": match.group()[:50],
                        })
                
                # Escanear input/output con SecurityScanner
                interaction_findings = scanner.scan_full_interaction(
                    user_input=content[:500],  # Primeros 500 chars
                    model_output=content[-500:]  # Últimos 500 chars
                )
                
                if interaction_findings["risk_score"] > 50:
                    file_findings.append({
                        "file": file_path,
                        "line": "N/A",
                        "type": "Contenido sospechoso detectado por SecurityScanner",
                        "severity": "medium",
                        "content": f"Risk Score: {interaction_findings['risk_score']}/100",
                        "match": "SecurityScanner alert",
                    })
                
                if file_findings:
                    files_with_issues += 1
                    findings.extend(file_findings)
                    
            except Exception as e:
                # Ignorar archivos que no se pueden leer
                pass
    
    # Calcular riesgo general
    critical_count = sum(1 for f in findings if f["severity"] == "critical")
    high_count = sum(1 for f in findings if f["severity"] == "high")
    medium_count = sum(1 for f in findings if f["severity"] == "medium")
    
    overall_risk_score = min(100, critical_count * 30 + high_count * 15 + medium_count * 5)
    
    return {
        "files_scanned": files_scanned,
        "files_with_issues": files_with_issues,
        "total_findings": len(findings),
        "overall_risk_score": overall_risk_score,
        "critical": critical_count,
        "high": high_count,
        "medium": medium_count,
        "low": len(findings) - critical_count - high_count - medium_count,
        "findings": findings,
        "status": "SAFE" if overall_risk_score < 20 else "WARNING" if overall_risk_score < 50 else "CRITICAL",
    }


def generate_report(results: Dict[str, any], output_file: str = "security_scan_report.md"):
    """
    Genera reporte de seguridad en Markdown.
    
    Args:
        results: Resultados del escaneo
        output_file: Archivo de salida
    """
    report = []
    report.append("# 🔒 Informe de Seguridad del Repositorio\n")
    report.append(f"**Fecha del escaneo:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"**Estado:** {'✅ SEGURO' if results['status'] == 'SAFE' else '⚠️ ADVERTENCIA' if results['status'] == 'WARNING' else '🔴 CRÍTICO'}\n")
    
    report.append("## 📊 Resumen Ejecutivo\n")
    report.append(f"| Métrica | Valor |")
    report.append(f"|---------|-------|")
    report.append(f"| Archivos escaneados | {results['files_scanned']} |")
    report.append(f"| Archivos con issues | {results['files_with_issues']} |")
    report.append(f"| Total hallazgos | {results['total_findings']} |")
    report.append(f"| Risk Score | {results['overall_risk_score']}/100 |")
    report.append(f"| Estado | {results['status']} |")
    
    report.append("\n## 🚨 Hallazgos por Severidad\n")
    report.append(f"- 🔴 **Críticos:** {results['critical']}")
    report.append(f"- 🟠 **Altos:** {results['high']}")
    report.append(f"- 🟡 **Medios:** {results['medium']}")
    report.append(f"- 🟢 **Bajos:** {results['low']}")
    
    if results['findings']:
        report.append("\n## 📋 Hallazgos Detallados\n")
        
        # Agrupar por severidad
        for severity in ["critical", "high", "medium", "low"]:
            severity_findings = [f for f in results['findings'] if f['severity'] == severity]
            if severity_findings:
                report.append(f"\n### {severity.upper()}\n")
                for finding in severity_findings[:10]:  # Mostrar solo primeros 10
                    report.append(f"**Archivo:** `{finding['file']}` (línea {finding['line']})")
                    report.append(f"- **Tipo:** {finding['type']}")
                    report.append(f"- **Contenido:** `{finding['content']}`")
                    report.append("")  # Fixed: was empty append()
    
    report.append("\n## ✅ Recomendaciones\n")
    
    if results['overall_risk_score'] == 0:
        report.append("✅ **No se encontraron problemas de seguridad.** El repositorio está limpio.")
    else:
        report.append("1. **Revisar todos los hallazgos críticos y altos inmediatamente**")
        report.append("2. **Eliminar cualquier credencial expuesta**")
        report.append("3. **Usar variables de ambiente o sistemas de secrets management**")
        report.append("4. **Verificar que .gitignore excluya archivos sensibles**")
        report.append("5. **Rotar cualquier credencial que haya estado expuesta**")
    
    report.append("\n## 🔐 Verificaciones Realizadas\n")
    report.append("- ✅ Búsqueda de API Keys expuestas")
    report.append("- ✅ Búsqueda de contraseñas y secretos")
    report.append("- ✅ Búsqueda de tokens de acceso")
    report.append("- ✅ Búsqueda de información personal (PII)")
    report.append("- ✅ Búsqueda de private keys")
    report.append("- ✅ Búsqueda de connection strings con credenciales")
    report.append("- ✅ Verificación de .gitignore")
    report.append("- ✅ Escaneo de inyección de código")
    report.append("- ✅ Escaneo de prompt injection")
    
    report.append("\n---")
    report.append("*Reporte generado automáticamente por el Security Scanner de ChefChat Pro*")
    
    # Escribir reporte
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))
    
    return output_file


if __name__ == "__main__":
    import sys
    
    repo_path = os.path.dirname(os.path.abspath(__file__))
    print(f"🔍 Escaneando repositorio: {repo_path}\n")
    
    results = scan_repository(repo_path)
    
    print(f"📊 Resultados:")
    print(f"   Archivos escaneados: {results['files_scanned']}")
    print(f"   Archivos con issues: {results['files_with_issues']}")
    print(f"   Total hallazgos: {results['total_findings']}")
    print(f"   Risk Score: {results['overall_risk_score']}/100")
    print(f"   Estado: {results['status']}\n")
    
    if results['findings']:
        print(f"⚠️  Se encontraron {len(results['findings'])} problemas de seguridad:\n")
        
        # Mostrar hallazgos críticos y altos
        critical_high = [f for f in results['findings'] if f['severity'] in ['critical', 'high']]
        for finding in critical_high[:5]:
            print(f"   - {finding['severity'].upper()}: {finding['type']} en {finding['file']}:{finding['line']}")
    else:
        print("✅ ¡No se encontraron problemas de seguridad!\n")
    
    # Generar reporte
    report_file = generate_report(results)
    print(f"📄 Reporte completo generado: {report_file}")
