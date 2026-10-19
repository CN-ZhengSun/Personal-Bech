<template>
  <div>
    <h1>JMeter 工具</h1>
    <div class="card">
      <div class="status" :class="launched ? 'ok' : 'idle'">
        {{ launched ? '✅ JMeter 已在本机启动（汉化版 GUI）' : (starting ? '正在启动 JMeter…' : '尚未启动') }}
      </div>
      <div class="info muted">
        本地路径：<code>{{ jmeterHome || 'D:\Test-Bench\tools\apache-jmeter-5.6.3' }}</code>
      </div>
      <div class="actions">
        <button class="btn" :disabled="starting" @click="launch">
          {{ launched ? '再次打开 JMeter' : '打开 JMeter' }}
        </button>
      </div>
      <div class="tip muted">
        点击后会在本机桌面弹出 JMeter 图形界面（已汉化，语言 zh_CN）。JMeter 已随本工作台一起迁移至
        <code>D:\Test-Bench\tools\apache-jmeter-5.6.3</code>，整机迁移时一并带走即可。
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { jmeterApi } from '../api'

const launched = ref(false)
const starting = ref(false)
const jmeterHome = ref('')

async function launch() {
  starting.value = true
  try {
    const { data } = await jmeterApi.launch()
    launched.value = true
    jmeterHome.value = data.jmeter_home
    window.$toast.success('JMeter 已在本机启动')
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || 'JMeter 启动失败')
  } finally {
    starting.value = false
  }
}
</script>

<style scoped>
.status { font-size: 15px; font-weight: 600; margin-bottom: 10px; }
.status.ok { color: #059669; }
.status.idle { color: #64748b; }
.info { margin-bottom: 14px; font-size: 13px; }
code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-family: Consolas, monospace; font-size: 12px; }
.actions { margin-bottom: 14px; }
.tip { font-size: 13px; line-height: 1.7; }
</style>
