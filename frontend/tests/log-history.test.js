import test from 'node:test'
import assert from 'node:assert/strict'

import {
  LOG_HISTORY_KEY,
  LOG_HISTORY_MAX,
  loadLogQueryHistory,
  saveLogQueryHistory,
  rememberLogQuery,
} from '../src/utils/log-history.js'

function fakeStorage() {
  const m = new Map()
  return {
    getItem: (k) => (m.has(k) ? m.get(k) : null),
    setItem: (k, v) => m.set(k, String(v)),
  }
}

test('empty storage yields empty history', () => {
  assert.deepEqual(loadLogQueryHistory(fakeStorage()), [])
})

test('corrupted JSON must not break loading (异常数据不导致页面打不开)', () => {
  const s = fakeStorage()
  s.setItem(LOG_HISTORY_KEY, '{not valid json!!')
  assert.deepEqual(loadLogQueryHistory(s), [])
})

test('non-array JSON yields empty history', () => {
  const s = fakeStorage()
  s.setItem(LOG_HISTORY_KEY, JSON.stringify({ foo: 1 }))
  assert.deepEqual(loadLogQueryHistory(s), [])
})

test('array with non-string entries filters them out and trims blanks', () => {
  const s = fakeStorage()
  s.setItem(LOG_HISTORY_KEY, JSON.stringify(['tag:Worker', 42, null, '  ', 'level:E']))
  assert.deepEqual(loadLogQueryHistory(s), ['tag:Worker', 'level:E'])
})

test('history longer than the cap is truncated', () => {
  const s = fakeStorage()
  s.setItem(LOG_HISTORY_KEY, JSON.stringify(Array.from({ length: 50 }, (_, i) => `q${i}`)))
  assert.equal(loadLogQueryHistory(s).length, LOG_HISTORY_MAX)
})

test('save then load round-trips in order', () => {
  const s = fakeStorage()
  saveLogQueryHistory(['b', 'a'], s)
  assert.deepEqual(loadLogQueryHistory(s), ['b', 'a'])
})

test('save tolerates non-array input', () => {
  const s = fakeStorage()
  saveLogQueryHistory('not-an-array', s)
  assert.deepEqual(loadLogQueryHistory(s), [])
})

test('remember dedupes, keeps newest first and caps the length', () => {
  const items = ['old', 'new']
  const next = rememberLogQuery(items, 'old')
  assert.deepEqual(next, ['old', 'new'])
  const many = Array.from({ length: 25 }, (_, i) => `q${i}`)
  assert.equal(rememberLogQuery(many, 'fresh').length, LOG_HISTORY_MAX)
  assert.equal(rememberLogQuery(many, 'fresh')[0], 'fresh')
})

test('remember ignores empty or non-string queries', () => {
  const items = ['a']
  assert.deepEqual(rememberLogQuery(items, '   '), items)
  assert.deepEqual(rememberLogQuery(items, 42), items)
  assert.deepEqual(rememberLogQuery(null, 'x'), ['x'])
})

test('missing localStorage environment does not throw', () => {
  // node 环境无 localStorage：不传 storage 时应安全返回空数组
  assert.deepEqual(loadLogQueryHistory(), [])
  assert.doesNotThrow(() => saveLogQueryHistory(['a']))
})
