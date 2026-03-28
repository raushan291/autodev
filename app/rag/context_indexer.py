import json
from datetime import datetime



class ContextIndexer:
    def __init__(self, store):
        self.store = store

    def _serialize_metadata(self, metadata):
        if metadata is None:
            return {}
        return {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in metadata.items()}

    def index_user_query(self, session_id, query, metadata=None):
        timestamp = datetime.now().isoformat()

        self.store.add(
            query,
            {
                "type": "user_query",
                "session_id": session_id,
                "timestamp": timestamp,
                **self._serialize_metadata(metadata)
            }
        )

    def index_user_context(self, session_id, context_type, content, metadata=None):
        timestamp = datetime.now().isoformat()

        self.store.add(
            content,
            {
                "type": "user_context",
                "context_type": context_type,
                "session_id": session_id,
                "timestamp": timestamp,
                **self._serialize_metadata(metadata)
            }
        )

    def index_suggestion(self, session_id, suggestion, metadata=None):
        timestamp = datetime.now().isoformat()

        self.store.add(
            suggestion,
            {
                "type": "suggestion",
                "session_id": session_id,
                "timestamp": timestamp,
                **self._serialize_metadata(metadata)
            }
        )

    def search_user_contexts(self, query, session_id=None, k=5):
        if session_id:
            where = {"session_id": session_id}
            return self.store.search(query, k=k, where=where)
        return self.store.search(query, k=k)

    def search_all_contexts(self, query, content_types=None, k=5):
        results = self.store.search(query, k=k)
        if content_types:
            results = [r for r in results if r[1].get("type") in content_types]
        return results
