import axios from 'axios'

const http = axios.create({ baseURL: '/api/v1', timeout: 15000, withCredentials: true })

// 响应拦截：401 跳登录；所选项目已删除时自动清除本地选择并提示
http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('twb_authenticated')
      localStorage.removeItem('twb_user')
      if (window.location.pathname !== '/login') window.location.href = '/login'
    }
    const detail = err.response && err.response.data ? err.response.data.detail : ''
    if (err.response && err.response.status === 404 && detail === '项目不存在') {
      localStorage.removeItem('twb_project')
      if (!window.__twb_project_missing__) {
        window.__twb_project_missing__ = true
        setTimeout(() => { window.__twb_project_missing__ = false }, 2000)
        try { window.$toast && window.$toast.warning('所选项目已不存在，请重新选择项目') } catch (e) { /* noop */ }
      }
    }
    return Promise.reject(err)
  }
)

// ---------- 认证 ----------
export const authApi = {
  login: (d) => http.post('/auth/login', d),
  me: () => http.get('/auth/me'),
  logout: () => http.post('/auth/logout'),
  changePassword: (d) => http.post('/auth/change-password', d)
}

// ---------- 项目 ----------
export const projectApi = {
  list: (params) => http.get('/projects', { params }),
  create: (d) => http.post('/projects', d),
  detail: (id) => http.get(`/projects/${id}`),
  update: (id, d) => http.patch(`/projects/${id}`, d),
  remove: (id) => http.delete(`/projects/${id}`)
}

// ---------- 需求/PRD ----------
export const prdApi = {
  list: (projectId) => http.get('/prd', { params: { project_id: projectId } }),
  create: (d) => http.post('/prd', d),
  detail: (id) => http.get(`/prd/${id}`),
  remove: (id) => http.delete(`/prd/${id}`)
}
export const requirementApi = {
  list: (projectId) => http.get('/requirements', { params: { project_id: projectId } }),
  create: (d) => http.post('/requirements', d),
  update: (id, d) => http.patch(`/requirements/${id}`, d),
  remove: (id) => http.delete(`/requirements/${id}`),
  coverage: (id) => http.get(`/requirements/${id}/coverage`)
}

// ---------- 测试计划 ----------
export const planApi = {
  list: (projectId) => http.get('/plans', { params: { project_id: projectId } }),
  create: (d) => http.post('/plans', d),
  update: (id, d) => http.patch(`/plans/${id}`, d),
  remove: (id) => http.delete(`/plans/${id}`),
  progress: (id) => http.get(`/plans/${id}/progress`)
}

// ---------- 用例 ----------
export const caseApi = {
  list: (projectId) => http.get('/cases', { params: { project_id: projectId } }),
  create: (d) => http.post('/cases', d),
  detail: (id) => http.get(`/cases/${id}`),
  update: (id, d) => http.patch(`/cases/${id}`, d),
  remove: (id) => http.delete(`/cases/${id}`),
  importCases: (projectId, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/cases/import', fd, { params: { project_id: projectId } })
  },
  templateUrl: () => `/api/v1/cases/template`
}

// ---------- 执行 ----------
export const executionApi = {
  list: (params) => http.get('/executions', { params }),
  create: (d) => http.post('/executions', d),
  batch: (d) => http.post('/executions/batch', d),
  update: (id, d) => http.patch(`/executions/${id}`, d),
  remove: (id) => http.delete(`/executions/${id}`)
}

// ---------- 缺陷 ----------
export const bugApi = {
  list: (params) => http.get('/bugs', { params }),
  create: (d) => http.post('/bugs', d),
  detail: (id) => http.get(`/bugs/${id}`),
  update: (id, d) => http.patch(`/bugs/${id}`, d),
  remove: (id) => http.delete(`/bugs/${id}`),
  comments: (id) => http.get(`/bugs/${id}/comments`),
  addComment: (id, d) => http.post(`/bugs/${id}/comments`, d)
}

// ---------- 自动化 ----------
export const scriptApi = {
  list: (projectId) => http.get('/automation/scripts', { params: { project_id: projectId } }),
  create: (d) => http.post('/automation/scripts', d),
  update: (id, d) => http.patch(`/automation/scripts/${id}`, d),
  remove: (id) => http.delete(`/automation/scripts/${id}`)
}
export const taskApi = {
  list: () => http.get('/automation/tasks'),
  create: (d) => http.post('/automation/tasks', d),
  update: (id, d) => http.patch(`/automation/tasks/${id}`, d),
  remove: (id) => http.delete(`/automation/tasks/${id}`),
  run: (id) => http.post(`/automation/tasks/${id}/run`)
}

