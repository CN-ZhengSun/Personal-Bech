// 查询历史工具：localStorage 持久化 + 异常数据防护。
// 设计约束：任何损坏/异常数据（非 JSON、非数组、非字符串条目）都不能让页面打不开，
// 因此所有读取都走 try/catch 并做类型校验；存储失败（隐私模式/配额超限）静默忽略。
export const LOG_HISTORY_KEY = 'twb_log_query_history'
export const LOG_HISTORY_MAX = 20

function resolveStorage(storage) {
  if (storage) return storage
  try {
    return typeof localStorage !== 'undefined' ? localStorage : null
  } catch {
    return null
  }
}

/** 读取查询历史，异常一律返回空数组。 */
export function loadLogQueryHistory(storage) {
  const store = resolveStorage(storage)
  if (!store) return []
  try {
    const raw = store.getItem(LOG_HISTORY_KEY)
    if (!raw) return []
    const arr = JSON.parse(raw)
    if (!Array.isArray(arr)) return []
    return arr
      .filter((x) => typeof x === 'string' && x.trim())
      .slice(0, LOG_HISTORY_MAX)
  } catch {
    return []
  }
}

/** 保存查询历史（截断到上限）；存储失败静默忽略，不影响功能。 */
export function saveLogQueryHistory(items, storage) {
  const store = resolveStorage(storage)
  if (!store) return
  try {
    const safe = Array.isArray(items) ? items.filter((x) => typeof x === 'string') : []
    store.setItem(LOG_HISTORY_KEY, JSON.stringify(safe.slice(0, LOG_HISTORY_MAX)))
  } catch {
    /* noop */
  }
}

/**
 * 记忆一条查询：返回新数组（去重、最新在前、上限 LOG_HISTORY_MAX）。
 * 纯函数，便于单元测试；空查询不做任何变更。
 */
export function rememberLogQuery(items, q) {
  const trimmed = typeof q === 'string' ? q.trim() : ''
  if (!trimmed) return items
  const base = Array.isArray(items) ? items : []
  return [trimmed, ...base.filter((x) => x !== trimmed)].slice(0, LOG_HISTORY_MAX)
}
