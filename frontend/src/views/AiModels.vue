<template>
  <div>
    <h1>AI 模型配置</h1>
    <div class="card">
      <h3 style="margin-bottom:10px">模型供应商</h3>
      <div class="form-row">
        <input v-model="mform.name" placeholder="配置名，如 豆包主模型" style="width:160px" />
        <select v-model="mform.provider">
          <option value="doubao">豆包</option><option value="openai">OpenAI</option><option value="deepseek">DeepSeek</option><option value="other">其他</option>
        </select>
        <input v-model="mform.model_name" placeholder="模型名，如 doubao-pro" style="width:160px" />
        <input v-model="mform.api_key" placeholder="API Key" style="flex:1" />
        <button class="btn" @click="createModel">新增模型</button>
      </div>
      <table class="table">
        <thead><tr><th>ID</th><th>名称</th><th>供应商</th><th>模型</th><th>温度</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="m in models" :key="m.id">
            <td>{{ m.id }}</td>
            <td>{{ m.name }}</td>
            <td><span class="tag tag-purple">{{ m.provider }}</span></td>
            <td>{{ m.model_name }}</td>
            <td>{{ m.temperature }}</td>
            <td><span class="tag" :class="m.status === 'enabled' ? 'tag-green' : 'tag-gray'">{{ m.status }}</span></td>
            <td>
              <select v-model="m.status" @change="updateModel(m)">
                <option value="enabled">启用</option><option value="disabled">停用</option>
              </select>
              <button class="btn btn-small btn-danger" @click="removeModel(m)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="card">
      <h3 style="margin-bottom:10px">Prompt 模板</h3>
      <div class="form-row">
        <input v-model="pform.name" placeholder="模板名，如 缺陷分析模板" style="flex:1" />
        <input v-model="pform.content" placeholder="模板内容，{input} 为变量" style="flex:2" />
        <button class="btn" @click="createPrompt">新增模板</button>
      </div>
      <table class="table">
        <thead><tr><th>ID</th><th>名称</th><th>内容</th><th>变量</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="p in prompts" :key="p.id">
            <td>{{ p.id }}</td>
            <td>{{ p.name }}</td>
            <td class="muted" style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ p.content }}</td>
            <td>{{ p.variables || '—' }}</td>
            <td><button class="btn btn-small btn-danger" @click="removePrompt(p)">删除</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { modelApi, promptApi } from '../api'

const models = ref([])
const prompts = ref([])
const mform = ref({ name: '', provider: 'doubao', model_name: '', api_key: '' })
const pform = ref({ name: '', content: '' })

async function load() {
  const [m, p] = await Promise.all([modelApi.list(), promptApi.list()])
  models.value = m.data
  prompts.value = p.data
}
async function createModel() {
  if (!mform.value.name || !mform.value.model_name) return window.$toast.warning('请填写配置名与模型名')
  await modelApi.create(mform.value)
  mform.value = { name: '', provider: 'doubao', model_name: '', api_key: '' }
  window.$toast.success('模型配置已新增')
  load()
}
async function updateModel(m) { await modelApi.update(m.id, { status: m.status }) }
async function removeModel(m) {
  if (!(await window.$confirm('确认删除模型配置「' + m.name + '」？', { danger: true }))) return
  await modelApi.remove(m.id); window.$toast.success('已删除'); load()
}
async function createPrompt() {
  if (!pform.value.name) return window.$toast.warning('请填写模板名')
  await promptApi.create(pform.value)
  pform.value = { name: '', content: '' }
  window.$toast.success('Prompt 模板已新增')
  load()
}
async function removePrompt(p) {
  if (!(await window.$confirm('确认删除模板「' + p.name + '」？', { danger: true }))) return
  await promptApi.remove(p.id); window.$toast.success('已删除'); load()
}
onMounted(load)
</script>

<style scoped>
h3 { font-size: 15px; }
</style>
