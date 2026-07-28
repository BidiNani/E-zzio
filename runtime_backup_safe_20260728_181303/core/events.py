import threading
import queue
import traceback

class EventBus:
    def __init__(self):
        self._subscribers = {}
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._process_events, daemon=True)
        self._worker.start()

    def subscribe(self, event_type: str, callback):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def emit(self, event_type: str, payload: dict):
        self._queue.put((event_type, payload))

    def _process_events(self):
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                event_type, payload = self._queue.get(timeout=0.1)
                
                # Récupération sécurisée des écouteurs
                listeners = list(self._subscribers.get(event_type, []))

                for callback in listeners:
                    try:
                        callback(payload)
                    except Exception as e:
                        print(f"\n[EVENTBUS HANDLER ERROR] event={event_type} error={e}")
                        traceback.print_exc()

                        if event_type != "EventListenerError":
                            self._queue.put((
                                "EventListenerError",
                                {
                                    "event": event_type,
                                    "error": str(e)
                                }
                            ))
                self._queue.task_done()

            except queue.Empty:
                continue

            except Exception as e:
                print(f"\n[EVENTBUS CORE ERROR] {e}")
                traceback.print_exc()

    def stop_and_wait(self):
        self._queue.join()
        self._stop_event.set()
        if self._worker.is_alive():
            self._worker.join(timeout=1.0)