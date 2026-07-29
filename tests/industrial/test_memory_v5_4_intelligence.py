from runtime.memory.semantic.pattern_engine import MemoryPattern
from runtime.memory.semantic.merge_engine import MemoryMerge
from runtime.memory.semantic.conflict_resolver import MemoryConflictResolver
from runtime.memory.semantic.knowledge_graph import MemoryGraph
from runtime.memory.semantic.coherence import MemoryCoherence



def test_pattern():

    assert (
        MemoryPattern.similarity(
            "hello world",
            "hello world"
        )
        ==
        100
    )



def test_merge():

    r=MemoryMerge.merge(
        {"a":1},
        {"b":2}
    )

    assert r["a"]==1
    assert r["b"]==2



def test_conflict():

    r=MemoryConflictResolver.resolve(
        "A",
        "B"
    )

    assert r["status"]=="CONFLICT"



def test_graph(tmp_path):

    g=MemoryGraph(
        str(tmp_path/"graph.json")
    )

    g.add(
        {"memory":"test"}
    )

    assert len(g.nodes)==1



def test_coherence():

    assert (
        MemoryCoherence.calculate(
            [1,2,3]
        )
        ==
        30
    )
