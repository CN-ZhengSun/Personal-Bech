<template>
  <div class="td-page">
    <div class="td-heading">
      <div>
        <p class="td-eyebrow">测试工具 / 合成数据</p>
        <h1>测试数据工厂</h1>
        <p class="td-lead">批量生成有效的图片、视频、音频和普通文件。每次任务都会保存在独立目录，不覆盖已有内容。</p>
      </div>
      <span class="td-local">● 本机生成</span>
    </div>

    <div class="td-kind-grid" role="group" aria-label="选择数据类型">
      <button v-for="item in kinds" :key="item.id" type="button" class="td-kind"
        :class="{ selected: form.kind === item.id }" :aria-pressed="form.kind === item.id" @click="selectKind(item.id)">
        <span class="td-kind-icon">{{ item.icon }}</span>
        <span class="td-kind-copy"><strong>{{ item.name }}</strong><small>{{ item.description }}</small></span>
        <span class="td-kind-arrow">↗</span>
      </button>
    </div>

    <div class="td-columns">
      <section class="td-panel">
        <div class="td-panel-head">
          <div><h2>生成配置</h2><p>填写本次任务参数，先预估空间再运行。</p></div>
          <span class="td-step">01 / 配置</span>
        </div>

        <div class="td-fields">
          <label class="td-field">
            <span>生成数量 <small>个文件</small></span>
            <input v-model.number="form.count" type="number" min="1" step="1" :max="currentKind.maxCount" />
          </label>
          <label class="td-field">
            <span>{{ form.kind === 'file' ? '单文件大小' : '目标单文件大小' }} <small>MiB</small></span>
            <input v-model.number="form.size_mib" type="number" :min="currentKind.minSize" :max="currentKind.maxSize" step="0.01" />
          </label>
          <label class="td-field">
            <span>文件格式</span>
            <select v-model="form.format">
              <option v-for="option in currentKind.formats" :key="option" :value="option">{{ option.toUpperCase() }}</option>
            </select>
          </label>
          <label v-if="form.kind === 'video' || form.kind === 'audio'" class="td-field">
            <span>每个文件时长 <small>秒</small></span>
            <input v-model.number="form.duration_seconds" type="number" min="1" max="600" step="1" />
          </label>
          <div v-if="form.kind === 'image' || form.kind === 'file'" class="td-field td-field-wide">
            <label for="td-similarity">本次文件相似度 <small>{{ form.similarity_percent }}%</small></label>
            <div class="td-similarity-controls">
              <input id="td-similarity" v-model.number="form.similarity_percent" type="range" min="0" max="100" step="1" />
              <input v-model.number="form.similarity_percent" type="number" min="0" max="100" step="1" aria-label="相似度百分比" />
              <span>%</span>
            </div>
            <small>以本批第 1 个文件为参照：图片按编码前像素、普通文件按内容字节控制；0% 尽量不同，100% 完全相同。生成 1 个文件时不生效。</small>
          </div>
          <div class="td-field td-field-wide">
            <label for="td-output">保存到本机目录</label>
            <div class="td-path-row">
              <input id="td-output" v-model.trim="form.output_dir" type="text" placeholder="选择或填写已存在的本机目录" />
              <button type="button" class="td-secondary" @click="openBrowser">选择目录</button>
            </div>
            <small>任务会在该目录下新建独立文件夹。路径是工作台服务器所在电脑的路径。</small>
          </div>
        </div>

        <div class="td-hint" v-if="form.kind === 'file'">普通文件按字节数精确生成；可选二进制 BIN 或纯文本 TXT。</div>
        <div class="td-hint" v-else>媒体文件保持格式有效，大小是目标值；实际大小会在任务完成后显示。视频使用 H.264 MP4，音频使用 MP3。</div>

        <div v-if="error" class="td-error" role="alert">{{ error }}</div>
        <div class="td-actions">
          <button type="button" class="td-secondary" :disabled="planning || starting" @click="plan">{{ planning ? '计算中…' : '预估任务' }}</button>
          <button type="button" class="td-primary" :disabled="!estimate || !estimate.can_run || starting || !!activeJob" @click="start">
            {{ starting ? '启动中…' : '开始生成' }}
          </button>
        </div>
      </section>

      <aside class="td-panel td-summary">
        <div class="td-panel-head">
          <div><h2>运行预估</h2><p>执行前确认空间与依赖。</p></div>
          <span class="td-step">02 / 确认</span>
        </div>
        <div v-if="estimate" class="td-metrics">
          <div><span>预计文件</span><strong>{{ form.count.toLocaleString() }}</strong></div>
          <div><span>目标总量</span><strong>{{ formatBytes(estimate.estimated_bytes) }}</strong></div>
          <div><span>磁盘可用</span><strong>{{ formatBytes(estimate.free_bytes) }}</strong></div>
          <div><span>空间检查</span><strong :class="estimate.can_run ? 'td-ok' : 'td-bad'">{{ estimate.can_run ? '可运行' : '空间不足' }}</strong></div>
        </div>
        <div v-else class="td-empty">填写配置后点击“预估任务”，这里会显示空间需求和运行条件。</div>
        <div v-if="estimate?.needs_confirmation" class="td-confirm">
          <label for="td-confirm-text">大任务确认文字</label>
          <code>{{ estimate.confirmation_text }}</code>
          <input id="td-confirm-text" v-model="confirmationText" type="text" autocomplete="off" placeholder="请逐字输入上方内容" />
        </div>
        <p v-if="capabilityWarning" class="td-warning">{{ capabilityWarning }}</p>
        <p class="td-note">生成过程可停止；已完成文件会保留并写入清单，不会自动删除。</p>
      </aside>
    </div>

    <section v-if="activeJob" class="td-panel td-running" aria-live="polite">
      <div class="td-panel-head">
        <div><h2>{{ activeJob.state === 'stopping' ? '正在停止任务' : '正在生成' }}</h2><p>{{ kindName(activeJob.kind) }} · {{ activeJob.output_dir }}</p></div>
        <button type="button" class="td-stop" :disabled="activeJob.state === 'stopping'" @click="stop">{{ activeJob.state === 'stopping' ? '停止中…' : '停止任务' }}</button>
      </div>
      <div class="td-progress-head"><strong>{{ activeJob.completed }} / {{ activeJob.count }}</strong><span>{{ Math.round(activeJob.completed / activeJob.count * 100) }}%</span></div>
      <div class="td-progress"><div :style="{ width: `${activeJob.completed / activeJob.count * 100}%` }"></div></div>
      <p class="td-progress-meta">已生成 {{ formatBytes(activeJob.actual_bytes) }} <span v-if="activeJob.last_file">· 最近完成 {{ activeJob.last_file }}</span></p>
    </section>

    <section class="td-panel td-history">
      <div class="td-panel-head">
        <div><h2>最近任务</h2><p>保留任务状态与文件清单，便于回查实际输出。</p></div>
        <button type="button" class="td-secondary" @click="refreshJobs">刷新</button>
      </div>
      <div v-if="!jobs.length" class="td-empty">还没有生成任务。</div>
      <div v-else class="td-job-list">
        <div v-for="job in jobs" :key="job.id" class="td-job">
          <span class="td-job-icon">{{ kindIcon(job.kind) }}</span>
          <div class="td-job-main">
            <strong>{{ kindName(job.kind) }} · {{ job.completed }}/{{ job.count }} 个<span v-if="job.similarity_percent != null && ['image', 'file'].includes(job.kind)"> · 相似度 {{ job.similarity_percent }}%</span></strong>
            <small :title="job.output_dir">{{ job.output_dir }}</small>
            <small v-if="job.error" class="td-job-error">{{ job.error }}</small>
          </div>
          <div class="td-job-side">
            <span class="td-state" :class="`state-${job.state}`">{{ stateLabel(job.state) }}</span>
            <small>{{ formatBytes(job.actual_bytes) }}</small>
            <a v-if="['completed', 'stopped', 'failed'].includes(job.state)" :href="testDataApi.manifestUrl(job.id)" target="_blank" rel="noopener">查看清单</a>
          </div>
        </div>
      </div>
    </section>

    <div v-if="browserOpen" class="td-modal-mask" @click.self="browserOpen = false">
      <div class="td-modal" role="dialog" aria-modal="true" aria-label="选择保存目录">
        <div class="td-modal-head"><h2>选择本机目录</h2><button type="button" aria-label="关闭" @click="browserOpen = false">×</button></div>
        <div class="td-browser-path">{{ browserPath || '本机磁盘' }}</div>
        <div class="td-browser-actions"><button type="button" class="td-secondary" :disabled="!browserParent" @click="browse(browserParent)">上一级</button><button type="button" class="td-secondary" @click="browse('')">磁盘列表</button></div>
        <div class="td-browser-list">
          <p v-if="browserLoading" class="td-empty">读取中…</p>
          <button v-for="item in browserItems" :key="item.path" type="button" @click="browse(item.path)">📁 {{ item.name }}</button>
          <p v-if="!browserLoading && !browserItems.length" class="td-empty">该目录下没有子目录。</p>
        </div>
        <div class="td-modal-footer"><button type="button" class="td-secondary" @click="browserOpen = false">取消</button><button type="button" class="td-primary" :disabled="!browserPath" @click="chooseDirectory">使用此目录</button></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onActivated, onDeactivated, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { adbApi, testDataApi } from '../api'

