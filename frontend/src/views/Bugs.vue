<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin:4px 0 12px">
      <h1 style="margin:0">缺陷跟踪</h1>
      <ProjectSelect />
    </div>
    <div class="card">
      <div class="form-row">
        <input v-model="filter.keyword" placeholder="搜索标题" style="flex:1" @keyup.enter="load" />
        <select v-model="filter.status" @change="load">
          <option value="">全部状态</option>
          <option v-for="(t, k) in statusText" :key="k" :value="k">{{ t }}</option>
        </select>
        <select v-model="filter.severity" @change="load">
          <option value="">全部严重程度</option>
          <option v-for="(t, k) in sevText" :key="k" :value="k">{{ t }}</option>
        </select>
        <button class="btn" @click="openCreate">新增缺陷</button>
      </div>
      <div class="table-wrap">
      <table class="table bug-table">
        <thead><tr>
          <th style="width:48px">ID</th>
          <th style="width:200px">标题</th>
          <th style="width:90px">严重程度</th>
          <th style="width:70px">优先级</th>
          <th style="width:90px">出现概率</th>
          <th style="width:100px">状态</th>
          <th style="width:90px">模块</th>
          <th style="width:80px">负责人</th>
          <th style="width:110px">操作</th>
        </tr></thead>
        <tbody>
          <template v-for="b in bugs" :key="b.id">
            <tr :class="{ 'row-active': expandedId === b.id }" style="cursor:pointer" @click="toggleDetail(b)">
              <td>{{ b.id }}</td>
              <td><span class="cell-clamp" :title="b.title">{{ b.title }}</span></td>
              <td>
                <select v-if="canEdit(b)" class="cell-select" :style="{ color: sevColor(b.severity) }" :value="b.severity" @click.stop @change="updateField(b, 'severity', $event.target.value)">
                  <option v-for="(t, k) in sevText" :key="k" :value="k">{{ t }}</option>
                </select>
                <span v-else :style="{ color: sevColor(b.severity) }">{{ sevText[b.severity] || b.severity }}</span>
              </td>
              <td>
                <select v-if="canEdit(b)" class="cell-select" :style="{ color: prioColor(b.priority) }" :value="b.priority" @click.stop @change="updateField(b, 'priority', $event.target.value)">
                  <option>P0</option><option>P1</option><option>P2</option><option>P3</option>
                </select>
                <span v-else :style="{ color: prioColor(b.priority) }">{{ b.priority }}</span>
              </td>
              <td>
                <select v-if="canEdit(b)" class="cell-select" :style="{ color: probColor(b.probability) }" :value="b.probability" @click.stop @change="updateField(b, 'probability', $event.target.value)">
                  <option v-for="(t, k) in probText" :key="k" :value="k">{{ t }}</option>
                </select>
                <span v-else :style="{ color: probColor(b.probability) }">{{ probText[b.probability] || b.probability || '—' }}</span>
              </td>
              <td>
                <select v-if="canEdit(b)" class="cell-select" :style="{ color: statusColor(b.status) }" :value="b.status" @click.stop @change="updateField(b, 'status', $event.target.value)">
                  <option v-for="(t, k) in statusText" :key="k" :value="k">{{ t }}</option>
                </select>
                <span v-else :style="{ color: statusColor(b.status) }">{{ statusText[b.status] || b.status }}</span>
              </td>
              <td>{{ b.module || '—' }}</td>
              <td>{{ b.assignee || '—' }}</td>
              <td @click.stop>
                <button v-if="canEdit(b)" class="btn btn-small btn-gray" @click="openEdit(b)">编辑</button>
                <button class="btn btn-small btn-danger" @click="remove(b)">删除</button>
              </td>
            </tr>
            <!-- 行内向下展开详情 -->
            <tr v-if="expandedId === b.id" class="detail-row">
              <td colspan="9">
                <div class="detail-box">
                  <div class="detail-head">
                    <div class="detail-meta">
                      <span>报告人：{{ b.reporter || '—' }}</span>
                      <span>模块：{{ b.module || '—' }}</span>
                      <span>环境：{{ b.environment || '—' }}</span>
                      <span>版本：{{ b.version || '—' }}</span>
                      <span>严重程度：<b :style="{ color: sevColor(b.severity) }">{{ sevText[b.severity] || b.severity }}</b></span>
                      <span>优先级：<b :style="{ color: prioColor(b.priority) }">{{ b.priority }}</b></span>
                      <span>概率：<b :style="{ color: probColor(b.probability) }">{{ probText[b.probability] || b.probability || '—' }}</b></span>
                      <span>创建：{{ fmt(b.created_at) }}</span>
                    </div>
                    <div class="detail-status">
                      <label>BUG状态</label>
                      <select :style="{ color: statusColor(b.status) }" v-model="b.status" @change="updateStatus(b)">
                        <option v-for="(t, k) in statusText" :key="k" :value="k">{{ t }}</option>
                      </select>
                      <div v-if="!canEdit(b)" class="muted" style="margin-top:4px;font-size:12px">（仅执行人/管理员可操作，非可编辑状态仅供查看）</div>
                    </div>
                  </div>
                  <p class="detail-title">描述</p>
                  <p class="detail-content">{{ b.description || '（无描述）' }}</p>
                  <p class="detail-title">复现步骤</p>
                  <table v-if="parseSteps(b.steps).length" class="table" style="margin-top:6px">
                    <thead><tr><th style="width:44px">#</th><th>操作</th><th>预期</th><th>实际</th></tr></thead>
                    <tbody>
                      <tr v-for="s in parseSteps(b.steps)" :key="s.step_no">
                        <td>{{ s.step_no }}</td><td>{{ s.action }}</td><td>{{ s.expected || '—' }}</td><td>{{ s.actual || '—' }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <p v-else class="muted">{{ b.steps || '无' }}</p>
                  <div class="detail-bottom">
                    <!-- 附件：左半边 -->
                    <div class="detail-left">
                      <p class="detail-title">附件（{{ attachments(b).length }}）</p>
                      <div v-if="attachments(b).length" class="bug-attach-grid">
                        <div v-for="(u, i) in attachments(b)" :key="i" class="bug-attach-tile">
                          <div class="bug-thumb" :class="{ 'img-thumb': isImage(u.url) }" @click="previewAttachment(u)">
                            <img v-if="isImage(u.url)" :src="u.url" :alt="u.name" />
                            <div v-else class="file-icon" :class="'fic-' + fileKind(u.name)">
                              <span class="fic-label">{{ fileLabel(u.name) }}</span>
                            </div>
                          </div>
                          <div class="bug-attach-name" :title="u.name">{{ u.name }}</div>
                        </div>
                      </div>
                      <p v-else class="muted">暂无附件</p>
                    </div>
                    <!-- 流转记录：右半边 -->
                    <div class="detail-right">
                      <p class="detail-title">流转记录 / 评论</p>
                      <div class="comment-scroll">
                        <div v-for="c in commentsMap[b.id] || []" :key="c.id" class="comment">
                          <span class="event-tag" :class="eventTag(c.event_type)">{{ eventText[c.event_type] || c.event_type }}</span>
                          <span class="muted">{{ c.user || '匿名' }}</span>
                          <span class="comment-time">{{ fmt(c.created_at) }}</span>
                          <div v-if="c.event_type !== 'created'" class="comment-content">{{ commentContent(c) }}</div>
                        </div>
                        <div v-if="!(commentsMap[b.id] || []).length" class="muted">暂无流转记录</div>
                      </div>
                      <div class="form-row" style="margin-top:10px">
                        <input v-model="commentDraft[b.id]" placeholder="添加评论/流转说明" style="flex:1" @keyup.enter="addComment(b)" />
                        <button class="btn btn-small" @click="addComment(b)">提交</button>
                      </div>
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      </div>
      <p v-if="!bugs.length" class="muted" style="margin-top:10px">暂无缺陷，点击「新增缺陷」提交。</p>
    </div>

    <!-- 新增缺陷 -->
    <div class="modal-mask" v-if="showCreate">
      <div class="modal">
        <h3>新增缺陷</h3>
        <div class="field"><label>标题 *</label><input v-model="form.title" /></div>
        <div class="field"><label>描述</label><textarea v-model="form.description"></textarea></div>
        <div class="field"><label>复现步骤</label>
          <div v-for="(s, i) in stepsArr" :key="i" class="step-row">
            <span class="muted">{{ i + 1 }}</span>
            <input v-model="s.action" placeholder="操作步骤" style="flex:2" />
            <input v-model="s.expected" placeholder="预期结果" style="flex:1.5" />
            <input v-model="s.actual" placeholder="实际" style="flex:1.5" />
            <button class="btn btn-small btn-gray" @click="stepsArr.splice(i, 1)">✕</button>
          </div>
          <button class="btn btn-small" style="margin-top:6px" @click="stepsArr.push({ step_no: stepsArr.length + 1, action: '', expected: '', actual: '' })">+ 添加步骤</button>
        </div>
        <div class="field"><label>严重程度</label>
          <select v-model="form.severity"><option v-for="(t, k) in sevText" :key="k" :value="k">{{ t }}</option></select>
        </div>
        <div class="field"><label>优先级</label>
          <select v-model="form.priority"><option>P0</option><option>P1</option><option>P2</option><option>P3</option></select>
        </div>
        <div class="field"><label>出现概率</label>
          <select v-model="form.probability"><option v-for="(t, k) in probText" :key="k" :value="k">{{ t }}</option></select>
        </div>
        <div class="field"><label>负责人</label><input v-model="form.assignee" /></div>
        <div class="actions">
          <button class="btn btn-gray" @click="showCreate = false">取消</button>
          <button class="btn" @click="create">保存</button>
        </div>
      </div>
    </div>

    <!-- 编辑缺陷（仅 待修复 / 重新打开 状态） -->
    <div class="modal-mask" v-if="showEdit">
      <div class="modal">
        <h3>编辑缺陷 #{{ editForm.id }}</h3>
        <div class="field"><label>标题 *</label><input v-model="editForm.title" /></div>
        <div class="field"><label>描述</label><textarea v-model="editForm.description"></textarea></div>
        <div class="field"><label>复现步骤</label>
          <div v-for="(s, i) in stepsArr" :key="i" class="step-row">
            <span class="muted">{{ i + 1 }}</span>
            <input v-model="s.action" placeholder="操作步骤" style="flex:2" />
            <input v-model="s.expected" placeholder="预期结果" style="flex:1.5" />
            <input v-model="s.actual" placeholder="实际" style="flex:1.5" />
            <button class="btn btn-small btn-gray" @click="stepsArr.splice(i, 1)">✕</button>
          </div>
          <button class="btn btn-small" style="margin-top:6px" @click="stepsArr.push({ step_no: stepsArr.length + 1, action: '', expected: '', actual: '' })">+ 添加步骤</button>
        </div>
        <div class="field"><label>严重程度</label>
          <select v-model="editForm.severity"><option v-for="(t, k) in sevText" :key="k" :value="k">{{ t }}</option></select>
        </div>
        <div class="field"><label>优先级</label>
          <select v-model="editForm.priority"><option>P0</option><option>P1</option><option>P2</option><option>P3</option></select>
        </div>
        <div class="field"><label>出现概率</label>
          <select v-model="editForm.probability"><option v-for="(t, k) in probText" :key="k" :value="k">{{ t }}</option></select>
        </div>
        <div class="field"><label>模块</label><input v-model="editForm.module" /></div>
        <div class="field"><label>环境</label><input v-model="editForm.environment" /></div>
        <div class="field"><label>版本</label><input v-model="editForm.version" /></div>
        <div class="field"><label>负责人</label><input v-model="editForm.assignee" /></div>
        <div class="actions">
          <button class="btn btn-gray" @click="showEdit = false">取消</button>
          <button class="btn" @click="saveEdit">保存</button>
        </div>
      </div>
    </div>
    <!-- 附件预览：当前页面内展示，支持 word/pdf/ppt/excel/mp4/txt 等 -->
    <AttachmentPreview :url="preview?.url" :name="preview?.name" :visible="!!preview" @close="preview = null" />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import AttachmentPreview from '../components/AttachmentPreview.vue'
import ProjectSelect from '../components/ProjectSelect.vue'
import { bugApi } from '../api'

const bugs = ref([])
const expandedId = ref(null)
const commentsMap = ref({})
const commentDraft = ref({})
const preview = ref(null)
const showCreate = ref(false)
const showEdit = ref(false)
const editForm = ref({})
const stepsArr = ref([])
const filter = ref({ keyword: '', status: '', severity: '' })
const form = ref({ title: '', description: '', steps: '', severity: 'major', priority: 'P1', probability: 'always', assignee: '' })
const sevText = { critical: '致命', major: '严重', minor: '一般', trivial: '轻微' }
const probText = { always: '必现', occasional: '偶现', multiple: '多次出现', unreproducible: '无法复现' }
// 缺陷状态（图1）：待修复 / 修复中 / 已修复 / 验证通过 / 无法修复 / 暂不修复 / 设计如此 / 重新打开
const statusText = {
  to_fix: '待修复', fixing: '修复中', fixed: '已修复', verified: '验证通过',
  cant_fix: '无法修复', wont_fix: '暂不修复', by_design: '设计如此', reopen: '重新打开'
}
const sevTag = (s) => ({ critical: 'tag-red', major: 'tag-orange', minor: 'tag-blue', trivial: 'tag-gray' }[s] || 'tag-gray')
const prioTag = (p) => ({ P0: 'tag-red', P1: 'tag-orange', P2: 'tag-blue', P3: 'tag-gray' }[p] || 'tag-gray')
const statusTag = (s) => ({
  to_fix: 'tag-orange', fixing: 'tag-blue', fixed: 'tag-purple', verified: 'tag-green',
  cant_fix: 'tag-gray', wont_fix: 'tag-yellow', by_design: 'tag-gray', reopen: 'tag-red'
}[s] || 'tag-gray')
// 字体颜色：按严重程度/优先级/概率/状态值区分（参考对应选项背景色）
const sevColor = (s) => ({ critical: '#dc2626', major: '#ea580c', minor: '#2563eb', trivial: '#16a34a' }[s] || '#334155')
const prioColor = (p) => ({ P0: '#dc2626', P1: '#ea580c', P2: '#2563eb', P3: '#16a34a' }[p] || '#334155')
const probColor = (p) => ({ always: '#dc2626', occasional: '#ea580c', multiple: '#2563eb', unreproducible: '#16a34a' }[p] || '#334155')
const statusColor = (s) => ({
  to_fix: '#ea580c', fixing: '#2563eb', fixed: '#7c3aed', verified: '#059669',
  cant_fix: '#64748b', wont_fix: '#b45309', by_design: '#64748b', reopen: '#dc2626'
}[s] || '#334155')
const projectId = () => localStorage.getItem('twb_project') || undefined
const fmt = (d) => (d ? String(d).replace('T', ' ').slice(0, 19) : '—')
// 流转事件类型：创建 / 状态变更 / 评论
const eventText = { created: '创建缺陷', status: '状态变更', comment: '评论' }
const eventTag = (t) => ({ created: 'ev-created', status: 'ev-status', comment: 'ev-comment' }[t] || 'ev-comment')
// 内容去重：状态变更不再重复"状态变更："前缀，创建缺陷无需内容（标签已表达）
const commentContent = (c) => {
  if (c.event_type === 'status') return String(c.content || '').replace(/^状态变更[:：]?/, '')
  return c.content || ''
}
// 仅「待修复 / 重新打开」状态可编辑已提交内容
const canEdit = (b) => b && (b.status === 'to_fix' || b.status === 'reopen')
// 复现步骤解析为表格结构（兼容 "1. 操作（预期：xxx）（实际：yyy）" / "1. 操作（预期：xxx）" / "1. 操作" 及自由文本）
function parseSteps(steps) {
  if (!steps) return []
  const lines = String(steps).split('\n').map((s) => s.trim()).filter(Boolean)
  return lines.map((line, idx) => {
    const m = line.match(/^(\d+)[.、]\s*(.+?)(?:[（(]预期[:：]\s*(.+?)[）)])?(?:[（(]实际[:：]\s*(.+?)[）)])?$/)
    if (m) return { step_no: m[1], action: m[2].trim(), expected: (m[3] || '').trim(), actual: (m[4] || '').trim() }
    return { step_no: idx + 1, action: line, expected: '', actual: '' }
  })
}
function stepsToText(arr) {
  return arr.filter((s) => s.action || s.expected || s.actual)
    .map((s, i) => `${i + 1}. ${s.action || ''}（预期：${s.expected || ''}）（实际：${s.actual || ''}）`).join('\n')
}
function stepsToArr(text) {
  return parseSteps(text).map((s) => ({ step_no: s.step_no, action: s.action, expected: s.expected, actual: s.actual }))
}

// ---------- 附件解析与缩略图 ----------
function parseAttachments(att) {
  if (!att) return []
  try {
    const a = JSON.parse(att)
    return (Array.isArray(a) ? a : [att]).map((x) => (typeof x === 'string' ? { url: x, name: x.split('/').pop() } : { url: x.url, name: x.name || x.url.split('/').pop() }))
  } catch {
    return [{ url: att, name: att.split('/').pop() }]
  }
}
const attachments = (b) => (b ? parseAttachments(b.attachments) : [])
const isImage = (url) => /\.(png|jpe?g|gif|webp|bmp|svg)(\?|#|$)/i.test(url || '')
// 文件类型缩略图：word/doc/xls/ppt/txt/md 专属，其他通用"其他"
const fileKind = (name) => {
  const ext = (name || '').split('.').pop().toLowerCase()
  if (['doc', 'docx'].includes(ext)) return 'word'
  if (['xls', 'xlsx', 'csv'].includes(ext)) return 'excel'
  if (['ppt', 'pptx'].includes(ext)) return 'ppt'
  if (ext === 'txt') return 'txt'
  if (ext === 'md') return 'md'
  if (['pdf'].includes(ext)) return 'pdf'
  return 'other'
}
const fileLabel = (name) => {
  const kind = fileKind(name)
  return { word: 'DOC', excel: 'XLS', ppt: 'PPT', txt: 'TXT', md: 'MD', pdf: 'PDF', other: 'FILE' }[kind] || 'FILE'
}
function previewAttachment(u) {
  preview.value = { url: u.url, name: u.name }
}

async function load() {
  const { data } = await bugApi.list({ project_id: projectId(), status: filter.value.status || undefined, severity: filter.value.severity || undefined })
  bugs.value = data.filter((b) => !filter.value.keyword || b.title.includes(filter.value.keyword))
}
async function toggleDetail(b) {
  expandedId.value = expandedId.value === b.id ? null : b.id
  if (expandedId.value === b.id && !commentsMap.value[b.id]) {
    const { data } = await bugApi.comments(b.id)
    commentsMap.value = { ...commentsMap.value, [b.id]: data }
  }
}
async function loadComments(b) {
  const { data } = await bugApi.comments(b.id)
  commentsMap.value = { ...commentsMap.value, [b.id]: data }
}
async function updateStatus(b) {
  await updateField(b, 'status', b.status)
}
// 行内直接修改字段（仅可编辑状态显示下拉）
async function updateField(b, field, value) {
  try {
    await bugApi.update(b.id, { [field]: value })
    b[field] = value
    if (field === 'status') {
      window.$toast.success('状态已更新为「' + statusText[value] + '」')
      // 状态流转后刷新流转记录
      const { data } = await bugApi.comments(b.id)
      commentsMap.value = { ...commentsMap.value, [b.id]: data }
    } else {
      window.$toast.success('已更新')
    }
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '更新失败')
  }
}
function openCreate() {
  if (!projectId()) return window.$toast.warning('请先在上方选择项目')
  stepsArr.value = []
  showCreate.value = true
}
async function create() {
  if (!form.value.title) return window.$toast.warning('请填写缺陷标题')
  const u = JSON.parse(localStorage.getItem('twb_user') || '{}')
  form.value.steps = stepsToText(stepsArr.value)
  await bugApi.create({ project_id: Number(projectId()), ...form.value, reporter: u.display_name || u.username || 'admin' })
  showCreate.value = false
  form.value = { title: '', description: '', steps: '', severity: 'major', priority: 'P1', probability: 'always', assignee: '' }
  stepsArr.value = []
  window.$toast.success('缺陷已创建')
  load()
}
function openEdit(b) {
  editForm.value = { id: b.id, title: b.title, description: b.description, steps: b.steps, severity: b.severity, priority: b.priority, probability: b.probability, module: b.module, environment: b.environment, version: b.version, assignee: b.assignee }
  stepsArr.value = stepsToArr(editForm.value.steps)
  showEdit.value = true
}
async function saveEdit() {
  if (!editForm.value.title) return window.$toast.warning('请填写缺陷标题')
  try {
    editForm.value.steps = stepsToText(stepsArr.value)
    await bugApi.update(editForm.value.id, {
      title: editForm.value.title, description: editForm.value.description, steps: editForm.value.steps,
      severity: editForm.value.severity, priority: editForm.value.priority, probability: editForm.value.probability,
      module: editForm.value.module, environment: editForm.value.environment, version: editForm.value.version, assignee: editForm.value.assignee
    })
    showEdit.value = false
    window.$toast.success('缺陷已更新')
    load()
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '更新失败')
  }
}
async function addComment(b) {
  const content = commentDraft.value[b.id]
  if (!content) return window.$toast.warning('请输入评论内容')
  await bugApi.addComment(b.id, { user: JSON.parse(localStorage.getItem('twb_user') || '{}').display_name || '', content })
  commentDraft.value[b.id] = ''
  await loadComments(b)
}
async function remove(b) {
  if (!(await window.$confirm('确认删除缺陷「' + b.title + '」？', { danger: true }))) return
  await bugApi.remove(b.id); window.$toast.success('已删除'); load()
}
onMounted(load)
watch(() => localStorage.getItem('twb_project'), load)
</script>

