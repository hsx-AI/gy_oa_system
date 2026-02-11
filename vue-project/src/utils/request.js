import axios from 'axios'

// 创建 axios 实例
const request = axios.create({
  baseURL: '/api', // 通过 Vite 代理转发到后端
  timeout: 10000,
  withCredentials: true,  // 重要！允许跨域请求携带 Cookie
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    // FormData 提交时不要设置 Content-Type，让浏览器自动带上 multipart boundary
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    const res = response.data
    
    // 假设返回 { success: true, data: ... }
    if (res.success === false) {
      console.error('业务错误:', res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    
    return res
  },
  error => {
    console.error('响应错误:', error.message)
    
    // 处理不同的 HTTP 错误状态
    if (error.response) {
      switch (error.response.status) {
        case 401:
          console.error('未授权，请重新登录')
          // 可以在这里跳转到登录页
          break
        case 403:
          console.error('拒绝访问')
          break
        case 404:
          console.error('请求的资源不存在')
          break
        case 500:
          console.error('服务器内部错误')
          break
        default:
          console.error(`连接错误${error.response.status}`)
      }
    } else {
      console.error('网络连接失败，请检查网络')
    }
    
    return Promise.reject(error)
  }
)

export default request




