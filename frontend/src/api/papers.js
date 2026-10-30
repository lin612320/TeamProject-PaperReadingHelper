const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

// 统一处理后端返回结果
async function request(url) {
  const response = await fetch(`${API_BASE}${url}`)
  const result = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(result?.message || `请求失败（HTTP ${response.status}）`)
  }

  if (!result || result.code !== 0) {
    throw new Error(result?.message || '服务器返回了异常结果')
  }

  return result.data
}

// 获取文献列表
export async function getPapers(page = 1, size = 20) {
  const data = await request(
    `/api/papers?page=${page}&size=${size}`
  )

  return { items: data?.items ?? [], total: data?.total ?? 0 }
}

// 获取单篇文献详情，用于查询解析状态
export async function getPaper(paperId) {
  return request(`/api/papers/${encodeURIComponent(paperId)}`)
}

// 针对单篇论文提问（25 秒超时，超过则中止并抛错）
export async function askQuestion(paperId, question) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 25000)

  try {
    const response = await fetch(`${API_BASE}/api/qa/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paperId, question }),
      signal: controller.signal,
    })

    const result = await response.json().catch(() => null)

    if (!response.ok) {
      throw new Error(result?.message || `请求失败（HTTP ${response.status}）`)
    }

    if (!result || result.code !== 0) {
      throw new Error(result?.message || '服务器返回了异常结果')
    }

    return result.data
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('AI 服务响应超时（>25s），请稍后重试')
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}