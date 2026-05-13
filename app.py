from flask import Flask, render_template, request, jsonify, send_file
import yt_dlp
import os
import threading

app = Flask(__name__)
@app.route("/")
def index():
    return render_template("index.html")
DOWNLOAD_FOLDER = os.path.join(os.path.expanduser("~"), "Downloads", "VideoDown")
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# ── Obtener info del video ─────────────────────
@app.route("/info", methods=["POST"])
def get_info():
    url = request.json.get("url", "").strip()
    if not url:
        return jsonify({"error": "URL vacía"}), 400

    ydl_opts = {"quiet": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formatos = []
        seen = set()
        for f in info.get("formats", []):
            height = f.get("height")
            ext    = f.get("ext")
            vcodec = f.get("vcodec", "none")
            acodec = f.get("acodec", "none")

            if not height or vcodec == "none":
                continue

            label = f"{height}p"
            if label not in seen:
                seen.add(label)
                formatos.append({
                    "format_id": f["format_id"],
                    "label":     label,
                    "ext":       ext,
                    "filesize":  f.get("filesize") or f.get("filesize_approx")
                })

        formatos.sort(key=lambda x: int(x["label"].replace("p", "")), reverse=True)

        # Agregar opción de solo audio
        formatos.append({"format_id": "bestaudio", "label": "Solo audio (MP3)", "ext": "mp3", "filesize": None})

        return jsonify({
            "title":     info.get("title", "Sin título"),
            "thumbnail": info.get("thumbnail", ""),
            "duration":  info.get("duration", 0),
            "uploader":  info.get("uploader", ""),
            "formatos":  formatos
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Descargar video ────────────────────────────
@app.route("/download", methods=["POST"])
def download():
    url       = request.json.get("url", "").strip()
    format_id = request.json.get("format_id", "best")
    titulo    = request.json.get("titulo", "video")

    if not url:
        return jsonify({"error": "URL vacía"}), 400

    # Limpiar nombre de archivo
    safe_title = "".join(c for c in titulo if c.isalnum() or c in " -_").strip()[:60]
    out_path   = os.path.join(DOWNLOAD_FOLDER, safe_title)

    if format_id == "bestaudio":
        ydl_opts = {
            "format":           "bestaudio/best",
            "outtmpl":          out_path + ".%(ext)s",
            "postprocessors":   [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
            "quiet":            True,
        }
    else:
        ydl_opts = {
            "format":  f"{format_id}+bestaudio/best",
            "outtmpl": out_path + ".%(ext)s",
            "quiet":   True,
            "merge_output_format": "mp4",
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Buscar el archivo descargado
        for f in os.listdir(DOWNLOAD_FOLDER):
            if f.startswith(safe_title):
                return jsonify({"ok": True, "filename": f, "folder": DOWNLOAD_FOLDER})

        return jsonify({"error": "No se encontró el archivo descargado"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("🎬 VideoDown corriendo en http://localhost:5000")
    print(f"📁 Descargas en: {DOWNLOAD_FOLDER}")
    app.run(debug=False, port=5000)
