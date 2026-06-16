
import librosa
import numpy as np
from collections import Counter

audio_path = "./samples/*.wav"

sr = 44100
frame_length = 2048
hop_length = 512

fmin = librosa.note_to_hz("C2")
fmax = librosa.note_to_hz("C7")

min_duration = 0.25

y, sr = librosa.load(audio_path, sr=sr, mono=True)

f0 = librosa.yin(
    y,
    fmin=fmin,
    fmax=fmax,
    sr=sr,
    frame_length=frame_length,
    hop_length=hop_length
)

times = librosa.frames_to_time(
    np.arange(len(f0)),
    sr=sr,
    hop_length=hop_length
)

notes = []

for freq in f0:
    if np.isnan(freq) or freq <= 0:
        notes.append("Pauza")
    else:
        midi = librosa.hz_to_midi(freq)
        midi = int(round(midi))
        note = librosa.midi_to_note(midi)
        notes.append(note)

detected_notes = []

current_note = notes[0]
start_time = times[0]

for i in range(1, len(notes)):
    if notes[i] != current_note:
        end_time = times[i]
        duration = end_time - start_time

        if current_note != "Pauza" and duration >= min_duration:
            detected_notes.append({
                "nota": current_note,
                "start": round(start_time, 3),
                "end": round(end_time, 3),
                "durata": round(duration, 3)
            })

        current_note = notes[i]
        start_time = times[i]

end_time = times[-1]
duration = end_time - start_time

if current_note != "Pauza" and duration >= min_duration:
    detected_notes.append({
        "nota": current_note,
        "start": round(start_time, 3),
        "end": round(end_time, 3),
        "durata": round(duration, 3)
    })

print("\nNote detectate cu YIN:\n")

for i, item in enumerate(detected_notes, start=1):
    print(
        f"{i}. {item['nota']} | "
        f"start: {item['start']}s | "
        f"end: {item['end']}s | "
        f"durata: {item['durata']}s"
    )

print("\nNumar total de note detectate:", len(detected_notes))

counter = Counter([item["nota"] for item in detected_notes])

print("\nCounter note:")
for note, count in counter.items():
    print(f"{note}: {count}")
