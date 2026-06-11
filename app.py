from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from pathlib import Path
from urllib.parse import urlparse
import subprocess
import uuid
import requests

app = Flask(__name__)

UPLOAD_FOLDER = Path("storage/uploads")
OUTPUT_FOLDER = Path("storage/outputs")

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".mp4", ".mov", ".mkv", ".webm"}

YOUTUBE_DOMAINS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be"
}

def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def is_youtube_url(url):
    try:
        host = urlparse(url).hostname or ""
        host = host.lower()
        return any(host == d or host.endswith("." + d) for d in YOUTUBE_DOMAINS)
    except:
        return False

def youtube_preview(url):
    try:
        res = requests.get(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
            timeout=10
        )
        if res.ok:
            return res.json()
    except:
        pass
    return None

def download_direct_file(url):
    parsed = urlparse(url)
    name = secure_filename(Path(parsed.path).name or "media_file")
    if not Path(name).suffix:
        name += ".mp4"

    input_path = UPLOAD_FOLDER / f"{uuid.uuid4()}_{name}"

    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()

        content_type = r.headers.get("content-type", "").lower()
        if "text/html" in content_type:
            raise Exception("That URL looks like a webpage, not a direct media file.")

        with open(input_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    return input_path

def convert_to_mp3(input_path, quality):
    output_path = OUTPUT_FOLDER / f"{input_path.stem}.mp3"

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
        raise Exception("Conversion failed. Make sure ffmpeg is installed.")

    return output_path

@app.route("/", methods=["GET", "POST"])
def index():
    error = None
    download_file = None
    preview = None

    if request.method == "POST":
        file = request.files.get("file")
        media_url = request.form.get("media_url", "").strip()
        quality = request.form.get("quality", "192k")

        try:
            input_path = None

            if media_url:
                if is_youtube_url(media_url):
                    preview = youtube_preview(media_url)
                    error = "YouTube links can be previewed here, but this app cannot download or convert YouTube audio. Upload a file you own instead."
                    return render_template("index.html", error=error, download_file=download_file, preview=preview)

                input_path = download_direct_file(media_url)

            elif file and file.filename:
                if not allowed_file(file.filename):
                    error = "Unsupported file type."
                else:
                    filename = secure_filename(file.filename)
                    input_path = UPLOAD_FOLDER / f"{uuid.uuid4()}_{filename}"
                    file.save(input_path)

            else:
                error = "Upload a file or paste a direct media URL."

            if input_path and not error:
                output_path = convert_to_mp3(input_path, quality)
                download_file = output_path.name

        except Exception as e:
            error = str(e)

    return render_template("index.html", error=error, download_file=download_file, preview=preview)

@app.route("/download/<filename>")
def download(filename):
    file_path = OUTPUT_FOLDER / filename
    return send_file(file_path, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
