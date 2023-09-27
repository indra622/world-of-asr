import nemo.collections.asr as nemo_asr

asr_model = nemo_asr.models.EncDecRNNTBPEModel.from_pretrained(model_name="nvidia/stt_en_fastconformer_transducer_xlarge")
