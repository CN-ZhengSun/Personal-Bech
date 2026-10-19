<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin:4px 0 12px">
      <h1 style="margin:0">接口测试工具</h1>
      <ProjectSelect />
    </div>

    <div class="api-layout">
      <!-- ============ 左栏：用例列表 + 历史 ============ -->
      <div class="api-side">
        <div class="side-head">
          <span class="search-ico">⌕</span>
          <input v-model="keyword" placeholder="搜索用例" @input="loadCases" />
          <select v-model="methodFilter" class="method-filter" title="按方法筛选">
            <option value="">全部</option>
            <option v-for="m in methods" :key="m" :value="m">{{ m }}</option>
          </select>
          <button class="btn-new" title="新建用例" @click="newCase">＋</button>
        </div>
        <div class="side-tools">
          <button class="link-btn" @click="openEnvManager">
            <span class="env-ico">◈</span> 环境管理
          </button>
          <span class="muted count">{{ filteredCases.length }} 条</span>
        </div>
        <div class="case-list">
          <div v-for="c in filteredCases" :key="c.id" class="case-item" :class="{ active: c.id === currentId }" @click="selectCase(c)">
            <span class="m-badge" :class="'b-' + c.method.toLowerCase()">{{ c.method }}</span>
            <div class="case-meta">
              <div class="case-name">{{ c.name }}</div>
              <div class="case-url">{{ c.url || '—' }}</div>
            </div>
            <button class="case-del" title="删除" @click.stop="removeCase(c)">✕</button>
          </div>
          <div v-if="!filteredCases.length" class="muted empty">
            {{ methodFilter || keyword ? '无匹配用例' : '暂无接口用例，点「＋」新建' }}
          </div>
        </div>
        <div class="history">
          <div class="history-head">
            <span class="history-title">请求历史</span>
            <button v-if="history.length" class="history-clear" @click="clearHistory">清空</button>
          </div>
          <div v-for="(h, i) in history" :key="i" class="history-item" @click="useHistory(h)">
            <span class="m-badge mini" :class="'b-' + h.method.toLowerCase()">{{ h.method }}</span>
            <div class="history-meta">
              <div class="history-url">{{ h.url }}</div>
              <div class="history-time">{{ h.time }}</div>
            </div>
            <button class="case-del" title="删除" @click.stop="delHistory(i)">✕</button>
          </div>
          <div v-if="!history.length" class="muted empty">暂无历史记录</div>
        </div>
      </div>

      <!-- ============ 右栏：调试器 ============ -->
      <div class="api-main">
        <div class="editor-wrap" :class="splitMode === 'row' ? 'split-row' : 'split-col'">
          <!-- 请求侧 -->
          <div class="req-side">
            <div class="req-bar">
              <div class="method-wrap">
                <select v-model="form.method" class="method-select" :class="'m-' + form.method.toLowerCase()">
                  <option v-for="m in methods" :key="m" :value="m">{{ m }}</option>
                </select>
              </div>
              <input v-model="form.url" placeholder="输入请求 URL，可用 {{变量}} 引用环境变量" class="url-input" @keyup.enter="send" />
              <select v-model="currentEnvId" class="env-select" title="选择环境（变量与 baseUrl）">
                <option :value="null">不选环境</option>
                <option v-for="e in envs" :key="e.id" :value="e.id">{{ e.name }}</option>
              </select>
              <button class="btn-send" @click="send" :disabled="sending">
                <span class="send-ico">▶</span>{{ sending ? '发送中…' : '发送' }}
              </button>
              <button class="btn-save" @click="saveCase" :disabled="saving">{{ saving ? '保存中…' : '保存' }}</button>
            </div>

            <div class="req-tabs">
              <button v-for="t in tabs" :key="t.id" class="tab-btn" :class="{ active: tab === t.id }" @click="tab = t.id">
                {{ t.name }}
                <span v-if="t.id === 'params' && activeCount(form.query)" class="badge">{{ activeCount(form.query) }}</span>
                <span v-if="t.id === 'headers' && activeCount(form.headers)" class="badge">{{ activeCount(form.headers) }}</span>
                <span v-if="t.id === 'body' && form.body_type !== 'none'" class="badge dot"></span>
              </button>
              <button class="tab-btn" :class="{ active: tab === 'assert' }" @click="tab = 'assert'">断言
                <span v-if="form.assertions.length" class="badge">{{ form.assertions.length }}</span>
              </button>
            </div>

            <!-- Params / Headers 表格 -->
            <div v-if="tab === 'params'" class="kv-editor">
              <div class="kv-head">
                <span class="col-w36"></span><span class="col-key">Key</span><span class="col-val">Value</span><span class="col-w40"></span>
              </div>
              <div v-for="(r, i) in form.query" :key="i" class="kv-row">
                <input type="checkbox" v-model="r.enabled" class="kv-check" />
                <input v-model="r.key" placeholder="参数名" class="kv-input" />
                <input v-model="r.value" placeholder="参数值" class="kv-input" />
                <button class="row-del" @click="form.query.splice(i, 1)">✕</button>
              </div>
              <button class="add-row" @click="form.query.push({ key: '', value: '', enabled: true })">＋ 添加参数</button>
            </div>

            <div v-if="tab === 'headers'" class="kv-editor">
              <div class="kv-head">
                <span class="col-w36"></span><span class="col-key">Key</span><span class="col-val">Value</span><span class="col-w40"></span>
              </div>
              <div v-for="(r, i) in form.headers" :key="i" class="kv-row">
                <input type="checkbox" v-model="r.enabled" class="kv-check" />
                <input v-model="r.key" placeholder="Header 名" class="kv-input" />
                <input v-model="r.value" placeholder="Header 值" class="kv-input" />
                <button class="row-del" @click="form.headers.splice(i, 1)">✕</button>
              </div>
              <button class="add-row" @click="form.headers.push({ key: '', value: '', enabled: true })">＋ 添加 Header</button>
            </div>

            <!-- Body -->
            <div v-if="tab === 'body'" class="body-editor">
              <div class="body-type-row">
                <select v-model="form.body_type" class="body-type">
                  <option value="none">无 Body</option>
                  <option value="json">JSON</option>
                  <option value="form">表单 (x-www-form-urlencoded)</option>
                  <option value="raw">原始文本</option>
                </select>
              </div>
              <textarea v-if="form.body_type !== 'none'" v-model="form.body" class="body-input" :placeholder="form.body_type === 'json' ? '{\n  &quot;key&quot;: &quot;value&quot;\n}' : '输入请求体内容'" spellcheck="false"></textarea>
            </div>

            <!-- 断言 -->
            <div v-if="tab === 'assert'" class="kv-editor">
              <div class="kv-head">
                <span class="col-100">类型</span><span class="col-key">字段 / 表达式</span><span class="col-110">操作符</span><span class="col-val">期望值</span><span class="col-w40"></span>
              </div>
              <div v-for="(a, i) in form.assertions" :key="i" class="kv-row">
                <select v-model="a.type" class="kv-sel">
                  <option value="status">状态码</option>
                  <option value="json">JSON 字段</option>
                  <option value="text">文本包含</option>
                </select>
                <input v-model="a.field" :placeholder="a.type === 'status' ? '—' : a.type === 'json' ? 'data.code / data.list[0].id' : '响应文本片段'" class="kv-input" :disabled="a.type === 'status'" />
                <select v-model="a.operator" class="kv-sel">
                  <option value="==">==</option>
                  <option value="!=">!=</option>
                  <option value="contains">包含</option>
                  <option value="not contains">不包含</option>
                  <option value="regex">正则</option>
                </select>
                <input v-model="a.value" placeholder="期望值" class="kv-input" />
                <button class="row-del" @click="form.assertions.splice(i, 1)">✕</button>
              </div>
              <button class="add-row" @click="form.assertions.push({ type: 'status', field: '', operator: '==', value: '200' })">＋ 添加断言</button>
            </div>
          </div>

          <!-- 响应侧 -->
          <div class="resp-side">
            <div class="resp-toolbar">
              <span class="resp-label">响应</span>
              <div class="split-switch" title="切换分屏方向">
                <button class="split-btn" :class="{ active: splitMode === 'col' }" @click="splitMode = 'col'">⇕</button>
                <button class="split-btn" :class="{ active: splitMode === 'row' }" @click="splitMode = 'row'">⇔</button>
              </div>
            </div>

            <div class="resp-wrap" v-if="resp">
              <div class="resp-head">
                <span class="status-badge" :class="statusClass(resp)">
                  {{ resp.error ? '请求失败' : resp.status_code }}
                </span>
                <span v-if="!resp.error" class="status-text">{{ statusText(resp.status_code) }}</span>
                <span class="meta"><span class="meta-ico">⏱</span>{{ resp.elapsed_ms }} ms</span>
                <span class="meta"><span class="meta-ico">📦</span>{{ fmtSize(resp.size_bytes) }}</span>
                <span class="meta" v-if="resp.error && !resp.ok"><span class="meta-ico">⚠</span>{{ resp.error }}</span>
                <span class="pass-tag" v-if="resp.all_passed === true">✓ 断言全部通过</span>
                <span class="fail-tag" v-else-if="resp.all_passed === false">✗ {{ (resp.assertions || []).filter(a => !a.ok).length }} 条断言失败</span>
              </div>
              <div v-if="resp.assertions && resp.assertions.length" class="assert-list">
                <div v-for="(a, i) in resp.assertions" :key="i" class="assert-item" :class="a.ok ? 'ok' : 'bad'">
                  <span class="a-ico">{{ a.ok ? '✓' : '✗' }}</span>
                  <span class="a-desc">{{ a.desc }}</span>
                  <span class="a-actual">实际: {{ a.actual }}</span>
                </div>
              </div>
              <div class="resp-body-head">
                <button class="tab-btn" :class="{ active: respTab === 'body' }" @click="respTab = 'body'">响应体</button>
                <button class="tab-btn" :class="{ active: respTab === 'headers' }" @click="respTab = 'headers'">响应头</button>
                <button class="tab-btn" :class="{ active: respTab === 'curl' }" @click="respTab = 'curl'">实际请求</button>
                <span class="body-len muted" v-if="respTab === 'body' && resp.response_body">{{ resp.response_body.length }} 字符</span>
              </div>
              <div v-if="respTab === 'body'" class="resp-body" :class="{ err: !!resp.error }">
                <pre v-if="!resp.error" class="json-pre" v-html="highlight(resp)"></pre>
                <pre v-else class="err-pre">{{ resp.error }}</pre>
              </div>
              <pre v-else-if="respTab === 'headers'" class="resp-body plain-pre">{{ prettyHeaders(resp.response_headers) }}</pre>
              <pre v-else class="resp-body curl-pre">{{ genCurl() }}</pre>
            </div>

            <!-- 空态 -->
            <div v-if="!resp" class="resp-empty">
              <div class="empty-ico">◈</div>
              <div class="empty-title">开始调试接口</div>
              <div class="empty-sub">填写 URL 后点击「发送」或按 Ctrl + Enter，响应将在这里展示</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ============ 环境管理弹窗 ============ -->
    <div v-if="envManager" class="modal-mask" @click.self="envManager = false">
      <div class="modal">
        <div class="modal-head">
          <h3 style="margin:0">环境管理</h3>
          <button class="modal-close" @click="envManager = false">✕</button>
        </div>
        <div class="form-row">
          <input v-model="envForm.name" placeholder="环境名，如：测试环境" class="modal-input" />
          <input v-model="envForm.base_url" placeholder="基础 URL，如：https://api.example.com" class="modal-input" />
          <button class="btn-primary-sm" @click="saveEnv" :disabled="!envForm.name">保存环境</button>
        </div>
        <template v-if="envForm.id">
          <div class="vars-label">变量表（可用 {{变量名}} 引用）</div>
          <div class="kv-editor">
            <div v-for="(v, i) in envForm.variablesArr" :key="i" class="kv-row">
              <input v-model="v.key" placeholder="变量名" class="kv-input" />
              <input v-model="v.value" placeholder="变量值" class="kv-input" />
              <button class="row-del" @click="envForm.variablesArr.splice(i, 1)">✕</button>
            </div>
            <div class="vars-actions">
              <button class="add-row" @click="envForm.variablesArr.push({ key: '', value: '' })">＋ 添加变量</button>
              <button class="btn-primary-sm" @click="saveEnvVars">保存变量</button>
            </div>
          </div>
        </template>
        <div class="env-list">
          <div v-for="e in envs" :key="e.id" class="env-item">
            <span class="env-name">{{ e.name }}</span>
            <span class="muted env-sub">{{ e.base_url || '无 baseUrl' }} · {{ Object.keys(e.variables || {}).length }} 个变量</span>
            <button class="env-op" @click="editEnv(e)">编辑</button>
            <button class="env-op danger" @click="removeEnv(e)">删除</button>
          </div>
          <div v-if="!envs.length" class="muted" style="padding:10px 0;text-align:center">暂无环境</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import ProjectSelect from '../components/ProjectSelect.vue'
