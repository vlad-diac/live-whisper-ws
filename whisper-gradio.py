import gradio as gr
import requests, tempfile

BACKEND = "http://localhost:8000/transcribe"

def transcribe(audio):
    # audio is (sr, np.array) or a filepath depending on gradio version; easiest: receive file
    filepath = audio if isinstance(audio, str) else audio[0] if isinstance(audio, tuple) else None
    if not filepath:
        # save to temp wav
        import soundfile as sf, numpy as np
        sr, y = audio
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        sf.write(tmp.name, y, sr)
        filepath = tmp.name
    with open(filepath, "rb") as f:
        r = requests.post(BACKEND, files={"file": f})
    try:
        return r.json().get("text", "")
    except:
        return r.text

demo = gr.Interface(
    fn=transcribe,
    inputs=gr.Audio(sources=["microphone", "upload"], type="filepath"),
    outputs="text",
    title="Whisper WS backend (HTTP sanity)",
)
demo.launch(server_port=7860)
