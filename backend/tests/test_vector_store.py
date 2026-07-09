"""Unit tests for the vector store index manager and retriever."""

from app.services.vector_store.chroma_service import ChromaService, collection_name
from app.services.vector_store.index_manager import IndexManager
from app.services.vector_store.retrieval import RetrievedChunk, Retriever


class _FakeCollection:
    """In-memory stand-in for a Chroma collection."""

    def __init__(self) -> None:
        self.added: dict[str, list] = {}
        self.documents: list[str] = []

    def add(self, ids, embeddings, documents, metadatas) -> None:
        self.added = {
            "ids": ids,
            "embeddings": embeddings,
            "documents": documents,
            "metadatas": metadatas,
        }
        self.documents = documents

    def query(self, query_embeddings, n_results):
        return {"documents": [self.documents[:n_results]]}


class _FakeChroma:
    """In-memory stand-in for ChromaService."""

    def __init__(self) -> None:
        self.collections: dict[str, _FakeCollection] = {}
        self.deleted: list[str] = []

    def get_collection(self, name: str) -> _FakeCollection:
        return self.collections.setdefault(name, _FakeCollection())

    def delete_collection(self, name: str) -> None:
        self.deleted.append(name)
        self.collections.pop(name, None)


class _FakeEmbeddings:
    """Deterministic fake embedding service."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text))] for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return [float(len(text))]


def test_collection_name_is_prefixed() -> None:
    """Collection names should be namespaced by file id."""

    assert collection_name("abc") == "pdf_abc"


def test_index_chunks_stores_documents_and_returns_count() -> None:
    """Indexing should embed, store, and report the chunk count."""

    chroma = _FakeChroma()
    manager = IndexManager(chroma, _FakeEmbeddings())

    count = manager.index_chunks("file1", ["alpha", "beta"])

    collection = chroma.collections[collection_name("file1")]
    assert count == 2
    assert collection.added["documents"] == ["alpha", "beta"]
    assert collection.added["ids"] == ["file1-0", "file1-1"]
    assert collection_name("file1") in chroma.deleted  # replaced prior index


def test_index_empty_chunks_returns_zero() -> None:
    """Indexing an empty list should be a no-op."""

    manager = IndexManager(_FakeChroma(), _FakeEmbeddings())

    assert manager.index_chunks("file1", []) == 0


def test_retrieve_returns_top_k_documents() -> None:
    """Retrieval should return the stored documents up to top_k."""

    chroma = _FakeChroma()
    embeddings = _FakeEmbeddings()
    IndexManager(chroma, embeddings).index_chunks("file1", ["a", "b", "c"])
    retriever = Retriever(chroma, embeddings)

    results = retriever.retrieve("file1", "query", top_k=2)

    assert results == ["a", "b"]


def test_retrieve_empty_query_returns_empty() -> None:
    """A blank query should short-circuit to an empty result."""

    retriever = Retriever(_FakeChroma(), _FakeEmbeddings())

    assert retriever.retrieve("file1", "   ") == []


class _SearchFakeChroma:
    """Fake ChromaService returning a fixed search payload."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def search(self, file_id, query_embedding, top_k):
        return self._payload


def test_retrieve_with_citations_maps_metadata() -> None:
    """Citation retrieval should map documents and metadata to chunks."""

    payload = {
        "documents": [["alpha", "beta"]],
        "metadatas": [
            [
                {"chunk_id": "f-0", "chunk_index": 0, "page": 2},
                {"chunk_id": "f-1", "chunk_index": 1, "page": 5},
            ]
        ],
        "distances": [[0.1, 0.2]],
    }
    retriever = Retriever(_SearchFakeChroma(payload), _FakeEmbeddings())

    results = retriever.retrieve_with_citations("file1", "query", top_k=2)

    assert [chunk.text for chunk in results] == ["alpha", "beta"]
    assert [chunk.page for chunk in results] == [2, 5]
    assert [chunk.chunk_id for chunk in results] == ["f-0", "f-1"]
    assert isinstance(results[0], RetrievedChunk)


def test_retrieve_with_citations_empty_query_returns_empty() -> None:
    """A blank query should not hit the vector store."""

    retriever = Retriever(_SearchFakeChroma({}), _FakeEmbeddings())

    assert retriever.retrieve_with_citations("file1", "  ") == []


def test_chroma_service_add_search_count_delete(tmp_path) -> None:
    """The reusable vector store service should add, search, and delete."""

    chroma = ChromaService(persist_dir=str(tmp_path / "chroma"))
    chroma.add_documents(
        "file1",
        ids=["file1-0", "file1-1"],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
        documents=["alpha", "beta"],
        metadatas=[
            {"file_id": "file1", "chunk_index": 0, "chunk_id": "file1-0", "page": 1},
            {"file_id": "file1", "chunk_index": 1, "chunk_id": "file1-1", "page": 2},
        ],
    )

    assert chroma.count("file1") == 2

    result = chroma.search("file1", [1.0, 0.0], top_k=1)
    assert result["documents"][0][0] == "alpha"
    assert result["metadatas"][0][0]["page"] == 1

    chroma.delete_document("file1")
    assert chroma.count("file1") == 0

