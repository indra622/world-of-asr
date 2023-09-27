
import gradio as gr
import gc
import torch
import tqdm
import os
import json


from custom_asr import load_model
from custom_utils import get_writer


hf_token="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"
CONTAINER_ID="3f3ba2d022f6"



def fastconformer_process(
    files,
    device,
    model,
    lang,
    allign,
    diarization,
    batch_size,
    output_format,
    min_speakers,
    max_speakers,
    max_line_count,
    max_line_width,
    interpolate_method,
    return_char_alignments,
    vad_onset,
    vad_offset,
    compute_type,
    beam_size,
    patience,
    length_penalty,
    temperature,
    compression_ratio_threshold,
    logprob_threshold,
    no_speech_threshold,
    initial_prompt,
    progress=gr.Progress(track_tqdm=True),
):
    progress(0, desc="Loading models...")

    if files is None:
        raise gr.Error("Please upload a file to transcribe")

    asr_options = {
        "beam_size": beam_size,
        "patience": None if patience == 0 else patience,
        "length_penalty": None if length_penalty == 0 else length_penalty,
        "temperatures": temperature,
        "compression_ratio_threshold": compression_ratio_threshold,
        "log_prob_threshold": logprob_threshold,
        "no_speech_threshold": no_speech_threshold,
        "condition_on_previous_text": False,
        "initial_prompt": None if initial_prompt == "" else initial_prompt,
        "suppress_tokens": [-1],
        "suppress_numerals": True,
    }

    results = []
    tmp_results = []
    gc.collect()
    torch.cuda.empty_cache()

    ########################
    #####docker zone #######
    ########################

    import docker
    client = docker.from_env()
    container = client.containers.get(CONTAINER_ID)

    def post_processing(str):
        import ast
        result = ast.literal_eval(str)
        return result


    for file in tqdm.tqdm(files, desc="Transcribing", position=0, leave=True, unit="files"):
        audio = f'{file.name}'
        result = container.exec_run(f"python run_nemo.py {audio}", stderr=False)
        result = post_processing(result.output.decode("utf-8"))
        results.append((result[0][0], file.name))

    
    gc.collect()
    torch.cuda.empty_cache()

    

    writer_args = {"max_line_width": None if max_line_width == 0 else max_line_width, "max_line_count": None if max_line_count == 0 else max_line_count, "highlight_words": False}

    for res, audio_path in tqdm.tqdm(results, desc="Writing", position=0, leave=True, unit="files"):

        filename_alpha_numeric = "".join([c for c in os.path.basename(audio_path) if c.isalpha() or c.isdigit() or c == " "]).rstrip()+"_fastconformer"

        

        if not os.path.exists(os.getcwd() + "/output/" + filename_alpha_numeric):
            os.mkdir(os.getcwd() + "/output/" + filename_alpha_numeric)
        
        with open(os.getcwd()+"/output/"+filename_alpha_numeric+'/'+os.path.splitext(os.path.basename(audio_path))[0]+'.txt', 'wt') as f:
            json.dump(res, f)




def whisper_process(
    files,
    device,
    model,
    lang,
    allign,
    diarization,
    batch_size,
    output_format,
    min_speakers,
    max_speakers,
    max_line_count,
    max_line_width,
    interpolate_method,
    return_char_alignments,
    vad_onset,
    vad_offset,
    compute_type,
    beam_size,
    patience,
    length_penalty,
    temperature,
    compression_ratio_threshold,
    logprob_threshold,
    no_speech_threshold,
    initial_prompt,
    progress=gr.Progress(track_tqdm=True),
):
    progress(0, desc="Loading models...")
    import whisperx

    if files is None:
        raise gr.Error("Please upload a file to transcribe")

    asr_options = {
        "beam_size": beam_size,
        "patience": None if patience == 0 else patience,
        "length_penalty": None if length_penalty == 0 else length_penalty,
        "temperatures": temperature,
        "compression_ratio_threshold": compression_ratio_threshold,
        "log_prob_threshold": logprob_threshold,
        "no_speech_threshold": no_speech_threshold,
        "condition_on_previous_text": False,
        "initial_prompt": None if initial_prompt == "" else initial_prompt,
        "suppress_tokens": [-1],
        "suppress_numerals": True,
    }

    results = []
    tmp_results = []
    gc.collect()
    torch.cuda.empty_cache()
    whisper_model = load_model(
        model,
        device=device,
        compute_type=compute_type,
        language=None if lang == "" else lang,
        asr_options=asr_options,
        vad_options={"vad_onset": vad_onset, "vad_offset": vad_offset},
    )
    print(type(files))
    print(files)
    print(files[0].name)

    for file in tqdm.tqdm(files, desc="Transcribing", position=0, leave=True, unit="files"):
        audio = whisperx.load_audio(file.name)
        result = whisper_model.transcribe(audio, batch_size=batch_size)
        results.append((result, file.name))

    del whisper_model
    gc.collect()
    torch.cuda.empty_cache()

    # load whisperx model
    if allign:
        tmp_results = results

        if lang == "":
            lang = "en"

        results = []
        align_model, align_metadata = whisperx.load_align_model(model_name="WAV2VEC2_ASR_LARGE_LV60K_960H" if lang == "en" else None, language_code=lang, device=device)

        for result, audio_path in tqdm.tqdm(tmp_results, desc="Alligning", position=0, leave=True, unit="files"):
            input_audio = audio_path

            if align_model is not None and len(result["segments"]) > 0:
                if result.get("language") != align_metadata["language"]:
                    # load new model
                    print(f"Loading new model for {result['language']}")
                    align_model, align_metadata = whisperx.load_align_model(result["language"], device=device)
                result = whisperx.align(
                    result["segments"], align_model, align_metadata, input_audio, device, interpolate_method=interpolate_method, return_char_alignments=return_char_alignments
                )
            results.append((result, audio_path))

        del align_model
        gc.collect()
        torch.cuda.empty_cache()

    if diarization:
        if hf_token is None:
            print("Please provide a huggingface token to use speaker diarization")
        else:
            tmp_res = results
            results = []
            diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
            for result, input_audio_path in tqdm.tqdm(tmp_res, desc="Diarizing", position=0, leave=True, unit="files"):
                diarize_segments = diarize_model(input_audio_path, min_speakers=min_speakers, max_speakers=max_speakers)
                result = whisperx.diarize.assign_word_speakers(diarize_segments, result)
                results.append((result, input_audio_path))

    writer_args = {"max_line_width": None if max_line_width == 0 else max_line_width, "max_line_count": None if max_line_count == 0 else max_line_count, "highlight_words": False}

    for res, audio_path in tqdm.tqdm(results, desc="Writing", position=0, leave=True, unit="files"):

        filename_alpha_numeric = "".join([c for c in os.path.basename(audio_path) if c.isalpha() or c.isdigit() or c == " "]).rstrip()+"_whisper"



        if not os.path.exists(os.getcwd() + "/output/" + filename_alpha_numeric):
            os.mkdir(os.getcwd() + "/output/" + filename_alpha_numeric)

        writer = get_writer(output_format, os.getcwd() + "/output/" + filename_alpha_numeric)
        writer(res, audio_path, writer_args)
