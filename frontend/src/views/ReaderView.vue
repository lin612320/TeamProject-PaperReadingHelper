<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount, shallowRef, watch } from 'vue'
import { useRoute } from 'vue-router'
import { getPaper, askQuestion, explainText } from '../api/papers'
import { useSettings } from '../composables/useSettings'
import * as pdfjsLib from 'pdfjs-dist'
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl

const route = useRoute()
const { settings, isConfigured } = useSettings()
const paperId = Number(route.params.paperId)


const PDF_API_BASE = import.meta.env.VITE_API_BASE || ''
const FALLBACK_SAMPLE = '/sample.pdf'

function formatPdfError(error) {
  const msg = error?.message || ''

  if (/[\u4e00-\u9fa5]/.test(msg)) return msg
  if (
    msg.includes('fake worker') ||
    msg.includes('Failed to load module script') ||
    msg.includes('MIME type') ||
    msg.includes('workerSrc') ||
    msg.includes('Cannot use the specified')
  ) {
    return 'PDF 渲染组件加载失败，请刷新页面重试；若持续出现，请联系管理员检查静态资源配置'
  }
  if (msg.includes('Failed to fetch') || msg.includes('NetworkError') || msg.includes('server response')) {
    return '无法连接到服务器，请检查网络或后端服务是否启动'
  }
  if (msg.includes('Invalid PDF') || msg.includes('Invalid structure') || msg.includes('corrupt')) {
    return '这份 PDF 文件已损坏或格式不支持，无法打开'
  }
  if (msg.includes('password') || msg.includes('Password')) {
    return '这份 PDF 已加密，请提供密码后再试'
  }
  if (msg.includes('RenderingCancelled')) {
    return ''
  }
  return 'PDF 加载失败，请稍后重试'
}

const canvasEls = new Map()
const textLayerEls = new Map()
const textLayerTasks = new Map()
const pdfLoading = ref(true)
const pdfErrorMessage = ref('')
const usingSample = ref(false)
const pageCount = ref(0)
const renderedPages = ref(0)
const scale = ref(1.4)
const pdfDoc = shallowRef(null)
let renderTasks = []

// ===== #6 翻页 / 缩放 =====
const ZOOM_MIN = 0.6
const ZOOM_MAX = 2.4
const ZOOM_STEP = 0.2
const BASE_SCALE = 1.4 // 自适应宽度时的基准倍率

const scrollContainer = ref(null)
const pageEls = new Map()
const currentPage = ref(1)
const pageInput = ref(1)
const editingPage = ref(false)
const zooming = ref(false)

let scrollRafId = 0

const zoomPercent = computed(() => Math.round(scale.value * 100))
const zoomedIn = computed(() => scale.value > BASE_SCALE + 1e-6)
const canPrev = computed(() => !pdfLoading.value && currentPage.value > 1)
const canNext = computed(() => !pdfLoading.value && currentPage.value < pageCount.value)
const canZoomIn = computed(
  () => !pdfLoading.value && !zooming.value && scale.value < ZOOM_MAX - 1e-6
)
const canZoomOut = computed(
  () => !pdfLoading.value && !zooming.value && scale.value > ZOOM_MIN + 1e-6
)

function setCanvasEl(pageNumber, el) {
  if (el) canvasEls.set(pageNumber, el)
  else canvasEls.delete(pageNumber)
}

function setTextLayerEl(pageNumber, el) {
  if (el) textLayerEls.set(pageNumber, el)
  else textLayerEls.delete(pageNumber)
}

function setPageEl(pageNumber, el) {
  if (el) pageEls.set(pageNumber, el)
  else pageEls.delete(pageNumber)
}

async function openDocument() {
  const url = `${PDF_API_BASE}/api/papers/${encodeURIComponent(paperId)}/file`

  try {
    return await pdfjsLib.getDocument({ url }).promise
  } catch (error) {
    if (!import.meta.env.DEV) throw error

    usingSample.value = true
    try {
      return await pdfjsLib.getDocument({ url: FALLBACK_SAMPLE }).promise
    } catch {
      throw new Error('且本地样本缺失：请把任意 PDF 放到 frontend/public/sample.pdf 后刷新')
    }
  }
}

async function renderAllPages({ resetProgress = true } = {}) {
  if (!pdfDoc.value) return

  pdfLoading.value = true
  pdfErrorMessage.value = ''
  // 缩放重绘时不重置，避免整片画布闪白
  if (resetProgress) renderedPages.value = 0

  // 重渲染前清除旧 text layer 任务和内容
  textLayerTasks.forEach((t) => {
    try {
      t.cancel?.()
    } catch {
      // 忽略
    }
  })
  textLayerTasks.clear()
  textLayerEls.forEach((el) => {
    if (el) el.textContent = ''
  })

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
      canvas.width = Math.floor(viewport.width)
      canvas.height = Math.floor(viewport.height)

      const task = page.render({ canvas, canvasContext: context, viewport })
      renderTasks.push(task)
      await task.promise
      renderedPages.value = pageNumber

      // 渲染 text layer，让文字可选中
      const textLayerEl = textLayerEls.get(pageNumber)
      if (textLayerEl) {
        const textContent = await page.getTextContent()
        const textLayer = new pdfjsLib.TextLayer({
          textContentSource: textContent,
          container: textLayerEl,
          viewport,
        })
        textLayerTasks.set(pageNumber, textLayer)
        await textLayer.render()

        // canvas 可能被 max-width:100% 缩放，让 text layer 跟随显示尺寸
        // 通过设置 --total-scale-factor 让 pdfjs 自己计算容器尺寸和字体大小
        const { pageWidth } = viewport.rawDims
        requestAnimationFrame(() => {
          // 用 clientWidth（不含 border），避免边框导致的偏移
          const displayScale = canvas.clientWidth / pageWidth
          textLayerEl.style.setProperty('--total-scale-factor', displayScale)
        })
      }
    }
  } catch (error) {
    const friendly = formatPdfError(error)
    if (friendly) pdfErrorMessage.value = friendly
  } finally {
    pdfLoading.value = false
  }
}

