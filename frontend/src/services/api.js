const API = 'http://127.0.0.1:8000/api'
async function request(path, options = {}) {
  const res = await fetch(`${API}${path}`, { headers: { 'Content-Type': 'application/json', ...(options.headers || {}) }, ...options })
  if (!res.ok) { const text = await res.text(); throw new Error(text || `HTTP ${res.status}`) }
  return res.json()
}
export const api = {
  health: () => request('/health'), dashboard: () => request('/dashboard'), products: () => request('/products'), orders: () => request('/orders'), tasks: () => request('/tasks'), exceptions: () => request('/exceptions'), analytics: () => request('/analytics'),
  createProduct: (body) => request('/products', { method:'POST', body: JSON.stringify(body) }),
  createOrder: (body) => request('/orders', { method:'POST', body: JSON.stringify(body) }),
  allocate: (id) => request(`/orders/${id}/allocate`, { method:'POST' }),
  updateTask: (id, status) => request(`/tasks/${id}?status=${encodeURIComponent(status)}`, { method:'PATCH' }),
  resolveException: (id) => request(`/exceptions/${id}/resolve`, { method:'PATCH' }),
  damage: (id, quantity, reason) => request(`/products/${id}/damage`, { method:'POST', body: JSON.stringify({ quantity, reason }) }),
}
