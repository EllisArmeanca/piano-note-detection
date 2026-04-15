import os
import subprocess
from music21 import stream, note, meter, tempo, metadata

# Semnatura de timp folosita in partitura
TIME_SIGNATURE = "4/4"

# Valorile permise pentru durate, exprimate in quarterLength
# 0.25 = saisprezecime
# 0.5 = optime
# 1.0 = patrime
# 1.5 = patrime cu punct
# 2.0 = doime
ALLOWED_DURATIONS = [0.25, 0.5, 1.0, 1.5, 2.0]


def seconds_to_quarter_length(duration_sec, bpm):
    # Calculeaza cat inseamna durata in secunde raportata la tempo-ul piesei
    # Rezultatul este exprimat in quarterLength, adica unitatea folosita de music21
    quarter_sec = 60.0 / bpm
    return duration_sec / quarter_sec


def quantize_duration(duration_sec, bpm, allowed_values):
    # Transforma durata reala intr-o durata muzicala apropiata
    raw_q = seconds_to_quarter_length(duration_sec, bpm)

    best_val = allowed_values[0]
    best_diff = abs(raw_q - best_val)

    for val in allowed_values[1:]:
        diff = abs(raw_q - val)
        if diff < best_diff:
            best_diff = diff
            best_val = val

    return best_val


def add_quantized_rest(part, gap_sec, bpm):
    # Daca exista o pauza intre doua note, o adaugam in partitura
    if gap_sec <= 0:
        return

    rest_q = quantize_duration(gap_sec, bpm, ALLOWED_DURATIONS)

    if rest_q > 0:
        r = note.Rest()
        r.quarterLength = rest_q
        part.append(r)


def export_pdf_with_musescore(musicxml_file, pdf_file, musescore_path):
    # Foloseste MuseScore pentru a converti MusicXML in PDF
    cmd = [musescore_path, musicxml_file, "-o", pdf_file]
    subprocess.run(cmd, check=True)


def export_sheet(final_notes, bpm, base_name="output", output_dir="outputs",
                 export_pdf=False, musescore_path=None, export_midi=True):
    # Creeaza folderul de output daca nu exista deja
    os.makedirs(output_dir, exist_ok=True)

    # Construim caile pentru fisierele generate
    musicxml_file = os.path.join(output_dir, f"{base_name}.musicxml")
    pdf_file = os.path.join(output_dir, f"{base_name}.pdf")
    midi_file = os.path.join(output_dir, f"{base_name}.mid")

    # Cream obiectul principal de tip Score
    score = stream.Score()

    # Adaugam metadate simple
    score.metadata = metadata.Metadata()
    score.metadata.title = f"Detected Piano Notes - {base_name}"
    score.metadata.composer = "Generated from audio"

    # Cream o singura partitura/instrument
    part = stream.Part()

    # Adaugam tempo-ul estimat si masura
    part.append(tempo.MetronomeMark(number=round(bpm)))
    part.append(meter.TimeSignature(TIME_SIGNATURE))

    prev_end_time = 0.0

    # Parcurgem notele detectate si le adaugam in partitura
    for note_name, f0, start_time, end_time, duration_sec in final_notes:
        # Distanta dintre nota curenta si nota precedenta
        gap_sec = start_time - prev_end_time

        # Daca exista pauza semnificativa, o adaugam
        if gap_sec > 0.05:
            add_quantized_rest(part, gap_sec, bpm)

        # Cuantizam durata notei
        q_len = quantize_duration(duration_sec, bpm, ALLOWED_DURATIONS)

        # Cream nota si ii setam durata muzicala
        n = note.Note(note_name)
        n.quarterLength = q_len
        part.append(n)

        prev_end_time = end_time

    # Adaugam part-ul in score
    score.append(part)

    # Export MusicXML
    score.write("musicxml", fp=musicxml_file)
    print(f"MusicXML file saved as: {musicxml_file}")

    # Export MIDI
    if export_midi:
        score.write("midi", fp=midi_file)
        print(f"MIDI file saved as: {midi_file}")
    else:
        midi_file = None

    # Export PDF prin MuseScore
    if export_pdf:
        if musescore_path is None:
            print("PDF export skipped: musescore_path is not set.")
            pdf_file = None
        else:
            try:
                export_pdf_with_musescore(musicxml_file, pdf_file, musescore_path)
                print(f"PDF file saved as: {pdf_file}")
            except Exception as e:
                print("PDF export failed:", e)
                pdf_file = None
    else:
        pdf_file = None

    return musicxml_file, pdf_file, midi_file