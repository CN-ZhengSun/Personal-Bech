<template>
  <div>
    <h1>项目管理</h1>
    <div class="card">
      <div class="form-row">
        <input v-model="filter.name" placeholder="项目名称搜索" style="width:180px" @input="applyFilter" />
        <input v-model="filter.owner" placeholder="负责人搜索" style="width:140px" @input="applyFilter" />
        <span class="date-label">时间区间：</span>
        <label class="radio-inline"><input type="radio" value="created" v-model="filter.dateType" @change="applyFilter" />创建时间</label>
        <label class="radio-inline"><input type="radio" value="deliver" v-model="filter.dateType" @change="applyFilter" />交付日期</label>
        <input type="date" v-model="filter.startDate" @change="applyFilter" style="width:150px" />
        <span class="date-sep">至</span>
        <input type="date" v-model="filter.endDate" @change="applyFilter" style="width:150px" />
        <button class="btn btn-gray" @click="resetFilter">重置</button>
        <button class="btn" @click="openCreate">新增项目</button>
      </div>
      <table class="table" style="table-layout:fixed">
        <thead><tr><th style="width:55px">ID</th><th style="width:160px">项目名称</th><th style="width:90px">负责人</th><th style="width:90px">状态</th><th style="width:150px">创建时间</th><th style="width:110px">交付时间</th><th style="width:230px">操作</th></tr></thead>
        <tbody>
          <template v-for="p in projects" :key="p.id">
            <tr class="clickable" @click="toggle(p)">
              <td>{{ p.id }}</td>
              <td class="pname" title="点击展开详情"><a href="#" @click.prevent="useProject(p)">{{ p.name }}</a></td>
              <td>{{ p.owner || '—' }}</td>
              <td><span class="tag" :class="statusTag(p.status)">{{ statusText[p.status] || p.status }}</span></td>
              <td>{{ fmtTime(p.created_at) }}</td>
              <td>{{ fmtTime(p.deliver_date) }}</td>
              <td @click.stop style="white-space:nowrap">
                <button class="btn btn-small btn-gray" @click="useProject(p)">设为当前</button>
                <button class="btn btn-small btn-gray op-btn" @click="openEdit(p)">编辑</button>
                <button class="btn btn-small btn-gray op-btn" @click="duplicate(p)">复制</button>
                <button class="btn btn-small btn-danger op-btn" @click="remove(p)">删除</button>
              </td>
            </tr>
            <tr v-if="expanded === p.id" class="detail-row">
              <td colspan="7">
                <div class="detail-grid">
                  <div class="d-item"><span class="d-label">ID</span><span>{{ p.id }}</span></div>
                  <div class="d-item"><span class="d-label">项目名称</span><span>{{ p.name }}</span></div>
                  <div class="d-item"><span class="d-label">负责人</span><span>{{ p.owner || '—' }}</span></div>
                  <div class="d-item"><span class="d-label">状态</span><span><span class="tag" :class="statusTag(p.status)">{{ statusText[p.status] || p.status }}</span></span></div>
                  <div class="d-item"><span class="d-label">交付日期</span><span>{{ p.deliver_date || '—' }}</span></div>
                  <div class="d-item"><span class="d-label">创建时间</span><span>{{ fmtTime(p.created_at) }}</span></div>
                  <div class="d-item"><span class="d-label">更新时间</span><span>{{ fmtTime(p.updated_at) }}</span></div>
                  <div class="d-item d-full"><span class="d-label">项目描述</span><span class="d-desc">{{ p.description || '—' }}</span></div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <p v-if="!projects.length" class="muted" style="margin-top:10px">暂无项目，点击「新增项目」创建。</p>
    </div>

    <!-- 新增/编辑项目弹窗 -->
    <div class="modal-mask" v-if="showCreate">
      <div class="modal">
        <h3>{{ editingId ? '编辑项目' : '新增项目' }}</h3>
        <div class="field"><label>项目名称 *</label><input v-model="form.name" placeholder="请输入项目名称" /></div>
        <div class="field"><label>项目描述</label><textarea v-model="form.description" placeholder="请输入项目描述"></textarea></div>
        <div class="field"><label>负责人</label><input v-model="form.owner" placeholder="请输入负责人" /></div>
        <div class="field"><label>状态</label>
          <select v-model="form.status">
            <option value="draft">草稿</option>
            <option value="researching">调研中</option>
            <option value="approved">已通过</option>
            <option value="delivering">交付中</option>
            <option value="delivered">已交付</option>
          </select>
        </div>
        <div class="field"><label>交付时间</label><input type="datetime-local" v-model="form.deliver_date" /></div>
        <div class="actions">
          <button class="btn btn-gray" @click="showCreate = false">取消</button>
          <button class="btn" @click="editingId ? saveEdit() : create()">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { projectApi } from '../api'