async function loadDocument() {
  pdfLoading.value = true
  pdfErrorMessage.value = ''
  usingSample.value = false
  pageCount.value = 0
  renderedPages.value = 0
  currentPage.value = 1
  pageInput.value = 1
  clearCitationHighlight()

  try {
    pdfDoc.value = await openDocument()
    pageCount.value = pdfDoc.value.numPages
    await nextTick()
    await renderAllPages()
    updateCurrentPage()
  } catch (error) {
    const friendly = formatPdfError(error)
    pdfErrorMessage.value = friendly || '无法打开这份 PDF，请稍后重试'
    pdfLoading.value = false
  }
}

// ===== #6 翻页 / 缩放 =====

// 元素相对滚动容器顶部的位置（不依赖 offsetParent，兼容横向滚动） 
function pageOffsetTop(el, container) {
  return el.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop
}

// 取视口上部 30% 处所在页作为当前页 
function updateCurrentPage() {
  const container = scrollContainer.value
  const total = pageCount.value
  if (!container || !total) return

  const anchorY = container.scrollTop + Math.min(container.clientHeight * 0.3, 240)
  let page = 1

  for (let n = 1; n <= total; n++) {
    const el = pageEls.get(n)
    if (!el) continue
    if (pageOffsetTop(el, container) <= anchorY) page = n
    else break
  }

  currentPage.value = page
}

function handleScroll() {
  if (scrollRafId) return
  scrollRafId = requestAnimationFrame(() => {
    scrollRafId = 0
    updateCurrentPage()
  })
}

// 滚动到指定页，页码会被夹到 1..pageCount
function goToPage(target, smooth = true) {
  const container = scrollContainer.value
  const total = pageCount.value
  if (!container || !total) return

  const page = Math.min(total, Math.max(1, Math.floor(Number(target)) || 1))
  const el = pageEls.get(page)
  if (!el) return

  currentPage.value = page
  pageInput.value = page
  container.scrollTo({
    top: Math.max(0, pageOffsetTop(el, container) - 4),
    behavior: smooth ? 'smooth' : 'auto',
  })
}

// 页码输入框：回车、失焦时跳转，非法值回退 
function commitPageInput() {
  editingPage.value = false
  const target = Number(pageInput.value)
  if (!Number.isFinite(target)) {
    pageInput.value = currentPage.value
    return
  }
  goToPage(target)
}

// ===== #8 引用页码跳页 =====

const flashPageNumber = ref(0)
let flashTimer = 0

// ===== #41 引用 bbox 高亮层 =====
const citationHighlight = ref(null)
let citationHighlightTimer = 0
let citationHighlightSeq = 0

/** 页码是否有效（1..pageCount），防止后端脏数据导致跳转异常 */
function isValidPage(page) {
  const n = Number(page)
  return Number.isFinite(n) && n >= 1 && n <= pageCount.value
}

/**
 * 把 citation 的归一化 bbox 转成相对页面的 CSS 百分比。
 * 无效 / 四字段为 null / 面积过小 → 返回 null，调用方退回“只跳页不画框”。
 */
function citationBoxStyle(cite) {
  if (!cite) return null

  const raw = [cite.bboxX0, cite.bboxY0, cite.bboxX1, cite.bboxY1]
  if (raw.some((v) => v === null || v === undefined || v === '')) return null

  const values = raw.map(Number)
  if (!values.every(Number.isFinite)) return null

  const left = Math.max(0, Math.min(1, Math.min(values[0], values[2])))
  const top = Math.max(0, Math.min(1, Math.min(values[1], values[3])))
  const right = Math.max(0, Math.min(1, Math.max(values[0], values[2])))
  const bottom = Math.max(0, Math.min(1, Math.max(values[1], values[3])))

  if (right - left < 0.002 || bottom - top < 0.002) return null

  return {
    left: `${left * 100}%`,
    top: `${top * 100}%`,
    width: `${(right - left) * 100}%`,
    height: `${(bottom - top) * 100}%`,
  }
}

function clearCitationHighlight() {
  clearTimeout(citationHighlightTimer)
  citationHighlightTimer = 0
  citationHighlight.value = null
}

