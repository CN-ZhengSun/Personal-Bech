<template>
  <div class="layout" v-if="authed">
    <aside class="sidebar" :class="{ collapsed }">
      <div class="logo-row">
        <div class="logo">🧪<span class="label">测试工作台</span></div>
        <button class="collapse-btn" :title="collapsed ? '展开菜单' : '收起菜单'" @click="collapsed = !collapsed">{{ collapsed ? '»' : '«' }}</button>
      </div>
      <nav class="menu">
        <template v-for="group in menuGroups" :key="group.key">
          <div class="group"><span class="label">{{ group.name }}</span></div>
          <RouterLink v-for="item in group.items" :key="item.path" :to="item.path" class="item"><span class="label">{{ item.name }}</span></RouterLink>
        </template>
      </nav>
    </aside>
    <main class="content">
      <header class="topbar">
        <span class="user">{{ user.display_name || user.username }}（{{ roleText }}）</span>
        <button class="btn btn-small btn-gray" @click="showPassword = true">修改密码</button>
        <button class="btn btn-small" @click="logout">退出登录</button>
      </header>
      <RouterView v-slot="{ Component }">
        <KeepAlive :max="30">
          <component :is="Component" :key="pageKey" />
        </KeepAlive>
      </RouterView>
    </main>
    <div v-if="showPassword" class="modal-mask" @click.self="showPassword = false">
      <div class="modal" style="width:380px">
        <h3>修改管理员密码</h3>
        <div class="field"><label>当前密码</label><input v-model="passwordForm.current_password" type="password" /></div>
        <div class="field"><label>新密码（至少 8 位）</label><input v-model="passwordForm.new_password" type="password" /></div>
        <div class="field"><label>确认新密码</label><input v-model="passwordConfirm" type="password" /></div>
        <div class="actions">
          <button class="btn btn-gray" @click="showPassword = false">取消</button>
          <button class="btn" @click="changePassword">保存</button>
        </div>
      </div>
    </div>
  </div>
  <RouterView v-else />
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authApi, menuApi } from './api'

const router = useRouter()
const route = useRoute()
const authed = ref(!!localStorage.getItem('twb_authenticated'))
const user = ref({})
const showPassword = ref(false)
const collapsed = ref(localStorage.getItem('twb_sidebar_collapsed') === '1')
const passwordForm = ref({ current_password: '', new_password: '' })
const passwordConfirm = ref('')
// 会话版本号：退出登录时 +1，使已缓存页面状态失效（同一登录会话内切换页面状态保留）
const sessionTick = ref(0)
// 项目切换版本号：任一页面内切换项目（localStorage twb_project）后 +1，重建组件拉取新项目数据
const projectTick = ref(0)
function onProjectChanged() { projectTick.value++ }
function onStorageProject(e) { if (e.key === 'twb_project') projectTick.value++ }
// 页面缓存键：路由路径 + 项目版本 + 会话版本。切项目或重新登录时重建组件拉取新数据
const pageKey = computed(() => `${route.path}|${projectTick.value}|${sessionTick.value}`)

const roleMap = { admin: '管理员', manager: '测试负责人', tester: '测试工程师', dev: '开发', viewer: '只读' }
const roleText = computed(() => roleMap[user.value.role] || user.value.role)

// ---------- 菜单（后端配置驱动，失败时回退内置默认） ----------
const DEFAULT_MENU = [
  { key: 'test_manage', name: '测试管理', items: [
    { path: '/requirements', name: '需求 PRD' }, { path: '/cases', name: '测试用例' },
    { path: '/executions', name: '测试执行' }, { path: '/bugs', name: '缺陷跟踪' },
    { path: '/projects', name: '项目管理' }, { path: '/report', name: '质量报表' },
    { path: '/automation', name: '自动化脚本' }, { path: '/releases', name: '版本与环境' } ] },
  { key: 'test_tools', name: '测试工具', items: [
    { path: '/apitest', name: '接口测试工具' }, { path: '/tracking', name: '埋点监控' }, { path: '/adbtools', name: 'ADB 工具' } ] },
  { key: 'assets_ai', name: '资产与 AI', items: [
    { path: '/knowledge', name: '知识库' }, { path: '/skills', name: 'SKILL 管理' },
    { path: '/ai', name: 'AI 模型配置' }, { path: '/menu-manage', name: '菜单管理' } ] }
]
const menuGroups = ref(DEFAULT_MENU)

