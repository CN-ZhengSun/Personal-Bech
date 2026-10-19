<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin:4px 0 12px">
      <h1 style="margin:0">测试执行</h1>
      <ProjectSelect />
    </div>
    <div class="card">
      <div class="form-row">
        <button class="btn btn-small all-btn" :class="{ 'all-on': allSelected }" @click="toggleAllBtn">全选</button>
        <span class="sel-count">已选 {{ selected.length }} 条</span>
        <button class="btn btn-small" style="background:#ea580c;color:#fff;border:none;white-space:nowrap" @click="openBatchBug">批量转为BUG</button>
        <button class="btn btn-small btn-danger" style="white-space:nowrap" @click="batchRemove">批量删除</button>
        <select v-model="filter.assignee" @change="applyFilter" style="width:110px">
          <option value="">全部执行人</option>
          <option v-for="a in assigneeOptions" :key="a" :value="a">{{ a }}</option>
        </select>
        <select v-model="filter.status" @change="applyFilter" style="width:100px">
          <option value="">全部状态</option>
          <option v-for="(t, k) in statusText" :key="k" :value="k">{{ t }}</option>
        </select>
        <select v-model="filter.environment" @change="applyFilter" style="width:110px">
          <option value="">全部环境</option>
          <option v-for="a in envOptions" :key="a" :value="a">{{ a }}</option>
        </select>
        <select v-model="filter.version" @change="applyFilter" style="width:95px">
          <option value="">全部版本</option>
          <option v-for="a in verOptions" :key="a" :value="a">{{ a }}</option>
        </select>
      </div>
      <div class="exec-table-wrap">
      <table class="table exec-table">
        <thead><tr>
          <th style="width:32px"><input type="checkbox" :checked="allSelected" @change="toggleAll" @click.stop /></th>
          <th style="width:48px">ID</th>
          <th style="min-width:130px">用例</th>
          <th style="width:90px">执行人</th>
          <th style="width:110px">状态</th>
          <th style="width:180px">执行结果</th>
          <th style="width:260px">附件</th>
          <th style="width:90px">环境</th>
          <th style="width:90px">版本</th>
          <th style="width:150px">操作</th>
        </tr></thead>
        <tbody>
          <template v-for="e in execs" :key="e.id">
            <tr :class="{ 'row-disabled': !canEdit(e), 'row-open': expanded === e.id }" @click="toggleDetail(e)">
              <td @click.stop><input type="checkbox" :checked="selected.includes(e.id)" @change="toggleOne(e, $event)" /></td>
              <td>{{ e.id }}</td>
              <td><span class="cell-clamp" :title="caseMap[e.case_id] || '#' + e.case_id">{{ caseMap[e.case_id] || '#' + e.case_id }}</span></td>
              <td><span class="cell-clamp" :title="e.assignee || '—'">{{ e.assignee || '—' }}</span></td>
              <td @click.stop>
                <select :value="e.status" @change="update(e, $event.target.value)" :disabled="!canEdit(e)">
                  <option v-for="(t, k) in statusText" :key="k" :value="k">{{ t }}</option>
                </select>
              </td>
              <td @click.stop>
                <div class="result-box" :class="{ 'result-editing': isAbnormal(e.status) && canEdit(e) }">
                  <textarea v-if="isAbnormal(e.status) && canEdit(e)" class="result-textarea" rows="2" v-model="e.actual_result"
                    placeholder="填写失败/阻塞结果" @blur="saveResult(e)"></textarea>
                  <span v-else class="result-clamp" :class="{ 'result-auto': e.actual_result === '用例通过' }" :title="e.actual_result || ''">{{ e.actual_result || '—' }}</span>
                </div>
              </td>
              <td class="attach-cell" @click.stop>
                <div class="attach-actions" :class="{ 'attach-locked': !(isAbnormal(e.status) && canEdit(e)) }">
                  <div class="paste-zone" tabindex="0" @paste="onPaste($event, e)" :title="'点击后按 Ctrl+V 粘贴截图，或点按钮选择多个文件'"
                    :class="{ 'paste-disabled': !(isAbnormal(e.status) && canEdit(e)) }">粘贴截图 / 上传</div>
                  <input type="file" :id="'file-' + e.id" class="hidden-file" multiple
                    @change="onFileChange($event, e)" :disabled="!(isAbnormal(e.status) && canEdit(e))" />
                  <button class="btn btn-small btn-gray" @click="pickFile(e)" :disabled="!(isAbnormal(e.status) && canEdit(e))">选择文件</button>
                </div>
                <div v-if="attachments(e).length" class="attach-list">
                  <div v-for="(u, i) in attachments(e).slice(0, attachShown)" :key="i" class="attach-item">
                    <a class="attach-link" @click.prevent="previewAttachment(u)" :title="u.name">{{ u.name }}</a>
                  </div>
                  <span v-if="attachments(e).length > attachShown" class="attach-more" @click="toggleDetail(e)"
                    :title="'共 ' + attachments(e).length + ' 个附件，点击查看全部'">+{{ attachments(e).length - attachShown }}</span>
                </div>
                <span v-else class="muted">—</span>
              </td>
              <td><span class="cell-clamp" :title="e.environment || envOf(e.case_id) || '—'">{{ e.environment || envOf(e.case_id) || '—' }}</span></td>
              <td><span class="cell-clamp" :title="e.version || verOf(e.case_id) || '—'">{{ e.version || verOf(e.case_id) || '—' }}</span></td>
              <td @click.stop>
                <button v-if="isAbnormal(e.status) && canEdit(e) && !e.bug_id" class="btn btn-small" style="background:#ea580c;color:#fff;border:none" @click="toBug(e)">转为BUG</button>
                <button v-if="isAbnormal(e.status) && canEdit(e) && e.bug_id" class="btn btn-small" style="background:#64748b;color:#fff;border:none" @click="unlinkBug(e)">撤销BUG</button>
                <button v-if="canEdit(e)" class="btn btn-small btn-danger" @click="remove(e)">删除</button>
              </td>
            </tr>
            <tr v-if="expanded === e.id" class="detail-row">
              <td colspan="10">
                <div class="detail-box">
                  <div class="detail-cols">
                    <div class="detail-info">
                      <div class="detail-title">{{ caseMap[e.case_id] || '未知用例' }}</div>
                      <div class="detail-grid2">
                        <div><span class="lbl">模块</span><span class="fv">{{ caseDetail(e.case_id)?.module || '—' }}</span></div>
                        <div><span class="lbl">优先级</span><span class="fv">{{ caseDetail(e.case_id)?.priority || '—' }}</span></div>
                        <div><span class="lbl">类型</span><span class="fv">{{ typeText[caseDetail(e.case_id)?.case_type] || caseDetail(e.case_id)?.case_type || '—' }}</span></div>
                        <div><span class="lbl">环境</span><span class="fv">{{ e.environment || envOf(e.case_id) || '—' }}</span></div>
                        <div><span class="lbl">版本</span><span class="fv">{{ e.version || verOf(e.case_id) || '—' }}</span></div>
                        <div><span class="lbl">执行状态</span><span class="fv">{{ statusText[e.status] || e.status }}</span></div>
                        <div><span class="lbl">执行人</span><span class="fv">{{ e.assignee || '—' }}</span></div>
                      </div>
                      <p class="lbl" style="margin-top:12px">前置条件</p>
                      <div class="detail-expected">{{ caseDetail(e.case_id)?.preconditions || '—' }}</div>
                      <p class="lbl" style="margin-top:12px">附件（{{ attachments(e).length }}）</p>
                      <div class="attach-grid">
                        <div v-for="(u, i) in attachments(e)" :key="i" class="attach-tile">
                          <a v-if="isImage(u.url)" class="attach-thumb" @click.prevent="previewAttachment(u)">
                            <img :src="u.url" :alt="u.name" />
                          </a>
                          <a v-else-if="isVideo(u.url)" class="attach-thumb" @click.prevent="previewAttachment(u)">
                            <video :src="u.url + '#t=0.1'" muted playsinline preload="metadata"></video>
                          </a>
                          <a v-else class="attach-thumb file-card" @click.prevent="previewAttachment(u)"
                            :style="{ '--c': fileType(u).bg, '--light': fileType(u).light }">
                            <span class="ft-label">{{ fileType(u).label }}</span>
                          </a>
                          <div class="attach-name" :title="u.name">{{ u.name }}</div>
                          <button v-if="canEdit(e)" class="btn btn-small btn-danger" @click="removeAttachment(e, i)">删除</button>
                        </div>
                      </div>
                      <p v-if="!attachments(e).length" class="muted" style="margin-top:6px">暂无附件</p>
                      <div v-if="canEdit(e)" class="form-row" style="margin-top:8px">
                        <button class="btn btn-small" @click="pickFile(e)">添加附件</button>
                        <input type="file" :id="'file-' + e.id" class="hidden-file" multiple @change="onFileChange($event, e)" />
                        <span class="muted" style="font-size:12px">可多选文件，或点击「粘贴截图 / 上传」后 Ctrl+V 粘贴</span>
                      </div>
                    </div>
                    <div class="detail-steps">
                      <p class="lbl" style="margin-bottom:6px">操作步骤</p>
                      <table class="table">
                        <thead><tr><th style="width:48px">#</th><th>操作</th></tr></thead>
                        <tbody>
                          <tr v-for="s in (caseDetail(e.case_id)?.steps || [])" :key="s.id || s.step_no">
                            <td>{{ s.step_no }}</td><td>{{ s.action }}</td>
                          </tr>
                        </tbody>
                      </table>
                      <p v-if="!caseDetail(e.case_id)?.steps?.length" class="muted" style="margin-top:6px">无步骤</p>
                      <p class="lbl" style="margin-top:12px">预期结果</p>
                      <div class="detail-expected">{{ caseDetail(e.case_id)?.expected || '—' }}</div>
                      <p class="lbl" style="margin-top:12px">实际结果</p>
                      <div class="detail-expected">{{ e.actual_result || '—' }}</div>
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      </div>
      <p v-if="!execs.length" class="muted" style="margin-top:10px">暂无执行记录，在用例页勾选后「批量执行」或点「去执行」生成。</p>
    </div>

    <!-- 附件预览：当前页面内展示，支持 word/pdf/ppt/excel/mp4/txt 等 -->
    <AttachmentPreview :url="preview?.url" :name="preview?.name" :visible="!!preview" @close="preview = null" />

    <!-- 转为 BUG 弹窗：自动预填用例标题、操作步骤与附件 -->
    <div class="modal-mask" v-if="showBug">
      <div class="modal">
        <h3>新增缺陷（来自执行记录）</h3>
        <div class="field"><label>标题 *</label><input v-model="bugForm.title" /></div>
        <div class="field"><label>描述</label><textarea v-model="bugForm.description"></textarea></div>
        <div class="field"><label>复现步骤</label><textarea v-model="bugForm.steps" style="min-height:120px"></textarea></div>
        <div class="field"><label>严重程度</label>
          <select v-model="bugForm.severity"><option v-for="(t, k) in sevText" :key="k" :value="k">{{ t }}</option></select>
        </div>
        <div class="field"><label>优先级</label>
          <select v-model="bugForm.priority"><option>P0</option><option>P1</option><option>P2</option><option>P3</option></select>
        </div>
        <div class="field"><label>出现概率</label>
          <select v-model="bugForm.probability"><option v-for="(t, k) in probText" :key="k" :value="k">{{ t }}</option></select>
        </div>
        <div class="field"><label>负责人</label><input v-model="bugForm.assignee" /></div>
        <div class="form-row" style="margin-top:8px">
          <div class="field" style="flex:1"><label>环境（来自执行记录）</label><input v-model="bugForm.environment" placeholder="自动带入，可修改" /></div>
          <div class="field" style="flex:1"><label>版本（来自执行记录）</label><input v-model="bugForm.version" placeholder="自动带入，可修改" /></div>
        </div>
        <div class="field" v-if="attachments(bugSource)">
          <label>附件（随执行记录带入）</label>
          <div class="attach-list">
            <div v-for="(u, i) in attachments(bugSource)" :key="i" class="attach-item">
              <span>{{ u.name }}</span>
            </div>
          </div>
        </div>
        <p v-if="bugSource && bugSource.bug_id" class="muted">该执行记录已关联缺陷 #{{ bugSource.bug_id }}</p>
        <div class="actions">
          <button class="btn btn-gray" @click="showBug = false">取消</button>
          <button class="btn" @click="createBug">保存</button>
        </div>
      </div>
    </div>
    <!-- 批量转为 BUG 弹窗：公共字段统一填写，标题/复现步骤/附件按各执行记录带入 -->
    <div class="modal-mask" v-if="showBatchBug">
      <div class="modal">
        <h3>批量转为缺陷（共 {{ batchBugTargets.length }} 条）</h3>
        <p class="muted" style="margin:6px 0">以下缺陷将使用各执行记录对应的用例标题、操作步骤和附件。</p>
        <div class="batch-bug-list">
          <div v-for="(e, i) in batchBugTargets" :key="e.id" class="batch-bug-item">
            <span class="badge">{{ statusText[e.status] }}</span>
            <span class="tt" :title="caseMap[e.case_id] || e.case_id">{{ caseMap[e.case_id] || ('#' + e.case_id) }}</span>
            <span v-if="e.bug_id" class="muted">已关联 #{{ e.bug_id }}</span>
          </div>
        </div>
        <div class="field"><label>严重程度</label>
          <select v-model="batchBugForm.severity"><option v-for="(t, k) in sevText" :key="k" :value="k">{{ t }}</option></select>
        </div>
        <div class="field"><label>优先级</label>
          <select v-model="batchBugForm.priority"><option>P0</option><option>P1</option><option>P2</option><option>P3</option></select>
        </div>
        <div class="field"><label>出现概率</label>
          <select v-model="batchBugForm.probability"><option v-for="(t, k) in probText" :key="k" :value="k">{{ t }}</option></select>
        </div>
        <div class="field"><label>负责人</label><input v-model="batchBugForm.assignee" placeholder="留空表示不指定负责人" /></div>
        <div class="actions">
          <button class="btn btn-gray" @click="showBatchBug = false">取消</button>
          <button class="btn" @click="createBatchBugs">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import AttachmentPreview from '../components/AttachmentPreview.vue'
