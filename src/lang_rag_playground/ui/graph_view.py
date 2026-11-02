# Sol paneldeki canlı graph diyagramı: o an çalışan node'u ve bu turda geçilen yolu renklendirir.
#
# YAPILACAKLAR
#
# 1. Temel diyagram
#    - services.py'de bir kez üretilen graph.get_graph().draw_mermaid() metnini kullan.
#    - Bu metin node'ları ve kenarları içerir; renklendirme için sonuna classDef / class satırları eklenir.
#
# 2. render(active_node: str | None, visited: list[str], failed_node: str | None = None) -> str
#    - classDef active  fill:#fde68a,stroke:#d97706   (şu an çalışan node: sarı)
#    - classDef visited fill:#bbf7d0,stroke:#16a34a   (bu turda geçilen node'lar: yeşil)
#    - classDef failed  fill:#fecaca,stroke:#dc2626   (hata veren node: kırmızı)
#    - Her tur başında visited sıfırlanır. Retry döngüsünde assistant/judge tekrar aktif olur; bu,
#      döngünün ekranda görünmesini sağlar.
#    - Dönen değer: "```mermaid\n...\n```" biçiminde markdown.
#
# 3. Gösterim
#    - app.py'de gr.Markdown ile gösterilir (Gradio Markdown mermaid bloklarını çizer).
#    - Çizilmezse yedek plan: gr.HTML + mermaid.js (cdnjs) ile istemci tarafında çizim.
#
# 4. Lejant
#    - Diyagramın altında kısa açıklama: sarı = çalışıyor, yeşil = tamamlandı, kırmızı = hata,
#      kesikli ok = koşullu kenar (router).
