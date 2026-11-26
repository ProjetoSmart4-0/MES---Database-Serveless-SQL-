"""Capacidade fixa de materiais instalada na máquina SMART 4.0.

Esses números representam a capacidade física disponível e NÃO são saldo
contábil. Por isso, nunca são debitados ou alterados pelo MES.
"""

ESTOQUE_FIXO = [
    {"id": 1, "item_name": "Base", "category": "COMPONENTE", "color": "PRETA", "current_quantity": 6, "min_quantity": 0, "unit": "unidades"},
    {"id": 2, "item_name": "Base", "category": "COMPONENTE", "color": "VERMELHA", "current_quantity": 6, "min_quantity": 0, "unit": "unidades"},
    {"id": 3, "item_name": "Tampa", "category": "COMPONENTE", "color": "PRETA", "current_quantity": 6, "min_quantity": 0, "unit": "unidades"},
    {"id": 4, "item_name": "Tampa", "category": "COMPONENTE", "color": "VERMELHA", "current_quantity": 6, "min_quantity": 0, "unit": "unidades"},
    *[
        {"id": i + 5, "item_name": "Plaquinha lateral", "category": "COMPONENTE", "color": color, "current_quantity": 10, "min_quantity": 0, "unit": "unidades"}
        for i, color in enumerate(("VERMELHA", "PRETA", "BRANCA", "AMARELA", "VERDE", "AZUL"))
    ],
]


def listar_estoque():
    """Retorna uma cópia do estoque/capacidade fixa configurada na máquina."""
    return [item.copy() for item in ESTOQUE_FIXO]
