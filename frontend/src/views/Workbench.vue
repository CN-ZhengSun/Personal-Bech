<template>
  <div>
    <h1>工作台</h1>
    <div class="stats-grid">
      <div class="stat-card clickable" @click="go('/requirements')" title="点击查看需求 PRD">
        <div class="num">{{ s.requirement_total ?? 0 }}</div><div class="lbl">需求数 →</div>
      </div>
      <div class="stat-card clickable" @click="go('/cases')" title="点击查看测试用例">
        <div class="num">{{ s.case_total ?? 0 }}</div><div class="lbl">用例数 →</div>
      </div>
      <div class="stat-card clickable" @click="go('/bugs')" title="点击查看缺陷跟踪">
        <div class="num">{{ s.bug_total ?? 0 }}</div><div class="lbl">缺陷总数 →</div>
      </div>
      <div class="stat-card clickable" @click="go('/bugs')" title="点击查看未关闭缺陷">
        <div class="num" style="color:#dc2626">{{ s.open_bugs ?? 0 }}</div><div class="lbl">未关闭缺陷 →</div>
      </div>
      <div class="stat-card clickable" @click="go('/executions')" title="点击查看测试执行">
        <div class="num">{{ s.exec_rate ?? 0 }}%</div><div class="lbl">用例执行率 →</div>
      </div>
      <div class="stat-card clickable" @click="go('/executions')" title="点击查看测试执行">
        <div class="num" style="color:#059669">{{ s.pass_rate ?? 0 }}%</div><div class="lbl">用例通过率 →</div>
      </div>
      <div class="stat-card clickable" @click="go('/requirements')" title="点击查看需求覆盖">
        <div class="num" style="color:#2563eb">{{ s.req_coverage ?? 0 }}%</div><div class="lbl">需求覆盖率 →</div>
      </div>
    </div>

    <div class="card" style="margin-top:16px">
      <h3 style="margin-bottom:10px">快捷入口</h3>
      <div class="quick">
        <RouterLink to="/requirements" class="q">📋 需求 PRD</RouterLink>
        <RouterLink to="/cases" class="q">🧪 测试用例</RouterLink>
        <RouterLink to="/executions" class="q">▶️ 测试执行</RouterLink>
        <RouterLink to="/bugs" class="q">🐛 缺陷跟踪</RouterLink>
        <RouterLink to="/report" class="q">📊 质量报表</RouterLink>
      </div>
    </div>

    <div class="card">
      <h3 style="margin-bottom:10px">执行状态分布</h3>
      <div v-for="(v, k) in (s.exec_counts || {})" :key="k" class="row">
        <span class="muted" style="width:70px">{{ statusText[k] || k }}</span>
        <div class="bar" style="flex:1"><div :style="{ width: pct(k) + '%', background: color(k) }"></div></div>
        <span style="width:40px;text-align:right;font-size:13px">{{ v }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardApi } from '../api'

const router = useRouter()
const s = ref({})
const statusText = { pass: '通过', fail: '失败', blocked: '阻塞', skipped: '跳过', untested: '未执行' }
const statusColor = { pass: '#059669', fail: '#dc2626', blocked: '#ea580c', skipped: '#64748b', untested: '#94a3b8' }
const color = (k) => statusColor[k]
const pct = (k) => {
  const total = Object.values(s.value.exec_counts || {}).reduce((a, b) => a + b, 0)
  return total ? Math.round(((s.value.exec_counts || {})[k] || 0) / total * 100) : 0
}
// 指标点击跳转到对应功能页
function go(path) { router.push(path) }

async function load() {
  const pid = localStorage.getItem('twb_project') || undefined
  try {
    const { data } = await dashboardApi.summary(pid)
    s.value = data
  } catch {}
}
onMounted(load)
watch(() => localStorage.getItem('twb_project'), load)
</script>

<style scoped>
.quick { display: flex; flex-wrap: wrap; gap: 10px; }
.q { padding: 10px 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; text-decoration: none; color: #334155; font-size: 14px; }
.q:hover { border-color: #2563eb; color: #2563eb; }
.stat-card.clickable { cursor: pointer; transition: transform .12s ease, box-shadow .12s ease; }
.stat-card.clickable:hover { transform: translateY(-2px); box-shadow: 0 4px 14px rgba(37, 99, 235, .12); border-color: #93c5fd; }
.row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
h3 { font-size: 15px; }
</style>
