const LEVELS = {
  V: 0, VERBOSE: 0,
  D: 1, DEBUG: 1,
  I: 2, INFO: 2,
  W: 3, WARN: 3, WARNING: 3,
  E: 4, ERROR: 4,
  F: 5, FATAL: 5, ASSERT: 5,
}

const FIELD_KEYS = new Set(['tag', 'package', 'process', 'message', 'line', 'pid'])
const SPECIAL_KEYS = new Set(['level', 'age', 'is', 'name'])

function tokenize(input) {
  const tokens = []
  let value = ''
  let quote = ''
  let escaped = false
  const flush = () => {
    if (value) tokens.push({ type: 'term', value })
    value = ''
  }

  for (const char of input) {
    if (quote) {
      if (escaped) {
        value += char
        escaped = false
      } else if (char === '\\') {
        escaped = true
      } else if (char === quote) {
        quote = ''
      } else {
        value += char
      }
      continue
    }
    if (char === '"' || char === "'") {
      quote = char
    } else if (/\s/.test(char)) {
      flush()
    } else if ('&|()'.includes(char)) {
      flush()
      tokens.push({ type: char })
    } else {
      value += char
    }
  }
  if (quote) throw new Error('引号未闭合')
  if (escaped) value += '\\'
  flush()
  return tokens
}

function termNode(text) {
  const match = text.match(/^(-)?([a-z]+)([~=]?):(.*)$/i)
  if (!match) return { type: 'term', key: '', value: text, modifier: '', negated: false }
  const key = match[2].toLowerCase()
  if (!FIELD_KEYS.has(key) && !SPECIAL_KEYS.has(key)) {
    throw new Error('不支持的查询字段：' + key)
  }
  if (!match[4]) throw new Error(key + ': 缺少查询值')
  return {
    type: 'term',
    key,
    value: match[4],
    modifier: match[3],
    negated: Boolean(match[1]),
  }
}

function combine(type, nodes) {
  if (nodes.length === 1) return nodes[0]
  return { type, nodes }
}

function implicitGroup(nodes) {
  const joined = []
  for (const node of nodes) {
    const previous = joined[joined.length - 1]
    if (node.type === 'term' && !node.key && previous?.type === 'term' && !previous.key) {
      previous.value += ' ' + node.value
    } else {
      joined.push(node)
    }
  }

  const groups = []
  const keyed = new Map()
  for (const node of joined) {
    const canImplicitOr = node.type === 'term' && node.key && !node.negated
    if (!canImplicitOr) {
      groups.push(node)
      continue
    }
    if (!keyed.has(node.key)) {
      const bucket = []
      keyed.set(node.key, bucket)
      groups.push(bucket)
    }
    keyed.get(node.key).push(node)
  }
  return combine('and', groups.map((group) => Array.isArray(group) ? combine('or', group) : group))
}

function parse(tokens) {
  let index = 0
  const peek = () => tokens[index]
  const take = () => tokens[index++]

  function primary() {
    const token = take()
    if (!token) throw new Error('查询表达式不完整')
    if (token.type === 'term') return termNode(token.value)
    if (token.type === '(') {
      const node = orExpression()
      if (take()?.type !== ')') throw new Error('缺少右括号')
      return node
    }
    throw new Error('意外的运算符：' + token.type)
  }

  function implicitExpression() {
    const nodes = [primary()]
    while (peek() && (peek().type === 'term' || peek().type === '(')) nodes.push(primary())
    return implicitGroup(nodes)
  }

  function andExpression() {
    const nodes = [implicitExpression()]
    while (peek()?.type === '&') {
      take()
      nodes.push(implicitExpression())
    }
    return combine('and', nodes)
  }

  function orExpression() {
    const nodes = [andExpression()]
    while (peek()?.type === '|') {
      take()
      nodes.push(andExpression())
    }
    return combine('or', nodes)
  }

  if (!tokens.length) return null
  const root = orExpression()
  if (index !== tokens.length) throw new Error('意外的符号：' + peek().type)
  return root
}

function contains(actual, expected, matchCase) {
  if (matchCase) return String(actual || '').includes(expected)
  return String(actual || '').toLowerCase().includes(expected.toLowerCase())
}

function equal(actual, expected, matchCase) {
  if (matchCase) return String(actual || '') === expected
  return String(actual || '').toLowerCase() === expected.toLowerCase()
}

function packageValue(record) {
  if (record.applicationId) return record.applicationId
  return record.packageNames?.length === 1 ? record.packageNames[0] : ''
}

function fieldValue(record, key, canonicalLine) {
  if (key === 'tag') return record.tag
  if (key === 'package') return packageValue(record)
  if (key === 'process') return record.processName
  if (key === 'message') return record.message
  if (key === 'line') return canonicalLine
  if (key === 'pid') return record.pid
  return ''
}

function timestampMillis(value) {
  if (!value) return Number.NaN
  const withYear = /^\d{4}-/.test(value) ? value : new Date().getFullYear() + '-' + value
  return new Date(withYear.replace(' ', 'T')).getTime()
}

