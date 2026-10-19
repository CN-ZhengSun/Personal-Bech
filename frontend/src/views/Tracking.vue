<template>
  <div>
    <div style="display:flex;align-items:center;gap:12px;margin:4px 0 12px">
      <h1 style="margin:0">埋点实时监控</h1>
      <ProjectSelect />
    </div>
    <!-- 控制栏 -->
    <div class="card">
      <div class="form-row">
        <span class="ctl-label">采集方式：</span>
        <label class="radio-inline"><input type="radio" value="adb" v-model="config.collect_type" @change="saveCfg" />ADB 日志采集</label>
        <label class="radio-inline"><input type="radio" value="mitmproxy" v-model="config.collect_type" @change="mitmNotReady" />Mitmproxy 抓包</label>
        <span class="ctl-label">日志TAG</span>
        <input v-model="config.log_tag" style="width:110px" @change="saveCfg" />
        <span class="ctl-label">去重窗口(秒)</span>
        <input v-model.number="config.dedup_window" type="number" min="0" style="width:80px" @change="saveCfg" />
        <span class="ctl-label">上报域名</span>
        <input v-model="domainsText" style="width:220px" placeholder="逗号分隔，如 api.xx.com" @change="saveCfg" />
      </div>
      <div class="form-row" style="margin-bottom:0">
        <button v-if="status !== 'running'" class="btn" @click="startCollect">开始监控</button>
        <button v-else class="btn btn-danger" @click="stopCollect">停止监控</button>
        <label class="btn btn-ghost" style="cursor:pointer">导入清单<input type="file" accept=".csv" style="display:none" @change="onImport" /></label>
        <button class="btn btn-ghost" @click="download(trackingApi.exportUrl(pid))">导出结果</button>
        <button class="btn btn-ghost" @click="download(trackingApi.templateUrl())">模板下载</button>
        <button class="btn btn-ghost" @click="resetCounts">重置计数</button>
        <button class="btn" @click="openCreate">新增埋点</button>
        <button class="btn btn-danger" @click="clearAll">清空清单</button>
      </div>
    </div>

    <!-- 状态栏 -->
    <div class="status-bar">
      <span>当前项目：<b>{{ projectName }}</b></span>
      <span>采集方式：<b>{{ config.collect_type === 'adb' ? 'ADB 日志' : 'Mitmproxy' }}</b></span>
      <span>运行状态：<b :class="status === 'running' ? 'st-run' : 'st-stop'">{{ status === 'running' ? '采集中' : '已停止' }}</b></span>
      <span>ADB：<b :class="adbClass">{{ adbText }}</b></span>
      <span>已触发：<b>{{ triggeredCount }}</b></span>
      <span>未触发：<b>{{ untriggeredCount }}</b></span>
      <span>已忽略：<b>{{ ignoredCount }}</b></span>
      <span>清单总数：<b>{{ events.length }}</b></span>
    </div>

    <!-- ADB 已连接设备 -->
    <div class="adb-bar" v-if="adbLoaded">
      <span class="ctl-label">已连接设备：</span>
      <span v-if="!adbInfo.adb_installed" class="adb-none">{{ adbInfo.error || '未检测到 adb' }}</span>
      <span v-else-if="!adbInfo.devices.length" class="adb-none">无已连接设备，请先 USB 连接真机或启动模拟器</span>
      <template v-else>
        <span class="ctl-label">监控设备：</span>
        <select v-model="monitorSerial" style="width:auto;max-width:320px" :disabled="status === 'running'">
          <option v-for="d in onlineDevices" :key="d.serial" :value="d.serial">
            {{ d.model ? d.model + ' (' + d.serial + ')' : d.serial }}
          </option>
        </select>
        <span v-if="status === 'running' && currentSerial" class="adb-item">采集中：{{ currentSerial }}</span>
        <span v-for="d in adbInfo.devices" :key="d.serial" class="adb-item">
          <span class="dot" :class="d.state === 'device' ? 'dot-ok' : 'dot-bad'"></span>
          {{ d.model ? d.model + ' (' + d.serial + ')' : d.serial }}
          <span class="adb-state" :class="d.state === 'device' ? 'st-run' : 'st-stop'">{{ d.state }}</span>
        </span>
      </template>
      <button class="btn btn-small btn-gray" @click="loadAdb">刷新</button>
    </div>

    <!-- 分组 Tab -->
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'recent' }" @click="activeTab = 'recent'">
        最近触发 <span class="tab-num">{{ recentList.length }}</span>
      </button>
      <button class="tab" :class="{ active: activeTab === 'triggered' }" @click="activeTab = 'triggered'">
        已触发埋点 <span class="tab-num">{{ triggered.length }}</span>
      </button>
      <button class="tab" :class="{ active: activeTab === 'untriggered' }" @click="activeTab = 'untriggered'">
        未触发埋点 <span class="tab-num">{{ untriggered.length }}</span>
      </button>
      <button class="tab" :class="{ active: activeTab === 'ignored' }" @click="activeTab = 'ignored'">
        已忽略 <span class="tab-num">{{ ignoredList.length }}</span>
      </button>
      <button v-if="activeTab !== 'ignored'" class="btn btn-small btn-gray" :disabled="!checkedIds.length" @click="ignoreSelected(true)" style="margin-left:8px">忽略所选({{ checkedIds.length }})</button>
      <button v-else class="btn btn-small btn-gray" :disabled="!checkedIds.length" @click="ignoreSelected(false)" style="margin-left:8px">恢复所选({{ checkedIds.length }})</button>
      <span class="tab-sort">排序：</span>
      <select v-model="sortBy" style="width:130px">
        <option value="recent">最后触发时间</option>
        <option value="name">事件名称</option>
        <option value="count">触发次数</option>
      </select>
      <span class="tab-sort">搜索：</span>
      <input v-model="searchText" class="search-input" placeholder="按事件ID/名称搜索" />
    </div>

    <!-- 最近触发（不限条数，按触发时间倒序，实时置顶+闪烁） -->
    <div class="card" v-if="activeTab === 'recent'">
      <table class="table">
        <thead><tr><th style="width:36px"><input type="checkbox" :checked="isAllChecked(recentList)" @change="toggleAll(recentList)" /></th><th style="width:40px">#</th><th style="width:240px">事件ID/名称</th><th>触发操作/打点含义</th><th style="width:90px">触发次数</th><th style="width:170px">最后触发时间</th><th style="width:90px">操作</th></tr></thead>
        <tbody>
          <tr v-for="(e, i) in recentPaged" :key="e.id" :class="{ flash: flashSet.has(e.event_id) }">
            <td><input type="checkbox" :checked="checkedIds.includes(e.id)" @change="toggleCheck(e.id)" /></td>
            <td>{{ (currentPage - 1) * pageSize + i + 1 }}</td>
            <td><b>{{ e.event_id }}</b><span v-if="e.event_name && e.event_name !== e.event_id" class="sub"> · {{ e.event_name }}</span></td>
            <td class="cell-wrap">{{ e.operation || e.meaning || '—' }}</td>
            <td><span class="cnt">{{ e.trigger_count }}</span></td>
            <td>{{ e.last_triggered_at || '—' }}</td>
            <td>
              <button class="btn btn-small btn-gray" @click="openEdit(e)">编辑</button>
              <button class="btn btn-small btn-danger" @click="removeOne(e)">删除</button>
            </td>
          </tr>
          <tr v-if="!recentPaged.length"><td colspan="7" class="muted center">暂无触发事件，开始监控后实时展示</td></tr>
        </tbody>
      </table>
      <div class="pager">
        <span class="pager-info">共 {{ recentList.length }} 条</span>
        <button class="btn btn-small btn-gray" :disabled="currentPage <= 1" @click="goto(-1, recentList)">上一页</button>
        <span class="pager-page">{{ currentPage }} / {{ pageCount(recentList) }}</span>
        <button class="btn btn-small btn-gray" :disabled="currentPage >= pageCount(recentList)" @click="goto(1, recentList)">下一页</button>
        <select v-model="pageSize" class="pager-size" @change="currentPage = 1">
          <option :value="10">10条/页</option>
          <option :value="20">20条/页</option>
          <option :value="50">50条/页</option>
          <option :value="100">100条/页</option>
        </select>
      </div>
    </div>

    <!-- 已触发埋点 -->
    <div class="card" v-if="activeTab === 'triggered'">
      <table class="table">
        <thead><tr><th style="width:36px"><input type="checkbox" :checked="isAllChecked(triggered)" @change="toggleAll(triggered)" /></th><th style="width:240px">事件ID/名称</th><th>触发操作/打点含义</th><th style="width:90px">触发次数</th><th style="width:170px">最后触发时间</th><th style="width:90px">操作</th></tr></thead>
        <tbody>
          <tr v-for="e in triggeredPaged" :key="e.id">
            <td><input type="checkbox" :checked="checkedIds.includes(e.id)" @change="toggleCheck(e.id)" /></td>
            <td><b>{{ e.event_id }}</b><span v-if="e.event_name && e.event_name !== e.event_id" class="sub"> · {{ e.event_name }}</span></td>
            <td class="cell-wrap">{{ e.operation || e.meaning || '—' }}</td>
            <td><span class="cnt">{{ e.trigger_count }}</span></td>
            <td>{{ e.last_triggered_at || '—' }}</td>
            <td>
              <button class="btn btn-small btn-gray" @click="openEdit(e)">编辑</button>
              <button class="btn btn-small btn-danger" @click="removeOne(e)">删除</button>
            </td>
          </tr>
          <tr v-if="!triggeredPaged.length"><td colspan="6" class="muted center">暂无已触发埋点</td></tr>
        </tbody>
      </table>
      <div class="pager">
        <span class="pager-info">共 {{ triggered.length }} 条</span>
        <button class="btn btn-small btn-gray" :disabled="currentPage <= 1" @click="goto(-1, triggered)">上一页</button>
        <span class="pager-page">{{ currentPage }} / {{ pageCount(triggered) }}</span>
        <button class="btn btn-small btn-gray" :disabled="currentPage >= pageCount(triggered)" @click="goto(1, triggered)">下一页</button>
        <select v-model="pageSize" class="pager-size" @change="currentPage = 1">
          <option :value="10">10条/页</option>
          <option :value="20">20条/页</option>
          <option :value="50">50条/页</option>
          <option :value="100">100条/页</option>
        </select>
      </div>
    </div>

    <!-- 未触发埋点 -->
    <div class="card" v-if="activeTab === 'untriggered'">
      <table class="table">
        <thead><tr><th style="width:36px"><input type="checkbox" :checked="isAllChecked(untriggered)" @change="toggleAll(untriggered)" /></th><th style="width:240px">事件ID/名称</th><th>触发操作/打点含义</th><th style="width:90px">触发次数</th><th style="width:170px">最后触发时间</th><th style="width:90px">操作</th></tr></thead>
        <tbody>
          <tr v-for="e in untriggeredPaged" :key="e.id">
            <td><input type="checkbox" :checked="checkedIds.includes(e.id)" @change="toggleCheck(e.id)" /></td>
            <td class="untag"><b>{{ e.event_id }}</b><span v-if="e.event_name && e.event_name !== e.event_id" class="sub"> · {{ e.event_name }}</span></td>
            <td class="cell-wrap untag">{{ e.operation || e.meaning || '—' }}</td>
            <td><span class="cnt muted">0</span></td>
            <td class="muted">—</td>
            <td>
              <button class="btn btn-small btn-gray" @click="openEdit(e)">编辑</button>
              <button class="btn btn-small btn-danger" @click="removeOne(e)">删除</button>
            </td>
          </tr>
          <tr v-if="!untriggeredPaged.length"><td colspan="6" class="muted center">清单内所有埋点均已触发</td></tr>
        </tbody>
      </table>
      <div class="pager">
        <span class="pager-info">共 {{ untriggered.length }} 条</span>
        <button class="btn btn-small btn-gray" :disabled="currentPage <= 1" @click="goto(-1, untriggered)">上一页</button>
        <span class="pager-page">{{ currentPage }} / {{ pageCount(untriggered) }}</span>
        <button class="btn btn-small btn-gray" :disabled="currentPage >= pageCount(untriggered)" @click="goto(1, untriggered)">下一页</button>
        <select v-model="pageSize" class="pager-size" @change="currentPage = 1">
          <option :value="10">10条/页</option>
          <option :value="20">20条/页</option>
          <option :value="50">50条/页</option>
          <option :value="100">100条/页</option>
        </select>
      </div>
    </div>

    <!-- 已忽略埋点（清单级忽略，不参与监控匹配；可勾选恢复） -->
    <div class="card" v-if="activeTab === 'ignored'">
      <table class="table">
        <thead><tr><th style="width:36px"><input type="checkbox" :checked="isAllChecked(ignoredList)" @change="toggleAll(ignoredList)" /></th><th style="width:240px">事件ID/名称</th><th>触发操作/打点含义</th><th style="width:90px">触发次数</th><th style="width:170px">最后触发时间</th><th style="width:90px">操作</th></tr></thead>
        <tbody>
          <tr v-for="e in ignoredPaged" :key="e.id" class="row-ignored">
            <td><input type="checkbox" :checked="checkedIds.includes(e.id)" @change="toggleCheck(e.id)" /></td>
            <td><b>{{ e.event_id }}</b><span v-if="e.event_name && e.event_name !== e.event_id" class="sub"> · {{ e.event_name }}</span><span class="tag tag-gray" style="margin-left:6px">已忽略</span></td>
            <td class="cell-wrap">{{ e.operation || e.meaning || '—' }}</td>
            <td><span class="cnt">{{ e.trigger_count }}</span></td>
            <td>{{ e.last_triggered_at || '—' }}</td>
            <td>
              <button class="btn btn-small btn-gray" @click="openEdit(e)">编辑</button>
              <button class="btn btn-small btn-danger" @click="removeOne(e)">删除</button>
            </td>
          </tr>
          <tr v-if="!ignoredPaged.length"><td colspan="6" class="muted center">暂无已忽略埋点</td></tr>
        </tbody>
      </table>
      <div class="pager">
        <span class="pager-info">共 {{ ignoredList.length }} 条</span>
        <button class="btn btn-small btn-gray" :disabled="currentPage <= 1" @click="goto(-1, ignoredList)">上一页</button>
        <span class="pager-page">{{ currentPage }} / {{ pageCount(ignoredList) }}</span>
        <button class="btn btn-small btn-gray" :disabled="currentPage >= pageCount(ignoredList)" @click="goto(1, ignoredList)">下一页</button>
        <select v-model="pageSize" class="pager-size" @change="currentPage = 1">
          <option :value="10">10条/页</option>
          <option :value="20">20条/页</option>
          <option :value="50">50条/页</option>
          <option :value="100">100条/页</option>
        </select>
      </div>
    </div>

    <!-- 新增/编辑埋点弹窗 -->
    <div class="modal-mask" v-if="showForm">
      <div class="modal">
        <h3>{{ editingId ? '编辑埋点' : '新增埋点' }}</h3>
        <div class="field"><label>事件ID *</label><input v-model="form.event_id" placeholder="如 ad_load_failed_x" /></div>
        <div class="field"><label>事件名称</label><input v-model="form.event_name" placeholder="如 广告加载失败" /></div>
        <div class="field"><label>触发操作/打点含义</label><textarea v-model="form.operation" placeholder="触发该埋点的操作或打点含义"></textarea></div>
        <div class="field"><label>备注</label><textarea v-model="form.meaning" placeholder="补充说明"></textarea></div>
        <div class="actions">
          <button class="btn btn-gray" @click="showForm = false">取消</button>
          <button class="btn" @click="saveForm">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { trackingApi, projectApi } from '../api'
