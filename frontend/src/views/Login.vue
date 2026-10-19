<template>
  <div class="login-wrap">
    <div class="login-card">
      <h2>🧪 测试工作台</h2>
      <p class="muted">一站式测试管理平台</p>
      <form @submit.prevent="login">
        <input v-model="form.username" placeholder="用户名" required />
        <input v-model="form.password" type="password" placeholder="密码" required />
        <button class="btn" type="submit" style="width:100%">登 录</button>
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
.login-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: #0f172a; }
.login-card { background: #fff; border-radius: 12px; padding: 36px; width: 340px; text-align: center; }
h2 { margin-bottom: 6px; }
.login-card form { display: flex; flex-direction: column; gap: 12px; margin-top: 18px; }
.login-card input { padding: 10px 12px; border: 1px solid #d0d7de; border-radius: 6px; }
.msg { color: #dc2626; font-size: 13px; margin-top: 10px; }
</style>
