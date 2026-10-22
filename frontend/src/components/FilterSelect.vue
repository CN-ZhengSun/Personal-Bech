<template>
  <div class="fs" ref="root">
    <div class="fs-box" @mousedown.prevent="onMousedown" :title="hint">
      <span v-if="!inputMode" :class="['fs-text', { 'fs-ph': !displayText }]">{{ displayText || placeholder }}</span>
      <input v-else ref="inp" v-model="kw" class="fs-input" :placeholder="placeholder"
        @input="onInput" @blur="onBlur" @keydown.enter.prevent="applyKw" @keydown.esc.prevent="exitInput" />
      <span class="fs-caret" v-if="!inputMode">▾</span>
    </div>
    <div v-if="dropdown" class="fs-menu">
      <div class="fs-item fs-clear" @click="pick('')">
        <span>全部（清除筛选）</span>
      </div>
      <div v-for="op in options" :key="op" class="fs-item" :class="{ 'fs-active': op === modelValue }" @click="pick(op)">{{ op }}</div>
      <div v-if="!options.length" class="fs-empty">无可选项</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  options: { type: Array, default: () => [] },
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue', 'update:search'])

const root = ref(null)
const inp = ref(null)
const inputMode = ref(false)
const dropdown = ref(false)
const kw = ref('')
// 单击/双击识别：按下即开下拉（无延迟），300ms 内的第二次按下判定为双击切输入
let lastDown = 0

const displayText = computed(() => (props.modelValue ? props.modelValue : ''))
const hint = '单击下拉选择，双击输入搜索'

function onMousedown() {
  if (inputMode.value) return
  const now = Date.now()
  if (now - lastDown < 300) {
    // 双击：切换为输入搜索
    lastDown = 0
    closeDropdown()
    openInput()
  } else {
    // 单击：已打开则收起，否则展开（切换）
    lastDown = now
    if (dropdown.value) closeDropdown()
    else openDropdown()
  }
}
function openDropdown() {
  dropdown.value = true
}
function closeDropdown() {
  dropdown.value = false
}
async function openInput() {
  inputMode.value = true
  kw.value = ''
  await nextTick()
  inp.value?.focus()
  emit('update:search', '')
}
function onInput() {
  emit('update:search', kw.value)
}
function applyKw() {
  emit('update:search', kw.value)
  exitInput()
}
function onBlur() {
  // 失焦后退出输入模式，保留已输入的关键字筛选
  setTimeout(() => {
    inputMode.value = false
  }, 120)
}
function exitInput() {
  inputMode.value = false
  closeDropdown()
}
function pick(val) {
  closeDropdown()
  emit('update:modelValue', val)
}
function onClickOutside(e) {
  if (root.value && !root.value.contains(e.target)) {
    closeDropdown()
    if (inputMode.value) inputMode.value = false
  }
}
onMounted(() => document.addEventListener('click', onClickOutside))
onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside)
})
</script>

<style scoped>
.fs {
  position: relative;
  display: inline-block;
  min-width: 120px;
  font-family: inherit;
  font-size: 13px;
}
.fs-box {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  padding: 0 10px;
  height: 34px;
  border: 1px solid var(--border-color);
  border-radius: 7px;
  font-size: 13px;
  font-family: inherit;
  line-height: normal;
  background: var(--bg-card);
  cursor: pointer;
  user-select: none;
  box-sizing: border-box;
  transition: all 0.15s ease;
}
.fs-box:hover {
  border-color: var(--border-focus);
}
.fs-text {
  color: var(--text-main);
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.fs-ph {
  color: var(--text-muted);
}
.fs-caret {
  color: var(--text-muted);
  font-size: 11px;
}
.fs-input {
  border: none;
  outline: none;
  width: 100%;
  font-size: 13px;
  font-family: inherit;
  padding: 0;
  margin: 0;
  background: transparent;
  color: var(--text-main);
  box-sizing: border-box;
}
.fs-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 30;
  min-width: 100%;
  max-height: 220px;
  overflow-y: auto;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  box-shadow: var(--shadow-elevated);
  font-family: inherit;
  font-size: 13px;
}
.fs-item {
  padding: 7px 12px;
  font-size: 13px;
  font-family: inherit;
  color: var(--text-main);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.12s ease;
}
.fs-item:hover {
  background: var(--accent-light);
  color: var(--accent-primary);
}
.fs-item.fs-active {
  background: var(--accent-light);
  color: var(--accent-primary);
  font-weight: 600;
}
.fs-item.fs-clear {
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
}
.fs-item.fs-clear:hover {
  background: var(--bg-card-subtle);
  color: var(--text-main);
}
.fs-empty {
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text-muted);
}
</style>
