from langchain.tools import ToolRuntime, tool
from langchain_core.runnables import Runnable

from lang_rag_playground.core.exceptions import RerankerError
from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.core.settings import settings
from lang_rag_playground.models.agent_context_model import AgentContext
from lang_rag_playground.nodes.utils import format_sources
from lang_rag_playground.retrieval.reranking import rerank_documents
from lang_rag_playground.retrieval.retrieval_service import RetrievalService

NOT_FOUND_ANSWER = "Bu sorguyla ilgili belge bulunamadı. Farklı kelimelerle tekrar aramayı dene; arama hakkın bittiyse kullanıcıya bilginin yüklenen dokümanlarda bulunamadığını söyle."

logger = get_logger(__name__)


def make_search_documents_tool(
    retrieval_service: RetrievalService,
    reranker_chain: Runnable,
    candidates: int = settings.RERANK_CANDIDATES,
    top_k: int = settings.TOP_K_CANDIDATES,
    min_score: float = settings.MIN_RERANK_SCORE,
):
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
        logger.info(f"search_documents called with query: '{query}'")
        if not query or not query.strip():
            logger.warning("search_documents called with an empty query.")
            return NOT_FOUND_ANSWER
        # TODO (Görev 8): Öğrenci Rehberi > Görev 8 (aday getirme ve rerank)
        # Adım 1: retrieval_service.search ile `candidates` adet aday getir (await).
        # Adım 2: Aday yoksa NOT_FOUND_ANSWER döndür.
        # Adım 3: rerank_documents ile yeniden sırala; RerankerError olursa candidate_docs[:top_k] kullan.
        # Adım 4: Hiç belge kalmadıysa NOT_FOUND_ANSWER döndür.
        raise NotImplementedError("TODO (Görev 8): Öğrenci Rehberi > Görev 8 (aday getirme ve rerank)")
        # TODO (Görev 8): Öğrenci Rehberi > Görev 8 (kaynak biriktirme)
        # Adım 1: start = şimdiye kadar biriken kaynak sayısı + 1 (runtime.context.sources).
        # Adım 2: documents'ı runtime.context.sources'a ekle (extend).
        # Adım 3: format_sources(documents, start=start) ile metni üret ve 'Bulunan kaynaklar:' başlığıyla döndür.
        raise NotImplementedError("TODO (Görev 8): Öğrenci Rehberi > Görev 8 (kaynak biriktirme)")

    return search_documents
