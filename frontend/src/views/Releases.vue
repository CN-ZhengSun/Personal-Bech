<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin:4px 0 12px">
      <h1 style="margin:0">版本与环境</h1>
      <ProjectSelect />
    </div>

    <div class="card">
      <h3 style="margin-bottom:10px">被测版本</h3>
      <div class="form-row">
        <input v-model="vform.name" placeholder="版本号，如 v1.0.0" />
        <button class="btn" @click="createVersion">新增版本</button>
      </div>
      <table class="table">
        <thead><tr><th>ID</th><th>名称</th><th>状态</th><th>描述</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="v in versions" :key="v.id">
            <td>{{ v.id }}</td>
            <td>{{ v.name }}</td>
            <td><span class="tag" :class="verStatusTag(v.status)">{{ verStatusText[v.status] || v.status }}</span></td>
            <td>{{ v.description || '—' }}</td>
            <td>
              <select v-model="v.status" @change="updateVersion(v)">
                <option v-for="(t, k) in verStatusText" :key="k" :value="k">{{ t }}</option>
              </select>
              <button class="btn btn-small btn-danger" @click="removeVersion(v)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!versions.length" class="muted" style="margin-top:10px">暂无版本，点击上方「新增版本」创建。</p>
    </div>

    <div class="card">
      <h3 style="margin-bottom:10px">测试环境</h3>
      <div class="form-row">
        <input v-model="eform.name" placeholder="环境名，如 测试环境" />
        <input v-model="eform.base_url" placeholder="Base URL" style="flex:1" />
        <button class="btn" @click="createEnv">新增环境</button>
      </div>
      <table class="table">
        <thead><tr><th>ID</th><th>名称</th><th>Base URL</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="e in envs" :key="e.id">
            <td>{{ e.id }}</td>
            <td>{{ e.name }}</td>
            <td>{{ e.base_url || '—' }}</td>
            <td><span class="tag" :class="envStatusTag(e.status)">{{ envStatusText[e.status] || e.status }}</span></td>
            <td>
              <select v-model="e.status" @change="updateEnv(e)">
                <option v-for="(t, k) in envStatusText" :key="k" :value="k">{{ t }}</option>
              </select>
              <button class="btn btn-small btn-danger" @click="removeEnv(e)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { versionApi, envApi } from '../api'
import ProjectSelect from '../components/ProjectSelect.vue'

const versions = ref([])
const envs = ref([])
const vform = ref({ name: '', description: '' })
const eform = ref({ name: '', base_url: '' })
const verStatusText = { dev: '开发中', testing: '测试中', released: '已发布', archived: '已归档' }
const verStatusTag = (s) => ({ dev: 'tag-gray', testing: 'tag-blue', released: 'tag-green', archived: 'tag-gray' }[s] || 'tag-gray')
const envStatusText = { available: '可用', maintenance: '维护中', offline: '离线' }
const envStatusTag = (s) => ({ available: 'tag-green', maintenance: 'tag-orange', offline: 'tag-red' }[s] || 'tag-gray')
const projectId = () => localStorage.getItem('twb_project') || undefined

async function load() {
  const pid = projectId()
  const [v, e] = await Promise.all([versionApi.list(pid), envApi.list()])
  versions.value = v.data
  envs.value = e.data
}
async function createVersion() {
  if (!vform.value.name) return window.$toast.warning('请填写版本名')
  if (!projectId()) return window.$toast.warning('请先在上方选择项目')
  await versionApi.create({ project_id: Number(projectId()), name: vform.value.name })
  vform.value = { name: '', description: '' }
  window.$toast.success('版本已创建')
  load()
}
async function updateVersion(v) { await versionApi.update(v.id, { status: v.status }) }
async function removeVersion(v) {
  if (!(await window.$confirm('确认删除版本「' + v.name + '」？', { danger: true }))) return
  await versionApi.remove(v.id); window.$toast.success('已删除'); load()
}
async function createEnv() {
  if (!eform.value.name) return window.$toast.warning('请填写环境名')
  await envApi.create(eform.value)
  eform.value = { name: '', base_url: '' }
  window.$toast.success('环境已创建')
  load()
}
async function updateEnv(e) { await envApi.update(e.id, { status: e.status }) }
async function removeEnv(e) {
  if (!(await window.$confirm('确认删除环境「' + e.name + '」？', { danger: true }))) return
  await envApi.remove(e.id); window.$toast.success('已删除'); load()
}
onMounted(load)
watch(() => localStorage.getItem('twb_project'), load)
</script>

<style scoped>
h3 { font-size: 15px; }
</style>
