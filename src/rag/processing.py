import asyncio
from concurrent.futures import ThreadPoolExecutor
from docling.document_converter import DocumentConverter
from chonkie import RecursiveChunker
from sentence_transformers import SentenceTransformer
import uuid
from src.repository.chunk_repo import get_chunk_repo
import logfire

_executor = ThreadPoolExecutor(max_workers=4)  

class DocumentProcessor:
    def __init__(self):
        self._converter = None
        self._chunker = None
        self._embedder = None
    
    @property
    def converter(self) -> DocumentConverter:
        if self._converter is None:
            self._converter = DocumentConverter()
        return self._converter

    @property
    def chunker(self) -> RecursiveChunker:
        if self._chunker is None:
            self._chunker = RecursiveChunker()
        return self._chunker
    
    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        return self._embedder
    
    def heavy_processing_pipeline(self, file_path: str):
        # parsing document
        with logfire.span("Parsing Document"):
            doc = self.converter.convert(file_path).document
            markeddown_text = doc.export_to_markdown()

        # chunking document
        with logfire.span("Chunking Document"):
            chunks = self.chunker(markeddown_text)
            texts = [chunk.text for chunk in chunks]

        with logfire.span("Embedding Document"):
            embeddings = self.embedder.encode(texts)
        return texts, embeddings


    async def process(self, file_path: str, doc_id: str) -> str:

        loop = asyncio.get_running_loop()

        with logfire.span("Processing Document"):
            texts, embeddings = await loop.run_in_executor(_executor, self.heavy_processing_pipeline, file_path)

        insert_data = [(str(uuid.uuid4()), text, "[" + ",".join(map(str, embedding)) + "]", doc_id) for text, embedding in zip(texts, embeddings)]

        # Repo for SQL operations
        chunkRepo = await get_chunk_repo()

        with logfire.span("Inserting Batch Chunks to Database"):
            await chunkRepo.batch_insert_chunks(insert_data)

    async def search_chunk_by_query(self, query: str, top_k: int = 5):
        loop = asyncio.get_running_loop()
        with logfire.span("Embedding Search Query"):
            query_embedding = await loop.run_in_executor(_executor, self.embedder.encode, [query])
        query_embedding_str = "[" + ",".join(str(x) for x in query_embedding[0]) + "]"
        chunkRepo = await get_chunk_repo()
        with logfire.span("Searching Chunks in Database"):
            results = await chunkRepo.search_chunks_by_embedding(query_embedding_str, top_k)
        return results
    
_document_processor = None
def get_document_processor():
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    return _document_processor