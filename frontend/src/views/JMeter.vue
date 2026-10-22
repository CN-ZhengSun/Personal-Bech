<template>
  <div class="perf-page">
    <header class="perf-heading">
      <div><p class="eyebrow">测试工具 / PERFORMANCE</p><h1>性能测试</h1><p class="lead">从场景到报告，在工作台完成每一次压测。</p></div>
      <span class="engine" :class="{ ready: capability.ready }"><i></i>{{ capability.message || '检测本机引擎…' }}</span>
    </header>
    <div v-if="error" class="error" role="alert">{{ error }}</div>
    <div v-if="!projectId" class="panel empty"><h2>先选择一个项目</h2><p>在顶部选择当前项目，脚本和运行记录将按项目保存。</p></div>
    <template v-else>
      <div class="perf-layout">
        <section class="panel config">
          <div class="section-title"><div><span class="eyebrow">01 / SCENARIO</span><h2>配置测试</h2></div><a href="/api/v1/jmeter/template">下载 JMX 模板 ↗</a></div>
          <div class="mode-tabs"><button :class="{ active: mode === 'quick' }" @click="mode = 'quick'">HTTP 快速场景</button><button :class="{ active: mode === 'script' }" @click="mode = 'script'">已有 JMX 脚本</button></div>
          <form @submit.prevent="start">
            <label v-if="mode === 'quick'">目标地址 <input v-model.trim="target" type="url" required placeholder="https://example.com/api" /><small>GET 请求，固定 100ms 请求间隔。默认地址用于本机体验。</small></label>
            <template v-else>
              <label>选择脚本<select v-model="form.script_id" required><option value="">请选择 JMX 脚本</option><option v-for="s in scripts" :key="s.id" :value="s.id">{{ s.name }} · {{ date(s.created_at) }}</option></select></label>
              <div class="upload"><input ref="fileInput" type="file" accept=".jmx,.csv" multiple @change="upload" :disabled="busy" /><small>一个 JMX + 可选 CSV · 单文件 ≤ 10 MiB</small></div>
              <p v-if="chosenScript && !chosenScript.parameterized" class="warning">此脚本未适配运行参数，请参考模板使用 __P 读取三个参数后重新导入。</p>
              <details class="help"><summary>脚本参数与信任说明</summary><p>线程数：${__P(threads,5)}<br />升压时间：${__P(ramp_seconds,5)}<br />持续时间：${__P(duration_seconds,30)}</p><p>普通线程组需开启调度器。CSV 请使用同目录文件名。仅导入可信脚本：JMX 可以执行本机代码；参数检测不替代脚本审查。</p></details>
            </template>
            <label>任务名称<input v-model.trim="form.name" required maxlength="100" /></label>
            <div class="fields three"><label>并发用户<input v-model.number="form.threads" type="number" min="1" max="200" required /><small>最多 200</small></label><label>升压时间 / 秒<input v-model.number="form.ramp_seconds" type="number" min="0" max="600" required /></label><label>持续时间 / 秒<input v-model.number="form.duration_seconds" type="number" min="1" max="3600" required /></label></div>
            <div class="fields"><label>环境<input v-model.trim="form.environment" list="perf-environments" placeholder="选择或填写环境" maxlength="100" /><datalist id="perf-environments"><option v-for="e in environments" :key="e.id" :value="e.name" /></datalist></label><label>版本<input v-model.trim="form.version" list="perf-versions" placeholder="选择或填写版本" maxlength="100" /><datalist id="perf-versions"><option v-for="v in versions" :key="v.id" :value="v.name" /></datalist></label></div>
            <p class="run-meta">环境与版本用于记录归档，请在目标地址或脚本中配置实际测试服务。</p>
            <div class="threshold"><span class="eyebrow">验收阈值</span><div class="fields"><label>错误率 ≤ %<input v-model.number="form.max_error_rate" type="number" min="0" max="100" step="0.1" required /></label><label>P95 ≤ ms<input v-model.number="form.max_p95_ms" type="number" min="1" max="600000" required /></label></div></div>
            <button class="primary launch" type="submit" :disabled="busy || !!capability.active_run || !capability.ready || (mode === 'script' && !chosenScript?.parameterized)">{{ busy ? '正在提交…' : capability.active_run ? '本机已有任务运行中' : '▶ 开始测试' }}</button>
            <small class="footnote">本机单任务执行。运行时会冻结本次脚本和配置。</small>
          </form>
        </section>
        <section class="panel monitor">
          <div class="section-title"><div><span class="eyebrow">02 / MONITOR</span><h2>{{ selected ? selected.name : '运行监控' }}</h2></div><span class="badge" :class="selected?.state">{{ selected ? states[selected.state] : '等待运行' }}</span></div>
          <template v-if="selected">
            <p class="run-meta">{{ selected.script_name }} · {{ selected.threads }} 用户 · {{ selected.duration_seconds }} 秒 <span v-if="selected.environment">· {{ selected.environment }}</span><span v-if="selected.version"> · {{ selected.version }}</span></p>
            <div class="metrics"><div v-for="m in metricCards" :key="m.label"><span>{{ m.label }}</span><strong>{{ m.value }}<small>{{ m.unit }}</small></strong></div></div>
            <div class="chart-heading"><strong>响应时间趋势</strong><span>累计 P95 · ms · 最近 120 个采样点</span></div>
            <div class="chart" v-if="selected.timeline?.length > 1"><svg viewBox="0 0 600 170" role="img" aria-label="累计 P95 响应时间趋势" preserveAspectRatio="none"><line v-for="y in [25,70,115,160]" :key="y" x1="0" :y1="y" x2="600" :y2="y" stroke="currentColor" opacity=".12" /><polyline :points="chartPoints" fill="none" stroke="var(--accent-primary)" stroke-width="2.5" vector-effect="non-scaling-stroke" /></svg><div><span>{{ time(selected.timeline[0].at) }}</span><span>{{ time(selected.timeline.at(-1).at) }}</span></div></div>
            <div v-else class="chart-placeholder">{{ isActive ? '等待引擎产生采样…' : '本次运行暂无趋势数据' }}</div>
            <div class="run-message"><span :class="{ failed: selected.verdict === 'failed' }">{{ selected.message }}<template v-if="selected.verdict !== 'pending'"> · {{ selected.verdict === 'passed' ? '指标达标' : '指标未达标' }}</template></span><button v-if="isActive" class="danger" :disabled="stopping" @click="stop">{{ stopping ? '停止中…' : '停止测试' }}</button></div>
            <div class="artifacts"><button v-if="selected.report_ready" class="primary" @click="showReport = true">查看完整报告 ↗</button><a :href="fileUrl('results.jtl')">下载 JTL</a><button @click="viewLog">查看日志</button><a :href="fileUrl('console.log')">下载运行日志</a></div>
            <pre v-if="logText !== null" class="log">{{ logText || '暂无日志' }}</pre>
          </template>
          <div v-else class="monitor-empty"><span class="empty-icon">↗</span><h3>让性能表现有据可依</h3><p>配置左侧场景并开始测试，<br />这里将展示真实采样指标与响应趋势。</p><span class="empty-note">采样数 · 吞吐量 · 响应时间 · 错误率</span></div>
        </section>
      </div>
      <section class="panel history"><div class="section-title"><div><span class="eyebrow">03 / HISTORY</span><h2>运行记录 <small>{{ runs.length }} 次</small></h2></div><button @click="refresh">刷新记录</button></div><div class="table-scroll"><table><thead><tr><th>任务 / 时间</th><th>环境 / 版本</th><th>负载</th><th>采样数</th><th>吞吐量</th><th>P95</th><th>错误率</th><th>状态 / 验收</th><th></th></tr></thead><tbody><tr v-for="r in runs" :key="r.id" :class="{ selected: selected?.id === r.id }"><td><strong>{{ r.name }}</strong><small>{{ date(r.created_at) }}</small></td><td>{{ r.environment || '—' }}<small>{{ r.version || '—' }}</small></td><td>{{ r.threads }} 用户 / {{ r.duration_seconds }}s</td><td>{{ r.metrics.samples ?? '—' }}</td><td>{{ r.metrics.throughput ?? '—' }} /s</td><td>{{ r.metrics.p95_ms ?? '—' }} ms</td><td>{{ r.metrics.error_rate ?? '—' }}%</td><td><span class="badge" :class="r.state">{{ states[r.state] }}</span><small v-if="r.verdict !== 'pending'" :class="{ failed: r.verdict === 'failed' }">{{ r.verdict === 'passed' ? '指标达标' : '指标未达标' }}</small></td><td><button @click="selectRun(r)">查看</button></td></tr><tr v-if="!runs.length"><td colspan="9" class="empty-row">还没有运行记录，开始你的第一次测试。</td></tr></tbody></table></div></section>
    </template>
    <div v-if="showReport && selected" class="report-overlay"><section class="report-dialog"><header><strong>{{ selected.name }} · JMeter 报告</strong><button @click="showReport = false">关闭 ✕</button></header><iframe :src="fileUrl('report/index.html')" sandbox="allow-scripts allow-same-origin" title="JMeter HTML 报告"></iframe></section></div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { envApi, jmeterApi, versionApi } from '../api'
