import threading
import time
from typing import Dict, Optional

from app.api.youtube_api import YouTubeAPI
from app.db import (
    add_messages,
    get_db_session,
    StreamMessage,
    get_or_create_stream_session,
    update_stream_session
)


class LiveChatCollector:
    """Polls live chat continuously and stores messages + nextPageToken into DB."""

    def __init__(self, api: YouTubeAPI):
        self.api = api
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None
        self._state: Dict = {"collecting": False, "live_chat_id": None, "last_error": None}

    def start(self, live_chat_id: str) -> None:
        # Important: stop() must NOT be called while holding _lock (would deadlock).
        with self._lock:
            already_collecting_same = self._state["collecting"] and self._state["live_chat_id"] == live_chat_id
        if already_collecting_same:
            return

        self.stop()

        with self._lock:
            self._stop_event = threading.Event()
            self._state = {"collecting": True, "live_chat_id": live_chat_id, "last_error": None}
            self._thread = threading.Thread(target=self._run, args=(live_chat_id, self._stop_event), daemon=True)
            self._thread.start()
        print("TEMP: Collector started for", live_chat_id)

    def stop(self) -> None:
        thread = None
        with self._lock:
            if self._stop_event:
                self._stop_event.set()
            self._state["collecting"] = False
            thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=2.0)
        print("TEMP: Collector stopped")

    def status(self) -> Dict:
        with self._lock:
            return dict(self._state)

    def _run(self, live_chat_id: str, stop_event: threading.Event) -> None:
        db = None
        try:
            db = get_db_session()
            session = get_or_create_stream_session(db, live_chat_id, reset_on_new_live_chat=False)
            page_token = session.next_page_token

            while not stop_event.is_set():
                try:
                    messages, next_page_token, polling_interval_ms = self.api.fetch_live_chat_page(
                        live_chat_id=live_chat_id,
                        page_token=page_token
                    )
                    if messages:
                        add_messages(db, session, messages)

                    page_token = next_page_token or page_token
                    total_comments = db.query(StreamMessage).filter_by(session_id=session.id).count()
                    update_stream_session(db, session, next_page_token=page_token, total_comments=total_comments)

                    with self._lock:
                        self._state["last_error"] = None
                except Exception as e:
                    with self._lock:
                        self._state["last_error"] = str(e)
                    polling_interval_ms = 5000

                sleep_sec = max(0.5, (polling_interval_ms or 1000) / 1000.0)
                time.sleep(min(sleep_sec, 2.0))
        finally:
            if db:
                db.close()
            with self._lock:
                self._state["collecting"] = False
