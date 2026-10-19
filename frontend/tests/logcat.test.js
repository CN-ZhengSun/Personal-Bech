import test from 'node:test'
import assert from 'node:assert/strict'

import {
  canonicalLogLine,
  compileLogMatcher,
  decodeLogcatEvent,
  matchesLogRecord,
} from '../src/utils/logcat.js'

function record(overrides = {}) {
  return {
    raw: '2026-09-10 15:34:53.819 10291 13537 13537 D WorkerTag: Work started',
    parsed: true,
    time: '2026-09-10 15:34:53.819',
    uid: '10291',
    pid: '13537',
    tid: '13537',
    level: 'D',
    tag: 'WorkerTag',
    message: 'Work started',
    applicationId: 'com.qwe.test.test',
    packageNames: ['com.qwe.test.test'],
    processName: 'com.qwe.test.test',
    ...overrides,
  }
}

test('decodes a structured websocket log record', () => {
  const decoded = decodeLogcatEvent(JSON.stringify({
    type: 'log',
    raw: 'raw line',
    parsed: true,
    timestamp: '2026-09-10 15:34:53.819',
    uid: '10291',
    pid: '13537',
    tid: '13537',
    level: 'D',
    tag: 'WorkerTag',
    message: 'Work started',
    application_id: 'com.qwe.test.test',
    package_names: ['com.qwe.test.test'],
    process_name: 'com.qwe.test.test',
  }))

  assert.equal(decoded.applicationId, 'com.qwe.test.test')
  assert.equal(decoded.tag, 'WorkerTag')
})

test('plain text searches the canonical line including application id', () => {
  assert.match(canonicalLogLine(record()), /com\.qwe\.test\.test/)
  assert.equal(matchesLogRecord(record(), 'com.qwe.test.test'), true)
})

test('package field does not match another process merely mentioning the package', () => {
  const systemLog = record({
    pid: '1723',
    applicationId: 'android',
    packageNames: ['android'],
    processName: 'system_server',
    message: 'Started com.qwe.test.test',
  })

  assert.equal(matchesLogRecord(systemLog, 'com.qwe.test.test'), true)
  assert.equal(matchesLogRecord(systemLog, 'package:com.qwe.test.test'), false)
})

test('tag field is isolated from the message', () => {
  const item = record({ tag: 'ActivityManager', message: 'WorkerTag failed' })

  assert.equal(matchesLogRecord(item, 'tag:WorkerTag'), false)
  assert.equal(matchesLogRecord(item, 'message:WorkerTag'), true)
})

test('level is a severity threshold and accepts full names', () => {
  const warning = record({ level: 'W' })

  assert.equal(matchesLogRecord(warning, 'level:INFO'), true)
  assert.equal(matchesLogRecord(warning, 'level:ERROR'), false)
  assert.equal(matchesLogRecord(warning, '', 'I'), true)
})

test('same positive fields use implicit OR and different fields use AND', () => {
  const matcher = compileLogMatcher('tag:Alpha tag:Worker package:com.qwe')

  assert.equal(matcher.predicate(record()), true)
  assert.equal(matcher.predicate(record({ applicationId: 'other.app', packageNames: ['other.app'] })), false)
})

test('supports explicit operators, parentheses and precedence', () => {
  const matcher = compileLogMatcher('(tag:Worker | level:ERROR) & package:com.qwe')

  assert.equal(matcher.predicate(record()), true)
  assert.equal(matcher.predicate(record({ tag: 'Other', level: 'D' })), false)
})

test('supports negation, regex, exact matching and quoted values', () => {
  assert.equal(compileLogMatcher('-tag:Other message~:"Work.*started"').predicate(record()), true)
  assert.equal(compileLogMatcher('tag=:WorkerTag').predicate(record()), true)
  assert.equal(compileLogMatcher('"Work started"').predicate(record()), true)
})

test('reports invalid syntax and safely falls back to whole-line search', () => {
  const matcher = compileLogMatcher('(tag:Worker')

  assert.match(matcher.error, /右括号/)
  assert.equal(matcher.predicate(record()), false)
})

test('supports age and crash classifiers', () => {
  const now = new Date().toISOString()
  const recent = record({ time: now })
  const crash = record({ level: 'E', tag: 'AndroidRuntime', message: 'FATAL EXCEPTION: main' })

  assert.equal(compileLogMatcher('age:5m').predicate(recent), true)
  assert.equal(compileLogMatcher('is:crash').predicate(crash), true)
})

test('package:mine uses the configured mine package', () => {
  const matcher = compileLogMatcher('package:mine', '', '', false, 'com.qwe.test.test')
  assert.equal(matcher.predicate(record()), true)
  assert.equal(matcher.predicate(record({ applicationId: 'other.app', packageNames: ['other.app'] })), false)
})

test('package:mine without a configured package reports a clear error', () => {
  const matcher = compileLogMatcher('package:mine')
  assert.match(matcher.error, /我的包名/)
  assert.equal(matcher.predicate(record()), false)
})

test('is:stacktrace matches stack frames, caused-by chains and more markers', () => {
  const frame = record({ level: 'E', tag: 'AndroidRuntime', message: 'at com.qwe.test.Main.onCreate(Main.java:12)' })
  const native = record({ level: 'E', message: '    at com.qwe.test.Native.run(Native.kt:4)' })
  const caused = record({ level: 'E', message: 'Caused by: java.lang.NullPointerException: boom' })
  const suppressed = record({ level: 'E', message: 'Suppressed: java.io.IOException' })
  const more = record({ level: 'E', message: '... 2 more' })
  const normal = record({ message: 'Work started' })

  assert.equal(compileLogMatcher('is:stacktrace').predicate(frame), true)
  assert.equal(compileLogMatcher('is:stacktrace').predicate(native), true)
  assert.equal(compileLogMatcher('is:stacktrace').predicate(caused), true)
  assert.equal(compileLogMatcher('is:stacktrace').predicate(suppressed), true)
  assert.equal(compileLogMatcher('is:stacktrace').predicate(more), true)
  assert.equal(compileLogMatcher('is:stacktrace').predicate(normal), false)
})

test('query and regex length limits are enforced', () => {
  assert.match(compileLogMatcher('a'.repeat(1001)).error, /1000/)
  assert.match(compileLogMatcher('tag~:' + 'a'.repeat(201)).error, /200/)
  assert.match(compileLogMatcher('tag~:[a-z').error, /无效正则/)
})
