# Monophonic piano note analysis: waveform, spectrogram, F0 detection, onsets, notes + durations

#importuri:
import os
from scipy.io.wavfile import read
from scipy.signal import medfilt
import numpy as np
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import librosa
import librosa.display

#detectarea varfurilor
def detect_peaks(mag_spectrum, threshold_ratio=0.3):
    peaks = []
    mags = []

    # Threshold to ignore small values / noise

    thr = threshold_ratio * np.max(mag_spectrum)

    # ne uitam pe spectru, fara primul si ultimul element
    #maxim local, verificam daca e peste threshold
    for k in range(1, len(mag_spectrum) - 1):
        if mag_spectrum[k] > mag_spectrum[k - 1] and mag_spectrum[k] > mag_spectrum[k + 1]:
            if mag_spectrum[k] > thr:
                peaks.append(k)
                mags.append(mag_spectrum[k])

    return peaks, mags


#functie hps - estimeaza f0 folosind HPS
def hps_f0(mag_spectrum, fs, harmonics=5):
    spectrum = mag_spectrum.copy() # spectrul de magnitudine
    n_bins = len(spectrum)

    hps = spectrum.copy() # initializam hps  cu spectrul original

    for h in range(2, harmonics + 1): # Multiply with downsampled
        down = spectrum[::h]
        hps[:len(down)] *= down

    idx = np.argmax(hps) # Index of maximum in HPS
    f0 = idx * (fs / 2) / (n_bins - 1) # Convertim varful indexului to frequency

    return f0

# bpm-ul este estimat pe baza distantei dintre onseturi 
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

#functie principala de analiza audio 

def analyze_audio(audio_path, save_plots=True):
    fn = os.path.splitext(os.path.basename(audio_path))[0]
    fig_base_dir = f"./figures/{fn}/"
    os.makedirs(fig_base_dir, exist_ok=True)

    frame_size = 2048
    hop_size = 512

    # -------
    # 1. LOAD + PREPROCESS
    # ----------
    #PSEUDOCOD:
    # 1. Citim fisierul audio WAV.
    # 2. Convertim la mono daca fisierul este stereo.
    # 3. Normalizam semnalul.


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

    # -----------
    # 2. WAVEFORM PLOTS
    # -----------
    #PSEUDOCOD: 
    # 4. Generam waveform si spectrograma.


    #plot clasic cu matplotlib si plot cu librosa
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

    # -----------
    # 3. SPECTROGRAM (STFT)
    # -----------

    stft = librosa.stft(x, n_fft=4096, hop_length=256, window="hann")
    spectrogram_db = librosa.amplitude_to_db(np.abs(stft), ref=np.max)
   
    # Display spectrogram: time on x-axis, log-frequency on y-axis.

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

    # -----------
    # 4. FRAME + FFT
    # -----------

    # window hann pentru spectral leakage
    window = np.hanning(frame_size)
    fft_frames = [] # spectrul de magnitudine pe fiecare fereastra.


    num_frames = 1 + int((len(x) - frame_size) / hop_size)

    for i in range(num_frames):
        start = i * hop_size
        end = start + frame_size

        frame = x[start:end] #extragem frame
        frame = frame * window #aplicam hann

        X = np.fft.rfft(frame) #real fft
        fft_frames.append(np.abs(X))

    fft_frames = np.array(fft_frames) # *num_frames, num_bins)
    freqs_per_bin = np.linspace(0, fs / 2, fft_frames.shape[1])

    print("Number of frames:", fft_frames.shape[0])

    # -----------
    # 5. PEAK DETECTION
    # -----------
    #PSEUDOCOD:
    # 5. Impartim semnalul in frame-uri.
    # 6. Aplicam fereastra Hann si FFT pe fiecare frame.

    peak_freqs = []
    peak_mags = []

    for mag in fft_frames:
        bins, mags = detect_peaks(mag)
        peak_freqs.append(freqs_per_bin[bins])
        peak_mags.append(mags)

    if len(peak_freqs) > 0 and len(peak_freqs[0]) > 0:
        print("First frame peak freqs (Hz):", peak_freqs[0][:10])

    # -----------
    # 6. F0 (HPS)
    # -----------
    #PSEUDOCOD:
    # 7. Estimam F0 folosind HPS.


    f0_per_frame = np.array([hps_f0(mag, fs) for mag in fft_frames])

    print("First 20 raw f0 estimates:", f0_per_frame[:20])

    # -----------
    # 7. SMOOTHING
    # -----------
    #PSEUDOCOD: # 8. Netezim valorile F0 cu filtrare mediana.


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

    # -----------
    # 8. ONSET DETECTION
    # -----------
    #PSEUDOCOD: # 9. Detectam onset-uri folosind spectral flux.


    # Spectral flux measures how much the spectrum changes between consecutive frames.
    # Onsets usually correspond to large positive changes in the spectrum.
    spectral_flux = []

    for i in range(1, len(fft_frames)):
        diff = fft_frames[i] - fft_frames[i - 1] # diff intre actual si precedent
        diff[diff < 0] = 0 # pastram doar dif pozitive
        spectral_flux.append(np.sum(diff)) # Spectral flux = sum of positive changes

    spectral_flux = np.array(spectral_flux)

    max_flux = np.max(spectral_flux)
    if max_flux > 0:
        spectral_flux = spectral_flux / max_flux # normalizare
 
    if save_plots:
        plt.figure(figsize=(12, 4))
        plt.plot(spectral_flux)
        plt.title("Spectral flux")
        plt.tight_layout()
        plt.savefig(os.path.join(fig_base_dir, "spectral_flux.png"), dpi=300)
        plt.close()

