<template>
  <div class="layout" :data-theme="currentTheme" v-if="authed">
    <button v-if="mobileNavOpen" class="mobile-nav-backdrop" aria-label="关闭导航菜单" @click="mobileNavOpen = false"></button>
    <!-- 侧边主导航栏（固定在左侧） -->
    <aside id="main-navigation" class="sidebar" :class="{ collapsed, 'mobile-open': mobileNavOpen }">
      <div class="logo-row">
        <button class="logo-box" @click="goHome" title="返回 ADB 工具">
          <span class="logo-emoji">🧪</span>
          <div class="logo-text label">
            <span class="logo-title">Personal-Bench</span>
            <span class="logo-sub">测试工作台</span>
          </div>
        </button>
        <button
          class="collapse-btn"
          :title="collapsed ? '展开侧边菜单' : '收起侧边菜单'"
          @click="toggleSidebar"
        >
          <span v-if="collapsed">»</span>
          <span v-else>«</span>
        </button>
      </div>

      <!-- 导航列表 -->
      <nav class="menu">
        <template v-for="group in menuGroups" :key="group.key">
          <div class="group-title">
            <span class="group-text label">{{ group.name }}</span>
            <span class="group-line" v-if="collapsed"></span>
          </div>
          <RouterLink
            v-for="item in group.items"
            :key="item.path"
            :to="item.path"
            class="menu-item"
            :title="collapsed ? item.name : ''"
            @click="mobileNavOpen = false"
          >
            <span class="item-icon">{{ getMenuIcon(item.path, item.name) }}</span>
            <span class="item-name label">{{ item.name }}</span>
          </RouterLink>
        </template>
      </nav>

      <!-- 底部系统信息 -->
      <div class="sidebar-foot" v-if="!collapsed">
        <span class="foot-tag">个人测试工作台</span>
      </div>
    </aside>

    <!-- 主视口区域（位于左侧栏右侧） -->
    <div class="main-viewport">
      <!-- 顶部全局导航栏 -->
      <header class="topbar">
        <div class="topbar-left">
          <button class="mobile-nav-toggle" type="button" aria-label="打开导航菜单" aria-controls="main-navigation" :aria-expanded="mobileNavOpen" @click="mobileNavOpen = true">☰</button>
          <div class="breadcrumb-trail">
            <span class="crumb-home">🏠</span>
            <span class="crumb-group" v-if="currentGroupTitle">{{ currentGroupTitle }}</span>
            <span class="crumb-sep" v-if="currentGroupTitle">/</span>
            <span class="crumb-page">{{ currentPageTitle }}</span>
          </div>
        </div>

        <div class="topbar-right">
          <!-- 5种风格主题切换器 -->
          <div class="theme-dropdown-wrap" ref="themeDropdownRef">
            <button
              class="theme-toggle-btn"
              @click="toggleThemeMenu"
              title="切换界面风格主题（共 5 种）"
              :aria-expanded="isThemeMenuOpen"
              aria-controls="theme-options"
            >
              <span class="theme-swatch" :style="{ background: activeThemeObj.primary }"></span>
              <span class="theme-label">{{ activeThemeObj.name }}</span>
              <span class="theme-badge-mini" v-if="activeThemeObj.badge">{{ activeThemeObj.badge }}</span>
              <span class="theme-arrow">▾</span>
            </button>

            <!-- 主题切换下拉浮层 -->
            <div id="theme-options" class="theme-menu-popover" v-if="isThemeMenuOpen">
              <div class="popover-head">
                <span class="popover-title">界面风格切换</span>
                <span class="popover-desc">5 种精心调配风格</span>
              </div>
              <div class="theme-list">
                <button
                  v-for="th in THEMES"
                  :key="th.id"
                  type="button"
                  class="theme-card-option"
                  :class="{ active: currentTheme === th.id }"
                  @click="onSelectTheme(th.id)"
                  :aria-pressed="currentTheme === th.id"
                >
                  <div class="swatch-circle" :style="{ background: th.primary }">
                    <span class="check-mark" v-if="currentTheme === th.id">✓</span>
                  </div>
                  <div class="theme-detail">
                    <div class="theme-row-top">
                      <span class="theme-opt-name">{{ th.name }}</span>
                      <span class="theme-opt-badge" v-if="th.badge">{{ th.badge }}</span>
                    </div>
                    <span class="theme-opt-desc">{{ th.tagline }}</span>
                  </div>
                </button>
              </div>
            </div>
          </div>

          <!-- 用户身份胶囊 -->
          <div class="user-chip" :title="'当前登录：' + (user.display_name || user.username)">
            <span class="user-avatar">{{ (user.display_name || user.username || '用')[0]?.toUpperCase() }}</span>
            <div class="user-meta">
              <span class="user-name">{{ user.display_name || user.username || '用户' }}</span>
              <span class="user-role">{{ roleText }}</span>
            </div>
          </div>

          <!-- 修改密码 -->
          <button class="top-action-btn" @click="showPassword = true" title="修改当前账户密码">
            修改密码
          </button>

          <!-- 退出登录 -->
          <button class="top-action-btn btn-logout" @click="logout" title="退出并清理登录会话">
            退出登录
          </button>
        </div>
      </header>

      <!-- 核心页面视图渲染容器 -->
      <main class="content">
        <RouterView v-slot="{ Component }">
          <KeepAlive :max="30">
            <component :is="Component" :key="pageKey" />
          </KeepAlive>
        </RouterView>
      </main>
    </div>

    <!-- 修改密码弹窗 -->
    <div v-if="showPassword" class="modal-mask" @click.self="showPassword = false">
      <div class="modal" style="width: 400px">
        <h3>修改账户密码</h3>
        <div class="field">
          <label>当前密码</label>
          <input
            v-model="passwordForm.current_password"
            type="password"
            placeholder="请输入当前密码"
            autocomplete="current-password"
          />
        </div>
        <div class="field">
          <label>新密码（至少 8 位）</label>
          <input
            v-model="passwordForm.new_password"
            type="password"
            placeholder="请输入 8 位以上新密码"
            autocomplete="new-password"
          />
        </div>
        <div class="field">
          <label>确认新密码</label>
          <input
            v-model="passwordConfirm"
            type="password"
            placeholder="请再次输入新密码"
            autocomplete="new-password"
          />
        </div>
        <div class="actions">
          <button class="btn btn-gray" @click="showPassword = false">取消</button>
          <button class="btn" @click="changePassword">确认修改</button>
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
import { THEMES, getCurrentTheme, applyTheme } from './utils/theme'

