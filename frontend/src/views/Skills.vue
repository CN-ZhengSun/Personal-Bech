<template>
  <div>
    <h1>SKILL 管理</h1>
    <div class="card">
      <div class="form-row">
        <input v-model="form.name" placeholder="Skill 名称，如 测试用例生成" style="flex:1" />
        <button class="btn" @click="openCreate">新增 Skill</button>
      </div>
      <table class="table">
        <thead><tr><th>ID</th><th>名称</th><th>描述</th><th>状态</th><th>版本</th><th>操作</th></tr></thead>
        <tbody>
          <tr v-for="s in skills" :key="s.id">
            <td>{{ s.id }}</td>
            <td>{{ s.name }}</td>
            <td>{{ s.description || '—' }}</td>
            <td><span class="tag" :class="s.status === 'enabled' ? 'tag-green' : s.status === 'draft' ? 'tag-gray' : 'tag-orange'">{{ s.status }}</span></td>
            <td>{{ s.version }}</td>
            <td>
              <button class="btn btn-small btn-gray" @click="view(s)">配置</button>
              <button class="btn btn-small btn-danger" @click="remove(s)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!skills.length" class="muted" style="margin-top:10px">暂无 Skill。AI 能力为后置模块，可先沉淀编排配置。</p>
    </div>

    <div class="modal-mask" v-if="showCreate || editing">
      <div class="modal">
        <h3>{{ editing ? '编辑 Skill' : '新增 Skill' }}</h3>
        <div class="field"><label>名称 *</label><input v-model="form.name" /></div>
        <div class="field"><label>描述</label><textarea v-model="form.description"></textarea></div>
        <div class="field"><label>输入模板</label><textarea v-model="form.input_template" placeholder="如：需求标题：{title}"></textarea></div>
        <div class="field"><label>Prompt 模板</label><textarea v-model="form.prompt_template" placeholder="如：请为以下需求生成测试用例：{input}"></textarea></div>
        <div class="field"><label>状态</label>
          <select v-model="form.status"><option value="draft">草稿</option><option value="enabled">启用</option><option value="disabled">停用</option></select>
        </div>
        <div class="actions">
          <button class="btn btn-gray" @click="close">取消</button>
          <button class="btn" @click="save">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { skillApi } from '../api'

const skills = ref([])
const showCreate = ref(false)
const editing = ref(null)
const form = ref({ name: '', description: '', input_template: '', prompt_template: '', status: 'draft' })

async function load() {
  const { data } = await skillApi.list()
  skills.value = data
}
function openCreate() {
  form.value = { name: '', description: '', input_template: '', prompt_template: '', status: 'draft' }
  showCreate.value = true
  editing.value = null
}
function view(s) {
  editing.value = s
  showCreate.value = false
  form.value = { name: s.name, description: s.description, input_template: s.input_template, prompt_template: s.prompt_template, status: s.status }
}
function close() { showCreate.value = false; editing.value = null }
async function save() {
  if (!form.value.name) return window.$toast.warning('请填写 Skill 名称')
  if (editing.value) {
    await skillApi.update(editing.value.id, form.value)
    window.$toast.success('Skill 已更新')
  } else {
    await skillApi.create(form.value)
    window.$toast.success('Skill 已创建')
  }
  close(); load()
}
async function remove(s) {
  if (!(await window.$confirm('确认删除 Skill「' + s.name + '」？', { danger: true }))) return
  await skillApi.remove(s.id); window.$toast.success('已删除'); load()
}
onMounted(load)
</script>

<style scoped>
h3 { font-size: 15px; }
</style>