import { apiTestApi } from '../api'

const methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
const tabs = [
  { id: 'params', name: 'Params' },
  { id: 'headers', name: 'Headers' },
  { id: 'body', name: 'Body' },
]
const HIST_KEY = 'twb_apitest_history'
const emptyForm = () => ({
  id: null, name: '未命名用例', method: 'GET', url: '',
  headers: [], query: [], body_type: 'none', body: '', assertions: [], description: '',
})

const keyword = ref('')
const methodFilter = ref('')
const cases = ref([])
const currentId = ref(null)
const form = ref(emptyForm())
const tab = ref('params')
const sending = ref(false)
const saving = ref(false)
const resp = ref(null)
const respTab = ref('body')
const splitMode = ref('col')

const envs = ref([])
const currentEnvId = ref(null)
const envManager = ref(false)
const envForm = ref({ id: null, name: '', base_url: '', variablesArr: [] })

const history = ref(loadHistory())

const projectId = () => localStorage.getItem('twb_project') || undefined
watch(() => localStorage.getItem('twb_project'), () => { loadCases(); loadEnvs() })

const filteredCases = computed(() => {
  if (!methodFilter.value) return cases.value
  return cases.value.filter(c => c.method === methodFilter.value)
})

function activeCount(arr) { return (arr || []).filter(r => r.enabled).length }

