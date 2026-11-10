<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { searchPapers, importPaper } from '../api/papers'

const router = useRouter()

const keyword = ref('')
const source = ref('arxiv')
const items = ref([])
const total = ref(0)
const loading = ref(false)
const errorMessage = ref('')
const degraded = ref(false)
const importingId = ref(null)
const searched = ref(false)

async function handleSearch() {
  const kw = keyword.value.trim()
  if (!kw) {
    errorMessage.value = '请输入关键词'
    return
  }

  loading.value = true
  errorMessage.value = ''
  degraded.value = false

  try {
    const result = await searchPapers(kw, source.value, 1, 10)
    items.value = result.items
    total.value = result.total
    degraded.value = result.degraded
    searched.value = true
  } catch (error) {
    errorMessage.value = error.message || '检索失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function handleImport(paper) {
  if (importingId.value !== null) return

  importingId.value = paper.arxivId || paper.doi || paper.title

  try {
    const data = await importPaper(paper)
    const paperId = data?.paperId
    if (!paperId) {
      throw new Error('导入成功但未返回 paperId')
    }
    router.push(`/reader/${paperId}?focus=qa`)
  } catch (error) {
    alert(error.message || '导入失败，请稍后重试')
  } finally {
    importingId.value = null
  }
}

function formatAuthors(authors) {
  if (!Array.isArray(authors) || authors.length === 0) return '未知作者'
  if (authors.length <= 3) return authors.join('、')
  return `${authors.slice(0, 3).join('、')} 等 ${authors.length} 人`
}

function sourceLabel(src) {
  const map = {
    arxiv: 'arXiv',
    openalex: 'OpenAlex',
    semanticscholar: 'Semantic Scholar',
    crossref: 'Crossref',
  }
  return map[src] || src
}
</script>

<template>
  <main class="search-page">
    <header class="page-header">
      <div>
        <p class="eyebrow">PAPERMIND</p>
        <h1>文献检索</h1>
        <p class="subtitle">从开放学术库中搜索论文，一键导入并提问。</p>
      </div>
    </header>

    <form class="search-bar" @submit.prevent="handleSearch">
      <input
        v-model="keyword"
        class="search-input"
        type="text"
        placeholder="输入关键词，例如：attention is all you need"
        :disabled="loading"
      />
      <select v-model="source" class="source-select" :disabled="loading">
        <option value="arxiv">arXiv</option>
      </select>
      <button class="search-button" type="submit" :disabled="loading">
        {{ loading ? '检索中…' : '检索' }}
      </button>
    </form>

    <section v-if="degraded && items.length === 0" class="state-card warning-card">
      <h2>外部学术库暂时不可用</h2>
      <p>网络连接超时或上游服务暂时不可达，请稍后重试。</p>
    </section>

    <section v-else-if="errorMessage" class="state-card error-card">
      <h2>检索失败</h2>
      <p>{{ errorMessage }}</p>
    </section>

    <section v-else-if="loading" class="state-card">
      <p>正在检索…</p>
    </section>

    <section v-else-if="searched && items.length === 0" class="state-card">
      <h2>没搜到相关结果</h2>
      <p>换个关键词试试。</p>
    </section>

    <section v-else class="result-list">
      <div v-if="degraded" class="degraded-banner">
        ⚠️ 外部学术库响应超时，以下为部分结果或缓存数据。
      </div>

      <article v-for="(paper, idx) in items" :key="paper.arxivId || paper.doi || idx" class="result-card">
        <div class="result-main">
          <h2 class="result-title">{{ paper.title || '未命名文献' }}</h2>

          <div class="result-meta">
            <span>{{ formatAuthors(paper.authors) }}</span>
            <span v-if="paper.year">{{ paper.year }}</span>
            <span class="source-tag">{{ sourceLabel(paper.source) }}</span>
            <span v-if="paper.pdfUrl" class="oa-tag">OA</span>
            <span v-else class="no-oa-tag">非 OA</span>
          </div>

          <p v-if="paper.abstract" class="result-abstract">{{ paper.abstract }}</p>
        </div>

        <div class="result-actions">
          <button
            class="import-button"
            :disabled="importingId !== null || !paper.pdfUrl"
            @click="handleImport(paper)"
          >
            <template v-if="importingId === (paper.arxivId || paper.doi || paper.title)">
              导入中…
            </template>
            <template v-else-if="!paper.pdfUrl">
              仅查看原文
            </template>
            <template v-else>
              导入并提问
            </template>
          </button>
          <a
            v-if="paper.landingUrl"
            class="text-link"
            :href="paper.landingUrl"
            target="_blank"
            rel="noopener"
          >查看原文</a>
        </div>
      </article>

      <footer v-if="items.length > 0" class="list-footer">
        共找到 {{ total }} 条结果（当前显示前 {{ items.length }} 条）
      </footer>
    </section>
  </main>
</template>

<style scoped>
.search-page {
  width: min(900px, calc(100% - 40px));
  margin: 48px auto;
  color: #202938;
}

.page-header {
  margin-bottom: 24px;
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

.search-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 24px;
}

.search-input {
  flex: 1;
  padding: 12px 14px;
  border: 1px solid #d5dce5;
  border-radius: 8px;
  font-size: 15px;
  outline: none;
}

.search-input:focus {
  border-color: #2563eb;
}

.source-select {
  padding: 12px 14px;
  border: 1px solid #d5dce5;
  border-radius: 8px;
  background: white;
  font-size: 15px;
  cursor: pointer;
}

.search-button {
  padding: 12px 22px;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.search-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
}

.error-card {
  border-color: #fecaca;
}

.warning-card {
  border-color: #fde68a;
  background: #fffbeb;
}

.degraded-banner {
  padding: 12px 16px;
  margin-bottom: 16px;
  border: 1px solid #fde68a;
  border-radius: 8px;
  background: #fffbeb;
  color: #92400e;
  font-size: 14px;
}

.result-list {
  display: grid;
  gap: 14px;
}

.result-card {
  display: flex;
  align-items: flex-start;
  gap: 18px;
  padding: 22px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: white;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.result-card:hover {
  border-color: #93b4f5;
  box-shadow: 0 5px 18px rgb(15 23 42 / 6%);
}

.result-main {
  flex: 1;
  min-width: 0;
}

.result-title {
  margin: 0 0 12px;
  font-size: 17px;
  overflow-wrap: anywhere;
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: center;
  color: #64748b;
  font-size: 13px;
}

.source-tag {
  padding: 2px 8px;
  border-radius: 4px;
  background: #eff6ff;
  color: #1d4ed8;
  font-weight: 600;
}

.oa-tag {
  padding: 2px 8px;
  border-radius: 4px;
  background: #dcfce7;
  color: #15803d;
  font-weight: 600;
}

.no-oa-tag {
  padding: 2px 8px;
  border-radius: 4px;
  background: #f1f5f9;
  color: #64748b;
  font-weight: 600;
}

.result-abstract {
  margin: 12px 0 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.result-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-shrink: 0;
  align-items: flex-end;
}

.import-button {
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  background: #2563eb;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.import-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.text-link {
  color: #2563eb;
  font-size: 13px;
  text-decoration: none;
}

.list-footer {
  margin-top: 20px;
  color: #64748b;
  font-size: 13px;
  text-align: right;
}

@media (max-width: 600px) {
  .search-page {
    margin: 28px auto;
  }

  .search-bar {
    flex-direction: column;
  }

  .result-card {
    flex-direction: column;
    gap: 14px;
    padding: 16px;
  }

  .result-actions {
    flex-direction: row;
    align-items: center;
  }
}
</style>