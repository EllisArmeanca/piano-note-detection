<template>
  <div class="page">
    <div class="container">
      <header class="hero">
        <h1>Detectarea automata a notelor de pian</h1>
        <p class="subtitle">
          Aplicatie web pentru analiza semnalelor audio monofonice de pian si generarea automata de partitura.
        </p>
        <p class="limitations">
          Limitari: aplicatia este conceputa pentru inregistrari de pian monofonice, cu cate o singura nota la un moment dat.
        </p>
      </header>

      <section class="card upload-card">
        <h2>Incarcare fisier audio</h2>
        <label class="label">Alege un fisier WAV</label>
        <input type="file" accept=".wav" @change="handleFileChange" />

        <button @click="uploadFile" :disabled="!selectedFile || loading">
             {{ loadingButtonText }}
        </button>

        <p v-if="selectedFile" class="info">
          Fisier selectat: {{ selectedFile.name }}
        </p>

        <p v-if="message" class="success">{{ message }}</p>
        <p v-if="error" class="error">{{ error }}</p>
      </section>

      <section v-if="result" class="card results-card">
        <div class="results-header">
          <div>
            <h2>Rezultate</h2>
            <p><strong>BPM estimat:</strong> {{ result.bpm }}</p>
          </div>
        </div>

        <div class="audio-grid">
  <div class="audio-box" v-if="result.original_audio">
    <h3>Inregistrare originala</h3>
    <audio
      ref="originalAudioRef"
      controls
      :src="mediaUrl(result.original_audio)"
      @play="handleOriginalPlay"
    ></audio>
  </div>

  <div class="audio-box" v-if="result.preview_audio">
    <h3>Preview generat de aplicatie</h3>
    <audio
      ref="previewAudioRef"
      controls
      :src="mediaUrl(result.preview_audio)"
      @play="handlePreviewPlay"
    ></audio>
  </div>
