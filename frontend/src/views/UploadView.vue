<script setup>
import { ref } from 'vue'

const selectedFile = ref(null)
const errorMessage = ref('')
const successMessage = ref('')

function handleFileChange(event) {
  const file = event.target.files?.[0]

  selectedFile.value = null
  errorMessage.value = ''
  successMessage.value = ''

  if (!file) return

  // 仅允许 PDF 文件
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    errorMessage.value = '仅支持 PDF 格式文件，请重新选择。'
    event.target.value = ''
    return
  }

  selectedFile.value = file
  successMessage.value = '文件格式正确，可以继续上传。'
}

function resetFile() {
  selectedFile.value = null
  errorMessage.value = ''
  successMessage.value = ''
}
</script>

<template>
  <main class="upload-page">
    <section class="upload-card">
      <h1>PaperMind</h1>
      <p class="subtitle">智能论文阅读助手</p>

      <div class="upload-area">
        <h2>上传文献</h2>
        <p>选择 PDF 文件，开始你的论文阅读之旅</p>

        <input
          id="file-input"
          type="file"
          @change="handleFileChange"
        />

        <label for="file-input" class="select-button">
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

        <button
          v-if="selectedFile"
          class="reset-button"
          @click="resetFile"
        >
          重新选择
        </button>
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
  border: 1px dashed #aab9d1;
  border-radius: 16px;
}

.upload-area h2 {
  margin-top: 0;
}

.upload-area > p {
  color: #718096;
}

input[type="file"] {
  display: block;
  max-width: 100%;
  margin: 24px auto 12px;
}

.select-button,
.reset-button {
  display: inline-block;
  padding: 10px 22px;
  border: 0;
  border-radius: 8px;
  background: #3568d4;
  color: white;
  cursor: pointer;
}

.reset-button {
  margin-left: 8px;
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
</style>
