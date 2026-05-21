# ChefChat Pro v1.0 — Guia de Despliegue

## 1. Requisitos del Entorno

### 1.1 Hardware

| Componente | Minimo | Recomendado |
|------------|--------|-------------|
| CPU | 2 nucleos (x64) | 4 nucleos (x64) |
| RAM | 8 GB | 16 GB |
| Disco | 2 GB libres | 10 GB libres |
| SO | Windows 10 | Windows 11 |

### 1.2 Software

| Componente | Version | URL |
|------------|---------|-----|
| Python | 3.10+ | https://python.org |
| Git | 2.x | https://git-scm.com |
| Ollama (opcional) | Ultima | https://ollama.ai |
| Microsoft Office | 2016+ | Para integracion COM |

## 2. Instalacion desde Cero

### 2.1 Clonar Repositorio

```powershell
git clone <url-del-repositorio>
cd ChefChat
```

### 2.2 Entorno Virtual

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2.3 Instalar Dependencias

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.4 Dependencias Opcionales

```powershell
# Busqueda semantica FAISS
pip install faiss-cpu sentence-transformers

# Dashboard fallback (sin Excel COM)
pip install openpyxl matplotlib
```

### 2.5 Configurar Entorno

```powershell
copy .env.example .env
```

Editar `.env` con las API keys correspondientes.

### 2.6 Verificar Instalacion

```powershell
python scripts/check_setup.py
```

### 2.7 Poblar Datos Iniciales (Opcional)

```powershell
python scripts/data_seeder.py
```

### 2.8 Iniciar Aplicacion

```powershell
python main.py
```

## 3. Configuracion de Ollama (Opcional)

```powershell
# Instalar Ollama
# Descargar desde https://ollama.ai

# Iniciar servicio
ollama serve

# Descargar modelos
ollama pull llama3.2
ollama pull mistral

# Verificar
ollama list
```

## 4. Estructura de Archivos de Configuracion

```
ChefChat/
├── .env                    # Variables de entorno (NO COMMITEAR)
├── .env.example            # Plantilla de configuracion
├── .gitignore              # Archivos ignorados por git
├── chefchat.db             # Base de datos SQLite
├── requirements.txt        # Dependencias de Python
└── pyrightconfig.json      # Configuracion de type checker
```

## 5. Variables de Entorno

```ini
# === PROVEEDOR PRINCIPAL ===
CHEFCHAT_AI_PROVIDER=openrouter

# === API KEYS ===
CHEFCHAT_OPENROUTER_API_KEY=
CHEFCHAT_DEEPSEEK_API_KEY=
CHEFCHAT_GEMINI_API_KEY=
CHEFCHAT_CLAUDE_API_KEY=
CHEFCHAT_OPENAI_API_KEY=
CHEFCHAT_OPENCODE_API_KEY=

# === BASE DE DATOS ===
CHEFCHAT_DB_PATH=chefchat.db

# === RAG ===
CHEFCHAT_RAG_ONLY=true

# === DSPy OPTIMIZER ===
CHEFCHAT_USE_DSPY=true

# === LOGS ===
CHEFCHAT_LOG_LEVEL=INFO

# === SANDBOX ===
CHEFCHAT_SANDBOX_PATH=C:\Temp\ChefChat_Sandbox\
```

## 6. Verificacion Post-Instalacion

### 6.1 Pruebas Unitarias

```powershell
python -m pytest tests/ -v
```

**Resultado esperado**: 79 passed, 3 skipped, 2 errors

### 6.2 Pruebas de Integracion

```powershell
python -m pytest tests/test_mcp.py -v
python -m pytest tests/test_gui.py -v
```

### 6.3 Escaneo de Seguridad

```powershell
python scripts/security_scan.py
```

### 6.4 Diagnostico de API Keys

```powershell
python scripts/diagnose_keys.py
```

## 7. Actualizacion

```powershell
git pull origin main
.venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade
python scripts/check_setup.py
```

## 8. CI/CD (Recomendado)

### 8.1 GitHub Actions Workflow

```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: windows-latest
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.12'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    - name: Run tests
      run: |
        python -m pytest tests/ -v --ignore=tests/test_gui.py
```

### 8.2 Dependabot Configuration

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

## 9. Resolucion de Problemas de Instalacion

### 9.1 Error: pip install falla

```powershell
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### 9.2 Error: PyQt6 no se instala

```powershell
pip install PyQt6-sip PyQt6-Qt6 PyQt6
```

### 9.3 Error: modulo no encontrado

Verificar que el entorno virtual esta activado:
```powershell
.venv\Scripts\Activate.ps1
python -c "import sys; print(sys.path)"
```

### 9.4 Error: Base de datos corrupta

```powershell
# Respaldar base de datos actual
copy chefchat.db chefchat.db.bak

# Eliminar y recrear
del chefchat.db
python main.py  # Se crea automaticamente

# Si hay datos semilla
python scripts/data_seeder.py
```

---

*Documento generado para ChefChat Pro v1.0 — Mayo 2026*
