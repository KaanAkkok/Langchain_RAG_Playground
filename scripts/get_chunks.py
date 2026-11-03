from pathlib import Path
import json
import aiofiles

from lang_rag_playground.retrieval.retrieval_service import RetrievalService
from lang_rag_playground.retrieval.vectordb_service import AsyncQdrantVectorDBService
from lang_rag_playground.ingestion.document_chunker import DocumentChunker
from lang_rag_playground.ingestion.document_io import DocumentIO
from lang_rag_playground.ingestion.document_extractor import DocumentExtractor
from lang_rag_playground.models.file_type_model import FileType
from lang_rag_playground.core.settings import settings


async def save_documents_to_json(documents: list, output_path: Path) -> None:
    documents_dict = [document.__dict__ for document in documents]
    if output_path.exists():
        async with aiofiles.open(output_path, "r", encoding="utf-8") as f:
            content = await f.read()
            existing_documents = json.loads(content) if content.strip() else []
    else:
        existing_documents = []
    existing_documents.extend(documents_dict)
    async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(existing_documents, ensure_ascii=False, indent=4))



async def init_vector_store_and_save_chunks(
    retriever: RetrievalService,
    document_chunker: DocumentChunker,
    document_io: DocumentIO,
    document_extractor: DocumentExtractor,
    collection_name: str,
    output_path: Path,
    document_paths: list[Path | str] | None = None,
) -> None:
    """
    Initialize the vector store, retrieve chunks based on the given query, and save them to a JSON file.

    Args:
        retriever (RetrievalService): The retrieval service instance.
        collection_name (str): The name of the collection to use.
        output_path (Path): The path to the output JSON file.
        document_chunker (DocumentChunker): The document chunker instance.
        document_io (DocumentIO): The document I/O instance.
        document_extractor (DocumentExtractor): The document extractor instance.
        document_paths (list[Path | str] | None): A list of paths to the documents to be stored in the vector store.
    """
    fixed_document_paths: list[Path] = []
    if document_paths is not None:
        fixed_document_paths.extend([Path(path) for path in document_paths])
    else:
        fixed_document_paths.extend(Path(settings.EVALUATION_DOCUMENTS_DIR).glob("*.pdf"))
    
    if not await retriever.is_collection_exists(collection_name):
        for doc_path in fixed_document_paths:
            if not doc_path.exists():
                raise FileNotFoundError(f"Document not found: {doc_path}")
            filename = doc_path.stem
            content = doc_path.read_bytes()
            saved_file_path = await document_io.save_document(
                content=content,
                filename=filename,
                save_dir=Path(settings.EVALUATION_DOCUMENTS_DIR),
                file_type=FileType.PDF,
            )
            content = document_extractor.extract(saved_file_path)
            saved_extracted_file_path = await document_io.save_document(
                content=content.encode("utf-8"),
                filename=filename,
                save_dir=Path(settings.SAVED_DOCUMENTS_DIR),
                file_type=FileType.MD,
            )
            chunks = await document_chunker.chunk(content=content, document_path=saved_extracted_file_path)
            await retriever.store_documents(chunks)
            await save_documents_to_json(chunks, output_path)
    else:
        raise NotImplementedError(f"Collection '{collection_name}' already exists. Retrieval of chunks from existing collection is not implemented yet.")


if __name__ == "__main__":
    import asyncio
    from lang_rag_playground.retrieval.retrieval_service import RetrievalService
    from lang_rag_playground.retrieval.vectordb_service import AsyncQdrantVectorDBService
    from lang_rag_playground.services.llm import build_embedding_model

    embedding_model = build_embedding_model()
    vector_store = AsyncQdrantVectorDBService(
        embedding=embedding_model
    )
    retriever = RetrievalService(
        vector_store=vector_store,
        collection_name=settings.VECTORDB_EVALUATION_COLLECTION_NAME
    )
    output_path = Path("data/evaluation/retrieved_chunks.json")

        
    asyncio.run(init_vector_store_and_save_chunks(
        retriever=retriever, 
        document_chunker=DocumentChunker(embedding_model=embedding_model),
        document_io=DocumentIO(),
        document_extractor=DocumentExtractor(),
        collection_name=settings.VECTORDB_EVALUATION_COLLECTION_NAME,
        output_path=output_path
    ))
