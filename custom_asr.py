import os
import warnings
from typing import List, Union

import ctranslate2
import faster_whisper
import numpy as np
import torch
from transformers import Pipeline
from transformers.pipelines.pt_utils import PipelineIterator

from whisperx.audio import N_SAMPLES, SAMPLE_RATE, load_audio, log_mel_spectrogram
from whisperx.vad import load_vad_model, merge_chunks
from whisperx.types import TranscriptionResult, SingleSegment
from whisperx.asr import FasterWhisperPipeline
import whisperx.asr as wasr


def load_model(whisper_arch,
               device,
               device_index=0,
               compute_type="float16",
               asr_options=None,
               language=None,
               vad_options=None,
               model=None,
               task="transcribe",
               download_root=None):
    '''Load a Whisper model for inference.
    Args:
        whisper_arch: str - The name of the Whisper model to load.
        device: str - The device to load the model on.
        compute_type: str - The compute type to use for the model.
        options: dict - A dictionary of options to use for the model.
        language: str - The language of the model. (use English for now)
        download_root: Optional[str] - The root directory to download the model to.
    Returns:
        A Whisper pipeline.
    '''

    if whisper_arch.endswith(".en"):
        language = "en"

    model = WhisperModel(whisper_arch,
                         device=device,
                         device_index=device_index,
                         compute_type=compute_type,
                         download_root=download_root)
    if language is not None:
        tokenizer = faster_whisper.tokenizer.Tokenizer(model.hf_tokenizer, model.model.is_multilingual, task=task, language=language)
    else:
        print("No language specified, language will be first be detected for each audio file (increases inference time).")
        tokenizer = None

    default_asr_options =  {
        "beam_size": 5,
        "best_of": 5,
        "patience": 1,
        "length_penalty": 1,
        "temperatures": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
        "compression_ratio_threshold": 2.4,
        "log_prob_threshold": -1.0,
        "no_speech_threshold": 0.6,
        "condition_on_previous_text": False,
        "initial_prompt": None,
        "prefix": None,
        "suppress_blank": True,
        "suppress_tokens": [-1],
        "without_timestamps": True,
        "max_initial_timestamp": 0.0,
        "word_timestamps": False,
        "prepend_punctuations": "\"'“¿([{-",
        "append_punctuations": "\"'.。,，!！?？:：”)]}、",
        "repetition_penalty": 1,
        "no_repeat_ngram_size": 0,
        "prompt_reset_on_temperature": 0.5,
    }
    if asr_options is not None:
        default_asr_options.update(asr_options)
        del default_asr_options["suppress_numerals"]

    default_asr_options = faster_whisper.transcribe.TranscriptionOptions(**default_asr_options)

    default_vad_options = {
        "vad_onset": 0.500,
        "vad_offset": 0.363
    }

    if vad_options is not None:
        default_vad_options.update(vad_options)

    vad_model = load_vad_model(torch.device(device), use_auth_token=None, **default_vad_options)

    return FasterWhisperPipeline(model, vad_model, default_asr_options, tokenizer)


class WhisperModel(wasr.WhisperModel):
    '''
    FasterWhisperModel provides batched inference for faster-whisper.
    Currently only works in non-timestamp mode and fixed prompt for all samples in batch.
    '''

    def generate_segment_batched(self, features: np.ndarray, tokenizer: faster_whisper.tokenizer.Tokenizer, options: faster_whisper.transcribe.TranscriptionOptions, encoder_output = None):
        batch_size = features.shape[0]
        all_tokens = []
        prompt_reset_since = 0
        if options.initial_prompt is not None:
            initial_prompt = " " + options.initial_prompt.strip()
            initial_prompt_tokens = tokenizer.encode(initial_prompt)
            all_tokens.extend(initial_prompt_tokens)
        previous_tokens = all_tokens[prompt_reset_since:]
        prompt = self.get_prompt(
            tokenizer,
            previous_tokens,
            without_timestamps=options.without_timestamps,
            prefix=options.prefix,
        )

        encoder_output = self.encode(features)

        max_initial_timestamp_index = int(
            round(options.max_initial_timestamp / self.time_precision)
        )

        result = self.model.generate(
                encoder_output,
                [prompt] * batch_size,
                # length_penalty=options.length_penalty,
                # max_length=self.max_length,
                # return_scores=True,
                # return_no_speech_prob=True,
                # suppress_blank=options.suppress_blank,
                # suppress_tokens=options.suppress_tokens,
                # max_initial_timestamp_index=max_initial_timestamp_index,
            )

        tokens_batch = [x.sequences_ids[0] for x in result]

        def decode_batch(tokens: List[List[int]]) -> str:
            res = []
            for tk in tokens:
                res.append([token for token in tk if token < tokenizer.eot])
            # text_tokens = [token for token in tokens if token < self.eot]
            return tokenizer.tokenizer.decode_batch(res)

        text = decode_batch(tokens_batch)

        return text

    def encode(self, features: np.ndarray) -> ctranslate2.StorageView:
        # When the model is running on multiple GPUs, the encoder output should be moved
        # to the CPU since we don't know which GPU will handle the next job.
        to_cpu = self.model.device == "cuda" and len(self.model.device_index) > 1
        # unsqueeze if batch size = 1
        if len(features.shape) == 2:
            features = np.expand_dims(features, 0)
        features = faster_whisper.transcribe.get_ctranslate2_storage(features)

        return self.model.encode(features, to_cpu=to_cpu)
