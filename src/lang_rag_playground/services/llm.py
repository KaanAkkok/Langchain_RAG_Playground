from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from lang_rag_playground.core.settings import settings


def build_chat_model(model_name: str, temperature: float = 0.0) -> BaseChatModel:
    if not model_name:
        raise ValueError("Model name must be provided")
    if not (0.0 <= temperature <= 1.0):
        raise ValueError("Temperature must be between 0.0 and 1.0")
    return init_chat_model(
        model_name.strip(),
        model_provider="google_genai",
        temperature=temperature,
        api_key=settings.GEMINI_API_KEY,
    )


def build_embedding_model(
    model_name: str = settings.GEMINI_EMBEDDING_MODEL,
) -> GoogleGenerativeAIEmbeddings:
    if not model_name:
        raise ValueError("Embedding model name must be provided")
    return GoogleGenerativeAIEmbeddings(
        model=model_name.strip(),
        api_key=settings.GEMINI_API_KEY,
    )
