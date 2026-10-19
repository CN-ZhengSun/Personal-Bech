// 全局轻量 Toast 提示（成功/错误/警告/信息），替代原生 alert
let container = null

function ensure() {
  if (!container) {
    container = document.createElement('div')
    container.id = 'toast-container'
    container.style.cssText =
      'position:fixed;top:20px;right:20px;z-index:99999;display:flex;flex-direction:column;gap:8px;align-items:flex-end;pointer-events:none;'
    document.body.appendChild(container)
  }
  return container
}

const STYLES = {
  success: { bg: '#ecfdf5', color: '#059669', icon: '✓' },
  error: { bg: '#fef2f2', color: '#dc2626', icon: '✕' },
  warning: { bg: '#fffbeb', color: '#d97706', icon: '!' },
  info: { bg: '#eff6ff', color: '#2563eb', icon: 'ℹ' },
}

export function toast(type, msg, duration = 2500) {
  const c = ensure()
  const s = STYLES[type] || STYLES.info
  const el = document.createElement('div')
  el.style.cssText = `background:${s.bg};color:${s.color};padding:10px 16px;border-radius:8px;font-size:13px;box-shadow:0 2px 10px rgba(0,0,0,.14);display:flex;align-items:center;gap:8px;border:1px solid ${s.color}33;max-width:420px;line-height:1.5;`
  const icon = document.createElement('span')
  icon.style.fontWeight = '700'
  icon.textContent = s.icon
  const text = document.createElement('span')
  text.textContent = msg
  el.appendChild(icon)
  el.appendChild(text)
  c.appendChild(el)
  setTimeout(() => {
    el.style.opacity = '0'
    el.style.transition = 'opacity .3s'
    setTimeout(() => el.remove(), 320)
  }, duration)
  return el
}

export default {
  success: (m) => toast('success', m),
  error: (m) => toast('error', m),
  warning: (m) => toast('warning', m),
  info: (m) => toast('info', m),
}
