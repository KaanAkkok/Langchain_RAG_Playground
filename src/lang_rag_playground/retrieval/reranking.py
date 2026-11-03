import json

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

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
    """Reranker zincirini kurar: RERANK_TEMPLATE | structured-output LLM.

    Girdi: model_name, temperature.
    Cikti: {"payload": str} alip RerankResponse donduren Runnable.
    Adimlar: LLM'i kur, with_structured_output(RerankResponse) ile sar, sablonla | birlestir.
    """
    llm = build_chat_model(model_name, temperature=temperature)
    return RERANK_TEMPLATE | llm.with_structured_output(RerankResponse)


async def rerank_documents(
    chain: Runnable,
    query: str,
    candidates: list[Document],
    top_k: int,
    min_score: float = settings.MIN_RERANK_SCORE,
) -> list[Document]:
    """Adaylari LLM skoruyla yeniden siralar.

    Girdi: chain, query, candidates, top_k, min_score.
    Cikti: "reranker_score" metadata'li, azalan skorlu, en fazla top_k Document.
    Adimlar: skorlari azalan sirala; min_score alti, yinelenen ve
    gecersiz id'leri ele; metadata'ya reranker_score ekle; ilk top_k'yi dondur.
    """
    if not candidates:
        raise ValueError("The candidates list is empty.")
    if not query or not query.strip():
        raise ValueError("The query is empty or only contains whitespace.")
    passages = [{"id": i, "text": doc.page_content} for i, doc in enumerate(candidates)]
    payload = json.dumps({"query": query, "passages": passages}, ensure_ascii=False)
    response = await chain.ainvoke({"payload": payload})
    if not isinstance(response, RerankResponse):
        raise TypeError("The response is not of type RerankResponse class.")
    # TODO (Görev 3): Öğrenci Rehberi > Görev 3
    # Adım 1: response.scores'u score'a göre azalan sırala
    # Adım 2: score < min_score, tekrar eden id ve id >= len(candidates) olanları atla
    # Adım 3: doc.model_copy ile metadata'ya "reranker_score" ekle
    # Adım 4: ilk top_k belgeyi döndür
    raise NotImplementedError("TODO (Görev 3): Öğrenci Rehberi > Görev 3")
