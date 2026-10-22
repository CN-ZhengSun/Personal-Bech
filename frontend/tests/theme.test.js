import test from 'node:test'
import assert from 'node:assert/strict'
import { applyTheme, DEFAULT_THEME, getCurrentTheme, STORAGE_KEY } from '../src/utils/theme.js'

function withBrowserGlobals(storage, run) {
  const previous = {
    localStorage: globalThis.localStorage,
    document: globalThis.document,
    window: globalThis.window,
    CustomEvent: globalThis.CustomEvent
  }
  const attributes = { html: {}, body: {} }
  const events = []
  globalThis.localStorage = storage
  globalThis.document = {
    documentElement: { setAttribute: (name, value) => { attributes.html[name] = value } },
    body: { setAttribute: (name, value) => { attributes.body[name] = value } }
  }
  globalThis.window = { dispatchEvent: event => events.push(event) }
  globalThis.CustomEvent = class { constructor(type, options) { this.type = type; this.detail = options.detail } }
  try {
    run({ attributes, events })
  } finally {
    for (const [name, value] of Object.entries(previous)) {
      if (value === undefined) delete globalThis[name]
      else globalThis[name] = value
    }
  }
}

test('loads a saved supported theme and rejects stale values', () => {
  const data = new Map([[STORAGE_KEY, 'tech-blue']])
  withBrowserGlobals({ getItem: key => data.get(key) }, () => {
    assert.equal(getCurrentTheme(), 'tech-blue')
    data.set(STORAGE_KEY, 'removed-theme')
    assert.equal(getCurrentTheme(), DEFAULT_THEME)
  })
})

test('applies the fallback theme when storage is unavailable', () => {
  withBrowserGlobals({
    getItem: () => { throw new Error('storage blocked') },
    setItem: () => { throw new Error('storage blocked') }
  }, ({ attributes, events }) => {
    assert.equal(getCurrentTheme(), DEFAULT_THEME)
    assert.equal(applyTheme('not-a-theme'), DEFAULT_THEME)
    assert.equal(attributes.html['data-theme'], DEFAULT_THEME)
    assert.equal(attributes.body['data-theme'], DEFAULT_THEME)
    assert.equal(events[0].detail, DEFAULT_THEME)
  })
})
