from __future__ import annotations

from typing import Any, Dict, Optional, List
import gc
import logging

from app.core.models.base import ASRModelBase

logger = logging.getLogger(__name__)


class HFAutoASRModel(ASRModelBase):

    def __init__(self, model_size: str, device: str):
        super().__init__(model_size, device)
        self._processor: Optional[Any] = None
        self._torch: Optional[Any] = None
        self._architecture: Optional[str] = None

    def load_model(self) -> None:
        try:
            import torch
            from transformers import (
                AutoModelForCTC,
                AutoModelForSpeechSeq2Seq,
                AutoProcessor,
                pipeline,
            )

            self._torch = torch
            model_id = self.model_size
            use_cuda = self.device == "cuda" and torch.cuda.is_available()
            device_index = 0 if use_cuda else -1
            torch_dtype = torch.float16 if use_cuda else torch.float32

            logger.info(
                "Loading HF Auto ASR model: %s (device=%s)",
                model_id,
                "cuda" if use_cuda else "cpu",
            )

            errors: List[str] = []

            try:
                processor = AutoProcessor.from_pretrained(model_id)
                model = AutoModelForSpeechSeq2Seq.from_pretrained(
                    model_id,
                    torch_dtype=torch_dtype,
                )
                if use_cuda:
                    model.to("cuda")

                tokenizer = getattr(processor, "tokenizer", None)
                feature_extractor = getattr(processor, "feature_extractor", None)

                self.model = pipeline(
                    task="automatic-speech-recognition",
                    model=model,
                    tokenizer=tokenizer,
                    feature_extractor=feature_extractor,
                    device=device_index,
                    torch_dtype=torch_dtype,
                )
                self._processor = processor
                self._architecture = "seq2seq"
                self.is_loaded = True
                logger.info("HF Auto ASR loaded as seq2seq: %s", model_id)
                return
            except Exception as exc:
                errors.append(f"seq2seq load failed: {exc}")

            try:
                processor = AutoProcessor.from_pretrained(model_id)
                model = AutoModelForCTC.from_pretrained(
                    model_id,
                    torch_dtype=torch_dtype,
                )
                if use_cuda:
                    model.to("cuda")

                tokenizer = getattr(processor, "tokenizer", None)
                feature_extractor = getattr(processor, "feature_extractor", None)

                self.model = pipeline(
                    task="automatic-speech-recognition",
                    model=model,
                    tokenizer=tokenizer,
                    feature_extractor=feature_extractor,
                    device=device_index,
                    torch_dtype=torch_dtype,
                )
                self._processor = processor
                self._architecture = "ctc"
                self.is_loaded = True
                logger.info("HF Auto ASR loaded as ctc: %s", model_id)
                return
            except Exception as exc:
                errors.append(f"ctc load failed: {exc}")

            raise RuntimeError(
                "Failed to load Hugging Face ASR model "
                f"'{model_id}'. "
                + " | ".join(errors)
            )

        except Exception as exc:
            logger.error("Failed to initialize HF Auto ASR: %s", exc)
            raise

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self.is_loaded:
            self.load_model()

        if self.model is None:
            raise RuntimeError("HF Auto ASR pipeline is not initialized")

        generate_kwargs: Dict[str, Any] = {}
        initial_prompt = params.get("initial_prompt")
        if initial_prompt and self._architecture == "seq2seq":
            generate_kwargs["prompt"] = initial_prompt

        if language and language != "auto" and self._architecture == "seq2seq":
            processor = self._processor
            if processor is not None:
                try:
                    decoder_prompt_ids = processor.get_decoder_prompt_ids(
                        language=language,
                        task="transcribe",
                    )
                    if decoder_prompt_ids:
                        generate_kwargs["forced_decoder_ids"] = decoder_prompt_ids
                except AttributeError:
                    logger.debug(
                        "Processor does not support language decoder prompt ids: %s",
                        self.model_size,
                    )

        run_kwargs: Dict[str, Any] = {"return_timestamps": True}
        if generate_kwargs:
            run_kwargs["generate_kwargs"] = generate_kwargs

        try:
            output = self.model(audio_path, **run_kwargs)
        except Exception as exc:
            logger.warning(
                "Timestamped inference failed for %s, fallback without timestamps: %s",
                self.model_size,
                exc,
            )
            fallback_kwargs: Dict[str, Any] = {}
            if generate_kwargs:
                fallback_kwargs["generate_kwargs"] = generate_kwargs
            output = self.model(audio_path, **fallback_kwargs)

        text = str(output.get("text", "")).strip()
        chunks = output.get("chunks")

        segments: List[Dict[str, Any]] = []
        if isinstance(chunks, list):
            for chunk in chunks:
                if not isinstance(chunk, dict):
                    continue
                ts = chunk.get("timestamp")
                if not isinstance(ts, (tuple, list)) or len(ts) != 2:
                    continue

                start = float(ts[0]) if ts[0] is not None else 0.0
                end = float(ts[1]) if ts[1] is not None else start
                chunk_text = str(chunk.get("text", "")).strip()
                if not chunk_text:
                    continue
                segments.append({"start": start, "end": end, "text": chunk_text})

        if not segments and text:
            segments = [{"start": 0.0, "end": 0.0, "text": text}]

        return {"segments": segments}

    def unload_model(self) -> None:
        if self.model is not None:
            del self.model
            self.model = None

        self._processor = None
        self._architecture = None
        self.is_loaded = False

        gc.collect()
        if self._torch is not None and self.device == "cuda":
            try:
                self._torch.cuda.empty_cache()
            except Exception:
                logger.debug("CUDA cache clear skipped")
