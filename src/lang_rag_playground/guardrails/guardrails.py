import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Any, Literal

from langchain.agents.middleware import PIIMatch
from langchain_core.messages import BaseMessage

from lang_rag_playground.core.logger import get_logger
from lang_rag_playground.guardrails.address_pii_masking import address_detector
from lang_rag_playground.guardrails.birth_date_pii_masking import birth_date_detector
from lang_rag_playground.guardrails.card_pii_masking import card_detector
from lang_rag_playground.guardrails.custom_detector import custom_detector
from lang_rag_playground.guardrails.email_pii_masking import email_detector
from lang_rag_playground.guardrails.iban_pii_masking import iban_detector
from lang_rag_playground.guardrails.ip_pii_masking import ip_detector
from lang_rag_playground.guardrails.name_pii_masking import name_detector
from lang_rag_playground.guardrails.phone_pii_masking import phone_detector
from lang_rag_playground.guardrails.plate_pii_masking import plate_detector
from lang_rag_playground.guardrails.prompt_injection import _PROMPT_INJECTION_RE
from lang_rag_playground.guardrails.tckn_pii_masking import tckn_detector

logger = get_logger(__name__)


_INVISIBLE_CHARS = str.maketrans(
    {
        "\x00": "",
        "­": "",
        "\u200b": "",
        "‌": "",
        "‍": "",
        "⁠": "",
        "﻿": "",
        " ": " ",
        " ": " ",
    }
)
INJECTION_REFUSAL = "Güvenlik politikası ihlali tespit edildi. Lütfen sorunuzu farklı bir şekilde ifade edin."

Detector = Callable[[str], list[PIIMatch]]
Content = str | list[str | dict[str, Any]]


@dataclass(frozen=True)
class InputGuardrailResult:
    is_input_safe: bool
    message: BaseMessage | None