const kinds = [
  { id: 'image', name: '图片', icon: '▧', description: 'JPG / PNG 合成图像', formats: ['jpg', 'png'], count: 10, size: 1, duration: 10, minSize: 0.02, maxSize: 10, maxCount: 10000 },
  { id: 'video', name: '视频', icon: '▶', description: '有效 H.264 视频', formats: ['mp4'], count: 3, size: 3, duration: 5, minSize: 0.2, maxSize: 100, maxCount: 5000 },
  { id: 'audio', name: '音频', icon: '♫', description: '合成音调 MP3', formats: ['mp3'], count: 5, size: 0.2, duration: 10, minSize: 0.05, maxSize: 20, maxCount: 10000 },
  { id: 'file', name: '普通文件', icon: '▤', description: '精确大小 BIN / TXT', formats: ['bin', 'txt'], count: 10, size: 1, duration: 10, minSize: 0.001, maxSize: 2048, maxCount: 50000 }
]
const form = reactive({ kind: 'image', count: 10, size_mib: 1, format: 'jpg', duration_seconds: 10, similarity_percent: 0, output_dir: '' })
const currentKind = computed(() => kinds.find(item => item.id === form.kind) || kinds[0])
const estimate = ref(null)
const confirmationText = ref('')
const capabilities = ref(null)
const jobs = ref([])
const activeJob = computed(() => jobs.value.find(job => ['running', 'stopping'].includes(job.state)) || null)
const error = ref('')
const planning = ref(false)
const starting = ref(false)
const browserOpen = ref(false)
const browserLoading = ref(false)
const browserPath = ref('')
const browserParent = ref('')
const browserItems = ref([])
let pollTimer = null

