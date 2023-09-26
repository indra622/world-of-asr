import nemo.collections.asr as nemo_asr
import sys

#print(sys.argv[1])

import logging 
logging.getLogger('nemo_logger').setLevel(logging.CRITICAL)

def transcribe(file):
    asr_model = nemo_asr.models.EncDecRNNTBPEModel.from_pretrained(model_name="nvidia/stt_en_fastconformer_transducer_xlarge")
    results = asr_model.transcribe([file])
    return results

print(transcribe(sys.argv[1]))

