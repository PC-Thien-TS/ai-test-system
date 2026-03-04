from __future__ import annotations

import os
from pathlib import Path


class LocalSentenceTransformerEmbedder:
    def __init__(
        self,
        *,
        model_name: str,
        embedding_local_path: str | None = None,
        local_files_only: bool = True,
    ) -> None:
        self.model_name = model_name
        self.embedding_local_path = embedding_local_path
        self.local_files_only = local_files_only
        self._model = None

    def _load_model(self):
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for KB embeddings. "
                "Install it locally with 'pip install sentence-transformers'."
            ) from exc

        model_ref = Path(self.embedding_local_path) if self.embedding_local_path else self.model_name
        kwargs = {"local_files_only": self.local_files_only}
        try:
            return SentenceTransformer(str(model_ref), **kwargs)
        except Exception as exc:
            model_hint = self.embedding_local_path or self.model_name
            raise RuntimeError(
                "Failed to load the local embedding model. "
                f"Expected a preloaded model at '{model_hint}' or inside the local Hugging Face cache."
            ) from exc

    @property
    def model(self):
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def embed_texts(self, texts: list[str]):
        if not texts:
            raise ValueError("No texts provided for embedding.")
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

    def embedding_dimension(self) -> int:
        return int(self.embed_texts(["dimension probe"]).shape[1])
