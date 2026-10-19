<template>
  <div>
    <h1>测试计划</h1>
    <div class="card">
      <div class="form-row">
        <input v-model="filter.name" placeholder="搜索计划名称" style="flex:1" @input="applyFilter" />
        <input type="date" v-model="filter.start_date" title="按开始日期筛选" @change="applyFilter" />
        <input type="date" v-model="filter.end_date" title="按结束日期筛选" @change="applyFilter" />
        <button class="btn" @click="openCreate">新增计划</button>
      </div>
      <table class="table">
        <thead><tr><th>ID</th><th>名称</th><th>状态</th><th>周期</th><th>进度(执行/通过率)</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="p in plans" :key="p.id">
            <td>{{ p.id }}</td>
            <td>{{ p.name }}</td>
            <td><span class="tag" :class="planStatusTag(p.status)">{{ planStatusText[p.status] || p.status }}</span></td>
            <td>{{ p.start_date || '—' }} ~ {{ p.end_date || '—' }}</td>
            <td>
              <template v-if="progress[p.id]">
                {{ progress[p.id].total }} 条 / {{ progress[p.id].pass_rate }}%
              </template>
              <span v-else class="muted">—</span>
            </td>
            <td>
              <select v-model="p.status" @change="update(p)">
                <option v-for="(t, k) in planStatusText" :key="k" :value="k">{{ t }}</option>
              </select>
              <button class="btn btn-small btn-gray" @click="viewProgress(p)">进度</button>
              <button class="btn btn-small btn-danger" @click="remove(p)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!plans.length" class="muted" style="margin-top:10px">暂无测试计划，点击「新增计划」创建。</p>
    </div>

    <!-- 新增计划弹窗 -->
    <div class="modal-mask" v-if="showCreate">
      <div class="modal">
        <h3>新增测试计划</h3>
        <div class="field"><label>计划名称 *</label><input v-model="form.name" /></div>
        <div class="field"><label>开始日期</label><input type="date" v-model="form.start_date" /></div>
        <div class="field"><label>结束日期</label><input type="date" v-model="form.end_date" /></div>
        <div class="actions">
          <button class="btn btn-gray" @click="showCreate = false">取消</button>
          <button class="btn" @click="create">保存</button>
        </div>
      </div>
    </div>

    <div class="modal-mask" v-if="view">
      <div class="modal">
        <h3>{{ view.name }} 执行进度</h3>
        <div v-for="(v, k) in (progress[view.id]?.counts || {})" :key="k" class="row">
          <span class="muted" style="width:70px">{{ statusText[k] || k }}</span>
          <div class="bar" style="flex:1"><div :style="{ width: pct(k) + '%' }"></div></div>
          <span>{{ v }}</span>
        </div>
        <div class="actions"><button class="btn btn-gray" @click="view = null">关闭</button></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { planApi } from '../api'

const allPlans = ref([])
const plans = ref([])
const progress = ref({})
const view = ref(null)
const showCreate = ref(false)
const form = ref({ name: '', start_date: '', end_date: '' })
const filter = ref({ name: '', start_date: '', end_date: '' })
const statusText = { pass: '通过', fail: '失败', blocked: '阻塞', skipped: '跳过', untested: '未执行' }
const planStatusText = { draft: '草稿', active: '进行中', done: '已完成' }
const planStatusTag = (s) => ({ draft: 'tag-gray', active: 'tag-blue', done: 'tag-green' }[s] || 'tag-gray')

const projectId = () => localStorage.getItem('twb_project') || undefined

async function load() {
  const pid = projectId()
  const { data } = await planApi.list(pid)
  allPlans.value = data
  applyFilter()
  progress.value = {}
  await Promise.all(allPlans.value.map(async (p) => {
    try {
      const r = await planApi.progress(p.id)
      progress.value[p.id] = r.data
    } catch {}
  }))
}
// 名称 / 开始日期 / 结束日期 均只做筛选
function applyFilter() {
  const { name, start_date, end_date } = filter.value
  plans.value = allPlans.value.filter((p) =>
    (!name || p.name.includes(name)) &&
    (!start_date || (p.start_date || '') === start_date) &&
    (!end_date || (p.end_date || '') === end_date)
  )
}
function openCreate() {
  if (!projectId()) return window.$toast.warning('请先在上方选择项目')
  form.value = { name: '', start_date: '', end_date: '' }
  showCreate.value = true
}
async function create() {
  if (!form.value.name) return window.$toast.warning('请填写计划名称')
  await planApi.create({ project_id: Number(projectId()), name: form.value.name, start_date: form.value.start_date, end_date: form.value.end_date })
  showCreate.value = false
  window.$toast.success('测试计划已创建')
  load()
}
async function update(p) { await planApi.update(p.id, { status: p.status }) }
function viewProgress(p) { view.value = p }
async function remove(p) {
  if (!(await window.$confirm('确认删除测试计划「' + p.name + '」？', { danger: true }))) return
  await planApi.remove(p.id); window.$toast.success('已删除'); load()
}
const pct = (k) => {
  const c = progress.value[view.value?.id]?.counts || {}
  const total = Object.values(c).reduce((a, b) => a + b, 0)
  return total ? Math.round((c[k] || 0) / total * 100) : 0
}
onMounted(load)
watch(() => localStorage.getItem('twb_project'), load)
</script>

<style scoped>
.row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
h3 { font-size: 15px; }
</style>
