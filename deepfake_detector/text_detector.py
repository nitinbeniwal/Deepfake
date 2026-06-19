import threading

_MODEL = "Hello-SimpleAI/chatgpt-detector-roberta"
_det, _lock = None, threading.Lock()

def _get():
    global _det
    if _det is None:
        with _lock:
            if _det is None:
                from transformers import pipeline
                print(f"Loading text model: {_MODEL} ...")
                _det = pipeline("text-classification", model=_MODEL)
                print("Text model loaded ✅")
    return _det

def detect_ai_text(text):
    r = _get()(text[:512])[0]
    lbl = r["label"].strip().lower()
    conf = round(r["score"] * 100, 2)
    fake = any(t in lbl for t in ("fake","ai","gpt","generated","label_1","machine"))
    label = "Fake" if fake else "Real"
    print(f"{'🚨 AI TEXT' if fake else '✅ HUMAN TEXT'} ({conf}%)")
    return label, conf
