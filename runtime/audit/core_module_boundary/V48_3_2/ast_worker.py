
import ast
import json
import sys


path=sys.argv[1]


result={
    "file":path,
    "imports":[]
}


try:

    with open(
        path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as f:
        tree=ast.parse(f.read())


    for node in ast.walk(tree):

        if isinstance(node,ast.Import):

            for item in node.names:

                result["imports"].append(
                    {
                        "module":item.name,
                        "level":0
                    }
                )


        elif isinstance(node,ast.ImportFrom):

            if node.module:

                result["imports"].append(
                    {
                        "module":node.module,
                        "level":node.level
                    }
                )


except Exception as e:

    result["error"]=str(e)



print(json.dumps(result))

