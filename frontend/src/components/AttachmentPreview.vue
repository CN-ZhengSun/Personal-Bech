<template>
  <div class="modal-mask" v-if="visible" @click.self="close">
    <div class="modal preview-modal">
      <div class="preview-head">
        <h3 class="preview-title" :title="name">{{ name }}</h3>
        <div class="preview-actions">
          <a :href="url" class="btn btn-small" download>下载</a>
          <button class="btn btn-small btn-gray" @click="close">关闭</button>
        </div>
      </div>
      <div class="preview-body">
        <img v-if="kind === 'image'" :src="url" class="preview-img" :alt="name" />
        <iframe v-else-if="kind === 'pdf'" :src="url" class="preview-frame"></iframe>
        <video v-else-if="kind === 'video'" :src="url" controls autoplay class="preview-frame"></video>
        <pre v-else-if="kind === 'text'" class="preview-text">{{ textContent || '（文件内容为空或无法读取）' }}</pre>
        <div v-else-if="kind === 'word'" ref="docxBox" class="preview-scroll"></div>
        <div v-else-if="kind === 'excel'" class="preview-scroll excel-box">
          <div v-for="(sh, si) in sheets" :key="si" class="sheet-block">
            <div class="sheet-name">{{ sh.name }}</div>
            <div class="sheet-table" v-html="sh.html"></div>
          </div>
        </div>
        <div v-else-if="kind === 'ppt'" class="preview-scroll ppt-slides">
          <div v-for="(s, si) in pptSlides" :key="si" class="ppt-slide">
            <div class="ppt-slide-head">第 {{ s.no }} 页</div>
            <div class="ppt-slide-body">
              <img v-for="(im, ii) in s.images" :key="ii" :src="im.url" class="ppt-slide-img" :alt="im.name" />
              <p v-for="(t, ti) in s.texts" :key="ti" class="ppt-slide-text">{{ t }}</p>
              <p v-if="!s.texts.length && !s.images.length" class="muted">（本页无文字内容）</p>
            </div>
          </div>
        </div>
        <div v-else-if="kind === 'xmind'" class="xmind-box me-host">
          <div class="xmind-toolbar" v-if="meSheets.length > 1">
            <span v-for="(sh, si) in meSheets" :key="si" class="xmind-tab"
              :class="{ active: si === meCur }" @click="meSwitch(si)">{{ sh.title }}</span>
          </div>
          <div ref="meBox" class="me-canvas"></div>
          <div v-if="fvErr" class="muted preview-note">该 xmind 文件解析失败，可下载后查看。</div>
        </div>
        <div v-else class="muted preview-note">该类型暂不支持在线预览，可下载后查看。</div>
        <div v-if="errMsg" class="preview-err">{{ errMsg }}</div>
        <div v-if="loading" class="preview-loading"><span>正在加载「{{ name }}」…</span></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { renderAsync } from 'docx-preview'
import * as XLSX from 'xlsx'
import JSZip from 'jszip'
import MindElixir from 'mind-elixir'
import '../assets/mind-elixir.css'
import { importXMindFile, convertXmindToMindElixir } from '@mind-elixir/import-xmind'

const props = defineProps({ url: String, name: String, visible: Boolean })
const emit = defineEmits(['close'])

const loading = ref(false)
const textContent = ref('')
const fvErr = ref(false)