import ProjectSelect from '../components/ProjectSelect.vue'
import { caseApi, executionApi, bugApi, uploadApi } from '../api'

const allExecs = ref([])
const execs = ref([])
const cases = ref([])
const caseMap = ref({})
const caseEnv = ref({})
const caseVer = ref({})
const caseDetailMap = ref({})
const filter = ref({ assignee: '', status: '', environment: '', version: '' })
const expanded = ref(null)
const showBug = ref(false)
const bugSource = ref(null)
const preview = ref(null)
const selected = ref([])
const showBatchBug = ref(false)
const batchBugTargets = ref([])
const batchBugForm = ref({ severity: 'major', priority: 'P1', probability: 'always', assignee: '' })
const bugForm = ref({ title: '', description: '', steps: '', severity: 'major', priority: 'P1', probability: 'always', assignee: '', attachments: '', environment: '', version: '', module: '' })
const statusText = { untested: '未执行', pass: '通过', fail: '失败', blocked: '阻塞', skipped: '跳过' }
const sevText = { critical: '致命', major: '严重', minor: '一般', trivial: '轻微' }
const probText = { always: '必现', occasional: '偶现', multiple: '多次出现', unreproducible: '无法复现' }
const typeText = { functional: '功能', ui: 'UI', api: '接口', performance: '性能', other: '其他' }
const projectId = () => localStorage.getItem('twb_project') || undefined
const currentUser = () => { try { return JSON.parse(localStorage.getItem('twb_user') || '{}') } catch { return {} } }

