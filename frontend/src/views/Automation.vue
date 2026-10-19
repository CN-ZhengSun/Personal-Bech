<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin:4px 0 12px">
      <h1 style="margin:0">自动化脚本管理</h1>
      <ProjectSelect />
    </div>

    <div class="card">
      <h3 style="margin-bottom:10px">脚本库（托管）</h3>
      <div class="form-row">
        <input v-model="sform.name" placeholder="脚本名称" style="flex:1" />
        <select v-model="sform.script_type"><option value="ui">UI</option><option value="api">API</option></select>
        <input v-model="sform.framework" placeholder="框架，如 pytest+selenium" style="width:180px" />
        <button class="btn" @click="createScript">新增脚本</button>
      </div>
      <table class="table">
        <thead><tr><th>ID</th><th>名称</th><th>类型</th><th>框架</th><th>版本</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="s in scripts" :key="s.id">
            <td>{{ s.id }}</td>
            <td>{{ s.name }}</td>
            <td><span class="tag" :class="s.script_type === 'ui' ? 'tag-blue' : 'tag-purple'">{{ s.script_type.toUpperCase() }}</span></td>
            <td>{{ s.framework || '—' }}</td>
            <td>{{ s.version || '—' }}</td>
            <td><span class="tag" :class="s.status === 'active' ? 'tag-green' : 'tag-gray'">{{ s.status }}</span></td>
            <td>
              <button class="btn btn-small btn-gray" @click="viewScript(s)">查看</button>
              <button class="btn btn-small btn-danger" @click="removeScript(s)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!scripts.length" class="muted" style="margin-top:10px">暂无脚本，点击上方「新增脚本」创建。</p>
    </div>

    <div class="card">
      <h3 style="margin-bottom:10px">调度任务</h3>
      <div class="form-row">
        <select v-model="tform.script_id" style="min-width:200px">
          <option v-for="s in scripts" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
        <input v-model="tform.name" placeholder="任务名称" style="flex:1" />
        <input v-model="tform.schedule" placeholder="cron，如 0 2 * * *" style="width:160px" />
        <button class="btn" @click="createTask">新增任务</button>
      </div>
      <table class="table">
        <thead><tr><th>ID</th><th>名称</th><th>脚本</th><th>调度</th><th>状态</th><th>上次执行</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="t in tasks" :key="t.id">
            <td>{{ t.id }}</td>
            <td>{{ t.name }}</td>
            <td>{{ scriptMap[t.script_id] || '#' + t.script_id }}</td>
            <td>{{ t.schedule || '手动' }}</td>
            <td><span class="tag" :class="t.status === 'enabled' ? 'tag-green' : 'tag-gray'">{{ t.status }}</span></td>
            <td>{{ t.last_run_at || '—' }}</td>
            <td>
              <button class="btn btn-small" @click="runTask(t)">触发</button>
              <button class="btn btn-small btn-danger" @click="removeTask(t)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!tasks.length" class="muted" style="margin-top:10px">暂无调度任务，点击上方「新增任务」创建。</p>
    </div>

    <div class="modal-mask" v-if="scriptView">
      <div class="modal">
        <h3>{{ scriptView.name }}</h3>
        <pre class="pre">{{ scriptView.content || '（暂无脚本内容）' }}</pre>
        <div class="actions"><button class="btn btn-gray" @click="scriptView = null">关闭</button></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { scriptApi, taskApi } from '../api'
import ProjectSelect from '../components/ProjectSelect.vue'

const scripts = ref([])
const tasks = ref([])
const scriptMap = ref({})
const scriptView = ref(null)
const sform = ref({ name: '', script_type: 'ui', framework: '' })
const tform = ref({ script_id: null, name: '', schedule: '' })
const projectId = () => localStorage.getItem('twb_project') || undefined

async function load() {
  const pid = projectId()
  // 脚本库列表用当前项目；名称映射用全量（调度任务可能引用其他项目脚本）
  const [s, allS, t] = await Promise.all([scriptApi.list(pid), scriptApi.list(), taskApi.list()])
  scripts.value = s.data
  tasks.value = t.data
  scriptMap.value = Object.fromEntries(allS.data.map((x) => [x.id, x.name]))
}
async function createScript() {
  if (!sform.value.name) return window.$toast.warning('请填写脚本名称')
  if (!projectId()) return window.$toast.warning('请先在上方选择项目')
  await scriptApi.create({ project_id: Number(projectId()), name: sform.value.name, script_type: sform.value.script_type, framework: sform.value.framework })
  sform.value = { name: '', script_type: 'ui', framework: '' }
  window.$toast.success('脚本已添加')
  load()
}
async function createTask() {
  if (!tform.value.name || !tform.value.script_id) return window.$toast.warning('请选择脚本并填写任务名')
  await taskApi.create(tform.value)
  tform.value = { script_id: null, name: '', schedule: '' }
  window.$toast.success('调度任务已创建')
  load()
}
function viewScript(s) { scriptView.value = s }
async function runTask(t) {
  const { data } = await taskApi.run(t.id)
  t.last_run_at = data.last_run_at
  window.$toast.success('任务「' + t.name + '」已触发，执行报告：' + (data.report || '已完成'))
}
async function removeScript(s) {
  if (!(await window.$confirm('确认删除脚本「' + s.name + '」？', { danger: true }))) return
  await scriptApi.remove(s.id); window.$toast.success('已删除'); load()
}
async function removeTask(t) {
  if (!(await window.$confirm('确认删除任务「' + t.name + '」？', { danger: true }))) return
  await taskApi.remove(t.id); window.$toast.success('已删除'); load()
}
onMounted(load)
watch(() => localStorage.getItem('twb_project'), load)
</script>

<style scoped>
.pre { background: #f8fafc; border-radius: 6px; padding: 12px; white-space: pre-wrap; font-size: 13px; max-height: 50vh; overflow-y: auto; }
h3 { font-size: 15px; }
</style>
