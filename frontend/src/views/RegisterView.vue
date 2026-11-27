<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})
const errors = reactive({
  username: '',
  password: '',
  confirmPassword: '',
})
const showPassword = ref(false)
const submitting = ref(false)
const serverError = ref('')

function validateUsername() {
  const v = form.username.trim()
  if (!v) return '请输入用户名'
  if (v.length < 3 || v.length > 20) return '用户名长度需在 3-20 位之间'
  if (!/^[A-Za-z0-9_]+$/.test(v)) return '用户名只能包含字母、数字和下划线'
  return ''
}

function validatePassword() {
  if (!form.password) return '请输入密码'
  if (form.password.length < 6 || form.password.length > 20) return '密码长度需在 6-20 位之间'
  return ''
}

function validateConfirmPassword() {
  if (!form.confirmPassword) return '请再次输入密码'
  if (form.confirmPassword !== form.password) return '两次输入的密码不一致'
  return ''
}

function handleSubmit() {
  serverError.value = ''
  errors.username = validateUsername()
  errors.password = validatePassword()
  errors.confirmPassword = validateConfirmPassword()
  if (errors.username || errors.password || errors.confirmPassword) return

  submitting.value = true
  setTimeout(() => {
    submitting.value = false
    router.push('/login')
  }, 500)
}
</script>

<template>
  <main class="auth-page">
    <section class="auth-card">
      <h1>注册</h1>
      <p class="subtitle">创建账号，开始管理你的文献。</p>

      <form class="form" @submit.prevent="handleSubmit">
        <div class="field">
          <label for="username">用户名</label>
          <input
            id="username"
            type="text"
            v-model="form.username"
            placeholder="3-20 位字母、数字或下划线"
            autocomplete="username"
            spellcheck="false"
            @blur="errors.username = validateUsername()"
          />
          <p v-if="errors.username" class="field-error" role="alert">{{ errors.username }}</p>
        </div>

        <div class="field">
          <label for="password">密码</label>
          <div class="input-with-action">
            <input
              id="password"
              :type="showPassword ? 'text' : 'password'"
              v-model="form.password"
              placeholder="6-20 位"
              autocomplete="new-password"
              spellcheck="false"
              @blur="errors.password = validatePassword()"
            />
            <button type="button" class="toggle-btn" @click="showPassword = !showPassword">
              {{ showPassword ? '隐藏' : '显示' }}
            </button>
          </div>
          <p v-if="errors.password" class="field-error" role="alert">{{ errors.password }}</p>
        </div>

        <div class="field">
          <label for="confirmPassword">确认密码</label>
          <input
            id="confirmPassword"
            type="password"
            v-model="form.confirmPassword"
            placeholder="请再次输入密码"
            autocomplete="new-password"
            spellcheck="false"
            @blur="errors.confirmPassword = validateConfirmPassword()"
          />
          <p v-if="errors.confirmPassword" class="field-error" role="alert">
            {{ errors.confirmPassword }}
          </p>
        </div>

        <p v-if="serverError" class="error-message" role="alert">{{ serverError }}</p>

        <button type="submit" class="submit-btn" :disabled="submitting">
          {{ submitting ? '注册中…' : '注册' }}
        </button>
      </form>

      <p class="switch-link">
        已有账号？
        <RouterLink to="/login">去登录</RouterLink>
      </p>
    </section>
  </main>
</template>

<style scoped>
.auth-page {
  min-height: 100vh;
  padding: 48px 20px;
  background: #f5f7fb;
  color: #243047;
  font-family: Arial, sans-serif;
}

.auth-card {
  max-width: 400px;
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

.form {
  display: flex;
  flex-direction: column;
  gap: 18px;
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

.field-error {
  margin: 0;
  color: #dc2626;
  font-size: 12px;
  line-height: 1.5;
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

.submit-btn {
  padding: 10px 24px;
  border: 0;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.submit-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.switch-link {
  margin: 20px 0 0;
  text-align: center;
  color: #64748b;
  font-size: 13px;
}

.switch-link a {
  color: #2563eb;
  text-decoration: none;
}

.switch-link a:hover {
  text-decoration: underline;
}

@media (max-width: 480px) {
  .auth-card {
    padding: 20px;
  }
}
</style>