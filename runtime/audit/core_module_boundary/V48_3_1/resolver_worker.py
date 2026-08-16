import ast
import json
import sys


path = sys.argv[1]


result = {
    "file": path,
    "imports": [],
    "error": None
}


try:

    with open(
        path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:

        source = f.read()


    tree = ast.parse(source)


    for node in ast.walk(tree):

        if isinstance(node, ast.Import):

            for item in node.names:

                result["imports"].append(
                    {
                        "module": item.name,
                        "level": 0,
                        "kind": "import"
                    }
                )


        elif isinstance(node, ast.ImportFrom):

            module = node.module or ""

            result["imports"].append(
                {
                    "module": module,
                    "level": node.level,
                    "kind": "from"
                }
            )


except Exception as e:

    result["error"] = str(e)


print(
    json.dumps(
        result,
        ensure_ascii=False
    )
)