function loadHistory() {
  try {
    const raw = JSON.parse(localStorage.getItem(HIST_KEY) || '[]')
    return Array.isArray(raw) ? raw.slice(0, 20) : []
  } catch { return [] }
}
function persistHistory() {
  try { localStorage.setItem(HIST_KEY, JSON.stringify(history.value.slice(0, 20))) } catch { /* ignore */ }
}
function addHistory() {
  const rec = {
    method: form.value.method,
    url: form.value.url,
    envId: currentEnvId.value,
    bodyType: form.value.body_type,
    body: form.value.body,
    headers: form.value.headers.map(h => ({ ...h })),
    query: form.value.query.map(q => ({ ...q })),
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
  }
  history.value = [rec, ...history.value.filter(h => !(h.method === rec.method && h.url === rec.url))].slice(0, 20)
  persistHistory()
}
function useHistory(h) {
  currentId.value = null
  form.value = { ...emptyForm(), method: h.method, url: h.url, body_type: h.bodyType || 'none', body: h.body || '', headers: [...(h.headers || [])], query: [...(h.query || [])] }
  if (h.envId && envs.value.some(e => e.id === h.envId)) currentEnvId.value = h.envId
  else currentEnvId.value = null
  resp.value = null
}
function delHistory(i) {
  history.value.splice(i, 1)
  persistHistory()
}
function clearHistory() {
  history.value = []
  persistHistory()
}

