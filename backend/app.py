import os
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

from main import run_pipeline

app = Flask(__name__)
CORS(app)

# Folder unde salvam fisierele incarcate
UPLOAD_FOLDER = "uploads"

# Extensii permise
ALLOWED_EXTENSIONS = {"wav"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ne asiguram ca folderul exista
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    # Verifica daca fisierul are extensia corecta
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/api/process", methods=["POST"])
def process_audio():
    # Verifica daca a fost trimis un fisier
    if "file" not in request.files:
        return jsonify({"error": "Nu a fost trimis niciun fisier"}), 400

    file = request.files["file"]

    # Verifica daca numele fisierului nu este gol
    if file.filename == "":
        return jsonify({"error": "Nu a fost selectat niciun fisier"}), 400

    # Verifica extensia
    if not allowed_file(file.filename):
        return jsonify({"error": "Se accepta doar fisiere WAV"}), 400

    # Curata numele fisierului
    filename = secure_filename(file.filename)

    # Calea unde salvam fisierul audio incarcat
    input_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(input_path)

    # Cream un folder separat de output pentru fiecare fisier
    base_name = os.path.splitext(filename)[0]
    output_dir = os.path.join("outputs", base_name)
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Rulam pipeline-ul complet
        results = run_pipeline(
            audio_path=input_path,
            output_dir=output_dir,
            save_plots=True,
            export_pdf=True,
            export_midi=True
        )

        # Cautam graficele generate pentru acest fisier
        fig_dir = os.path.join("figures", base_name)
        figures = []

        if os.path.exists(fig_dir):
            for f in os.listdir(fig_dir):
                if f.endswith(".png"):
                    figures.append(os.path.join(fig_dir, f))

        # Optional: sortare pentru afisare consistenta
        figures.sort()

        # Intoarcem raspuns JSON catre frontend
        return jsonify({
            "message": "Procesare finalizata cu succes",
            "bpm": round(results["bpm"], 2),
            "notes": results["final_notes"],
            "original_audio": input_path,
            "preview_audio": results["preview_audio"],
            "figures": figures,
            "files": {
                "musicxml": results["musicxml"],
                "pdf": results["pdf"],
                "midi": results["midi"]
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/download", methods=["GET"])
def download_file():
    # Primeste calea fisierului prin query parameter
    file_path = request.args.get("path")

    if not file_path:
        return jsonify({"error": "Lipseste calea fisierului"}), 400

    if not os.path.exists(file_path):
        return jsonify({"error": "Fisierul nu exista"}), 404

    return send_file(file_path, as_attachment=True)


@app.route("/api/media", methods=["GET"])
def stream_media():
    # Trimite fisierul catre browser pentru playerul audio
    file_path = request.args.get("path")

    if not file_path:
        return jsonify({"error": "Lipseste calea fisierului"}), 400

    if not os.path.exists(file_path):
        return jsonify({"error": "Fisierul nu exista"}), 404

    return send_file(file_path)


if __name__ == "__main__":
    app.run(debug=True)