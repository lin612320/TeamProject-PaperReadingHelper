import { createRouter, createWebHistory } from 'vue-router'

import UploadView from '../views/UploadView.vue'
import LibraryView from '../views/LibraryView.vue'

const ReaderPlaceholder = {
  template: `
    <main style="max-width: 800px; margin: 48px auto; padding: 24px;">
      <h1>论文阅读器</h1>
      <p>阅读器页面正在开发中。</p>
      <router-link to="/library">返回文献列表</router-link>
    </main>
  `,
}

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
      component: ReaderPlaceholder,
    },
  ],
})

export default router