async function loadCases() {
  try {
    const { data } = await apiTestApi.cases(projectId(), keyword.value || undefined)
    cases.value = data || []
    if (currentId.value && !cases.value.some((c) => c.id === currentId.value)) {
      currentId.value = null
      form.value = emptyForm()
    }
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '用例加载失败')
  }
}

function selectCase(c) {
  currentId.value = c.id
  form.value = { ...c, headers: [...(c.headers || [])], query: [...(c.query || [])], assertions: [...(c.assertions || [])] }
  resp.value = null
}

function newCase() {
  currentId.value = null
  form.value = emptyForm()
  resp.value = null
  tab.value = 'params'
}

function collectPayload() {
  return {
    project_id: Number(projectId() || 0),
    name: form.value.name,
    method: form.value.method,
    url: form.value.url,
    headers: form.value.headers,
    query: form.value.query,
    body_type: form.value.body_type,
    body: form.value.body,
    assertions: form.value.assertions,
    description: form.value.description,
    enabled: true,
  }
}

async function saveCase() {
  if (!projectId()) return window.$toast.warning('请先选择项目')
  if (!form.value.url) return window.$toast.warning('请填写 URL')
  saving.value = true
  try {
    if (form.value.id) {
      await apiTestApi.updateCase(form.value.id, collectPayload())
    } else {
      const { data } = await apiTestApi.createCase(collectPayload())
      form.value.id = data.id
      currentId.value = data.id
    }
    window.$toast.success('用例已保存')
    loadCases()
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '保存失败')
  } finally { saving.value = false }
}

async function removeCase(c) {
  if (!(await window.$confirm(`确认删除用例「${c.name}」？`))) return
  try {
    await apiTestApi.deleteCase(c.id)
    window.$toast.success('已删除')
    if (currentId.value === c.id) newCase()
    loadCases()
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '删除失败')
  }
}

function currentEnv() {
  return envs.value.find((e) => e.id === currentEnvId.value) || null
}

async function send() {
  if (!form.value.url) return window.$toast.warning('请填写 URL')
  sending.value = true
  resp.value = null
  try {
    const env = currentEnv()
    const { data } = await apiTestApi.run({
      case: collectPayload(),
      env: { base_url: env?.base_url || '', variables: env?.variables || {} },
    })
    resp.value = data
    respTab.value = 'body'
    addHistory()
  } catch (e) {
    resp.value = { ok: false, error: e.response?.data?.detail || '请求失败', elapsed_ms: 0, size_bytes: 0, response_headers: {}, assertions: [] }
  } finally { sending.value = false }
}

