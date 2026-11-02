import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_core.documents import Document

from lang_rag_playground.core.settings import settings
from lang_rag_playground.prompts.prompts import RERANK_PROMPT
from lang_rag_playground.schemas.reranker_schema import RerankResponse
from lang_rag_playground.services.llm import build_chat_model

RERANK_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", RERANK_PROMPT),
        ("human", "{payload}"),
    ]
)


def build_reranker_chain(
    model_name: str = settings.GEMINI_RERANKER_MODEL,
    temperature: float = settings.RERANKER_TEMPERATURE,
) -> Runnable:
    llm = build_chat_model(model_name, temperature=temperature)
    return RERANK_TEMPLATE | llm.with_structured_output(RerankResponse)


async def rerank_documents(
    chain: Runnable, 
    query: str, 
    candidates: list[Document], 
    top_k: int, 
    min_score: float
) -> list[Document]:
    if not candidates:
        raise ValueError("The candidates list is empty.")
    if not query or not query.strip():
        raise ValueError("The query is empty or only contains whitespace.")
    passages = [
        {"id": i, "text": doc.page_content} for i, doc in enumerate(candidates)
    ]
    payload = json.dumps({"query": query, "passages": passages}, ensure_ascii=False)
    response = await chain.ainvoke({"payload": payload})
    if not isinstance(response, RerankResponse):
        raise TypeError("The response is not of type RerankResponse class.")
    reranked_documents = []
    seen_ids = set()
    sorted_scores = sorted(
        response.scores,
        key=lambda item: item.score,
        reverse=True,
    )
    for item in sorted_scores:
        if item.score < min_score:
            continue
        if item.id in seen_ids or item.id >= len(candidates):
            continue
        seen_ids.add(item.id)
        doc = candidates[item.id]
        updated_metadata = {
            **doc.metadata,
            "reranker_score": item.score,
        }
        reranked_documents.append(
            doc.model_copy(update={"metadata": updated_metadata})
        )
    return reranked_documents[:top_k]