/** bboxMode=null 时的降级：只闪一下目标页，不画框 */
function flashPage(page) {
  flashPageNumber.value = page
  clearTimeout(flashTimer)
  flashTimer = setTimeout(() => {
    flashPageNumber.value = 0
  }, 1200)
}

/** 点击引用：跳页 + 画半透明 bbox 框；无坐标时只跳页 */
function jumpToCitation(cite) {
  if (!cite || !isValidPage(cite.page)) return

  const target = Math.floor(Number(cite.page))
  goToPage(target)
  clearCitationHighlight()

   const style = citationBoxStyle(cite)
  if (!style) {
    flashPage(target)
    return
  }

  citationHighlight.value = {
    page: target,
    style,
    // precise = 单栏细框；block = 双栏/复杂版面的整段框，用虚线区分
    mode: cite.bboxMode === 'block' ? 'block' : 'precise',
    key: ++citationHighlightSeq,
  }

  // 2.8 秒后移除；快速连点会先清掉上一个 timer
  citationHighlightTimer = setTimeout(() => {
    citationHighlight.value = null
  }, 2800)
}

// 缩放前记录「当前页 + 页内偏移比例」，重绘后滚回同一位置 
function captureAnchor(container) {
  if (!container) return null
  const el = pageEls.get(currentPage.value)
  if (!el) return null

  const top = pageOffsetTop(el, container)
  const height = el.offsetHeight || 1
  return {
    page: currentPage.value,
    ratio: Math.min(1, Math.max(0, (container.scrollTop - top) / height)),
  }
}

function restoreAnchor(container, anchor) {
  if (!container || !anchor) return
  const el = pageEls.get(anchor.page)
  if (!el) return
  container.scrollTop = Math.max(0, pageOffsetTop(el, container) + anchor.ratio * (el.offsetHeight || 1))
}

async function changeZoom(delta) {
  if (pdfLoading.value || zooming.value || !pdfDoc.value) return

  const next = Math.min(
    ZOOM_MAX,
    Math.max(ZOOM_MIN, Math.round((scale.value + delta) * 100) / 100)
  )
  if (next === scale.value) return

  const container = scrollContainer.value
  const anchor = captureAnchor(container)

  zooming.value = true
  scale.value = next
  try {
    await renderAllPages({ resetProgress: false })
    await nextTick()
    restoreAnchor(container, anchor)
    updateCurrentPage()
  } finally {
    zooming.value = false
  }
}

watch(currentPage, (page) => {
  if (!editingPage.value) pageInput.value = page
})

// P3: Q&A 侧栏
const paper = ref(null)
const pageLoading = ref(true)
const pageError = ref('')

const question = ref('')
const sending = ref(false)
const questionInput = ref(null)

const chatItems = ref([])

let nextId = 1

const canSend = computed(() => question.value.trim().length > 0 && !sending.value)

function scrollToBottom() {
  nextTick(() => {
    const el = document.querySelector('.qa-messages')
    if (el) el.scrollTop = el.scrollHeight
  })
}

async function loadPaper() {
  pageLoading.value = true
  pageError.value = ''
  try {
    paper.value = await getPaper(paperId)
  } catch (error) {
    // 后端未就绪时不阻塞页面，仅记录错误并继续
    pageError.value = error.message || '文献加载失败'
    paper.value = null
  } finally {
    pageLoading.value = false
  }
}

