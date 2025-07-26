import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'BankReconciliation',
    component: () => import('@/pages/BankReconciliation.vue'),
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('@/pages/Reports.vue'),
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/pages/History.vue'),
  },
]

let router = createRouter({
  history: createWebHistory('/advanced-bank-reconciliation'),
  routes,
})

export default router
