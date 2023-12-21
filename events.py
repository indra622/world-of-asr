
import gradio as gr
import gc
import torch
import tqdm
import os
import json

from custom_asr import load_model
from custom_utils import get_writer, format_output_largev3

hf_token=str(os.environ['HF_TOKEN'])
CONTAINER_ID=str(os.environ['CONTAINER_ID'])


def origin_whisper_process(
    files,
    device,
    model,
    lang,
    diarization,
    output_format,
    min_speakers,
    max_speakers,
    beam_size,
    patience,
    length_penalty,
    temperature,
    compression_ratio_threshold,
    logprob_threshold,
    no_speech_threshold,
    initial_prompt,
    condition_on_previous_text,
    remove_punctuation_from_words,
    remove_empty_words,
    progress=gr.Progress(track_tqdm=True),
):
    progress(0, desc="Loading models...")
    import whisper_timestamped as whisper

    if files is None:
        raise gr.Error("Please upload a file to transcribe")

    results = []
    tmp_results = []
    gc.collect()
    torch.cuda.empty_cache()
    whisper_model = whisper.load_model(model,device=device)

    for file in tqdm.tqdm(files, desc="Transcribing", position=0, leave=True, unit="files"):
        audio = whisper.load_audio(file.name)
        result = whisper.transcribe(whisper_model, audio, beam_size=beam_size, 
                                    language=None if lang == "" else lang, vad='auditok', 
                                    temperature=temperature, condition_on_previous_text=condition_on_previous_text,
                                    initial_prompt=initial_prompt, length_penalty=length_penalty, patience=patience,
                                    compression_ratio_threshold=compression_ratio_threshold, logprob_threshold=logprob_threshold,
                                    no_speech_threshold=no_speech_threshold, remove_punctuation_from_words=remove_punctuation_from_words,
                                    remove_empty_words=remove_empty_words, 
                                    )
        results.append((result, file.name))

    del whisper_model
    gc.collect()
    torch.cuda.empty_cache()

    if diarization:
        from custom_diarize import WeSpeakerResNet34
        import librosa
        from custom_diarize import AgglomerativeClustering
        import numpy as np

        embedding_model = WeSpeakerResNet34.load_from_checkpoint('wespeaker-voxceleb-resnet34-LM.bin', strict=False, map_location='cpu')
        embedding_model.eval()
        embedding_model.to('cpu')

        audio, sr = librosa.load(file.name, sr=16000, mono=True)
        
        tmp_results = results
        results = []
        for result in tmp_results:
            embeddings = []
            for transcript in result[0]["segments"]:
                start, end = transcript["start"], transcript["end"]
                audio_segment = audio[int(start * sr):int(end * sr)]
                audio_segment = torch.Tensor(audio_segment).reshape(1, 1, -1)
                embedding = embedding_model(audio_segment)
                embeddings.append(embedding.detach().numpy())
        
            cluster_model = AgglomerativeClustering()
            cluster_model.set_num_clusters(embedding.shape[0], min_clusters=min_speakers, max_clusters=max_speakers)
            clusters = cluster_model.cluster(np.vstack(embeddings))
            clusters = list(clusters)

            if len(result[0]['segments']) != len(clusters):
                print("Error: number of segments and number of clusters do not match")

            output = {
                'segments': [
                    {
                        'start': segment['start'],
                        'end': segment['end'],
                        'text': segment['text'],
                        'speaker': f"발언자_{clusters.pop(0)}",
                        
                    }
                    for segment in result[0]['segments']
                ],
            }

            results.append((output, file.name))

    del embedding_model
    gc.collect()
    torch.cuda.empty_cache()

    writer_args = {"max_line_width": None, "max_line_count": None, "highlight_words": False}

    for res, audio_path in tqdm.tqdm(results, desc="Writing", position=0, leave=True, unit="files"):
        filename_alpha_numeric = "".join([c for c in os.path.basename(audio_path) if c.isalpha() or c.isdigit() or c == " "]).rstrip()+"_original_whisper"
        if not os.path.exists(os.getcwd() + "/output/" + filename_alpha_numeric):
            os.mkdir(os.getcwd() + "/output/" + filename_alpha_numeric)
        writer = get_writer(output_format, os.getcwd() + "/output/" + filename_alpha_numeric)
        writer(res, audio_path, writer_args)
    return os.getcwd()+"/output/"+filename_alpha_numeric+"/"+os.path.splitext(os.path.basename(audio_path))[0]+"."+output_format

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
    print("MODEL:"+str(model))
    if model == "large-v3":
        from faster_whisper import WhisperModel

        whisper_model = WhisperModel(model, device=device, compute_type=compute_type)
    else:
    
        whisper_model = load_model(
            model,
            device=device,
            compute_type=compute_type,
            language=None if lang == "" else lang,
            asr_options=asr_options,
            vad_options={"vad_onset": vad_onset, "vad_offset": vad_offset},
        )
    print(files[0].name)
    print("lang!!!:"+lang)

    for file in tqdm.tqdm(files, desc="Transcribing", position=0, leave=True, unit="files"):
        if model == "large-v3":
            allign=False
            
            segs,info = whisper_model.transcribe(file.name, language=None if lang == "" else lang)
            result = format_output_largev3(segs)

        else:
            audio = whisperx.load_audio(file.name)
            result = whisper_model.transcribe(audio, batch_size=batch_size, )
        results.append((result, file.name))

    del whisper_model
    gc.collect()
    torch.cuda.empty_cache()

    if diarization:
        if hf_token is None:
            print("Please provide a huggingface token to use speaker diarization")
        else:
            from custom_diarize import WeSpeakerResNet34
            import librosa
            from custom_diarize import AgglomerativeClustering
            import numpy as np

            embedding_model = WeSpeakerResNet34.load_from_checkpoint('wespeaker-voxceleb-resnet34-LM.bin', strict=False, map_location='cpu')
            embedding_model.eval()
            embedding_model.to('cpu')

            audio, sr = librosa.load(file.name, sr=16000, mono=True)
            
            tmp_results = results
            results = []
            for result in tmp_results:
                embeddings = []
                for transcript in result[0]["segments"]:
                    start, end = transcript["start"], transcript["end"]
                    audio_segment = audio[int(start * sr):int(end * sr)]
                    audio_segment = torch.Tensor(audio_segment).reshape(1, 1, -1)
                    embedding = embedding_model(audio_segment)
                    embeddings.append(embedding.detach().numpy())
            
                cluster_model = AgglomerativeClustering()
                cluster_model.set_num_clusters(embedding.shape[0], min_clusters=min_speakers, max_clusters=max_speakers)
                clusters = cluster_model.cluster(np.vstack(embeddings))
                clusters = list(clusters)

                if len(result[0]['segments']) != len(clusters):
                    print("Error: number of segments and number of clusters do not match")

                output = {
                    'segments': [
                        {
                            'start': segment['start'],
                            'end': segment['end'],
                            'text': segment['text'],
                            'speaker': f"발언자_{clusters.pop(0)}",
                            
                        }
                        for segment in result[0]['segments']
                    ],
                }

                results.append((output, file.name))

        del embedding_model
        gc.collect()
        torch.cuda.empty_cache()

    writer_args = {"max_line_width": None if max_line_width == 0 else max_line_width, "max_line_count": None if max_line_count == 0 else max_line_count, "highlight_words": False}

    for res, audio_path in tqdm.tqdm(results, desc="Writing", position=0, leave=True, unit="files"):

        filename_alpha_numeric = "".join([c for c in os.path.basename(audio_path) if c.isalpha() or c.isdigit() or c == " "]).rstrip()+"_whisper"

        if not os.path.exists(os.getcwd() + "/output/" + filename_alpha_numeric):
            os.mkdir(os.getcwd() + "/output/" + filename_alpha_numeric)

        writer = get_writer(output_format, os.getcwd() + "/output/" + filename_alpha_numeric)
        writer(res, audio_path, writer_args)
    #print("!!!!!!!!!!!:"+str(type(results))+ str(type(results[0])))
    #api_rtn = [t[0] for t in results if t]
    return os.getcwd()+"/output/"+filename_alpha_numeric+"/"+os.path.splitext(os.path.basename(audio_path))[0]+"."+output_format

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