async function handleSend() {
  const q = question.value.trim()
  if (!q || sending.value) return

  const qId = nextId++
  const aId = nextId++

  chatItems.value.push({ id: qId, type: 'question', text: q })
  chatItems.value.push({
    id: aId,
    type: 'answer',
    text: '',
    citations: [],
    status: 'loading',
    errorMessage: '',
    questionText: q,
  })

  question.value = ''
  sending.value = true
  scrollToBottom()

  try {
    const aiConfig = isConfigured() ? settings.value : null
    const data = await askQuestion(paperId, q, aiConfig)
    const idx = chatItems.value.findIndex((item) => item.id === aId)
    if (idx !== -1) {
      chatItems.value[idx] = {
        ...chatItems.value[idx],
        text: data.answer,
        citations: data.citations || [],
        status: 'done',
      }
    }
  } catch (error) {
    const idx = chatItems.value.findIndex((item) => item.id === aId)
    if (idx !== -1) {
      chatItems.value[idx] = {
        ...chatItems.value[idx],
        status: 'error',
        errorMessage: error.message || '问答请求失败',
      }
    }
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

async function handleRetry(questionText) {
  if (sending.value) return

  const aId = nextId++

  chatItems.value.push({
    id: aId,
    type: 'answer',
    text: '',
    citations: [],
    status: 'loading',
    errorMessage: '',
    questionText,
  })

  sending.value = true
  scrollToBottom()

  try {
    const aiConfig = isConfigured() ? settings.value : null
    const data = await askQuestion(paperId, questionText, aiConfig)
    const idx = chatItems.value.findIndex((item) => item.id === aId)
    if (idx !== -1) {
      chatItems.value[idx] = {
        ...chatItems.value[idx],
        text: data.answer,
        citations: data.citations || [],
        status: 'done',
      }
    }
  } catch (error) {
    const idx = chatItems.value.findIndex((item) => item.id === aId)
    if (idx !== -1) {
      chatItems.value[idx] = {
        ...chatItems.value[idx],
        status: 'error',
        errorMessage: error.message || '问答请求失败',
      }
    }
  } finally {
    sending.value = false
    scrollToBottom()
  }
}

// ===== #42 划词翻译 / 术语解释 =====
const MAX_TEXT = 1000
const MAX_CONTEXT = 600

const selectedText = ref('')
const selectionRange = ref(null)
const explainBubbleVisible = ref(false)
const explainBubbleStyle = ref({ top: '0px', left: '0px' })
const explainPanelVisible = ref(false)
const explainPanelStyle = ref({ top: '0px', left: '0px' })
const explainLoading = ref(false)
const explainMode = ref('translate')
const explainResult = ref(null)
const explainError = ref('')
const explainTruncated = ref(false)
const explainCopied = ref(false)

function getSelectionContext() {
  const sel = window.getSelection()
  if (!sel || sel.rangeCount === 0 || !selectedText.value) return null

  const range = sel.getRangeAt(0)
  const container = range.commonAncestorContainer
  const textLayerEl = container.nodeType === 1 ? container.closest('.text-layer') : container.parentElement?.closest('.text-layer')
  if (!textLayerEl) return null

  const fullText = textLayerEl.textContent || ''
  const selText = selectedText.value
  const idx = fullText.indexOf(selText)
  if (idx === -1) return null

  const half = Math.floor(MAX_CONTEXT / 2)
  const start = Math.max(0, idx - half)
  const end = Math.min(fullText.length, idx + selText.length + half)
  return fullText.slice(start, end)
}

function handleSelection() {
  if (explainLoading.value) return

  const sel = window.getSelection()
  const text = sel?.toString().trim() || ''

  if (!text) {
    explainBubbleVisible.value = false
    return
  }

  // 只在 PDF 区域内的选区显示气泡
  const anchorNode = sel.anchorNode
  if (!anchorNode) return
  const el = anchorNode.nodeType === 1 ? anchorNode : anchorNode.parentElement
  if (!el?.closest('.text-layer')) return

  selectedText.value = text.slice(0, MAX_TEXT)
  selectionRange.value = sel.getRangeAt(0).cloneRange()

  // 计算气泡位置（选区上方居中）
  const rect = sel.getRangeAt(0).getBoundingClientRect()
  const scrollRect = scrollContainer.value?.getBoundingClientRect()
  if (!scrollRect) return

  explainBubbleStyle.value = {
    top: `${rect.top - scrollRect.top + scrollContainer.value.scrollTop - 40}px`,
    left: `${rect.left - scrollRect.left + scrollContainer.value.scrollLeft + rect.width / 2 - 90}px`,
  }
  explainBubbleVisible.value = true
}

async function runExplain(mode) {
  explainMode.value = mode
  explainLoading.value = true
  explainError.value = ''
  explainResult.value = null
  explainTruncated.value = false
  explainBubbleVisible.value = false

  // 浮层位置：选区下方
  if (selectionRange.value) {
    const rect = selectionRange.value.getBoundingClientRect()
    const scrollRect = scrollContainer.value?.getBoundingClientRect()
    if (scrollRect) {
      explainPanelStyle.value = {
        top: `${rect.bottom - scrollRect.top + scrollContainer.value.scrollTop + 8}px`,
        left: `${Math.max(8, rect.left - scrollRect.left + scrollContainer.value.scrollLeft)}px`,
      }
    }
  }
  explainPanelVisible.value = true

  try {
    const aiConfig = isConfigured() ? settings.value : null
    const context = getSelectionContext()
    const data = await explainText(selectedText.value, mode, {
      paperId: paperId || null,
      context,
      aiConfig,
    })
    explainResult.value = data
    explainTruncated.value = data?.truncated === true
  } catch (error) {
    explainError.value = error.message || '解释请求失败'
  } finally {
    explainLoading.value = false
  }
}

function retryExplain() {
  runExplain(explainMode.value)
}

function copyExplainResult() {
  if (!explainResult.value) return
  const content = explainMode.value === 'translate'
    ? explainResult.value.translation
    : explainResult.value.explanation
  if (!content) return
  navigator.clipboard?.writeText(content).then(() => {
    explainCopied.value = true
    setTimeout(() => {
      explainCopied.value = false
    }, 1500)
  })
}

function closeExplainPanel() {
  explainPanelVisible.value = false
  explainResult.value = null
  explainError.value = ''
  explainLoading.value = false
  explainTruncated.value = false
  explainCopied.value = false
  window.getSelection()?.removeAllRanges()
  selectedText.value = ''
}

function handleDocumentMouseUp(e) {
  // 点击浮层/气泡内不处理
  if (e.target.closest('.explain-bubble') || e.target.closest('.explain-panel')) return
  nextTick(() => handleSelection())
}

onMounted(async () => {
  await loadPaper()
  await loadDocument()
  document.addEventListener('mouseup', handleDocumentMouseUp)
  if (route.query.focus === 'qa') {
    nextTick(() => {
      questionInput.value?.focus()
    })
  }
})

watch(
  () => route.params.paperId,
  () => {
    if (route.name === 'reader') {
      loadPaper()
      loadDocument()
    }
  }
)

onBeforeUnmount(() => {
  document.removeEventListener('mouseup', handleDocumentMouseUp)
  if (scrollRafId) {
    cancelAnimationFrame(scrollRafId)
    scrollRafId = 0
  }
  clearTimeout(flashTimer)
  clearCitationHighlight()
  renderTasks.forEach((task) => {
    try {
      task.cancel()
    } catch {
      // 渲染任务可能已自行结束，忽略取消异常
    }
  })
  renderTasks = []
  textLayerTasks.forEach((t) => {
    try {
      t.cancel?.()
    } catch {
      // 忽略
    }
  })
  textLayerTasks.clear()
  if (typeof pdfDoc.value?.destroy === 'function') {
    pdfDoc.value.destroy()
  }
  pdfDoc.value = null
  canvasEls.clear()
  textLayerEls.clear()
})
</script>

<template>
  <div class="reader-layout">
    <!--左侧：PDF 阅读区（P2 PDF.js 连续渲染）-->
    <section class="pdf-panel">
      <header class="reader-bar">
        <RouterLink class="back-link" to="/library">← 返回文献列表</RouterLink>

        <!-- #6 翻页 / 跳页 -->
        <div v-if="pageCount" class="pdf-toolbar">
          <button
            class="tool-btn"
            title="上一页"
            :disabled="!canPrev"
            @click="goToPage(currentPage - 1)"
          >
            ‹
          </button>

          <input
            v-model.number="pageInput"
            class="page-input"
            type="number"
            min="1"
            :max="pageCount"
            aria-label="跳转页码"
            @focus="editingPage = true"
            @blur="commitPageInput"
            @keyup.enter="commitPageInput"
          />
          <span class="page-total">/ {{ pageCount }}</span>

          <button
            class="tool-btn"
            title="下一页"
            :disabled="!canNext"
            @click="goToPage(currentPage + 1)"
          >
            ›
          </button>
        </div>

        <!-- #6 缩放 -->
        <div v-if="pageCount" class="zoom-toolbar">
          <button
            class="tool-btn"
            title="缩小"
            :disabled="!canZoomOut"
            @click="changeZoom(-ZOOM_STEP)"
          >
            −
          </button>
          <span class="zoom-value">{{ zoomPercent }}%</span>
          <button
            class="tool-btn"
            title="放大"
            :disabled="!canZoomIn"
            @click="changeZoom(ZOOM_STEP)"
          >
            +
          </button>
        </div>
      </header>

      <p v-if="usingSample" class="sample-hint">
        后端接口暂不可用，当前显示的是本地示例 PDF。
      </p>

      <!-- 文献元数据失败不阻塞 PDF -->
      <p v-if="pageError && !pageLoading" class="meta-hint">
        文献元数据加载失败：{{ pageError }}
      </p>

      <!-- PDF 渲染错误 -->
      <div v-if="pdfErrorMessage" class="state-card error-card" role="alert">
        <h2>打不开这份文献</h2>
        <p>{{ pdfErrorMessage }}</p>
        <button class="btn-retry" @click="loadDocument">重试</button>
      </div>

      <!-- 页面加载中占位 -->
      <div v-else-if="pageLoading" class="state-card">
        <p>正在加载文献信息…</p>
      </div>

      <!-- PDF 渲染中 / 完成 -->
      <div v-else ref="scrollContainer" class="canvas-wrap" @scroll="handleScroll">
        <p v-if="pdfLoading" class="loading-tip" role="status">
          {{
            zooming
              ? '正在调整缩放…'
              : pageCount
                ? `正在渲染 ${renderedPages} / ${pageCount} 页…`
                : '正在加载文档…'
          }}
        </p>

        <div class="page-list" :class="{ 'zoom-overflow': zoomedIn }">
          <div
            v-for="n in pageCount"
            :key="n"
            :ref="(el) => setPageEl(n, el)"
            class="page"
            :class="{ 'page-flash': n === flashPageNumber }"
          >
            <canvas
              :ref="(el) => setCanvasEl(n, el)"
              class="pdf-canvas"
              :class="{ 'is-rendered': n <= renderedPages }"
            ></canvas>
            <div :ref="(el) => setTextLayerEl(n, el)" class="text-layer"></div>
            <!-- #41 引用 bbox 高亮层：百分比定位，随缩放/旋转页自动对齐 -->
            <div
              v-if="citationHighlight && citationHighlight.page === n"
              :key="citationHighlight.key"
              class="citation-highlight-layer"
              aria-hidden="true"
            >
              <div
                class="citation-highlight"
                :class="{ 'is-block': citationHighlight.mode === 'block' }"
                :style="citationHighlight.style"
              ></div>
            </div>
          </div>
        </div>

        <!-- 划词操作气泡 -->
        <div
          v-if="explainBubbleVisible"
          class="explain-bubble"
          :style="explainBubbleStyle"
        >
          <button class="explain-bubble-btn" @click.stop="runExplain('translate')">翻译</button>
          <span class="explain-bubble-sep"></span>
          <button class="explain-bubble-btn" @click.stop="runExplain('term')">解释</button>
        </div>

        <!-- 解释结果浮层 -->
        <div
          v-if="explainPanelVisible"
          class="explain-panel"
          :style="explainPanelStyle"
          @click.stop
        >
          <div class="explain-panel-header">
            <span class="explain-mode-tag">
              {{ explainMode === 'translate' ? '翻译' : '术语解释' }}
            </span>
            <button class="explain-close-btn" @click.stop="closeExplainPanel" aria-label="关闭">×</button>
          </div>

          <p v-if="explainTruncated" class="explain-truncated-hint">
            选中文本超过 1000 字，已截断处理
          </p>

          <div v-if="explainLoading" class="explain-loading">
            <span class="spinner"></span>
            <span>正在{{ explainMode === 'translate' ? '翻译' : '解释' }}…</span>
          </div>

          <div v-else-if="explainError" class="explain-error">
            <p class="explain-error-text">{{ explainError }}</p>
            <button class="btn-retry" @click.stop="retryExplain">重试</button>
          </div>

          <div v-else-if="explainResult" class="explain-result">
            <p v-if="explainMode === 'translate'" class="explain-content">
              {{ explainResult.translation }}
            </p>
            <p v-else class="explain-content">
              {{ explainResult.explanation }}
            </p>
            <div class="explain-actions">
              <button class="explain-copy-btn" @click.stop="copyExplainResult">
                {{ explainCopied ? '已复制' : '复制' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!--右侧：Q&A 侧栏-->
    <section class="qa-sidebar">
      <header class="qa-header">
        <h2>问答</h2>
        <p v-if="paper" class="paper-badge">{{ paper.title }}</p>
      </header>

      <!-- 聊天消息列表 -->
      <div class="qa-messages" v-if="chatItems.length > 0">
        <div
          v-for="item in chatItems"
          :key="item.id"
          :class="['qa-message', `msg-${item.type}`, item.status === 'error' ? 'msg-error' : '']"
        >
          <template v-if="item.type === 'question'">
            <div class="msg-bubble question-bubble">
              <p>{{ item.text }}</p>
            </div>
          </template>

          <template v-else-if="item.status === 'loading'">
            <div class="msg-bubble answer-bubble loading-bubble">
              <span class="spinner"></span>
              <span>正在思考中，请耐心等待…</span>
            </div>
          </template>

          <template v-else-if="item.status === 'error'">
            <div class="msg-bubble answer-bubble error-bubble">
              <p class="error-text">请求失败</p>
              <p class="error-detail">{{ item.errorMessage }}</p>
              <button
                class="btn-retry"
                :disabled="sending"
                @click="handleRetry(item.questionText)"
              >
                重试
              </button>
            </div>
          </template>

          <template v-else>
            <div class="msg-bubble answer-bubble">
              <p class="answer-text">{{ item.text }}</p>

              <div v-if="item.citations && item.citations.length > 0" class="citations">
                <p class="citations-title">引用来源：</p>
                <div
                  v-for="(cite, ci) in item.citations"
                  :key="ci"
                  class="citation-item"
                >
                  <button
                    type="button"
                    class="citation-page"
                    :disabled="!pageCount || pdfLoading || !isValidPage(cite.page)"
                    :title="`跳转到第 ${cite.page} 页`"
                    @click="jumpToCitation(cite)"
                  >
                    第 {{ cite.page }} 页
                  </button>
                  <p class="citation-snippet">{{ cite.snippet }}</p>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <div v-else class="qa-empty">
        <p>在下方输入问题，开始向 AI 提问这篇论文。</p>
      </div>

      <div v-if="!isConfigured()" class="qa-config-notice">
        <span>尚未配置 API Key，</span>
        <RouterLink to="/settings">前往设置</RouterLink>
      </div>

      <div class="qa-input-area">
        <textarea
          ref="questionInput"
          v-model="question"
          class="qa-textarea"
          rows="2"
          placeholder="输入你的问题…"
          :disabled="sending"
          @keydown.enter.exact.prevent="handleSend"
        ></textarea>
        <button
          class="qa-send-btn"
          :disabled="!canSend"
          @click="handleSend"
        >
          {{ sending ? '发送中…' : '发送' }}
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
/*整体布局*/
.reader-layout {
  display: flex;
  height: calc(100vh - 60px);
  overflow: hidden;
  background: #f1f5f9;
}

/* 左侧 PDF 面板*/
.pdf-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.reader-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: rgb(255 255 255 / 96%);
  backdrop-filter: blur(6px);
  flex-shrink: 0;
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
  margin: 0;
  padding: 8px 20px;
  border-bottom: 1px solid #fde68a;
  background: #fffbeb;
  color: #92400e;
  font-size: 13px;
  flex-shrink: 0;
}

.sample-hint code {
  font-size: 12px;
}

.meta-hint {
  margin: 0;
  padding: 8px 20px;
  border-bottom: 1px solid #fed7aa;
  background: #fff7ed;
  color: #9a3412;
  font-size: 13px;
  flex-shrink: 0;
}

.canvas-wrap {
  position: relative;
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
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
  gap: 16px;
  padding: 0 12px;
}

.page {
  position: relative;
  line-height: 0;
}

.pdf-canvas {
  display: block;
  max-width: 100%;
  height: auto;
  border: 1px solid #e2e8f0;
  border-radius: 4px;
  background: #fff;
  box-shadow: 0 4px 16px rgb(15 23 42 / 6%);
  opacity: 0;
  transition: opacity 0.15s ease-out;
}

.pdf-canvas.is-rendered {
  opacity: 1;
}

/* text layer：覆盖在 canvas 上，文字透明可选 */
.text-layer {
  position: absolute;
  top: 1px;
  left: 1px;
  overflow: hidden;
  line-height: 1;
  pointer-events: auto;
  --total-scale-factor: 1;
  --scale-round-x: 1px;
  --scale-round-y: 1px;
}

.text-layer :deep(span) {
  color: transparent !important;
  -webkit-text-fill-color: transparent !important;
  position: absolute;
  white-space: pre;
  cursor: text;
  transform-origin: 0% 0%;
  font-size: calc(var(--font-height, 0) * var(--total-scale-factor));
  transform: scaleX(var(--scale-x, 1)) rotate(var(--rotate, 0deg));
}

.text-layer :deep(.markedContent) {
  position: absolute;
  inset: 0;
}

.text-layer :deep(::selection) {
  background: rgb(59 130 246 / 30%);
}

/* ===== #41 引用 bbox 高亮层 ===== */
.citation-highlight-layer {
  position: absolute;
  top: 1px;
  left: 1px;
  width: calc(100% - 2px);
  height: calc(100% - 2px);
  z-index: 15;
  pointer-events: none;
}

.citation-highlight {
  position: absolute;
  box-sizing: border-box;
  border: 2px solid #f59e0b;
  border-radius: 3px;
  background: rgb(245 158 11 / 18%);
  box-shadow: 0 0 0 2px rgb(245 158 11 / 12%);
  animation: citation-highlight-fade 2.6s ease-out forwards;
}

/* 双栏/复杂版面：bboxMode=block，用虚线提示“整段范围”，不冒充逐句精确 */
.citation-highlight.is-block {
  border-color: #2563eb;
  border-style: dashed;
  background: rgb(37 99 235 / 14%);
  box-shadow: 0 0 0 2px rgb(37 99 235 / 10%);
}

@keyframes citation-highlight-fade {
  0% { opacity: 0; }
  8% { opacity: 1; }
  75% { opacity: 1; }
  100% { opacity: 0; }
}

/* bboxMode=null：契约要求“只跳页不画框”，这里只闪一下目标页 */
.page-flash::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 14;
  border: 2px solid rgb(37 99 235 / 55%);
  border-radius: 4px;
  pointer-events: none;
  animation: page-flash-fade 1.1s ease-out forwards;
}

@keyframes page-flash-fade {
  0% { opacity: 0; }
  15% { opacity: 1; }
  100% { opacity: 0; }
}

/* ===== #42 划词翻译气泡 ===== */
.explain-bubble {
  position: absolute;
  z-index: 50;
  display: flex;
  align-items: center;
  background: #1e293b;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgb(0 0 0 / 20%);
  padding: 2px;
}

.explain-bubble-btn {
  padding: 6px 14px;
  border: none;
  background: transparent;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  border-radius: 6px;
  transition: background 0.15s;
}

.explain-bubble-btn:hover {
  background: #334155;
}

.explain-bubble-sep {
  width: 1px;
  height: 16px;
  background: #475569;
}

/* ===== #42 解释结果浮层 ===== */
.explain-panel {
  position: absolute;
  z-index: 50;
  width: 340px;
  max-width: calc(100% - 16px);
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  box-shadow: 0 8px 32px rgb(15 23 42 / 12%);
  overflow: hidden;
}

.explain-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid #f1f5f9;
}

.explain-mode-tag {
  font-size: 13px;
  font-weight: 600;
  color: #2563eb;
}

.explain-close-btn {
  border: none;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  color: #94a3b8;
  cursor: pointer;
  padding: 0 4px;
}

.explain-close-btn:hover {
  color: #475569;
}

.explain-truncated-hint {
  margin: 0;
  padding: 8px 14px;
  font-size: 12px;
  color: #b45309;
  background: #fef3c7;
}

.explain-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 14px;
  color: #64748b;
  font-size: 14px;
}