function genCurl() {
  const lines = [`curl --request ${form.value.method} '${form.value.url}'`]
  const hs = (form.value.headers || []).filter(h => h.enabled && h.key)
  hs.forEach(h => lines.push(`  --header '${h.key}: ${h.value}'`))
  const qs = (form.value.query || []).filter(q => q.enabled && q.key)
  if (qs.length) {
    const qstr = qs.map(q => `${encodeURIComponent(q.key)}=${encodeURIComponent(q.value)}`).join('&')
    lines.push(`  --data-urlencode '${qstr}'`)
  }
  if (form.value.body_type === 'json' && form.value.body) {
    lines.push(`  --data '${form.value.body.replace(/'/g, "'\\''")}'`)
  } else if (form.value.body_type === 'form') {
    const f = (form.value.body || '').split('\n').map(s => s.trim()).filter(Boolean)
    f.forEach(kv => lines.push(`  --data-urlencode '${kv}'`))
  } else if (form.value.body_type === 'raw' && form.value.body) {
    lines.push(`  --data '${form.value.body.replace(/'/g, "'\\''")}'`)
  }
  return lines.join(' \\\n')
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

function highlight(r) {
  if (r.response_json !== undefined && r.response_json !== null) {
    return hl(JSON.stringify(r.response_json, null, 2))
  }
  return esc(r.response_body || '')
}

function hl(json) {
  return esc(json).replace(/(&quot;|")(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*(&quot;|")(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?/g, (m) => {
    let cls = 'jv-num'
    if (/^&quot;|^"/.test(m)) { cls = /:\s*$/.test(m) ? 'jv-key' : 'jv-str' }
    else if (/true|false/.test(m)) cls = 'jv-bool'
    else if (/null/.test(m)) cls = 'jv-null'
    return `<span class="${cls}">${m}</span>`
  })
}

function statusClass(r) {
  if (r.error) return 'bad'
  const c = r.status_code
  if (c >= 200 && c < 300) return 'ok'
  if (c >= 300 && c < 400) return 'info'
  if (c >= 400 && c < 500) return 'warn'
  return 'bad'
}

function statusText(c) {
  const m = { 200: 'OK', 201: 'Created', 204: 'No Content', 301: 'Moved', 302: 'Found', 304: 'Not Modified', 400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden', 404: 'Not Found', 405: 'Method Not Allowed', 409: 'Conflict', 422: 'Unprocessable', 429: 'Too Many', 500: 'Server Error', 502: 'Bad Gateway', 503: 'Unavailable' }
  return m[c] || ''
}

function prettyHeaders(h) {
  return Object.entries(h || {}).map(([k, v]) => `${k}: ${v}`).join('\n')
}

function fmtSize(n) {
  if (!n) return '0 B'
  if (n < 1024) return n + ' B'
  if (n < 1048576) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1048576).toFixed(1) + ' MB'
}

// ---------- 环境 ----------
async function loadEnvs() {
  try {
    const { data } = await apiTestApi.envs(projectId())
    envs.value = data || []
    if (currentEnvId.value && !envs.value.some((e) => e.id === currentEnvId.value)) currentEnvId.value = null
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '环境加载失败')
  }
}

function openEnvManager() {
  envManager.value = true
  envForm.value = { id: null, name: '', base_url: '', variablesArr: [] }
}

async function saveEnv() {
  if (!projectId()) return window.$toast.warning('请先选择项目')
  try {
    if (envForm.value.id) {
      await apiTestApi.updateEnv(envForm.value.id, { name: envForm.value.name, base_url: envForm.value.base_url })
    } else {
      await apiTestApi.createEnv({ project_id: Number(projectId()), name: envForm.value.name, base_url: envForm.value.base_url, variables: {} })
    }
    window.$toast.success('环境已保存')
    loadEnvs()
    envForm.value = { id: null, name: '', base_url: '', variablesArr: [] }
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '保存失败')
  }
}

function editEnv(e) {
  envForm.value = {
    id: e.id, name: e.name, base_url: e.base_url,
    variablesArr: Object.entries(e.variables || {}).map(([k, v]) => ({ key: k, value: v })),
  }
}

async function saveEnvVars() {
  const vars = {}
  for (const v of envForm.value.variablesArr) {
    if (v.key) vars[v.key] = v.value
  }
  try {
    await apiTestApi.updateEnv(envForm.value.id, { variables: vars })
    window.$toast.success('变量已保存')
    loadEnvs()
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '保存失败')
  }
}

async function removeEnv(e) {
  if (!(await window.$confirm(`确认删除环境「${e.name}」？`))) return
  try {
    await apiTestApi.deleteEnv(e.id)
    if (currentEnvId.value === e.id) currentEnvId.value = null
    loadEnvs()
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '删除失败')
  }
}

// Ctrl+Enter 快捷发送
function onKey(e) {
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault()
    send()
  }
}

onMounted(() => {
  loadCases(); loadEnvs()
  window.addEventListener('keydown', onKey)
})
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.api-layout { display: flex; gap: 14px; align-items: flex-start; }

