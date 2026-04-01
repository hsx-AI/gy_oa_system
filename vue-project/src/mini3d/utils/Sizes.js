import { EventEmitter } from "./EventEmitter"

export class Sizes extends EventEmitter {
  constructor({ canvas }) {
    super()
    this.canvas = canvas
    this.pixelRatio = 0
    this.init()
    this._onResize = () => {
      this.init()
      this.emit("resize")
    }
    window.addEventListener("resize", this._onResize)
  }
  init() {
    const container = this.canvas?.parentElement
    if (container) {
      this.width = container.clientWidth
      this.height = container.clientHeight
    } else {
      this.width = window.innerWidth
      this.height = window.innerHeight
    }
    this.pixelRatio = this.pixelRatio || Math.min(window.devicePixelRatio, 2)
  }
  destroy() {
    this.off("resize")
    window.removeEventListener("resize", this._onResize)
  }
}
