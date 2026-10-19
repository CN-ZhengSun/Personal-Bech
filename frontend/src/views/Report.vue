<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin:4px 0 12px">
      <h1 style="margin:0">质量报表</h1>
      <ProjectSelect />
    </div>
    <div class="card" v-if="Object.keys(s).length">
      <h3 style="margin-bottom:12px">核心指标</h3>
      <div class="stats-grid">
        <div class="stat-card"><div class="num">{{ s.requirement_total }}</div><div class="lbl">需求数</div></div>
        <div class="stat-card"><div class="num">{{ s.case_total }}</div><div class="lbl">用例数</div></div>
        <div class="stat-card"><div class="num">{{ s.bug_total }}</div><div class="lbl">缺陷数</div></div>
        <div class="stat-card"><div class="num">{{ s.pass_rate }}%</div><div class="lbl">用例通过率</div></div>
        <div class="stat-card"><div class="num">{{ s.exec_rate }}%</div><div class="lbl">用例执行率</div></div>
        <div class="stat-card"><div class="num">{{ s.req_coverage }}%</div><div class="lbl">需求覆盖率</div></div>
      </div>
    </div>

    <!-- 缺陷严重程度分布：饼状图 + 按模块筛选 -->
    <div class="card">
      <div class="card-head">
        <h3>缺陷严重程度分布（饼状图）</h3>
        <select v-model="sevModule" @change="load">
          <option value="">全部模块</option>
          <option v-for="m in s.bug_modules || []" :key="m" :value="m">{{ m }}</option>
        </select>
      </div>
      <div v-if="hasSeverity" class="pie-wrap">
        <svg viewBox="0 0 220 220" class="pie-svg" role="img" aria-label="缺陷严重程度饼状图">
          <circle cx="110" cy="110" r="80" fill="none" stroke="#f1f5f9" stroke-width="34" />
          <path v-for="seg in pieSegments" :key="seg.k"
            :d="seg.d" fill="none" :stroke="sevColor[seg.k]" stroke-width="34" />
        </svg>
        <div class="pie-center">
          <div class="pie-total">{{ sevTotal }}</div>
          <div class="pie-total-lbl">缺陷数</div>
        </div>
      </div>
      <div v-if="hasSeverity" class="pie-legend">
        <div v-for="seg in pieSegments" :key="seg.k" class="legend-row">
          <span class="dot" :style="{ background: sevColor[seg.k] }"></span>
          <span class="legend-name">{{ sevText[seg.k] || seg.k }}</span>
          <span class="legend-val">{{ seg.v }}</span>
          <span class="legend-pct">{{ seg.pct }}%</span>
        </div>
      </div>
      <p v-else class="muted">暂无数据</p>
    </div>

    <div class="card">
      <h3 style="margin-bottom:12px">缺陷状态分布</h3>
      <div v-if="Object.keys(s.bug_status_dist || {}).length">
        <div v-for="(v, k) in s.bug_status_dist" :key="k" class="row">
          <span class="muted" style="width:80px">{{ bugStatusText[k] || k }}</span>
          <div class="bar" style="flex:1"><div :style="{ width: pctBug(k) + '%' }"></div></div>
          <span style="width:40px;text-align:right">{{ v }}</span>
        </div>
      </div>
      <p v-else class="muted">暂无数据</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { dashboardApi } from '../api'
import ProjectSelect from '../components/ProjectSelect.vue'

const s = ref({})
const sevModule = ref('')
const sevText = { critical: '致命', major: '严重', minor: '一般', trivial: '轻微' }
const sevColor = { critical: '#dc2626', major: '#ea580c', minor: '#eab308', trivial: '#94a3b8' }
const bugStatusText = { to_fix: '待修复', fixing: '修复中', fixed: '已修复', verified: '验证通过', cant_fix: '无法修复', wont_fix: '暂不修复', by_design: '设计如此', reopen: '重新打开' }

const hasSeverity = computed(() => Object.keys(s.value.severity_dist || {}).length > 0)
const sevTotal = computed(() => Object.values(s.value.severity_dist || {}).reduce((a, b) => a + b, 0))
const pieSegments = computed(() => {
  const dist = s.value.severity_dist || {}
  const total = sevTotal.value || 1
  const order = ['critical', 'major', 'minor', 'trivial']
  let acc = 0
  return order.filter((k) => dist[k]).map((k) => {
    const start = acc / total * 2 * Math.PI - Math.PI / 2
    acc += dist[k]
    const end = acc / total * 2 * Math.PI - Math.PI / 2
    const d = arcPath(110, 110, 80, start, end)
    return { k, v: dist[k], pct: Math.round(dist[k] / total * 100), d }
  })
})
// 环形饼图路径（SVG arc）
function arcPath(cx, cy, r, a0, a1) {
  const large = a1 - a0 > Math.PI ? 1 : 0
  const x0 = cx + r * Math.cos(a0), y0 = cy + r * Math.sin(a0)
  const x1 = cx + r * Math.cos(a1), y1 = cy + r * Math.sin(a1)
  return `M ${x0} ${y0} A ${r} ${r} 0 ${large} 1 ${x1} ${y1}`
}

const pctBug = (k) => Math.round(((s.value.bug_status_dist || {})[k] || 0) / (s.value.bug_total || 1) * 100)

async function load() {
  const pid = localStorage.getItem('twb_project') || undefined
  try {
    const { data } = await dashboardApi.summary(pid, sevModule.value || undefined)
    s.value = data
  } catch {}
}
onMounted(load)
watch(() => localStorage.getItem('twb_project'), load)
</script>

<style scoped>
.row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
h3 { font-size: 15px; }
.card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.card-head select { padding: 5px 8px; border: 1px solid #d0d7de; border-radius: 6px; font-size: 13px; }
.pie-wrap { position: relative; width: 220px; margin: 0 auto; }
.pie-svg { width: 220px; height: 220px; display: block; }
.pie-center { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); text-align: center; }
.pie-total { font-size: 30px; font-weight: 700; color: #1e293b; }
.pie-total-lbl { font-size: 12px; color: #64748b; }
.pie-legend { margin-top: 16px; max-width: 320px; margin-left: auto; margin-right: auto; }
.legend-row { display: flex; align-items: center; gap: 10px; padding: 4px 0; font-size: 13px; }
.dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
.legend-name { width: 56px; color: #334155; }
.legend-val { flex: 1; text-align: right; color: #475569; font-weight: 600; }
.legend-pct { width: 48px; text-align: right; color: #94a3b8; }
</style>
