
import ast
import json
import sys


path=sys.argv[1]


result={
    "file":path,
    "imports":[],
    "classes":[],
    "functions":[],
    "decorators":[]
}


try:

    source=open(
        path,
        "r",
        encoding="utf-8",
        errors="ignore"
    ).read()


    tree=ast.parse(source)


    for node in ast.walk(tree):

        if isinstance(node,ast.Import):

            for n in node.names:
                result["imports"].append(n.name)


        elif isinstance(node,ast.ImportFrom):

            if node.module:
                result["imports"].append(node.module)


        elif isinstance(node,ast.ClassDef):

            result["classes"].append(node.name)


        elif isinstance(node,ast.FunctionDef):

            result["functions"].append(node.name)


        elif isinstance(node,ast.Call):

            if isinstance(node.func,ast.Name):
                result["decorators"].append(node.func.id)


except Exception as e:

    result["error"]=str(e)


print(json.dumps(result))

