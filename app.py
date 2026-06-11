from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
import subprocess
import uuid

app = Flask(__name__)

UPLOAD_FOLDER = Path("storage/uploads")
OUTPUT_FOLDER = Path("storage/outputs")

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".mp4", ".mov", ".mkv", ".webm"}

def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    download_file = None

    if request.method == "POST":
        file = request.files.get("file")
        quality = request.form.get("quality", "192k")

        if not file or file.filename == "":
            error = "Please upload a file."
        elif not allowed_file(file.filename):
            error = "Unsupported file type."
        else:
            filename = secure_filename(file.filename)
            input_path = UPLOAD_FOLDER / f"{uuid.uuid4()}_{filename}"
            output_path = OUTPUT_FOLDER / f"{input_path.stem}.mp3"

            file.save(input_path)

            command = [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-vn",
                "-codec:a",
                "libmp3lame",
                "-b:a",
                quality,
                str(output_path)
            ]

            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode != 0:
                error = "Conversion failed. Make sure ffmpeg is installed."
            else:
                download_file = output_path.name

    return render_template("index.html", error=error, download_file=download_file)

@app.route("/download/<filename>")
def download(filename):
    file_path = OUTPUT_FOLDER / filename
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