// ---- xmind：MindElixir 渲染 ----
const meSheets = ref([])
const meCur = ref(0)
const meBox = ref(null)
let meInst = null
// 把 xmind 的 summary/概要节点并入 attached，避免解析丢失；并返回 File
async function xmindFileWithSummary(buf, name) {
  const zip = await JSZip.loadAsync(buf)
  if (!zip.files['content.json']) return new File([buf], name, { type: 'application/octet-stream' })
  const data = JSON.parse(await zip.files['content.json'].async('string'))
  function merge(n) {
    const ch = n.children || {}
    const merged = [...(ch.attached || []), ...(ch.summary || [])]
    if (merged.length) n.children = { ...ch, attached: merged, summary: [], detached: ch.detached || [] }
    for (const k of ['attached', 'summary', 'detached']) for (const c of ch[k] || []) merge(c)
  }
  ;(Array.isArray(data) ? data : [data]).forEach((sh) => { if (sh && sh.rootTopic) merge(sh.rootTopic) })
  zip.file('content.json', JSON.stringify(data))
  const out = await zip.generateAsync({ type: 'blob' })
  return new File([out], name, { type: 'application/octet-stream' })
}
async function loadXmindME() {
  if (!props.url || !meBox.value) return
  meSheets.value = []
  meCur.value = 0
  fvErr.value = false
  try {
    meInst && meInst.destroy && meInst.destroy()
    meInst = null
    const res = await fetch(props.url)
    if (!res.ok) throw new Error('HTTP ' + res.status)
    const buf = await res.arrayBuffer()
    const file = await xmindFileWithSummary(buf, props.name || 'mindmap.xmind')
    const sheets = await importXMindFile(file)
    if (!sheets || !sheets.length) throw new Error('未解析到画布')
    meSheets.value = sheets.map((s) => ({ title: s.title || '画布', data: s }))
    renderME(0)
  } catch (e) {
    console.error('[xmind] load failed:', e)
    fvErr.value = true
  }
}
function renderME(i) {
  if (!meBox.value || !meSheets.value[i]) return
  try {
    meInst && meInst.destroy && meInst.destroy()
    meInst = null
    const data = convertXmindToMindElixir(meSheets.value[i].data)
    // 强制全部展开（xmind 里折叠保存的分支也要显示），保证内容完整可见
    ;(function expandAll(n) {
      n.expanded = true
      for (const c of n.children || []) expandAll(c)
    })(data.nodeData)
    meInst = new MindElixir({ el: meBox.value, direction: MindElixir.SIDE, draggable: false, contextMenu: false, nodeMenu: false })
    meInst.init(data)
    meInst.fit && meInst.fit()
  } catch (e) {
    console.error('[xmind] render failed:', e)
    fvErr.value = true
  }
}
function meSwitch(i) {
  meCur.value = i
  renderME(i)
}
watch(() => props.url, () => {
  if (props.visible) nextTick(() => loadXmindME())
})
const sheets = ref([])
const pptSlides = ref([])
const errMsg = ref('')
const docxBox = ref(null)

// ---- xmind 预览状态 ----
const xmSheets = ref([])       // [{id, title, root}]
const xmCur = ref(0)           // 当前画布索引
const xmZoom = ref(1)          // 缩放系数
const xmCanvasBox = ref(null)  // 画布容器（用于 fit 计算）
const XM_NODE_H = 34
const XM_LEVEL_W = 170
const XM_V_GAP = 12
const XM_MAX_W = 300

