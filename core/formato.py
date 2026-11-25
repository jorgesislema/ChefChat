"""Formato de dinero igual que en la pantalla (Ecuador): $1.234,56"""


def dinero(x: float) -> str:
    texto = f"{abs(x):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"-${texto}" if x < 0 else f"${texto}"
