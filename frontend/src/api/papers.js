const API_BASE = import.meta.env.VITE_API_BASE || ''

// 将各种异常统一转换为人话
function formatApiError(error, response, result) {
  if (error?.name === 'AbortError') {
    return new Error('请求超时，请稍后重试')
  }

  if (error instanceof TypeError) {
    return new Error('网络连接失败，请检查网络或后端服务是否启动')
  }

  if (response && !response.ok) {
    const status = response.status
    const friendlyMap = {
      400: '请求参数有误，请检查输入',
      401: '登录已失效，请重新登录',
      403: '没有权限执行此操作',
      404: '请求的资源不存在',
      413: '文件过大，请选择更小的文件',
      422: '提交的数据格式有误',
      429: '请求过于频繁，请稍后再试',
      500: '服务器内部错误，请稍后重试',
      502: '服务器暂时不可用，请稍后重试',
      503: '服务器正在维护，请稍后重试',
      504: '服务器响应超时，请稍后重试',
    }
    const msg = friendlyMap[status] || result?.message
    if (msg) return new Error(msg)
    return new Error(`请求失败（HTTP ${status}）`)
  }

  if (result && result.code !== 0) {
    return new Error(result.message || '操作失败，请稍后重试')
  }

  if (error instanceof Error) return error
  return new Error('操作失败，请稍后重试')
}

// 统一处理后端返回结果
async function request(url) {
  let response
  let result
  try {
    response = await fetch(`${API_BASE}${url}`)
    result = await response.json().catch(() => null)
  } catch (error) {
    throw formatApiError(error)
  }

  if (!response.ok || !result || result.code !== 0) {
    throw formatApiError(null, response, result)
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
        return
      }

      const statusFriendly = {
        400: '请求参数有误，请检查输入',
        401: '登录已失效，请重新登录',
        403: '没有权限执行此操作',
        404: '请求的资源不存在',
        413: '文件过大，请选择更小的文件',
        422: '提交的数据格式有误',
        429: '请求过于频繁，请稍后再试',
        500: '服务器内部错误，请稍后重试',
        502: '服务器暂时不可用，请稍后重试',
        503: '服务器正在维护，请稍后重试',
        504: '服务器响应超时，请稍后重试',
      }
      reject(new Error(result?.message || statusFriendly[xhr.status] || '上传失败，请稍后重试'))
    })

    xhr.addEventListener('error', () => {
      reject(new Error('网络连接失败，请检查后端服务是否启动'))
    })

    xhr.send(formData)
  })
}

// 针对单篇论文提问（25 秒超时，超过则中止并抛错）
// aiConfig 可选，包含用户在设置页配置的 apiKey/baseUrl/model
export async function askQuestion(paperId, question, aiConfig = null) {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 25000)

  const payload = { paperId, question }
  if (aiConfig) {
    payload.apiKey = aiConfig.apiKey
    payload.baseUrl = aiConfig.baseUrl
    payload.model = aiConfig.model
  }

  let response
  let result
  try {
    response = await fetch(`${API_BASE}/api/qa/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })

    result = await response.json().catch(() => null)
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error('AI 服务响应超时（>25s），请稍后重试')
    }
    throw formatApiError(error)
  } finally {
    clearTimeout(timeoutId)
  }

  if (!response.ok || !result || result.code !== 0) {
    throw formatApiError(null, response, result)
  }

  return result.data
}

// 关键词检索外部学术库
// source 默认 arxiv；返回 { items, total, degraded, cached }
export async function searchPapers(keyword, source = 'arxiv', page = 1, size = 10) {
  const params = new URLSearchParams({
    keyword,
    source,
    page: String(page),
    size: String(size),
  })

  const data = await request(`/api/search?${params.toString()}`)

  return {
    items: data?.items ?? [],
    total: data?.total ?? 0,
    degraded: data?.degraded === true,
    cached: data?.cached === true,
  }
}

// 把检索到的一条论文导入本库
// 入参是 /api/search 返回的 PaperMeta 原样回传
// 返回 { paperId }
export async function importPaper(paperMeta) {
  let response
  let result
  try {
    response = await fetch(`${API_BASE}/api/papers/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(paperMeta),
    })
    result = await response.json().catch(() => null)
  } catch (error) {
    throw formatApiError(error)
  }

  if (!response.ok || !result || result.code !== 0) {
    throw formatApiError(null, response, result)
  }

  return result.data
}