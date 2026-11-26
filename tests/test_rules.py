import unittest
# Extract pure business-rule function without requiring a live PostgreSQL driver.
import ast
from collections import Counter
from pathlib import Path
source = Path(__file__).resolve().parents[1] / "estoque" / "production_orders.py"
tree = ast.parse(source.read_text())
nodes = [n for n in tree.body if isinstance(n, (ast.Assign, ast.FunctionDef)) and (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ("BLOCK_SIZES", "COLORS", "BASE_COLORS", "PLAQUE_LIMIT") for t in n.targets) or isinstance(n, ast.FunctionDef) and n.name == "_validate_order")]
namespace = {"Counter": Counter}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
_validate_order, BLOCK_SIZES = namespace["_validate_order"], namespace["BLOCK_SIZES"]
from estoque.estoque import listar_estoque

class RulesTests(unittest.TestCase):
    def test_sizes(self):
        for block, n in BLOCK_SIZES.items():
            boxes = [{"plaque_colors": ["PRETA", "AZUL", "VERDE"]} for _ in range(n)]
            self.assertEqual(len(_validate_order(block, "PRETA", boxes)), n)
    def test_wrong_box_count(self):
        with self.assertRaises(ValueError):
            _validate_order("TRIPLO", "PRETA", [{"plaque_colors": ["AZUL"]*3}])
    def test_wrong_plaque_count(self):
        with self.assertRaises(ValueError):
            _validate_order("UNICO", "PRETA", [{"plaque_colors": ["AZUL"]*2}])
    def test_bad_base(self):
        with self.assertRaises(ValueError):
            _validate_order("UNICO", "AZUL", [{"plaque_colors": ["AZUL"]*3}])
    def test_fixed_stock_copy(self):
        first = listar_estoque()
        first[0]["current_quantity"] = 0
        self.assertEqual(listar_estoque()[0]["current_quantity"], 6)

if __name__ == "__main__": unittest.main()
