<script setup>
import { reactive, ref } from 'vue'
import { useToast } from 'vue-toastification'
import { authAPI } from '@/services/api'
const toast = useToast()

const form = reactive({
  email: '',
  password: '',
})

const isLoading = ref(false)

const handleLogin = async () => {
  isLoading.value = true

  try {
    await authAPI.login(form.email, form.password)
    localStorage.setItem('userEmail', form.email)
    toast.success('Login successful!')

    window.location.href = '/quizzes'
  } catch (error) {
    console.error('Login error:', error)
    if (error.response?.status === 401) {
      toast.error('Invalid email or password')
    } else {
      toast.error('Login failed. Please try again.')
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <section class="bg-blue-50 min-h-screen flex items-center justify-center">
    <div class="container max-w-md">
      <div class="bg-white rounded-lg shadow-lg p-8">
        <!-- Header -->
        <div class="text-center mb-8">
          <h1 class="text-3xl font-bold text-gray-800 mb-2">Welcome Back</h1>
          <p class="text-gray-600">Login to your account to continue</p>
        </div>

        <!-- Login Form -->
        <form @submit.prevent="handleLogin">
          <!-- Email Field -->
          <div class="mb-4">
            <label for="email" class="block text-gray-700 font-semibold mb-2">
              Email Address
            </label>
            <input
              v-model="form.email"
              type="email"
              id="email"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-purple-500"
              placeholder="you@example.com"
              :disabled="isLoading"
              required
            />
          </div>

          <!-- Password Field -->
          <div class="mb-6">
            <label for="password" class="block text-gray-700 font-semibold mb-2"> Password </label>
            <input
              v-model="form.password"
              type="password"
              id="password"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-purple-500"
              placeholder="••••••••"
              :disabled="isLoading"
              required
            />
          </div>

          <!-- Login Button -->
          <button
            type="submit"
            :disabled="isLoading"
            class="w-full bg-purple-500 hover:bg-purple-600 disabled:bg-gray-400 text-white font-bold py-3 px-4 rounded-lg transition duration-200"
          >
            <span v-if="isLoading" class="flex items-center justify-center">
              <svg
                class="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                fill="none"
                viewBox="0 0 24 24"
              >
                <circle
                  class="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  stroke-width="4"
                ></circle>
                <path
                  class="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                ></path>
              </svg>
              Logging in...
            </span>
            <span v-else>Login</span>
          </button>
        </form>

        <!-- Divider -->
        <div class="my-6 flex items-center">
          <div class="flex-1 border-t border-gray-300"></div>
          <span class="px-4 text-sm text-gray-500">OR</span>
          <div class="flex-1 border-t border-gray-300"></div>
        </div>

        <!-- Sign Up Link -->
        <div class="text-center">
          <p class="text-gray-600">
            Don't have an account?
            <RouterLink to="/signup" class="text-purple-500 hover:text-purple-700 font-semibold">
              Sign Up
            </RouterLink>
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
