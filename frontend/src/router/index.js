import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue'), meta: { public: true } },
  { path: '/', redirect: '/adbtools' },
  { path: '/report', name: 'report', component: () => import('../views/Report.vue') },
  { path: '/projects', name: 'projects', component: () => import('../views/Projects.vue') },
  { path: '/requirements', name: 'requirements', component: () => import('../views/Requirements.vue') },
  { path: '/cases', name: 'cases', component: () => import('../views/Cases.vue') },
  { path: '/executions', name: 'executions', component: () => import('../views/Executions.vue') },
  { path: '/bugs', name: 'bugs', component: () => import('../views/Bugs.vue') },
  { path: '/automation', name: 'automation', component: () => import('../views/Automation.vue') },
  { path: '/tracking', name: 'tracking', component: () => import('../views/Tracking.vue') },
  { path: '/adbtools', name: 'adbtools', component: () => import('../views/ADBTools.vue') },
  { path: '/jmeter', name: 'jmeter', component: () => import('../views/JMeter.vue') },
  { path: '/apitest', name: 'apitest', component: () => import('../views/Hoppscotch.vue') },
  { path: '/releases', name: 'releases', component: () => import('../views/Releases.vue') },
  { path: '/knowledge', name: 'knowledge', component: () => import('../views/Knowledge.vue') },
  { path: '/skills', name: 'skills', component: () => import('../views/Skills.vue') },
  { path: '/ai', name: 'ai', component: () => import('../views/AiModels.vue') },
  { path: '/menu-manage', name: 'menu-manage', component: () => import('../views/MenuManage.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to) => {
  const token = localStorage.getItem('twb_authenticated')
  if (!to.meta.public && !token) return '/login'
  if (to.path === '/login' && token) return '/'
  return true
})

export default router
