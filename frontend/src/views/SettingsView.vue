<script setup>
import { ref } from 'vue'
import { useSettings } from '../composables/useSettings'

const { settings, updateSettings, resetSettings, isConfigured } = useSettings()

const apiKey = ref(settings.value.apiKey)
const baseUrl = ref(settings.value.baseUrl)
const model = ref(settings.value.model)
const showKey = ref(false)
const saved = ref(false)
const error = ref('')

function handleSave() {
  error.value = ''
  saved.value = false

  const key = apiKey.value.trim()
  const url = baseUrl.value.trim()
  const mdl = model.value.trim()

  if (!key) {
    error.value = '请输入 API Key'
    return
  }
  if (!url) {
    error.value = '请输入 API 地址'
    return
  }
  if (!mdl) {
    error.value = '请输入模型名称'
    return
  }

  try {
    new URL(url)
  } catch {
    error.value = 'API 地址格式不正确，请输入以 http:// 或 https:// 开头的地址'
    return
  }

  updateSettings({ apiKey: key, baseUrl: url, model: mdl })
  saved.value = true
  setTimeout(() => {
    saved.value = false
  }, 2000)
}

function handleReset() {
  resetSettings()
  apiKey.value = ''
  baseUrl.value = 'https://api.deepseek.com'
  model.value = 'deepseek-chat'
  saved.value = false
  error.value = ''
}

function toggleShowKey() {
  showKey.value = !showKey.value
}

const configured = isConfigured()
</script>

<template>
  <main class="settings-page">
    <section class="settings-card">
      <h1>AI 问答设置</h1>
      <p class="subtitle">
        配置大模型 API 后，即可在阅读器中向 AI 提问。密钥仅保存在你的浏览器本地，不会上传到服务器。
      </p>

      <div v-if="!configured" class="notice warning">
        <strong>尚未配置 API Key</strong>
        <span>问答功能将无法使用，请先在下方填入配置并保存。</span>
      </div>
      <div v-else class="notice success">
        <strong>已配置</strong>
        <span>当前模型：{{ settings.model }}</span>
      </div>

      <form class="form" @submit.prevent="handleSave">
        <div class="field">
          <label for="apiKey">API Key</label>
          <div class="input-with-action">
            <input
              id="apiKey"
              :type="showKey ? 'text' : 'password'"
              v-model="apiKey"
              placeholder="sk-xxxxxxxxxxxxxxxx"
              autocomplete="off"
              spellcheck="false"
            />
            <button type="button" class="toggle-btn" @click="toggleShowKey">
              {{ showKey ? '隐藏' : '显示' }}
            </button>
          </div>
          <p class="hint">
            在
            <a href="https://platform.deepseek.com" target="_blank" rel="noopener">DeepSeek 开放平台</a>
            获取。请勿泄露给他人。
          </p>
        </div>

        <div class="field">
          <label for="baseUrl">API 地址</label>
          <input
            id="baseUrl"
            type="text"
            v-model="baseUrl"
            placeholder="https://api.deepseek.com"
            spellcheck="false"
          />
          <p class="hint">OpenAI 兼容接口的 Base URL，默认 DeepSeek 官方地址。</p>
        </div>

        <div class="field">
          <label for="model">模型名称</label>
          <input
            id="model"
            type="text"
            v-model="model"
            placeholder="deepseek-chat"
            spellcheck="false"
          />
          <p class="hint">如 deepseek-chat、deepseek-reasoner 等。</p>
        </div>

        <p v-if="error" class="error-message" role="alert">{{ error }}</p>
        <p v-if="saved" class="success-message" role="status">配置已保存</p>

        <div class="actions">
          <button type="submit" class="save-btn">保存配置</button>
          <button type="button" class="reset-btn" @click="handleReset">
            恢复默认
          </button>
        </div>
      </form>
    </section>
  </main>
</template>

<style scoped>
.settings-page {
  min-height: 100vh;
  padding: 48px 20px;
  background: #f5f7fb;
  color: #243047;
  font-family: Arial, sans-serif;
}

.settings-card {
  max-width: 640px;
  margin: 0 auto;
  padding: 32px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgb(15 23 42 / 6%);
}

h1 {
  margin: 0 0 8px;
  color: #1e293b;
  font-size: 24px;
}

.subtitle {
  margin: 0 0 24px;
  color: #64748b;
  font-size: 14px;
  line-height: 1.6;
}

.notice {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 24px;
  font-size: 14px;
  line-height: 1.6;
}

.notice strong {
  display: block;
  margin-bottom: 4px;
}

.notice.warning {
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
}

.notice.success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field label {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.field input {
  padding: 10px 12px;
  border: 1px solid #d5dce5;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  outline: none;
  transition: border-color 0.2s;
}

.field input:focus {
  border-color: #2563eb;
}

.input-with-action {
  display: flex;
  gap: 8px;
}

.input-with-action input {
  flex: 1;
}

.toggle-btn {
  padding: 0 14px;
  border: 1px solid #d5dce5;
  border-radius: 8px;
  background: white;
  color: #475569;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}

.toggle-btn:hover {
  background: #f8fafc;
}

.hint {
  margin: 0;
  color: #94a3b8;
  font-size: 12px;
  line-height: 1.5;
}

.hint a {
  color: #2563eb;
  text-decoration: none;
}

.hint a:hover {
  text-decoration: underline;
}

.error-message {
  margin: 0;
  padding: 10px 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 14px;
}

.success-message {
  margin: 0;
  padding: 10px 12px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 8px;
  color: #166534;
  font-size: 14px;
}

.actions {
  display: flex;
  gap: 12px;
  margin-top: 4px;
}

.save-btn {
  padding: 10px 24px;
  border: 0;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.save-btn:hover {
  background: #1d4ed8;
}

.reset-btn {
  padding: 10px 24px;
  border: 1px solid #d5dce5;
  border-radius: 8px;
  background: white;
  color: #475569;
  font-size: 14px;
  cursor: pointer;
}

.reset-btn:hover {
  background: #f8fafc;
}

@media (max-width: 480px) {
  .settings-card {
    padding: 20px;
  }

  .actions {
    flex-direction: column;
  }

  .save-btn,
  .reset-btn {
    width: 100%;
  }
}
</style>