import ProjectSelect from '../components/ProjectSelect.vue'

const pid = () => {
  const n = Number(localStorage.getItem('twb_project'))
  return Number.isInteger(n) && n > 0 ? n : 0
}
const events = ref([])
const config = ref({ collect_type: 'adb', log_tag: 'EM', batch_rule: '', domains: [], dedup_window: 3 })
const domainsText = ref('')
const status = ref('stopped')
const sortBy = ref('recent')
const activeTab = ref('recent')
const searchText = ref('')
const pageSize = ref(10)
const currentPage = ref(1)
const showForm = ref(false)
const editingId = ref(null)
const form = ref({ event_id: '', event_name: '', operation: '', meaning: '' })
const flashSet = ref(new Set())
const projectName = ref('')
const adbInfo = ref({ adb_installed: false, devices: [], error: '' })
const adbLoaded = ref(false)
const monitorSerial = ref('')
const currentSerial = ref('')
const onlineDevices = computed(() => adbInfo.value.devices.filter(d => d.state === 'device'))
const adbText = computed(() => {
  if (!adbInfo.value.adb_installed) return '未安装'
  const n = adbInfo.value.devices.length
  if (n === 0) return '无设备'
  const ok = adbInfo.value.devices.filter(d => d.state === 'device').length
  return `${ok}/${n} 台`
})
const adbClass = computed(() => {
  if (!adbInfo.value.adb_installed || adbInfo.value.devices.length === 0) return 'st-stop'
  return 'st-run'
})
async function loadAdb() {
  try {
    const { data } = await trackingApi.adbDevices()
    adbInfo.value = data
    adbLoaded.value = true
    // 默认选中第一台在线设备；若当前选中已离线则重置
    const online = (data.devices || []).filter(d => d.state === 'device')
    if (!online.some(d => d.serial === monitorSerial.value)) {
      monitorSerial.value = online.length ? online[0].serial : ''
    }
  } catch (err) {
    adbInfo.value = { adb_installed: false, devices: [], error: '查询失败' }
    adbLoaded.value = true
  }
}

