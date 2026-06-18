// 轻量 Markdown 渲染：先转义 HTML，再处理常见语法，避免引入第三方依赖与 XSS 风险。
// 支持：代码块、行内代码、标题、加粗/斜体、无序/有序列表、简单表格、链接、换行。

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

// 将绝对地址（如 http://localhost:xxxx/api/ai-assistant/...）规范为相对路径，
// 保证部署后链接指向当前访问域名而非开发环境 localhost。
function normalizeLinkUrl(u) {
  const m = (u || '').match(/^https?:\/\/[^/]+(\/api\/ai-assistant\/.*)$/i)
  return m ? m[1] : u
}

function isBlockedGeneratedChartUrl(u) {
  const s = String(u || '')
  return /^https?:\/\//i.test(s)
    && /(via\.placeholder\.com|placehold\.co|quickchart\.io|image-charts\.com|chart\.googleapis\.com|placeholder|chart)/i.test(s)
    && !/^https?:\/\/[^/]+\/api\/ai-assistant\//i.test(s)
}

function inlineFormat(text) {
  let s = text
  // 行内代码
  s = s.replace(/`([^`]+)`/g, '<code class="md-code">$1</code>')
  // 加粗
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  // 斜体（避免影响加粗，已先处理加粗）
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>')
  // 链接 [text](url)
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|\/[^\s)]*)\)/g,
    (_m, label, url) => {
      if (isBlockedGeneratedChartUrl(url)) return '（图表请使用下方本地生成的附件下载）'
      return `<a href="${normalizeLinkUrl(url)}" target="_blank" rel="noopener" class="md-link">${label}</a>`
    })
  return s
}

function renderTable(lines) {
  // lines: 含表头、分隔、若干数据行
  const parseRow = (line) => line.replace(/^\||\|$/g, '').split('|').map(c => c.trim())
  const head = parseRow(lines[0])
  const body = lines.slice(2).map(parseRow)
  let html = '<table class="md-table"><thead><tr>'
  head.forEach(h => { html += `<th>${inlineFormat(h)}</th>` })
  html += '</tr></thead><tbody>'
  body.forEach(row => {
    html += '<tr>'
    head.forEach((_, i) => { html += `<td>${inlineFormat(row[i] || '')}</td>` })
    html += '</tr>'
  })
  html += '</tbody></table>'
  return html
}

export function renderMarkdown(raw) {
  if (!raw) return ''
  const escaped = escapeHtml(raw)
  const lines = escaped.split('\n')
  const out = []
  let i = 0
  let inList = null // 'ul' | 'ol'

  const closeList = () => {
    if (inList) { out.push(`</${inList}>`); inList = null }
  }

  while (i < lines.length) {
    const line = lines[i]

    // 代码块 ```
    if (/^\s*```/.test(line)) {
      closeList()
      const buf = []
      i++
      while (i < lines.length && !/^\s*```/.test(lines[i])) {
        buf.push(lines[i]); i++
      }
      i++ // 跳过结束 ```
      out.push(`<pre class="md-pre"><code>${buf.join('\n')}</code></pre>`)
      continue
    }

    // 表格：当前行与下一行形如 |---|---|
    if (/^\s*\|.*\|\s*$/.test(line) && i + 1 < lines.length && /^\s*\|?[\s:-]*\|[\s:|-]*$/.test(lines[i + 1])) {
      closeList()
      const tbl = [line, lines[i + 1]]
      let j = i + 2
      while (j < lines.length && /^\s*\|.*\|\s*$/.test(lines[j])) { tbl.push(lines[j]); j++ }
      out.push(renderTable(tbl))
      i = j
      continue
    }

    // 标题
    const h = line.match(/^(#{1,4})\s+(.*)$/)
    if (h) {
      closeList()
      const level = h[1].length + 2 // h3~h6，避免与页面主标题冲突
      out.push(`<h${level} class="md-h">${inlineFormat(h[2])}</h${level}>`)
      i++
      continue
    }

    // 无序列表
    if (/^\s*[-*+]\s+/.test(line)) {
      if (inList !== 'ul') { closeList(); out.push('<ul class="md-ul">'); inList = 'ul' }
      out.push(`<li>${inlineFormat(line.replace(/^\s*[-*+]\s+/, ''))}</li>`)
      i++
      continue
    }

    // 有序列表
    if (/^\s*\d+\.\s+/.test(line)) {
      if (inList !== 'ol') { closeList(); out.push('<ol class="md-ol">'); inList = 'ol' }
      out.push(`<li>${inlineFormat(line.replace(/^\s*\d+\.\s+/, ''))}</li>`)
      i++
      continue
    }

    // 空行
    if (/^\s*$/.test(line)) {
      closeList()
      i++
      continue
    }

    // 普通段落
    closeList()
    out.push(`<p class="md-p">${inlineFormat(line)}</p>`)
    i++
  }
  closeList()
  return out.join('\n')
}

export default renderMarkdown