// ---------- 埋点监控 ----------
export const adbApi = {
  devices: () => http.get('/adb/devices'),
  connect: (host, port) => http.post('/adb/connect', null, { params: { host, port } }),
  disconnect: (serial) => http.post('/adb/disconnect', null, { params: { serial } }),
  info: (serial) => http.get(`/adb/devices/${serial}/info`),
  apps: (serial) => http.get(`/adb/devices/${serial}/apps`),
  activity: (serial) => http.get(`/adb/devices/${serial}/activity`),
  screencapUrl: (serial) => `/api/v1/adb/devices/${serial}/screencap`,
  install: (serial, file, flag = '-r') => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post(`/adb/devices/${serial}/install`, fd, { params: { flag }, timeout: 200000 })
  },
  uninstall: (serial, pkg, flag = '') => http.post(`/adb/devices/${serial}/uninstall`, null, { params: { package: pkg, flag } }),
  clear: (serial, pkg) => http.post(`/adb/devices/${serial}/clear`, null, { params: { package: pkg } }),
  launch: (serial, pkg) => http.post(`/adb/devices/${serial}/launch`, null, { params: { package: pkg } }),
  shell: (serial, cmd) => http.post(`/adb/devices/${serial}/shell`, { cmd }),
  execute: (serial, command) => http.post(`/adb/devices/${serial}/execute`, { command }, { timeout: 200000 }),
  reboot: (serial, mode) => http.post(`/adb/devices/${serial}/reboot`, null, { params: { mode } }),
  shutdown: (serial) => http.post(`/adb/devices/${serial}/shutdown`),
  record: (serial, d) => http.post(`/adb/devices/${serial}/record`, null, { params: d, timeout: 220000 }),
  recordStart: (serial, d) => http.post(`/adb/devices/${serial}/record/start`, null, { params: d, timeout: 30000 }),
  recordStop: (serial) => http.post(`/adb/devices/${serial}/record/stop`, null, { timeout: 300000 }),
  logcatDump: (serial, lines) => http.get(`/adb/devices/${serial}/logcat/dump`, { params: { lines }, timeout: 60000 }),
  logcatClear: (serial) => http.post(`/adb/devices/${serial}/logcat/clear`),
  analyzeApk: (serial, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post(`/adb/devices/${serial}/apk/package-name`, fd, { timeout: 60000 })
  },
  fsPush: (serial, path, file) => {
    const fd = new FormData()
    fd.append('path', path)
    fd.append('file', file)
    return http.post(`/adb/devices/${serial}/fs/push`, fd, { timeout: 200000 })
  },
  logcatWs: (serial) => `/ws/adb/${serial}/logcat`,
  monkey: (serial, d) => http.post(`/adb/devices/${serial}/monkey`, null, { params: d, timeout: 0 }),
  monkeyStatus: (serial) => http.get(`/adb/devices/${serial}/monkey/status`),
  monkeyStop: (serial) => http.post(`/adb/devices/${serial}/monkey/stop`),
  monkeyReports: (serial) => http.get(`/adb/devices/${serial}/monkey/reports`),
  deleteMonkeyReport: (serial, name) => http.delete(`/adb/devices/${serial}/monkey/reports/${encodeURIComponent(name)}`),
  notifyJobs: (serial, pkg) => http.get(`/adb/devices/${serial}/notify/jobs`, { params: { pkg }, timeout: 30000 }),
  notifyTrigger: (serial, type, jobId, pkg) => http.post(`/adb/devices/${serial}/notify/trigger`, null, { params: { type, job_id: jobId, pkg }, timeout: 60000 }),
  fsList: (serial, path) => http.get(`/adb/devices/${serial}/fs`, { params: { path } }),
  fsPull: (serial, path) => http.post(`/adb/devices/${serial}/fs/pull`, { path }, { timeout: 150000 }),
  logAnalyzeModels: () => http.get('/adb/log-analyze/models'),
  logAnalyze: (serial, lines, modelId) => http.post(`/adb/devices/${serial}/log-analyze`, { lines, model_id: modelId }, { timeout: 150000 }),
  getSettings: () => http.get('/adb/settings'),
  setSettings: (save_dir) => http.post('/adb/settings', { save_dir }),
  browseDir: (path) => http.get('/adb/browse', { params: { path } })
}
export const apiTestApi = {
  cases: (projectId, keyword) => http.get('/apitest/cases', { params: { project_id: projectId, keyword } }),
  createCase: (d) => http.post('/apitest/cases', d),
  updateCase: (id, d) => http.put(`/apitest/cases/${id}`, d),
  deleteCase: (id) => http.delete(`/apitest/cases/${id}`),
  envs: (projectId) => http.get('/apitest/envs', { params: { project_id: projectId } }),
  createEnv: (d) => http.post('/apitest/envs', d),
  updateEnv: (id, d) => http.put(`/apitest/envs/${id}`, d),
  deleteEnv: (id) => http.delete(`/apitest/envs/${id}`),
  run: (d) => http.post('/apitest/run', d, { timeout: 60000 })
}
export const trackingApi = {
  events: (projectId) => http.get('/tracking/events', { params: { project_id: projectId } }),
  ignoreEvents: (projectId, ids, ignored) => http.post('/tracking/events/ignore', { project_id: projectId, ids, ignored }),
  createEvent: (d) => http.post('/tracking/events', d),
  updateEvent: (id, d) => http.patch(`/tracking/events/${id}`, d),
  removeEvent: (id) => http.delete(`/tracking/events/${id}`),
  clearEvents: (projectId) => http.delete('/tracking/events', { params: { project_id: projectId } }),
  resetCounts: (projectId) => http.post('/tracking/events/reset', null, { params: { project_id: projectId } }),
  importCsv: (projectId, file) => {
    const fd = new FormData()
    fd.append('file', file)
    return http.post('/tracking/import', fd, { params: { project_id: projectId } })
  },
  getConfig: (projectId) => http.get('/tracking/config', { params: { project_id: projectId } }),
  saveConfig: (projectId, d) => http.put('/tracking/config', d, { params: { project_id: projectId } }),
  status: (projectId) => http.get('/tracking/status', { params: { project_id: projectId } }),
  adbDevices: () => http.get('/tracking/adb/devices'),
  start: (projectId, serial) => http.post('/tracking/start', null, { params: { project_id: projectId, serial: serial || '' } }),
  stop: (projectId) => http.post('/tracking/stop', null, { params: { project_id: projectId } }),
  templateUrl: () => `/api/v1/tracking/template`,
  exportUrl: (projectId) => `/api/v1/tracking/export?project_id=${projectId}`
}