const triggeredCount = computed(() => events.value.filter(e => e.trigger_count > 0 && !e.is_ignored).length)
const untriggeredCount = computed(() => events.value.filter(e => e.trigger_count === 0 && !e.is_ignored).length)
const ignoredCount = computed(() => events.value.filter(e => e.is_ignored).length)
const byTime = (a, b) => (b.last_triggered_at || '').localeCompare(a.last_triggered_at || '')
// 搜索过滤：按事件ID/名称/触发操作
function matchSearch(e) {
  const kw = searchText.value.trim().toLowerCase()
  if (!kw) return true
  return (e.event_id || '').toLowerCase().includes(kw)
    || (e.event_name || '').toLowerCase().includes(kw)
    || (e.operation || '').toLowerCase().includes(kw)
}
// 最近触发：所有已触发事件按最后触发时间倒序，条数不限（忽略的事件不展示）
const recentList = computed(() => [...events.value].filter(e => e.trigger_count > 0 && !e.is_ignored && matchSearch(e)).sort(byTime))
const triggered = computed(() => events.value.filter(e => e.trigger_count > 0 && !e.is_ignored && matchSearch(e)).sort(byTime))
const untriggered = computed(() => events.value.filter(e => e.trigger_count === 0 && !e.is_ignored && matchSearch(e)))
const ignoredList = computed(() => events.value.filter(e => e.is_ignored && matchSearch(e)).sort(byTime))
// 分页
function pageCount(list) {
  return Math.max(1, Math.ceil(list.length / pageSize.value))
}
function paged(list) {
  const start = (currentPage.value - 1) * pageSize.value
  return list.slice(start, start + pageSize.value)
}
function goto(delta, list) {
  currentPage.value = Math.max(1, Math.min(currentPage.value + delta, pageCount(list)))
}
const recentPaged = computed(() => paged(recentList.value))
const triggeredPaged = computed(() => paged(sortList(triggered.value)))
const untriggeredPaged = computed(() => paged(sortList(untriggered.value)))
const ignoredPaged = computed(() => paged(sortList(ignoredList.value)))

