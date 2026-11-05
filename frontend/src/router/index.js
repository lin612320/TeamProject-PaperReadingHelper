import { createRouter, createWebHistory } from 'vue-router'

import UploadView from '../views/UploadView.vue'
import LibraryView from '../views/LibraryView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: UploadView,
    },
    {
      path: '/library',
      component: LibraryView,
    },
    {
      path: '/reader/:paperId',
      name: 'reader',
      component: () => import('../views/ReaderView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('../views/SettingsView.vue'),
    },
  ],
})

export default router