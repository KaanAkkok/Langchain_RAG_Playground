# Uygulama boyunca tek örnek (singleton) olarak yaşayacak servislerin kurulumu.
#
# YAPILACAKLAR
#
# 1. AppServices dataclass'ı
#    - Alanlar: graph, checkpointer, store, retrieval_service, guardrails, extractor, chunker.
#    - app.py yalnızca bu nesneyi kullanır; hiçbir UI dosyası servisleri kendisi kurmaz.
#
# 2. build_app_services() -> AppServices
#    - embeddings = build_embedding_model()
#    - vectordb = AsyncQdrantVectorDBService(embeddings, host=settings.QDRANT_HOST, port=settings.QDRANT_PORT,
#      api_key=...)
#    - retrieval_service = RetrievalService(vectordb, settings.VECTORDB_KNOWLEDGE_COLLECTION_NAME)
#    - guardrails = Guardrails()
#    - checkpointer = InMemorySaver()   (anlık; kalıcılık istenirse burada SqliteSaver'a geçilir, tek satır)
#    - store = InMemoryStore(index={"embed": embeddings, "dims": <embedding boyutu>, "fields": ["content"]})
#        * dims: vectordb_service'teki gibi bir örnek embed ile ölç ya da settings'e sabit olarak ekle.
#    - graph = workflow_graph(retrieval_service, guardrails, store, checkpointer)
#        * workflow_graph şu an checkpointer'ı kendi içinde oluşturuyor; checkpointer parametresi geri
#          eklenmeli. Geçmiş paneli thread'leri listeleyebilmek için AYNI checkpointer nesnesine erişmek zorunda.
#    - extractor = DocumentExtractor(), chunker = DocumentChunker() (bkz. ingestion.py).
#
# 3. Başlangıç kontrolleri (hata mesajı açık olsun)
#    - Qdrant'a bağlanılabiliyor mu? Bağlanılamıyorsa "Qdrant çalışmıyor: docker run ..." gibi anlaşılır bir hata ver.
#    - Model adları ve API anahtarı settings'te dolu mu?
#
# 4. Graph diyagramı için mermaid metni
#    - graph.get_graph().draw_mermaid() sonucunu burada bir kez üret ve AppServices'e koy (graph_view.py kullanır).
#
# 5. LangGraph Studio için ayrı fabrika fonksiyonu
#    - studio_graph(): checkpointer ve store VERMEDEN workflow_graph çağırır (langgraph dev bunları kendisi sağlar).
#    - langgraph.json bu fonksiyonu gösterecek:
#        {"dependencies": ["."], "graphs": {"rag": "src/lang_rag_playground/ui/services.py:studio_graph"},
#         "env": ".env"}
