from langchain.tools import tool
from datetime import datetime
from zoneinfo import ZoneInfo

from lang_rag_playground.core.logger import get_logger

logger = get_logger(__name__)


@tool
def get_today_date() -> str:
    """Bugünün tarihini döndürür. Kullanıcının sorularında tarih ile ilgili bir referans gerekiyorsa çağır. 
    Örn: "Bugün hangi gün?", "Bugünün tarihi nedir?", "Bugün hangi aydayız?".
    """
    logger.info("get_today_date tool is called.")
    now = datetime.now(ZoneInfo("Europe/Istanbul"))

    return (
        f"Bugünün tarihi: {now.strftime('%Y-%m-%d')} "
        f"Saat: {now.strftime('%H:%M:%S')} "
        f"(İstanbul saati, UTC+3)."
    )