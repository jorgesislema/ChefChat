"""
Script de Verificación Inicial para ChefChat Pro

Verifica:
1. Dependencias instaladas
2. API keys configuradas
3. Base de datos existente
4. Permisos de escritura
5. Seguridad del sistema
"""

import sys
import os
from pathlib import Path


def print_header(text: str):
    print("\n" + "="*60)
    print(f" {text}")
    print("="*60)


def check_dependencies():
    """Verifica dependencias críticas."""
    print_header("VERIFICANDO DEPENDENCIAS")
    
    dependencies = {
        "PyQt6": "Interfaz gráfica",
        "langchain": "Framework LLM",
        "langchain-openai": "Integración OpenAI",
        "pydantic": "Validación de datos",
        "keyring": "Gestión de secrets",
        "pytest": "Tests",
    }
    
    all_ok = True
    for package, description in dependencies.items():
        try:
            __import__(package.replace("-", "_"))
            print(f"  [OK] {package:20} - {description}")
        except ImportError:
            print(f"  [ERROR] {package:20} - {description} - FALTA!")
            all_ok = False
    
    return all_ok


def check_api_keys():
    """Verifica si hay API keys configuradas."""
    print_header("API KEYS CONFIGURADAS")
    
    try:
        from core.config import ConfigManager, AIProvider
        
        providers = {
            AIProvider.OPENROUTER: "OpenRouter (MiniMax, GPT)",
            AIProvider.OPENAI: "OpenAI (GPT-4)",
            AIProvider.DEEPSEEK: "DeepSeek",
            AIProvider.GEMINI: "Google Gemini",
            AIProvider.CLAUDE: "Claude (Anthropic)",
            AIProvider.OPENCODE: "OpenCode (GRATIS)",
        }
        
        configured = []
        not_configured = []
        
        for provider, name in providers.items():
            api_key = ConfigManager.get_api_key(provider)
            if api_key:
                # Mostrar solo primeros y últimos caracteres
                key_preview = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
                print(f"  [OK] {name:30} - Configurada ({key_preview})")
                configured.append(provider)
            else:
                print(f"  [!] {name:30} - No configurada")
                not_configured.append(provider)
        
        if configured:
            print(f"\n  [OK] Proveedores configurados: {len(configured)}")
            return True
        else:
            print(f"\n  [!] No hay API keys configuradas")
            print(f"  [i] Usa OpenCode (GRATIS) o configura una API key")
            return False
            
    except Exception as e:
        print(f"  [ERROR] Error verificando API keys: {e}")
        return False


def check_database():
    """Verifica base de datos."""
    print_header("BASE DE DATOS")
    
    db_path = Path("chefchat.db")
    if db_path.exists():
        size = db_path.stat().st_size
        print(f"  [OK] chefchat.db existe ({size/1024:.1f} KB)")
        
        # Verificar tablas
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            print(f"  [OK] Tablas encontradas: {len(tables)}")
            for table in tables[:5]:  # Mostrar primeras 5
                print(f"     - {table}")
            if len(tables) > 5:
                print(f"     ... y {len(tables)-5} mas")
            
            return True
        except Exception as e:
            print(f"  [!] Error leyendo base de datos: {e}")
            return False
    else:
        print(f"  [!] chefchat.db no existe")
        print(f"  [i] Se creara automaticamente al cargar recetas")
        return True  # No es crítico


def check_permissions():
    """Verifica permisos de escritura."""
    print_header("PERMISOS")
    
    test_dir = Path("C:\\Temp\\ChefChat_Sandbox")
    try:
        test_dir.mkdir(parents=True, exist_ok=True)
        test_file = test_dir / "test_permissions.txt"
        test_file.write_text("test")
        test_file.unlink()
        print(f"  [OK] Escritura en sandbox: OK")
        return True
    except Exception as e:
        print(f"  [ERROR] Error de permisos: {e}")
        return False


def check_security():
    """Verifica seguridad del sistema."""
    print_header("SEGURIDAD")
    
    # Verificar .gitignore
    gitignore_path = Path(".gitignore")
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        sensitive_files = [".env", "*.log", "logs/", "ChefChat_Sandbox"]
        
        print(f"  [OK] .gitignore existe")
        
        for sensitive in sensitive_files:
            if sensitive in content:
                print(f"     [OK] Excluye: {sensitive}")
            else:
                print(f"     [!] No excluye: {sensitive}")
    else:
        print(f"  [!] .gitignore no existe")
    
    # Verificar archivos sensibles
    print(f"\n  [i] Escaneando archivos sensibles...")
    sensitive_found = False
    
    for pattern in ["*.env", "*.key", "*.secret"]:
        for file in Path(".").rglob(pattern):
            if ".venv" not in str(file):
                print(f"  [!] Archivo sensible encontrado: {file}")
                sensitive_found = True
    
    if not sensitive_found:
        print(f"  [OK] No se encontraron archivos sensibles expuestos")
    
    return not sensitive_found


def show_recommendations(has_api_key: bool):
    """Muestra recomendaciones."""
    print_header("RECOMENDACIONES")
    
    if not has_api_key:
        print("  [!] No tienes API keys configuradas")
        print("\n  [GRATIS] Opcion GRATIS:")
        print("     1. Ejecuta: python main.py")
        print("     2. Selecciona proveedor: OpenCode")
        print("     3. Modelo: big-pickle")
        print("     4. Listo! No requiere API key")
        print("\n  [PREMIUM] Opcion PREMIUM (recomendada):")
        print("     1. Ve a: https://openrouter.ai/")
        print("     2. Crea cuenta (gratis)")
        print("     3. Agrega $5 USD de credito")
        print("     4. Copia tu API key")
        print("     5. Configurala en ChefChat")
    else:
        print("  [OK] Tienes API keys configuradas")
        print("  [i] Ya puedes usar ChefChat Pro!")
    
    print("\n  [DOC] Documentacion:")
    print("     - CONFIGURACION_RAPIDA.md")
    print("     - SECURITY_REPORT.md")
    print("     - evaluation/README.md")


def main():
    """Ejecuta todas las verificaciones."""
    print("\n" + "V"*60)
    print(" CHEFCHAT PRO - VERIFICACION INICIAL")
    print("V"*60)
    
    # Ejecutar verificaciones
    deps_ok = check_dependencies()
    has_api_key = check_api_keys()
    db_ok = check_database()
    perms_ok = check_permissions()
    security_ok = check_security()
    
    # Mostrar recomendaciones
    show_recommendations(has_api_key)
    
    # Resumen final
    print_header("RESUMEN")
    
    checks = [
        ("Dependencias", deps_ok),
        ("API Keys", has_api_key),
        ("Base de Datos", db_ok),
        ("Permisos", perms_ok),
        ("Seguridad", security_ok),
    ]
    
    for name, ok in checks:
        status = "[OK]" if ok else "[!]"
        print(f"  {status} {name:20} - {'OK' if ok else 'REVISAR'}")
    
    all_ok = all(ok for _, ok in checks)
    
    print()
    if all_ok:
        print("  [OK] Todo esta listo! Ejecuta: python main.py")
    else:
        print("  [!] Hay items por revisar. Verifica arriba.")
    
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Verificacion cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Error durante la verificacion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
