# Agentic RAG Playground

PDF dokümanlar üzerinde soru cevaplayan, kaynak gösteren bir **Agentic RAG** uygulaması. LangChain, LangGraph, Qdrant (hibrit arama) ve Gemini ile yazılmıştır; arayüz Gradio'dur.

## Gereksinimler

| Araç | Not |
|---|---|
| [Docker](https://docs.docker.com/get-docker/) (Docker Compose dahil) | Uygulama ve Qdrant konteynerde çalışır |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Testleri yerelde çalıştırmak için; Python 3.12'yi gerekirse kendisi indirir |
| Gemini API anahtarı | [Google AI Studio](https://aistudio.google.com/apikey) üzerinden ücretsiz alınabilir |

## Kurulum

```bash
# 1. Repoyu klonla
git clone <repo-adresi>
cd lang_rag_playground

# 2. Ortam değişkenlerini hazırla
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env

# 3. Testler için yerel bağımlılıkları kur (pytest dahil)
uv sync
```

`.env` dosyasını açıp en az `GEMINI_API_KEY` değerini gir. Diğer değerler varsayılan haliyle çalışır; Qdrant adresi konteyner içinde otomatik ayarlanır.

## Çalıştırma

```bash
docker compose up --build
```

Bu komut uygulama imajını derler, Qdrant ve uygulamayı başlatır; loglar terminalde akar. Durdurmak için `Ctrl+C`. Kodda değişiklik yaptıktan sonra aynı komutu tekrar çalıştır; `--build` imajı yeni kodla yeniden derler. İlk derleme bağımlılıkları indirdiği için birkaç dakika sürer.

Arka planda çalıştırmak istersen `docker compose up -d --build`, logları izlemek için `docker compose logs -f app`.

Tarayıcıda http://localhost:7860 adresini aç. PDF yükle ve soru sor. Arayüzden graph türünü seçebilirsin:
- **workflow**: Akış sabittir; her bilgi sorusunda arama yapılır.
- **agentic**: Asistan, arama aracını ne zaman ve hangi sorguyla çağıracağına kendisi karar verir.

İlk çalıştırmada knowledge base boş olacağından dolayı önce PDF yükleyin ve ardından sorular sorun. PDF yükleme ve chunklama işlemi biraz zaman alabilir.

Qdrant panosu: http://localhost:6333/dashboard

## Testler

```bash
uv run pytest tests/exercises -q
```

Testler API anahtarı ve Qdrant gerektirmez. Lab görevleri ve tek görev çalıştırma için `docs/STUDENT_GUIDE.pdf` dosyasına bak.

## Değerlendirme (evaluation)

`data/evaluation/` altındaki doküman ve ground truth seti ile retrieval metriklerini hesaplar. Yerelde çalışır ama Qdrant'a ihtiyaç duyar; önce `docker compose up -d qdrant` ile Qdrant'ı başlat:

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
