import {
  Fog, Group, MeshBasicMaterial, DirectionalLight, AmbientLight, PointLight,
  Vector3, LineBasicMaterial, Color, MeshStandardMaterial, PlaneGeometry,
  PointsMaterial, Mesh, DoubleSide, RepeatWrapping, SRGBColorSpace,
  AdditiveBlending, NearestFilter, BoxGeometry
} from 'three'
import {
  Mini3d, Particles, FlyLine, PathLine, Label3d, Plane,
  GradientShader, getBoundBox
} from '@/mini3d'
import { Assets } from './Assets'
import { ExtrudeMap } from './extrudeMap'
import { DiffuseShader } from './DiffuseShader'
import { Reflector } from './Reflector'
import { InteractionManager } from 'three.interactive'
import gsap from 'gsap'

function sortByValue(data) {
  data.sort((a, b) => b.value - a.value)
  return data
}

export class World extends Mini3d {
  constructor(canvas, config) {
    super(canvas, config)
    this.pointCenter = [108.55, 34.32]
    this.flyLineCenter = [126.6424, 45.757]
    this.depth = 5
    this.scene.fog = new Fog(0x011024, 1, 500)
    this.scene.background = new Color(0x011024)
    this.camera.instance.position.set(0.00002366776247217723, 225.1025284992283, 0.0002238648924037432)
    this.camera.instance.near = 1
    this.camera.instance.far = 10000
    this.camera.instance.updateProjectionMatrix()

    this.interactionManager = new InteractionManager(
      this.renderer.instance, this.camera.instance, this.canvas
    )
    this.renderer.resize()
    this.initEnvironment()
    this.tripData = []

    this.assets = new Assets(() => {
      this.sceneGroup = new Group()
      this.mainSceneGroup = new Group()
      this.labelGroup = new Group()
      this.gqGroup = new Group()
      this.provinceNameGroup = new Group()
      this.label3d = new Label3d(this)
      this.mainSceneGroup.rotateX(-Math.PI / 2)
      this.mainSceneGroup.add(this.labelGroup, this.gqGroup, this.provinceNameGroup)
      this.sceneGroup.add(this.mainSceneGroup)
      this.scene.add(this.sceneGroup)

      this.createFloor()
      this.createRotateBorder()
      this.createModel()
      this.addEvent()
      this.createParticles()
      this.createStorke()

      this.runEntryAnimation()
      this.config.onReady && this.config.onReady()
    })
  }

  initEnvironment() {
    this.scene.add(new AmbientLight(0xffffff, 2))
    const dir = new DirectionalLight(0xffffff, 4)
    dir.position.set(-30, 6, -8)
    dir.castShadow = true
    dir.shadow.radius = 20
    dir.shadow.mapSize.set(1024, 1024)
    this.scene.add(dir)
    this._addPointLight('#0e81fb', 160, 10000, -3, 16, -3)
    this._addPointLight('#1f5f7a', 100, 100, -4, 8, 43)
  }

  _addPointLight(color, intensity, distance, x, y, z) {
    const pl = new PointLight(new Color(color).getHex(), intensity, distance, 1)
    pl.position.set(x, y, z)
    this.scene.add(pl)
  }

  createModel() {
    const mapGroup = new Group()
    mapGroup.name = 'chinaMapGroup'
    const focusMapGroup = new Group()
    this.focusMapGroup = focusMapGroup

    const { province } = this.createProvince()
    this.provinceMesh = province
    province.setParent(focusMapGroup)

    focusMapGroup.position.set(0, 0, -5)
    focusMapGroup.scale.set(1, 1, 0)

    mapGroup.add(focusMapGroup)
    mapGroup.position.set(0, 0.2, 0)
    this.mainSceneGroup.add(mapGroup)
  }