const isAbnormal = (s) => s === 'fail' || s === 'blocked'
const canEdit = (e) => {
  const u = currentUser()
  if (!u.username) return true
  if (u.role === 'admin') return true
  if (!e.assignee) return true
  return e.assignee === u.username
}
const envOf = (cid) => caseEnv.value[cid]
const verOf = (cid) => caseVer.value[cid]
const caseDetail = (cid) => caseDetailMap.value[cid] || {}

const assigneeOptions = computed(() => [...new Set(allExecs.value.map((e) => e.assignee).filter(Boolean))])
const envOptions = computed(() => [...new Set(allExecs.value.map((e) => e.environment || envOf(e.case_id)).filter(Boolean))])
const verOptions = computed(() => [...new Set(allExecs.value.map((e) => e.version || verOf(e.case_id)).filter(Boolean))])

// ---------- 批量勾选 ----------
const selectedExecs = computed(() => allExecs.value.filter((e) => selected.value.includes(e.id)))
const allSelected = computed(() => execs.value.length > 0 && execs.value.every((e) => selected.value.includes(e.id)))
function toggleAllBtn() {
  selected.value = allSelected.value ? [] : execs.value.map((e) => e.id)
}
function toggleOne(e, ev) {
  if (ev.target.checked) { if (!selected.value.includes(e.id)) selected.value.push(e.id) }
  else selected.value = selected.value.filter((x) => x !== e.id)
}

