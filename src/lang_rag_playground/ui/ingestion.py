# "+" ile yüklenen dosyaları işler: çıkar → chunk'la → Qdrant'a yaz. Graph'tan bağımsız çalışır.
#
# YAPILACAKLAR
#
# 1. async def ingest_files(paths, extractor, chunker, retrieval_service) -> AsyncIterator[str]
#    Her dosya için üç adım (ayrı bir servis sınıfı yok, doğrudan bu üç çağrı):
#      a) content = await asyncio.to_thread(extractor.extract, path)
#         - extract senkron ve yavaş (OCR); to_thread olmadan arayüz donar.
#      b) chunks = await chunker.chunk(content, path)
#      c) count = await retrieval_service.store_documents(chunks)
#    - Her adımda ilerleme mesajı yield et:
#        "📄 tez.pdf: metin çıkarılıyor..." → "✂️ 42 chunk" → "💾 Qdrant'a yazıldı"
#    - Aynı dosya tekrar yüklenirse DB'de kopya oluşmaz (vectordb'deki uuid5 point id'leri aynı chunk'ın
#      üzerine yazar); yalnızca extract süresi boşa gider. Bu kabul edilebilir.
#    - Bir dosya hata verirse (DocumentExtractionError / DocumentChunkingError) o dosyayı "❌" ile raporla,
#      diğerlerine devam et.
#
# 2. Kısıtlar
#    - İzin verilen uzantılar: app.py'deki MultimodalTextbox file_types ile aynı liste.
#    - Boyut sınırı (ör. 50 MB) ve anlaşılır hata mesajı.
#    - OCR'lı PDF'ler yavaştır: işlem bitene kadar mesaj kutusunu devre dışı bırak (interactive=False).
#
# 3. Sohbete bağlama
#    - Mesajda hem dosya hem metin varsa: önce dosyaları işle, sonra soruyu graph'a gönder.
#      Böylece "bu PDF'te örneklem kaç kişi?" tek mesajda çalışır.