async function loadMenu() {
  try {
    const { data } = await menuApi.list()
    const groups = []
    let cur = null
    for (const row of data) {
      if (row.is_group) {
        cur = { key: row.group_key, name: row.name, items: [] }
        groups.push(cur)
      } else if (cur) {
        cur.items.push({ path: row.menu_key, name: row.name })
      }
    }
    if (groups.length && groups.some(g => g.items.length)) menuGroups.value = groups
  } catch { /* 拉取失败时保持内置默认菜单 */ }
}

function onMenuChanged() { loadMenu() }

watch(collapsed, v => localStorage.setItem('twb_sidebar_collapsed', v ? '1' : '0'))

function loadUser() {
  try { user.value = JSON.parse(localStorage.getItem('twb_user') || '{}') } catch { user.value = {} }
}

async function loadProjects() {
  /* 项目选择器已移入各测试管理页面（ProjectSelect 组件），App 不再维护项目列表 */
}

async function logout() {
  try { await authApi.logout() } catch { /* 本地服务异常时仍清理页面状态 */ }
  sessionTick.value++
  authed.value = false
  localStorage.removeItem('twb_authenticated')
  localStorage.removeItem('twb_user')
  router.push('/login')
}

async function changePassword() {
  if (!passwordForm.value.current_password) return window.$toast.warning('请输入当前密码')
  if (passwordForm.value.new_password.length < 8) return window.$toast.warning('新密码至少 8 位')
  if (passwordForm.value.new_password !== passwordConfirm.value) return window.$toast.warning('两次输入的新密码不一致')
  try {
    await authApi.changePassword(passwordForm.value)
    showPassword.value = false
    passwordForm.value = { current_password: '', new_password: '' }
    passwordConfirm.value = ''
    window.$toast.success('密码已修改，当前设备保持登录')
  } catch (e) {
    window.$toast.error(e.response?.data?.detail || '密码修改失败')
  }
}

async function bootstrap() {
  try {
    const { data } = await authApi.me()
    user.value = data
    authed.value = true
    localStorage.setItem('twb_authenticated', '1')
    localStorage.setItem('twb_user', JSON.stringify(data))
    await loadProjects()
  } catch {
    authed.value = false
    localStorage.removeItem('twb_authenticated')
    localStorage.removeItem('twb_user')
    if (route.path !== '/login') router.replace('/login')
  }
}

