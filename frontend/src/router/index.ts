import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import ChatView from '@/views/ChatView.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'chat',
    component: ChatView,
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router