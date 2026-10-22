// 5 种主题系统定义与管理（主版本为「小清新浅绿」）
export const THEMES = [
  {
    id: 'fresh-mint',
    name: '小清新浅绿',
    tagline: '清新自然 · 护眼舒缓',
    badge: '主版本',
    primary: '#10b981',
    light: '#ecfdf5',
    sidebar: '#142e23',
    isDark: false
  },
  {
    id: 'tech-blue',
    name: '科技极简蓝',
    tagline: '专业高效 · 经典沉稳',
    badge: '推荐',
    primary: '#2563eb',
    light: '#eff6ff',
    sidebar: '#0f172a',
    isDark: false
  },
  {
    id: 'warm-amber',
    name: '暖木舒雅金',
    tagline: '温暖柔和 · 护眼阅读',
    badge: '舒雅',
    primary: '#d97706',
    light: '#fffbeb',
    sidebar: '#29211b',
    isDark: false
  },
  {
    id: 'lilac-violet',
    name: '紫曜先锋',
    tagline: '灵动优雅 · 现代前沿',
    badge: '潮流',
    primary: '#7c3aed',
    light: '#f5f3ff',
    sidebar: '#201633',
    isDark: false
  },
  {
    id: 'obsidian-dark',
    name: '极光曜黑',
    tagline: '沉浸极夜 · 极客暗黑',
    badge: '暗色',
    primary: '#38bdf8',
    light: '#1e293b',
    sidebar: '#0a0f1d',
    isDark: true
  }
]

export const STORAGE_KEY = 'twb_theme'
export const DEFAULT_THEME = 'fresh-mint'

export function getCurrentTheme() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved && THEMES.some(t => t.id === saved)) {
      return saved
    }
  } catch {
    // fallback
  }
  return DEFAULT_THEME
}

export function applyTheme(themeId) {
  const validTheme = THEMES.some(t => t.id === themeId) ? themeId : DEFAULT_THEME
  try {
    localStorage.setItem(STORAGE_KEY, validTheme)
  } catch {
    // 禁用本地存储时仍允许在当前页面切换主题。
  }
  document.documentElement.setAttribute('data-theme', validTheme)
  document.body?.setAttribute('data-theme', validTheme)
  window.dispatchEvent(new CustomEvent('twb-theme-changed', { detail: validTheme }))
  return validTheme
}

export function initTheme() {
  const current = getCurrentTheme()
  applyTheme(current)
  return current
}