const projectId = Number(localStorage.getItem('twb_project')) || null
const capability = ref({}), scripts = ref([]), runs = ref([]), selected = ref(null)
const environments = ref([]), versions = ref([])
const mode = ref('quick'), target = ref('http://127.0.0.1:8000/health')
const error = ref(''), busy = ref(false), stopping = ref(false), showReport = ref(false), logText = ref(null)
const form = reactive({ name: 'HTTP 性能测试', script_id: '', threads: 5, ramp_seconds: 5, duration_seconds: 30, environment: '', version: '', max_error_rate: 1, max_p95_ms: 1000 })
const states = { starting: '准备中', running: '运行中', reporting: '生成报告', stopping: '停止中', stopped: '已停止', completed: '已完成', failed: '执行失败', interrupted: '已中断' }
const activeStates = ['starting', 'running', 'reporting', 'stopping']
const isActive = computed(() => activeStates.includes(selected.value?.state))
const chosenScript = computed(() => scripts.value.find(s => s.id === form.script_id))
const metricCards = computed(() => { const m = selected.value?.metrics || {}; return [{ label: '总采样数', value: m.samples ?? '—', unit: '' }, { label: '吞吐量', value: m.throughput ?? '—', unit: 'req/s' }, { label: '平均响应', value: m.average_ms ?? '—', unit: 'ms' }, { label: 'P95 响应', value: m.p95_ms ?? '—', unit: 'ms' }, { label: '错误率', value: m.error_rate ?? '—', unit: '%' }, { label: '错误采样', value: m.errors ?? '—', unit: '' }] })
const chartPoints = computed(() => { const points = selected.value?.timeline || []; const max = Math.max(1, ...points.map(p => p.p95_ms)); return points.map((p, i) => `${i * 600 / Math.max(1, points.length - 1)},${160 - p.p95_ms / max * 140}`).join(' ') })
const date = v => new Date(v).toLocaleString('zh-CN', { hour12: false })
const time = v => new Date(v).toLocaleTimeString('zh-CN', { hour12: false })
const fileUrl = path => `/api/v1/jmeter/runs/${selected.value.id}/files/${path}`
function fail(e) { const detail = e.response?.data?.detail; error.value = typeof detail === 'string' ? detail : '操作失败，请检查输入和服务状态' }
async function refresh() {
  try {
    const cap = await jmeterApi.capabilities(); capability.value = cap.data
    if (!projectId) return
    const [s, r] = await Promise.all([jmeterApi.scripts(projectId), jmeterApi.runs(projectId)])
    scripts.value = s.data; runs.value = r.data
    if (selected.value) selected.value = runs.value.find(r => r.id === selected.value.id) || null
    else selected.value = runs.value[0] || null
  } catch (e) { fail(e) }
}
async function upload(event) {
  if (!event.target.files.length) return
  busy.value = true; error.value = ''
  try { const data = new FormData(); data.append('project_id', projectId); for (const f of event.target.files) data.append('files', f); const result = await jmeterApi.upload(data); form.script_id = result.data.id; await refresh(); window.$toast.success('脚本已导入') } catch (e) { fail(e) } finally { busy.value = false; event.target.value = '' }
}
async function start() {
  busy.value = true; error.value = ''; logText.value = null
  try { let scriptId = form.script_id; if (mode.value === 'quick') { const result = await jmeterApi.scenario({ project_id: projectId, url: target.value }); scriptId = result.data.id } const result = await jmeterApi.start({ ...form, project_id: projectId, script_id: scriptId }); selected.value = result.data; await refresh(); window.$toast.success('测试已启动') } catch (e) { fail(e) } finally { busy.value = false }
}
async function stop() { stopping.value = true; try { await jmeterApi.stop(selected.value.id); await refresh() } catch (e) { fail(e) } finally { stopping.value = false } }
function selectRun(run) { selected.value = run; logText.value = null; showReport.value = false }
async function viewLog() { try { const { data } = await jmeterApi.log(selected.value.id); logText.value = typeof data === 'string' ? data : JSON.stringify(data) } catch (e) { fail(e) } }
let timer, disposed = false
async function poll() { await refresh(); if (!disposed) timer = setTimeout(poll, 2500) }
onMounted(async () => {
  poll()
  if (projectId) {
    try {
      const [e, v] = await Promise.all([envApi.list(), versionApi.list(projectId)])
      environments.value = e.data
      versions.value = v.data
    } catch (e) { fail(e) }
  }
})
onUnmounted(() => { disposed = true; clearTimeout(timer) })
</script>

