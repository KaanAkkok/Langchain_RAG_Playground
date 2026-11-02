from langchain_core.documents import Document
from langchain_core.runnables import Runnable
from langchain.tools import tool, ToolRuntime 

from lang_rag_playground.models.agent_context_model import AgentContext
from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.core.settings import settings
from lang_rag_playground.retrieval.reranking import rerank_documents
from lang_rag_playground.retrieval.retrieval_service import RetrievalService
from lang_rag_playground.nodes.utils import format_sources

logger = get_logger(__name__)


def make_search_documents_tool(
    retrieval_service: RetrievalService,
    reranker_chain: Runnable,
    candidates: int = settings.RERANK_CANDIDATES,
    top_k: int = settings.TOP_K_CANDIDATES,
    min_score: float = settings.MIN_RERANK_SCORE,
):
    not_found = (
        "Bu sorguyla ilgili belge bulunamadı. Farklı kelimelerle tekrar aramayı dene; "
        "arama hakkın bittiyse kullanıcıya bilginin yüklenen dokümanlarda bulunamadığını söyle."
    )

    @tool
    async def search_documents(
        query: str,
        runtime: ToolRuntime[AgentContext],
    ) -> str:
        """Yüklenen dokümanlarda (tez, rapor, makale, vs ...) arama yapar ve ilgili pasajları numaralı kaynaklar olarak döndürür.

        Kullanıcının dokümanlarla ilgili her sorusunda, cevap vermeden önce çağır.
        Sohbet, selamlaşma ve kapsam dışı isteklerde çağırma.
        Sonuçlar soruyu karşılamıyorsa farklı kelimelerle (eş anlamlı, akademik terim) tekrar çağır.

        Args:
            query: Kısa ve anahtar kelime odaklı arama sorgusu. Türkçe veya İngilizce olabilir.
        """
        if not query or not query.strip():
            logger.warning("search_documents called with an empty query.")
            return not_found
        candidate_docs = await retrieval_service.search(query=query, top_k=candidates)
        if not candidate_docs:
            logger.info(f"search_documents('{query}'): no candidates.")
            return not_found
        try:
            documents = await rerank_documents(
                chain=reranker_chain,
                query=query,
                candidates=candidate_docs,
                top_k=top_k,
                min_score=min_score
            )
        except Exception as e:
            logger.warning(f"Rerank failed, falling back to vector order: {e}")
            documents = candidate_docs[:top_k]
        if not documents:
            logger.info(f"search_documents('{query}'): no candidate passed min_score={min_score}.")
            return not_found
        start = len(runtime.context.sources) + 1
        runtime.context.sources.extend(documents)
        scores = [doc.metadata.get("reranker_score") for doc in documents]
        logger.info(
            f"search_documents('{query}'): {len(candidate_docs)} candidates, kept {len(documents)} "
            f"as sources [{start}-{start + len(documents) - 1}], scores: {scores}"
        )
        formatted_sources = format_sources(documents, start=start)
        return f"Bulunan kaynaklar:\n\n{formatted_sources}"
    return search_documents