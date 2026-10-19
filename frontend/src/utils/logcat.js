import { compileLogQuery, levelAtLeast, isStackLine } from './logcat-query.js'
export { isStackLine }

function parseLegacyLine(raw) {
  const match = raw.match(
    /^((?:\d{4}-)?\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2}\.\d+)\s+(?:(\S+)\s+)?(\d+)\s+(\d+)\s+([VDIWEF])\s+(.*)$/,
  )
  if (!match) return null
  const body = match[7]
  const separator = body.indexOf(':')
  return {
    time: match[1] + ' ' + match[2],
    uid: match[3] || '',
    pid: match[4],
    tid: match[5],
    level: match[6],
    tag: separator >= 0 ? body.slice(0, separator).trim() : '',
    message: separator >= 0 ? body.slice(separator + 1).trimStart() : body,
  }
}

export function decodeLogcatEvent(data) {
  let payload = data
  if (typeof data === 'string' && data.startsWith('{')) {
    try {
      payload = JSON.parse(data)
    } catch {
      payload = data
    }
  }

  if (payload && typeof payload === 'object' && payload.type === 'log') {
    return {
      raw: String(payload.raw || ''),
      parsed: Boolean(payload.parsed),
      time: payload.timestamp || '',
      uid: String(payload.uid || ''),
      pid: String(payload.pid || ''),
      tid: String(payload.tid || ''),
      level: payload.level || '',
      tag: payload.tag || '',
      message: payload.message || '',
      applicationId: payload.application_id || '',
      packageNames: Array.isArray(payload.package_names) ? payload.package_names : [],
      processName: payload.process_name || '',
    }
  }

  const raw = typeof payload === 'string' ? payload : JSON.stringify(payload)
  const parsed = parseLegacyLine(raw)
  return {
    raw,
    parsed: Boolean(parsed),
    time: parsed?.time || '',
    uid: parsed?.uid || '',
    pid: parsed?.pid || '',
    tid: parsed?.tid || '',
    level: parsed?.level || '',
    tag: parsed?.tag || '',
    message: parsed?.message || raw,
    applicationId: '',
    packageNames: [],
    processName: '',
  }
}

export function canonicalLogLine(record) {
  if (!record.parsed) return record.raw
  return [
    record.time,
    record.pid && record.tid ? record.pid + '-' + record.tid : record.pid,
    record.tag,
    record.applicationId,
    record.level ? record.level + ':' : '',
    record.message,
  ].filter(Boolean).join(' ')
}

function contains(value, expected) {
  return String(value || '').toLowerCase().includes(expected.toLowerCase())
}

export function recordHasPackage(record, expected) {
  if (record.applicationId) return contains(record.applicationId, expected)
  if (record.packageNames?.length === 1) return contains(record.packageNames[0], expected)
  return false
}

export function matchesLogRecord(record, query = '', minimumLevel = '', processPid = '') {
  return compileLogMatcher(query, minimumLevel, processPid).predicate(record)
}

export function compileLogMatcher(query = '', minimumLevel = '', processPid = '', matchCase = false, minePackage = '') {
  const compiled = compileLogQuery(query, canonicalLogLine, { matchCase, minePackage })
  return {
    error: compiled.error,
    predicate: (record) => (
      (!processPid || record.pid === String(processPid))
      && levelAtLeast(record.level, minimumLevel)
      && compiled.predicate(record)
    ),
  }
}
