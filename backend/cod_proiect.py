import os
from scipy.io.wavfile import read
from scipy.signal import medfilt
import numpy as np
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import librosa
import librosa.display


def detect_peaks(mag_spectrum, threshold_ratio=0.3):
    peaks = []
    mags = []

    thr = threshold_ratio * np.max(mag_spectrum)

    for k in range(1, len(mag_spectrum) - 1):
        if mag_spectrum[k] > mag_spectrum[k - 1] and mag_spectrum[k] > mag_spectrum[k + 1]:
            if mag_spectrum[k] > thr:
                peaks.append(k)
                mags.append(mag_spectrum[k])

    return peaks, mags


def hps_f0(mag_spectrum, fs, harmonics=5):
    spectrum = mag_spectrum.copy()
    n_bins = len(spectrum)

    hps = spectrum.copy()

    for h in range(2, harmonics + 1):
        down = spectrum[::h]
        hps[:len(down)] *= down

    idx = np.argmax(hps)
    f0 = idx * (fs / 2) / (n_bins - 1)

    return f0


def estimate_bpm(onsets, hop_size, fs):
    hop_time = hop_size / fs
    onset_times = [o * hop_time for o in onsets]

    intervals = []
    for i in range(1, len(onset_times)):
        intervals.append(onset_times[i] - onset_times[i - 1])

    if len(intervals) == 0:
        return 120.0

    beat_duration = np.median(intervals)

    if beat_duration <= 0:
        return 120.0

    bpm = 60.0 / beat_duration
    return bpm


def merge_consecutive_same_notes(final_notes):
    if len(final_notes) == 0:
        return []

    merged = [list(final_notes[0])]

    for i in range(1, len(final_notes)):
        note_name, f0, st, en, dur = final_notes[i]

        prev_note_name, prev_f0, prev_st, prev_en, prev_dur = merged[-1]

        if note_name == prev_note_name:
            new_end = en
            new_dur = new_end - prev_st
            new_f0 = (prev_f0 + f0) / 2.0

            merged[-1] = [prev_note_name, new_f0, prev_st, new_end, new_dur]
        else:
            merged.append([note_name, f0, st, en, dur])

    return [tuple(x) for x in merged]