// ---------- 版本/环境 ----------
export const versionApi = {
  list: (projectId) => http.get('/releases/versions', { params: { project_id: projectId } }),
  create: (d) => http.post('/releases/versions', d),
  update: (id, d) => http.patch(`/releases/versions/${id}`, d),
  remove: (id) => http.delete(`/releases/versions/${id}`)
}
export const envApi = {
  list: () => http.get('/releases/environments'),
  create: (d) => http.post('/releases/environments', d),
  update: (id, d) => http.patch(`/releases/environments/${id}`, d),
  remove: (id) => http.delete(`/releases/environments/${id}`)
}

// ---------- 知识库 ----------
export const knowledgeApi = {
  list: (params) => http.get('/knowledge', { params }),
  create: (d) => http.post('/knowledge', d),
  detail: (id) => http.get(`/knowledge/${id}`),
  update: (id, d) => http.patch(`/knowledge/${id}`, d),
  remove: (id) => http.delete(`/knowledge/${id}`)
}

// ---------- 菜单管理 ----------
export const menuApi = {
  list: () => http.get('/menu-config'),
  save: (d) => http.put('/menu-config', d)
}

// ---------- JMeter 工具 ----------
export const jmeterApi = {
  launch: () => http.post('/jmeter/launch')
}

// ---------- AI ----------
export const modelApi = {
  list: () => http.get('/ai/models'),
  create: (d) => http.post('/ai/models', d),
  update: (id, d) => http.patch(`/ai/models/${id}`, d),
  remove: (id) => http.delete(`/ai/models/${id}`)
}
export const skillApi = {
  list: () => http.get('/ai/skills'),
  create: (d) => http.post('/ai/skills', d),
  update: (id, d) => http.patch(`/ai/skills/${id}`, d),
  remove: (id) => http.delete(`/ai/skills/${id}`)
}
export const promptApi = {
  list: () => http.get('/ai/prompts'),
  create: (d) => http.post('/ai/prompts', d),
  remove: (id) => http.delete(`/ai/prompts/${id}`)
}

// ---------- 附件上传 ----------
export const uploadApi = {
  upload: (file, subdir) => {
    const fd = new FormData()
    fd.append('file', file)
    if (subdir) fd.append('subdir', subdir)
    return http.post('/upload', fd)
  }
}

// ---------- 报表 ----------
export const dashboardApi = {
  summary: (projectId, module) => http.get('/dashboard/summary', { params: { project_id: projectId, module: module } })
}

export default http