const router = useRouter()
const route = useRoute()
const authed = ref(!!localStorage.getItem('twb_authenticated'))
const user = ref({})
const showPassword = ref(false)
const collapsed = ref(localStorage.getItem('twb_sidebar_collapsed') === '1')
const passwordForm = ref({ current_password: '', new_password: '' })
const passwordConfirm = ref('')

// 主题管理
const currentTheme = ref(getCurrentTheme())
const isThemeMenuOpen = ref(false)
const themeDropdownRef = ref(null)
const mobileNavOpen = ref(false)

const activeThemeObj = computed(() => {
  return THEMES.find(t => t.id === currentTheme.value) || THEMES[0]
})

function toggleThemeMenu() {
  isThemeMenuOpen.value = !isThemeMenuOpen.value
}

function onSelectTheme(themeId) {
  currentTheme.value = applyTheme(themeId)
  isThemeMenuOpen.value = false
  window.$toast.success(`已切换风格：${activeThemeObj.value.name}`)
}

function handleOutsideClick(e) {
  if (themeDropdownRef.value && !themeDropdownRef.value.contains(e.target)) {
    isThemeMenuOpen.value = false
  }
}

function handleEscape(e) {
  if (e.key === 'Escape') {
    isThemeMenuOpen.value = false
    mobileNavOpen.value = false
  }
}

// 会话版本号：退出登录时 +1，使已缓存页面状态失效
const sessionTick = ref(0)
// 项目切换版本号：任一页面内切换项目后 +1，重建组件拉取新项目数据
const projectTick = ref(0)
function onProjectChanged() { projectTick.value++ }
function onStorageProject(e) { if (e.key === 'twb_project') projectTick.value++ }
const pageKey = computed(() => `${route.path}|${projectTick.value}|${sessionTick.value}`)

const roleMap = { admin: '管理员', manager: '测试负责人', tester: '测试工程师', dev: '开发', viewer: '只读' }
const roleText = computed(() => roleMap[user.value.role] || user.value.role || '工程师')

