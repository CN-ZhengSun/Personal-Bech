<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin:4px 0 12px">
      <h1 style="margin:0">知识库</h1>
      <input v-model="keyword" placeholder="搜索标题 / 标签 / 分类 / 文件内容" style="flex:1" @input="onSearch" />
      <button class="btn" @click="openCreate">新增文档</button>
    </div>

    <!-- 卡片网格 -->
    <div v-if="docs.length" class="kb-grid">
      <div v-for="d in docs" :key="d.id" class="kb-card" @click="view(d)">
        <div class="kb-cover">
          <img v-if="isImage(d)" :src="d.file_url" :alt="d.title" />
          <div v-else class="file-card" :style="{ '--c': fileType(d).bg, '--light': fileType(d).light }">
            <span class="ft-label">{{ fileType(d).label }}</span>
          </div>
          <span class="kb-cat">{{ d.category || '通用' }}</span>
          <button class="kb-del" title="删除" @click.stop="remove(d)">✕</button>
        </div>
        <div class="kb-body">
          <div class="kb-title" :title="d.title">{{ d.title }}</div>
          <div class="kb-meta">
            <span v-if="d.file_name" class="kb-file" :title="d.file_name">{{ d.file_name }}</span>
            <span v-else class="kb-file muted">纯文本</span>
            <span v-if="d.file_size" class="muted">{{ fmtSize(d.file_size) }}</span>
          </div>
          <div class="kb-tags">
            <span v-for="t in tagList(d)" :key="t" class="tag tag-blue" style="font-size:11px">{{ t }}</span>
            <span v-if="!d.tags" class="muted" style="font-size:12px">—</span>
          </div>
          <div class="muted kb-time">{{ fmt(d.updated_at || d.created_at) }}</div>
        </div>
      </div>
    </div>
    <div v-else class="card">
      <p class="muted" style="margin:6px 0">
        {{ keyword ? '未找到匹配的知识文档，换个关键字试试。' : '暂无知识文档，点击「新增文档」沉淀你的学习笔记与项目注意事项。' }}
      </p>
    </div>

    <!-- 新增文档弹窗 -->
    <div class="modal-mask" v-if="showCreate">
      <div class="modal" style="width:520px">
        <h3>新增知识文档</h3>
        <div class="field"><label>标题 *</label><input v-model="form.title" placeholder="文档标题" /></div>
        <div class="field"><label>分类</label><input v-model="form.category" placeholder="如 测试规范 / 项目注意 / 学习笔记" /></div>
        <div class="field"><label>标签（逗号分隔）</label><input v-model="form.tags" placeholder="如 Android,ADB" /></div>
        <div class="field">
          <label>上传文件（txt / docx / xlsx / md / xmind / 图片，≤100M）</label>
          <div class="form-row">
            <input type="file" id="kb-file" accept=".txt,.docx,.xlsx,.xls,.md,.xmind,.png,.jpg,.jpeg,.gif,.webp,.bmp" @change="onFile" />
            <span v-if="form.file_name" class="attach-file">{{ form.file_name }}（{{ fmtSize(form.file_size) }}）</span>
          </div>
          <p class="muted" style="font-size:12px;margin:6px 0 0">选择了文件则以文件内容为准；也可不选文件，直接填写下方内容（纯文本记录）。xmind 暂不支持在线预览，可下载查看。</p>
        </div>
        <div class="field">
          <label>内容（纯文本，未选文件时使用）</label>
          <textarea v-model="form.content" style="min-height:120px" placeholder="或直接记录一段文字…"></textarea>
        </div>
        <div class="actions">
          <button class="btn btn-gray" @click="showCreate = false">取消</button>
          <button class="btn" @click="save">保存</button>
        </div>
      </div>
    </div>

    <!-- 纯文本预览弹窗 -->
    <div class="modal-mask" v-if="textView">
      <div class="modal" style="width:640px">
        <h3>{{ textView.title }}</h3>
        <p class="muted">{{ textView.category }} · {{ textView.tags || '无标签' }}</p>
        <pre class="pre">{{ textView.content || '（无内容）' }}</pre>
        <div class="actions"><button class="btn btn-gray" @click="textView = null">关闭</button></div>
      </div>
    </div>

    <!-- 附件预览：复用通用组件，当前页面内浏览 -->
    <AttachmentPreview :url="preview?.url" :name="preview?.name" :visible="!!preview" @close="preview = null" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { knowledgeApi, uploadApi } from '../api'
import AttachmentPreview from '../components/AttachmentPreview.vue'

const docs = ref([])
const keyword = ref('')
const showCreate = ref(false)
const preview = ref(null)
const textView = ref(null)
const form = ref({ title: '', category: '通用', tags: '', content: '', file_url: '', file_name: '', file_size: 0, file_type: '' })
let searchTimer = null

