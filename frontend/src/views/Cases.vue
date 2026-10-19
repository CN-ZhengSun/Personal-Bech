<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin:4px 0 12px">
      <h1 style="margin:0">测试用例</h1>
      <ProjectSelect />
    </div>
    <div class="card">
      <div class="form-row">
        <input v-model="filter.title" placeholder="搜索用例标题" style="flex:1" @input="applyFilter" />
        <FilterSelect :options="caseModules" v-model="filter.module"
          @update:modelValue="applyFilter" @update:search="(v)=>{filter.moduleKw=v; applyFilter()}"
          placeholder="全部模块" />
        <select v-model="filter.priority" @change="applyFilter" style="width:100px">
          <option value="">全部优先级</option><option>P0</option><option>P1</option><option>P2</option><option>P3</option>
        </select>
        <select v-model="filter.case_type" @change="applyFilter" style="width:100px">
          <option value="">全部类型</option>
          <option v-for="(t, k) in typeText" :key="k" :value="k">{{ t }}</option>
        </select>
        <button class="btn" style="background:#059669;color:#fff;border:none" @click="batchExecute">批量执行({{ selectedIds.length }})</button>
        <button class="btn btn-danger" @click="batchRemove">批量删除({{ selectedIds.length }})</button>
        <label class="btn" style="background:#eef2f7;color:#1f2329;cursor:pointer">导入用例<input type="file" accept=".xls,.xlsx,.csv" style="display:none" @change="onImportCase" /></label>
        <button class="btn" style="background:#eef2f7;color:#1f2329" @click="downloadTemplate">下载模板</button>
        <button class="btn" @click="openCreate">新增用例</button>
      </div>
      <div class="table-wrap">
      <table class="table" style="min-width:1050px">
        <thead><tr>
          <th style="width:34px"><input type="checkbox" :checked="allSelected" @change="toggleAll" /></th>
          <th>ID</th><th style="width:25em">标题</th><th>模块</th><th>优先级</th><th>类型</th><th>状态</th><th>环境</th><th>版本</th><th>操作</th>
        </tr></thead>
        <tbody>
          <template v-for="c in pagedCases" :key="c.id">
            <tr :class="{ 'row-open': expanded === c.id }" @click="toggleDetail(c)">
              <td @click.stop><input type="checkbox" :value="c.id" v-model="selectedIds" /></td>
              <td>{{ c.id }}</td>
              <td style="width:25em"><div class="case-title">{{ c.title }}</div></td>
              <td>{{ c.module || '—' }}</td>
              <td><span class="tag" :class="prioTag(c.priority)">{{ c.priority }}</span></td>
              <td>{{ typeText[c.case_type] || c.case_type }}</td>
              <td><span class="tag" :class="c.status === 'active' ? 'tag-green' : 'tag-gray'">{{ c.status === 'active' ? '启用' : '废弃' }}</span></td>
              <td>{{ c.environment || '—' }}</td>
              <td>{{ c.version || '—' }}</td>
              <td @click.stop style="white-space:nowrap">
                <button class="btn btn-small" style="background:#059669;color:#fff;border:none" @click="goExecute(c)">去执行</button>
                <button class="btn btn-small" style="background:#2563eb;color:#fff;border:none" @click="openEdit(c)">编辑</button>
                <button class="btn btn-small btn-danger" @click="remove(c)">删除</button>
              </td>
            </tr>
            <tr v-if="expanded === c.id" class="detail-row">
              <td colspan="10">
                                <div class="detail-box">
                  <div class="detail-cols">
                    <div class="detail-info">
                      <div class="detail-grid2">
                        <div class="f-title"><span class="lbl">标题</span><div class="detail-title">{{ c.title }}</div></div>
                        <div><span class="lbl">级别</span><span class="fv">{{ c.priority }}</span></div>
                        <div><span class="lbl">模块</span><span class="fv">{{ c.module || '—' }}</span></div>
                        <div><span class="lbl">状态</span><span class="fv">{{ c.status === 'active' ? '启用' : '废弃' }}</span></div>
                        <div><span class="lbl">类型</span><span class="fv">{{ typeText[c.case_type] || c.case_type }}</span></div>
                        <div><span class="lbl">版本</span><span class="fv">{{ c.version || '—' }}</span></div>
                        <div><span class="lbl">环境</span><span class="fv">{{ c.environment || '—' }}</span></div>
                      </div>
                      <p class="lbl" style="margin-top:12px">前置条件</p>
                      <div class="detail-expected">{{ c.preconditions || '—' }}</div>
                    </div>
                    <div class="detail-steps">
                      <p class="lbl" style="margin-bottom:6px">用例步骤</p>
                      <table class="table">
                        <thead><tr><th style="width:48px">#</th><th>操作步骤</th></tr></thead>
                        <tbody>
                          <tr v-for="s in (c.steps || [])" :key="s.id || s.step_no">
                            <td>{{ s.step_no }}</td><td>{{ s.action }}</td>
                          </tr>
                        </tbody>
                      </table>
                      <p v-if="!c.steps?.length" class="muted" style="margin-top:6px">无步骤</p>
                      <p class="lbl" style="margin-top:12px">预期结果</p>
                      <div class="detail-expected">{{ c.expected || '—' }}</div>
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      </div>
      <div class="pager" v-if="cases.length">
        <span class="pager-info">共 {{ cases.length }} 条</span>
        <button class="btn btn-small btn-gray" :disabled="currentPage <= 1" @click="goto(-1, cases)">上一页</button>
        <span class="pager-page">{{ currentPage }} / {{ pageCount(cases) }}</span>
        <button class="btn btn-small btn-gray" :disabled="currentPage >= pageCount(cases)" @click="goto(1, cases)">下一页</button>
        <select v-model="pageSize" class="pager-size" @change="currentPage = 1">
          <option :value="10">10条/页</option>
          <option :value="20">20条/页</option>
          <option :value="50">50条/页</option>
          <option :value="100">100条/页</option>
        </select>
      </div>
      <p v-if="!cases.length" class="muted" style="margin-top:10px">暂无测试用例，点击「新增用例」创建。</p>
    </div>

    <!-- 新增/编辑用例弹窗 -->
    <div class="modal-mask" v-if="showCreate">
      <div class="modal modal-lg">
        <h3>{{ editId ? '编辑用例' : '新增用例' }}</h3>
        <div class="field"><label>标题 *</label><input v-model="form.title" /></div>
        <div class="field"><label>所属模块</label><input v-model="form.module" /></div>
        <div class="field-row">
          <div class="field"><label>优先级</label><select v-model="form.priority"><option>P0</option><option>P1</option><option>P2</option><option>P3</option></select></div>
          <div class="field"><label>类型</label><select v-model="form.case_type"><option v-for="(t, k) in typeText" :key="k" :value="k">{{ t }}</option></select></div>
          <div class="field"><label>状态</label><select v-model="form.status"><option value="active">启用</option><option value="deprecated">废弃</option></select></div>
        </div>
        <div class="field-row">
          <div class="field"><label>环境</label><select v-model="form.environment"><option value="">选择环境</option><option value="dev">开发环境</option><option value="test">测试环境</option><option value="staging">预发布</option><option value="prod">生产环境</option></select></div>
          <div class="field"><label>版本</label>
            <input list="version-options" v-model="form.version" placeholder="选择或输入版本" />
            <datalist id="version-options"><option v-for="v in versions" :key="v" :value="v" /></datalist>
          </div>
        </div>
        <div class="field"><label>前置条件</label><textarea v-model="form.preconditions"></textarea></div>
        <div class="field"><label>用例步骤</label>
          <div v-for="(s, i) in steps" :key="i" class="step-row">
            <span class="muted">{{ i + 1 }}</span>
            <input v-model="s.action" placeholder="操作步骤" style="flex:1" />
            <button class="btn btn-small btn-gray" @click="steps.splice(i, 1)">✕</button>
          </div>
          <button class="btn btn-small" @click="steps.push({ step_no: steps.length + 1, action: '', expected: '' })">+ 添加步骤</button>
        </div>
        <div class="field"><label>预期结果（最终结果）</label><textarea v-model="form.expected" rows="3"></textarea></div>
        <div class="actions">
          <button class="btn btn-gray" @click="closeCreate">取消</button>
          <button class="btn" @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { caseApi, executionApi } from '../api'
