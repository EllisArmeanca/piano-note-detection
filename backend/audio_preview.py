import numpy as np
from scipy.io.wavfile import write

PREVIEW_SR = 44100


def note_to_frequency(note_name):
    # Converteste nota text in frecventa
    note_map = {
        "C": 0,
        "C#": 1,
        "D": 2,
        "D#": 3,
        "E": 4,
        "F": 5,
        "F#": 6,
        "G": 7,
        "G#": 8,
        "A": 9,
        "A#": 10,
        "B": 11,
    }

    if len(note_name) < 2:
        return None

    if len(note_name) >= 3 and note_name[1] == "#":
        pitch = note_name[:2]
        octave = int(note_name[2:])
    else:
        pitch = note_name[:1]
        octave = int(note_name[1:])

    midi = (octave + 1) * 12 + note_map[pitch]
    freq = 440.0 * (2 ** ((midi - 69) / 12.0))
    return freq


def synthesize_note(freq, duration_sec, sr=PREVIEW_SR):
    # Genereaza un sunet mai apropiat de ideea de pian
    if freq is None or duration_sec <= 0:
        return np.array([], dtype=np.float32)

    n_samples = int(sr * duration_sec)
    if n_samples <= 0:
        return np.array([], dtype=np.float32)

    t = np.linspace(0, duration_sec, n_samples, endpoint=False)

    # Cateva armonici simple
    signal = (
        0.75 * np.sin(2 * np.pi * freq * t) +
        0.18 * np.sin(2 * np.pi * 2 * freq * t) +
        0.10 * np.sin(2 * np.pi * 3 * freq * t) +
        0.05 * np.sin(2 * np.pi * 4 * freq * t)
    )

    # Envelope mai "pian-like":
    # atac rapid + decay mai evident
    attack_time = 0.01
    attack_len = max(1, int(sr * attack_time))

    envelope = np.ones_like(signal)

    # Attack
    envelope[:attack_len] = np.linspace(0, 1, attack_len)

    # Exponential decay pe toata nota
    decay_curve = np.exp(-3.5 * t / max(duration_sec, 1e-6))
    envelope *= decay_curve

    # Mic release la final
    release_len = min(int(0.03 * sr), len(signal))
    if release_len > 1:
        envelope[-release_len:] *= np.linspace(1, 0, release_len)

    signal = signal * envelope
    return signal.astype(np.float32)


def generate_preview_audio(final_notes, output_path, sr=PREVIEW_SR):
    # Construieste preview-ul audio pe baza notelor detectate
    if not final_notes:
        empty = np.zeros(sr // 2, dtype=np.float32)
        write(output_path, sr, (empty * 32767).astype(np.int16))
        return output_path

    audio_parts = []

    for i, (note_name, f0, start_time, end_time, duration_sec) in enumerate(final_notes):
        # Timpul pana la urmatoarea nota
        if i < len(final_notes) - 1:
            next_start = final_notes[i + 1][2]
        else:
            next_start = end_time

        # Durata efectiva pentru preview:
        # scurtam putin nota ca sa lasam respiratie intre note
        raw_note_len = max(0.05, duration_sec * 0.82)

        # Nu depasim inceputul urmatoarei note
        max_allowed = max(0.05, next_start - start_time - 0.02)
        play_duration = min(raw_note_len, max_allowed)

        freq = note_to_frequency(note_name)
        note_audio = synthesize_note(freq, play_duration, sr=sr)
        audio_parts.append(note_audio)

        # Dupa nota, adaugam pauza reala pana la urmatoarea nota
        silence_after = max(0.0, next_start - start_time - play_duration)
        if silence_after > 0:
            silence = np.zeros(int(sr * silence_after), dtype=np.float32)
            audio_parts.append(silence)

    full_audio = np.concatenate(audio_parts) if audio_parts else np.zeros(sr // 2, dtype=np.float32)

    max_val = np.max(np.abs(full_audio))
    if max_val > 0:
        full_audio = full_audio / max_val

    write(output_path, sr, (full_audio * 32767).astype(np.int16))
    return output_path