onMounted(() => { loadUser(); bootstrap(); loadMenu(); window.addEventListener('twb-menu-changed', onMenuChanged); window.addEventListener('twb-project-changed', onProjectChanged); window.addEventListener('storage', onStorageProject) })
onUnmounted(() => { window.removeEventListener('twb-menu-changed', onMenuChanged); window.removeEventListener('twb-project-changed', onProjectChanged); window.removeEventListener('storage', onStorageProject) })
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
select { font-family: inherit; }
body { font-family: "Microsoft YaHei", "PingFang SC", sans-serif; background: #f5f6f8; color: #1f2329; }
.layout { display: flex; min-height: 100vh; }
.sidebar { width: 176px; background: #1e293b; color: #fff; padding: 12px 0; flex-shrink: 0; display: flex; flex-direction: column; transition: width .18s ease; overflow: hidden; }
.sidebar.collapsed { width: 46px; }
.logo-row { display: flex; align-items: center; justify-content: space-between; padding: 0 10px 12px; }
.logo { font-size: 15px; font-weight: 600; white-space: nowrap; }
.collapse-btn { flex-shrink: 0; width: 24px; height: 24px; border: none; border-radius: 6px; background: #334155; color: #cbd5e1; font-size: 12px; cursor: pointer; line-height: 1; }
.collapse-btn:hover { background: #475569; color: #fff; }
.sidebar.collapsed .logo-row { justify-content: center; padding: 0 0 12px; }
.sidebar.collapsed .label { display: none; }
.proj { padding: 0 12px 12px; }
.proj select { width: 100%; padding: 6px 8px; border-radius: 6px; border: none; background: #334155; color: #fff; font-size: 13px; }
.menu { flex: 1; overflow-y: auto; }
.group { padding: 10px 20px 4px; font-size: 12px; color: #64748b; white-space: nowrap; }
.sidebar.collapsed .group { padding: 12px 0 4px; text-align: center; }
.item { display: flex; align-items: center; padding: 8px 20px; color: #cbd5e1; text-decoration: none; font-size: 14px; white-space: nowrap; }
.sidebar.collapsed .item { justify-content: center; padding: 9px 0; }
.item:hover { background: #334155; color: #fff; }
.item.router-link-active { background: #2563eb; color: #fff; }
.content { flex: 1; padding: 20px 24px; overflow-x: hidden; }
.topbar { display: flex; justify-content: flex-end; align-items: center; gap: 12px; margin-bottom: 16px; }
.user { font-size: 13px; color: #64748b; }
.card { background: #fff; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 16px; }
h1 { font-size: 20px; margin-bottom: 14px; }
.btn { padding: 7px 14px; background: #2563eb; color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 13px; }
.btn:hover { background: #1d4ed8; }
.btn-small { padding: 5px 12px; font-size: 12px; }
.btn-danger { background: #dc2626; }
.btn-danger:hover { background: #b91c1c; }
.btn-gray { background: #64748b; }
.btn-gray:hover { background: #475569; }
.form-row { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
.form-row input, .form-row select, .form-row textarea { padding: 7px 10px; border: 1px solid #d0d7de; border-radius: 6px; font-size: 13px; }
.form-row input, .form-row select { min-width: 120px; }
.form-row textarea { width: 100%; min-height: 80px; font-family: inherit; }
.table { width: 100%; border-collapse: collapse; font-size: 13px; }
.table th, .table td { text-align: left; padding: 9px 10px; border-bottom: 1px solid #eef1f4; }
.table th { background: #f8fafc; font-weight: 600; white-space: nowrap; }
.table tr:hover td { background: #f8fafc; }
.muted { color: #8896a7; font-size: 13px; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 12px; }
.tag-green { background: #ecfdf5; color: #059669; }
.tag-red { background: #fef2f2; color: #dc2626; }
.tag-orange { background: #fff7ed; color: #ea580c; }
.tag-blue { background: #eff6ff; color: #2563eb; }
.tag-gray { background: #f1f5f9; color: #64748b; }
.tag-purple { background: #f5f3ff; color: #7c3aed; }
.tag-yellow { background: #fefce8; color: #ca8a04; }
.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
.modal { background: #fff; border-radius: 10px; padding: 20px; width: 520px; max-width: 92vw; max-height: 88vh; overflow-y: auto; }
.modal h3 { margin-bottom: 14px; }
.modal .field { margin-bottom: 10px; }
.modal .field label { display: block; font-size: 13px; color: #64748b; margin-bottom: 4px; }
.modal .field input, .modal .field select, .modal .field textarea { width: 100%; padding: 7px 10px; border: 1px solid #d0d7de; border-radius: 6px; font-size: 13px; }
.modal .field textarea { min-height: 70px; font-family: inherit; }
.modal .actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 14px; }
.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
.stat-card { background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.stat-card .num { font-size: 26px; font-weight: 700; }
.stat-card .lbl { font-size: 12px; color: #8896a7; margin-top: 4px; }
.bar { height: 8px; background: #eef1f4; border-radius: 4px; overflow: hidden; margin-top: 6px; }
.bar > div { height: 100%; background: #2563eb; }
</style>
