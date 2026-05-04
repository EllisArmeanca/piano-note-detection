import os
from analiza_audio import analyze_audio
from export_partitura import export_sheet
from audio_preview import generate_preview_audio

# Calea catre MuseScore, folosita pentru exportul PDF
MUSESCORE_PATH = os.environ.get(
    "MUSESCORE_PATH",
    r"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"
)

def run_pipeline(audio_path, output_dir="outputs", save_plots=False,
                 export_pdf=True, export_midi=True, musescore_path=MUSESCORE_PATH):
    # Ruleaza analiza audio si obtine notele finale + BPM-ul estimat
    final_notes, bpm_est = analyze_audio(audio_path, save_plots=save_plots)

    # Numele de baza al fisierelor generate porneste de la numele fisierului audio
    base_name = os.path.splitext(os.path.basename(audio_path))[0] + "_sheet"

    # Genereaza MusicXML, PDF si MIDI
    musicxml_file, pdf_file, midi_file = export_sheet(
        final_notes=final_notes,
        bpm=bpm_est,
        base_name=base_name,
        output_dir=output_dir,
        export_pdf=export_pdf,
        musescore_path=musescore_path,
        export_midi=export_midi
    )

    # Genereaza si un preview audio simplu pe baza notelor detectate
    preview_audio_file = os.path.join(output_dir, f"{base_name}_preview.wav")
    generate_preview_audio(final_notes, preview_audio_file)

    # Intoarce toate rezultatele intr-un dictionar
    return {
        "final_notes": final_notes,
        "bpm": bpm_est,
        "musicxml": musicxml_file,
        "pdf": pdf_file,
        "midi": midi_file,
        "preview_audio": preview_audio_file
    }


if __name__ == "__main__":
    # Exemplu de rulare locala, fara interfata web
    audio_path = "../samples/vars1.wav"

    results = run_pipeline(
        audio_path=audio_path,
        output_dir="outputs",
        save_plots=True,
        export_pdf=True,
        export_midi=True
    )

    print("\n=== FINAL OUTPUT ===")
    print("Estimated BPM:", round(results["bpm"], 2))

    for idx, (note_txt, f0, st, en, dur) in enumerate(results["final_notes"]):
        print(f"{idx + 1}. {note_txt} | f0={f0:.2f} Hz | start={st:.2f}s | end={en:.2f}s | dur={dur:.2f}s")

    print("\nGenerated files:")
    print("MusicXML:", results["musicxml"])
    print("PDF:", results["pdf"])
    print("MIDI:", results["midi"])
    print("Preview audio:", results["preview_audio"])