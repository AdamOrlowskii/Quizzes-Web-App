<!-- eslint-disable vue/multi-word-component-names -->
<script setup>
import { RouterLink, useRoute } from 'vue-router'

const isActiveLink = routePath => {
  const route = useRoute()
  return route.path === routePath
}
</script>

<template>
  <nav class="bg-purple-700 border-b border-purple-500">
    <div class="mx-auto max-w-7xl px-2 sm:px-6 lg:px-8">
      <div class="flex h-20 items-center justify-between">
        <div class="flex flex-1 items-center justify-center md:items-stretch md:justify-start">
          <!-- Logo -->
          <RouterLink class="flex flex-shrink-0 items-center mr-4" to="/">
            <span class="hidden md:block text-white text-2xl font-bold ml-2">Quizzes App</span>
          </RouterLink>
          <div class="md:ml-auto">
            <div class="flex space-x-2">
              <RouterLink
                to="/"
                :class="[
                  isActiveLink('/') ? 'bg-purple-900' : 'hover:bg-gray-900 hover:text-white',
                  'text-white',
                  'px-3',
                  'py-2',
                  'rounded-md',
                ]"
                >Home</RouterLink
              >
              <RouterLink
                to="/quizzes"
                :class="[
                  isActiveLink('/quizzes') ? 'bg-purple-900' : 'hover:bg-gray-900 hover:text-white',
                  'text-white',
                  'px-3',
                  'py-2',
                  'rounded-md',
                ]"
                >Quizzes</RouterLink
              >
              <RouterLink
                to="/quizzes/my_quizzes"
                :class="[
                  isActiveLink('/quizzes/my_quizzes')
                    ? 'bg-purple-900'
                    : 'hover:bg-gray-900 hover:text-white',
                  'text-white',
                  'px-3',
                  'py-2',
                  'rounded-md',
                ]"
                >My Quizzes</RouterLink
              >
              <RouterLink
                to="/quizzes/add"
                :class="[
                  isActiveLink('/quizzes/add')
                    ? 'bg-purple-900'
                    : 'hover:bg-gray-900 hover:text-white',
                  'text-white',
                  'px-3',
                  'py-2',
                  'rounded-md',
                ]"
                >Add Quiz</RouterLink
              >
              <RouterLink
                to="/login"
                :class="[
                  isActiveLink('/login') ? 'bg-purple-900' : 'hover:bg-gray-900 hover:text-white',
                  'text-white',
                  'px-3',
                  'py-2',
                  'rounded-md',
                ]"
                >Login</RouterLink
              >
              <RouterLink
                to="/signup"
                :class="[
                  isActiveLink('/users') ? 'bg-purple-900' : 'hover:bg-gray-900 hover:text-white',
                  'text-white',
                  'px-3',
                  'py-2',
                  'rounded-md',
                ]"
                >Sign Up</RouterLink
              >
            </div>
          </div>
        </div>
      </div>
    </div>
  </nav>
</template>
