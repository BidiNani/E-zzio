"""Convertit Field(..., example=X) -> Field(..., json_schema_extra={"example": X})."""
import ast
import pathlib
import sys

TARGET = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "routers/generators.py")

class FieldTransformer(ast.NodeTransformer):
    def visit_Call(self, node):
        self.generic_visit(node)

        # Chercher les kwargs "example="
        new_kwargs = []
        example_node = None
        has_json_schema_extra = False

        for kw in node.keywords:
            if kw.arg == "example":
                example_node = kw.value
            elif kw.arg == "json_schema_extra":
                has_json_schema_extra = True
                new_kwargs.append(kw)
            else:
                new_kwargs.append(kw)

        if example_node is not None and not has_json_schema_extra:
            # Creer json_schema_extra={"example": <example_node>}
            dict_node = ast.Dict(
                keys=[ast.Constant(value="example")],
                values=[example_node],
            )
            new_kwargs.append(ast.keyword(arg="json_schema_extra", value=dict_node))
            node.keywords = new_kwargs
            return node

        return node


src = TARGET.read_text(encoding="utf-8")
tree = ast.parse(src)

transformer = FieldTransformer()
new_tree = transformer.visit(tree)
ast.fix_missing_locations(new_tree)

new_src = ast.unparse(new_tree)
TARGET.write_text(new_src + "\n", encoding="utf-8")
print(f"Fichier reecrit : {TARGET}")