// 附件解析：兼容纯 url 字符串与 {url,name} 对象
function parseEvidence(ev) {
  if (!ev) return []
  try {
    const a = JSON.parse(ev)
    return (Array.isArray(a) ? a : [ev]).map((x) => (typeof x === 'string' ? { url: x, name: x.split('/').pop() } : { url: x.url, name: x.name || x.url.split('/').pop() }))
  } catch {
    return [{ url: ev, name: ev.split('/').pop() }]
  }
}
const attachments = (e) => (e ? parseEvidence(e.evidence) : [])
const isImage = (url) => /\.(png|jpe?g|gif|webp|bmp|svg)(\?|#|$)/i.test(url || '')
const isVideo = (url) => /\.(mp4|mov|avi|mkv|webm|m4v|flv|wmv|mpg|mpeg|3gp)(\?|#|$)/i.test(url || '')
const fileType = (u) => {
  const n = (u && (u.name || u.url)) || ''
  const m = n.split('?')[0].split('#')[0].match(/\.([A-Za-z0-9]+)$/)
  const e = ((m && m[1]) || '').toLowerCase()
  const map = {
    pdf: ['PDF', '#dc2626', '#fee2e2'], doc: ['DOC', '#2563eb', '#dbeafe'], docx: ['DOCX', '#2563eb', '#dbeafe'],
    xls: ['XLS', '#16a34a', '#dcfce7'], xlsx: ['XLSX', '#16a34a', '#dcfce7'],
    ppt: ['PPT', '#ea580c', '#ffedd5'], pptx: ['PPTX', '#ea580c', '#ffedd5'],
    txt: ['TXT', '#64748b', '#f1f5f9'], md: ['MD', '#64748b', '#f1f5f9'],
    zip: ['ZIP', '#b45309', '#fef3c7'], rar: ['RAR', '#b45309', '#fef3c7'], '7z': ['7Z', '#b45309', '#fef3c7'], gz: ['GZ', '#b45309', '#fef3c7'], tar: ['TAR', '#b45309', '#fef3c7'],
    mp3: ['MP3', '#7c3aed', '#ede9fe'], wav: ['WAV', '#7c3aed', '#ede9fe'], m4a: ['M4A', '#7c3aed', '#ede9fe'], aac: ['AAC', '#7c3aed', '#ede9fe'], ogg: ['OGG', '#7c3aed', '#ede9fe'], flac: ['FLAC', '#7c3aed', '#ede9fe'],
  }
  const hit = map[e]
  return hit ? { label: hit[0], bg: hit[1], light: hit[2] } : { label: '文件', bg: '#475569', light: '#f1f5f9' }
}

// 附件单行展示：每项固定宽 92px + 间距 4px，按列宽计算一行能容纳几个，溢出用 +N 收起
const attachShown = ref(2)
function computeAttachShown() {
  nextTick(() => {
    const list = document.querySelector('.attach-list')
    if (!list) return
    const itemW = 96 // 92 项宽 + 4 gap
    attachShown.value = Math.max(1, Math.floor((list.clientWidth + 4) / itemW))
  })
}
function refreshShown() {
  computeAttachShown()
}
window.addEventListener('resize', computeAttachShown)

async function load() {
  const pid = projectId()
  const [c, allC, e] = await Promise.all([caseApi.list(pid), caseApi.list(), executionApi.list()])
  cases.value = c.data
  allExecs.value = e.data
  caseMap.value = Object.fromEntries(allC.data.map((x) => [x.id, x.title]))
  caseEnv.value = Object.fromEntries(allC.data.map((x) => [x.id, x.environment]).filter(([, v]) => v))
  caseVer.value = Object.fromEntries(allC.data.map((x) => [x.id, x.version]).filter(([, v]) => v))
  applyFilter()
  computeAttachShown()
}
function applyFilter() {
  const { assignee, status, environment, version } = filter.value
  execs.value = allExecs.value.filter((e) =>
    (!assignee || e.assignee === assignee) &&
    (!status || e.status === status) &&
    (!environment || (e.environment || envOf(e.case_id)) === environment) &&
    (!version || (e.version || verOf(e.case_id)) === version)
  )
}
async function toggleDetail(e) {
  if (expanded.value === e.id) { expanded.value = null; return }
  expanded.value = e.id
  if (!caseDetailMap.value[e.case_id]) {
    try {
      const { data } = await caseApi.detail(e.case_id)
      caseDetailMap.value[e.case_id] = data
    } catch {}
  }
}
async function update(e, status) {
  const patch = { status }
  if (!e.assignee) {
    e.assignee = currentUser().username || currentUser().display_name || ''
    patch.assignee = e.assignee
  }
  if (!e.environment) { e.environment = envOf(e.case_id) || null; if (e.environment) patch.environment = e.environment }
  if (!e.version) { e.version = verOf(e.case_id) || null; if (e.version) patch.version = e.version }
  // 改为「通过」且执行结果为空时，自动填入「用例通过」；从「通过」改到其他状态时清除该默认值
  if (status === 'pass' && !e.actual_result) {
    e.actual_result = '用例通过'
    patch.actual_result = '用例通过'
  } else if (status !== 'pass' && e.actual_result === '用例通过') {
    e.actual_result = ''
    patch.actual_result = ''
  }
  await executionApi.update(e.id, patch)
  e.status = status
  window.$toast.success('状态已更新为「' + statusText[status] + '」')
}
async function saveResult(e) {
  await executionApi.update(e.id, { actual_result: e.actual_result || '' })
  window.$toast.success('执行结果已保存')
}

// ---------- 附件上传（文件多选 + 剪贴板粘贴多张） ----------
function pickFile(e) {
  document.getElementById('file-' + e.id)?.click()
}
async function onFileChange(ev, e) {
  const files = Array.from(ev.target.files || [])
  for (const file of files) await uploadAttachment(e, file)
  ev.target.value = ''
}
async function onPaste(ev, e) {
  const items = Array.from(ev.clipboardData?.items || [])
  const imgs = items.filter((it) => it.type && it.type.startsWith('image/'))
  if (imgs.length) {
    ev.preventDefault()
    for (const it of imgs) {
      const file = it.getAsFile()
      if (file) await uploadAttachment(e, file)
    }
    return
  }
  if (ev.clipboardData?.files?.length) {
    ev.preventDefault()
    for (const f of Array.from(ev.clipboardData.files)) await uploadAttachment(e, f)
  }
}
async function uploadAttachment(e, file) {
  try {
    const { data } = await uploadApi.upload(file)
    const arr = parseEvidence(e.evidence)
    arr.push({ url: data.url, name: file.name })
    await executionApi.update(e.id, { evidence: JSON.stringify(arr) })
    e.evidence = JSON.stringify(arr)
    window.$toast.success('附件「' + file.name + '」已上传')
    refreshShown()
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '上传失败')
  }
}
async function removeAttachment(e, i) {
  if (!(await window.$confirm('确认移除该附件？', { danger: true }))) return
  const arr = parseEvidence(e.evidence)
  arr.splice(i, 1)
  await executionApi.update(e.id, { evidence: JSON.stringify(arr) })
  e.evidence = JSON.stringify(arr)
  window.$toast.success('已移除附件')
  refreshShown()
}
function previewAttachment(u) {
  preview.value = { url: u.url, name: u.name }
}

// ---------- 转为 BUG：预填用例标题 + 操作步骤 + 执行附件 + 环境/版本 ----------
async function toBug(e) {
  if (!projectId()) return window.$toast.warning('请先在上方选择项目')
  bugForm.value = { title: caseMap.value[e.case_id] || '执行失败缺陷', description: e.actual_result || '', steps: '', severity: 'major', priority: 'P1', probability: 'always', assignee: '', attachments: e.evidence || '', environment: e.environment || '', version: e.version || '', module: '' }
  try {
    const { data } = await caseApi.detail(e.case_id)
    if (data?.title) bugForm.value.title = data.title
    if (data?.module) bugForm.value.module = data.module
    if (data?.steps?.length) {
      bugForm.value.steps = data.steps.map((s) => `${s.step_no}. ${s.action}（预期：${s.expected || '—'}）`).join('\n')
    } else {
      bugForm.value.steps = '（该用例无操作步骤，请补充复现步骤）'
    }
  } catch {}
  bugSource.value = e
  showBug.value = true
}
async function createBug() {
  if (!bugForm.value.title) return window.$toast.warning('请填写缺陷标题')
  const u = currentUser()
  const { data } = await bugApi.create({ project_id: Number(projectId()), ...bugForm.value, reporter: u.display_name || u.username || 'admin' })
  if (bugSource.value) {
    await executionApi.update(bugSource.value.id, { bug_id: data.id })
    bugSource.value.bug_id = data.id
  }
  showBug.value = false
  bugForm.value = { title: '', description: '', steps: '', severity: 'major', priority: 'P1', probability: 'always', assignee: '', attachments: '', environment: '', version: '', module: '' }
  window.$toast.success('缺陷已创建，已关联到该执行记录')
}
async function remove(e) {
  if (!(await window.$confirm('确认删除该执行记录？', { danger: true }))) return
  await executionApi.remove(e.id); window.$toast.success('已删除'); load()
}
// 撤销 BUG：解除关联并删除对应缺陷
async function unlinkBug(e) {
  const bugId = e.bug_id
  if (!bugId) return
  if (!(await window.$confirm('确认撤销该执行记录关联的缺陷 #' + bugId + '？撤销后将同步删除该缺陷。', { danger: true }))) return
  await executionApi.update(e.id, { bug_id: null })
  await bugApi.remove(bugId)
  e.bug_id = null
  window.$toast.success('已撤销 BUG 关联并删除对应缺陷')
}

// ---------- 批量转为 BUG：仅失败/阻塞的记录，公共字段统一，标题/步骤/附件各自带入 ----------
async function openBatchBug() {
  const targets = selectedExecs.value.filter((e) => isAbnormal(e.status))
  if (!targets.length) return window.$toast.warning('请先勾选「失败」或「阻塞」状态的执行记录')
  for (const e of targets) {
    if (!caseDetailMap.value[e.case_id]) {
      try { caseDetailMap.value[e.case_id] = (await caseApi.detail(e.case_id)).data } catch {}
    }
  }
  batchBugTargets.value = targets
  batchBugForm.value = { severity: 'major', priority: 'P1', probability: 'always', assignee: '' }
  showBatchBug.value = true
}
async function createBatchBugs() {
  if (!projectId()) return window.$toast.warning('请先在上方选择项目')
  let n = 0
  for (const e of batchBugTargets.value) {
    const d = caseDetailMap.value[e.case_id] || {}
    const title = d.title || caseMap.value[e.case_id] || '执行失败缺陷'
    const steps = d.steps?.length ? d.steps.map((s) => `${s.step_no}. ${s.action}（预期：${s.expected || '—'}）`).join('\n') : '（该用例无操作步骤，请补充复现步骤）'
    const { data } = await bugApi.create({
      project_id: Number(projectId()), title, description: e.actual_result || '',
      steps, severity: batchBugForm.value.severity, priority: batchBugForm.value.priority,
      probability: batchBugForm.value.probability, assignee: batchBugForm.value.assignee,
      attachments: e.evidence || '', environment: e.environment || '', version: e.version || '',
      module: d.module || '', reporter: currentUser().display_name || currentUser().username || 'admin'
    })
    await executionApi.update(e.id, { bug_id: data.id })
    e.bug_id = data.id
    n++
  }
  showBatchBug.value = false
  selected.value = []
  window.$toast.success('已批量创建 ' + n + ' 条缺陷并关联到执行记录')
}
async function batchRemove() {
  if (!selected.value.length) return window.$toast.warning('请先勾选要删除的执行记录')
  if (!(await window.$confirm('确认删除选中的 ' + selected.value.length + ' 条执行记录？', { danger: true }))) return
  for (const id of [...selected.value]) {
    try { await executionApi.remove(id) } catch {}
  }
  selected.value = []
  window.$toast.success('已批量删除')
  load()
}
onMounted(load)
watch(() => localStorage.getItem('twb_project'), load)
onBeforeUnmount(() => window.removeEventListener('resize', computeAttachShown))
</script>

<style scoped>
.exec-table-wrap { overflow-x: auto; }
.exec-table { table-layout: fixed; min-width: 1180px; }
.exec-table th, .exec-table td { overflow: hidden; }
.all-btn { min-width: 58px; background: #fff; color: #2563eb; border: 1px solid #2563eb; }
.all-btn:hover { background: #eff6ff; }
.all-btn.all-on { background: #2563eb; color: #fff; }
.sel-count { font-size: 12px; color: #64748b; white-space: nowrap; min-width: 76px; }
.batch-bug-list { max-height: 160px; overflow-y: auto; border: 1px solid #eef1f4; border-radius: 6px; padding: 6px 8px; margin-bottom: 10px; background: #fafbfc; }
.batch-bug-item { display: flex; align-items: center; gap: 8px; padding: 3px 0; font-size: 13px; }
.batch-bug-item .tt { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #334155; }
.batch-bug-item .badge { font-size: 12px; padding: 1px 8px; border-radius: 10px; background: #fee2e2; color: #dc2626; flex-shrink: 0; }
.result-input {
  width: 100%; min-width: 140px; padding: 5px 8px;
  border: 1px solid #fca5a5; border-radius: 6px; font-size: 12px;
  background: #fff5f5;
}
.result-input:focus { outline: none; border-color: #ef4444; background: #fff; }
/* 执行结果统一容器：所有状态外观一致，编辑态/只读态固定同高 */
.result-box {
  border: 1px solid #e5e7eb; border-radius: 6px; padding: 4px 8px;
  height: 46px; background: #fff; box-sizing: border-box; overflow: hidden;
}
.result-editing { border-color: #fca5a5; background: #fff5f5; }
.result-textarea {
  width: 100%; height: 36px; border: none; outline: none; resize: none; background: transparent;
  font-size: 12px; line-height: 1.5; color: #374151; font-family: inherit;
  padding: 0; display: block; box-sizing: border-box;
}
.result-clamp {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  max-width: 240px; white-space: pre-wrap; font-size: 12px; color: #374151; word-break: break-all;
}
.result-auto { color: #94a3b8; }
/* 文本列统一最多两行，超出省略 */
.cell-clamp {
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  word-break: break-all; max-width: 200px; white-space: pre-wrap;
}
.attach-cell { min-width: 150px; }
.attach-actions { display: flex; align-items: center; gap: 4px; margin-bottom: 4px; }
.attach-actions .paste-zone { margin-bottom: 0; flex-shrink: 0; }
.attach-actions button { flex-shrink: 0; white-space: nowrap; }
.attach-locked { opacity: 0.55; }
.paste-zone {
  display: inline-block; padding: 5px 8px; border: 1px dashed #cbd5e1; border-radius: 6px;
  font-size: 12px; color: #64748b; cursor: text; background: #f8fafc; white-space: nowrap;
}
.paste-zone:focus { outline: none; border-color: #2563eb; color: #2563eb; background: #eff6ff; }
.paste-disabled { cursor: not-allowed; opacity: 0.5; }
.hidden-file { display: none; }
.attach-list { margin-top: 4px; display: flex; flex-wrap: nowrap; gap: 4px; align-items: center; overflow: hidden; }
.attach-item {
  display: inline-flex; align-items: center; justify-content: flex-start; padding: 2px 6px;
  background: #eff6ff; border-radius: 4px; font-size: 12px; width: 92px; box-sizing: border-box; flex-shrink: 0;
}
.attach-link {
  display: inline-block; color: #2563eb; text-decoration: none; cursor: pointer;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 72px; vertical-align: middle;
}
.attach-link:hover { text-decoration: underline; }
.attach-more {
  display: inline-flex; align-items: center; padding: 2px 8px; background: #f1f5f9;
  border: 1px solid #e2e8f0; border-radius: 4px; font-size: 12px; color: #475569;
  cursor: pointer; white-space: nowrap; flex-shrink: 0;
}
.attach-more:hover { background: #e2e8f0; color: #1e293b; }
.preview-body { text-align: center; }
.preview-img { max-width: 100%; max-height: 60vh; border-radius: 6px; }
.row-disabled .paste-zone { opacity: 0.6; }
.row-open { background: #f0f7ff; }
.detail-row td { background: #f8fafc; }
.detail-box { padding: 6px 2px; }
.detail-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px; }
.lbl { color: #6b7280; font-size: 12px; margin-right: 6px; }
.result-text { white-space: pre-wrap; font-size: 13px; color: #374151; background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px; margin-top: 4px; }
.detail-section { margin-top: 12px; }
.attach-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 6px; }
.attach-tile { width: calc((100% - 32px) / 5); text-align: center; flex-shrink: 0; }
.attach-thumb { display: block; width: 100%; aspect-ratio: 4 / 3; border-radius: 6px; overflow: hidden; border: 1px solid #e5e7eb; background: #f1f5f9; cursor: pointer; }
.attach-thumb img { width: 100%; height: 100%; object-fit: cover; }
.file-card {
  position: relative; display: flex; align-items: center; justify-content: center;
  width: 100%; aspect-ratio: 4/3; border-radius: 6px; cursor: pointer;
  background: var(--light, #f1f5f9); border: 1px solid #e2e8f0;
  box-sizing: border-box; overflow: hidden;
}
.file-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 5px;
  background: var(--c, #475569);
}
.ft-label { font-size: 14px; font-weight: 700; letter-spacing: 1px; color: var(--c, #475569); line-height: 1; }
.attach-thumb video { width: 100%; height: 100%; object-fit: cover; display: block; }
.attach-name { font-size: 12px; color: #374151; margin: 4px 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.detail-cols { display: flex; gap: 18px; align-items: flex-start; }
.detail-info { flex: 1; min-width: 0; }
.detail-steps { flex: 1; min-width: 0; }
.detail-title { font-size: 16px; font-weight: 600; color: #111827; line-height: 1.4; margin-bottom: 8px; }
.detail-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; }
.detail-grid2 > div { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.detail-grid2 .fv { font-size: 13px; color: #374151; word-break: break-all; }
.detail-expected { background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px 10px; white-space: pre-wrap; word-break: break-all; font-size: 13px; }
</style>