# Threshold for spectral flux peaks.
# Lower value (=0.2) is more sensitive, detects softer onsets.
    threshold = 0.2
    onsets = []

    # We detect local maxima in the spectral flux that are above threshold.

    for i in range(1, len(spectral_flux) - 1):
        if spectral_flux[i] > threshold:
            if spectral_flux[i] > spectral_flux[i - 1] and spectral_flux[i] > spectral_flux[i + 1]:
                onsets.append(i)

    # For safety, we always include the first frame as an onset
    # so that the first note is not missed.
    if 0 not in onsets:
        onsets.insert(0, 0)

    print("Onset frame indices:", onsets)

    bpm_est = estimate_bpm(onsets, hop_size, fs)
    print("Estimated BPM:", round(bpm_est, 2))

    # -----------
    # 9. NOTE SEGMENTATION
    # -----------
    #PSEUDOCOD: # 10. Segmentam notele intre onset-uri consecutive.

    # fiecare nota intre doua onset consecutive
    notes = [] # list of (f0_note, start_time, end_time, duration)
    hop_time = hop_size / fs # seconds per frame

    onsets_with_end = onsets + [len(f0_smooth)]

    for i in range(len(onsets)):
        start_f = onsets[i]
        end_f = onsets_with_end[i + 1]

        if end_f <= start_f:
            continue

        # Extract F0 values
        f0_segment = f0_smooth[start_f:end_f]
        # Remove zero or very low F0 values
        f0_segment = f0_segment[f0_segment > 10]

        if len(f0_segment) == 0:
            continue

        f0_note = np.median(f0_segment)

        # frame -> time conversion
        start_time = start_f * hop_time
        end_time = end_f * hop_time
        duration = end_time - start_time

      

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

    # -----------
    # 10. MAP F0 -> MIDI NOTE
    # -----------
    #PSEUDOCOD: # 11. Convertim frecventele F0 in note MIDI.


    note_names = ["C", "C#", "D", "D#", "E", "F",
                  "F#", "G", "G#", "A", "A#", "B"]

    final_notes = []

    for (f0, st, en, dur) in notes:

    # Convert frequency (Hz) to MIDI note number.
    # Formula: midi = 69 + 12 * log2(f0 / 440)
        midi = 69 + 12 * np.log2(f0 / 440.0)
        midi = int(round(midi))

    # Get note name and octave from MIDI number
        name = note_names[midi % 12]
        octave = midi // 12 - 1
        note_full = f"{name}{octave}"

        final_notes.append((note_full, f0, st, en, dur))


    #PSEUDOCOD: 12. Returnam notele finale si BPM-ul estimat.

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