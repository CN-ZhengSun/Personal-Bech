<template>
  <div class="hopp-wrap">
    <div class="hopp-head">
      <h1 style="margin:0;font-size:20px">接口测试工具</h1>
      <a class="open-btn" :href="hoppUrl" target="_blank" rel="noopener">新窗口打开 ↗</a>
    </div>
    <iframe :src="hoppUrl" class="hopp-frame" frameborder="0" allow="clipboard-write"></iframe>
  </div>
</template>

<script setup>
const hoppUrl = 'http://localhost:3000'
</script>

<style scoped>
.hopp-wrap { display: flex; flex-direction: column; height: calc(100vh - 68px); }
.hopp-head { display: flex; align-items: center; gap: 12px; margin: 0 0 4px; flex: none; flex-wrap: wrap; }
.open-btn { margin-left: auto; font-size: 12px; color: #5b4ffc; text-decoration: none; border: 1px solid #e3e6ea; padding: 3px 10px; border-radius: 6px; }
.open-btn:hover { border-color: #5b4ffc; background: #f2f0ff; }
.hopp-frame { flex: 1; width: 100%; border: 1px solid #e6e8eb; border-radius: 10px; background: #fff; }
</style>
