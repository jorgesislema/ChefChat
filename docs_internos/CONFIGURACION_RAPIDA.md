# 🚀 Guía de Configuración - ChefChat Pro

## ⚡ Configuración Rápida (Primer Uso)

### Paso 1: Abrir la Aplicación
```bash
python main.py
```

### Paso 2: Configurar API Key

Al hacer tu **primera consulta**, se abrirá automáticamente el diálogo de configuración.

**O también puedes:**
- Hacer clic en el botón **⚙️** (Settings) en la esquina superior derecha
- O presionar la tecla de configuración (si está disponible)

### Paso 3: Seleccionar Proveedor

**Opciones recomendadas:**

| Proveedor | Modelos | Precio | Recomendado para |
|-----------|---------|--------|------------------|
| **OpenRouter** | MiniMax, GPT-4, Claude | Desde $0.10/1M tokens | ⭐ **Mejor opción** |
| **OpenCode** | Big Pickle, Open-Code-v1 | **GRATIS** 🆓 | Testing y desarrollo |
| **DeepSeek** | DeepSeek-Chat, Coder | $0.27/1M tokens | Código y recetas |
| **Google Gemini** | Gemini 1.5, 2.0 | $0.10/1M tokens | Multimodal |
| **OpenAI** | GPT-4, GPT-3.5 | $0.15-$5/1M tokens | Calidad premium |
| **Claude** | Claude 3.5, Opus | $3-$15/1M tokens | Texto largo |

### Paso 4: Ingresar API Key

**¿No tienes API key?**

#### Opción A: Usar OpenCode (GRATIS)
1. Selecciona proveedor: **OpenCode (Big Pickle 🆓)**
2. Modelo: **big-pickle** o **open-code-v1**
3. **No requiere API key** - ¡Es gratis!

#### Opción B: OpenRouter (Recomendado)
1. Ve a: https://openrouter.ai/
2. Crea una cuenta (gratis)
3. Genera una API key
4. Mínimo crédito: $5 USD
5. Copia tu API key (empieza con `sk-or-...`)

#### Opción C: Otros Proveedores
- **OpenAI**: https://platform.openai.com/api-keys
- **DeepSeek**: https://platform.deepseek.com/
- **Google Gemini**: https://makersuite.google.com/
- **Claude**: https://console.anthropic.com/

### Paso 5: Guardar y Usar

1. Pega tu API key en el campo correspondiente
2. Haz clic en **Guardar** 💾
3. ¡Listo! Ahora puedes hacer consultas

---

## 🛠️ Solución de Problemas

### Problema: "La aplicación se cierra al hacer una consulta"

**Causa:** API key no configurada o inválida

**Solución:**
1. Abre la configuración (⚙️)
2. Verifica que el proveedor seleccionado tenga una API key válida
3. Si usas OpenCode, selecciona ese proveedor (no requiere key)
4. Guarda y reintenta

### Problema: "Error de credenciales"

**Causa:** API key incorrecta o expirada

**Solución:**
1. Verifica que la API key esté correcta (sin espacios)
2. Renueva tu API key en el proveedor
3. Actualiza en Configuración

### Problema: "Timeout en las respuestas"

**Causa:** La consulta tardó más de 90 segundos

**Solución:**
1. Simplifica tu consulta
2. Usa modelos más rápidos (GPT-4o-mini, MiniMax)
3. Verifica tu conexión a internet

---

## 🎯 Comandos Útiles

### Verificar Tests
```bash
python -m pytest tests/ -v
```

### Escaneo de Seguridad
```bash
python security_scan.py
```

### Ejecutar con Debug
```bash
python main.py --debug
```

---

## 📞 Soporte

Si tienes problemas:

1. **Verifica logs** en `logs/` (si existen)
2. **Revisa la consola** para mensajes de error
3. **Ejecuta tests** para verificar instalación
4. **Consulta** `SECURITY_REPORT.md` para temas de seguridad

---

## 🔐 Seguridad

- ✅ Las API keys se guardan en **Windows Credential Manager** (encriptado)
- ✅ **No se guardan** en archivos de texto
- ✅ **No se commitean** a Git (.gitignore actualizado)
- ✅ **Sandbox** para operaciones de archivos

---

**Documentación generada para ChefChat Pro v1.0**  
*Última actualización: Mayo 2026*