// 解析 content.json 树：{...node} -> {id, title, children: []}（attached/detached/summary 全部纳入）
function xmBuildTree(node) {
  const title = (node.title || '').trim() || '（无标题）'
  const out = { id: node.id || ('n' + Math.random().toString(36).slice(2)), title }
  const ch = node.children || {}
  const kids = []
  for (const key of ['attached', 'detached', 'summary']) {
    for (const c of ch[key] || []) kids.push(xmBuildTree(c))
  }
  if (kids.length) out.children = kids
  return out
}
// 标题拆行（保留原始换行）并计算节点宽高
function xmLines(title) {
  const lines = String(title).split('\n').map((s) => s.trim()).filter((s) => s !== '')
  return lines.length ? lines : ['（无标题）']
}
function xmEstW(t) {
  let w = 0
  for (const ch of t) w += /[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(ch) ? 15 : 8
  return Math.min(Math.max(70, w + 26), XM_MAX_W)
}
// 按节点宽截断单行（显示省略号，完整文本用 title 提示）
function xmTrimLine(l, w) {
  let tw = 0
  for (let i = 0; i < l.length; i++) {
    tw += /[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(l[i]) ? 15 : 8
    if (tw > w - 14) return l.slice(0, i) + '…'
  }
  return l
}
// 布局：计算坐标（x 按层级、y 递归堆叠），返回 {nodes, edges, W, H}
function xmLayout(root) {
  const nodes = []
  const edges = []
  let seq = 0
  let maxDepth = 0
  const LINE_H = 20
  function calc(node, depth) {
    node.depth = depth
    if (depth > maxDepth) maxDepth = depth
    node.lines = xmLines(node.title)
    node.w = Math.max(...node.lines.map(xmEstW))
    node.h = Math.max(XM_NODE_H, 14 + node.lines.length * LINE_H)
    node.dispLines = node.lines.map((l) => xmTrimLine(l, node.w))
    const kids = node.children || []
    let h = 0
    for (const c of kids) { calc(c, depth + 1); h += c.subH + XM_V_GAP }
    node.subH = kids.length ? Math.max(h - XM_V_GAP, node.h) : node.h
  }
  function place(node, x, yTop) {
    const cx = yTop + node.subH / 2
    node.x = x
    node.y = cx - node.h / 2
    nodes.push({ id: node.id, depth: node.depth, x: node.x, y: node.y, w: node.w, h: node.h, lines: node.dispLines, full: node.title })
    let y = yTop
    for (const c of node.children || []) {
      place(c, x + XM_LEVEL_W, y)
      edges.push({ id: 'e' + (seq++), d: xmEdgePath(x + node.w, cx, x + XM_LEVEL_W, y + c.subH / 2) })
      y += c.subH + XM_V_GAP
    }
  }
  calc(root, 0)
  place(root, 24, 24)
  const W = 24 + root.w + maxDepth * XM_LEVEL_W + XM_LEVEL_W + 60
  const H = 24 + root.subH + 48
  return { nodes, edges, W, H }
}
function xmEdgePath(x1, y1, x2, y2) {
  const mx = (x1 + x2) / 2
  return `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`
}

const xmCurSheet = computed(() => xmSheets.value[xmCur.value] || null)
const xmLayoutData = ref({ nodes: [], edges: [], W: 800, H: 400 })
const xmNodes = computed(() => xmLayoutData.value.nodes)
const xmEdges = computed(() => xmLayoutData.value.edges)
const xmSvgW = computed(() => Math.max(100, xmLayoutData.value.W * xmZoom.value))
const xmSvgH = computed(() => Math.max(100, xmLayoutData.value.H * xmZoom.value))
function xmFit() {
  const box = xmCanvasBox.value
  if (!box || !xmCurSheet.value) return
  const { W } = xmLayoutData.value
  // 优先适配宽度（纵向超长可滚动），保证节点可读
  const z = box.clientWidth / W
  xmZoom.value = Math.min(Math.max(z, 0.4), 1.2)
}
function xmZoomBy(f) {
  xmZoom.value = Math.min(Math.max(xmZoom.value * f, 0.2), 3)
}
function xmOnWheel(ev) {
  const f = ev.deltaY > 0 ? 0.9 : 1.1
  xmZoom.value = Math.min(Math.max(xmZoom.value * f, 0.2), 3)
}
watch(xmCur, () => {
  const sh = xmCurSheet.value
  if (sh) { xmLayoutData.value = xmLayout(sh.root); xmFit() }
})
async function loadXmind(buf) {
  const zip = await JSZip.loadAsync(buf)
  let data = null
  if (zip.files['content.json']) {
    data = JSON.parse(await zip.files['content.json'].async('string'))
  }
  if (!data) {
    // 兼容老版本 content.xml（简单抽取 <topic> 标题）
    const xmlName = Object.keys(zip.files).find((n) => n.endsWith('content.xml'))
    if (xmlName) {
      const xml = await zip.files[xmlName].async('string')
      const rootMatch = /<topic[^>]*>([\s\S]*?)<\/topic>/.exec(xml)
      const titles = [...xml.matchAll(/<title>([\s\S]*?)<\/title>/g)].map((m) => m[1].trim()).filter(Boolean)
      if (titles.length) {
        data = [{ id: 'legacy', title: titles[0], rootTopic: { title: titles[0], children: { attached: titles.slice(1).map((t) => ({ title: t })) } } }]
      }
    }
  }
  if (!data) { xmSheets.value = []; return }
  xmSheets.value = (Array.isArray(data) ? data : [data]).map((sh, i) => {
    const rt = (sh && sh.rootTopic) || {}
    return { id: sh.id || ('s' + i), title: (sh.title || '').trim() || ('画布 ' + (i + 1)), root: xmBuildTree(rt) }
  })
  xmCur.value = 0
  await nextTick()
  const sh = xmSheets.value[0]
  if (sh) { xmLayoutData.value = xmLayout(sh.root); xmFit() }
}

const ext = computed(() => {
  const m = (props.name || '').match(/\.([A-Za-z0-9]+)$/)
  return m ? m[1].toLowerCase() : ''
})
const kind = computed(() => {
  const e = ext.value
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'svg'].includes(e)) return 'image'
  if (e === 'pdf') return 'pdf'
  if (['mp4', 'mov', 'avi', 'mkv', 'webm', 'm4v', 'flv', 'wmv', 'mpg', 'mpeg'].includes(e)) return 'video'
  if (['txt', 'md', 'log'].includes(e)) return 'text'
  if (e === 'docx') return 'word'
  if (['xlsx', 'xls'].includes(e)) return 'excel'
  if (e === 'pptx') return 'ppt'
  if (e === 'xmind') return 'xmind'
  return 'unknown'
})

