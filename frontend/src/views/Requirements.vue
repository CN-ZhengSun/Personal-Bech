<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin:4px 0 12px">
      <h1 style="margin:0">需求 PRD 管理</h1>
      <ProjectSelect />
    </div>

    <div class="card">
      <div class="form-row">
        <input v-model="prdFilter.title" placeholder="搜索 PRD 标题" style="flex:1" @input="applyPrdFilter" />
        <FilterSelect :options="prdVersions" v-model="prdFilter.version"
          @update:modelValue="applyPrdFilter" @update:search="(v)=>{prdFilter.versionKw=v; applyPrdFilter()}"
          placeholder="全部版本" />
        <button class="btn" @click="openPrdCreate">新增 PRD 文档</button>
      </div>
      <table class="table">
        <thead><tr><th>ID</th><th>标题</th><th>所属模块</th><th>版本</th><th>研发负责人</th><th>附件</th><th>创建时间</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="p in prds" :key="p.id">
            <td>{{ p.id }}</td>
            <td>{{ p.title }}</td>
            <td>{{ p.module || '—' }}</td>
            <td><span class="tag tag-blue">{{ p.version }}</span></td>
            <td>{{ p.owner || '—' }}</td>
            <td>
              <a v-if="prdAttach(p)" class="attach-link" style="cursor:pointer" @click.prevent="previewAtt = prdAttach(p)">{{ prdAttach(p).name }}</a>
              <span v-else class="muted">---</span>
            </td>
            <td class="muted">{{ fmt(p.created_at) }}</td>
            <td>
              <button class="btn btn-small btn-gray" @click="viewPrd(p)">查看</button>
              <button class="btn btn-small btn-danger" @click="removePrd(p)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!prds.length" class="muted" style="margin-top:10px">暂无 PRD 文档，点击「新增 PRD 文档」创建。</p>
    </div>

    <div class="card">
      <h3 style="margin-bottom:10px">需求点（从 PRD 拆分）</h3>
      <div class="form-row">
        <input v-model="reqFilter.title" placeholder="搜索需求标题" style="flex:1" @input="applyReqFilter" />
        <select v-model="reqFilter.priority" @change="applyReqFilter" style="width:110px">
          <option value="">全部优先级</option><option>P0</option><option>P1</option><option>P2</option>
        </select>
        <FilterSelect :options="reqModules" v-model="reqFilter.module"
          @update:modelValue="applyReqFilter" @update:search="(v)=>{reqFilter.moduleKw=v; applyReqFilter()}"
          placeholder="全部模块" />
        <input v-model="reqFilter.owner" placeholder="搜索负责人" style="width:120px" @input="applyReqFilter" />
        <button class="btn" @click="openReqCreate">新增需求</button>
      </div>
      <table class="table">
        <thead><tr><th>ID</th><th>标题</th><th>优先级</th><th>模块</th><th>负责人</th><th>期望上线</th><th>状态</th><th>覆盖</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="r in reqs" :key="r.id">
            <td>{{ r.id }}</td>
            <td>{{ r.title }}</td>
            <td><span class="tag" :class="prioTag(r.priority)">{{ r.priority }}</span></td>
            <td>{{ r.module || '—' }}</td>
            <td>{{ r.owner || '—' }}</td>
            <td>{{ r.target_date || '—' }}</td>
            <td><span class="tag" :class="reqStatusTag(r.status)">{{ reqStatusText[r.status] || r.status }}</span></td>
            <td>{{ r.case_count ?? '' }}</td>
            <td>
              <select v-model="r.status" @change="updateReq(r)">
                <option v-for="(t, k) in reqStatusText" :key="k" :value="k">{{ t }}</option>
              </select>
              <button class="btn btn-small btn-gray" @click="coverage(r)">覆盖</button>
              <button class="btn btn-small btn-danger" @click="removeReq(r)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!reqs.length" class="muted" style="margin-top:10px">暂无需求，点击「新增需求」拆分。</p>
    </div>

    <!-- 新增 PRD 文档弹窗 -->
    <div class="modal-mask" v-if="showPrdCreate">
      <div class="modal">
        <h3>新增 PRD 文档</h3>
        <div class="field"><label>PRD 标题 *</label><input v-model="prdForm.title" /></div>
        <div class="field"><label>所属模块（可不填）</label><input v-model="prdForm.module" /></div>
        <div class="field"><label>版本</label><input v-model="prdForm.version" placeholder="如 v1.0" /></div>
        <div class="field"><label>研发负责人</label><input v-model="prdForm.owner" /></div>
        <div class="field"><label>上传 PRD 文件（≤100M，可不传）</label>
          <div class="form-row">
            <input type="file" id="prd-file" @change="onPrdFile" />
            <span v-if="prdForm.attachment" class="attach-file">{{ prdForm.attachment }}</span>
          </div>
        </div>
        <div class="actions">
          <button class="btn btn-gray" @click="showPrdCreate = false">取消</button>
          <button class="btn" @click="createPrd">保存</button>
        </div>
      </div>
    </div>

    <!-- 新增需求点弹窗 -->
    <div class="modal-mask" v-if="showReqCreate">
      <div class="modal">
        <h3>新增需求</h3>
        <div class="field"><label>需求标题 *</label><input v-model="reqForm.title" /></div>
        <div class="field"><label>所属模块</label><input v-model="reqForm.module" /></div>
        <div class="field"><label>优先级</label>
          <select v-model="reqForm.priority"><option>P0</option><option>P1</option><option>P2</option></select>
        </div>
        <div class="field"><label>负责人</label><input v-model="reqForm.owner" /></div>
        <div class="field"><label>期望上线时间（非必填）</label><input type="date" v-model="reqForm.target_date" /></div>
        <div class="actions">
          <button class="btn btn-gray" @click="showReqCreate = false">取消</button>
          <button class="btn" @click="createReq">保存</button>
        </div>
      </div>
    </div>

    <div class="modal-mask" v-if="prdView">
      <div class="modal">
        <h3>{{ prdView.title }} <span class="muted">{{ prdView.version }}</span></h3>
        <p class="muted">模块：{{ prdView.module || '—' }} · 负责人：{{ prdView.owner || '—' }}</p>
        <pre v-if="prdView.content" class="pre">{{ prdView.content }}</pre>
        <div class="field" v-if="prdAttach(prdView)">
          <label>附件</label>
          <a class="attach-link" style="cursor:pointer" @click.prevent="previewAtt = prdAttach(prdView)">{{ prdAttach(prdView).name }}</a>
        </div>
        <div class="actions"><button class="btn btn-gray" @click="prdView = null">关闭</button></div>
      </div>
    </div>

    <!-- 附件预览：复用通用组件，当前页面内浏览 -->
    <AttachmentPreview :url="previewAtt?.url" :name="previewAtt?.name" :visible="!!previewAtt" @close="previewAtt = null" />
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue'
import { prdApi, requirementApi, uploadApi } from '../api'
import FilterSelect from '../components/FilterSelect.vue'
import ProjectSelect from '../components/ProjectSelect.vue'
import AttachmentPreview from '../components/AttachmentPreview.vue'