class Guardrails:
    def __init__(
        self,
        mode: Literal["strict", "lenient", "loose"] = "strict",
        regex_patterns: list[re.Pattern] | None = None,
        proprietary_dictionary: list[str] | None = None,
        normalization_form: Literal["NFC", "NFD", "NFKC", "NFKD"] = "NFKC",
    ):
        if mode not in ("strict", "lenient", "loose"):
            raise ValueError(f"Unknown mode: {mode!r}")
        self.mode = mode
        self.regex_patterns = list(dict.fromkeys(regex_patterns or []))
        self.proprietary_dictionary = list(
            dict.fromkeys(w for w in proprietary_dictionary or [] if w)
        )
        self.normalization_form: Literal["NFC", "NFD", "NFKC", "NFKD"] = (
            normalization_form
        )

        detectors: dict[str, list[Detector]] = {
            "strict": [
                tckn_detector,
                email_detector,
                phone_detector,
                plate_detector,
                iban_detector,
                card_detector,
                ip_detector,
                birth_date_detector,
                name_detector,
                address_detector,
            ],
            "lenient": [
                tckn_detector,
                email_detector,
                phone_detector,
                plate_detector,
                iban_detector,
                card_detector,
                ip_detector,
            ],
            "loose": [
                tckn_detector,
                email_detector,
                phone_detector,
                card_detector,
            ],
        }
        self.detectors: list[Detector] = detectors[mode]
        if self.regex_patterns:
            self.detectors.append(
                partial(custom_detector, regex_patterns=self.regex_patterns)
            )
        if self.proprietary_dictionary:
            self.detectors.append(self._proprietary_dictionary_detector)

    def _proprietary_dictionary_detector(self, content: str) -> list[PIIMatch]:
        matches = []
        for word in self.proprietary_dictionary:
            for match in re.finditer(
                rf"(?<!\w){re.escape(word)}(?!\w)", content, re.IGNORECASE
            ):
                matches.append(
                    PIIMatch(
                        type="PROPRIETARY_DICTIONARY",
                        value=match.group(),
                        start=match.start(),
                        end=match.end(),
                    )
                )
        return matches

    def _normalize(self, text: str) -> str:
        text = text.translate(_INVISIBLE_CHARS)
        return unicodedata.normalize(self.normalization_form, text).strip()

    def _detect(self, text: str) -> list[PIIMatch]:
        matches = []
        for detector in self.detectors:
            matches.extend(detector(text))
        return matches

    @staticmethod
    def _mask(text: str, matches: list[PIIMatch]) -> str:
        selected: list[PIIMatch] = []
        for match in sorted(
            matches, key=lambda m: (m["start"], -(m["end"] - m["start"]))
        ):
            if selected and match["start"] < selected[-1]["end"]:
                continue
            selected.append(match)
        for match in reversed(selected):
            text = (
                text[: match["start"]]
                + f"[MASKED_{match['type']}]"
                + text[match["end"] :]
            )
        return text

    def _process_text(self, text: str) -> tuple[str, list[PIIMatch]]:
        text = self._normalize(text)
        matches = self._detect(text)
        return self._mask(text, matches), matches

    def _process_content(self, content: Content) -> tuple[Content, list[PIIMatch]]:
        if isinstance(content, str):
            return self._process_text(content)
        if not isinstance(content, list):
            raise TypeError("Content must be a string or a list of content blocks.")
        new_content: list[str | dict[str, Any]] = []
        all_matches: list[PIIMatch] = []
        for block in content:
            if isinstance(block, str):
                block, matches = self._process_text(block)
                all_matches.extend(matches)
            elif isinstance(block, dict) and isinstance(block.get("text"), str):
                text, matches = self._process_text(block["text"])
                block = {**block, "text": text}
                all_matches.extend(matches)
            new_content.append(block)
        return new_content, all_matches

    def _is_prompt_injection(self, message: BaseMessage) -> bool:
        return bool(_PROMPT_INJECTION_RE.search(self._normalize(message.text)))

    def _mask_message(self, message: BaseMessage) -> BaseMessage | None:
        if not message.content:
            return None
        new_content, matches = self._process_content(message.content)
        if new_content == message.content:
            return None
        update: dict[str, Any] = {"content": new_content}
        if matches:
            update["additional_kwargs"] = {
                **message.additional_kwargs,
                "pii_types": sorted({match["type"] for match in matches}),
            }
        return message.model_copy(update=update)

    def input_guardrail(self, message: BaseMessage) -> InputGuardrailResult:
        """Kullanici mesajini guvenlik kontrolunden gecirir.

        Girdi: BaseMessage (kullanici mesaji).
        Cikti: InputGuardrailResult(is_input_safe, message).
        Adimlar:
            1. _is_prompt_injection ile mesaji kontrol et.
            2. Injection varsa logger.warning yaz ve
               InputGuardrailResult(is_input_safe=False, message=None) dondur.
            3. Guvenliyse _mask_message(message) sonucuyla
               InputGuardrailResult(is_input_safe=True, message=...) dondur.
               (_mask_message degisiklik yoksa None dondurur; oldugu gibi birak.)
        """
        # TODO (Görev 4): Öğrenci Rehberi > Görev 4
        # Adım 1: self._is_prompt_injection(message) kontrolü
        # Adım 2: injection ise logla ve is_input_safe=False, message=None dön
        # Adım 3: değilse is_input_safe=True ve self._mask_message(message) ile dön
        raise NotImplementedError("TODO (Görev 4): Öğrenci Rehberi > Görev 4")

    def output_guardrail(self, text: str) -> str:
        """Model ciktisindaki kisisel verileri maskeler.

        Girdi: str (uretilen cevap).
        Cikti: str (PII maskelenmis cevap).
        Adimlar:
            1. self._process_text(text) (maskeli_metin, eslesmeler) dondurur.
            2. Eslesmeleri yok sayip sadece maskeli metni dondur.
        """
        masked_text, _ = self._process_text(text)
        return masked_text
