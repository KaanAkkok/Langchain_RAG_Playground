# Agentic RAG Playground

PDF dokümanlar üzerinde soru cevaplayan, kaynak gösteren bir **Agentic RAG** uygulaması. LangChain, LangGraph, Qdrant (hibrit arama) ve Gemini ile yazılmıştır; arayüz Gradio'dur.

## Gereksinimler

| Araç | Not |
|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Bağımlılıkları kurmak ve uygulamayı çalıştırmak için; Python 3.12'yi gerekirse kendisi indirir |
| Docker (isteğe bağlı) | Qdrant'ı ayrı bir konteynerde çalıştırmak için |
| Gemini API anahtarı | [Google AI Studio](https://aistudio.google.com/apikey)|

## Kurulum

```bash
# 1. Repoyu klonla
git clone <repo-adresi>
cd langchain_rag_playground

# 2. Ortam değişkenlerini hazırla
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env

# 3. Testler için yerel bağımlılıkları kur (pytest dahil)
uv sync
```

`.env` dosyasını açıp en az `GEMINI_API_KEY` değerini gir. Diğer değerler varsayılan haliyle çalışır; Qdrant adresi konteyner içinde otomatik ayarlanır.

Yerel Qdrant klasör modunda veriler `data/qdrant/` altında tutulur; Qdrant sunucusu veya Docker gerekmez.

## Çalıştırma

### uv + yerel Qdrant (Docker gerekmez)

```bash
uv run lang-rag-playground
```

Tarayıcıda http://localhost:7860 adresini açın. `QDRANT_PATH` değerini değiştirerek veri klasörünü farklı bir konuma taşıyabilirsiniz. Uygulama kapatılıp açıldığında koleksiyonlar bu klasörden yeniden kullanılır.

### Docker Compose (alternatif)

```bash
docker compose up --build
```

Bu komut uygulama imajını derler, Qdrant ve uygulamayı başlatır; loglar terminalde akar. Durdurmak için `Ctrl+C`. Kodda değişiklik yaptıktan sonra aynı komutu tekrar çalıştır; `--build` imajı yeni kodla yeniden derler. İlk derleme bağımlılıkları indirdiği için birkaç dakika sürer.

Arka planda çalıştırmak istersen `docker compose up -d --build`, logları izlemek için `docker compose logs -f app`.

Tarayıcıda http://localhost:7860 adresini aç. PDF yükle ve soru sor. Arayüzden graph türünü seçebilirsin:
- **workflow**: Akış sabittir; her bilgi sorusunda arama yapılır.
- **agentic**: Asistan, arama aracını ne zaman ve hangi sorguyla çağıracağına kendisi karar verir.

İlk çalıştırmada knowledge base boş olacağından dolayı önce PDF yükleyin ve ardından sorular sorun. PDF yükleme ve chunklama işlemi biraz zaman alabilir.

Docker modu kullanılıyorsa Qdrant panosu: http://localhost:6333/dashboard

## Testler

```bash
uv run pytest tests/exercises -q
```

Testler API anahtarı ve Qdrant gerektirmez. Lab görevleri ve tek görev çalıştırma için `docs/STUDENT_GUIDE.pdf` dosyasına bak.

## Değerlendirme (evaluation)

`data/evaluation/` altındaki doküman ve ground truth seti ile retrieval metriklerini hesaplar. Yerel Qdrant klasör modunda Docker olmadan çalışır:

```bash
uv run python -m lang_rag_playground.evaluation.eval
```

## Proje yapısı

```text
src/lang_rag_playground/
├── core/         # Ayarlar, loglama, hata sınıfları
├── services/     # Gemini sohbet ve embedding modelleri
├── ingestion/    # PDF -> Markdown çıkarma (Docling + OCR) ve chunklama
├── retrieval/    # Qdrant hibrit arama ve LLM reranker
├── guardrails/   # Prompt injection ve kişisel veri (PII) maskeleme
├── memory/       # Uzun süreli kullanıcı hafızası
├── nodes/        # LangGraph düğümleri (intent, asistan, judge...)
├── tools/        # Agent araçları (doküman arama, tarih)
├── graphs/       # Router'lar, workflow ve agentic graph
├── evaluation/   # Retrieval ve generation metrikleri
├── models/, schemas/, prompts/
└── ui/           # Gradio arayüzü
```