const projectId = () => localStorage.getItem('twb_project') || undefined
const allPrds = ref([])
const allReqs = ref([])
const prds = ref([])
const reqs = ref([])
const prdFilter = ref({ title: '', version: '', versionKw: '' })
const reqFilter = ref({ title: '', priority: '', module: '', moduleKw: '', owner: '' })
const prdForm = ref({ title: '', module: '', version: 'v1.0', owner: '', attachment: '' })
const reqForm = ref({ title: '', module: '', priority: 'P1', owner: '', target_date: '' })
const showPrdCreate = ref(false)
const showReqCreate = ref(false)
const prdView = ref(null)
const previewAtt = ref(null)

const reqStatusText = { draft: '草稿', review: '评审中', approved: '已通过', changed: '已变更', done: '已完成' }
const reqStatusTag = (s) => ({ draft: 'tag-gray', review: 'tag-orange', approved: 'tag-green', changed: 'tag-purple', done: 'tag-blue' }[s] || 'tag-gray')
const prioTag = (p) => ({ P0: 'tag-red', P1: 'tag-orange', P2: 'tag-blue' }[p] || 'tag-gray')
const fmt = (d) => (d ? String(d).replace('T', ' ').slice(0, 16) : '—')
const prdVersions = computed(() => [...new Set(allPrds.value.map((p) => p.version).filter(Boolean))])
const reqModules = computed(() => [...new Set(allReqs.value.map((r) => r.module).filter(Boolean))])
const prdAttach = (p) => {
  if (!p.attachment) return null
  try { return JSON.parse(p.attachment) } catch { return { name: p.attachment, url: p.attachment } }
}