const IMG_EXT = ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp']
const fmt = (d) => (d ? String(d).replace('T', ' ').slice(0, 16) : '—')
const fmtSize = (n) => {
  if (!n) return ''
  if (n < 1024) return n + 'B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + 'KB'
  return (n / 1024 / 1024).toFixed(1) + 'MB'
}
const tagList = (d) => (d.tags ? d.tags.split(/[,，]/).map((t) => t.trim()).filter(Boolean) : [])
const fileType = (d) => {
  const e = (d.file_type || (d.file_name || '').split('.').pop() || '').toLowerCase()
  const map = {
    pdf: ['PDF', '#dc2626', '#fee2e2'], doc: ['DOC', '#2563eb', '#dbeafe'], docx: ['DOCX', '#2563eb', '#dbeafe'],
    xls: ['XLS', '#16a34a', '#dcfce7'], xlsx: ['XLSX', '#16a34a', '#dcfce7'],
    ppt: ['PPT', '#ea580c', '#ffedd5'], pptx: ['PPTX', '#ea580c', '#ffedd5'],
    txt: ['TXT', '#64748b', '#f1f5f9'], md: ['MD', '#0f766e', '#ccfbf1'], log: ['LOG', '#64748b', '#f1f5f9'],
    xmind: ['XMIND', '#7c3aed', '#ede9fe'],
    mp4: ['MP4', '#7c3aed', '#ede9fe'], mp3: ['MP3', '#7c3aed', '#ede9fe'],
    zip: ['ZIP', '#b45309', '#fef3c7'], rar: ['RAR', '#b45309', '#fef3c7'], '7z': ['7Z', '#b45309', '#fef3c7'],
  }
  const hit = map[e]
  return hit ? { label: hit[0], bg: hit[1], light: hit[2] } : { label: '文件', bg: '#475569', light: '#f1f5f9' }
}
const isImage = (d) => IMG_EXT.includes((d.file_type || '').toLowerCase())

async function load() {
  const { data } = await knowledgeApi.list(keyword.value ? { q: keyword.value } : undefined)
  docs.value = data
}
function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
}
function openCreate() {
  form.value = { title: '', category: '通用', tags: '', content: '', file_url: '', file_name: '', file_size: 0, file_type: '' }
  showCreate.value = true
}
async function onFile(ev) {
  const file = ev.target.files?.[0]
  if (!file) return
  if (file.size > 100 * 1024 * 1024) return window.$toast.error('文件超过 100MB 限制')
  const m = file.name.match(/\.([A-Za-z0-9]+)$/)
  const ext = (m && m[1]) || ''
  if (!['txt', 'docx', 'xlsx', 'xls', 'md', 'xmind', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'].includes(ext.toLowerCase()))
    return window.$toast.error('不支持该文件类型')
  try {
    const { data } = await uploadApi.upload(file, 'knowledge')
    form.value.file_url = data.url
    form.value.file_name = file.name
    form.value.file_size = file.size
    form.value.file_type = ext.toLowerCase()
    window.$toast.success('文件已上传')
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '上传失败')
  }
  ev.target.value = ''
}
async function save() {
  if (!form.value.title) return window.$toast.warning('请填写文档标题')
  const payload = {
    title: form.value.title,
    category: form.value.category || '通用',
    tags: form.value.tags || null,
    visibility: 'global',
    ...(form.value.file_url
      ? { file_url: form.value.file_url, file_name: form.value.file_name, file_size: form.value.file_size, file_type: form.value.file_type }
      : { content: form.value.content || '' }),
  }
  await knowledgeApi.create(payload)
  showCreate.value = false
  window.$toast.success('知识文档已保存')
  load()
}
function view(d) {
  if (d.file_url) {
    preview.value = { url: d.file_url, name: d.file_name || d.title }
  } else {
    textView.value = d
  }
}
async function remove(d) {
  if (!(await window.$confirm('确认删除「' + d.title + '」？关联文件将一并删除。', { danger: true }))) return
  await knowledgeApi.remove(d.id)
  window.$toast.success('已删除')
  load()
}
onMounted(load)
</script>

<style scoped>
.kb-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 14px;
}
.kb-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  cursor: pointer;
  transition: box-shadow .15s, transform .15s;
}
.kb-card:hover { box-shadow: 0 6px 18px rgba(15, 23, 42, .08); transform: translateY(-2px); }
.kb-cover {
  position: relative;
  aspect-ratio: 4 / 2.6;
  background: #f1f5f9;
  overflow: hidden;
}
.kb-cover img { width: 100%; height: 100%; object-fit: cover; display: block; }
.kb-cover .file-card {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--light, #f1f5f9);
  box-sizing: border-box;
}
.file-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 5px;
  background: var(--c, #475569);
}
.ft-label { font-size: 18px; font-weight: 700; letter-spacing: 1px; color: var(--c, #475569); }
.kb-cat {
  position: absolute; left: 8px; bottom: 8px;
  background: rgba(15, 23, 42, .72); color: #fff;
  font-size: 11px; padding: 2px 8px; border-radius: 999px;
}
.kb-del {
  position: absolute; top: 6px; right: 6px;
  width: 22px; height: 22px; line-height: 20px;
  border-radius: 50%; border: none; cursor: pointer;
  background: rgba(15, 23, 42, .55); color: #fff; font-size: 12px;
  opacity: 0; transition: opacity .15s;
}
.kb-card:hover .kb-del { opacity: 1; }
.kb-del:hover { background: #dc2626; }
.kb-body { padding: 10px 12px 12px; }
.kb-title {
  font-size: 14px; font-weight: 600; color: #111827;
  line-height: 1.4; margin-bottom: 6px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.kb-meta { display: flex; justify-content: space-between; gap: 8px; font-size: 12px; margin-bottom: 6px; }
.kb-file { color: #374151; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kb-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 6px; min-height: 18px; }
.kb-time { font-size: 12px; }
.pre {
  background: #f8fafc; border-radius: 6px; padding: 12px;
  white-space: pre-wrap; word-break: break-all; font-size: 13px;
  max-height: 50vh; overflow-y: auto;
}
h3 { font-size: 15px; }
.attach-file { color: #059669; font-size: 13px; }
</style>
