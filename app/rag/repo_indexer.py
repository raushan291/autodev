import os


class RepoIndexer:
    def __init__(self, store, chunk_size=500, overlap=200):
        self.store = store
        self.chunk_size = chunk_size
        self.overlap = overlap

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

    def index_repo(self, path):
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".venv"}]

            for file in files:
                if not file.endswith(".py"):
                    continue

                full_path = os.path.join(root, file)

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception:
                    continue

                chunks = self.chunk_text(content)

                for chunk, start_line in chunks:
                    self.store.add(
                        chunk,
                        {
                            "file": file,
                            "path": full_path,
                            "start_line": start_line,
                            "type": "indexed",
                        }
                    )