.explain-error {
  padding: 16px 14px;
  text-align: center;
}

.explain-error-text {
  margin: 0 0 12px;
  font-size: 13px;
  color: #dc2626;
}

.explain-result {
  padding: 14px;
}

.explain-content {
  margin: 0 0 12px;
  font-size: 14px;
  line-height: 1.7;
  color: #1e293b;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 260px;
  overflow-y: auto;
}

.explain-actions {
  display: flex;
  justify-content: flex-end;
  border-top: 1px solid #f1f5f9;
  padding-top: 10px;
}

.explain-copy-btn {
  padding: 5px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}

.explain-copy-btn:hover {
  border-color: #93b4f5;
  color: #2563eb;
}

/* ===== #6 翻页 / 缩放 ===== */
.reader-bar {
  flex-wrap: wrap;
}

.pdf-toolbar,
.zoom-toolbar {
  display: flex;
  align-items: center;
  gap: 6px;
}

.tool-btn {
  min-width: 30px;
  height: 30px;
  padding: 0 8px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  background: #fff;
  color: #334155;
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}

.tool-btn:hover:not(:disabled) {
  border-color: #93b4f5;
  color: #2563eb;
}

.tool-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.page-input {
  width: 52px;
  height: 30px;
  padding: 0 6px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 13px;
  text-align: center;
  outline: none;
}