const capabilityWarning = computed(() => {
  if (!capabilities.value) return ''
  if (form.kind === 'image' && !capabilities.value.pillow) return '未检测到 Pillow，图片任务暂不可运行。'
  if (['video', 'audio'].includes(form.kind) && (!capabilities.value.ffmpeg || !capabilities.value.ffprobe)) return '未检测到 FFmpeg 或 ffprobe，视频和音频任务暂不可运行。'
  return ''
})

watch(form, () => { estimate.value = null; confirmationText.value = ''; error.value = '' }, { deep: true })

function selectKind(id) {
  const item = kinds.find(kind => kind.id === id)
  if (!item) return
  Object.assign(form, { kind: id, count: item.count, size_mib: item.size, format: item.formats[0], duration_seconds: item.duration, similarity_percent: 0 })
}

function payload() {
  return { kind: form.kind, count: Number(form.count), size_mib: Number(form.size_mib),
    format: form.format, duration_seconds: Number(form.duration_seconds),
    similarity_percent: Number(form.similarity_percent), output_dir: form.output_dir }
}

function apiError(exc) {
  const detail = exc.response?.data?.detail
  if (Array.isArray(detail)) return detail.map(item => item.msg).join('；')
  return detail || exc.message || '操作失败'
}

function formatBytes(value) {
  const size = Number(value) || 0
  if (size >= 1024 ** 3) return `${(size / 1024 ** 3).toFixed(2)} GiB`
  if (size >= 1024 ** 2) return `${(size / 1024 ** 2).toFixed(2)} MiB`
  return `${(size / 1024).toFixed(1)} KiB`
}

