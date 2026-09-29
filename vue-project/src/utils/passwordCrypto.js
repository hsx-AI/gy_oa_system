/**
 * Encrypt passwords with server RSA-OAEP public key before HTTP transfer.
 * Uses node-forge so it works on plain HTTP (Web Crypto subtle needs HTTPS/localhost).
 */
import forge from 'node-forge'
import request from '@/utils/request'

let cachedKey = null
let loadingPromise = null

async function fetchPublicKey(force = false) {
  if (!force && cachedKey?.publicKeyPem) return cachedKey
  if (!force && loadingPromise) return loadingPromise
  loadingPromise = request({ url: '/auth/public-key', method: 'get' })
    .then((res) => {
      if (!res?.publicKeyPem) throw new Error(res?.message || '��ȡ���ܹ�Կʧ��')
      cachedKey = {
        publicKeyPem: res.publicKeyPem,
        keyId: res.keyId || '',
      }
      return cachedKey
    })
    .finally(() => {
      loadingPromise = null
    })
  return loadingPromise
}

function encryptWithPem(publicKeyPem, text) {
  const publicKey = forge.pki.publicKeyFromPem(publicKeyPem)
  const encrypted = publicKey.encrypt(String(text ?? ''), 'RSA-OAEP', {
    md: forge.md.sha256.create(),
    mgf1: { md: forge.md.sha256.create() },
  })
  return forge.util.encode64(encrypted)
}

/** @returns {Promise<{ passwordCipher: string, keyId: string }>} */
export async function encryptPasswordForTransport(password) {
  const first = await fetchPublicKey(false)
  try {
    const passwordCipher = encryptWithPem(first.publicKeyPem, password)
    return { passwordCipher, keyId: first.keyId }
  } catch (e) {
    // key rotated mid-flight
    const second = await fetchPublicKey(true)
    const passwordCipher = encryptWithPem(second.publicKeyPem, password)
    return { passwordCipher, keyId: second.keyId }
  }
}
