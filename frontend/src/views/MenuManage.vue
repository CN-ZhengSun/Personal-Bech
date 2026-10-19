<template>
  <div>
    <div class="head">
      <h1>菜单管理</h1>
      <div class="head-actions">
        <button class="btn btn-gray" @click="load">重置未保存修改</button>
        <button class="btn" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button>
      </div>
    </div>
    <div class="tip">拖动「上移 / 下移」调整菜单顺序，直接编辑名称后点「保存配置」生效。</div>
    <div class="card">
      <div class="toolbar">
        <label class="muted">共 {{ rows.length }} 行（含分组 {{ groupCount }} 个、菜单 {{ itemCount }} 项）</label>
        <label class="check"><input type="checkbox" v-model="showKey" /> 显示路由标识</label>
      </div>
      <table class="table menu-table">
        <thead>
          <tr>
            <th style="width:60px">顺序</th>
            <th style="width:90px">类型</th>
            <th>名称</th>
            <th v-if="showKey">路由标识</th>
            <th style="width:160px">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in rows" :key="row.uid" :class="{ 'group-row': row.is_group }">
            <td class="muted">{{ idx + 1 }}</td>
            <td><span class="tag" :class="row.is_group ? 'tag-blue' : 'tag-gray'">{{ row.is_group ? '分组' : '菜单' }}</span></td>
            <td>
              <input v-model="row.name" class="name-input" :class="{ 'group-name': row.is_group }"
                :placeholder="row.is_group ? '分组名称' : '菜单名称'" maxlength="50" />
            </td>
            <td v-if="showKey"><span class="muted mono">{{ row.is_group ? row.group_key : row.menu_key }}</span></td>
            <td>
              <div class="row-ops">
                <button class="btn btn-small btn-gray" :disabled="idx === 0" @click="move(idx, -1)">↑ 上移</button>
                <button class="btn btn-small btn-gray" :disabled="idx === rows.length - 1" @click="move(idx, 1)">↓ 下移</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <div class="foot-actions">
        <button class="btn" :disabled="saving" @click="save">{{ saving ? '保存中…' : '保存配置' }}</button>
        <button class="btn btn-gray" @click="load">重置</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { menuApi } from '../api'

const rows = ref([])
const saving = ref(false)
const showKey = ref(false)

const groupCount = computed(() => rows.value.filter(r => r.is_group).length)
const itemCount = computed(() => rows.value.filter(r => !r.is_group).length)

async function load() {
  try {
    const { data } = await menuApi.list()
    rows.value = data.map(r => ({ ...r, uid: `${r.id}-${Math.random().toString(36).slice(2, 7)}` }))
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '菜单配置加载失败')
  }
}

function move(idx, dir) {
  const target = idx + dir
  if (target < 0 || target >= rows.value.length) return
  const arr = rows.value
  ;[arr[idx], arr[target]] = [arr[target], arr[idx]]
  rows.value = [...arr]
}

async function save() {
  // 校验：名称非空
  for (const r of rows.value) {
    if (!r.name.trim()) return window.$toast.warning('名称不能为空')
  }
  // 校验：分组行标识唯一
  const groups = rows.value.filter(r => r.is_group).map(r => r.group_key)
  if (new Set(groups).size !== groups.length) return window.$toast.error('分组标识重复，请刷新后重试')
  saving.value = true
  try {
    const payload = rows.value.map((r, i) => ({
      menu_key: r.is_group ? null : r.menu_key,
      name: r.name,
      group_key: r.group_key,
      is_group: r.is_group,
      sort_order: (i + 1) * 10
    }))
    await menuApi.save(payload)
    window.$toast.success('菜单配置已保存')
    window.dispatchEvent(new CustomEvent('twb-menu-changed'))
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
.head-actions { display: flex; gap: 8px; }
.tip { font-size: 13px; color: #8896a7; margin: -6px 0 14px; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.check { font-size: 13px; color: #64748b; display: flex; align-items: center; gap: 6px; cursor: pointer; }
.menu-table .group-row td { background: #f8fafc; }
.name-input { width: 280px; max-width: 100%; padding: 6px 10px; border: 1px solid #d0d7de; border-radius: 6px; font-size: 13px; }
.name-input:focus { outline: 2px solid #2563eb33; border-color: #2563eb; }
.group-name { font-weight: 600; background: #f0f4ff; }
.mono { font-family: Consolas, monospace; font-size: 12px; }
.row-ops { display: flex; gap: 6px; }
.foot-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
</style>
