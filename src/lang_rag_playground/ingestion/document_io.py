import hashlib
import os
from pathlib import Path

import aiofiles

from lang_rag_playground.core.exceptions import DocumentSavingError
from lang_rag_playground.models.file_type_model import FileType


class DocumentIO:
    def __init__(
        self,
        encoding: str = "utf-8",
    ):
        self.encoding = encoding

    async def save_document(
        self, content: str | bytes, filename: str, save_dir: Path, file_type: FileType
    ) -> Path:
        if not content or content == "" or not filename:
            raise ValueError("Content and filename must be provided.")
        ext = file_type.value if hasattr(file_type, "value") else file_type
        file_path = save_dir / f"{filename}.{ext}"
        os.makedirs(file_path.parent, exist_ok=True)
        try:
            if isinstance(content, bytes):
                async with aiofiles.open(file=file_path, mode="wb") as f:
                    await f.write(content)
            elif isinstance(content, str):
                async with aiofiles.open(
                    file=file_path, mode="w", encoding=self.encoding
                ) as f:
                    await f.write(content)
            else:
                raise TypeError("Content must be of type str or bytes.")
        except DocumentSavingError as e:
            raise DocumentSavingError(f"Error occurred while saving document: {e}")
        return file_path

    def read_file(self, file_path: Path) -> tuple[str, str]:
        with open(file_path, "rb", encoding=self.encoding) as f:
            file_bytes = f.read()
            hash_value = hashlib.sha256(file_bytes).hexdigest()
        return file_bytes.decode(self.encoding), hash_value