def analyze_audio(audio_path, save_plots=True):
    fn = os.path.splitext(os.path.basename(audio_path))[0]
    fig_base_dir = f"./figures/{fn}/"
    os.makedirs(fig_base_dir, exist_ok=True)

    frame_size = 2048
    hop_size = 512

    # ======================
    # 1. LOAD + PREPROCESS
    # ======================

    fs, x = read(audio_path)
    print("Sampling rate:", fs)

    if x.ndim == 2:
        x = x[:, 0]

    x = x.astype(np.float32)

    max_val = np.max(np.abs(x))
    if max_val > 0:
        x = x / max_val

    print("Number of samples:", x.size)
    print("Timpul (secunde):", x.size / fs)

    t = np.arange(x.size) / float(fs)

    # ======================
    # 2. WAVEFORM PLOTS
    # ======================

    if save_plots:
        plt.figure(figsize=(10, 4))
        plt.plot(t, x)
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude")
        plt.title("Piano waveform")
        plt.tight_layout()
        plt.savefig(os.path.join(fig_base_dir, "waveform_matplotlib.png"), dpi=300)
        plt.close()

        plt.figure(figsize=(10, 4))
        librosa.display.waveshow(x, sr=fs, color="blue")
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude")
        plt.title("Waveform (librosa)")
        plt.tight_layout()
        plt.savefig(os.path.join(fig_base_dir, "waveform_librosa.png"), dpi=300)
        plt.close()

    # ======================
    # 3. SPECTROGRAM (STFT)
    # ======================

    stft = librosa.stft(x, n_fft=4096, hop_length=256, window="hann")
    spectrogram_db = librosa.amplitude_to_db(np.abs(stft), ref=np.max)

    if save_plots:
        plt.figure(figsize=(10, 4))
        librosa.display.specshow(
            spectrogram_db,
            sr=fs,
            hop_length=256,
            x_axis="time",
            y_axis="log",
            cmap="magma"
        )
        plt.colorbar()
        plt.title("Spectrogram (librosa, log-frequency)")
        plt.tight_layout()
        plt.savefig(os.path.join(fig_base_dir, "spectrogram_librosa.png"), dpi=300)
        plt.close()

    # ======================
    # 4. FRAME + FFT
    # ======================

    window = np.hanning(frame_size)
    fft_frames = []

    num_frames = 1 + int((len(x) - frame_size) / hop_size)

    for i in range(num_frames):
        start = i * hop_size
        end = start + frame_size

        frame = x[start:end]
        frame = frame * window

        X = np.fft.rfft(frame)
        fft_frames.append(np.abs(X))

    fft_frames = np.array(fft_frames)
    freqs_per_bin = np.linspace(0, fs / 2, fft_frames.shape[1])

    print("Number of frames:", fft_frames.shape[0])

    # ======================
    # 5. PEAK DETECTION
    # ======================

    peak_freqs = []
    peak_mags = []

    for mag in fft_frames:
        bins, mags = detect_peaks(mag)
        peak_freqs.append(freqs_per_bin[bins])
        peak_mags.append(mags)

    if len(peak_freqs) > 0 and len(peak_freqs[0]) > 0:
        print("First frame peak freqs (Hz):", peak_freqs[0][:10])

    # ======================
    # 6. F0 (HPS)
    # ======================

    f0_per_frame = np.array([hps_f0(mag, fs) for mag in fft_frames])

    print("First 20 raw f0 estimates:", f0_per_frame[:20])

    # ======================
    # 7. SMOOTHING
    # ======================

    f0_smooth = medfilt(f0_per_frame, kernel_size=5)

    if save_plots:
        plt.figure(figsize=(10, 4))
        plt.plot(f0_per_frame, label="Raw f0", alpha=0.7)
        plt.plot(f0_smooth, label="Smoothed f0", linewidth=2)
        plt.legend()
        plt.title("F0 smoothing")
        plt.tight_layout()
        plt.savefig(os.path.join(fig_base_dir, "f0_smoothing.png"), dpi=300)
        plt.close()

    # ======================
    # 8. ONSET DETECTION
    # ======================

    spectral_flux = []

    for i in range(1, len(fft_frames)):
        diff = fft_frames[i] - fft_frames[i - 1]
        diff[diff < 0] = 0
        spectral_flux.append(np.sum(diff))

    spectral_flux = np.array(spectral_flux)

    max_flux = np.max(spectral_flux)
    if max_flux > 0:
        spectral_flux = spectral_flux / max_flux

    if save_plots:
        plt.figure(figsize=(12, 4))
        plt.plot(spectral_flux)
        plt.title("Spectral flux")
        plt.tight_layout()
        plt.savefig(os.path.join(fig_base_dir, "spectral_flux.png"), dpi=300)
        plt.close()

    threshold = 0.2
    onsets = []

    for i in range(1, len(spectral_flux) - 1):
        if spectral_flux[i] > threshold:
            if spectral_flux[i] > spectral_flux[i - 1] and spectral_flux[i] > spectral_flux[i + 1]:
                onsets.append(i)

    if 0 not in onsets:
        onsets.insert(0, 0)

    print("Onset frame indices:", onsets)

    bpm_est = estimate_bpm(onsets, hop_size, fs)
    print("Estimated BPM:", round(bpm_est, 2))

    # ======================
    # 9. NOTE SEGMENTATION
    # ======================

    notes = []
    hop_time = hop_size / fs

    onsets_with_end = onsets + [len(f0_smooth)]

    for i in range(len(onsets)):
        start_f = onsets[i]
        end_f = onsets_with_end[i + 1]

        if end_f <= start_f:
            continue

        f0_segment = f0_smooth[start_f:end_f]
        f0_segment = f0_segment[f0_segment > 10]

        if len(f0_segment) == 0:
            continue

        f0_note = np.median(f0_segment)

        start_time = start_f * hop_time
        end_time = end_f * hop_time
        duration = end_time - start_time

        # Ignore very early noise at the start of the recording
        if start_time < 0.15:
            continue

        # Ignore very short segments
        if duration < 0.08:
            continue

        # Keep only realistic note range for this recording
        if f0_note < 180 or f0_note > 2000:
            continue

        notes.append((f0_note, start_time, end_time, duration))

    print("\n=== Notes (F0 + time) ===")
    for idx, (f0, st, en, dur) in enumerate(notes):
        print(f"Note {idx + 1}: f0={f0:.2f} Hz | start={st:.2f}s | end={en:.2f}s | dur={dur:.2f}s")

    # ======================
    # 10. MAP F0 -> MIDI NOTE
    # ======================

    note_names = ["C", "C#", "D", "D#", "E", "F",
                  "F#", "G", "G#", "A", "A#", "B"]

    final_notes = []

    for (f0, st, en, dur) in notes:
        midi = 69 + 12 * np.log2(f0 / 440.0)
        midi = int(round(midi))

        name = note_names[midi % 12]
        octave = midi // 12 - 1
        note_full = f"{name}{octave}"

        final_notes.append((note_full, f0, st, en, dur))

    # Do not merge repeated notes
    # final_notes = merge_consecutive_same_notes(final_notes)

    print("\n=== DETECTED NOTES ===")
    for idx, (note_txt, f0, st, en, dur) in enumerate(final_notes):
        print(f"{idx + 1}. {note_txt} | f0={f0:.2f} Hz | start={st:.2f}s | end={en:.2f}s | dur={dur:.2f}s")

    return final_notes, bpm_est


if __name__ == "__main__":
    audio_path = "../samples/scale_doremi.wav"

    final_notes, bpm_est = analyze_audio(audio_path, save_plots=True)

    print("\n=== FINAL OUTPUT ===")
    print("Estimated BPM:", round(bpm_est, 2))

    for idx, (note_txt, f0, st, en, dur) in enumerate(final_notes):
        print(f"{idx + 1}. {note_txt} | f0={f0:.2f} Hz | start={st:.2f}s | end={en:.2f}s | dur={dur:.2f}s")