/* ===== 左栏 ===== */
.api-side { width: 320px; flex: none; border: 1px solid #e6e8eb; border-radius: 10px; background: #fff; overflow: hidden; box-shadow: 0 1px 3px rgba(16,24,40,.04); display: flex; flex-direction: column; max-height: calc(100vh - 140px); }
.side-head { display: flex; align-items: center; gap: 6px; padding: 10px 12px; border-bottom: 1px solid #eef1f4; }
.search-ico { color: #9aa3af; font-size: 15px; }
.side-head input { flex: 1; padding: 6px 8px; border: 1px solid #e3e6ea; border-radius: 7px; font-size: 13px; outline: none; transition: border-color .15s; min-width: 0; }
.side-head input:focus { border-color: #5b4ffc; }
.method-filter { width: 62px; padding: 6px 4px; border: 1px solid #e3e6ea; border-radius: 7px; font-size: 12px; color: #475467; outline: none; flex: none; }
.btn-new { width: 28px; height: 28px; border: none; border-radius: 7px; background: #5b4ffc; color: #fff; font-size: 16px; line-height: 1; cursor: pointer; flex: none; }
.btn-new:hover { background: #4a3ff0; }
.side-tools { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; border-bottom: 1px solid #eef1f4; }
.link-btn { display: flex; align-items: center; gap: 5px; border: none; background: none; color: #5b4ffc; font-size: 13px; cursor: pointer; padding: 0; }
.link-btn:hover { color: #4a3ff0; }
.env-ico { font-size: 12px; }
.count { font-size: 12px; }
.case-list { flex: 1; overflow-y: auto; min-height: 120px; }
.case-item { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-bottom: 1px solid #f5f6f8; cursor: pointer; transition: background .1s; }
.case-item:hover { background: #f7f8fa; }
.case-item.active { background: #f2f0ff; }
.m-badge { flex: none; width: 46px; text-align: center; padding: 2px 0; border-radius: 4px; color: #fff; font-size: 11px; font-weight: 700; letter-spacing: .5px; }
.m-badge.mini { width: 36px; font-size: 10px; }
.b-get { background: #10b981; } .b-post { background: #3b82f6; } .b-put { background: #f59e0b; }
.b-patch { background: #8b5cf6; } .b-delete { background: #ef4444; } .b-head, .b-options { background: #64748b; }
.case-meta { flex: 1; min-width: 0; }
.case-name { font-size: 13px; font-weight: 600; color: #1e293b; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.case-url { font-size: 11px; color: #98a2b3; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.case-del { display: none; border: none; background: none; color: #c0c6cf; font-size: 12px; cursor: pointer; flex: none; }
.case-item:hover .case-del, .history-item:hover .case-del { display: block; }
.case-del:hover { color: #ef4444; }
.empty { padding: 16px 10px; text-align: center; font-size: 12px; }
.history { border-top: 1px solid #eef1f4; max-height: 34%; overflow-y: auto; flex: none; }
.history-head { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px 4px; }
.history-title { font-size: 12px; font-weight: 700; color: #667085; }
.history-clear { border: none; background: none; color: #98a2b3; font-size: 11px; cursor: pointer; }
.history-clear:hover { color: #ef4444; }
.history-item { display: flex; align-items: center; gap: 8px; padding: 6px 10px; cursor: pointer; border-bottom: 1px solid #f7f8fa; }
.history-item:hover { background: #f7f8fa; }
.history-meta { flex: 1; min-width: 0; }
.history-url { font-size: 12px; color: #344054; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.history-time { font-size: 10px; color: #b0b7c3; }

/* ===== 右栏 ===== */
.api-main { flex: 1; min-width: 0; }

.editor-wrap { display: flex; gap: 12px; }
.editor-wrap.split-col { flex-direction: column; }
.editor-wrap.split-row { flex-direction: row; }
.split-row .req-side { flex: 1; width: 50%; }
.split-row .resp-side { flex: 1; width: 50%; }

.req-side { min-width: 0; }

/* 请求栏 */
.req-bar { display: flex; gap: 8px; margin-bottom: 4px; align-items: stretch; flex-wrap: wrap; }
.method-wrap { position: relative; }
.method-select { width: 96px; padding: 9px 8px; border-radius: 8px; border: none; font-weight: 700; font-size: 13px; color: #fff; cursor: pointer; outline: none; appearance: none; text-align: center; }
.method-select option { color: #1e293b; background: #fff; font-weight: 400; }
.m-get { background: #10b981; } .m-post { background: #3b82f6; } .m-put { background: #f59e0b; }
.m-patch { background: #8b5cf6; } .m-delete { background: #ef4444; } .m-head, .m-options { background: #64748b; }
.url-input { flex: 1 1 220px; padding: 9px 12px; border: 1px solid #e3e6ea; border-radius: 8px; font-size: 13px; font-family: Consolas, 'Courier New', monospace; background: #f8f9fb; outline: none; transition: border-color .15s, background .15s; min-width: 220px; }
.url-input:focus { border-color: #5b4ffc; background: #fff; }
.env-select { width: 128px; padding: 0 8px; border: 1px solid #e3e6ea; border-radius: 8px; font-size: 13px; background: #fff; color: #475467; outline: none; cursor: pointer; }
.btn-send { display: flex; align-items: center; gap: 6px; background: linear-gradient(135deg, #5b4ffc, #6c5ce7); color: #fff; border: none; padding: 0 20px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; white-space: nowrap; transition: opacity .15s, transform .1s; }
.btn-send:hover { opacity: .92; transform: translateY(-1px); }
.btn-send:disabled { opacity: .6; cursor: not-allowed; transform: none; }
.send-ico { font-size: 10px; }
.btn-save { padding: 0 16px; border: 1px solid #e3e6ea; border-radius: 8px; background: #fff; color: #475467; font-size: 13px; cursor: pointer; white-space: nowrap; transition: border-color .15s, color .15s; }
.btn-save:hover { border-color: #5b4ffc; color: #5b4ffc; }
.btn-save:disabled { opacity: .6; cursor: not-allowed; }

/* Tabs */
.req-tabs, .resp-body-head { display: flex; align-items: center; gap: 2px; border-bottom: 1px solid #e8eaee; margin: 8px 0 10px; }
.tab-btn { position: relative; padding: 8px 12px; border: none; background: none; font-size: 13px; color: #667085; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; transition: color .15s; }
.tab-btn:hover { color: #344054; }
.tab-btn.active { color: #5b4ffc; border-bottom-color: #5b4ffc; font-weight: 600; }
.badge { display: inline-flex; align-items: center; justify-content: center; min-width: 16px; height: 16px; padding: 0 4px; border-radius: 8px; background: #5b4ffc; color: #fff; font-size: 10px; font-weight: 700; margin-left: 4px; vertical-align: middle; }
.badge.dot { width: 6px; min-width: 6px; height: 6px; padding: 0; border-radius: 50%; }

/* KV 表格 */
.kv-editor { margin-bottom: 10px; }
.kv-head { display: flex; align-items: center; gap: 8px; padding: 0 4px 6px; font-size: 12px; color: #98a2b3; font-weight: 600; }
.col-w36 { width: 36px; flex: none; } .col-w40 { width: 40px; flex: none; }
.col-100 { width: 100px; flex: none; } .col-110 { width: 110px; flex: none; }
.col-key { flex: 1; } .col-val { flex: 1; }
.kv-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.kv-check { width: 15px; height: 15px; accent-color: #5b4ffc; flex: none; }
.kv-input { flex: 1; padding: 7px 10px; border: 1px solid #e3e6ea; border-radius: 7px; font-size: 13px; outline: none; transition: border-color .15s; min-width: 0; }
.kv-input:focus { border-color: #5b4ffc; }
.kv-input:disabled { background: #f5f6f8; color: #98a2b3; }
.kv-sel { width: 108px; padding: 7px 6px; border: 1px solid #e3e6ea; border-radius: 7px; font-size: 13px; outline: none; flex: none; }
.row-del { width: 26px; height: 26px; border: none; border-radius: 6px; background: none; color: #c0c6cf; cursor: pointer; font-size: 11px; flex: none; }
.row-del:hover { background: #fef2f2; color: #ef4444; }
.add-row { margin-top: 2px; border: none; background: none; color: #5b4ffc; font-size: 13px; cursor: pointer; padding: 4px 6px; border-radius: 6px; }
.add-row:hover { background: #f2f0ff; }

/* Body */
.body-editor { margin-bottom: 10px; }
.body-type-row { margin-bottom: 8px; }
.body-type { padding: 7px 10px; border: 1px solid #e3e6ea; border-radius: 7px; font-size: 13px; outline: none; }
.body-input { width: 100%; min-height: 200px; padding: 12px; border: 1px solid #e3e6ea; border-radius: 8px; font-family: Consolas, 'Courier New', monospace; font-size: 13px; line-height: 1.6; box-sizing: border-box; outline: none; resize: vertical; }
.body-input:focus { border-color: #5b4ffc; }

/* 响应侧 */
.resp-side { min-width: 0; display: flex; flex-direction: column; }
.resp-toolbar { display: flex; justify-content: space-between; align-items: center; margin: 8px 0 4px; }
.resp-label { font-size: 13px; font-weight: 700; color: #344054; }
.split-switch { display: flex; gap: 2px; border: 1px solid #e3e6ea; border-radius: 7px; overflow: hidden; }
.split-btn { width: 30px; height: 26px; border: none; background: #fff; color: #98a2b3; cursor: pointer; font-size: 13px; }
.split-btn:hover { color: #5b4ffc; }
.split-btn.active { background: #5b4ffc; color: #fff; }
.resp-wrap { border: 1px solid #e8eaee; border-radius: 10px; overflow: hidden; background: #fff; display: flex; flex-direction: column; min-height: 0; }
.split-row .resp-wrap { flex: 1; }
.resp-head { display: flex; align-items: center; gap: 14px; padding: 10px 14px; background: #f8f9fb; border-bottom: 1px solid #eef1f4; flex-wrap: wrap; }
.status-badge { font-weight: 700; font-size: 14px; padding: 3px 12px; border-radius: 6px; color: #fff; letter-spacing: .3px; }
.status-badge.ok { background: #10b981; } .status-badge.info { background: #3b82f6; }
.status-badge.warn { background: #f59e0b; } .status-badge.bad { background: #ef4444; }
.status-text { font-size: 13px; color: #475467; font-weight: 600; }
.meta { font-size: 12px; color: #667085; display: inline-flex; align-items: center; gap: 4px; }
.meta-ico { font-size: 11px; }
.pass-tag { color: #10b981; font-size: 12px; font-weight: 700; margin-left: auto; }
.fail-tag { color: #ef4444; font-size: 12px; font-weight: 700; margin-left: auto; }
.assert-list { padding: 6px 14px; border-bottom: 1px solid #eef1f4; background: #fcfcfd; }
.assert-item { display: flex; gap: 10px; align-items: baseline; font-size: 12px; padding: 3px 0; }
.assert-item.ok { color: #10b981; }
.assert-item.bad { color: #ef4444; }
.a-ico { font-weight: 700; flex: none; }
.a-desc { font-weight: 600; }
.a-actual { color: #98a2b3; word-break: break-all; }
.resp-body-head { padding: 0 10px; margin: 0; flex: none; }
.body-len { margin-left: auto; padding-right: 6px; font-size: 12px; }
.resp-body { background: #0f172a; padding: 14px; min-height: 120px; max-height: 480px; overflow: auto; }
.split-row .resp-body { max-height: calc(100vh - 320px); }
.json-pre { margin: 0; font-family: Consolas, 'Courier New', monospace; font-size: 12.5px; line-height: 1.65; color: #e2e8f0; white-space: pre; }
.json-pre :deep(.jv-key) { color: #93c5fd; }
.json-pre :deep(.jv-str) { color: #86efac; }
.json-pre :deep(.jv-num) { color: #fcd34d; }
.json-pre :deep(.jv-bool) { color: #c4b5fd; }
.json-pre :deep(.jv-null) { color: #c4b5fd; font-style: italic; }
.plain-pre { margin: 0; color: #e2e8f0; white-space: pre-wrap; word-break: break-all; font-size: 12.5px; }
.curl-pre { margin: 0; color: #7dd3fc; white-space: pre-wrap; word-break: break-all; font-size: 12.5px; }
.err-pre { margin: 0; color: #fca5a5; white-space: pre-wrap; word-break: break-all; font-size: 12.5px; }

/* 空态 */
.resp-empty { border: 1px dashed #d5d9e0; border-radius: 10px; padding: 50px 20px; text-align: center; background: #fafbfc; flex: 1; }
.empty-ico { font-size: 30px; color: #c9cdd6; }
.empty-title { margin-top: 10px; font-size: 14px; color: #667085; font-weight: 600; }
.empty-sub { margin-top: 4px; font-size: 12px; color: #98a2b3; }

/* 弹窗 */
.modal-mask { position: fixed; inset: 0; background: rgba(16,24,40,.5); display: flex; align-items: flex-start; justify-content: center; z-index: 100; padding-top: 8vh; }
.modal { background: #fff; border-radius: 12px; width: 620px; max-height: 78vh; overflow: auto; box-shadow: 0 12px 32px rgba(16,24,40,.16); }
.modal-head { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 12px; }
.modal-close { border: none; background: none; font-size: 14px; color: #98a2b3; cursor: pointer; }
.modal-close:hover { color: #475467; }
.form-row { display: flex; gap: 8px; padding: 0 20px 10px; }
.modal-input { flex: 1; padding: 8px 10px; border: 1px solid #e3e6ea; border-radius: 7px; font-size: 13px; outline: none; min-width: 0; }
.modal-input:focus { border-color: #5b4ffc; }
.btn-primary-sm { padding: 8px 14px; background: #5b4ffc; color: #fff; border: none; border-radius: 7px; font-size: 13px; cursor: pointer; white-space: nowrap; }
.btn-primary-sm:hover { background: #4a3ff0; }
.btn-primary-sm:disabled { opacity: .6; cursor: not-allowed; }
.vars-label { padding: 10px 20px 6px; font-size: 12px; color: #98a2b3; font-weight: 600; }
.vars-actions { display: flex; gap: 8px; align-items: center; }
.env-list { padding: 4px 20px 16px; }
.env-item { display: flex; align-items: center; gap: 10px; padding: 9px 0; border-bottom: 1px solid #f1f3f5; font-size: 13px; }
.env-item:last-child { border-bottom: none; }
.env-name { font-weight: 600; min-width: 90px; color: #1e293b; }
.env-sub { flex: 1; font-size: 12px; }
.env-op { border: 1px solid #e3e6ea; background: #fff; color: #475467; font-size: 12px; padding: 3px 10px; border-radius: 6px; cursor: pointer; }
.env-op:hover { border-color: #5b4ffc; color: #5b4ffc; }
.env-op.danger:hover { border-color: #ef4444; color: #ef4444; }
</style>