const projects = ref([])
const showCreate = ref(false)
const expanded = ref(null)
const editingId = ref(null)
const form = ref({ name: '', description: '', owner: '', status: 'draft', deliver_date: '' })
const filter = ref({ name: '', owner: '', dateType: 'created', startDate: '', endDate: '' })

const statusText = { draft: '草稿', researching: '调研中', approved: '已通过', delivering: '交付中', delivered: '已交付' }
const statusTag = (s) => ({ draft: 'tag-gray', researching: 'tag-blue', approved: 'tag-green', delivering: 'tag-orange', delivered: 'tag-purple' }[s] || 'tag-gray')

function fmtTime(v) {
  if (!v) return '—'
  return String(v).replace('T', ' ').slice(0, 19)
}
// 后端 datetime 值转 datetime-local 输入值（yyyy-MM-ddTHH:mm）
function toLocal(v) {
  if (!v) return ''
  return String(v).slice(0, 16)
}
// datetime-local 值提交（补秒）
function submitDate(v) {
  if (!v) return null
  return v.length === 16 ? v + ':00' : v
}

async function load() {
  const params = {}
  if (filter.value.name) params.name = filter.value.name
  if (filter.value.owner) params.owner = filter.value.owner
  params.date_type = filter.value.dateType
  if (filter.value.startDate) params.start_date = filter.value.startDate
  if (filter.value.endDate) params.end_date = filter.value.endDate
  const { data } = await projectApi.list(params)
  projects.value = data
}
function applyFilter() { load() }
function resetFilter() {
  filter.value = { name: '', owner: '', dateType: 'created', startDate: '', endDate: '' }
  load()
}

function openCreate() {
  editingId.value = null
  form.value = { name: '', description: '', owner: '', status: 'draft', deliver_date: '' }
  showCreate.value = true
}
async function create() {
  if (!form.value.name) return window.$toast.warning('请填写项目名称')
  try {
    await projectApi.create({ ...form.value, deliver_date: submitDate(form.value.deliver_date) })
    showCreate.value = false
    window.$toast.success('项目已创建')
    load()
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '创建失败')
  }
}
function openEdit(p) {
  editingId.value = p.id
  form.value = { name: p.name, description: p.description || '', owner: p.owner || '', status: p.status, deliver_date: toLocal(p.deliver_date) }
  showCreate.value = true
}
async function saveEdit() {
  if (!form.value.name) return window.$toast.warning('请填写项目名称')
  await projectApi.update(editingId.value, { ...form.value, deliver_date: submitDate(form.value.deliver_date) })
  showCreate.value = false
  editingId.value = null
  window.$toast.success('项目已更新')
  load()
}
function useProject(p) {
  localStorage.setItem('twb_project', p.id)
  window.$toast.success('已将「' + p.name + '」设为当前项目')
}
function duplicate(p) {
  // 打开「新增项目」弹窗，预填被复制项目的全部信息（项目名称原样）
  // 保存时若名称与其他项目重复，后端会提示「项目名称已存在」，修改名称后即可保存
  editingId.value = null
  form.value = {
    name: p.name,
    description: p.description || '',
    owner: p.owner || '',
    status: p.status,
    deliver_date: toLocal(p.deliver_date)
  }
  showCreate.value = true
}
function toggle(p) {
  expanded.value = expanded.value === p.id ? null : p.id
}
async function remove(p) {
  if (!(await window.$confirm('确认删除项目「' + p.name + '」？将同时删除该项目下所有需求、用例、执行、缺陷等数据。', { danger: true }))) return
  await projectApi.remove(p.id)
  if (localStorage.getItem('twb_project') == p.id) localStorage.removeItem('twb_project')
  window.$toast.success('已删除')
  load()
}
onMounted(load)
</script>

<style scoped>
.center { text-align: center; }
.date-label { font-size: 13px; color: #64748b; }
.date-sep { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; font-size: 13px; color: #1f2329; }
.form-row input[type="date"] { font-family: inherit; font-size: 13px; }
.radio-inline { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; color: #1f2329; }
.radio-inline input { width: auto; min-width: auto; margin: 0; }
.clickable { cursor: pointer; }
.pname { max-width: 160px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pname a { display: inline-block; max-width: 150px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: bottom; }
.op-btn { margin-left: 4px; }
.detail-row td { background: #f8fafc; padding: 14px; }
.detail-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px 20px; }
.d-item { display: flex; flex-direction: column; gap: 2px; font-size: 13px; }
.d-item .d-label { color: #64748b; font-size: 12px; }
.d-item .d-desc { white-space: pre-wrap; }
.d-full { grid-column: 1 / -1; }
</style>