function kindName(kind) { return kinds.find(item => item.id === kind)?.name || kind }
function kindIcon(kind) { return kinds.find(item => item.id === kind)?.icon || '▤' }
function stateLabel(state) {
  return ({ running: '运行中', stopping: '停止中', completed: '已完成', stopped: '已停止', failed: '失败', interrupted: '已中断' })[state] || state
}

async function plan() {
  error.value = ''
  planning.value = true
  try { estimate.value = (await testDataApi.plan(payload())).data }
  catch (exc) { error.value = apiError(exc) }
  finally { planning.value = false }
}

async function start() {
  if (!estimate.value || activeJob.value) return
  if (estimate.value.needs_confirmation && confirmationText.value !== estimate.value.confirmation_text) {
    error.value = '请逐字输入大任务确认文字'
    return
  }
  starting.value = true
  error.value = ''
  try {
    const { data: job } = await testDataApi.start(payload(), confirmationText.value)
    jobs.value = [job, ...jobs.value.filter(item => item.id !== job.id)]
    estimate.value = null
    confirmationText.value = ''
    await refreshJobs()
  } catch (exc) { error.value = apiError(exc) }
  finally { starting.value = false }
}

async function stop() {
  if (!activeJob.value) return
  try { await testDataApi.stop(activeJob.value.id); await refreshJobs() }
  catch (exc) { error.value = apiError(exc) }
}

async function refreshJobs() {
  try { jobs.value = (await testDataApi.jobs()).data }
  catch (exc) { error.value = apiError(exc) }
}

async function browse(path) {
  browserLoading.value = true
  try {
    const { data } = await adbApi.browseDir(path)
    browserPath.value = data.path
    browserParent.value = data.parent
    browserItems.value = data.items
  } catch (exc) { error.value = apiError(exc) }
  finally { browserLoading.value = false }
}

function openBrowser() { browserOpen.value = true; browse(form.output_dir || '') }
function chooseDirectory() { form.output_dir = browserPath.value; browserOpen.value = false }