.page-input:focus {
  border-color: #2563eb;
}

/* 去掉 number 输入框的上下箭头，省出宽度 */
.page-input::-webkit-outer-spin-button,
.page-input::-webkit-inner-spin-button {
  margin: 0;
  -webkit-appearance: none;
  appearance: none;
}

.page-total,
.zoom-value {
  color: #64748b;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.zoom-value {
  min-width: 42px;
  text-align: center;
}

/* 放大超出面板宽度时允许横向滚动；默认仍按宽度自适应 */
.canvas-wrap {
  overflow: auto;
}

.page-list.zoom-overflow {
  width: max-content;
  min-width: 100%;
}

.page-list.zoom-overflow .pdf-canvas {
  max-width: none;
}

/*共用状态卡片 */
.state-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 36px 24px;
}

.state-card h2 {
  margin: 0 0 8px;
  color: #475569;
  font-size: 18px;
}

.state-card p {
  margin: 0 0 16px;
  color: #94a3b8;
  overflow-wrap: anywhere;
}

.error-card h2,
.error-card p {
  color: #dc2626;
}

.btn-retry {
  display: inline-block;
  padding: 8px 20px;
  border: 0;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  font-size: 14px;
  cursor: pointer;
}

.btn-retry:hover {
  background: #1d4ed8;
}