  createProvince() {
    const mapJsonData = this.assets.instance.getResource('china')
    const topNormal = this.assets.instance.getResource('topNormal')
    topNormal.wrapS = topNormal.wrapT = RepeatWrapping

    this.provinceLineMaterial = new LineBasicMaterial({
      color: 0x2bc4dc, opacity: 0, transparent: true, fog: false
    })

    const [topMaterial, sideMaterial] = this.createProvinceMaterial()
    this.focusMapTopMaterial = topMaterial
    this.focusMapSideMaterial = sideMaterial

    const province = new ExtrudeMap(this, {
      center: this.pointCenter,
      position: new Vector3(0, 0, 0.06),
      data: mapJsonData,
      depth: this.depth,
      topFaceMaterial: topMaterial,
      sideMaterial: sideMaterial,
      lineMaterial: this.provinceLineMaterial,
      renderOrder: 9
    })

    this.time.on('tick', () => { sideMaterial.map.offset.y += 0.002 })

    const { boxSize, box3 } = getBoundBox(province.mapGroup)
    this.eventElement = []
    province.mapGroup.children.forEach(group => {
      group.children.forEach(mesh => {
        if (mesh.type === 'Mesh') {
          this.eventElement.push(mesh)
          this.calcUv2(mesh.geometry, boxSize.x, boxSize.y, box3.min.x, box3.min.y)
        }
      })
    })

    return { province }
  }

