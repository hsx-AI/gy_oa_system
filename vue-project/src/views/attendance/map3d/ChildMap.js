import { Group, RepeatWrapping, LineBasicMaterial, Vector3, SpriteMaterial, Sprite, Color } from "three"
import { ExtrudeMap } from "./extrudeMap"
import { getBoundBox, emptyObject } from "@/mini3d"
import { geoMercator } from "d3-geo"
import { gsap } from "gsap"
export class ChildMap {
  constructor(parent, options) {
    this.parent = parent
    this.instance = new Group()
    this.instance.rotateX(-Math.PI / 2)
    this.instance.position.set(0, 0.2, 0)
    let defaultOptions = {
      adcode: 10000,
      center: [0, 0],
      centroid: [0, 0],
      childrenNum: 0,
      parentBoxSize: [1, 1], // 上级地图的尺寸
      mapData: {},
      geoProjectionCenter: [0, 0],
      geoProjectionScale: 120,
      geoProjectionTranslate: [0, 0],
    }
    this.options = Object.assign({}, defaultOptions, options)
    // 是否点击了
    this.clicked = false
    // 缩放值
    this.scale = 1
    // 地图的box大小
    this.boundBox = {}
    // 地图的区域数据
    this.areaData = []
    // 区域标签
    this.allAreaLabel = []
    // 区域标签组
    this.areaLabelGroup = new Group()
    // 区域点组
    this.areaPointGroup = new Group()
    // 信息标签组
    this.allInfoLabel = []
    this.infoLabelGroup = new Group()
    this.instance.add(this.areaLabelGroup, this.areaPointGroup, this.infoLabelGroup)
    // 事件元素
    this.eventElement = []
    this.pointEventElement = []
    this.init()
  }
  init() {
    this.createModel()
    this.addLabel()
    if (this.options.childrenNum) {
      this.addEvent()
    }
    this.addPointEvent()
  }
  createModel() {
    let { map } = this.createMap()
    this.setScale(map)
    map.setParent(this.instance)
  }
  // 创建省份
  createMap() {
    // 广东地图
    let mapJsonData = this.options.mapData
    let topNormal = this.parent.assets.instance.getResource("topNormal")
    topNormal.wrapS = topNormal.wrapT = RepeatWrapping

    // 地图线
    this.mapLineMaterial = new LineBasicMaterial({
      color: 0x2bc4dc,
      opacity: 0,
      transparent: true,
      fog: false,
    })
    let [top, side] = this.parent.createProvinceMaterial()
    let topMaterial = top.clone()
    topMaterial.opacity = 1
    let sideMaterial = side.clone()
    sideMaterial.opacity = 1
    let map = new ExtrudeMap(this.parent, {
      center: this.options.center,
      position: new Vector3(0, 0, 0.06),
      data: mapJsonData,
      depth: this.parent.depth,
      topFaceMaterial: topMaterial,
      sideMaterial: sideMaterial,
      lineMaterial: this.parent.mapLineMaterial,
      renderOrder: 9,
    })
    this.areaData = map.coordinates

    let { boxSize, box3 } = getBoundBox(map.mapGroup)
    map.mapGroup.children.map((group, index) => {
      group.children.map((mesh) => {
        if (mesh.type === "Mesh") {
          mesh.userData.type = "map"
          this.eventElement.push(mesh)
          this.parent.calcUv2(mesh.geometry, boxSize.x, boxSize.y, box3.min.x, box3.min.y)
        }
      })
    })

    return {
      map,
    }
  }

