<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { uploadPaper } from '../api/papers'

const router = useRouter()

const MAX_FILE_SIZE = 50 * 1024 * 1024

const selectedFile = ref(null)
const errorMessage = ref('')
const successMessage = ref('')
const uploading = ref(false)
const uploadProgress = ref(0)
const isDragging = ref(false)

const fileInputRef = ref(null)

function validateAndSelectFile(file) {
  selectedFile.value = null
  errorMessage.value = ''
  successMessage.value = ''

  if (!file) return

  if (!file.name.toLowerCase().endsWith('.pdf')) {
    errorMessage.value = '仅支持 PDF 格式文件，请重新选择。'
    return
  }

  if (file.size > MAX_FILE_SIZE) {
    errorMessage.value = '文件超过 50MB，请选择更小的 PDF。'
    return
  }

  selectedFile.value = file
  successMessage.value = '文件格式正确，可以继续上传。'
}

function handleFileChange(event) {
  const file = event.target.files?.[0]
  validateAndSelectFile(file)
  event.target.value = ''
}

function handleDropZoneClick() {
  if (uploading.value) return
  fileInputRef.value?.click()
}

function handleDragOver(event) {
  event.preventDefault()
  if (uploading.value) return
  isDragging.value = true
}

function handleDragLeave(event) {
  event.preventDefault()
  isDragging.value = false
}

function handleDrop(event) {
  event.preventDefault()
  isDragging.value = false
  if (uploading.value) return

  const file = event.dataTransfer.files?.[0]
  validateAndSelectFile(file)
}

function resetFile() {
  selectedFile.value = null
  errorMessage.value = ''
  successMessage.value = ''
  uploading.value = false
  uploadProgress.value = 0
}

async function handleUpload() {
  if (!selectedFile.value || uploading.value) return

  uploading.value = true
  uploadProgress.value = 0
  errorMessage.value = ''
  successMessage.value = ''

  try {
    await uploadPaper(selectedFile.value, (progress) => {
      uploadProgress.value = progress
    })
    router.push('/library')
  } catch (error) {
    errorMessage.value = error.message || '上传失败，请稍后重试。'
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <main class="upload-page">
    <section class="upload-card">
      <h1>PaperMind</h1>
      <p class="subtitle">智能论文阅读助手</p>

      <div
        class="upload-area"
        :class="{ 'is-dragging': isDragging }"
        @click="handleDropZoneClick"
        @dragover="handleDragOver"
        @dragleave="handleDragLeave"
        @drop="handleDrop"
      >
        <h2>上传文献</h2>
        <p>点击选择，或将 PDF 拖拽到此处</p>

        <input
          ref="fileInputRef"
          type="file"
          accept=".pdf"
          class="file-input"
          @change="handleFileChange"
        />

        <label class="select-button" @click.stop="handleDropZoneClick">
          选择文件
        </label>

        <p v-if="selectedFile" class="file-name">
          已选择：{{ selectedFile.name }}
        </p>

        <p v-if="errorMessage" class="error-message" role="alert">
          {{ errorMessage }}
        </p>

        <p v-if="successMessage" class="success-message" role="status">
          {{ successMessage }}
        </p>

        <div v-if="uploading" class="progress-container">
          <div class="progress-bar">
            <div
              class="progress-fill"
              :style="{ width: uploadProgress + '%' }"
            ></div>
          </div>
          <span class="progress-text">{{ uploadProgress }}%</span>
        </div>

        <div v-if="selectedFile" class="action-buttons">
          <button
            class="upload-button"
            :disabled="uploading"
            @click.stop="handleUpload"
          >
            {{ uploading ? '上传中…' : '上传文献' }}
          </button>

          <button
            class="reset-button"
            :disabled="uploading"
            @click.stop="resetFile"
          >
            重新选择
          </button>
        </div>
      </div>
    </section>
  </main>
</template>

<style scoped>
.upload-page {
  min-height: 100vh;
  padding: 48px 20px;
  background: #f5f7fb;
  color: #243047;
  font-family: Arial, sans-serif;
}

.upload-card {
  max-width: 720px;
  margin: 40px auto;
  text-align: center;
}

h1 {
  margin-bottom: 8px;
  color: #3568d4;
}

.subtitle {
  color: #718096;
}

.upload-area {
  margin-top: 36px;
  padding: 48px 24px;
  background: white;
  border: 2px dashed #aab9d1;
  border-radius: 16px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.upload-area.is-dragging {
  border-color: #3568d4;
  background: #eef4ff;
}

.upload-area h2 {
  margin-top: 0;
}

.upload-area > p {
  color: #718096;
}

.file-input {
  display: none;
}

.select-button,
.upload-button,
.reset-button {
  display: inline-block;
  padding: 10px 22px;
  border: 0;
  border-radius: 8px;
  background: #3568d4;
  color: white;
  cursor: pointer;
  font-size: 14px;
}

.action-buttons {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 20px;
}

.upload-button {
  background: #21834a;
}

.upload-button:disabled,
.reset-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.reset-button {
  background: #6b7280;
}

.file-name {
  overflow-wrap: anywhere;
}

.upload-area .error-message {
  margin-top: 18px;
  color: #d93025;
  font-weight: 600;
}

.upload-area .success-message {
  margin-top: 18px;
  color: #21834a;
  font-weight: 600;
}

.progress-container {
  margin-top: 22px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  height: 10px;
  background: #e2e8f0;
  border-radius: 5px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #21834a;
  border-radius: 5px;
  transition: width 0.2s ease;
}

.progress-text {
  min-width: 42px;
  text-align: right;
  font-size: 13px;
  font-weight: 600;
  color: #21834a;
}
</style>