from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
import subprocess
import uuid
import shutil

app = Flask(__name__)

UPLOAD_FOLDER = Path("storage/uploads")
OUTPUT_FOLDER = Path("storage/outputs")

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg",
    ".mp4", ".mov", ".mkv", ".webm", ".avi"
}

def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def convert_to_mp3(input_path, quality):
    output_path = OUTPUT_FOLDER / f"{uuid.uuid4().hex}.mp3"

    command = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-vn",
        "-codec:a", "libmp3lame",
        "-b:a", quality,
        str(output_path)
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception("MP3 conversion failed. Make sure FFmpeg is installed.")

    return output_path

def convert_to_mp4(input_path):
    output_path = OUTPUT_FOLDER / f"{uuid.uuid4().hex}.mp4"

    command = [
        "ffmpeg",
        "-y",
        "-i", str(input_path),
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path)
    ]

    result = subprocess.run(command, capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception("MP4 conversion failed. Make sure FFmpeg is installed.")

    return output_path

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        return render_template("index.html", error=None)

    try:
        if shutil.which("ffmpeg") is None:
            return render_template(
                "index.html",
                error="FFmpeg is not installed. Run: winget install --id Gyan.FFmpeg -e"
            )

        uploaded_file = request.files.get("file")
        output_type = request.form.get("output_type", "mp3")
        quality = request.form.get("quality", "192k")

        if not uploaded_file or uploaded_file.filename == "":
            return render_template("index.html", error="Please upload a video or audio file.")

        if not allowed_file(uploaded_file.filename):
            return render_template("index.html", error="Unsupported file type.")

        filename = secure_filename(uploaded_file.filename)
        input_path = UPLOAD_FOLDER / f"{uuid.uuid4().hex}_{filename}"
        uploaded_file.save(input_path)

        if output_type == "mp4":
            output_path = convert_to_mp4(input_path)
            download_name = f"{Path(filename).stem}.mp4"
        else:
            output_path = convert_to_mp3(input_path, quality)
            download_name = f"{Path(filename).stem}.mp3"

        return send_file(
            output_path,
            as_attachment=True,
            download_name=download_name
        )

    except Exception as e:
        return render_template("index.html", error=str(e))

if __name__ == "__main__":
    app.run(debug=True)
