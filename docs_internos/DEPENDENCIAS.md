# Dependencias Opcionales para ChefChat Pro

## Proveedores de IA

### DeepSeek (Recomendado ✅)
Ya está instalado. No requiere librerías adicionales.

### Google Gemini
```bash
pip install langchain-google-genai
```

### Claude (Anthropic)
```bash
pip install langchain-anthropic
```

### OpenAI
```bash
pip install langchain-openai
```

### OpenRouter
```bash
pip install langchain-openai
```

---

## Si la aplicación se congela:

1. **Verifica tu conexión a internet**
2. **Cambia de proveedor** en Configuración → API Keys
3. **Reduce el timeout** editando `gui/main_window.py:660`

---

## Recomendaciones:

- **DeepSeek**: Más económico, pero puede estar lento en horas pico
- **OpenRouter**: Mejor disponibilidad, múltiples modelos
- **Gemini**: Requiere librería adicional
- **Claude**: Mejor calidad, requiere librería adicional

---

## Para cargar documentos de capacitación:

1. Abre ChefChat Pro
2. Clic en "📚 Ingesta RAG"
3. Selecciona tus archivos .md
4. El sistema los guardará automáticamente