  addEvent() {
    let objectsHover = []

    const reset = (mesh) => {
      gsap.to(mesh.scale, {
        duration: 0.3,
        z: 1,
        onComplete: () => {
          mesh.traverse((obj) => {
            if (obj.isMesh) {
              obj.material[0].emissive.setHex(mesh.userData.materialEmissiveHex)
              obj.material[0].emissiveIntensity = 1
              obj.renderOrder = 9
            }
          })
        },
      })

      this.setLabelMove(mesh.userData.adcode, "down")
      this.setPointMove(mesh.userData.adcode, "down")
    }
    const move = (mesh) => {
      gsap.to(mesh.scale, {
        duration: 0.3,
        z: 1.5,
      })

      this.setLabelMove(mesh.userData.adcode)
      this.setPointMove(mesh.userData.adcode)

      mesh.traverse((obj) => {
        if (obj.isMesh) {
          obj.material[0].emissive.setHex(0x0b112d)
          obj.material[0].emissiveIntensity = 1.5
          obj.renderOrder = 21
        }
      })
    }

    // 循环添加事件
    this.eventElement.map((mesh) => {
      this.parent.interactionManager.add(mesh)
      mesh.addEventListener("mousedown", (event) => {
        if (this.clicked) return false
        this.clicked = true
        let userData = event.target.parent.userData
        this.parent.history.push(userData)
        this.parent.loadChildMap(userData)
      })
      mesh.addEventListener("mouseup", (ev) => {
        this.clicked = false
      })
      mesh.addEventListener("mouseover", (event) => {
        if (!objectsHover.includes(event.target.parent)) {
          objectsHover.push(event.target.parent)
        }

        document.body.style.cursor = "pointer"
        move(event.target.parent)
      })
      mesh.addEventListener("mouseout", (event) => {
        objectsHover = objectsHover.filter((n) => n.userData.name !== event.target.parent.userData.name)
        if (objectsHover.length > 0) {
          const mesh = objectsHover[objectsHover.length - 1]
        }
        reset(event.target.parent)
        document.body.style.cursor = "default"
      })
    })
  }
  // 添加标点事件
  addPointEvent() {
    let objectsHover = []

    this.pointEventElement.map((mesh) => {
      this.parent.interactionManager.add(mesh)
      mesh.addEventListener("mousedown", (event) => {
        if (this.clicked) return false
        this.clicked = true
        let userData = event.target.userData
        this.allInfoLabel.map((label, index) => {
          label.hide()
          if (userData.index === index) {
            label.show()
          }
        })
      })
      mesh.addEventListener("mouseup", (ev) => {
        this.clicked = false
      })
      mesh.addEventListener("mouseover", (event) => {
        if (!objectsHover.includes(event.target.parent)) {
          objectsHover.push(event.target.parent)
        }

        document.body.style.cursor = "pointer"
        let sprite = event.target
        sprite.material = this.pointHoverMaterial.clone()
      })
      mesh.addEventListener("mouseout", (event) => {
        objectsHover = objectsHover.filter((n) => n.userData.name !== event.target.parent.userData.name)
        if (objectsHover.length > 0) {
          const mesh = objectsHover[objectsHover.length - 1]
        }

        document.body.style.cursor = "default"
        let sprite = event.target
        sprite.material = this.pointDefaultMaterial.clone()
      })
    })
  }
  // 设置标签移动
  setLabelMove(adcode, type = "up") {
    ;[...this.allAreaLabel].map((label) => {
      if (label.userData.adcode === adcode) {
        gsap.to(label.position, {
          duration: 0.3,
          z: type === "up" ? label.userData.position[2] + 3 / this.scale : label.userData.position[2],
        })
      }
    })
  }
  // 设置点移动
  setPointMove(adcode, type = "up") {
    this.areaPointGroup.children.map((point) => {
      if (point.userData.adcode === adcode) {
        gsap.to(point.position, {
          duration: 0.3,
          z: type === "up" ? point.userData.position[2] + 3 / this.scale : point.userData.position[2],
        })
      }
    })
  }
  addLabel() {
    // 贴图
    const texture = this.parent.assets.instance.getResource("point")

    const material = new SpriteMaterial({
      map: texture,
      color: 0xffffff,
      transparent: true,
      depthTest: false,
    })
    this.pointDefaultMaterial = material
    this.pointHoverMaterial = material.clone()
    this.pointHoverMaterial.color = new Color(0x00ffff)
    const sprite = new Sprite(material)
    sprite.renderOrder = 23
    this.areaData.map((item, index) => {
      let [x, y] = this.geoProjection(item.centroid)
      // 名称
      let nameLabel = this.labelNameStyle(item, index, new Vector3(x, -y, 0))
      this.allAreaLabel.push(nameLabel)
      // 信息
      let infoLabel = this.infoLabel(item, index, new Vector3(x, -y, 0))
      this.allInfoLabel.push(infoLabel)

      //点
      let areaPoint = sprite.clone()
      sprite.material = material.clone()
      areaPoint.position.set(x, -y, 0)
      areaPoint.userData.adcode = item.adcode

      areaPoint.userData.type = "point"
      areaPoint.userData.name = item.name
      areaPoint.userData.position = [x, -y, 0]
      areaPoint.userData.index = index
      this.areaPointGroup.add(areaPoint)
    })
    this.setNameScale()
    this.setInfoScale()
    this.setPointScale()
  }
  infoLabel(data, index, position) {
    let label3d = this.parent.label3d
    let label = label3d.create("", "info-point", true)

    label.init(
      ` <div class="info-point-wrap">
      <div class="info-point-wrap-inner">
        <div class="info-point-line">
          <div class="line"></div>
          <div class="line"></div>
          <div class="line"></div>
        </div>
        <div class="info-point-content">
          <div class="content-item"><span class="label">名称</span><span class="value">${data.name}</span></div>
          <div class="content-item"><span class="label">PM2.5</span><span class="value">100ug/m²</span></div>
          <div class="content-item"><span class="label">等级</span><span class="value">良好</span></div>
        </div>
      </div>
    </div>
  `,
      position
    )
    label3d.setLabelStyle(label, 0.06 / this.scale, "x")
    label.setParent(this.infoLabelGroup)
    label.hide()
    return label
  }
  // 城市标签
  labelNameStyle(data, index, position) {
    let label3d = this.parent.label3d
    let label = label3d.create("", "area-name-label", true)
    label.init(`<div class="area-name-label-wrap">${data.name}</div>`, position)
    label3d.setLabelStyle(label, 0.08 / this.scale, "x")
    label.setParent(this.areaLabelGroup)
    label.userData.adcode = data.adcode
    label.userData.position = [position.x, position.y, position.z]
    return label
  }

