import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from app.config import settings


class SimpleVectorStore:
    def __init__(
        self,
        collection_name=settings.COLLECTION_NAME,
        persist_dir=settings.PERSIST_DIR,
        model_name=settings.EMB_MODLEL_NAME,
    ):
        # embedding model
        self.model = SentenceTransformer(model_name)

        # chroma client
        self.client = chromadb.PersistentClient(path=persist_dir)

        # embedding function wrapper
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )

        # collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )

        self.id_counter = 0  # simple ID generator

    def add(self, text, metadata=None):
        doc_id = str(self.id_counter)
        self.id_counter += 1

        self.collection.add(
            documents=[text],
            metadatas=[metadata or {}],
            ids=[doc_id]
        )

    def search(self, query, k=3, where=None):
        results = self.collection.query(
            query_texts=[query],
            n_results=k,
            where=where if where else None
        )

        output = []
        if not results["documents"] or not results["documents"][0]:
            return output
            
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = 1 - dist
            output.append((doc, meta, float(score)))

        return output

    def persist(self):
        self.client.persist()
