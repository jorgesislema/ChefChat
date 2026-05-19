"""
Test de extracción de ingredientes
"""

test_messages = [
    "elabora un menu para el almuerso",
    "elabora el menu para mañana desayuno con fresas chocolate, almuerzo con pollo arroz, merienda con galletas",
    "crea un menu con pollo fresas y chocolate",
    "menu para hoy con lo que haya",
]

stop_words = {"para", "el", "la", "los", "las", "un", "una", "del", "de", "por", "con", 
             "dia", "día", "mañana", "hoy", "almuerso", "almuerzo", "desayuno", 
             "merienda", "cena", "comida", "menu", "menú", "incluye", "incluya",
             "que", "tenga", "lleve", "llebe", "incluya", "sea", "tengan"}

print("="*60)
print(" TEST: Extracción de Ingredientes")
print("="*60)

for message in test_messages:
    print(f"\nMensaje: '{message}'")
    
    ingredientes_texto = ""
    
    # Estrategia 1: Buscar prefijos
    for prefix in ["que tenga ", "que lleve ", "que llebe ", "con ", "que incluya "]:
        idx = message.find(prefix)
        if idx >= 0:
            ingredientes_texto = message[idx + len(prefix):].strip()
            for stop in [" para ", " el dia ", " día ", " desayuno ", " almuerzo ", " merienda ", " cena "]:
                sidx = ingredientes_texto.find(stop)
                if sidx >= 0:
                    ingredientes_texto = ingredientes_texto[:sidx]
            break
    
    # Estrategia 2: Si hay comidas
    if not ingredientes_texto and any(c in message for c in ["desayuno", "almuerzo", "merienda", "cena"]):
        for keyword in ["menú", "menu"]:
            idx = message.find(keyword)
            if idx >= 0:
                ingredientes_texto = message[idx + len(keyword):].strip()
                break
    
    # Estrategia 3: Después de "menu"
    if not ingredientes_texto:
        for keyword in ["menú", "menu"]:
            idx = message.find(keyword)
            if idx >= 0:
                ingredientes_texto = message[idx + len(keyword):].strip()
                break
    
    # Filtrar stop words
    if ingredientes_texto:
        palabras = ingredientes_texto.replace(",", " ").replace(".", "").split()
        ingredientes_filtrados = [p for p in palabras if p.lower() not in stop_words and len(p) > 1]
        ingredientes_texto = " ".join(ingredientes_filtrados)
    
    print(f"  Extraído: '{ingredientes_texto}'")
    
    if ingredientes_texto and len(ingredientes_texto.split()) > 0:
        print(f"  [OK] Ingredientes válidos: {ingredientes_texto}")
    else:
        print(f"  [!] No se extrajeron ingredientes válidos")

print("\n" + "="*60)
print(" TEST COMPLETADO")
print("="*60)
