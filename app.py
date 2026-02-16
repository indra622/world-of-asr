import gc
import tqdm
import gradio as gr
import os
import torch
import requests
import time

from woa.events import origin_whisper_process, whisper_process, fastconformer_process

if not os.path.exists(os.getcwd() + "/output/"):
    os.mkdir(os.getcwd() + "/output/")


#########################################
############UI zone######################
#########################################


with gr.Blocks() as ui:
    with gr.Tab(label="Whisper"):
        with gr.Row():
            # # input field for audio / video file
            origin_whisper_input_files = gr.Files(label="Input Files")

            def clear():
                return None

            with gr.Column():
                with gr.Row():
                    origin_whisper_btn_run = gr.Button()
                    origin_whisper_btn_reset = gr.Button(value="Reset").click(fn=clear, outputs=[origin_whisper_input_files])

                with gr.Row():
                    # model selection dropdown
                    origin_model = gr.Dropdown(label="Model", choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"], value="large-v3")
                    # langaue hint input
                    origin_lang = gr.Text(label="Language Hint", placeholder="auto | ko | en")

                with gr.Row():
                    with gr.Group():
                        origin_diarization = gr.Checkbox(label="Speaker Diarization", value=True)
                        with gr.Row():
                            origin_min_speakers = gr.Slider(label="Min Speakers", minimum=1, maximum=20, step=1, value=1, visible=True)
                            origin_max_speakers = gr.Slider(label="Max Speakers", minimum=1, maximum=20, step=1, value=5, visible=True)

                            # enable min and max speakers if diarization is enabled
                            def change_interactive2(min, max, val):
                                return [
                                    gr.Number.update(visible=val),
                                    gr.Number.update(visible=val),
                                ]
                            origin_diarization.change(fn=change_interactive2, inputs=[origin_min_speakers, origin_max_speakers, origin_diarization], outputs=[origin_min_speakers, origin_max_speakers])

                    with gr.Group():
                        # device add cuda to dropdown if available
                        origin_device = gr.Dropdown(
                            label="Device", choices=["cpu", "cuda"] if torch.cuda.is_available() else ["cpu"], value="cuda" if torch.cuda.is_available() else "cpu"
                        )
                        condition_on_previous_text = gr.Checkbox(label="Condition on Previous Text", value=False)
                        remove_punctuation_from_words = gr.Checkbox(label="Remove Punctuation", value=False)
                with gr.Group():
                    origin_initial_prompt = gr.Textbox(label="Initial Prompt", placeholder="Enter initial prompt", visible=True)
                with gr.Group():
                    origin_advanced = gr.Checkbox(label="Advanced Options", value=False)

                    def change_visible1(advanced):
                        return [
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Checkbox.update(visible=advanced),
                        ]

                    with gr.Row():
                        remove_empty_words = gr.Checkbox(label="Remove Empty Words", value=False, visible=False)
                        origin_no_speech_threshold = gr.Slider(label="No Speech Threshold", minimum=0, maximum=1, step=0.001, value=0.6, visible=False)
                    with gr.Row():
                        origin_beam_size = gr.Slider(label="Beam Size (only when temperature is 0)", minimum=1, maximum=100, step=1, value=5, visible=False)
                        origin_patience = gr.Slider(label="Patience (0 default)", minimum=0, maximum=100, step=0.01, value=0, visible=False)
                    with gr.Row():
                        origin_length_penalty = gr.Slider(label="Length Penalty (0 default)", minimum=0, maximum=100, step=0.01, value=0, visible=False)
                        origin_temperature = gr.Slider(label="Temperature", minimum=0, maximum=100, step=0.01, value=0, visible=False)
                    with gr.Row():
                        origin_compression_ratio_threshold = gr.Slider(label="Compression Ratio Threshold", minimum=0, maximum=100, step=0.01, value=2.4, visible=False)
                        origin_logprob_threshold = gr.Slider(label="Logprob Threshold", minimum=-10, maximum=10, step=0.01, value=-1, visible=False)
                      
                        origin_advanced.change(
                            fn=change_visible1,
                            inputs=[origin_advanced],
                            outputs=[
                                origin_beam_size,
                                origin_patience,
                                origin_length_penalty,
                                origin_temperature,
                                origin_compression_ratio_threshold,
                                origin_logprob_threshold,
                                origin_no_speech_threshold,
                                remove_empty_words,
                            ],
                        )

                # output format
                origin_output_format = gr.Dropdown(label="Output Format", choices=["all", "json", "txt", "srt", "vtt", "tsv"], value="vtt")

    with gr.Tab(label="FasterWhisper"):
        with gr.Row():
            # # input field for audio / video file
            whisper_input_files = gr.Files(label="Input Files")

            def clear():
                return None

            with gr.Column():
                with gr.Row():
                    whisper_btn_run = gr.Button()
                    whisper_btn_reset = gr.Button(value="Reset").click(fn=clear, outputs=[whisper_input_files])

                with gr.Row():
                    # model selection dropdown
                    model = gr.Dropdown(label="Model", choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"], value="large-v3")
                    # langaue hint input
                    lang = gr.Text(label="Language Hint", placeholder="auto | ko | en")

                with gr.Row():
                    with gr.Group():
                        allign = gr.Checkbox(label="Allign Text", value=True)
                        max_line_width = gr.Slider(label="Max Line Width (0 for default)", minimum=0, step=1, maximum=10000, value=0)
                        max_line_count = gr.Slider(label="Max number of lines in a segment (0 for default)", minimum=0, step=1, maximum=10000, value=0, visible=False)

                        def change_interactive1(max_line_width, max_line_count, val):
                            return [
                                gr.Number.update(visible=val, value=0 if not val else max_line_width),
                                gr.Number.update(visible=not val, value=0 if val else max_line_count),
                            ]

                        allign.change(fn=change_interactive1, inputs=[max_line_width, max_line_count, allign], outputs=[max_line_width, max_line_count])
                        diarization = gr.Checkbox(label="Speaker Diarization", value=True)
                        with gr.Row():
                            min_speakers = gr.Slider(label="Min Speakers", minimum=1, maximum=20, step=1, value=1, visible=True)
                            max_speakers = gr.Slider(label="Max Speakers", minimum=1, maximum=20, step=1, value=5, visible=True)

                            # enable min and max speakers if diarization is enabled
                            def change_interactive2(min, max, val):
                                return [
                                    gr.Number.update(visible=val),
                                    gr.Number.update(visible=val),
                                ]

                            diarization.change(fn=change_interactive2, inputs=[min_speakers, max_speakers, diarization], outputs=[min_speakers, max_speakers])

                    with gr.Group():
                        # device add cuda to dropdown if available
                        device = gr.Dropdown(
                            label="Device", choices=["cpu", "cuda"] if torch.cuda.is_available() else ["cpu"], value="cuda" if torch.cuda.is_available() else "cpu"
                        )
                        batch_size = gr.Slider(label="Batch Size", min_value=1, maximum=100, step=1, value=8, interactive=True)
                        compute_type = gr.Dropdown(label="Compute Type", choices=["int8", "float32", "float16"], value="float16")

                with gr.Group():
                    advanced = gr.Checkbox(label="Advanced Options", value=False)

                    def change_visible1(advanced):
                        return [
                            gr.Dropdown.update(visible=advanced),
                            gr.Checkbox.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Textbox.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                        ]

                    with gr.Row():
                        interpolate_method = gr.Dropdown(label="Interpolate Method", choices=["nearest", "linear", "ignore"], value="nearest", visible=False)
                        return_char_alignments = gr.Checkbox(label="Return Char Alignments", value=False, visible=False)
                    with gr.Row():
                        beam_size = gr.Slider(label="Beam Size (only when temperature is 0)", minimum=1, maximum=100, step=1, value=5, visible=False)
                        patience = gr.Slider(label="Patience (0 default)", minimum=0, maximum=100, step=0.01, value=0, visible=False)
                    with gr.Row():
                        length_penalty = gr.Slider(label="Length Penalty (0 default)", minimum=0, maximum=100, step=0.01, value=0, visible=False)
                        temperature = gr.Slider(label="Temperature", minimum=0, maximum=100, step=0.01, value=0, visible=False)
                    with gr.Row():
                        compression_ratio_threshold = gr.Slider(label="Compression Ratio Threshold", minimum=0, maximum=100, step=0.01, value=2.4, visible=False)
                        logprob_threshold = gr.Slider(label="Logprob Threshold", minimum=-10, maximum=10, step=0.01, value=-1, visible=False)
                    with gr.Row():
                        no_speech_threshold = gr.Slider(label="No Speech Threshold", minimum=0, maximum=1, step=0.001, value=0.6, visible=False)
                        initial_prompt = gr.Textbox(label="Initial Prompt", placeholder="Enter initial prompt", visible=False)
                    with gr.Row():
                        vad_onset = gr.Slider(label="VAD Onset Threshold", minimum=0, maximum=1, step=0.0001, value=0.5, visible=False)
                        vad_offset = gr.Slider(label="VAD Offset Threshold", minimum=0, maximum=1, step=0.0001, value=0.363, visible=False)
                        advanced.change(
                            fn=change_visible1,
                            inputs=[advanced],
                            outputs=[
                                interpolate_method,
                                return_char_alignments,
                                beam_size,
                                patience,
                                length_penalty,
                                temperature,
                                compression_ratio_threshold,
                                logprob_threshold,
                                no_speech_threshold,
                                initial_prompt,
                                vad_onset,
                                vad_offset,
                            ],
                        )

                # output format
                output_format = gr.Dropdown(label="Output Format", choices=["all", "json", "txt", "srt", "vtt", "tsv"], value="vtt")    
    
    with gr.Tab(label="Fastconformer"):
        with gr.Row():
            # # input field for audio / video file
            fconformer_input_files = gr.Files(label="Input Files")

            def clear():
                return None

            with gr.Column():
                with gr.Row():
                    fconformer_btn_run = gr.Button()
                    fconformer_btn_reset = gr.Button(value="Reset").click(fn=clear, outputs=[fconformer_input_files])

                with gr.Row():
                    # model selection dropdown
                    f_model = gr.Dropdown(label="Model", choices=["tiny", "base", "small", "medium", "large", "large-v2"], value="base")
                    # langaue hint input
                    f_lang = gr.Text(label="Language Hint", placeholder="ko")

                with gr.Row():
                    with gr.Group():
                        f_allign = gr.Checkbox(label="Allign Text", value=True)
                        f_max_line_width = gr.Slider(label="Max Line Width (0 for default)", minimum=0, step=1, maximum=10000, value=0)
                        f_max_line_count = gr.Slider(label="Max number of lines in a segment (0 for default)", minimum=0, step=1, maximum=10000, value=0, visible=False)

                        def change_interactive1(max_line_width, max_line_count, val):
                            return [
                                gr.Number.update(visible=val, value=0 if not val else max_line_width),
                                gr.Number.update(visible=not val, value=0 if val else max_line_count),
                            ]

                        f_allign.change(fn=change_interactive1, inputs=[max_line_width, max_line_count, allign], outputs=[max_line_width, max_line_count])
                        f_diarization = gr.Checkbox(label="Speaker Diarization", value=True)
                        with gr.Row():
                            f_min_speakers = gr.Slider(label="Min Speakers", minimum=1, maximum=20, step=1, value=1, visible=True)
                            f_max_speakers = gr.Slider(label="Max Speakers", minimum=1, maximum=20, step=1, value=5, visible=True)

                            # enable min and max speakers if diarization is enabled
                            def change_interactive2(min, max, val):
                                return [
                                    gr.Number.update(visible=val),
                                    gr.Number.update(visible=val),
                                ]

                            f_diarization.change(fn=change_interactive2, inputs=[min_speakers, max_speakers, diarization], outputs=[min_speakers, max_speakers])

                    with gr.Group():
                        # device add cuda to dropdown if available
                        f_device = gr.Dropdown(
                            label="Device", choices=["cpu", "cuda"] if torch.cuda.is_available() else ["cpu"], value="cuda" if torch.cuda.is_available() else "cpu"
                        )
                        f_batch_size = gr.Slider(label="Batch Size", min_value=1, maximum=100, step=1, value=8, interactive=True)
                        f_compute_type = gr.Dropdown(label="Compute Type", choices=["int8", "float32", "float16"], value="float16")

                with gr.Group():
                    f_advanced = gr.Checkbox(label="Advanced Options", value=False)

                    def change_visible1(advanced):
                        return [
                            gr.Dropdown.update(visible=advanced),
                            gr.Checkbox.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Textbox.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                            gr.Slider.update(visible=advanced),
                        ]

                    with gr.Row():
                        f_interpolate_method = gr.Dropdown(label="Interpolate Method", choices=["nearest", "linear", "ignore"], value="nearest", visible=False)
                        f_return_char_alignments = gr.Checkbox(label="Return Char Alignments", value=False, visible=False)
                    with gr.Row():
                        f_beam_size = gr.Slider(label="Beam Size (only when temperature is 0)", minimum=1, maximum=100, step=1, value=5, visible=False)
                        f_patience = gr.Slider(label="Patience (0 default)", minimum=0, maximum=100, step=0.01, value=0, visible=False)
                    with gr.Row():
                        f_length_penalty = gr.Slider(label="Length Penalty (0 default)", minimum=0, maximum=100, step=0.01, value=0, visible=False)
                        f_temperature = gr.Slider(label="Temperature", minimum=0, maximum=100, step=0.01, value=0, visible=False)
                    with gr.Row():
                        f_compression_ratio_threshold = gr.Slider(label="Compression Ratio Threshold", minimum=0, maximum=100, step=0.01, value=2.4, visible=False)
                        f_logprob_threshold = gr.Slider(label="Logprob Threshold", minimum=-10, maximum=10, step=0.01, value=-1, visible=False)
                    with gr.Row():
                        f_no_speech_threshold = gr.Slider(label="No Speech Threshold", minimum=0, maximum=1, step=0.001, value=0.6, visible=False)
                        f_initial_prompt = gr.Textbox(label="Initial Prompt", placeholder="Enter initial prompt", visible=False)
                    with gr.Row():
                        f_vad_onset = gr.Slider(label="VAD Onset Threshold", minimum=0, maximum=1, step=0.0001, value=0.5, visible=False)
                        f_vad_offset = gr.Slider(label="VAD Offset Threshold", minimum=0, maximum=1, step=0.0001, value=0.363, visible=False)
                        f_advanced.change(
                            fn=change_visible1,
                            inputs=[f_advanced],
                            outputs=[
                                f_interpolate_method,
                                f_return_char_alignments,
                                f_beam_size,
                                f_patience,
                                f_length_penalty,
                                f_temperature,
                                f_compression_ratio_threshold,
                                f_logprob_threshold,
                                f_no_speech_threshold,
                                f_initial_prompt,
                                f_vad_onset,
                                f_vad_offset,
                            ],
                        )

                # output format
                f_output_format = gr.Dropdown(label="Output Format", choices=["all", "json", "txt", "srt", "vtt", "tsv"], value="vtt")
    
    with gr.Tab(label="Output"):

        def fill_dropdown():
            folders = os.listdir(os.getcwd() + "/output")
            return gr.Dropdown.update(choices=folders)

        history_dropdown = gr.Dropdown(label="Folder", choices=os.listdir(os.getcwd() + "/output"), interactive=True, value="")
        btn_refresh = gr.Button(value="Refresh output list")
        btn_refresh.click(fill_dropdown, inputs=None, outputs=history_dropdown)

        def set_file_type(selected):
            if selected == "":
                return gr.Dropdown.update(choices=["select a file"])
            files = [os.path.splitext(x)[1] for x in os.listdir(os.getcwd() + "/output/" + selected)]
            return gr.Dropdown.update(choices=files, interactive=True)

        file_type = gr.Dropdown(label="File Type", choices=[], value="select a file", interactive=False)
        history_dropdown.change(set_file_type, inputs=history_dropdown, outputs=file_type)

        def fill_output(folder, type):
            if folder == "" or type == "select a file":
                return gr.TextArea.update(value="")
            file = [x for x in os.listdir(os.getcwd() + "/output/" + folder) if os.path.splitext(x)[1] == type][0]
            with open(os.getcwd() + "/output/" + folder + "/" + file, "r", encoding="utf-8") as f:
                text = f.read()
            return gr.TextArea.update(value=text)

        output_text_field = gr.TextArea(label="Output (changes made wont be saved - files are also in the output folder)", value="", interactive=True)
        file_type.change(fill_output, inputs=[history_dropdown, file_type], outputs=output_text_field)


    with gr.Tab(label="Backend API"):
        with gr.Row():
            api_files = gr.Files(label="Input Files")
            with gr.Column():
                api_host = gr.Text(label="Backend Host", value="http://localhost:8000")
                api_model = gr.Dropdown(label="Model Type", choices=[
                    "faster_whisper", "origin_whisper", "fast_conformer", "google_stt", "qwen_asr"
                ], value="faster_whisper")
                api_model_size = gr.Text(label="Model Size", value="large-v3")
                api_language = gr.Text(label="Language", value="auto")
                api_device = gr.Dropdown(label="Device", choices=["cpu", "cuda"] if torch.cuda.is_available() else ["cpu"], value="cuda" if torch.cuda.is_available() else "cpu")
                api_prompt = gr.Textbox(label="Initial Prompt", placeholder="Optional initial prompt")
                api_diar = gr.Checkbox(label="Speaker Diarization", value=False)
                api_force_align = gr.Checkbox(label="Force Alignment (if supported)", value=False)
                api_format = gr.Dropdown(label="Output Format", choices=["vtt", "srt", "json", "txt", "tsv"], value="vtt")
                api_run = gr.Button(value="Run via Backend API")

            api_output = gr.TextArea(label="Transcription Output", value="", interactive=False)

        def backend_api_transcribe(files, host, model, model_size, language, device, prompt, diar, force_align, out_format):
            if not files:
                return "Please select one or more files."
            try:
                # upload
                m = []
                for f in files:
                    m.append(("files", (f.name.split("/")[-1], open(f.name, "rb"), "application/octet-stream")))
                up = requests.post(host.rstrip("/") + "/api/v1/upload", files=m, timeout=120)
                up.raise_for_status()
                file_ids = up.json().get("file_ids", [])
                if not file_ids:
                    return "Upload failed: no file_ids returned."
                # create job
                payload = {
                    "file_ids": file_ids,
                    "model_type": model,
                    "model_size": model_size,
                    "language": language,
                    "device": device,
                    "parameters": {"initial_prompt": prompt} if prompt else {},
                    "diarization": {"enabled": bool(diar), "min_speakers": 1, "max_speakers": 5},
                    "output_formats": [out_format],
                    "force_alignment": bool(force_align),
                    "alignment_provider": "qwen"
                }
                tr = requests.post(host.rstrip("/") + "/api/v1/transcribe", json=payload, timeout=30)
                tr.raise_for_status()
                job_id = tr.json().get("job_id")
                if not job_id:
                    return f"Failed to create job: {tr.text}"
                # poll
                status_url = host.rstrip("/") + f"/api/v1/transcribe/jobs/{job_id}"
                start = time.time()
                while True:
                    st = requests.get(status_url, timeout=30)
                    st.raise_for_status()
                    data = st.json()
                    if data.get("status") in ("completed", "failed", "cancelled"):
                        break
                    if time.time() - start > 900:
                        return "Timeout waiting for job completion"
                    time.sleep(2)
                if data.get("status") != "completed":
                    return f"Job finished with status: {data.get('status')} error={data.get('error')}"
                # download
                res = requests.get(host.rstrip("/") + f"/api/v1/results/{job_id}/{out_format}", timeout=120)
                if res.status_code != 200:
                    return f"Failed to download result: {res.status_code} {res.text}"
                text = res.text
                return text
            except Exception as e:
                return f"Error: {e}"

        api_run.click(
            backend_api_transcribe,
            inputs=[api_files, api_host, api_model, api_model_size, api_language, api_device, api_prompt, api_diar, api_force_align, api_format],
            outputs=[api_output]
        )

    #########################################
    ############Button Event Zone############
    #########################################

    origin_whisper_btn_run.click(
        origin_whisper_process,
        inputs=[
            origin_whisper_input_files,
            origin_device,
            origin_model,
            origin_lang,
            origin_diarization,
            origin_output_format,
            origin_min_speakers,
            origin_max_speakers,
            origin_beam_size,
            origin_patience,
            origin_length_penalty,
            origin_temperature,
            origin_compression_ratio_threshold,
            origin_logprob_threshold,
            origin_no_speech_threshold,
            origin_initial_prompt,
            condition_on_previous_text,
            remove_punctuation_from_words,
            remove_empty_words,
        ],
        outputs=[origin_whisper_input_files],
    )

    whisper_btn_run.click(
        whisper_process,
        inputs=[
            whisper_input_files,
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
        ],
        outputs=[whisper_input_files],
    )

    fconformer_btn_run.click(
        fastconformer_process,
        inputs=[
            fconformer_input_files,
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
        ],
        outputs=[fconformer_input_files],
    )

if __name__ == "__main__":
    port=16389
    if os.environ.get("IP_ADDR") is not None:
        ui.queue(concurrency_count=10).launch(server_name=str(os.environ["IP_ADDR"]), server_port=port)
    else:
        ui.queue(concurrency_count=10).launch(server_port=port)
