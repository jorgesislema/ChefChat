"""
Test para detección de menús por ingredientes
"""

test_messages = [
    "elabora el menu para el dia de mañana desayuno almuerso y merienda que llebe fresas chocolate pollo",
    "crea un menu con pollo fresas y chocolate",
    "sugiere un menu que tenga pollo arroz y verduras",
    "haz un menu para hoy con lo que haya",
    "arma un menu con fresas, chocolate, pollo",
]

print("="*60)
print(" TEST: Detección de Menús por Ingredientes")
print("="*60)

for message in test_messages:
    print(f"\nMensaje: '{message}'")
    
    # Verificar detección de menú
    es_menu = any(p in message for p in ["menú", "menu", "sugiere", "sugerir", "elabora", "elaborar", "crea", "crear", "haz", "hacer", "arma", "armar"])
    print(f"  - Detecta menú: {es_menu}")
    
    # Extraer ingredientes
    ingredientes = ""
    for prefix in ["que tenga ", "que lleve ", "que llebe ", "con ", ":"]:
        idx = message.find(prefix)
        if idx >= 0:
            ingredientes = message[idx + len(prefix):].strip()
            break
    
    if not ingredientes:
        for keyword in ["menú", "menu"]:
            idx = message.find(keyword)
            if idx >= 0:
                ingredientes = message[idx + len(keyword):].strip()
                # Limpiar
                for stop in ["para", "del", "de la", "el dia", "día", "mañana", "hoy"]:
                    idx_stop = ingredientes.find(stop)
                    if idx_stop >= 0:
                        ingredientes = ingredientes[:idx_stop].strip()
                break
    
    print(f"  - Ingredientes extraídos: '{ingredientes}'")
    
    if es_menu and ingredientes:
        print(f"  - [OK] Debería ejecutar: sugerir_menu_por_ingredientes('{ingredientes}')")
    elif es_menu:
        print(f"  - [!] Detecta menú pero no ingredientes")
    else:
        print(f"  - [!] No detecta menú")

print("\n" + "="*60)
print(" TEST COMPLETADO")
print("="*60)
