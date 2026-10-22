<template>
  <div class="login-wrap">
    <div class="login-card">
      <div class="login-logo">🧪</div>
      <h2>Personal-Bench</h2>
      <p class="muted">敏捷测试管理与自动化工作台</p>
      <form @submit.prevent="login">
        <input v-model="form.username" aria-label="用户名" placeholder="用户名" required autocomplete="username" />
        <input v-model="form.password" aria-label="密码" type="password" placeholder="密码" required autocomplete="current-password" />
        <button class="btn btn-login" type="submit">登 录 工 作 台</button>
      </form>
      <p v-if="msg" class="msg">{{ msg }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '../api'

const router = useRouter()
const form = ref({ username: 'admin', password: '' })
const msg = ref('')

async function login() {
  msg.value = ''
  try {
    const { data } = await authApi.login(form.value)
    localStorage.setItem('twb_authenticated', '1')
    localStorage.setItem('twb_user', JSON.stringify(data.user))
    router.push('/')
  } catch (e) {
    msg.value = e.response?.data?.detail || '登录失败'
  }
}

onMounted(async () => {
  try {
    const { data } = await authApi.me()
    localStorage.setItem('twb_authenticated', '1')
    localStorage.setItem('twb_user', JSON.stringify(data))
    router.replace('/')
  } catch { /* 尚未登录 */ }
})
</script>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 50% 20%, var(--sidebar-hover) 0%, var(--sidebar-bg) 100%);
  padding: 20px;
}
.login-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  padding: 36px 32px;
  width: min(360px, 100%);
  text-align: center;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
}
.login-logo {
  font-size: 32px;
  margin-bottom: 8px;
}
h2 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-heading);
  margin-bottom: 4px;
}
.muted {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 20px;
}
.login-card form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.login-card input {
  padding: 10px 14px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: all 0.15s ease;
}
.login-card input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--accent-ring);
}
.btn-login {
  height: 40px;
  font-size: 14px;
  font-weight: 600;
  background: var(--accent-primary);
  color: var(--text-inverse);
  border: none;
  border-radius: 8px;
  margin-top: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.btn-login:hover {
  background: var(--accent-hover);
}
.msg {
  color: #dc2626;
  font-size: 13px;
  margin-top: 12px;
}
</style>