function sortList(list) {
  if (sortBy.value === 'name') return [...list].sort((a, b) => (a.event_id || '').localeCompare(b.event_id || ''))
  if (sortBy.value === 'count') return [...list].sort((a, b) => b.trigger_count - a.trigger_count)
  return list
}

// ---------- 清单勾选忽略 ----------
const checkedIds = ref([])
function toggleCheck(id) {
  const i = checkedIds.value.indexOf(id)
  if (i >= 0) checkedIds.value.splice(i, 1)
  else checkedIds.value.push(id)
}
function toggleAll(list) {
  const ids = list.map(e => e.id)
  const allOn = ids.length > 0 && ids.every(id => checkedIds.value.includes(id))
  if (allOn) checkedIds.value = checkedIds.value.filter(id => !ids.includes(id))
  else checkedIds.value = [...new Set([...checkedIds.value, ...ids])]
}
function isAllChecked(list) {
  return list.length > 0 && list.every(e => checkedIds.value.includes(e.id))
}
async function ignoreSelected(ignored) {
  if (!pid()) return window.$toast.warning('请先选择项目')
  if (!checkedIds.value.length) return window.$toast.warning(ignored ? '请先勾选要忽略的事件' : '请先勾选要恢复的事件')
  try {
    await trackingApi.ignoreEvents(pid(), checkedIds.value, ignored)
    window.$toast.success(ignored ? `已忽略 ${checkedIds.value.length} 个事件` : `已恢复 ${checkedIds.value.length} 个事件`)
    checkedIds.value = []
    load()
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '操作失败')
  }
}

