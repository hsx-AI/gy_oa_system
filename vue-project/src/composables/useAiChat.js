// AI 助手对话逻辑：基于 fetch + ReadableStream 解析后端 SSE 流式输出。
// 每次调用返回独立的会话状态，可在首页卡片与独立页面分别使用。
import { ref, reactive } from 'vue'

const CHAT_URL = '/api/ai-assistant/chat-stream'

function getCurrentUserName() {
  try {
    const raw = localStorage.getItem('userInfo')
    if (!raw) return ''
    const u = JSON.parse(raw)
    return (u.name || u.userName || '').trim()
  } catch {
    return ''
  }
}

let _uid = 0
function nextId() {
  _uid += 1
  return `m_${Date.now()}_${_uid}`
}

export function useAiChat() {
  const messages = ref([])      // { id, role, content, tools, attachments, error, streaming }
  const loading = ref(false)
  let abortController = null

  function reset() {
    if (loading.value) stop()
    messages.value = []
  }

  function stop() {
    if (abortController) {
      try { abortController.abort() } catch { /* ignore */ }
      abortController = null
    }
    loading.value = false
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant' && last.streaming) {
      last.streaming = false
      if (!last.content && !last.error) last.content = '（已停止）'
    }
  }

  async function send(text) {
    const content = (text || '').trim()
    if (!content || loading.value) return

    messages.value.push({
      id: nextId(), role: 'user', content,
      tools: [], attachments: [], error: '', streaming: false,
    })

    // 使用 reactive：直接修改该对象属性即可触发视图更新（普通对象 push 进 ref 数组后，
    // 修改原始引用不会触发依赖更新，会导致 status/流式正文不实时刷新）
    const assistant = reactive({
      id: nextId(), role: 'assistant', content: '', reasoning: '', status: '',
      tools: [], attachments: [], error: '', streaming: true,
    })
    messages.value.push(assistant)
    loading.value = true

    // 仅发送有内容的 user / assistant 文本作为历史
    const history = messages.value
      .filter(m => (m.role === 'user' || m.role === 'assistant') && m.content && m !== assistant)
      .map(m => ({ role: m.role, content: m.content }))

    abortController = new AbortController()
    try {
      const res = await fetch(CHAT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
        credentials: 'include',
        body: JSON.stringify({ messages: history, current_user: getCurrentUserName() }),
        signal: abortController.signal,
      })
      if (!res.ok) {
        let detail = `请求失败 (${res.status})`
        try { const j = await res.json(); detail = j.detail || j.message || detail } catch { /* ignore */ }
        throw new Error(detail)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        let sep
        while ((sep = buffer.indexOf('\n\n')) !== -1) {
          const rawEvent = buffer.slice(0, sep)
          buffer = buffer.slice(sep + 2)
          const dataLine = rawEvent.split('\n').find(l => l.startsWith('data:'))
          if (!dataLine) continue
          const jsonStr = dataLine.slice(5).trim()
          if (!jsonStr) continue
          let evt
          try { evt = JSON.parse(jsonStr) } catch { continue }
          handleEvent(evt, assistant)
        }
      }
    } catch (err) {
      if (err && err.name === 'AbortError') {
        // 用户主动停止，已在 stop() 处理
      } else {
        assistant.error = err?.message || '对话失败，请稍后重试'
      }
    } finally {
      assistant.streaming = false
      loading.value = false
      abortController = null
    }
  }

  function handleEvent(evt, assistant) {
    switch (evt.type) {
      case 'meta':
        assistant.model = evt.model
        break
      case 'tool': {
        const existing = assistant.tools.find(t => t.name === evt.name && t.status === 'running')
        if (evt.status === 'running') {
          if (!existing) assistant.tools.push({ name: evt.name, label: evt.label, status: 'running', summary: '' })
        } else if (evt.status === 'done') {
          if (existing) {
            existing.status = 'done'
            existing.summary = evt.summary || ''
          } else {
            assistant.tools.push({ name: evt.name, label: evt.label, status: 'done', summary: evt.summary || '' })
          }
        }
        break
      }
      case 'attachment':
        assistant.attachments.push({ label: evt.label, url: evt.url, filename: evt.filename })
        break
      case 'status':
        assistant.status = evt.text || ''
        break
      case 'reasoning':
        assistant.reasoning = (assistant.reasoning || '') + (evt.text || '')
        break
      case 'chunk':
        assistant.content += evt.text || ''
        assistant.status = ''
        break
      case 'error':
        assistant.error = evt.message || '模型调用出错'
        assistant.status = ''
        break
      case 'done':
        assistant.streaming = false
        assistant.status = ''
        break
      default:
        break
    }
  }

  return { messages, loading, send, stop, reset }
}

export default useAiChat
