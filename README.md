# Agentic RAG Playground

PDF dokümanlar üzerinde soru cevaplayan, kaynak gösteren bir **Agentic RAG** uygulaması. LangChain, LangGraph, Qdrant (hibrit arama) ve Gemini ile yazılmıştır; arayüz Gradio'dur.

## Gereksinimler

| Araç | Not |
|---|---|
| [uv](https://docs.astral.sh/uv/getting-started/installation/) veya pip | Bağımlılıkları kurmak ve uygulamayı çalıştırmak için |
| Python 3.12+ | |
| Docker (isteğe bağlı) | Qdrant sunucusunu konteynerde çalıştırmak için |
| Gemini API anahtarı | [Google AI Studio](https://aistudio.google.com/apikey) |

## Kurulum

```bash
# 1. Repoyu klonla
git clone <repo-adresi>
cd langchain_rag_playground

# 2. Ortam değişkenlerini hazırla
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env

# 3. uv kullanıyorsanız bağımlılıkları kurun (pytest dahil)
uv sync
```

`.env` dosyasını açıp en az `GEMINI_API_KEY` değerini girin.

pip ile kurulum için:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Çalıştırma

### uv veya pip + yerel Qdrant (Docker gerekmez)

Yerel çalıştırmada Qdrant verileri `data/qdrant/` altında tutulur; Qdrant sunucusu veya Docker gerekmez.

```bash
uv run lang-rag-playground
# pip ile kurulum yaptıysanız:
lang-rag-playground
```

Tarayıcıda http://localhost:7860 adresini açın. `QDRANT_PATH` değerini değiştirerek veri klasörünü farklı bir konuma taşıyabilirsiniz.

### Docker Compose (alternatif)

```bash
docker compose up --build
```

Bu komut uygulama imajını derler, Qdrant ve uygulamayı başlatır; loglar terminalde akar. Durdurmak için `Ctrl+C`. Kodda değişiklik yaptıktan sonra aynı komutu tekrar çalıştırın; `--build` imajı yeni kodla yeniden derler.

Arka planda çalıştırmak için `docker compose up -d --build`, logları izlemek için `docker compose logs -f app`.

Tarayıcıda http://localhost:7860 adresini açın. PDF yükleyin ve soru sorun. Arayüzden graph türünü seçebilirsiniz:
- **workflow**: Akış sabittir; her bilgi sorusunda arama yapılır.
- **agentic**: Asistan, arama aracını ne zaman ve hangi sorguyla çağıracağına kendisi karar verir.

İlk çalıştırmada knowledge base boş olacağından önce PDF yükleyin. PDF yükleme ve chunklama işlemi biraz zaman alabilir.

Docker modu kullanılıyorsa Qdrant panosu: http://localhost:6333/dashboard

## Testler

```bash
uv run pytest tests/exercises -q
# veya pip ile kurulum yaptıysanız:
python -m pytest tests/exercises -q
```

Testler API anahtarı ve Qdrant gerektirmez. Lab görevleri ve tek görev çalıştırma için `docs/STUDENT_GUIDE.pdf` dosyasına bakın.

## Değerlendirme (evaluation)

`data/evaluation/` altındaki doküman ve ground truth seti ile retrieval metriklerini hesaplar. Yerel Qdrant klasör modunda Docker olmadan çalışır:

```bash
uv run python -m lang_rag_playground.evaluation.eval
# veya pip ile kurulum yaptıysanız:
python -m lang_rag_playground.evaluation.eval
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
