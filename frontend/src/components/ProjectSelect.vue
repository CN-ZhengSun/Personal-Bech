<template>
  <select class="project-picker" :value="current" @change="onChange" title="按项目筛选页面数据">
    <option value="">全部项目</option>
    <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
  </select>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { projectApi } from '../api'

const projects = ref([])
const current = ref('')
try {
  const v = localStorage.getItem('twb_project') || ''
  current.value = /^\d+$/.test(v) ? v : ''
} catch { current.value = '' }

async function load() {
  try {
    const { data } = await projectApi.list()
    projects.value = data || []
  } catch { projects.value = [] }
}

function onChange(e) {
  current.value = e.target.value
  try { localStorage.setItem('twb_project', e.target.value) } catch { /* noop */ }
  // 通知全局：项目已切换（localStorage 非响应式，watch 不可靠，改用自定义事件驱动页面重建）
  window.dispatchEvent(new CustomEvent('twb-project-changed', { detail: e.target.value }))
}

onMounted(load)
</script>

<style scoped>
.project-picker {
  min-width: 180px;
  padding: 7px 10px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  font-size: 13px;
  background: #fff;
  color: #1e293b;
}
</style>
