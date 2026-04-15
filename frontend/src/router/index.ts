import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'Welcome',
      component: () => import('../views/WelcomePage.vue'),
    },
    {
      path: '/chat/:threadId',
      name: 'Chat',
      component: () => import('../views/ChatPage.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
})

export default router