let ws = null
function connectWs() {
  try {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    ws = new WebSocket(`${proto}://${location.host}/ws/tracking`)
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data)
        handleTrigger(d)
      } catch {}
    }
    ws.onclose = () => { ws = null; setTimeout(connectWs, 3000) }
  } catch {}
}
function handleTrigger(d) {
  if (d.project_id !== pid()) return
  const ev = events.value.find(x => x.event_id === d.event_id)
  if (!ev) return
  ev.trigger_count = d.trigger_count
  ev.last_triggered_at = d.last_triggered_at
  flashSet.value.add(d.event_id)
  setTimeout(() => { flashSet.value.delete(d.event_id) }, 800)
}

async function load() {
  if (!pid()) return window.$toast.warning('请先在上方选择项目')
  try {
    const [evs, cfg, st, projs] = await Promise.all([
      trackingApi.events(pid()), trackingApi.getConfig(pid()), trackingApi.status(pid()), projectApi.list()
    ])
    events.value = evs.data
    config.value = cfg.data
    const dm = cfg.data.domains
    domainsText.value = Array.isArray(dm) ? dm.join(',') : String(dm || '').replace(/^\[|\]$/g, '')
    status.value = st.data.status
    currentSerial.value = st.data.serial || ''
    const p = projs.data.find(x => x.id === pid())
    projectName.value = p ? p.name : ''
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '加载失败')
  }
}
async function saveCfg() {
  const d = { ...config.value, domains: domainsText.value.split(',').map(s => s.trim()).filter(Boolean) }
  try {
    const { data } = await trackingApi.saveConfig(pid(), d)
    config.value = data
    window.$toast.success('配置已保存')
  } catch (err) {
    window.$toast.error(err.response?.data?.detail || '保存配置失败')
  }
}
function mitmNotReady() {
  config.value.collect_type = 'adb'
  window.$toast.warning('Mitmproxy 采集需安装 mitmproxy 后使用，V1.1 提供')
}
async function startCollect() {
  if (!pid()) {
    window.$toast.warning('请先选择项目后再开始监控')
    return
  }
  if (!monitorSerial.value) {
    window.$toast.warning('请先在「已连接设备」中选择监控设备')
    return
  }
  try {
    const { data } = await trackingApi.start(pid(), monitorSerial.value)
    status.value = data.status
    currentSerial.value = data.serial || monitorSerial.value
    window.$toast.success('已开始监控：' + currentSerial.value)
  } catch (err) { window.$toast.error(err.response?.data?.detail || '启动失败') }
}
async function stopCollect() {
  try {
    await trackingApi.stop(pid())
    status.value = 'stopped'
    currentSerial.value = ''
    window.$toast.success('已停止监控')
  } catch (err) { window.$toast.error(err.response?.data?.detail || '停止失败') }
}
async function onImport(ev) {
  const file = ev.target.files[0]
  ev.target.value = ''
  if (!file) return
  if (!pid()) {
    window.$toast.warning('请先选择项目再导入埋点清单')
    return
  }
  try {
    const { data } = await trackingApi.importCsv(pid(), file)
    let msg = `导入 ${data.imported} 条`
    if (data.duplicated) msg += `，跳过重复 ${data.duplicated} 条`
    if (data.errors?.length) msg += `，错误 ${data.errors.length} 条：${data.errors.join('；')}`
    window.$toast[data.imported ? 'success' : 'error'](msg)
    load()
  } catch (err) { window.$toast.error(err.response?.data?.detail || '导入失败') }
}
async function download(url) {
  if (!pid() && url.includes('/export')) {
    window.$toast.warning('请先选择项目再导出结果')
    return
  }
  try {
    const res = await fetch(url, { credentials: 'same-origin' })
    const blob = await res.blob()
    const a = document.createElement('a')
    const objUrl = URL.createObjectURL(blob)
    a.href = objUrl
    const cd = res.headers.get('Content-Disposition') || ''
    const m = cd.match(/filename\*=UTF-8''([^;]+)/)
    a.download = m ? decodeURIComponent(m[1]) : 'download.csv'
    document.body.appendChild(a); a.click(); a.remove()
    URL.revokeObjectURL(objUrl)
  } catch (err) { window.$toast.error('下载失败') }
}
async function resetCounts() {
  if (!(await window.$confirm('确认清空所有埋点的触发次数？', { danger: true }))) return
  await trackingApi.resetCounts(pid())
  events.value.forEach(e => { e.trigger_count = 0; e.last_triggered_at = null })
  window.$toast.success('计数已重置')
}
async function clearAll() {
  if (!(await window.$confirm('确认清空当前项目全部埋点清单？', { danger: true }))) return
  await trackingApi.clearEvents(pid())
  events.value = []
  window.$toast.success('清单已清空')
}
function openCreate() {
  editingId.value = null
  form.value = { event_id: '', event_name: '', operation: '', meaning: '' }
  showForm.value = true
}
function openEdit(e) {
  editingId.value = e.id
  form.value = { event_id: e.event_id, event_name: e.event_name || '', operation: e.operation || '', meaning: e.meaning || '' }
  showForm.value = true
}
async function saveForm() {
  if (!form.value.event_id) return window.$toast.warning('请填写事件ID')
  try {
    if (editingId.value) {
      await trackingApi.updateEvent(editingId.value, form.value)
      window.$toast.success('埋点已更新')
    } else {
      await trackingApi.createEvent({ project_id: pid(), ...form.value })
      window.$toast.success('埋点已新增')
    }
    showForm.value = false
    load()
  } catch (err) { window.$toast.error(err.response?.data?.detail || '保存失败') }
}
async function removeOne(e) {
  if (!(await window.$confirm(`确认删除埋点「${e.event_id}」？`, { danger: true }))) return
  await trackingApi.removeEvent(e.id)
  window.$toast.success('已删除')
  load()
}