import FilterSelect from '../components/FilterSelect.vue'
import ProjectSelect from '../components/ProjectSelect.vue'

const router = useRouter()
const allCases = ref([])
const cases = ref([])
const expanded = ref(null)
const showCreate = ref(false)
const editId = ref(null)
const selectedIds = ref([])
const form = ref({ title: '', module: '', priority: 'P1', case_type: 'functional', status: 'active', environment: '', version: '', preconditions: '', expected: '' })
const steps = ref([])
const filter = ref({ title: '', module: '', moduleKw: '', priority: '', case_type: '' })
const currentPage = ref(1)
const pageSize = ref(10)
const pagedCases = computed(() => cases.value.slice((currentPage.value - 1) * pageSize.value, currentPage.value * pageSize.value))
// 沿用上一次新增数据（页面刷新后重置）
const lastForm = { module: '', priority: 'P1', case_type: 'functional', status: 'active', environment: '', version: '' }
const typeText = { functional: '功能', ui: 'UI', api: '接口', performance: '性能', other: '其他' }
const prioTag = (p) => ({ P0: 'tag-red', P1: 'tag-orange', P2: 'tag-blue', P3: 'tag-gray' }[p] || 'tag-gray')
const versions = computed(() => [...new Set(allCases.value.map((c) => c.version).filter(Boolean))])
const caseModules = computed(() => [...new Set(allCases.value.map((c) => c.module).filter(Boolean))])
const allSelected = computed(() => cases.value.length > 0 && cases.value.every((c) => selectedIds.value.includes(c.id)))
const projectId = () => localStorage.getItem('twb_project') || undefined
const currentUser = () => { try { return JSON.parse(localStorage.getItem('twb_user') || '{}') } catch { return {} } }

