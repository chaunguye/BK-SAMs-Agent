from docling.document_converter import DocumentConverter
from chonkie import RecursiveChunker
from sentence_transformers import SentenceTransformer
import uuid
from src.repository.chunk_repo import initialize_chunk_repo

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

    async def process(self, file_path: str, doc_id: str) -> str:

        # parsing document
        doc = self.converter.convert(file_path).document
        markeddown_text = doc.export_to_markdown()

        # chunking document
        chunks = self.chunker(markeddown_text)

        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedder.encode(texts)
        embeddings_str = ["[" + ",".join(str(x) for x in embedding) + "]" for embedding in embeddings]

        # Repo for SQL operations
        chunkRepo = await initialize_chunk_repo()

        # for chunk, embedding in zip(chunks, embeddings):
        #     chunk_id = str(uuid.uuid4())
        #     await chunkRepo.batch_insert_chunks([(chunk_id, chunk.text, embedding.tolist(), doc_id)])
        await chunkRepo.batch_insert_chunks([(str(uuid.uuid4()), chunk.text, embedding, doc_id) for chunk, embedding in zip(chunks, embeddings_str)])
DocumentProcessor = DocumentProcessor()