onMounted(() => { load(); loadAdb(); connectWs() })
onBeforeUnmount(() => { if (ws) { ws.onclose = null; ws.close() } })
// 项目切换由 App.vue 全局事件驱动组件重建（localStorage 非响应式，watch 不可靠），此处无需再监听
watch([searchText, activeTab, sortBy], () => { currentPage.value = 1 })
</script>

<style scoped>
.ctl-label { font-size: 13px; color: #64748b; }
.radio-inline { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; color: #1f2329; }
.radio-inline input { width: auto; min-width: auto; margin: 0; }
.btn-ghost { background: #eef2f7; color: #1f2329; }
.btn-ghost:hover { background: #e2e8f0; }
.status-bar { display: flex; gap: 24px; flex-wrap: wrap; background: #fff; border-radius: 8px; padding: 10px 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); font-size: 13px; }
.st-run { color: #059669; }
.st-stop { color: #dc2626; }
.sub { color: #8896a7; font-size: 12px; }
.cell-wrap { white-space: pre-wrap; word-break: break-all; }
.cnt { font-weight: 600; color: #2563eb; }
.row-ignored td { color: #9aa4b2; }
.row-ignored .cnt { color: #9aa4b2; }
.untag { color: #dc2626; }
.center { text-align: center; }
.adb-bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 16px; margin-bottom: 16px; font-size: 13px; }
.adb-item { display: inline-flex; align-items: center; gap: 6px; background: #fff; border: 1px solid #e2e8f0; border-radius: 6px; padding: 3px 10px; color: #1f2329; }
.adb-state { font-size: 12px; }
.adb-none { color: #dc2626; }
.dot-ok { background: #059669; }
.dot-bad { background: #dc2626; }
.flash { background: #dbeafe !important; animation: flashbg 0.8s ease; }
@keyframes flashbg { from { background: #bfdbfe; } to { background: #dbeafe; } }
/* 分组 Tab */
.tabs { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.tab { padding: 7px 16px; border: 1px solid #e2e8f0; background: #fff; border-radius: 6px; font-size: 13px; color: #475569; cursor: pointer; }
.tab:hover { background: #f1f5f9; }
.tab.active { background: #2563eb; border-color: #2563eb; color: #fff; }
.tab-num { display: inline-block; min-width: 18px; padding: 0 5px; border-radius: 9px; background: rgba(0,0,0,.12); font-size: 12px; margin-left: 4px; text-align: center; }
.tab.active .tab-num { background: rgba(255,255,255,.25); }
.tab-sort { font-size: 13px; color: #64748b; margin-left: auto; }
.search-input { width: 200px; font-size: 13px; padding: 6px 10px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; color: #1f2329; }
.search-input:focus { border-color: #2563eb; outline: none; }
/* 分页 */
.pager { display: flex; align-items: center; gap: 10px; margin-top: 10px; font-size: 13px; color: #475569; }
.pager-info { color: #64748b; }
.pager-page { min-width: 60px; text-align: center; }
.pager-size { width: 100px; font-size: 13px; padding: 5px 6px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; color: #1f2329; }
</style>