onMounted(async () => {
  try {
    capabilities.value = (await testDataApi.capabilities()).data
    form.output_dir = capabilities.value.default_output_dir
  } catch (exc) { error.value = apiError(exc) }
  await refreshJobs()
})
onActivated(() => {
  refreshJobs()
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(() => { if (activeJob.value) refreshJobs() }, 1200)
})
onDeactivated(() => { if (pollTimer) clearInterval(pollTimer); pollTimer = null })
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
.td-page { max-width: 1360px; margin: 0 auto; color: var(--text-main); }
.td-heading { display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; margin-bottom: 22px; }
.td-eyebrow { color: var(--accent-primary); font-size: 11px; font-weight: 700; letter-spacing: .12em; margin-bottom: 5px; }
.td-heading h1 { margin: 0 0 5px; font-size: 25px; letter-spacing: -.035em; color: var(--text-heading); }
.td-lead { color: var(--text-muted); font-size: 13px; line-height: 1.7; }
.td-local { white-space: nowrap; color: var(--accent-primary); border: 1px solid var(--accent-light-border); background: var(--accent-light); padding: 6px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; }
.td-kind-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 18px; }
.td-kind { display: flex; text-align: left; align-items: center; gap: 12px; min-width: 0; padding: 16px; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; color: var(--text-main); cursor: pointer; box-shadow: var(--shadow-subtle); transition: border-color .15s, transform .15s, box-shadow .15s; }
.td-kind:hover { transform: translateY(-2px); box-shadow: var(--shadow-card); border-color: var(--border-focus); }
.td-kind.selected { border-color: var(--accent-primary); box-shadow: 0 0 0 2px var(--accent-ring); }
.td-kind-icon { flex: none; display: grid; place-items: center; width: 40px; height: 40px; border-radius: 9px; color: var(--accent-primary); background: var(--accent-light); font-size: 21px; }
.td-kind-copy { display: flex; flex-direction: column; min-width: 0; gap: 3px; }
.td-kind-copy strong { font-size: 14px; color: var(--text-heading); }
.td-kind-copy small { font-size: 11px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.td-kind-arrow { margin-left: auto; color: var(--text-muted); font-size: 15px; }
.td-columns { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(290px, 1fr); gap: 18px; align-items: stretch; }
.td-panel { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; padding: 22px; box-shadow: var(--shadow-card); }
.td-panel-head { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 20px; }
.td-panel-head h2 { margin: 0 0 3px; color: var(--text-heading); font-size: 16px; }
.td-panel-head p { color: var(--text-muted); font-size: 12px; line-height: 1.6; overflow-wrap: anywhere; }
.td-step { flex: none; color: var(--text-muted); font-size: 10px; font-weight: 700; letter-spacing: .04em; }
.td-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 15px; }
.td-field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.td-field > span, .td-field > label { color: var(--text-heading); font-size: 12px; font-weight: 700; }
.td-field small { color: var(--text-muted); font-size: 11px; font-weight: 400; }
.td-field input, .td-field select { width: 100%; height: 38px; }
.td-field-wide { grid-column: 1 / -1; }
.td-path-row { display: flex; gap: 8px; }
.td-path-row input { flex: 1; min-width: 0; }
.td-similarity-controls { display: flex; align-items: center; gap: 9px; }
.td-similarity-controls input[type="range"] { flex: 1; min-width: 0; height: 28px; accent-color: var(--accent-primary); }
.td-similarity-controls input[type="number"] { width: 70px; flex: none; }
.td-similarity-controls > span { color: var(--text-muted); font-size: 12px; }
.td-primary, .td-secondary, .td-stop { min-height: 36px; padding: 7px 14px; border-radius: 7px; font: inherit; font-size: 12px; font-weight: 700; white-space: nowrap; cursor: pointer; }
.td-primary { color: var(--text-inverse); background: var(--accent-primary); border: 1px solid var(--accent-primary); }
.td-primary:hover { background: var(--accent-hover); }
.td-secondary { color: var(--text-main); background: var(--bg-card); border: 1px solid var(--border-color); }
.td-secondary:hover { border-color: var(--border-focus); background: var(--bg-card-subtle); }
.td-stop { color: #b91c1c; background: #fef2f2; border: 1px solid #fecaca; }
.td-stop:hover { background: #fee2e2; }
.td-primary:disabled, .td-secondary:disabled, .td-stop:disabled { opacity: .55; cursor: not-allowed; }
.td-hint { margin-top: 16px; padding: 10px 12px; border-radius: 8px; background: var(--bg-card-subtle); color: var(--text-muted); font-size: 12px; line-height: 1.6; }
.td-error { margin-top: 13px; padding: 10px 12px; border-radius: 8px; background: #fef2f2; color: #b91c1c; font-size: 12px; }
.td-actions { display: flex; justify-content: flex-end; gap: 9px; margin-top: 20px; }
.td-metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.td-metrics > div { display: flex; flex-direction: column; gap: 4px; background: var(--bg-card-subtle); border: 1px solid var(--border-subtle); border-radius: 9px; padding: 12px; }
.td-metrics span { font-size: 11px; color: var(--text-muted); }
.td-metrics strong { font-size: 16px; color: var(--text-heading); font-variant-numeric: tabular-nums; }
.td-metrics .td-ok { color: var(--accent-primary); }.td-metrics .td-bad { color: #b91c1c; }
.td-empty { padding: 30px 12px; text-align: center; color: var(--text-muted); font-size: 12px; line-height: 1.6; }
.td-confirm { display: flex; flex-direction: column; gap: 7px; margin-top: 16px; }
.td-confirm label { font-size: 12px; font-weight: 700; color: var(--text-heading); }
.td-confirm code { padding: 8px; background: var(--bg-card-subtle); border: 1px solid var(--border-color); border-radius: 6px; font-size: 11px; overflow-wrap: anywhere; }
.td-confirm input { width: 100%; height: 36px; }
.td-note, .td-warning { font-size: 11px; line-height: 1.65; margin-top: 15px; color: var(--text-muted); }
.td-warning { color: #b45309; }
.td-running, .td-history { margin-top: 18px; }
.td-running .td-panel-head { margin-bottom: 12px; }
.td-progress-head { display: flex; justify-content: space-between; font-size: 13px; color: var(--text-heading); margin-bottom: 7px; font-variant-numeric: tabular-nums; }
.td-progress { height: 9px; background: var(--bg-card-hover); border-radius: 99px; overflow: hidden; }
.td-progress > div { height: 100%; background: var(--accent-primary); border-radius: inherit; transition: width .3s ease; }
.td-progress-meta { font-size: 11px; color: var(--text-muted); margin-top: 8px; }
.td-history .td-panel-head { margin-bottom: 9px; }
.td-job-list { display: flex; flex-direction: column; }
.td-job { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-top: 1px solid var(--border-subtle); min-width: 0; }
.td-job-icon { flex: none; width: 34px; height: 34px; display: grid; place-items: center; border-radius: 8px; background: var(--bg-card-subtle); color: var(--accent-primary); font-size: 18px; }
.td-job-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.td-job-main strong { font-size: 12px; color: var(--text-heading); }
.td-job-main small { font-size: 11px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.td-job-main .td-job-error { color: #b91c1c; white-space: normal; }
.td-job-side { flex: none; display: flex; align-items: flex-end; flex-direction: column; gap: 3px; font-size: 11px; color: var(--text-muted); }
.td-job-side a { color: var(--accent-primary); text-decoration: none; }.td-job-side a:hover { text-decoration: underline; }
.td-state { font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 99px; background: var(--bg-card-subtle); color: var(--text-muted); }
.state-completed { background: var(--accent-light); color: var(--accent-primary); }.state-failed { background: #fef2f2; color: #b91c1c; }.state-running, .state-stopping { background: #eff6ff; color: #1d4ed8; }
.td-modal-mask { position: fixed; inset: 0; z-index: 110; display: grid; place-items: center; padding: 16px; background: rgba(5, 15, 13, .55); }
.td-modal { width: min(560px, 100%); max-height: min(650px, 90vh); display: flex; flex-direction: column; background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; box-shadow: var(--shadow-elevated); padding: 20px; }
.td-modal-head { display: flex; align-items: center; justify-content: space-between; }.td-modal-head h2 { font-size: 16px; color: var(--text-heading); }.td-modal-head button { border: 0; background: none; color: var(--text-muted); font-size: 24px; cursor: pointer; }
.td-browser-path { margin-top: 14px; min-height: 32px; padding: 7px 10px; background: var(--bg-card-subtle); border-radius: 6px; font-size: 12px; overflow-wrap: anywhere; }
.td-browser-actions { display: flex; gap: 7px; margin: 10px 0; }.td-browser-actions button { min-height: 30px; }
.td-browser-list { flex: 1; min-height: 180px; overflow: auto; border: 1px solid var(--border-color); border-radius: 8px; padding: 5px; }
.td-browser-list button { display: block; width: 100%; text-align: left; border: 0; border-radius: 5px; padding: 7px 9px; background: transparent; color: var(--text-main); font: inherit; font-size: 12px; cursor: pointer; }.td-browser-list button:hover { background: var(--bg-card-hover); }
.td-modal-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
@media (max-width: 1060px) { .td-kind-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }.td-columns { grid-template-columns: 1fr; } }
@media (max-width: 560px) { .td-heading { flex-direction: column; gap: 10px; }.td-kind-grid { gap: 8px; }.td-kind { padding: 12px; gap: 8px; }.td-kind-icon { width: 34px; height: 34px; }.td-kind-arrow { display: none; }.td-panel { padding: 16px; }.td-fields { grid-template-columns: 1fr; }.td-path-row { flex-direction: column; }.td-job { align-items: flex-start; }.td-job-icon { display: none; } }
</style>
