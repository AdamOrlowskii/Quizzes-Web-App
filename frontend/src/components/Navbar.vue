<!-- eslint-disable vue/multi-word-component-names -->
<script setup>
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { ref, onMounted } from 'vue'
import { authAPI } from '@/services/api'
import { useToast } from 'vue-toastification'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const isLoggedIn = ref(false)

const isActiveLink = routePath => {
  return route.path === routePath
}

const isAdmin = ref(false)

const checkAuth = () => {
  isLoggedIn.value = !!localStorage.getItem('token')
  isAdmin.value = localStorage.getItem('isAdmin') === 'true'
}

const handleLogout = () => {
  authAPI.logout()
  isLoggedIn.value = false
  toast.success('Logged out successfully')
  router.push('/')
}

onMounted(() => {
  checkAuth()
})

window.addEventListener('storage', checkAuth)
</script>

<template>
  <nav class="bg-purple-800 border-b border-purple-800">
    <div class="mx-auto max-w-7xl px-2 sm:px-6 lg:px-8">
      <div class="flex h-20 items-center justify-between">
        <div class="flex flex-1 items-center justify-center md:items-stretch md:justify-start">
          <!-- Logo -->
          <RouterLink class="flex flex-shrink-0 items-center mr-4" to="/">
            <span class="hidden md:block text-white text-2xl font-bold ml-2">Quiz App</span>
          </RouterLink>

          <div class="md:ml-auto">
            <div class="flex space-x-2">
              <RouterLink
                v-if="isAdmin"
                to="/admin"
                :class="[
                  isActiveLink('/admin') ? 'bg-purple-900' : 'hover:bg-purple-900 hover:text-white',
                  'text-white px-3 py-2 rounded-md',
                ]"
              >
                Administrators Panel
              </RouterLink>

              <RouterLink
                to="/"
                :class="[
                  isActiveLink('/') ? 'bg-purple-900' : 'hover:bg-purple-900 hover:text-white',
                  'text-white px-3 py-2 rounded-md',
                ]"
              >
                Home
              </RouterLink>

              <RouterLink
                to="/quizzes"
                :class="[
                  isActiveLink('/quizzes')
                    ? 'bg-purple-900'
                    : 'hover:bg-purple-900 hover:text-white',
                  'text-white px-3 py-2 rounded-md',
                ]"
              >
                Public Quizzes
              </RouterLink>

              <template v-if="isLoggedIn">
                <RouterLink
                  to="/quizzes/my_quizzes"
                  :class="[
                    isActiveLink('/quizzes/my_quizzes')
                      ? 'bg-purple-900'
                      : 'hover:bg-purple-900 hover:text-white',
                    'text-white px-3 py-2 rounded-md',
                  ]"
                >
                  My Quizzes
                </RouterLink>

                <RouterLink
                  to="/quizzes/my_favourite_quizzes"
                  :class="[
                    isActiveLink('/quizzes/my_favourite_quizzes')
                      ? 'bg-purple-900'
                      : 'hover:bg-purple-900 hover:text-white',
                    'text-white px-3 py-2 rounded-md',
                  ]"
                >
                  My favourites
                </RouterLink>

                <RouterLink
                  to="/quizzes/add"
                  :class="[
                    isActiveLink('/quizzes/add')
                      ? 'bg-purple-900'
                      : 'hover:bg-purple-900 hover:text-white',
                    'text-white px-3 py-2 rounded-md',
                  ]"
                >
                  Add Quiz
                </RouterLink>

                <button
                  @click="handleLogout"
                  class="text-white hover:bg-purple-900 hover:text-white px-3 py-2 rounded-md"
                >
                  Logout
                </button>
              </template>

              <template v-else>
                <RouterLink
                  to="/login"
                  :class="[
                    isActiveLink('/login')
                      ? 'bg-purple-900'
                      : 'hover:bg-purple-900 hover:text-white',
                    'text-white px-3 py-2 rounded-md',
                  ]"
                >
                  Log In
                </RouterLink>

                <RouterLink
                  to="/signup"
                  :class="[
                    isActiveLink('/signup')
                      ? 'bg-purple-900'
                      : 'hover:bg-purple-900 hover:text-white',
                    'text-white px-3 py-2 rounded-md',
                  ]"
                >
                  Sign Up
                </RouterLink>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>
  </nav>
</template>
