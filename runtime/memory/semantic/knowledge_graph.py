import json
import os


class MemoryGraph:


    def __init__(
        self,
        file="runtime/memory/knowledge_graph.json"
    ):

        self.file=file

        self.nodes=[]



    def add(self,node):

        self.nodes.append(node)

        self.save()



    def save(self):

        os.makedirs(
            os.path.dirname(self.file),
            exist_ok=True
        )


        with open(
            self.file,
            "w",
            encoding="utf8"
        ) as f:

            json.dump(
                self.nodes,
                f,
                indent=4
            )