async function load() {
  const pid = projectId()
  const [p, r] = await Promise.all([prdApi.list(pid), requirementApi.list(pid)])
  allPrds.value = p.data
  allReqs.value = r.data
  const coverageMap = {}
  await Promise.all(r.data.map(async (x) => {
    try {
      const c = await requirementApi.coverage(x.id)
      coverageMap[x.id] = `${c.data.case_count}用例/${c.data.bug_count}缺陷`
    } catch {}
  }))
  allReqs.value = allReqs.value.map((x) => ({ ...x, case_count: coverageMap[x.id] }))
  applyPrdFilter(); applyReqFilter()
}
// PRD 筛选：标题搜索 + 版本下拉筛选 + 版本关键字搜索
function applyPrdFilter() {
  const { title, version, versionKw } = prdFilter.value
  prds.value = allPrds.value.filter((p) =>
    (!title || p.title.includes(title)) &&
    (!version || p.version === version) &&
    (!versionKw || (p.version || '').toLowerCase().includes(versionKw.toLowerCase()))
  )
}
// 需求点筛选：标题搜索 + 优先级下拉 + 模块关键字/下拉 + 负责人搜索
function applyReqFilter() {
  const { title, priority, module, moduleKw, owner } = reqFilter.value
  reqs.value = allReqs.value.filter((r) =>
    (!title || r.title.includes(title)) &&
    (!priority || r.priority === priority) &&
    (!module || r.module === module) &&
    (!moduleKw || (r.module || '').toLowerCase().includes(moduleKw.toLowerCase())) &&
    (!owner || (r.owner || '').includes(owner))
  )
}

function openPrdCreate() {
  if (!projectId()) return window.$toast.warning('请先在上方选择项目')
  prdForm.value = { title: '', module: '', version: 'v1.0', owner: '', attachment: '' }
  showPrdCreate.value = true
}
async function onPrdFile(ev) {
  const file = ev.target.files?.[0]
  if (!file) return
  if (file.size > 100 * 1024 * 1024) return window.$toast.error('文件超过 100MB 限制')
  try {
    const { data } = await uploadApi.upload(file)
    prdForm.value.attachment = JSON.stringify({ name: file.name, url: data.url })
    window.$toast.success('文件已上传')
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '上传失败')
  }
  ev.target.value = ''
}
async function createPrd() {
  if (!prdForm.value.title) return window.$toast.warning('请填写 PRD 标题')
  await prdApi.create({ project_id: Number(projectId()), title: prdForm.value.title, module: prdForm.value.module || null, version: prdForm.value.version || 'v1.0', owner: prdForm.value.owner || null, attachment: prdForm.value.attachment })
  showPrdCreate.value = false
  window.$toast.success('PRD 文档已创建')
  load()
}
function viewPrd(p) { prdView.value = p }
async function removePrd(p) {
  if (!(await window.$confirm('确认删除 PRD「' + p.title + '」？', { danger: true }))) return
  await prdApi.remove(p.id); window.$toast.success('已删除'); load()
}

function openReqCreate() {
  if (!projectId()) return window.$toast.warning('请先在上方选择项目')
  reqForm.value = { title: '', module: '', priority: 'P1', owner: '', target_date: '' }
  showReqCreate.value = true
}
async function createReq() {
  if (!reqForm.value.title) return window.$toast.warning('请填写需求标题')
  await requirementApi.create({ project_id: Number(projectId()), title: reqForm.value.title, priority: reqForm.value.priority, module: reqForm.value.module || null, owner: reqForm.value.owner || null, target_date: reqForm.value.target_date || null })
  showReqCreate.value = false
  window.$toast.success('需求已创建')
  load()
}
async function updateReq(r) { await requirementApi.update(r.id, { status: r.status }) }
function coverage(r) { window.$toast.info(`需求「${r.title}」关联用例 / 缺陷：${r.case_count || '暂无数据'}`) }
async function removeReq(r) {
  if (!(await window.$confirm('确认删除需求「' + r.title + '」？', { danger: true }))) return
  await requirementApi.remove(r.id); window.$toast.success('已删除'); load()
}

onMounted(load)
watch(() => localStorage.getItem('twb_project'), load)
</script>

<style scoped>
.pre { background: #f8fafc; border-radius: 6px; padding: 12px; white-space: pre-wrap; font-size: 13px; max-height: 50vh; overflow-y: auto; }
h3 { font-size: 15px; }
.attach-link { color: #2563eb; text-decoration: none; }
.attach-link:hover { text-decoration: underline; }
.attach-file { color: #059669; font-size: 13px; margin-left: 8px; }
</style>