</div>

        <div class="downloads">
          <h3>Fisiere generate</h3>

          <div class="download-list">
            <a
              v-if="result.files.musicxml"
              :href="downloadUrl(result.files.musicxml)"
              target="_blank"
              class="download-link"
            >
              Descarca MusicXML
            </a>

            <a
              v-if="result.files.pdf"
              :href="downloadUrl(result.files.pdf)"
              target="_blank"
              class="download-link"
            >
              Descarca PDF
            </a>

            <a
              v-if="result.files.midi"
              :href="downloadUrl(result.files.midi)"
              target="_blank"
              class="download-link"
            >
              Descarca MIDI
            </a>
          </div>
        </div>

        <div class="notes" v-if="result.notes && result.notes.length">
          <h3>Note detectate</h3>

          <div class="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Nota</th>
                  <th>Frecventa (Hz)</th>
                  <th>Start (s)</th>
                  <th>End (s)</th>
                  <th>Durata (s)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, index) in result.notes" :key="index">
                  <td>{{ index + 1 }}</td>
                  <td>{{ item[0] }}</td>
                  <td>{{ Number(item[1]).toFixed(2) }}</td>
                  <td>{{ Number(item[2]).toFixed(2) }}</td>
                  <td>{{ Number(item[3]).toFixed(2) }}</td>
                  <td>{{ Number(item[4]).toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div v-if="result.figures && result.figures.length" class="graphs">
  <h3>Grafice generate</h3>

  <div class="graph-grid">
    <div v-for="(img, index) in result.figures" :key="index" class="graph-box">
<img 
  :src="mediaUrl(img)" 
  :alt="'Grafic ' + (index + 1)"
  @click="openImage(img)"
  class="clickable-img"
/>    </div>
  </div>
</div>
      </section>
      <div v-if="selectedImage" class="image-modal" @click="closeImage">
  <img :src="mediaUrl(selectedImage)" class="modal-img" />
</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from "vue"
import axios from "axios"

const selectedFile = ref(null)
const loading = ref(false)
const message = ref("")
const error = ref("")
const result = ref(null)

const loadingDots = ref(".")
let loadingInterval = null

const originalAudioRef = ref(null)
const previewAudioRef = ref(null)

const loadingButtonText = computed(() => {
  return loading.value ? `Se proceseaza${loadingDots.value}` : "Incarca si analizeaza"
})

function handleFileChange(event) {
  const file = event.target.files[0]

  selectedFile.value = file || null
  message.value = ""
  error.value = ""
  result.value = null
}

async function uploadFile() {
  if (!selectedFile.value) {
    error.value = "Te rog selecteaza un fisier WAV."
    return
  }

  const formData = new FormData()
  formData.append("file", selectedFile.value)

  loading.value = true
  message.value = ""
  error.value = ""
  result.value = null

  try {
    const response = await axios.post("http://127.0.0.1:5000/api/process", formData, {
      headers: {
        "Content-Type": "multipart/form-data"
      }
    })

    result.value = response.data
    message.value = response.data.message
  } catch (err) {
    if (err.response && err.response.data && err.response.data.error) {
      error.value = err.response.data.error
    } else {
      error.value = "A aparut o eroare la procesare."
    }
  } finally {
    loading.value = false
  }
}

function downloadUrl(path) {
  return `http://127.0.0.1:5000/api/download?path=${encodeURIComponent(path)}`
}

function mediaUrl(path) {
  return `http://127.0.0.1:5000/api/media?path=${encodeURIComponent(path)}`
}

function startLoadingAnimation() {
  loadingDots.value = "."
  loadingInterval = setInterval(() => {
    if (loadingDots.value === "...") {
      loadingDots.value = "."
    } else {
      loadingDots.value += "."
    }
  }, 400)
}

function stopLoadingAnimation() {
  if (loadingInterval) {
    clearInterval(loadingInterval)
    loadingInterval = null
  }
  loadingDots.value = "."
}

function handleOriginalPlay() {
  if (previewAudioRef.value) {
    previewAudioRef.value.pause()
    previewAudioRef.value.currentTime = 0
  }
}

function handlePreviewPlay() {
  if (originalAudioRef.value) {
    originalAudioRef.value.pause()
    originalAudioRef.value.currentTime = 0
  }
}

watch(loading, (newValue) => {
  if (newValue) {
    startLoadingAnimation()
  } else {
    stopLoadingAnimation()
  }
})

onBeforeUnmount(() => {
  stopLoadingAnimation()
})

const selectedImage = ref(null)

function openImage(img) {
  selectedImage.value = img
}

function closeImage() {
  selectedImage.value = null
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f5f7fb 0%, #edf2f9 100%);
  padding: 24px 16px 40px;
  font-family: Arial, sans-serif;
  color: #1f2937;
}

.container {
  max-width: 1100px;
  margin: 0 auto;
}

.hero {
  text-align: center;
  margin-bottom: 24px;
}

.hero h1 {
  margin-bottom: 10px;
  font-size: 34px;
}

.subtitle {
  font-size: 17px;
  color: #4b5563;
  max-width: 850px;
  margin: 0 auto 8px;
  line-height: 1.5;
}

.limitations {
  max-width: 850px;
  margin: 0 auto;
  color: #6b7280;
  font-size: 14px;
}

.card {
  background: #ffffff;
  border-radius: 18px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08);
}

.upload-card h2,
.results-card h2 {
  margin-top: 0;
  margin-bottom: 16px;
}

.label {
  display: block;
  margin-bottom: 10px;
  font-weight: bold;
}

input[type="file"] {
  width: 100%;
  margin-bottom: 16px;
}

.actions {
  margin-bottom: 10px;
}

button {
  display: inline-block;
  padding: 12px 20px;
  border: none;
  border-radius: 10px;
  background: #1f6feb;
  color: white;
  cursor: pointer;
  font-size: 15px;
  font-weight: bold;
}

button:disabled {
  background: #9aa4b2;
  cursor: not-allowed;
}

.info {
  margin-top: 12px;
  color: #374151;
}

.success {
  margin-top: 14px;
  color: #15803d;
  font-weight: bold;
}

.error {
  margin-top: 14px;
  color: #b91c1c;
  font-weight: bold;
}

.results-header {
  margin-bottom: 18px;
}

.audio-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 24px;
}

.audio-box {
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 16px;
}

.audio-box h3 {
  margin-top: 0;
  margin-bottom: 12px;
  font-size: 18px;
}

audio {
  width: 100%;
}

.downloads {
  margin-bottom: 24px;
}

.download-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.download-link {
  display: inline-block;
  padding: 10px 14px;
  border-radius: 10px;
  background: #eef4ff;
  color: #1f6feb;
  text-decoration: none;
  font-weight: bold;
}

.download-link:hover {
  background: #dfeaff;
}

.notes {
  margin-top: 10px;
}

.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  min-width: 700px;
  border-collapse: collapse;
  margin-top: 10px;
}

th,
td {
  border: 1px solid #d1d5db;
  padding: 10px;
  text-align: center;
}

th {
  background: #eef3fb;
}

@media (max-width: 768px) {
  .hero h1 {
    font-size: 26px;
  }

  .subtitle {
    font-size: 15px;
  }

  .card {
    padding: 18px;
  }

  .audio-grid {
    grid-template-columns: 1fr;
  }

  button {
    width: 100%;
  }
}

.graphs {
  margin-top: 30px;
}

.graph-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.graph-box img {
  width: 100%;
  border-radius: 10px;
  border: 1px solid #ddd;
}

@media (max-width: 768px) {
  .graph-grid {
    grid-template-columns: 1fr;
  }
}

.clickable-img {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.clickable-img:hover {
  transform: scale(1.03);
}

/* Modal fullscreen */
.image-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 999;
}

/* Imagine mare */
.modal-img {
  max-width: 90%;
  max-height: 90%;
  border-radius: 12px;
}
</style>