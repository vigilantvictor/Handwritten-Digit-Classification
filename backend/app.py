from pathlib import Path

import joblib
import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, ImageOps, UnidentifiedImageError
from scipy.ndimage import shift as shift_image

ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = Path(__file__).resolve().parent / "models" / "mnist_svm.joblib"
FRONTEND_DIST = ROOT / "frontend" / "dist"
MAX_IMAGE_BYTES = 10 * 1024 * 1024

app = Flask(__name__, static_folder=str(FRONTEND_DIST), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = MAX_IMAGE_BYTES
_model = None


def get_model():
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            raise RuntimeError(f"Model file is missing: {MODEL_PATH}")
        _model = joblib.load(MODEL_PATH)
    return _model


def image_to_mnist(image_file):
    """Extract one contrasting digit and format it like a 28x28 MNIST image."""
    image = Image.open(image_file).convert("L")
    image.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    pixels = np.asarray(image, dtype=np.float32)
    h, w = pixels.shape
    border = np.concatenate((pixels[0, :], pixels[-1, :], pixels[:, 0], pixels[:, -1]))
    background = float(np.median(border))
    contrast = np.abs(pixels - background)
    peak = float(contrast.max())
    if peak < 22:
        raise ValueError("Could not find a digit. Use a clearer image with a plain background.")

    # Drop mild paper texture and shadows, while keeping darker ink on white paper
    # and lighter ink on a dark drawing canvas.
    cutoff = max(18.0, peak * 0.10)
    ink = np.clip((contrast - cutoff) * (255.0 / max(1.0, peak - cutoff)), 0, 255)
    foreground = ink > 20
    ys, xs = np.where(foreground)
    if len(xs) == 0:
        raise ValueError("Could not isolate a digit in that image. Try cropping closer around it.")
    left, right = max(0, xs.min() - 2), min(w, xs.max() + 3)
    top, bottom = max(0, ys.min() - 2), min(h, ys.max() + 3)
    digit = Image.fromarray(ink[top:bottom, left:right].astype(np.uint8), mode="L")

    scale = 20.0 / max(digit.size)
    size = (max(1, round(digit.width * scale)), max(1, round(digit.height * scale)))
    digit = digit.resize(size, Image.Resampling.LANCZOS)
    frame = Image.new("L", (28, 28), 0)
    frame.paste(digit, ((28 - digit.width) // 2, (28 - digit.height) // 2))
    normalized = np.asarray(frame, dtype=np.float32)
    mass = normalized.sum()
    if mass > 0:
        yy, xx = np.indices(normalized.shape)
        cy = float((yy * normalized).sum() / mass)
        cx = float((xx * normalized).sum() / mass)
        normalized = shift_image(normalized, (13.5 - cy, 13.5 - cx), order=1,
                                 mode="constant", cval=0.0, prefilter=False)
    return (normalized / 255.0).reshape(1, 784)


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "model_ready": MODEL_PATH.exists()})


@app.post("/api/predict")
def predict():
    uploaded = request.files.get("image")
    if uploaded is None or not uploaded.filename:
        return jsonify({"error": "Choose a picture or draw a digit first."}), 400
    try:
        row = image_to_mnist(uploaded.stream)
        digit = int(get_model().predict(row)[0])
        return jsonify({"digit": digit})
    except (UnidentifiedImageError, OSError):
        return jsonify({"error": "That image could not be opened. Try a PNG, JPG, or WEBP file."}), 400
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        app.logger.exception("Digit prediction failed")
        return jsonify({"error": f"Prediction service error: {exc}"}), 500


@app.get("/")
def index():
    if not (FRONTEND_DIST / "index.html").exists():
        return ("Frontend is not built yet. Run npm install and npm run build in frontend/.", 503)
    return send_from_directory(FRONTEND_DIST, "index.html")


@app.errorhandler(413)
def image_too_large(_error):
    return jsonify({"error": "Please choose an image smaller than 10 MB."}), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
