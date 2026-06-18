// AI 助手对话逻辑：基于 fetch + ReadableStream 解析后端 SSE 流式输出。
// 每次调用返回独立的会话状态，可在首页卡片与独立页面分别使用。
// 支持：多会话（localStorage 持久化）、新建对话、历史切换、当前模型展示。
import { ref, reactive } from 'vue'

const CHAT_URL = '/api/ai-assistant/chat-stream'
const MODEL_INFO_URL = '/api/ai-assistant/model-info'

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

// 将可能出现的绝对地址（如 http://localhost:xxxx/api/ai-assistant/...）统一改为相对路径，
// 保证部署到服务器后下载链接始终指向当前访问的域名，而不是开发环境的 localhost。
function normalizeApiUrl(u) {
  const s = (u || '').trim()
  if (!s) return s
  const m = s.match(/^https?:\/\/[^/]+(\/api\/ai-assistant\/.*)$/i)
  if (m) return m[1]
  return s
}

export function useAiChat(options = {}) {
  const persist = !!options.persist
  const messages = ref([])      // { id, role, content, tools, attachments, error, streaming }
  const loading = ref(false)
  const sessions = ref([])      // [{ id, title, updatedAt, messages }]（仅 persist 模式）
  const currentSessionId = ref('')
  const currentModel = ref('')  // 当前生效模型（只读展示）
  let abortController = null

  const storageKey = () => `aiChatSessions_${getCurrentUserName() || 'guest'}`

  function loadSessions() {
    if (!persist) return
    try {
      const raw = localStorage.getItem(storageKey())
      sessions.value = raw ? (JSON.parse(raw) || []) : []
    } catch {
      sessions.value = []
    }
    // 默认载入最近一条会话；没有则开启空白新对话
    if (sessions.value.length) {
      const latest = sessions.value[0]
      currentSessionId.value = latest.id
      messages.value = (latest.messages || []).map(m => ({ ...m, streaming: false }))
    } else {
      currentSessionId.value = nextId()
      messages.value = []
    }
  }

  function persistSessions() {
    if (!persist) return
    try {
      localStorage.setItem(storageKey(), JSON.stringify(sessions.value.slice(0, 30)))
    } catch { /* ignore quota */ }
  }

  function deriveTitle() {
    const firstUser = messages.value.find(m => m.role === 'user' && m.content)
    const t = (firstUser?.content || '新对话').trim().replace(/\s+/g, ' ')
    return t.length > 20 ? `${t.slice(0, 20)}…` : t
  }

  // 将当前消息写回会话列表（去掉运行态字段）
  function saveCurrent() {
    if (!persist) return
    if (!messages.value.length) return
    const snapshot = messages.value.map(m => ({
      id: m.id, role: m.role, content: m.content || '',
      reasoning: m.reasoning || '', tools: m.tools || [],
      attachments: m.attachments || [], error: m.error || '',
    }))
    const entry = {
      id: currentSessionId.value || nextId(),
      title: deriveTitle(),
      updatedAt: Date.now(),
      messages: snapshot,
    }
    currentSessionId.value = entry.id
    const idx = sessions.value.findIndex(s => s.id === entry.id)
    if (idx >= 0) sessions.value.splice(idx, 1)
    sessions.value.unshift(entry)
    persistSessions()
  }

  function newConversation() {
    if (loading.value) stop()
    saveCurrent()
    currentSessionId.value = nextId()
    messages.value = []
  }

  function switchSession(id) {
    if (loading.value) stop()
    saveCurrent()
    const s = sessions.value.find(x => x.id === id)
    if (!s) return
    currentSessionId.value = s.id
    messages.value = (s.messages || []).map(m => ({ ...m, streaming: false }))
  }

  function deleteSession(id) {
    const idx = sessions.value.findIndex(s => s.id === id)
    if (idx >= 0) sessions.value.splice(idx, 1)
    persistSessions()
    if (id === currentSessionId.value) {
      currentSessionId.value = nextId()
      messages.value = []
    }
  }

  function reset() {
    if (loading.value) stop()
    messages.value = []
  }

  async function fetchModel() {
    try {
      const res = await fetch(`${MODEL_INFO_URL}?current_user=${encodeURIComponent(getCurrentUserName())}`, {
        credentials: 'include',
      })
      if (!res.ok) return
      const j = await res.json()
      currentModel.value = j?.label || j?.model || ''
    } catch { /* ignore */ }
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
      saveCurrent()
    }
  }

  function handleEvent(evt, assistant) {
    switch (evt.type) {
      case 'meta':
        assistant.model = evt.model
        if (evt.model) currentModel.value = evt.label || currentModel.value || evt.model
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
        assistant.attachments.push({ label: evt.label, url: normalizeApiUrl(evt.url), filename: evt.filename })
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

  return {
    messages, loading, send, stop, reset,
    sessions, currentSessionId, currentModel,
    loadSessions, newConversation, switchSession, deleteSession, fetchModel,
  }
}

export default useAiChat
