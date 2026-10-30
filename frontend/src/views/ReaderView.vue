<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import * as pdfjsLib from 'pdfjs-dist'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

// PDF.js 的解析工作跑在 Worker 线程里，主线程只负责画，页面才不会卡死。
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

// 用于测试的文件，把任意 PDF 重命名sample.pdf然后放到 frontend/public/sample.pdf 后即可
const FALLBACK_SAMPLE = '/sample.pdf'

const route = useRoute()

// 页码 → canvas 元素。v-for 生成的 canvas 通过 :ref 回调登记进来，
// 渲染时按页码取，元素卸载时（回调收到 null）自动移除。
const canvasEls = new Map()

const loading = ref(true)
const errorMessage = ref('')
const usingSample = ref(false)
const pageCount = ref(0)
const renderedPages = ref(0)

// 整体缩放倍率。1 point = 1/72 英寸，scale 1.4 时 A4 约为 833 × 1179 px。
const scale = ref(1.4)

const pdfDoc = shallowRef(null)

// 所有进行中的 RenderTask。取消它们可以避免切换文献后旧任务继续往画布上画。
let renderTasks = []

function setCanvasEl(pageNumber, el) {
  if (el) canvasEls.set(pageNumber, el)
  else canvasEls.delete(pageNumber)
}

// 取 PDF 文档：优先走后端契约接口，开发环境失败时退回本地样例 
async function openDocument() {
  const paperId = route.params.paperId
  const url = `${API_BASE}/api/papers/${encodeURIComponent(paperId)}/file`

  try {
    return await pdfjsLib.getDocument({ url }).promise
  } catch (error) {
    if (!import.meta.env.DEV) throw error

    // 这里会吞掉真实的 404 / 跨域错误，仅为了在后端就绪前先把渲染跑通。以后后段完成时需删除这一个部分
    usingSample.value = true
    try {
      return await pdfjsLib.getDocument({ url: FALLBACK_SAMPLE }).promise
    } catch {
      throw new Error(
        '且本地样例缺失：请把任意 PDF 放到 frontend/public/sample.pdf 后刷新'
      )
    }
  }
}

// 把整个文档逐页画到各自的 canvas 上
async function renderAllPages() {
  if (!pdfDoc.value) return

  loading.value = true
  errorMessage.value = ''
  renderedPages.value = 0

  try {
    for (let pageNumber = 1; pageNumber <= pdfDoc.value.numPages; pageNumber++) {
      const canvas = canvasEls.get(pageNumber)
      if (!canvas) {
        console.warn(`第 ${pageNumber} 页的 canvas 还没挂载，已跳过`)
        continue
      }

      const page = await pdfDoc.value.getPage(pageNumber)
      const viewport = page.getViewport({ scale: scale.value })

      const context = canvas.getContext('2d')

      // 位图尺寸必须是整数，否则右侧/下侧会有 1px 缝隙
      canvas.width = Math.floor(viewport.width)
      canvas.height = Math.floor(viewport.height)
      // 不写死 CSS 宽高：靠 .pdf-canvas 的 max-width:100% + height:auto 按比例自适应，
      // 窄屏时等比缩小而不会被压扁

      // pdf.js v6 推荐传 canvas；canvasContext 保留是为了兼容旧版本
      const task = page.render({ canvas, canvasContext: context, viewport })
      renderTasks.push(task)
      await task.promise

      // 渲染完一页就更新进度，用户能看到「3 / 15 页」在走
      renderedPages.value = pageNumber
    }
  } catch (error) {
    if (error?.name !== 'RenderingCancelledException') {
      errorMessage.value = error?.message || 'PDF 渲染失败'
    }
  } finally {
    loading.value = false
  }
}