  createProvinceMaterial() {
    const topNormal = this.assets.instance.getResource('topNormal')
    topNormal.wrapS = topNormal.wrapT = RepeatWrapping

    const topMaterial = new MeshStandardMaterial({
      color: 0x061e47, emissive: 0x000000,
      map: topNormal, transparent: true, normalMap: topNormal, opacity: 0
    })

    const sideMap = this.assets.instance.getResource('side')
    sideMap.wrapS = sideMap.wrapT = RepeatWrapping
    sideMap.repeat.set(1, 0.2)
    sideMap.offset.y += 0.01

    const sideMaterial = new MeshStandardMaterial({
      color: 0xffffff, map: sideMap, fog: false,
      transparent: true, opacity: 0, side: DoubleSide
    })

    sideMaterial.onBeforeCompile = (shader) => {
      shader.uniforms = {
        ...shader.uniforms,
        uColor1: { value: new Color(0x30b3ff) },
        uColor2: { value: new Color(0x30b3ff) }
      }
      shader.vertexShader = shader.vertexShader.replace(
        'void main() {',
        `attribute float alpha;
        varying vec3 vPosition;
        varying float vAlpha;
        void main() {
          vAlpha = alpha;
          vPosition = position;`
      )
      shader.fragmentShader = shader.fragmentShader.replace(
        'void main() {',
        `varying vec3 vPosition;
        varying float vAlpha;
        uniform vec3 uColor1;
        uniform vec3 uColor2;
        void main() {`
      )
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <opaque_fragment>',
        `#ifdef OPAQUE
        diffuseColor.a = 1.0;
        #endif
        #ifdef USE_TRANSMISSION
        diffuseColor.a *= transmissionAlpha + 0.1;
        #endif
        vec3 gradient = mix(uColor1, uColor2, vPosition.z/1.2);
        outgoingLight = outgoingLight*gradient;
        gl_FragColor = vec4( outgoingLight, diffuseColor.a );`
      )
    }
    return [topMaterial, sideMaterial]
  }

  addEvent() {
    let objectsHover = []
    const reset = (mesh) => {
      gsap.to(mesh.scale, {
        duration: 0.3, z: 1,
        onComplete: () => {
          mesh.traverse(obj => {
            if (obj.isMesh) {
              obj.material[0].emissive.setHex(mesh.userData.materialEmissiveHex)
              obj.material[0].emissiveIntensity = 1
              obj.renderOrder = 9
            }
          })
        }
      })
      this.setBarMove(mesh.userData.adcode, 'down')
      this.setGQMove(mesh.userData.adcode, 'down')
      this.setLabelMove(mesh.userData.adcode, 'down')
    }
    const move = (mesh) => {
      gsap.to(mesh.scale, { duration: 0.3, z: 1.5 })
      this.setBarMove(mesh.userData.adcode)
      this.setGQMove(mesh.userData.adcode)
      this.setLabelMove(mesh.userData.adcode)

      mesh.traverse(obj => {
        if (obj.isMesh) {
          obj.material[0].emissive.setHex(0x0b112d)
          obj.material[0].emissiveIntensity = 1.5
          obj.renderOrder = 21
        }
      })
    }

    this.eventElement.forEach(mesh => {
      this.interactionManager.add(mesh)
      mesh.addEventListener('mouseover', (event) => {
        if (!objectsHover.includes(event.target.parent)) objectsHover.push(event.target.parent)
        if (this.mainSceneGroup.visible) document.body.style.cursor = 'pointer'
        move(event.target.parent)
      })
      mesh.addEventListener('mouseout', (event) => {
        objectsHover = objectsHover.filter(n => n.userData.name !== event.target.parent.userData.name)
        reset(event.target.parent)
        document.body.style.cursor = 'default'
      })
    })
  }

  setBarMove(adcode, type = 'up') {
    if (!this.allBar) return
    this.allBar.forEach(barGroup => {
      if (barGroup.userData.adcode === adcode) {
        gsap.to(barGroup.position, {
          duration: 0.3,
          z: type === 'up' ? barGroup.userData.position[2] + this.depth / 2 + 0.3 : barGroup.userData.position[2]
        })
      }
    })
  }

  setGQMove(adcode, type = 'up') {
    if (!this.allGuangquan) return
    this.allGuangquan.forEach(group => {
      if (group.userData.adcode === adcode) {
        gsap.to(group.position, {
          duration: 0.3,
          z: type === 'up' ? group.userData.position[2] + this.depth / 2 + 0.3 : group.userData.position[2]
        })
      }
    })
    if (this.flyLineFocusGroup && this.flyLineFocusGroup.userData.adcode === adcode) {
      gsap.to(this.flyLineFocusGroup.position, {
        duration: 0.3,
        y: type === 'up'
          ? this.flyLineFocusGroup.userData.position[1] + this.depth / 2 + 0.3
          : this.flyLineFocusGroup.userData.position[1]
      })
    }
  }

  setLabelMove(adcode, type = 'up') {
    const labels = [...(this.allProvinceLabel || []), ...(this.allProvinceNameLabel || [])]
    labels.forEach(label => {
      if (label.userData.adcode === adcode) {
        gsap.to(label.position, {
          duration: 0.3,
          z: type === 'up' ? label.userData.position[2] + this.depth / 2 + 0.3 : label.userData.position[2]
        })
      }
    })
  }


  setLabelVisible(groupName, bool) {
    const g = this[groupName]
    if (!g) return
    g.visible = bool
    g.children.forEach(l => (bool ? l.show?.() : l.hide?.()))
  }

  // ==================== 柱状图（精确到市级，跟随飞线落点） ====================
  createBar(cityList) {
    this._clearBarVisuals()

    if (!cityList || !cityList.length) return

    const self = this
    const data = sortByValue(cityList.map(c => ({
      name: c.name, value: c.count, centroid: c.coord, persons: c.persons || []
    })))
    if (!data.length) return

    const barGroup = new Group()
    this.barGroup = barGroup
    this.barInteractionMeshes = []

    const factor = 7
    const height = 4.0 * factor
    const max = data[0].value || 1

    this.allBar = []
    this.allBarMaterial = []
    this.allGuangquan = []
    this.allProvinceLabel = []
    this.allProvinceNameLabel = []

    data.forEach((item, index) => {
      const geoHeight = Math.max(height * (item.value / max), 0.5)
      const material = new MeshBasicMaterial({
        color: 0xffffff, transparent: true, opacity: 0,
        depthTest: false, fog: false
      })

      new GradientShader(material, {
        uColor1: index < 3 ? 0xfbdf88 : 0x50bbfe,
        uColor2: index < 3 ? 0xfbdf88 : 0x50bbfe,
        size: geoHeight, dir: 'y'
      })

      const geo = new BoxGeometry(0.05 * factor, 0.05 * factor, geoHeight)
      geo.translate(0, 0, geoHeight / 2)
      const mesh = new Mesh(geo, material)
      mesh.renderOrder = 22

      const [x, y] = this.geoProjection(item.centroid)
      mesh.position.set(x, -y, this.depth + 0.46)
      mesh.scale.set(1, 1, 0)
      mesh.userData.name = item.name
      mesh.userData.position = [x, -y, this.depth + 0.46]
      mesh.userData.persons = item.persons
      mesh.userData.count = item.value

      // 光柱悬停交互
      this.interactionManager.add(mesh)
      mesh.addEventListener('mouseover', (ev) => {
        document.body.style.cursor = 'pointer'
        if (this.config.onBarHover) {
          this.config.onBarHover({
            name: item.name, count: item.value, persons: item.persons,
            mouseX: ev.event?.clientX ?? 0, mouseY: ev.event?.clientY ?? 0
          })
        }
      })
      mesh.addEventListener('mouseout', () => {
        document.body.style.cursor = 'default'
        if (this.config.onBarLeave) this.config.onBarLeave()
      })
      this.barInteractionMeshes.push(mesh)

      const guangQuan = this.createQuan()
      guangQuan.position.set(x, -y, this.depth + 0.46)
      guangQuan.userData.name = item.name
      guangQuan.userData.position = [x, -y, this.depth + 0.46]
      this.gqGroup.add(guangQuan)

      const hg = this.createHUIGUANG(geoHeight, index < 3 ? 0xfffef4 : 0x77fbf5)
      mesh.add(...hg)

      barGroup.add(mesh)

      const barLabel = labelStyle04(item, index, new Vector3(x, -y, this.depth + 0.9 + geoHeight))
      const nameLabel = labelNameStyle(item, index, new Vector3(x, -y - 1.5, this.depth + 0.4))

      this.allBar.push(mesh)
      this.allBarMaterial.push(material)
      this.allGuangquan.push(guangQuan)
      this.allProvinceLabel.push(barLabel)
      this.allProvinceNameLabel.push(nameLabel)
    })

    this.mainSceneGroup.add(barGroup)
    this._animateBarEntry()

    function labelStyle04(data, index, position) {
      const label = self.label3d.create('', 'provinces-label-style02', true)
      label.init(
        `<div class="provinces-label-style02 ${index < 3 ? 'yellow' : ''}">
          <div class="provinces-label-style02-wrap">
            <div class="number"><span class="value">${data.value}</span><span class="unit">人</span></div>
            <div class="no">${index + 1}</div>
          </div>
        </div>`,
        position
      )
      self.label3d.setLabelStyle(label, 0.05, 'x')
      label.setParent(self.labelGroup)
      label.userData.position = [position.x, position.y, position.z]
      return label
    }

    function labelNameStyle(data, index, position) {
      const label = self.label3d.create('', 'provinces-name-label', true)
      label.init(
        `<div class="provinces-name-label"><div class="provinces-name-label-wrap">${data.name}</div></div>`,
        position
      )
      self.label3d.setLabelStyle(label, 0.08, 'x')
      label.setParent(self.provinceNameGroup)
      label.userData.position = [position.x, position.y, position.z]
      return label
    }
  }

  _clearBarVisuals() {
    if (this.barInteractionMeshes) {
      this.barInteractionMeshes.forEach(m => this.interactionManager.remove(m))
      this.barInteractionMeshes = []
    }
    if (this.allProvinceLabel) this.allProvinceLabel.forEach(l => l.remove?.())
    if (this.allProvinceNameLabel) this.allProvinceNameLabel.forEach(l => l.remove?.())
    document.querySelectorAll('.provinces-label-style02, .provinces-name-label').forEach(e => e.parentNode?.removeChild(e))

    if (this.barGroup) {
      this.mainSceneGroup.remove(this.barGroup)
      this.barGroup = null
    }
    if (this.allGuangquan) {
      this.allGuangquan.forEach(g => this.gqGroup.remove(g))
    }
    this.allBar = []
    this.allBarMaterial = []
    this.allGuangquan = []
    this.allProvinceLabel = []
    this.allProvinceNameLabel = []
  }

  _animateBarEntry() {
    const tl = gsap.timeline()
    this.allBar.forEach((item, index) => {
      tl.add(gsap.to(item.scale, { duration: 0.8, delay: 0.03 * index, x: 1, y: 1, z: 1, ease: 'circ.out' }), 0)
    })
    this.allBarMaterial.forEach((item, index) => {
      tl.add(gsap.to(item, { duration: 0.5, delay: 0.03 * index, opacity: 1, ease: 'circ.out' }), 0)
    })
    this.allProvinceLabel.forEach((item, index) => {
      const el = item.element?.querySelector('.provinces-label-style02-wrap')
      const num = item.element?.querySelector('.number .value')
      if (el) {
        const numVal = Number(num?.innerText || 0)
        const anim = { score: 0 }
        tl.add(gsap.to(el, { duration: 0.5, delay: 0.03 * index, translateY: 0, opacity: 1, ease: 'circ.out' }), 0)
        if (num) {
          tl.add(gsap.to(anim, { duration: 0.5, delay: 0.03 * index, score: numVal, onUpdate: () => { num.innerText = anim.score.toFixed(0) } }), 0)
        }
      }
    })
    this.allProvinceNameLabel.forEach((item, index) => {
      const el = item.element?.querySelector('.provinces-name-label-wrap')
      if (el) tl.add(gsap.to(el, { duration: 0.5, delay: 0.03 * index, translateY: 0, opacity: 1, ease: 'circ.out' }), 0)
    })
    this.allGuangquan.forEach((item, index) => {
      tl.add(gsap.to(item.children[0].scale, { duration: 0.5, delay: 0.03 * index, x: 1, y: 1, z: 1, ease: 'circ.out' }), 0)
      tl.add(gsap.to(item.children[1].scale, { duration: 0.5, delay: 0.03 * index, x: 1, y: 1, z: 1, ease: 'circ.out' }), 0)
    })
  }

  createHUIGUANG(h, color) {
    const geometry = new PlaneGeometry(1.5, h)
    geometry.translate(0, h / 2, 0)
    const texture = this.assets.instance.getResource('huiguang')
    texture.colorSpace = SRGBColorSpace
    texture.wrapS = texture.wrapT = RepeatWrapping
    const material = new MeshBasicMaterial({
      color: color, map: texture, transparent: true, opacity: 0.4,
      depthWrite: false, side: DoubleSide, blending: AdditiveBlending
    })
    const mesh = new Mesh(geometry, material)
    mesh.renderOrder = 23
    mesh.rotateX(Math.PI / 2)
    const mesh2 = mesh.clone()
    const mesh3 = mesh.clone()
    mesh2.rotateY((Math.PI / 180) * 60)
    mesh3.rotateY((Math.PI / 180) * 120)
    return [mesh, mesh2, mesh3]
  }

  createQuan() {
    const guangquan1 = this.assets.instance.getResource('guangquan1')
    const guangquan2 = this.assets.instance.getResource('guangquan2')
    const geometry = new PlaneGeometry(2, 2)

    const material1 = new MeshBasicMaterial({
      color: 0xffffff, map: guangquan1, alphaMap: guangquan1, opacity: 1,
      transparent: true, depthTest: false, fog: false, blending: AdditiveBlending
    })
    const material2 = new MeshBasicMaterial({
      color: 0xffffff, map: guangquan2, alphaMap: guangquan2, opacity: 1,
      transparent: true, depthTest: false, fog: false, blending: AdditiveBlending
    })
    const mesh1 = new Mesh(geometry, material1)
    const mesh2 = new Mesh(geometry, material2)
    mesh1.renderOrder = mesh2.renderOrder = 24
    mesh2.position.z -= 0.001
    mesh1.scale.set(0, 0, 0)
    mesh2.scale.set(0, 0, 0)

    const quanGroup = new Group()
    quanGroup.add(mesh1, mesh2)
    this.time.on('tick', (delta) => { mesh1.rotation.z += delta * 2 })
    return quanGroup
  }

  // ==================== 飞线（真实公出数据，精确到市级） ====================
  createFlyLine(tripBarData, cityList = []) {
    this._clearFlyLineVisuals()

    if ((!tripBarData || !tripBarData.length) && (!cityList || !cityList.length)) return

    const coords = this.provinceMesh.getCoordinates()
    let flyData = []

    if (cityList && cityList.length) {
      // 每个城市一条飞线，坐标精确到市级
      flyData = cityList.map(c => ({ name: c.name, centroid: c.coord, value: c.count }))
    } else if (tripBarData && tripBarData.length) {
      // 无城市数据时回退到省级质心
      flyData = tripBarData.map(prov => {
        const match = coords.find(c => c.name === prov.name)
        return match ? { name: prov.name, centroid: match.centroid, value: prov.value } : null
      }).filter(Boolean)
    }

    if (!flyData.length) return

    const texture = this.assets.instance.getResource('flyLine')
    texture.wrapS = texture.wrapT = RepeatWrapping
    texture.generateMipmaps = false
    texture.magFilter = NearestFilter
    texture.repeat.set(0.5, 1)

    const flyLine = new FlyLine(this, {
      centerPoint: this.flyLineCenter,
      data: flyData,
      texture: texture,
      material: new MeshBasicMaterial({
        map: texture, alphaMap: texture, color: 0xfbdf88,
        transparent: true, fog: false, depthTest: false, blending: AdditiveBlending
      })
    })
    flyLine.setParent(this.mainSceneGroup)
    flyLine.instance.position.z = this.depth + 0.4
    this.flyLineGroup = flyLine

    this.createFlyLineFocus()
  }

  _clearFlyLineVisuals() {
    if (this.flyLineGroup) {
      this.flyLineGroup.instance?.parent?.remove(this.flyLineGroup.instance)
      this.flyLineGroup = null
    }
    if (this.flyLineFocusGroup) {
      this.flyLineFocusGroup.parent?.remove(this.flyLineFocusGroup)
      this.flyLineFocusGroup = null
    }
  }

  createFlyLineFocus() {
    this.flyLineFocusGroup = new Group()
    this.flyLineFocusGroup.visible = false

    const [x, y] = this.geoProjection(this.flyLineCenter)
    this.flyLineFocusGroup.position.set(x, -y, this.depth + 0.47)
    this.flyLineFocusGroup.userData.name = '黑龙江省'
    this.flyLineFocusGroup.userData.adcode = 230000
    this.flyLineFocusGroup.userData.position = [x, -y, this.depth + 0.47]
    this.mainSceneGroup.add(this.flyLineFocusGroup)

    const flyLineFocus = this.assets.instance.getResource('guangquan1')
    const geometry = new PlaneGeometry(5, 5)
    const material = new MeshBasicMaterial({
      color: 0xfbdf88, map: flyLineFocus, alphaMap: flyLineFocus,
      transparent: true, fog: false, depthTest: false, blending: AdditiveBlending
    })
    const mesh = new Mesh(geometry, material)
    mesh.renderOrder = 30
    mesh.scale.set(0, 0, 0)
    const mesh2 = mesh.clone()
    mesh2.material = material.clone()
    this.flyLineFocusGroup.add(mesh, mesh2)

    gsap.to(mesh.material, { opacity: 0, repeat: -1, yoyo: false, duration: 1 })
    gsap.to(mesh.scale, { x: 2, y: 2, z: 2, repeat: -1, yoyo: false, duration: 1 })
    gsap.to(mesh2.material, { delay: 0.5, opacity: 0, repeat: -1, yoyo: false, duration: 1 })
    gsap.to(mesh2.scale, { delay: 0.5, x: 2, y: 2, z: 2, repeat: -1, yoyo: false, duration: 1 })
  }

  // ==================== 装饰效果 ====================
  createFloor() {
    const geo = new PlaneGeometry(200, 200)
    const tex = this.assets.instance.getResource('gaoguang1')
    tex.colorSpace = SRGBColorSpace
    tex.wrapS = tex.wrapT = RepeatWrapping
    const mesh = new Mesh(geo, new MeshBasicMaterial({
      map: tex, opacity: 1, transparent: true, blending: AdditiveBlending
    }))
    mesh.rotateX(-Math.PI / 2)
    mesh.position.set(0, 0.05, 0)
    this.scene.add(mesh)

    const quanTex = this.assets.instance.getResource('quan')
    const quan = new Mesh(
      new PlaneGeometry(250, 250),
      new MeshBasicMaterial({
        map: quanTex, transparent: true, blending: AdditiveBlending, depthTest: false
      })
    )
    quan.rotateX(-Math.PI / 2)
    quan.position.set(0, this.depth + 2.05, 0)
    this.quan = quan
    this.scene.add(quan)
  }

  createRotateBorder() {
    const max = 100
    const rb1 = this.assets.instance.getResource('rotationBorder1')
    const rb2 = this.assets.instance.getResource('rotationBorder2')

    const p1 = new Plane(this, {
      width: max * 1.178, needRotate: true, rotateSpeed: 0.001,
      material: new MeshBasicMaterial({
        map: rb1, color: 0x48afff, transparent: true, opacity: 0.2,
        depthWrite: false, blending: AdditiveBlending
      }),
      position: new Vector3(0, 0.07, 0)
    })
    p1.instance.renderOrder = 6
    p1.instance.scale.set(0, 0, 0)
    p1.setParent(this.scene)

    const p2 = new Plane(this, {
      width: max * 1.116, needRotate: true, rotateSpeed: -0.004,
      material: new MeshBasicMaterial({
        map: rb2, color: 0x48afff, transparent: true, opacity: 0.4,
        depthWrite: false, blending: AdditiveBlending
      }),
      position: new Vector3(0, 0.06, 0)
    })
    p2.instance.renderOrder = 6
    p2.instance.scale.set(0, 0, 0)
    p2.setParent(this.scene)

    this.rotateBorder1 = p1.instance
    this.rotateBorder2 = p2.instance
  }

  createParticles() {
    this.particles = new Particles(this, {
      num: 10, range: 200, dir: 'up', speed: 0.1,
      material: new PointsMaterial({
        map: Particles.createTexture(), size: 10, color: 0x00eeee,
        transparent: true, opacity: 0.3, depthTest: false, depthWrite: false,
        vertexColors: true, blending: AdditiveBlending, sizeAttenuation: true
      })
    })
    this.particles.instance.position.set(0, 0, 0)
    this.particles.instance.rotation.x = -Math.PI / 2
    this.particles.setParent(this.scene)
    this.particles.enable = false
    this.particles.instance.visible = false
  }

  createGridRipple() {
    const tex = this.assets.instance.getResource('grid')
    const alpha = this.assets.instance.getResource('gridBlack')
    tex.wrapS = tex.wrapT = alpha.wrapS = alpha.wrapT = RepeatWrapping
    tex.repeat.set(40, 40)
    alpha.repeat.set(40, 40)

    const mat = new MeshBasicMaterial({
      map: tex, color: 0x00ffff, transparent: true, opacity: 0.5,
      alphaMap: alpha, blending: AdditiveBlending
    })
    const geo = new PlaneGeometry(300, 300)
    const mesh = new Mesh(geo, mat)
    mesh.rotateX(-Math.PI / 2)
    const [x, y] = this.geoProjection(this.pointCenter)
    mesh.position.set(x, -y, 0.01)

    const mesh2 = mesh.clone()
    mesh2.material = mat.clone()
    mesh2.material.opacity = 0.1
    this.scene.add(mesh, mesh2)

    new DiffuseShader({
      material: mat, time: this.time, size: 300,
      diffuseColor: 0x079fe6, diffuseSpeed: 30, diffuseWidth: 20, diffuseDir: 2.0
    })
  }

  createMirror() {
    const geo = new PlaneGeometry(200, 200)
    const gm = new Reflector(geo, {
      clipBias: 0.003, textureWidth: this.sizes.width, textureHeight: this.sizes.height,
      color: 0xb5b5b5, multisample: 1
    })
    gm.material.transparent = true
    gm.material.opacity = 0.2
    gm.position.y = -0.01
    gm.rotateX(-Math.PI / 2)
    this.groundMirror = gm
    this.groundMirror.visible = true
    this.scene.add(gm)
  }

  createStorke() {
    const tex = this.assets.instance.getResource('pathLine2')
    tex.wrapS = tex.wrapT = RepeatWrapping
    tex.repeat.set(1, 1)

    let data = this.assets.instance.getResource('chinaStorke')
    data = JSON.parse(data)
    const paths = data.features.map(f => ({ geometry: f.geometry }))

    const pl = new PathLine(this, {
      data: paths, texture: tex, renderOrder: 21, speed: 0.2,
      radius: 0.2, segments: 256 * 10, radialSegments: 4,
      material: new MeshBasicMaterial({
        color: 0x2bc4dc, map: tex, alphaMap: tex, fog: false,
        transparent: true, opacity: 1, blending: AdditiveBlending
      })
    })
    pl.setParent(this.mainSceneGroup)
    pl.instance.position.z = this.depth + 0.38
  }

  // ==================== 入场动画 ====================
  runEntryAnimation() {
    const tl = gsap.timeline()

    tl.addLabel('focusMap', 3.5)
    tl.addLabel('focusMapOpacity', 4.0)

    tl.add(gsap.to(this.camera.instance.position, {
      duration: 2.5, delay: 2,
      x: 3.134497983573052,
      y: 126.8312346165316,
      z: 78.77649752477839,
      ease: 'circ.out',
      onComplete: () => this.camera.controls.saveState()
    }))

    tl.add(gsap.to(this.quan.rotation, { duration: 5, z: -2 * Math.PI }), '-=2')

    tl.add(gsap.to(this.focusMapGroup.position, { duration: 1, x: 0, y: 0, z: 0 }), 'focusMap')
    tl.add(gsap.to(this.focusMapGroup.scale, {
      duration: 1, x: 1, y: 1, z: 1, ease: 'circ.out'
    }), 'focusMap')

    this.provinceMesh.mapGroup.traverse(obj => {
      if (obj.isMesh) {
        tl.add(gsap.to(obj.material[0], { duration: 1, opacity: 1, ease: 'circ.out' }), 'focusMapOpacity')
        tl.add(gsap.to(obj.position, { duration: 1, x: 0, y: 0, z: 0, ease: 'circ.out' }), 'focusMapOpacity')
      }
    })

    tl.add(gsap.to(this.focusMapSideMaterial, {
      duration: 1, opacity: 1, ease: 'circ.out',
      onComplete: () => { this.createMirror(); this.createGridRipple() }
    }), 'focusMapOpacity')

    tl.add(gsap.to(this.provinceLineMaterial, { duration: 0.5, delay: 0.3, opacity: 1 }), 'focusMapOpacity')

    tl.add(gsap.to(this.rotateBorder1.scale, {
      delay: 0.3, duration: 1, x: 1, y: 1, z: 1, ease: 'circ.out'
    }), 'focusMapOpacity')
    tl.add(gsap.to(this.rotateBorder2.scale, {
      duration: 1, delay: 0.5, x: 1, y: 1, z: 1, ease: 'circ.out'
    }), 'focusMapOpacity')
  }

  // ==================== 公出数据可视化 ====================
  setTripData(tripTree = [], cityList = []) {
    this.tripData = tripTree
    this._clearTripVisuals()

    this.createBar(cityList)
    this.createFlyLine(tripTree.map(p => ({ name: p.name, value: p.count })), cityList)
  }

  _clearTripVisuals() {
    // 旧 trip 标签清理（兼容）
    document.querySelectorAll('.trip-label').forEach(e => e.parentNode?.removeChild(e))
  }

  calcUv2(geometry, width, height, minX, minY) {
    const pos = geometry.attributes.position
    const uv = geometry.attributes.uv
    const count = geometry.groups[0].count
    for (let i = 0; i < count; i++) {
      uv.setXY(i, (pos.getX(i) - minX) / width, (pos.getY(i) - minY) / height)
    }
    uv.needsUpdate = true
    geometry.computeVertexNormals()
  }

  update() {
    super.update()
    this.interactionManager && this.interactionManager.update()
  }

  destroy() {
    this._clearTripVisuals()
    this._clearBarVisuals()
    this._clearFlyLineVisuals()
    super.destroy()
    this.label3d && this.label3d.destroy()
    this.groundMirror && this.groundMirror.dispose()
  }
}