<style scoped>
.comment { font-size: 13px; padding: 6px 0; border-bottom: 1px dashed #eef1f4; }
.comment-scroll { max-height: 152px; overflow-y: auto; }
.step-row { display: flex; gap: 8px; align-items: center; margin-bottom: 6px; }
.step-row input { padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
.table-wrap { overflow-x: auto; }
.bug-table { table-layout: fixed; min-width: 900px; }
.bug-table td { overflow: hidden; text-overflow: ellipsis; }
.cell-clamp { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; word-break: break-all; }
.cell-select { width: 100%; padding: 3px 4px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 12px; background: #fff; cursor: pointer; }
.cell-select:focus { outline: none; border-color: #2563eb; }
.cell-select option { color: #1f2329; background: #fff; }
.event-tag { display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: 12px; margin-right: 6px; }
.ev-created { background: #ecfdf5; color: #059669; }
.ev-status { background: #eff6ff; color: #2563eb; }
.ev-comment { background: #f1f5f9; color: #64748b; }
.comment-time { color: #94a3b8; font-size: 12px; margin-left: 6px; }
.comment-content { margin-top: 2px; color: #475569; }
h4 { font-size: 14px; }
.row-active { background: #f0f7ff !important; }
.detail-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; }
.detail-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; margin-bottom: 6px; }
.detail-meta { display: flex; flex-wrap: wrap; gap: 16px; font-size: 12px; color: #64748b; flex: 1; }
.detail-status { flex-shrink: 0; text-align: right; }
.detail-status label { font-size: 12px; color: #64748b; margin-right: 8px; }
.detail-status select { padding: 4px 8px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 13px; }
.detail-status select option { color: #1f2329; background: #fff; }
.detail-title { font-size: 13px; font-weight: 600; color: #334155; margin: 8px 0 4px; }
.detail-content { font-size: 13px; color: #475569; margin: 0; }
.detail-bottom { display: flex; gap: 20px; margin-top: 12px; padding-top: 12px; border-top: 1px solid #e2e8f0; }
.detail-left { flex: 1; min-width: 0; }
.detail-right { flex: 1; min-width: 0; border-left: 1px solid #e2e8f0; padding-left: 20px; }
.bug-attach-grid { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 6px; }
.bug-attach-tile { width: 140px; }
.bug-thumb { width: 100%; height: 110px; border-radius: 6px; overflow: hidden; border: 1px solid #e2e8f0; background: #fff; cursor: pointer; }
.img-thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
.file-icon {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 18px; letter-spacing: 1px;
}
.fic-word { background: #eef2ff; color: #4f46e5; }
.fic-excel { background: #ecfdf5; color: #059669; }
.fic-ppt { background: #fff7ed; color: #ea580c; }
.fic-txt { background: #f8fafc; color: #64748b; }
.fic-md { background: #f0f9ff; color: #0284c7; }
.fic-pdf { background: #fef2f2; color: #dc2626; }
.fic-other { background: #f1f5f9; color: #94a3b8; }
.bug-attach-name { font-size: 12px; color: #374151; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.preview-body { text-align: center; }
.preview-img { max-width: 100%; max-height: 60vh; border-radius: 6px; }
</style>
