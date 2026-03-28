import os
import json
from datetime import datetime
from app.utils.logger import setup_logger


logger = setup_logger("rag.code_indexer")


class CodeIndexer:
    def __init__(self, store, chunk_size=500, overlap=200):
        self.store = store
        self.chunk_size = chunk_size
        self.overlap = overlap

    def _serialize_metadata(self, metadata):
        if metadata is None:
            return {}
        return {k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in metadata.items()}

    def chunk_text(self, text):
        lines = text.split("\n")
        chunks = []
        start = 0
        total_lines = len(lines)

        while start < total_lines:
            end = start + self.chunk_size
            chunk = "\n".join(lines[start:end])
            chunks.append((chunk, start))
            start += self.chunk_size - self.overlap

        return chunks

    def index_files(self, file_paths):
        indexed_count = 0

        for full_path in file_paths:
            if not os.path.exists(full_path):
                logger.warning(f"File not found: {full_path}")
                continue

            if not full_path.endswith(".py"):
                logger.debug(f"Skipping non-Python file: {full_path}")
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading {full_path}: {e}")
                continue

            chunks = self.chunk_text(content)
            timestamp = datetime.now().isoformat()

            for chunk, start_line in chunks:
                self.store.add(
                    chunk,
                    {
                        "file": os.path.basename(full_path),
                        "path": full_path,
                        "start_line": start_line,
                        "type": "generated",
                        "timestamp": timestamp,
                    }
                )
                indexed_count += 1

        logger.info(f"Indexed {indexed_count} chunks from {len(file_paths)} files")
        return indexed_count

    def index_file_content(self, file_path, content, metadata=None):
        chunks = self.chunk_text(content)
        timestamp = datetime.now().isoformat()

        meta = {
            "file": os.path.basename(file_path),
            "path": file_path,
            "type": metadata.get("type", "generated") if metadata else "generated",
            "timestamp": timestamp,
        }
        if metadata:
            meta.update(self._serialize_metadata(metadata))

        for chunk, start_line in chunks:
            self.store.add(
                chunk,
                {
                    "file": os.path.basename(file_path),
                    "path": file_path,
                    "start_line": start_line,
                    "type": metadata.get("type", "generated") if metadata else "generated",
                    "timestamp": timestamp,
                }
            )

        return len(chunks)
