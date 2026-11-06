<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path v-for="(d,i) in (paths[name] || paths.dashboard)" :key="i" :d="d" /></svg>
</template>
<script setup>
defineProps({name:{type:String,required:true}})
const paths={
 dashboard:['M3 3h7v7H3z M14 3h7v5h-7z M3 14h7v7H3z M14 12h7v9h-7z'],
 '/adbtools':['M8 2.5h8a2 2 0 0 1 2 2v15a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2v-15a2 2 0 0 1 2-2Z','M10 5h4 M11 18.5h2 M9 10l-2 2 2 2 M15 10l2 2-2 2'],
 '/api-workspace':['m8 7-5 5 5 5 M16 7l5 5-5 5 M14 4l-4 16'],
 '/test-data':['m12 2 9 5-9 5-9-5 9-5Z M3 7v10l9 5 9-5V7 M12 12v10 M7.5 4.5l9 5'],
 '/requirements':['M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Z M14 3v6h6 M8 13h8 M8 17h5'],
 '/cases':['M9 4H5v17h14V4h-4 M9 2h6v4H9z M8 11l2 2 5-4 M8 17h7'],
 '/executions':['M4 5h7 M4 12h3 M4 19h7 M13 6l8 6-8 6V6Z'],
 '/bugs':['M8 10h8v6a4 4 0 0 1-8 0v-6Z M9 10V8a3 3 0 0 1 6 0v2 M9 5 7 3 M15 5l2-2 M4 11h4 M16 11h4 M3 16h5 M16 16h5 M5 21l4-3 M15 18l4 3 M12 11v8'],
 '/knowledge':['M12 5C9 3 5 3 2 4v15c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1v15 M5 8h4 M15 8h4 M5 12h4 M15 12h4'],
 '/ai':['M8 4h8v4h4v8h-4v4H8v-4H4V8h4V4Z M9 9h6v6H9z M9 1v3 M15 1v3 M9 20v3 M15 20v3 M1 9h3 M20 9h3 M1 15h3 M20 15h3'],
 '/projects':['M3 7V4h6l2 3h10v13H3V7Z M3 10h18'],
 '/report':['M4 3v18h17 M8 16v-4 M13 16V8 M18 16V5'],
 '/automation':['m13 2-9 12h7l-1 8 10-13h-8l1-7Z'],
 '/releases':['M3 3h8l10 10-8 8L3 11V3Z M7 7h.01'],
 '/apitest':['M8 3v5 M16 3v5 M6 8h12v4a6 6 0 0 1-12 0V8Z M12 18v4'],
 '/tracking':['M3 12h4l3-8 4 16 3-8h4'],
 '/notification-monitor':['M5 17h14l-2-3V9a5 5 0 0 0-10 0v5l-2 3Z M10 21h4 M12 2v2'],
 '/mysql-query':['M20 6c0 2-16 2-16 0s16-4 16 0v12c0 4-16 4-16 0V6 M4 12c0 3 16 3 16 0'],
 '/jmeter':['M12 8v5l3 2 M9 2h6 M12 2v3 M18 6l2-2 M20 14a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z'],
 '/skills':['M8 3h8v4h5v10h-5v4H8v-4H3V7h5V3Z M9 12l2 2 4-4'],
 '/menu-manage':['M8 5h13 M8 12h13 M8 19h13 M3 5h.01 M3 12h.01 M3 19h.01'],
 theme:['M20.5 13a8.5 8.5 0 1 1-9.5-9.5A7 7 0 0 0 20.5 13Z'],
 collapse:['M3 4h18v16H3z M9 4v16 M16 9l-3 3 3 3'],
 expand:['M3 4h18v16H3z M9 4v16 M13 9l3 3-3 3']
}
</script>
