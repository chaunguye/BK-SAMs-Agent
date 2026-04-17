import asyncio
from concurrent.futures import ThreadPoolExecutor
from chonkie import RecursiveChunker
from sentence_transformers import SentenceTransformer
import uuid
from src.repository.chunk_repo import get_chunk_repo
import logfire
from datetime import datetime
from docling.document_converter import DocumentConverter, InputFormat, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions



import threading

_executor = ThreadPoolExecutor(max_workers=4)

# Background preloading of SentenceTransformer model
def _preload_embedder():
    try:
        SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        print(f"[Warning] Failed to preload embedder: {e}")

_preload_thread = threading.Thread(target=_preload_embedder, daemon=True)
_preload_thread.start()


pipeline_options = PdfPipelineOptions()
# Disable OCR (only works if PDFs are digital, not scanned)
pipeline_options.do_ocr = False 
# Use a faster, simpler table model
pipeline_options.do_table_structure = False

class ChunkService:
    def __init__(self):
        self._converter = None
        self._chunker = None
        self._embedder = None
    
    @property
    def converter(self) -> DocumentConverter:
        if self._converter is None:
            self._converter = DocumentConverter(
                format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
            )
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
            # query_embedding = self.embedder.encode([query])
            query_embedding = await loop.run_in_executor(_executor, self.embedder.encode, [query])
        query_embedding_str = "[" + ",".join(str(x) for x in query_embedding[0]) + "]"

        chunkRepo = await get_chunk_repo()
        with logfire.span("Searching Chunks in Database"):
            results = await chunkRepo.search_chunks_by_embedding(query_embedding_str, top_k)
        return results
    
    async def search_chunks_of_activity(self, query: str, top_k: int, activity_id: uuid.UUID):
        loop = asyncio.get_running_loop()
        
        with logfire.span("Embedding Search Query for Activity Chunks"):
            query_embedding = await loop.run_in_executor(_executor, self.embedder.encode, [query])
        query_embedding_str = "[" + ",".join(str(x) for x in query_embedding[0]) + "]"

        chunkRepo = await get_chunk_repo()
        with logfire.span("Searching Activity Chunks in Database"):
            # results = await chunkRepo.search_chunks_of_activity(query_embedding_str, activity_id, top_k)
            results = await chunkRepo.search_chunks_of_activity_hybrid(query_embedding_str, query, activity_id, top_k)
        return results
    
    async def healthy_check(self):
        return {"converter": self._converter is not None, 
                "chunker": self._chunker is not None, 
                "embedder": self._embedder is not None}
    
_chunk_service = None
def get_chunk_service():
    global _chunk_service
    if _chunk_service is None:
        _chunk_service = ChunkService()
    return _chunk_service