// 加载文档 + 渲染全部页面 
async function loadDocument() {
  loading.value = true
  errorMessage.value = ''
  usingSample.value = false
  pageCount.value = 0
  renderedPages.value = 0

  try {
    pdfDoc.value = await openDocument()
    pageCount.value = pdfDoc.value.numPages

    // 等待 v-for 把 canvas 都挂到 DOM 上，否则 canvasEls 还是空的，什么都画不出来
    await nextTick()

    await renderAllPages()
  } catch (error) {
    errorMessage.value = `无法打开这份 PDF：${error?.message || '未知错误'}`
    loading.value = false
  }
}

onMounted(loadDocument)

watch(
  () => route.params.paperId,
  () => {
    if (route.name === 'reader') loadDocument()
  }
)

onBeforeUnmount(() => {
  renderTasks.forEach((task) => task.cancel())
  renderTasks = []
  pdfDoc.value?.destroy()
  pdfDoc.value = null
  canvasEls.clear()
})
</script>

<template>
  <main class="reader-page">
    <header class="reader-bar">
      <RouterLink class="back-link" to="/library">← 返回文献列表</RouterLink>

      <span v-if="pageCount" class="page-info">共 {{ pageCount }} 页</span>
    </header>

    <p v-if="usingSample" class="sample-hint">
      后端 <code>/api/papers/{id}/file</code> 还没就绪，当前显示的是本地示例 PDF。
    </p>

    <section v-show="!errorMessage" class="canvas-wrap">
      <p v-if="loading" class="loading-tip" role="status">
        {{ pageCount ? `正在渲染 ${renderedPages} / ${pageCount} 页…` : '正在加载文档…' }}
      </p>

      <div class="page-list">
        <div v-for="n in pageCount" :key="n" class="page">
          <canvas
            :ref="(el) => setCanvasEl(n, el)"
            class="pdf-canvas"
            :class="{ 'is-rendered': n <= renderedPages }"
          ></canvas>
        </div>
      </div>
    </section>

    <section v-if="errorMessage" class="state-card error-card" role="alert">
      <h2>打不开这份文献</h2>
      <p>{{ errorMessage }}</p>
      <RouterLink class="back-link" to="/library">返回文献列表</RouterLink>
    </section>
  </main>
</template>

<style scoped>
.reader-page {
  min-height: 100vh;
  padding: 0 0 48px;
  background: #f1f5f9;
  color: #202938;
}

.reader-bar {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 24px;
  border-bottom: 1px solid #e2e8f0;
  background: rgb(255 255 255 / 96%);
  backdrop-filter: blur(6px);
}

.back-link {
  color: #2563eb;
  font-size: 14px;
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.page-info {
  color: #64748b;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.sample-hint {
  width: min(900px, calc(100% - 40px));
  margin: 16px auto 0;
  padding: 10px 14px;
  border: 1px solid #fde68a;
  border-radius: 8px;
  background: #fffbeb;
  color: #92400e;
  font-size: 13px;
}

.sample-hint code {
  font-size: 12px;
}

.canvas-wrap {
  position: relative;
  width: min(900px, calc(100% - 40px));
  margin: 20px auto 0;
}

.loading-tip {
  margin: 0 0 12px;
  color: #64748b;
  font-size: 14px;
  text-align: center;
}

.page-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.page {
  line-height: 0;
}

.pdf-canvas {
  display: block;
  max-width: 100%;
  height: auto;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  background: #fff;
  box-shadow: 0 6px 24px rgb(15 23 42 / 8%);
  opacity: 0;
  transition: opacity 0.15s ease-out;
}

.pdf-canvas.is-rendered {
  opacity: 1;
}

.state-card {
  width: min(900px, calc(100% - 40px));
  margin: 20px auto 0;
  padding: 36px 24px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: #fff;
  text-align: center;
}

.state-card h2 {
  margin: 0 0 8px;
  font-size: 18px;
}

.state-card p {
  margin: 0 0 16px;
  color: #64748b;
  overflow-wrap: anywhere;
}

.error-card {
  border-color: #fecaca;
}
</style>