async function load() {
  const pid = projectId()
  const { data } = await caseApi.list(pid)
  allCases.value = data
  applyFilter()
}
function applyFilter() {
  const { title, module, moduleKw, priority, case_type } = filter.value
  cases.value = allCases.value.filter((c) =>
    (!title || c.title.includes(title)) &&
    (!module || c.module === module) &&
    (!moduleKw || (c.module || '').toLowerCase().includes(moduleKw.toLowerCase())) &&
    (!priority || c.priority === priority) &&
    (!case_type || c.case_type === case_type)
  )
  currentPage.value = 1
  selectedIds.value = selectedIds.value.filter((id) => cases.value.some((c) => c.id === id))
}
function pageCount(list) { return Math.max(1, Math.ceil(list.length / pageSize.value)) }
function goto(delta, list) {
  currentPage.value = Math.min(Math.max(1, currentPage.value + delta), pageCount(list))
}
function toggleAll(ev) {
  selectedIds.value = ev.target.checked ? cases.value.map((c) => c.id) : []
}
function toggleDetail(c) {
  if (expanded.value === c.id) { expanded.value = null; return }
  expanded.value = c.id
  if (!c.steps) caseApi.detail(c.id).then(({ data }) => Object.assign(c, data))
}
function openCreate() {
  if (!projectId()) return window.$toast.warning('请先在上方选择项目')
  editId.value = null
  form.value = { title: '', module: lastForm.module, priority: lastForm.priority, case_type: lastForm.case_type, status: lastForm.status, environment: lastForm.environment, version: lastForm.version, preconditions: '', expected: '' }
  steps.value = [{ step_no: 1, action: '', expected: '' }]
  showCreate.value = true
}
async function openEdit(c) {
  const { data } = await caseApi.detail(c.id)
  editId.value = c.id
  form.value = { title: data.title, module: data.module || '', priority: data.priority, case_type: data.case_type, status: data.status || 'active', environment: data.environment || '', version: data.version || '', preconditions: data.preconditions || '', expected: data.expected || '' }
  steps.value = (data.steps || []).map((s) => ({ step_no: s.step_no, action: s.action, expected: s.expected }))
  if (!steps.value.length) steps.value = [{ step_no: 1, action: '', expected: '' }]
  showCreate.value = true
}
function closeCreate() { showCreate.value = false; editId.value = null }
async function save() {
  if (!form.value.title) return window.$toast.warning('请填写用例标题')
  const payload = {
    project_id: Number(projectId()), title: form.value.title, module: form.value.module,
    priority: form.value.priority, case_type: form.value.case_type,
    status: form.value.status, environment: form.value.environment || null, version: form.value.version || null,
    preconditions: form.value.preconditions, expected: form.value.expected, steps: steps.value
  }
  if (editId.value) {
    await caseApi.update(editId.value, { ...payload, steps: steps.value })
    window.$toast.success('用例已更新')
  } else {
    await caseApi.create(payload)
    window.$toast.success('测试用例已创建')
    // 记忆本次数据，供下次新增沿用
    Object.assign(lastForm, { module: form.value.module, priority: form.value.priority, case_type: form.value.case_type, status: form.value.status, environment: form.value.environment, version: form.value.version })
  }
  closeCreate()
  load()
}
// 导入用例（xls/xlsx/csv）
async function onImportCase(ev) {
  const file = ev.target.files[0]
  ev.target.value = ''
  if (!file) return
  if (!projectId()) return window.$toast.warning('请先在上方选择项目')
  try {
    const { data } = await caseApi.importCases(projectId(), file)
    let msg = `导入 ${data.imported} 条`
    if (data.skipped) msg += `，跳过 ${data.skipped} 条`
    if (data.errors?.length) msg += `，错误 ${data.errors.length} 条`
    window.$toast[data.imported ? 'success' : 'error'](msg)
    if (data.errors?.length) console.warn('用例导入错误:', data.errors)
    load()
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '导入失败')
  }
}
async function downloadTemplate() {
  try {
    const res = await fetch(caseApi.templateUrl(), { credentials: 'same-origin' })
    const blob = await res.blob()
    const a = document.createElement('a')
    const objUrl = URL.createObjectURL(blob)
    a.href = objUrl
    const cd = res.headers.get('Content-Disposition') || ''
    const m = cd.match(/filename\*=UTF-8''([^;]+)/)
    a.download = m ? decodeURIComponent(m[1]) : '用例导入模板.xlsx'
    document.body.appendChild(a); a.click(); a.remove()
    URL.revokeObjectURL(objUrl)
  } catch (err) { window.$toast.error('模板下载失败') }
}
// 去执行：将用例加入测试执行（执行人=当前用户）
async function goExecute(c) {
  if (!projectId()) return window.$toast.warning('请先在上方选择项目')
  try {
    const u = currentUser()
    await executionApi.create({ case_id: c.id, assignee: u.username || u.display_name || '', status: 'untested' })
    window.$toast.success('已添加「' + c.title + '」到测试执行')
    router.push('/executions')
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '添加执行失败')
  }
}
// 批量执行：勾选用例全部加入测试执行
async function batchExecute() {
  if (!projectId()) return window.$toast.warning('请先在上方选择项目')
  if (!selectedIds.value.length) return window.$toast.warning('请先勾选用例')
  try {
    const u = currentUser()
    await executionApi.batch({ case_ids: selectedIds.value, assignee: u.username || u.display_name || '' })
    window.$toast.success(`已将 ${selectedIds.value.length} 条用例加入测试执行`)
    selectedIds.value = []
    router.push('/executions')
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '批量执行失败')
  }
}
// 批量删除勾选用例
async function batchRemove() {
  if (!selectedIds.value.length) return window.$toast.warning('请先勾选用例')
  if (!(await window.$confirm(`确认删除选中的 ${selectedIds.value.length} 条用例？`, { danger: true }))) return
  try {
    await Promise.all(selectedIds.value.map((id) => caseApi.remove(id)))
    window.$toast.success(`已删除 ${selectedIds.value.length} 条用例`)
    selectedIds.value = []
    load()
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '批量删除失败')
  }
}
async function remove(c) {
  if (!(await window.$confirm('确认删除用例「' + c.title + '」？', { danger: true }))) return
  await caseApi.remove(c.id); window.$toast.success('已删除'); load()
}
onMounted(load)
watch(() => localStorage.getItem('twb_project'), load)
</script>