// ---------- 菜单（后端配置驱动，失败时回退内置默认） ----------
const DEFAULT_MENU = [
  { key: 'test_manage', name: '测试管理', items: [
    { path: '/requirements', name: '需求 PRD' }, { path: '/cases', name: '测试用例' },
    { path: '/executions', name: '测试执行' }, { path: '/bugs', name: '缺陷跟踪' },
    { path: '/projects', name: '项目管理' }, { path: '/report', name: '质量报表' },
    { path: '/automation', name: '自动化脚本' }, { path: '/releases', name: '版本与环境' } ] },
  { key: 'test_tools', name: '测试工具', items: [
    { path: '/apitest', name: '接口测试工具' }, { path: '/tracking', name: '埋点监控' },
    { path: '/adbtools', name: 'ADB 工具' }, { path: '/test-data', name: '测试数据工厂' } ] },
  { key: 'assets_ai', name: '资产与 AI', items: [
    { path: '/knowledge', name: '知识库' }, { path: '/skills', name: 'SKILL 管理' },
    { path: '/ai', name: 'AI 模型配置' }, { path: '/menu-manage', name: '菜单管理' } ] }
]
const menuGroups = ref(DEFAULT_MENU)

const menuIcons = {
  '/workbench': '📊',
  '/requirements': '📝',
  '/cases': '🧪',
  '/plans': '📅',
  '/executions': '▶️',
  '/bugs': '🐞',
  '/projects': '📁',
  '/report': '📈',
  '/automation': '⚡',
  '/releases': '🏷️',
  '/apitest': '🔌',
  '/tracking': '📡',
  '/adbtools': '📱',
  '/test-data': '🧰',
  '/jmeter': '⏱️',
  '/knowledge': '📚',
  '/skills': '💡',
  '/ai': '🤖',
  '/menu-manage': '⚙️'
}

function getMenuIcon(path, name) {
  if (menuIcons[path]) return menuIcons[path]
  if (name.includes('工作台')) return '📊'
  if (name.includes('PRD') || name.includes('需求')) return '📝'
  if (name.includes('用例')) return '🧪'
  if (name.includes('计划')) return '📅'
  if (name.includes('执行')) return '▶️'
  if (name.includes('缺陷')) return '🐞'
  if (name.includes('接口') || name.includes('API')) return '🔌'
  if (name.includes('埋点')) return '📡'
  if (name.includes('ADB')) return '📱'
  if (name.includes('AI')) return '🤖'
  return '📄'
}

// 面包屑计算
const currentGroupTitle = computed(() => {
  for (const g of menuGroups.value) {
    if (g.items.some(i => i.path === route.path)) {
      return g.name
    }
  }
  return ''
})

const currentPageTitle = computed(() => {
  for (const g of menuGroups.value) {
    const item = g.items.find(i => i.path === route.path)
    if (item) return item.name
  }
  return route.name || '页面'
})

function toggleSidebar() {
  collapsed.value = !collapsed.value
}

function goHome() {
  mobileNavOpen.value = false
  router.push('/adbtools')
}

watch(() => route.path, () => { mobileNavOpen.value = false; isThemeMenuOpen.value = false })

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
  } catch { /* 保持默认 */ }
}

function onMenuChanged() { loadMenu() }

watch(collapsed, v => localStorage.setItem('twb_sidebar_collapsed', v ? '1' : '0'))

function loadUser() {
  try { user.value = JSON.parse(localStorage.getItem('twb_user') || '{}') } catch { user.value = {} }
}

async function loadProjects() {}

async function logout() {
  try { await authApi.logout() } catch {}
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

onMounted(() => {
  loadUser()
  bootstrap()
  loadMenu()
  window.addEventListener('twb-menu-changed', onMenuChanged)
  window.addEventListener('twb-project-changed', onProjectChanged)
  window.addEventListener('storage', onStorageProject)
  document.addEventListener('click', handleOutsideClick)
  document.addEventListener('keydown', handleEscape)
})

onUnmounted(() => {
  window.removeEventListener('twb-menu-changed', onMenuChanged)
  window.removeEventListener('twb-project-changed', onProjectChanged)
  window.removeEventListener('storage', onStorageProject)
  document.removeEventListener('click', handleOutsideClick)
  document.removeEventListener('keydown', handleEscape)
})
</script>
