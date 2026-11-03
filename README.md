# Agentic RAG Playground

PDF dokümanlar üzerinde soru cevaplayan, kaynak gösteren bir **Agentic RAG** uygulaması. LangChain, LangGraph, Qdrant (hibrit arama) ve Gemini ile yazılmıştır; arayüz Gradio'dur.

## Gereksinimler

| Araç | Not |
|---|---|
| Python 3.12+ | `uv` gerekirse kendisi indirir |
| [uv](https://docs.astral.sh/uv/getting-started/installation/) | Paket ve sanal ortam yöneticisi |
| [Docker](https://docs.docker.com/get-docker/) | Qdrant için |
| Gemini API anahtarı | [Google AI Studio](https://aistudio.google.com/apikey) üzerinden ücretsiz alınabilir |
| Tesseract OCR (opsiyonel) | Sadece taranmış (görüntü) PDF'ler için, `tur` ve `eng` dil paketleriyle |

## Kurulum

```bash
# 1. Repoyu klonla
git clone <repo-adresi>
cd lang_rag_playground

# 2. Bağımlılıkları kur (pytest dahil geliştirme araçları da kurulur)
uv sync

# 3. Ortam değişkenlerini hazırla
cp .env.example .env          # Windows PowerShell: Copy-Item .env.example .env
```

`.env` dosyasını açıp en az `GEMINI_API_KEY` değerini gir. Diğer değerler varsayılan haliyle çalışır.

```bash
# 4. Qdrant'ı başlat
docker compose up -d qdrant
```

Qdrant panosu: http://localhost:6333/dashboard

## Çalıştırma

```bash
docker compose up -d --build
```

Tarayıcıda http://localhost:7860 adresini aç. PDF yükle ve soru sor. Arayüzden graph türünü seçebilirsin:
- **workflow**: Akış sabittir; her bilgi sorusunda arama yapılır.
- **agentic**: Asistan, arama aracını ne zaman ve hangi sorguyla çağıracağına kendisi karar verir.

İlk çalıştırmada knowledge base boş olacağından dolayı önce PDF yükleyin ve ardından sorular sorun. PDF yükleme ve chunklama işlemi biraz zaman alabilir.


## Değerlendirme (evaluation)

`data/evaluation/` altındaki doküman ve ground truth seti ile retrieval metriklerini hesaplar (Qdrant çalışıyor olmalı):

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
