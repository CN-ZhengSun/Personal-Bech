// 全局自定义确认框（Promise-based），替代原生 confirm
let mask = null

function build(message, okText = '确认', cancelText = '取消') {
  mask = document.createElement('div')
  mask.style.cssText =
    'position:fixed;inset:0;background:rgba(15,23,42,.45);display:flex;align-items:center;justify-content:center;z-index:99998;'
  const box = document.createElement('div')
  box.style.cssText =
    'background:#fff;border-radius:12px;padding:22px 24px;width:380px;max-width:90vw;box-shadow:0 10px 40px rgba(0,0,0,.2);font-size:14px;'
  const msg = document.createElement('div')
  msg.style.cssText = 'color:#1f2329;margin-bottom:18px;line-height:1.6;'
  msg.textContent = message
  const actions = document.createElement('div')
  actions.style.cssText = 'display:flex;justify-content:flex-end;gap:10px;'
  const cancel = document.createElement('button')
  cancel.textContent = cancelText
  cancel.style.cssText =
    'padding:7px 16px;border:1px solid #d0d7de;background:#fff;color:#334155;border-radius:6px;cursor:pointer;font-size:13px;'
  cancel.onmouseover = () => (cancel.style.background = '#f8fafc')
  cancel.onmouseout = () => (cancel.style.background = '#fff')
  const ok = document.createElement('button')
  ok.textContent = okText
  ok.style.cssText =
    'padding:7px 16px;border:none;background:#2563eb;color:#fff;border-radius:6px;cursor:pointer;font-size:13px;'
  ok.onmouseover = () => (ok.style.background = '#1d4ed8')
  ok.onmouseout = () => (ok.style.background = '#2563eb')
  actions.appendChild(cancel)
  actions.appendChild(ok)
  box.appendChild(msg)
  box.appendChild(actions)
  mask.appendChild(box)
  document.body.appendChild(mask)
  return { mask, cancel, ok }
}

export function confirmDialog(message, options = {}) {
  const { okText, cancelText, danger = false } = options
  return new Promise((resolve) => {
    const { mask, cancel, ok } = build(message, okText, cancelText)
    if (danger) {
      ok.style.background = '#dc2626'
      ok.onmouseover = () => (ok.style.background = '#b91c1c')
      ok.onmouseout = () => (ok.style.background = '#dc2626')
    }
    const close = (val) => {
      mask.remove()
      resolve(val)
    }
    cancel.onclick = () => close(false)
    ok.onclick = () => close(true)
    mask.addEventListener('mousedown', (e) => {
      if (e.target === mask) close(false)
    })
  })
}

export default confirmDialog
