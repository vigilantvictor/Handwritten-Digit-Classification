"""Draw a digit with the mouse and classify it using Kaggle MNIST.

Install: py -m pip install pandas scikit-learn pillow
Run:     py .\outputs\live_digit_draw.py --data-dir .\data
Retrain: add --retrain after downloading a newer train.csv or changing the model.
"""
from pathlib import Path
import argparse
import tkinter as tk

import joblib
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from scipy.ndimage import shift as shift_image
from sklearn.svm import SVC


class DigitApp:
    def __init__(self, root, model):
        self.root = root
        self.model = model
        self.root.title("Handwritten Digit Classifier")
        self.root.resizable(False, False)
        tk.Label(root, text="Draw one large digit in the middle of the canvas", font=("Arial", 14)).pack(pady=8)
        self.canvas_size = 280
        self.canvas = tk.Canvas(root, width=self.canvas_size, height=self.canvas_size,
                                bg="black", cursor="cross", highlightthickness=1)
        self.canvas.pack(padx=12, pady=4)
        self.image = Image.new("L", (self.canvas_size, self.canvas_size), 0)
        self.pen = ImageDraw.Draw(self.image)
        self.last = None
        self.canvas.bind("<Button-1>", self.start_stroke)
        self.canvas.bind("<B1-Motion>", self.draw_stroke)
        controls = tk.Frame(root)
        controls.pack(pady=8)
        tk.Button(controls, text="Predict", command=self.predict, width=12).pack(side="left", padx=5)
        tk.Button(controls, text="Clear", command=self.clear, width=12).pack(side="left", padx=5)
        self.result = tk.Label(root, text="Draw a digit, then click Predict", font=("Arial", 16, "bold"))
        self.result.pack(pady=(0, 12))

    def start_stroke(self, event):
        self.last = (event.x, event.y)
        self.pen.ellipse((event.x - 12, event.y - 12, event.x + 12, event.y + 12), fill=255)
        self.canvas.create_oval(event.x - 12, event.y - 12, event.x + 12, event.y + 12,
                                fill="white", outline="white")

    def draw_stroke(self, event):
        if self.last is not None:
            x0, y0 = self.last
            self.pen.line((x0, y0, event.x, event.y), fill=255, width=24)
            self.pen.ellipse((event.x - 12, event.y - 12, event.x + 12, event.y + 12), fill=255)
            self.canvas.create_line(x0, y0, event.x, event.y, fill="white", width=24,
                                    capstyle=tk.ROUND, smooth=True)
        self.last = (event.x, event.y)

    def to_model_input(self):
        """Crop, scale to MNIST's 20x20 digit area, and center ink by its center of mass."""
        bbox = self.image.getbbox()
        if bbox is None:
            return None
        digit = self.image.crop(bbox)
        scale = 20.0 / max(digit.size)
        size = (max(1, round(digit.width * scale)), max(1, round(digit.height * scale)))
        digit = digit.resize(size, Image.Resampling.LANCZOS)
        frame = Image.new("L", (28, 28), 0)
        frame.paste(digit, ((28 - digit.width) // 2, (28 - digit.height) // 2))
        pixels = np.asarray(frame, dtype=np.float32)
        mass = pixels.sum()
        if mass > 0:
            yy, xx = np.indices(pixels.shape)
            center_y = float((yy * pixels).sum() / mass)
            center_x = float((xx * pixels).sum() / mass)
            pixels = shift_image(pixels, (13.5 - center_y, 13.5 - center_x), order=1,
                                 mode="constant", cval=0.0, prefilter=False)
        return (pixels / 255.0).reshape(1, 784)

    def predict(self):
        row = self.to_model_input()
        if row is None:
            self.result.config(text="Draw a digit first.")
            return
        digit = int(self.model.predict(row)[0])
        self.result.config(text=f"Prediction: {digit}   (draw slowly and clearly for best results)")

    def clear(self):
        self.canvas.delete("all")
        self.image = Image.new("L", (self.canvas_size, self.canvas_size), 0)
        self.pen = ImageDraw.Draw(self.image)
        self.last = None
        self.result.config(text="Draw a digit, then click Predict")


def main():
    parser = argparse.ArgumentParser(description="Draw a digit and classify it with an MNIST-trained SVM.")
    parser.add_argument("--data-dir", default="data", help="Folder containing Kaggle train.csv")
    parser.add_argument("--retrain", action="store_true", help="Train a fresh model instead of loading the saved one")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    train_path = data_dir / "train.csv"
    model_path = data_dir / "mnist_svm.joblib"
    if not train_path.exists():
        raise FileNotFoundError(f"Cannot find {train_path}. Ensure Kaggle train.csv is in your data folder.")

    if not args.retrain and model_path.exists() and model_path.stat().st_mtime >= train_path.stat().st_mtime:
        print(f"Loading saved SVM model from {model_path}")
        model = joblib.load(model_path)
    else:
        print("Training an SVM on Kaggle data; the first run can take several minutes...")
        df = pd.read_csv(train_path)
        if "label" not in df:
            raise ValueError("train.csv must include a 'label' column.")
        y = df["label"]
        X = df.drop(columns="label").astype("float32") / 255.0
        model = SVC(kernel="rbf", C=10, gamma="scale", cache_size=512)
        model.fit(X, y)
        data_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, model_path)
        print(f"Saved SVM model to {model_path}")

    root = tk.Tk()
    DigitApp(root, model)
    root.mainloop()


if __name__ == "__main__":
    main()

