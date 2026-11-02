# Gradio uygulamasının giriş noktası: sayfa yerleşimi ve olay bağlantıları.
# Çalıştırma: uv run python -m lang_rag_playground.ui.app
#
# YAPILACAKLAR
#
# 1. Başlangıç
#    - services.py'deki build_app_services() ile servisleri BİR KEZ kur (graph, checkpointer, store,
#      retrieval, guardrails, extractor, chunker). Her mesajda yeniden kurma: InMemorySaver/InMemoryStore
#      yeniden oluşursa tüm sohbetler ve hafıza kaybolur.
#    - Graph async olduğu için handler'lar `async def` olmalı (Gradio async handler'ları destekler).
#
# 2. Oturum durumu (gr.State, her tarayıcı sekmesine özel)
#    - user_id: oturum açılışında üretilir (ör. uuid4), Context(user_id=...) olarak graph'a verilir.
#    - thread_id: aktif sohbetin kimliği; "Yeni sohbet" ile yenilenir.
#
# 3. Yerleşim (gr.Blocks + gr.Row)
#    - Sol sütun, scale=1 (~1/3): graph_view.py'nin ürettiği canlı graph diyagramı.
#    - Sağ sütun, scale=2 (~2/3):
#        a) gr.Sidebar ya da açılır kapanır gr.Column: geçmiş sohbet listesi (history.py) + "Yeni sohbet" butonu.
#        b) gr.Chatbot(type="messages"): sohbet alanı. Adım mesajları metadata={"title": ...} ile
#           açılır kapanır gösterilir.
#        c) gr.MultimodalTextbox(file_types=[".pdf", ".docx", ".md", ".txt"]): mesaj kutusu + "+" ile dosya ekleme.
#
# 4. Olaylar
#    - Mesaj gönderilince:
#        * Dosya varsa → önce ingestion.py ile işle, ilerlemeyi sohbette göster.
#        * Metin varsa → chat.py'deki stream handler'ı çalıştır; her adımda hem Chatbot'u hem
#          graph diyagramını güncelle (aynı generator iki çıktı döndürür).
#        * Bittiğinde geçmiş listesini yenile.
#    - Geçmişten sohbet seçilince → thread_id'yi değiştir, history.py ile mesajları yükle, Chatbot'a bas.
#    - "Yeni sohbet" → yeni thread_id, Chatbot'u temizle, diyagramı sıfırla.
#
# 5. Başlatma
#    - demo.queue().launch(): queue, generator (stream) handler'ları için gerekli.
#    - if __name__ == "__main__": bloğu.
#
# NOT: LangGraph Studio (langgraph dev) Gradio'ya gömülmez; ayrı çalışır. Bunun için proje köküne
#      langgraph.json eklenecek ve checkpointer/store VERİLMEDEN derlenmiş graph'ı döndüren bir fonksiyon
#      gösterilecek (Studio'da sunucu kendi kalıcılığını sağlar). Bkz. services.py madde 5.
