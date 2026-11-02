const API_BASE = import.meta.env.VITE_API_BASE || ''

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

// 上传 PDF 文献（支持上传进度回调）
export function uploadPaper(file, onProgress) {
  return new Promise((resolve, reject) => {
    const formData = new FormData()
    formData.append('file', file)

    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}/api/papers`)

    if (onProgress) {
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          onProgress(Math.round((event.loaded / event.total) * 100))
        }
      })
    }

    xhr.addEventListener('load', () => {
      let result = null
      try {
        result = JSON.parse(xhr.responseText)
      } catch {
        reject(new Error('服务器返回了无法解析的响应'))
        return
      }

      if (xhr.status >= 200 && xhr.status < 300 && result?.code === 0) {
        resolve(result.data)
      } else {
        reject(new Error(result?.message || `请求失败（HTTP ${xhr.status}）`))
      }
    })

    xhr.addEventListener('error', () => {
      reject(new Error('网络连接失败，请检查后端服务是否启动'))
    })

    xhr.send(formData)
  })
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