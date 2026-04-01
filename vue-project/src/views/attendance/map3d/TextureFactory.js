import { CanvasTexture, RepeatWrapping, SRGBColorSpace, NearestFilter } from 'three'

function createCanvas(w, h) {
  const c = document.createElement('canvas')
  c.width = w
  c.height = h
  return c
}

function canvasToTexture(canvas, opts = {}) {
  const tex = new CanvasTexture(canvas)
  if (opts.repeat) { tex.wrapS = tex.wrapT = RepeatWrapping }
  if (opts.srgb) { tex.colorSpace = SRGBColorSpace }
  if (opts.nearest) { tex.magFilter = NearestFilter; tex.generateMipmaps = false }
  return tex
}

export function makeSideTexture() {
  const c = createCanvas(64, 256)
  const ctx = c.getContext('2d')
  const g = ctx.createLinearGradient(0, 0, 0, 256)
  g.addColorStop(0, 'rgba(48,179,255,0.9)')
  g.addColorStop(0.4, 'rgba(48,179,255,0.4)')
  g.addColorStop(1, 'rgba(48,179,255,0.05)')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, 64, 256)
  return canvasToTexture(c, { repeat: true, srgb: true })
}

export function makeTopNormalTexture() {
  const c = createCanvas(256, 256)
  const ctx = c.getContext('2d')
  ctx.fillStyle = '#8080ff'
  ctx.fillRect(0, 0, 256, 256)
  for (let i = 0; i < 400; i++) {
    const x = Math.random() * 256, y = Math.random() * 256
    const v = 120 + Math.random() * 16
    ctx.fillStyle = `rgb(${v},${v},255)`
    ctx.fillRect(x, y, 2, 2)
  }
  return canvasToTexture(c, { repeat: true })
}

export function makeGridTexture() {
  const c = createCanvas(64, 64)
  const ctx = c.getContext('2d')
  ctx.strokeStyle = 'rgba(0,255,255,0.3)'
  ctx.lineWidth = 0.5
  ctx.beginPath()
  ctx.moveTo(0, 0); ctx.lineTo(64, 0)
  ctx.moveTo(0, 0); ctx.lineTo(0, 64)
  ctx.stroke()
  return canvasToTexture(c, { repeat: true })
}

export function makeGridBlackTexture() {
  const c = createCanvas(64, 64)
  const ctx = c.getContext('2d')
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 45)
  g.addColorStop(0, 'rgba(255,255,255,1)')
  g.addColorStop(1, 'rgba(0,0,0,1)')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, 64, 64)
  return canvasToTexture(c, { repeat: true })
}

export function makeGaoguangTexture() {
  const c = createCanvas(512, 512)
  const ctx = c.getContext('2d')
  const g = ctx.createRadialGradient(256, 256, 0, 256, 256, 256)
  g.addColorStop(0, 'rgba(14,129,251,0.5)')
  g.addColorStop(0.5, 'rgba(14,129,251,0.15)')
  g.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, 512, 512)
  return canvasToTexture(c, { srgb: true })
}

export function makeGuangquanTexture() {
  const c = createCanvas(128, 128)
  const ctx = c.getContext('2d')
  ctx.beginPath()
  ctx.arc(64, 64, 50, 0, Math.PI * 2)
  ctx.strokeStyle = 'rgba(43,196,220,0.8)'
  ctx.lineWidth = 4
  ctx.stroke()
  const g = ctx.createRadialGradient(64, 64, 40, 64, 64, 60)
  g.addColorStop(0, 'rgba(43,196,220,0)')
  g.addColorStop(1, 'rgba(43,196,220,0.2)')
  ctx.fillStyle = g
  ctx.fill()
  return canvasToTexture(c)
}

export function makeGuangquan2Texture() {
  const c = createCanvas(128, 128)
  const ctx = c.getContext('2d')
  for (let i = 0; i < 3; i++) {
    ctx.beginPath()
    ctx.arc(64, 64, 30 + i * 12, 0, Math.PI * 2)
    ctx.strokeStyle = `rgba(43,196,220,${0.6 - i * 0.15})`
    ctx.lineWidth = 2
    ctx.stroke()
  }
  return canvasToTexture(c)
}

export function makeQuanTexture() {
  const c = createCanvas(512, 512)
  const ctx = c.getContext('2d')
  ctx.beginPath()
  ctx.arc(256, 256, 220, 0, Math.PI * 2)
  ctx.strokeStyle = 'rgba(72,175,255,0.3)'
  ctx.lineWidth = 2
  ctx.stroke()
  ctx.beginPath()
  ctx.arc(256, 256, 180, 0, Math.PI * 2)
  ctx.strokeStyle = 'rgba(72,175,255,0.15)'
  ctx.lineWidth = 1
  ctx.stroke()
  return canvasToTexture(c)
}

