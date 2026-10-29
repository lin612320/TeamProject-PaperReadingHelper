<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getPapers, getPaper } from '../api/papers'

const papers = ref([])
const loading = ref(false)
const errorMessage = ref('')
const refreshing = ref(false)

let pollTimer = null
let requestInProgress = false

// 格式化上传时间
function formatDate(value) {
  if (!value) return '未知'

  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return '未知'

  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 将后端状态转换为用户能看懂的文字
function statusText(status) {
  const statusMap = {
    pending: '等待解析',
    parsing: '正在解析',
    ready: '解析完成',
    failed: '解析失败',
  }

  return statusMap[status] || '状态未知'
}

// 加载文献列表
async function loadPapers(showLoading = true) {
  if (requestInProgress) return

  requestInProgress = true

  if (showLoading) loading.value = true

  errorMessage.value = ''

  try {
    papers.value = await getPapers(1, 20)
  } catch (error) {
    errorMessage.value =
      error.message || '文献列表加载失败，请稍后重试'
  } finally {
    loading.value = false
    refreshing.value = false
    requestInProgress = false
  }
}

// 更新正在解析的文献状态
async function refreshParsingStatuses() {
  const unfinished = papers.value.filter((paper) =>
    ['pending', 'parsing'].includes(paper.parseStatus)
  )

  if (unfinished.length === 0) {
    stopPolling()
    return
  }

  await Promise.all(
    unfinished.map(async (paper) => {
      try {
        const detail = await getPaper(paper.id)

        const index = papers.value.findIndex(
          (item) => item.id === paper.id
        )

        if (index !== -1) {
          papers.value[index] = {
            ...papers.value[index],
            ...detail,
          }
        }
      } catch (error) {
        // 单篇状态查询失败时保留原状态，
        // 下一轮继续查询，避免影响整个列表
        console.warn(
          `文献 ${paper.id} 的解析状态查询失败`,
          error
        )
      }
    })
  )

  // 所有文献都完成或失败后停止轮询
  const hasUnfinished = papers.value.some((paper) =>
    ['pending', 'parsing'].includes(paper.parseStatus)
  )

  if (!hasUnfinished) stopPolling()
}

// 开始轮询，每 3 秒检查一次
function startPolling() {
  stopPolling()

  const hasUnfinished = papers.value.some((paper) =>
    ['pending', 'parsing'].includes(paper.parseStatus)
  )

  if (hasUnfinished) {
    pollTimer = setInterval(refreshParsingStatuses, 3000)
  }
}

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

// 手动刷新
async function handleRefresh() {
  if (refreshing.value) return

  refreshing.value = true
  await loadPapers(false)
  startPolling()
}

// 点击文献进入阅读器
function openPaper(paper) {
  if (paper.parseStatus !== 'ready') return

  window.location.href = `/reader/${paper.id}`
}

onMounted(async () => {
  await loadPapers()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <main class="library-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">PAPERMIND</p>
        <h1>我的文献</h1>
        <p class="subtitle">管理已上传的论文，查看解析进度。</p>
      </div>

      <button
        class="refresh-button"
        :disabled="loading || refreshing"
        @click="handleRefresh"
      >
        {{ refreshing ? '刷新中…' : '刷新列表' }}
      </button>
    </header>

    <!-- 加载状态 -->
    <section v-if="loading" class="state-card">
      <p>正在加载文献列表…</p>
    </section>

    <!-- 错误状态 -->
    <section v-else-if="errorMessage" class="state-card error-card">
      <h2>暂时无法加载文献</h2>
      <p>{{ errorMessage }}</p>
      <button class="refresh-button" @click="handleRefresh">
        重试
      </button>
    </section>

    <!-- 空列表状态 -->
    <section v-else-if="papers.length === 0" class="state-card">
      <h2>还没有文献</h2>
      <p>上传 PDF 后，文献会显示在这里。</p>
      <a class="text-link" href="/">前往上传文献</a>
    </section>

    <!-- 文献列表 -->
    <section v-else class="paper-list">
      <article
        v-for="paper in papers"
        :key="paper.id"
        class="paper-card"
        :class="{ clickable: paper.parseStatus === 'ready' }"
        @click="openPaper(paper)"
      >
        <div class="file-icon" aria-hidden="true">PDF</div>

        <div class="paper-info">
          <h2>{{ paper.title || paper.filename || '未命名文献' }}</h2>

          <div class="paper-meta">
            <span>
              页数：{{ paper.pageCount ?? '暂不可用' }}
            </span>
            <span>上传时间：{{ formatDate(paper.createdAt) }}</span>
          </div>

          <div
            class="status"
            :class="`status-${paper.parseStatus || 'unknown'}`"
          >
            <span class="status-dot"></span>
            {{ statusText(paper.parseStatus) }}
          </div>

          <p v-if="paper.parseStatus === 'failed'" class="hint">
            解析未成功，请稍后刷新查看。
          </p>
          <p v-else-if="paper.parseStatus !== 'ready'" class="hint">
            解析完成后即可进入阅读器。
          </p>
        </div>

        <span
          v-if="paper.parseStatus === 'ready'"
          class="open-arrow"
          aria-hidden="true"
        >
          →
        </span>
      </article>
    </section>

    <footer v-if="papers.length > 0" class="list-footer">
      共 {{ papers.length }} 篇文献（当前显示前 20 篇）
    </footer>
  </main>
</template>

<style scoped>
.library-page {
  width: min(900px, calc(100% - 40px));
  margin: 48px auto;
  color: #202938;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 28px;
}

.eyebrow {
  margin: 0 0 8px;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 2px;
}

h1 {
  margin: 0;
  font-size: 30px;
}

.subtitle {
  color: #64748b;
  margin-top: 10px;
}

.refresh-button {
  padding: 10px 16px;
  border: 1px solid #d5dce5;
  border-radius: 8px;
  background: white;
  color: #202938;
  cursor: pointer;
}

.refresh-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.state-card {
  padding: 36px 24px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  text-align: center;
  background: #fff;
}

.state-card h2 {
  font-size: 18px;
}

.state-card p {
  color: #64748b;
  overflow-wrap: anywhere;
}

.error-card {
  border-color: #fecaca;
}

.text-link {
  color: #2563eb;
}

.paper-list {
  display: grid;
  gap: 14px;
}

.paper-card {
  display: flex;
  align-items: flex-start;
  gap: 18px;
  padding: 22px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: white;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.paper-card.clickable {
  cursor: pointer;
}

.paper-card.clickable:hover {
  border-color: #93b4f5;
  box-shadow: 0 5px 18px rgb(15 23 42 / 6%);
}

.file-icon {
  flex-shrink: 0;
  padding: 12px 8px;
  border-radius: 8px;
  background: #fff1f2;
  color: #be123c;
  font-size: 12px;
  font-weight: 800;
}

.paper-info {
  flex: 1;
  min-width: 0;
}

.paper-info h2 {
  margin: 0 0 12px;
  font-size: 17px;
  overflow-wrap: anywhere;
}

.paper-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 20px;
  color: #64748b;
  font-size: 13px;
}

.status {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-top: 14px;
  font-size: 13px;
  font-weight: 600;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #94a3b8;
}

.status-ready {
  color: #15803d;
}

.status-ready .status-dot {
  background: #22c55e;
}

.status-pending,
.status-parsing {
  color: #b45309;
}

.status-pending .status-dot,
.status-parsing .status-dot {
  background: #f59e0b;
}

.status-failed {
  color: #b91c1c;
}

.status-failed .status-dot {
  background: #ef4444;
}

.hint {
  margin: 8px 0 0;
  color: #64748b;
  font-size: 12px;
}

.open-arrow {
  color: #64748b;
  font-size: 24px;
}

.list-footer {
  margin-top: 20px;
  color: #64748b;
  font-size: 13px;
  text-align: right;
}

@media (max-width: 600px) {
  .library-page {
    margin: 28px auto;
  }

  .page-header {
    align-items: flex-start;
  }

  .paper-card {
    gap: 12px;
    padding: 16px;
  }

  .paper-meta {
    flex-direction: column;
    gap: 6px;
  }
}
</style>