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

  return data?.items ?? []
}

// 获取单篇文献详情，用于查询解析状态
export async function getPaper(paperId) {
  return request(`/api/papers/${encodeURIComponent(paperId)}`)
}