export function makeHuiguangTexture() {
  const c = createCanvas(32, 128)
  const ctx = c.getContext('2d')
  const g = ctx.createLinearGradient(0, 0, 0, 128)
  g.addColorStop(0, 'rgba(255,255,255,0)')
  g.addColorStop(0.3, 'rgba(255,255,255,0.6)')
  g.addColorStop(0.7, 'rgba(255,255,255,0.6)')
  g.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = g
  ctx.fillRect(12, 0, 8, 128)
  return canvasToTexture(c, { repeat: true, srgb: true })
}

export function makeRotationBorder1Texture() {
  const c = createCanvas(512, 512)
  const ctx = c.getContext('2d')
  ctx.strokeStyle = 'rgba(72,175,255,0.5)'
  ctx.lineWidth = 2
  ctx.setLineDash([20, 10])
  ctx.beginPath()
  ctx.arc(256, 256, 240, 0, Math.PI * 2)
  ctx.stroke()
  return canvasToTexture(c)
}

export function makeRotationBorder2Texture() {
  const c = createCanvas(512, 512)
  const ctx = c.getContext('2d')
  ctx.strokeStyle = 'rgba(72,175,255,0.6)'
  ctx.lineWidth = 1.5
  ctx.setLineDash([8, 16])
  ctx.beginPath()
  ctx.arc(256, 256, 220, 0, Math.PI * 2)
  ctx.stroke()
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2
    ctx.fillStyle = 'rgba(72,175,255,0.5)'
    ctx.beginPath()
    ctx.arc(256 + Math.cos(a) * 220, 256 + Math.sin(a) * 220, 3, 0, Math.PI * 2)
    ctx.fill()
  }
  return canvasToTexture(c)
}

export function makeFlyLineTexture() {
  const c = createCanvas(256, 32)
  const ctx = c.getContext('2d')
  const g = ctx.createLinearGradient(0, 0, 256, 0)
  g.addColorStop(0, 'rgba(255,255,255,0)')
  g.addColorStop(0.4, 'rgba(251,223,136,0.3)')
  g.addColorStop(1, 'rgba(251,223,136,1)')
  ctx.fillStyle = g
  ctx.fillRect(0, 8, 256, 16)
  const tex = canvasToTexture(c, { repeat: true, nearest: true })
  tex.repeat.set(0.5, 1)
  return tex
}

export function makeArrowTexture() {
  const c = createCanvas(64, 64)
  const ctx = c.getContext('2d')
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 28)
  g.addColorStop(0, 'rgba(255,255,0,1)')
  g.addColorStop(0.6, 'rgba(255,255,0,0.5)')
  g.addColorStop(1, 'rgba(255,255,0,0)')
  ctx.fillStyle = g
  ctx.beginPath()
  ctx.arc(32, 32, 28, 0, Math.PI * 2)
  ctx.fill()
  return canvasToTexture(c)
}

export function makePathLineTexture() {
  const c = createCanvas(256, 32)
  const ctx = c.getContext('2d')
  const g = ctx.createLinearGradient(0, 0, 256, 0)
  g.addColorStop(0, 'rgba(43,196,220,0)')
  g.addColorStop(0.5, 'rgba(43,196,220,0.8)')
  g.addColorStop(1, 'rgba(43,196,220,0)')
  ctx.fillStyle = g
  ctx.fillRect(0, 10, 256, 12)
  return canvasToTexture(c, { repeat: true })
}

export function makePathLine2Texture() {
  const c = createCanvas(256, 32)
  const ctx = c.getContext('2d')
  const g = ctx.createLinearGradient(0, 0, 256, 0)
  g.addColorStop(0, 'rgba(255,255,255,0)')
  g.addColorStop(0.5, 'rgba(255,255,255,0.9)')
  g.addColorStop(1, 'rgba(255,255,255,0)')
  ctx.fillStyle = g
  ctx.fillRect(0, 12, 256, 8)
  return canvasToTexture(c, { repeat: true })
}

export function makePointTexture() {
  const c = createCanvas(64, 64)
  const ctx = c.getContext('2d')
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 28)
  g.addColorStop(0, 'rgba(43,196,220,1)')
  g.addColorStop(0.5, 'rgba(43,196,220,0.4)')
  g.addColorStop(1, 'rgba(43,196,220,0)')
  ctx.fillStyle = g
  ctx.beginPath()
  ctx.arc(32, 32, 28, 0, Math.PI * 2)
  ctx.fill()
  return canvasToTexture(c)
}

export function makeLabelArrowTexture() {
  const c = createCanvas(27, 40)
  const ctx = c.getContext('2d')
  ctx.strokeStyle = 'rgba(43,196,220,0.8)'
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(13, 0)
  ctx.lineTo(13, 30)
  ctx.stroke()
  ctx.fillStyle = 'rgba(43,196,220,0.9)'
  ctx.beginPath()
  ctx.arc(13, 33, 4, 0, Math.PI * 2)
  ctx.fill()
  return canvasToTexture(c)
}
