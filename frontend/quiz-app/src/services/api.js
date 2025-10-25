// src/services/api.js
import axios from 'axios'

// Użyj /api - proxy w Vite przekieruje na backend
const API_URL = '/api'

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Automatyczne dodawanie tokena
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Obsługa wygasłego tokena
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ===== AUTH =====
export const authAPI = {
  register: (email, password) => api.post('/users/', { email, password }),

  login: async (email, password) => {
    const formData = new FormData()
    formData.append('username', email)
    formData.append('password', password)

    const response = await api.post('/login', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    if (response.data.access_token) {
      localStorage.setItem('token', response.data.access_token)
    }

    return response
  },

  logout: () => {
    localStorage.removeItem('token')
  },

  deleteAccount: () => api.delete('/users/delete_account'),
}

// ===== QUIZZES =====
export const quizAPI = {
  getAll: (limit = 100, skip = 0, search = '') =>
    api.get('/quizzes', { params: { limit, skip, search } }),

  getMyQuizzes: (limit = 100, skip = 0, search = '') =>
    api.get('/quizzes/my_quizzes', { params: { limit, skip, search } }),

  getMyFavouriteQuizzes: (limit = 100, skip = 0, search = '') =>
    api.get('/quizzes/my_favourite_quizzes', { params: { limit, skip, search } }),

  getById: id => api.get(`/quizzes/${id}`),

  getQuestions: id => api.get(`/quizzes/play/${id}`),

  create: async (file, title, published = true) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', title)
    formData.append('published', published)

    return api.post('/quizzes', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  update: (id, data) => api.put(`/quizzes/${id}`, data),

  updateQuestions: (id, questions) => api.put(`/quizzes/${id}/questions`, questions),

  delete: id => api.delete(`/quizzes/${id}`),
}

// ===== FAVOURITES =====
export const favouriteAPI = {
  add: quizId => api.post('/quizzes/favourites', { quiz_id: quizId, dir: 1 }),

  remove: quizId => api.post('/quizzes/favourites', { quiz_id: quizId, dir: 0 }),

  getMyFavourites: (limit = 100, skip = 0, search = '') =>
    api.get('/quizzes/my_favourite_quizzes', { params: { limit, skip, search } }),
}

// ===== USERS =====
export const userAPI = {
  getById: id => api.get(`/users/${id}`),

  getMe: () => api.get('/users/me'),
}

export default api
