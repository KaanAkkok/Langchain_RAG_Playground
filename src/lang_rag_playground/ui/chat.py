# Sohbet: kullanıcı mesajını graph'a gönderir, node olaylarını adım adım sohbete ve diyagrama yansıtır.
#
# YAPILACAKLAR
#
# 1. async def respond(message, chat_history, user_id, thread_id) -> AsyncIterator[(chat_history, diagram)]
#    - Kullanıcı mesajını chat_history'ye ekle ve hemen yield et (mesaj ekranda anında görünsün).
#    - graph.astream(
#          {"messages": [HumanMessage(message)]},
#          config={"configurable": {"thread_id": thread_id}, "metadata": {"user_id": user_id}},
#          context=Context(user_id=user_id),
#          stream_mode="updates",
#      )
#      ile her node bittiğinde gelen {node_adı: güncelleme} olayını işle:
#        * graph_view.render(active_node=node_adı, visited=...) ile diyagramı güncelle.
#        * NODE_STEPS'e göre bir adım mesajı ekle ve yield et.
#    - metadata.user_id: history.py'nin yalnızca bu kullanıcının thread'lerini listeleyebilmesi için gerekli.
#
# 2. NODE_STEPS: node adı → adım metni (güncellemedeki değerlerle doldurulur)
#    - input_guardrails  → "🛡️ Girdi kontrolü" (PII maskelendiyse belirt)
#    - intent            → "🎯 Niyet: {intent} (güven {intent_confidence:.2f})"
#    - memory_recall     → "🧠 {len(memories)} hatıra bulundu"
#    - retrieval         → "🔍 {len(raw_documents)} belge bulundu"
#    - reranker          → "📑 {len(reranked_documents)} belge sıralandı"
#    - assistant         → "✍️ Cevap yazıldı" (retry_count > 0 ise "yeniden yazıldı")
#    - judge             → "⚖️ Doğrulama: geçti / geçmedi ({feedback})"
#    - memory_extract    → "💾 Hafıza güncellendi"
#    - Adım mesajları: gr.ChatMessage(role="assistant", content=..., metadata={"title": ..., "status": "done"})
#      → Chatbot'ta açılır kapanır gri kutular olarak görünür.
#
# 3. Son cevap
#    - output_guardrails ya da blocked olayı geldiğinde son AIMessage'ı normal asistan mesajı olarak ekle.
#    - judge_passed False ise cevabın altına "⚠️ Bu yanıt doğrulanamadı" notu ekle.
#
# 4. Kaynaklar
#    - Son state'teki cited_documents'tan format_citations(documents) ile liste üret:
#        "[1] tez.pdf, s.3, ¶2 — reranker 9.0"
#      (Citation alanları: document_name, page, paragraph_no, reranker_score.)
#    - Son state için: güncellemeleri biriktir ya da sonunda await graph.aget_state(config) kullan.
#
# 5. Hata yönetimi
#    - astream içinde exception olursa (RetryPolicy de tükendiyse) kullanıcıya "Bir hata oluştu: ..."
#      mesajı göster; uygulama çökmesin, diyagramda hatanın çıktığı node'u kırmızı göster.
