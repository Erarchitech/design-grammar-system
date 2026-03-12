from fastapi import FastAPI, UploadFile, File, HTTPException
from faster_whisper import WhisperModel
import tempfile
import os

app = FastAPI()

# Use CPU-friendly default for broader compatibility on Windows/dev machines.
model = WhisperModel("base", compute_type="int8")


@app.post("/transcribe")
async def transcribe(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(data)
            tmp.flush()
            tmp_path = tmp.name

        segments, _info = model.transcribe(tmp_path)
        text = "".join(segment.text for segment in segments).strip()

        return {"text": text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)