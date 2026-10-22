import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import toast from './utils/toast'
import confirmDialog from './utils/confirm'
import { initTheme } from './utils/theme'
import './index.css'

// 全局 UI 工具：window.$toast（提示）/ window.$confirm（确认框）
window.$toast = toast
window.$confirm = confirmDialog

initTheme()
createApp(App).use(router).mount('#app')