  calculateScale(parentBoxSize, boxSize) {
    let xScale = parentBoxSize[0] / boxSize[0]
    let yScale = parentBoxSize[1] / boxSize[1]
    let scale = Math.min(xScale, yScale)

    return scale
  }

  setScale(map) {
    let { parentBoxSize } = this.options
    let boundBox = getBoundBox(map.mapGroup)

    let scale = this.calculateScale(parentBoxSize, [boundBox.boxSize.x, boundBox.boxSize.y])
    // 子地图缩放到主地图大小
    map.mapGroup.scale.set(scale, scale, 1)
    let boundBox1 = getBoundBox(map.mapGroup)
    // 放大后，中心坐标有偏移，偏移了多少，就反向移动多少
    map.mapGroup.position.x = -boundBox1.center.x
    map.mapGroup.position.y = -boundBox1.center.y
    this.scale = scale
    this.boundBox = boundBox1
  }

  setNameScale() {
    this.areaLabelGroup.scale.set(this.scale, this.scale, this.scale)

    this.areaLabelGroup.position.x = -this.boundBox.center.x
    this.areaLabelGroup.position.y = -this.boundBox.center.y
    this.allAreaLabel.map((label) => {
      let z = (this.parent.depth + 0.4) / this.scale
      label.position.z = z

      label.position.y -= 1.5 / this.scale
      label.userData.position = [label.position.x, label.position.y, label.position.z]
    })
  }

  setPointScale() {
    this.areaPointGroup.scale.set(this.scale, this.scale, this.scale)

    this.areaPointGroup.position.x = -this.boundBox.center.x
    this.areaPointGroup.position.y = -this.boundBox.center.y
    this.areaPointGroup.children.map((point) => {
      let z = (this.parent.depth + 1.4) / this.scale
      point.position.z = z
      point.userData.position[2] = z

      point.scale.set(5 / this.scale, 5 / this.scale, 5 / this.scale)

      point.userData.position = [point.position.x, point.position.y, point.position.z]

      this.pointEventElement.push(point)
    })
  }

  setInfoScale() {
    this.infoLabelGroup.scale.set(this.scale, this.scale, this.scale)

    this.infoLabelGroup.position.x = -this.boundBox.center.x
    this.infoLabelGroup.position.y = -this.boundBox.center.y
    this.infoLabelGroup.children.map((point) => {
      let z = (this.parent.depth + 10) / this.scale
      point.position.z = z

      point.scale.set(0.06 / this.scale, 0.06 / this.scale, 0.06 / this.scale)
    })
  }
  geoProjection = (args) => {
    let { geoProjectionScale, geoProjectionTranslate, center } = this.options
    return geoMercator().center(center).scale(geoProjectionScale).translate(geoProjectionTranslate)(args)
  }

  setParent(parent) {
    parent.add(this.instance)
  }

  destroy() {
    ;[...this.allAreaLabel, ...this.allInfoLabel].map((label) => {
      label.remove()
    })
    this.removeElement(".area-name-label")
    this.removeElement(".info-point")
    ;[...this.eventElement, ...this.pointEventElement].map((mesh) => {
      this.parent.interactionManager.remove(mesh)
    })

    emptyObject(this.instance)
  }
  removeElement(elementClassName) {
    var elements = document.querySelectorAll(elementClassName)
    for (let i = 0; i < elements.length; i++) {
      const element = elements[i]
      const parent = element.parentNode
      parent.removeChild(element)
    }
  }
}
