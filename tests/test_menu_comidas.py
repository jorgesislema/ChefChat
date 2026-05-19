"""
Test para menú separado por comidas
"""

from agents.tools import crear_herramientas_operativas
from data.db_manager import DatabaseManager
import os

db_path = os.path.join(os.path.dirname(__file__), "chefchat.db")
db = DatabaseManager(db_path=db_path)

tools = crear_herramientas_operativas(db)

# Buscar la herramienta
tool = next((t for t in tools if t.name == "sugerir_menu_por_ingredientes"), None)

if tool:
    print("Testing menú por comidas...\n")
    
    test_cases = [
        "desayuno fresas chocolate, almuerzo pollo arroz, merienda galletas leche",
        "desayuno huevos pan, almuerzo carne papa, cena sopa",
        "pollo arroz verduras",  # Sin comidas específicas
    ]
    
    for test in test_cases:
        print(f"="*60)
        print(f"Input: '{test}'")
        print(f"="*60)
        resultado = tool.func(test)
        print(f"Resultado:\n{resultado[:500]}...\n")
else:
    print("Herramienta no encontrada")