<style scoped>
.step-row { display: flex; gap: 6px; margin-bottom: 6px; align-items: center; }
.step-row input { padding: 6px 8px; border: 1px solid #d0d7de; border-radius: 6px; font-size: 13px; }
h3 { font-size: 15px; }
.row-open { background: #f0f7ff; }
.detail-row td { background: #f8fafc; }
.detail-box { padding: 6px 2px; }
.detail-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 8px; }
.detail-grid .lbl { margin-right: 6px; }
.detail-expected { background: #fff; border: 1px solid #e5e7eb; border-radius: 6px; padding: 8px 10px; white-space: pre-wrap; word-break: break-all; font-size: 13px; }
.detail-cols { display: flex; gap: 18px; align-items: flex-start; }
.detail-info { flex: 1; min-width: 0; }
.detail-steps { flex: 1; min-width: 0; }
.detail-grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; }
.detail-grid2 > div { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.detail-grid2 .f-title { display: block; grid-column: 1 / -1; }
.detail-title { font-size: 16px; font-weight: 600; color: #111827; line-height: 1.4; margin-top: 2px; }
.detail-grid2 .fv { font-size: 13px; color: #374151; word-break: break-all; }

.lbl { color: #6b7280; font-size: 12px; }
.field-row { display: flex; gap: 12px; }
.field-row .field { flex: 1; }

.case-title {
  max-width: 25em;
  line-height: 1.5;
  height: 3em;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  word-break: break-all;
  white-space: normal;
}

.table-wrap { overflow-x: auto; }

.pager { display: flex; align-items: center; gap: 10px; margin-top: 10px; font-size: 13px; color: #475569; }
.pager-info { color: #64748b; }
.pager-page { min-width: 60px; text-align: center; }
.pager-size { width: 100px; font-size: 13px; padding: 5px 6px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; color: #1f2329; }
</style>