function termPredicate(node, matchCase, minePackage) {
  const { key, value, modifier, negated } = node
  let predicate

  if (!key) {
    predicate = (record, canonicalLine) => contains(canonicalLine, value, matchCase)
  } else if (FIELD_KEYS.has(key)) {
    if (modifier === '~') {
      if (value.length > 200) throw new Error('正则表达式不能超过 200 个字符')
      let regex
      try {
        regex = new RegExp(value, matchCase ? '' : 'i')
      } catch {
        throw new Error('无效正则表达式：' + value)
      }
      predicate = (record, canonicalLine) => regex.test(fieldValue(record, key, canonicalLine))
    } else if (modifier === '=') {
      predicate = (record, canonicalLine) => equal(fieldValue(record, key, canonicalLine), value, matchCase)
    } else if (key === 'pid') {
      predicate = (record) => record.pid === value
    } else if (key === 'package' && String(value).toLowerCase() === 'mine') {
      // package:mine：使用配置的"我的包名"（compileLogQuery 预检保证已设置）
      const mine = minePackage || ''
      predicate = mine ? (record) => contains(packageValue(record), mine, matchCase) : () => false
    } else {
      predicate = (record, canonicalLine) => contains(fieldValue(record, key, canonicalLine), value, matchCase)
    }
  } else if (key === 'level') {
    const minimum = LEVELS[value.toUpperCase()]
    if (minimum === undefined) throw new Error('无效日志级别：' + value)
    predicate = (record) => {
      const actual = LEVELS[String(record.level || '').toUpperCase()]
      return actual !== undefined && actual >= minimum
    }
  } else if (key === 'age') {
    const match = value.match(/^(\d+)([smhd])$/i)
    if (!match) throw new Error('age 格式应为数字加 s/m/h/d')
    const unitMillis = { s: 1000, m: 60000, h: 3600000, d: 86400000 }
    const duration = Number(match[1]) * unitMillis[match[2].toLowerCase()]
    predicate = (record) => {
      const timestamp = timestampMillis(record.time)
      return Number.isFinite(timestamp) && Date.now() - timestamp <= duration
    }
  } else if (key === 'is') {
    const kind = value.toLowerCase()
    if (kind === 'crash') {
      predicate = (record) => (
        (record.level === 'E' && record.tag === 'AndroidRuntime' && record.message.startsWith('FATAL EXCEPTION'))
        || (record.level === 'F' && (record.tag === 'DEBUG' || record.tag === 'libc'))
      )
    } else if (kind === 'stacktrace') {
      // 更可靠的堆栈识别：Java 堆栈帧 / Caused by 链 / Suppressed / ... N more
      predicate = (record) => isStackLine(record.message)
    } else {
      throw new Error('is 仅支持 crash 或 stacktrace')
    }
  } else {
    predicate = () => true
  }
  return negated ? (record, line) => !predicate(record, line) : predicate
}

/** 判断文本（可含多行 message）是否为堆栈帧/堆栈链标记。 */
export function isStackLine(text) {
  return String(text || '').split('\n').some((l) => (
    /^\s*at\s+[\w.$]+\([^)]*\)/.test(l)
    || /^Caused by:\s/.test(l)
    || /^\s*(Suppressed:|\.\.\.\s+\d+\s+more)/.test(l)
  ))
}

function compileNode(node, matchCase, minePackage) {
  if (node.type === 'term') return termPredicate(node, matchCase, minePackage)
  const predicates = node.nodes.map((child) => compileNode(child, matchCase, minePackage))
  if (node.type === 'or') return (record, line) => predicates.some((fn) => fn(record, line))
  return (record, line) => predicates.every((fn) => fn(record, line))
}

export function compileLogQuery(query, canonicalLine, options = {}) {
  const source = query.trim()
  if (!source) return { error: '', predicate: () => true }
  if (source.length > 1000) return { error: '查询条件不能超过 1000 个字符', predicate: () => false }
  if (/package\s*:\s*mine\b/i.test(source) && !options.minePackage) {
    return { error: 'package:mine 需要先在日志分析中设置“我的包名”', predicate: () => false }
  }
  try {
    const root = parse(tokenize(source))
    const predicate = compileNode(root, Boolean(options.matchCase), options.minePackage)
    return { error: '', predicate: (record) => predicate(record, canonicalLine(record)) }
  } catch (error) {
    const fallback = (record) => contains(canonicalLine(record), source, Boolean(options.matchCase))
    return { error: error.message || '查询语法错误', predicate: fallback }
  }
}

export function levelAtLeast(actualLevel, minimumLevel) {
  if (!minimumLevel) return true
  const actual = LEVELS[String(actualLevel || '').toUpperCase()]
  const minimum = LEVELS[String(minimumLevel).toUpperCase()]
  return actual !== undefined && minimum !== undefined && actual >= minimum
}
