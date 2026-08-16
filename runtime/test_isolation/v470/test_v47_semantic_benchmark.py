import sys
import json
import time
import uuid
import threading
import psutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from concurrent_segmented_engine_v47 import ConcurrentSegmentedEngineV47

SANDBOX = Path("runtime/test_isolation/v470/sandbox_1m")

def producer_semantic_worker(engine, producer_id: int, count_per_producer: int):
    """Producteur générant des payloads sémantiques enrichis avec vecteurs d'embeddings."""
    agent_name = f"agent_worker_{producer_id:02d}"
    semantic_types = ["EPISODIC_MEMORY", "REASONING_TRACE", "CONTEXT_SNAPSHOT", "SYSTEM_LOG"]
    
    # Vecteur d'embedding fictif de 128 dimensions pour simuler la charge mémoire
    simulated_embedding = [round(0.001 * (i % 100), 4) for i in range(128)]
    payload_body = "Trace sémantique contextuelle enregistrée par le kernel de mémoire vive E-ZZIO."
    
    for i in range(count_per_producer):
        stype = semantic_types[i % len(semantic_types)]
        event = {
            "event_id": str(uuid.uuid4()),
            "seq": i,
            "timestamp": time.time(),
            "agent_source": agent_name,
            "semantic_type": stype,
            "metadata": {
                "tags": ["v47", "bench", agent_name, stype.lower()],
                "priority": (i % 3) + 1
            },
            "embedding_vector": simulated_embedding,
            "payload": payload_body
        }
        engine.write_event(event)

def run_v47_benchmark():
    print("=============================================================", flush=True)
    print(" E-ZZIO V4.7 — Benchmark Ingestion Sémantique (1 Million Target)", flush=True)
    print("=============================================================", flush=True)

    if SANDBOX.exists():
        for p in SANDBOX.glob("**/*"):
            try:
                p.unlink()
            except Exception:
                pass
    SANDBOX.mkdir(parents=True, exist_ok=True)

    # Configuration 1M Événements Sémantiques
    num_producers = 8
    events_per_producer = 125_000  # Total 1 000 000 événements
    total_target = num_producers * events_per_producer

    # Initialisation Moteur V4.7 (Segments de 50 Mo)
    engine = ConcurrentSegmentedEngineV47(str(SANDBOX), max_segment_size=50 * 1024 * 1024)

    process = psutil.Process()
    psutil.cpu_percent(interval=None)

    print(f"[*] Démarrage de {num_producers} producteurs parallèles (Objectif : {total_target:,} evts)...", flush=True)
    start_time = time.time()

    threads = []
    for pid in range(num_producers):
        t = threading.Thread(target=producer_semantic_worker, args=(engine, pid, events_per_producer))
        threads.append(t)
        t.start()

    # Suivi temps réel
    while any(t.is_alive() for t in threads):
        q_size = engine.queue.qsize()
        rss_mb = process.memory_info().rss / (1024 * 1024)
        l1_stats = engine.l1_index.stats()
        print(f"    [MONITOR] RAM RSS: {rss_mb:.2f} MB | Queue: {q_size:,} | L1 Indexed: {l1_stats['total_indexed_l1']:,}", flush=True)
        time.sleep(1.0)

    for t in threads:
        t.join()

    print("[*] Vidage de la queue et scellement du moteur...", flush=True)
    engine.close()
    duration = time.time() - start_time
    throughput = total_target / duration

    print("-------------------------------------------------------------", flush=True)
    print(f"[METRIC] Débit Global Sémantique : {throughput:.2f} events/sec", flush=True)
    print(f"[METRIC] Temps Total d'Exécution : {duration:.2f} secondes", flush=True)
    print(f"[METRIC] Empreinte Mémoire RSS   : {process.memory_info().rss / (1024 * 1024):.2f} MB", flush=True)
    print("-------------------------------------------------------------", flush=True)

    # Test de recherche L1
    l1_stats = engine.l1_index.stats()
    print(f"[*] Analyse de l'Index L1 en RAM : {l1_stats}", flush=True)
    
    t_lookup_start = time.time()
    sample_agent_evts = engine.l1_index.query_by_agent("agent_worker_03")
    sample_type_evts = engine.l1_index.query_by_type("EPISODIC_MEMORY")
    lookup_duration_ms = (time.time() - t_lookup_start) * 1000

    print(f"[L1 SEARCH] Événements trouvés pour 'agent_worker_03' : {len(sample_agent_evts):,}", flush=True)
    print(f"[L1 SEARCH] Événements 'EPISODIC_MEMORY'          : {len(sample_type_evts):,}", flush=True)
    print(f"[L1 SEARCH] Latence de recherche en RAM            : {lookup_duration_ms:.3f} ms", flush=True)

    # Audit d'intégrité L2 (Persistance physique)
    print("[*] Audit d'intégrité L2 (Fichiers segments sur disque)...", flush=True)
    total_l2_found = 0
    corrupt_count = 0
    footers_count = 0
    segments_dir = SANDBOX / "segments"

    for seg in sorted(segments_dir.glob("segment_*.jsonl")):
        with open(seg, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        obj = json.loads(line.strip())
                        if isinstance(obj, dict) and obj.get("__type__") == "SEGMENT_FOOTER":
                            footers_count += 1
                        else:
                            total_l2_found += 1
                    except json.JSONDecodeError:
                        corrupt_count += 1

    print(f"[AUDIT L2] Événements valides sur disque : {total_l2_found:,} / {total_target:,}", flush=True)
    print(f"[AUDIT L2] Footers de scellement trouvés : {footers_count}", flush=True)
    print(f"[AUDIT L2] Éléments corrompus            : {corrupt_count}", flush=True)

    assert corrupt_count == 0, f"FAIL: {corrupt_count} corruptions détectées sur disque !"
    assert total_l2_found == total_target, f"FAIL: Incohérence L1/L2 ! Attendu {total_target}, trouvé {total_l2_found}"
    assert l1_stats["total_indexed_l1"] == total_target, "FAIL: L1 Index incomplet !"

    print("=============================================================", flush=True)
    print(" STATUS : V4.7 1M SEMANTIC INGESTION & L1 INDEX CERTIFIÉS", flush=True)
    print("=============================================================", flush=True)

if __name__ == "__main__":
    run_v47_benchmark()