.btn-retry:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/*右侧 Q&A 侧栏*/
.qa-sidebar {
  width: 400px;
  min-width: 320px;
  display: flex;
  flex-direction: column;
  background: white;
  border-left: 1px solid #e2e8f0;
}

.qa-header {
  padding: 14px 20px;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.qa-header h2 {
  margin: 0 0 4px;
  font-size: 18px;
  color: #1e293b;
}

.paper-badge {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.qa-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.qa-message {
  display: flex;
}

.msg-question {
  justify-content: flex-end;
}

.msg-answer {
  justify-content: flex-start;
}

.msg-bubble {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.question-bubble {
  background: #2563eb;
  color: white;
  border-bottom-right-radius: 4px;
}

.question-bubble p {
  margin: 0;
}

.answer-bubble {
  background: #f1f5f9;
  color: #334155;
  border-bottom-left-radius: 4px;
}

.answer-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

/* Loading 态 */
.loading-bubble {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #64748b;
}

.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #cbd5e1;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 错误态 */
.error-bubble {
  background: #fef2f2;
  border: 1px solid #fecaca;
}

.error-text {
  margin: 0 0 4px;
  color: #dc2626;
  font-weight: 600;
}

.error-detail {
  margin: 0 0 10px;
  font-size: 12px;
  color: #ef4444;
}

.error-bubble .btn-retry {
  font-size: 13px;
  padding: 6px 16px;
}

/* 引用列表 */
.citations {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid #e2e8f0;
}

.citations-title {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.citation-item {
  margin-bottom: 8px;
  padding: 8px 10px;
  background: #f8fafc;
  border-radius: 6px;
  border-left: 3px solid #2563eb;
}

.citation-item:last-child {
  margin-bottom: 0;
}

.citation-page {
  display: inline-block;
  margin-bottom: 4px;
  padding: 2px 9px;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}

.citation-page:hover:not(:disabled) {
  border-color: #93c5fd;
  background: #dbeafe;
  text-decoration: underline;
}

.citation-page:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}


.citation-snippet {
  margin: 0;
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
}

/* 空状态 */
.qa-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  text-align: center;
  color: #94a3b8;
  font-size: 14px;
}

/* 未配置 API Key 提示 */
.qa-config-notice {
  padding: 8px 16px;
  background: #fffbeb;
  border-top: 1px solid #fde68a;
  color: #92400e;
  font-size: 13px;
  flex-shrink: 0;
}

.qa-config-notice a {
  color: #2563eb;
  text-decoration: none;
  font-weight: 600;
}

.qa-config-notice a:hover {
  text-decoration: underline;
}

/* 输入区域 */
.qa-input-area {
  padding: 12px 16px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.qa-textarea {
  flex: 1;
  resize: none;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  line-height: 1.5;
  outline: none;
  transition: border-color 0.2s;
}

.qa-textarea:focus {
  border-color: #2563eb;
}

.qa-textarea:disabled {
  background: #f8fafc;
  cursor: not-allowed;
}

.qa-send-btn {
  padding: 0 20px;
  border: 0;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s;
  align-self: flex-end;
  height: 40px;
}

.qa-send-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.qa-send-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

/* 响应式 */
@media (max-width: 768px) {
  .reader-layout {
    flex-direction: column;
  }

  .pdf-panel {
    height: 45%;
  }

  .qa-sidebar {
    width: 100%;
    min-width: 0;
    height: 55%;
    border-left: 0;
    border-top: 1px solid #e2e8f0;
  }
}
</style>