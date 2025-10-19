<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import { authAPI } from '@/services/api' // ✅ Zmienione

const router = useRouter()
const toast = useToast()

const form = reactive({
  email: '',
  password: '',
  confirmPassword: '',
})

const isLoading = ref(false)

const handleSignUp = async () => {
  // Validate passwords match
  if (form.password !== form.confirmPassword) {
    toast.error('Passwords do not match')
    return
  }

  // Validate password strength (optional)
  if (form.password.length < 6) {
    toast.error('Password must be at least 6 characters')
    return
  }

  isLoading.value = true

  try {
    // ✅ Zmienione - użycie authAPI
    await authAPI.register(form.email, form.password)

    toast.success('Account created successfully! Please login.')
    router.push('/login')
  } catch (error) {
    console.error('Sign up error:', error)
    if (error.response?.status === 400) {
      toast.error(error.response.data.detail || 'Email already exists')
    } else {
      toast.error('Sign up failed. Please try again.')
    }
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <section class="bg-purple-50 min-h-screen flex items-center justify-center">
    <div class="container max-w-md">
      <div class="bg-white rounded-lg shadow-lg p-8">
        <!-- Header -->
        <div class="text-center mb-8">
          <h1 class="text-3xl font-bold text-gray-800 mb-2">Create Account</h1>
          <p class="text-gray-600">Sign up to start creating quizzes</p>
        </div>

        <!-- Sign Up Form -->
        <form @submit.prevent="handleSignUp">
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
            <p class="text-xs text-gray-500 mt-1">We'll never share your email with anyone else.</p>
          </div>

          <!-- Password Field -->
          <div class="mb-4">
            <label for="password" class="block text-gray-700 font-semibold mb-2"> Password </label>
            <input
              v-model="form.password"
              type="password"
              id="password"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-purple-500"
              placeholder="••••••••"
              :disabled="isLoading"
              required
              minlength="6"
            />
            <p class="text-xs text-gray-500 mt-1">Minimum 6 characters</p>
          </div>

          <!-- Confirm Password Field -->
          <div class="mb-6">
            <label for="confirmPassword" class="block text-gray-700 font-semibold mb-2">
              Confirm Password
            </label>
            <input
              v-model="form.confirmPassword"
              type="password"
              id="confirmPassword"
              class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:border-purple-500"
              placeholder="••••••••"
              :disabled="isLoading"
              required
            />
          </div>

          <!-- Terms & Conditions -->
          <div class="mb-6">
            <label class="flex items-start">
              <input type="checkbox" class="mt-1 mr-2" required />
              <span class="text-sm text-gray-600">
                I agree to the
                <a href="#" class="text-purple-500 hover:text-purple-700">Terms and Conditions</a>
                and
                <a href="#" class="text-purple-500 hover:text-purple-700">Privacy Policy</a>
              </span>
            </label>
          </div>

          <!-- Sign Up Button -->
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
              Creating account...
            </span>
            <span v-else>Sign Up</span>
          </button>
        </form>

        <!-- Divider -->
        <div class="my-6 flex items-center">
          <div class="flex-1 border-t border-gray-300"></div>
          <span class="px-4 text-sm text-gray-500">OR</span>
          <div class="flex-1 border-t border-gray-300"></div>
        </div>

        <!-- Login Link -->
        <div class="text-center">
          <p class="text-gray-600">
            Already have an account?
            <RouterLink to="/login" class="text-purple-500 hover:text-purple-700 font-semibold">
              Login
            </RouterLink>
          </p>
        </div>
      </div>
    </div>
  </section>
</template>