async function loadPpt(buf) {
  const zip = await JSZip.loadAsync(buf)
  const slideFiles = Object.keys(zip.files)
    .filter((n) => /ppt\/slides\/slide\d+\.xml$/.test(n))
    .sort((a, b) => parseInt(a.match(/slide(\d+)/)[1], 10) - parseInt(b.match(/slide(\d+)/)[1], 10))
  const out = []
  for (const name of slideFiles) {
    const no = parseInt(name.match(/slide(\d+)/)[1], 10)
    const slideText = await zip.files[name].async('string')
    const texts = [...slideText.matchAll(/<a:t>([\s\S]*?)<\/a:t>/g)].map((m) => m[1].trim()).filter((t) => t)
    // 解析本页图片（通过 rels 找 media 文件）
    const relsName = name.replace(/slides\/(slide\d+\.xml)$/, 'slides/_rels/$1.rels')
    const images = []
    if (zip.files[relsName]) {
      const rels = await zip.files[relsName].async('string')
      const relMap = {}
      for (const m of [...rels.matchAll(/Id="(rId\d+)"[^>]*Target="([^"]+)"/g)]) relMap[m[1]] = m[2]
      const embeds = [...new Set([...slideText.matchAll(/r:embed="(rId\d+)"/g)].map((m) => m[1]))]
      for (const rid of embeds) {
        const target = relMap[rid]
        if (!target) continue
        const mediaName = 'ppt/' + target.replace(/^\.\.\//, '').replace(/^\//, '')
        const mf = zip.files[mediaName]
        if (mf) {
          const blob = await mf.async('blob')
          images.push({ url: URL.createObjectURL(blob), name: mediaName.split('/').pop() })
        }
      }
    }
    out.push({ no, texts, images })
  }
  return out
}

async function load() {
  if (!props.visible || !props.url) return
  const k = kind.value
  loading.value = true
  errMsg.value = ''
  textContent.value = ''
  sheets.value = []
  pptSlides.value = []
  xmSheets.value = []
  xmZoom.value = 1
  meSheets.value = []
  meCur.value = 0
  if (meInst) { meInst.destroy && meInst.destroy(); meInst = null }
  await nextTick()
  try {
    if (k === 'text') {
      const buf = await fetch(props.url).then((r) => r.arrayBuffer())
      textContent.value = new TextDecoder('utf-8').decode(buf)
    } else if (k === 'word') {
      if (!docxBox.value) return
      docxBox.value.innerHTML = ''
      const blob = await fetch(props.url).then((r) => r.blob())
      await renderAsync(blob, docxBox.value)
    } else if (k === 'excel') {
      const buf = await fetch(props.url).then((r) => r.arrayBuffer())
      const wb = XLSX.read(buf)
      sheets.value = wb.SheetNames.map((nm) => {
        const ws = wb.Sheets[nm]
        return { name: nm, html: XLSX.utils.sheet_to_html(ws) }
      })
    } else if (k === 'ppt') {
      const buf = await fetch(props.url).then((r) => r.arrayBuffer())
      pptSlides.value = await loadPpt(buf)
    } else if (k === 'xmind') {
      await loadXmindME()
    }
  } catch (err) {
    errMsg.value = '加载失败：' + (err && err.message ? err.message : err)
  } finally {
    loading.value = false
  }
}

watch(() => props.visible, (v) => { if (v) load() })

function close() { emit('close') }
</script>

<style scoped>
.preview-modal {
  width: min(920px, 92vw);
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  padding: 0;
  overflow: hidden;
}
.preview-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}
.preview-title {
  margin: 0;
  font-size: 15px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.preview-actions { display: flex; gap: 8px; flex-shrink: 0; }
.preview-body {
  position: relative;
  flex: 1;
  min-height: 0;
  padding: 14px 16px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  background: #fff;
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", "Helvetica Neue", Arial, sans-serif;
}
.preview-img {
  max-width: 100%;
  max-height: 64vh;
  object-fit: contain;
  margin: 0 auto;
}
.preview-frame {
  width: 100%;
  height: 64vh;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #fafafa;
}
.preview-text {
  margin: 0;
  padding: 12px;
  max-height: 64vh;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  font-size: 13px;
  line-height: 1.7;
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", sans-serif;
  background: #f8fafc;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}
.preview-scroll {
  max-height: 64vh;
  overflow: auto;
  min-height: 100px;
}
.preview-scroll :deep(.docx-wrapper) {
  font-family: "Microsoft YaHei", "微软雅黑", "PingFang SC", sans-serif !important;
}
.excel-box { width: 100%; }
.sheet-block { margin-bottom: 14px; }
.sheet-name {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  padding: 6px 10px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-bottom: none;
  border-radius: 6px 6px 0 0;
}
.sheet-table { border: 1px solid #e2e8f0; border-radius: 0 0 6px 6px; overflow: auto; background: #fff; }
.sheet-table :deep(table) { border-collapse: collapse; font-size: 12px; width: 100%; }
.sheet-table :deep(td), .sheet-table :deep(th) {
  border: 1px solid #e2e8f0;
  padding: 4px 8px;
  white-space: nowrap;
}
.sheet-table :deep(th) { background: #f8fafc; font-weight: 600; }
.pptx-box { width: 100%; }
.ppt-slides { width: 100%; }
.ppt-slide {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 14px;
  background: #fff;
  overflow: hidden;
}
.ppt-slide-head {
  padding: 6px 12px;
  background: #f1f5f9;
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  border-bottom: 1px solid #e2e8f0;
}
.ppt-slide-body {
  padding: 12px 14px;
  min-height: 40px;
}
.ppt-slide-img {
  display: block;
  max-width: 100%;
  max-height: 420px;
  margin: 0 auto 10px;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}
.ppt-slide-text {
  margin: 0 0 6px;
  font-size: 14px;
  line-height: 1.8;
  color: #334155;
}
.preview-note { padding: 40px 0; text-align: center; }
.xmind-box {
  display: flex;
  flex-direction: column;
  height: 64vh;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
  background: #fafbff;
}
.xmind-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-bottom: 1px solid #e5e7eb;
  background: #fff;
  flex-shrink: 0;
}
.xmind-tab {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 999px;
  cursor: pointer;
  color: #64748b;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
}
.xmind-tab.active { color: #fff; background: #7c3aed; border-color: #7c3aed; }
.xmind-canvas {
  flex: 1;
  overflow: auto;
  min-height: 0;
  position: relative;
}
.me-canvas {
  flex: 1;
  min-height: 0;
  position: relative;
}
.me-canvas .mind-elixir { height: 100%; }
.xmind-svg { display: block; }
.xmind-edge {
  fill: none;
  stroke: #c4b5fd;
  stroke-width: 1.5;
}
.xmind-node rect {
  stroke-width: 1;
}
.xmind-text { font-size: 13px; font-family: "Microsoft YaHei", "微软雅黑", sans-serif; }
.preview-err {
  padding: 10px 12px;
  margin-bottom: 8px;
  color: #b91c1c;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 6px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
.preview-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.85);
  font-size: 14px;
  color: #475569;
}
</style>