<style scoped>
.perf-page {
  max-width:1600px;
  margin:auto;
  color:var(--text-main);
}
.perf-heading {
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:20px;
  margin-bottom:26px;
}
.eyebrow {
  font-size:10px;
  font-weight:700;
  letter-spacing:1.6px;
  color:var(--text-muted);
  margin:0 0 9px;
}
h1 {
  font-size:29px;
  letter-spacing:-.7px;
  margin:0 0 8px;
}
h2 {
  font-size:17px;
  margin:6px 0 0;
}
h3 {
  font-size:20px;
}
.lead,.run-meta {
  font-size:13px;
  color:var(--text-muted);
  line-height:1.7;
  margin:0;
}
.engine {
  font-size:12px;
  padding:10px 14px;
  border:1px solid var(--border-color);
  border-radius:20px;
  background:var(--bg-card);
  white-space:nowrap;
  display:flex;
  align-items:center;
  gap:8px;
}
.engine i {
  width:7px;
  height:7px;
  border-radius:50%;
  background:#d97706;
}
.engine.ready i {
  background:var(--accent-primary);
}
.panel {
  background:var(--bg-card);
  border:1px solid var(--border-color);
  border-radius:14px;
  padding:24px;
  box-shadow:var(--shadow-subtle);
}
.perf-layout {
  display:grid;
  grid-template-columns:minmax(320px,420px) minmax(0,1fr);
  gap:22px;
  align-items:start;
}
.section-title {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  margin-bottom:22px;
}
.section-title a {
  font-size:11px;
}
a {
  color:var(--accent-hover);
  text-decoration:none;
}
button {
  font:inherit;
  font-size:12px;
  cursor:pointer;
  border:1px solid var(--border-color);
  border-radius:7px;
  background:var(--bg-card);
  color:var(--text-main);
  padding:8px 12px;
  transition:background .15s;
}
button:hover {
  background:var(--bg-card-hover);
}
button:disabled {
  opacity:.5;
  cursor:not-allowed;
}
button:focus-visible,a:focus-visible {
  outline:2px solid var(--accent-primary);
  outline-offset:3px;
}
.primary {
  background:var(--accent-primary);
  border-color:var(--accent-primary);
  color:white;
  font-weight:600;
}
.primary:hover {
  background:var(--accent-hover);
}
.mode-tabs {
  display:flex;
  background:var(--bg-canvas);
  padding:4px;
  border-radius:9px;
  margin-bottom:20px;
  gap:3px;
}
.mode-tabs button {
  flex:1;
  border:0;
  background:transparent;
  color:var(--text-muted);
  padding:9px 5px;
}
.mode-tabs button.active {
  background:var(--bg-card);
  color:var(--accent-hover);
  box-shadow:var(--shadow-subtle);
}
label {
  display:flex;
  flex-direction:column;
  gap:8px;
  font-size:12px;
  font-weight:600;
  margin-bottom:17px;
  min-width:0;
}
input,select {
  width:100%;
  box-sizing:border-box;
  background:var(--bg-card);
  color:var(--text-main);
  border:1px solid var(--border-color);
  border-radius:7px;
  padding:10px;
  font:inherit;
  font-size:13px;
  min-width:0;
}
input:focus,select:focus {
  outline:2px solid var(--accent-ring);
  border-color:var(--accent-primary);
}
small {
  font-size:11px;
  font-weight:400;
  color:var(--text-muted);
  line-height:1.6;
}
.fields {
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:12px;
}
.fields.three {
  grid-template-columns:1fr 1fr 1fr;
}
.threshold {
  border-top:1px solid var(--border-subtle);
  padding-top:17px;
}
.threshold>.eyebrow {
  display:block;
  margin-bottom:12px;
}
.launch {
  width:100%;
  padding:12px;
}
.footnote {
  display:block;
  text-align:center;
  margin-top:10px;
}
.upload {
  padding:12px;
  border:1px dashed var(--border-color);
  border-radius:8px;
  margin-bottom:14px;
}
.upload input {
  padding:0;
  border:0;
}
.upload small {
  display:block;
  margin-top:8px;
}
.help {
  font-size:11px;
  color:var(--text-muted);
  margin-bottom:18px;
  line-height:1.8;
}
.help summary {
  cursor:pointer;
}
.warning,.error {
  padding:12px;
  border-radius:8px;
  background:#fffbeb;
  color:#92400e;
  font-size:12px;
  line-height:1.6;
}
.error {
  margin-bottom:20px;
  background:#fef2f2;
  color:#b91c1c;
}
.badge {
  display:inline-block;
  background:var(--bg-canvas);
  color:var(--text-muted);
  font-size:11px;
  padding:5px 9px;
  border-radius:20px;
  white-space:nowrap;
}
.badge.running,.badge.reporting,.badge.starting,.badge.completed {
  background:var(--accent-light);
  color:var(--accent-hover);
}
.badge.failed,.failed {
  color:#dc2626;
}
.badge.failed {
  background:#fef2f2;
}
.monitor {
  min-height:568px;
}
.run-meta {
  margin-top:-7px;
  margin-bottom:22px;
}
.metrics {
  display:grid;
  grid-template-columns:repeat(3,1fr);
  gap:22px 15px;
  padding:22px;
  background:var(--bg-card-subtle);
  border:1px solid var(--border-subtle);
  border-radius:10px;
  margin-bottom:26px;
}
.metrics span {
  display:block;
  font-size:11px;
  color:var(--text-muted);
  margin-bottom:8px;
}
.metrics strong {
  font-size:27px;
  letter-spacing:-.5px;
  font-variant-numeric:tabular-nums;
}
.metrics small {
  margin-left:5px;
  font-size:10px;
}
.chart-heading {
  display:flex;
  justify-content:space-between;
  gap:12px;
  font-size:12px;
  margin-bottom:15px;
}
.chart-heading span {
  font-size:10px;
  color:var(--text-muted);
}
.chart svg {
  width:100%;
  height:170px;
  overflow:visible;
}
.chart>div {
  display:flex;
  justify-content:space-between;
  color:var(--text-muted);
  font-size:10px;
}
.chart-placeholder {
  height:180px;
  display:grid;
  place-items:center;
  background:var(--bg-card-subtle);
  color:var(--text-muted);
  font-size:12px;
  border-radius:8px;
}
.run-message {
  display:flex;
  justify-content:space-between;
  gap:12px;
  align-items:center;
  margin:22px 0 16px;
  font-size:12px;
}
.danger {
  color:#dc2626;
  border-color:#fecaca;
}
.artifacts {
  display:flex;
  align-items:center;
  gap:15px;
  flex-wrap:wrap;
  font-size:12px;
}
.monitor-empty {
  min-height:470px;
  display:flex;
  flex-direction:column;
  justify-content:center;
  align-items:center;
  text-align:center;
  color:var(--text-muted);
}
.monitor-empty h3 {
  color:var(--text-main);
  margin-bottom:0;
}
.monitor-empty p {
  font-size:13px;
  line-height:1.9;
}
.empty-icon {
  font-size:32px;
  background:var(--accent-light);
  color:var(--accent-primary);
  width:64px;
  height:64px;
  display:grid;
  place-items:center;
  border-radius:18px;
}
.empty-note {
  font-size:10px;
  letter-spacing:1px;
  margin-top:20px;
}
.history {
  margin-top:22px;
}
.history h2 small {
  margin-left:10px;
}
.table-scroll {
  overflow:auto;
}
table {
  width:100%;
  border-collapse:collapse;
  text-align:left;
  white-space:nowrap;
  font-size:12px;
}
th {
  color:var(--text-muted);
  font-size:11px;
  font-weight:500;
  background:var(--table-head-bg);
}
td,th {
  padding:14px 12px;
  border-bottom:1px solid var(--border-subtle);
}
td strong {
  font-size:12px;
}
td small {
  display:block;
  margin-top:4px;
}
tr.selected {
  background:var(--accent-light);
}
.empty-row {
  text-align:center;
  padding:36px;
  color:var(--text-muted);
}
.empty {
  text-align:center;
  padding:70px 24px;
}
.log {
  max-height:240px;
  overflow:auto;
  background:var(--bg-canvas);
  padding:14px;
  border-radius:8px;
  white-space:pre-wrap;
  overflow-wrap:anywhere;
  font-size:11px;
  line-height:1.7;
  margin-top:18px;
}
.report-overlay {
  position:fixed;
  inset:0;
  background:#0f172a99;
  z-index:1100;
  display:flex;
  padding:24px;
}
.report-dialog {
  background:var(--bg-card);
  border-radius:12px;
  overflow:hidden;
  width:100%;
  display:flex;
  flex-direction:column;
}
.report-dialog header {
  padding:14px 20px;
  display:flex;
  justify-content:space-between;
  align-items:center;
}
.report-dialog iframe {
  flex:1;
  width:100%;
  border:0;
  background:white;
}
@media(max-width:1100px) {
  .perf-layout {
    grid-template-columns:minmax(280px,360px) minmax(0,1fr);
  }
  .panel {
    padding:18px;
  }
  .metrics {
    grid-template-columns:repeat(2,1fr);
  }
  .metrics strong {
    font-size:24px;
  }
}
@media(max-width:800px) {
  .perf-layout {
    grid-template-columns:1fr;
  }
  .perf-heading {
    align-items:flex-start;
    flex-direction:column;
  }
  .monitor {
    min-height:0;
  }
  .monitor-empty {
    min-height:260px;
  }
  .report-overlay {
    padding:8px;
  }
  .chart-heading {
    flex-direction:column;
  }
  .metrics {
    grid-template-columns:repeat(3,1fr);
  }
}
</style>
