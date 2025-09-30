<script setup>
import { RouterLink } from 'vue-router'
import JobListing from '@/components/QuizCard.vue'
import { reactive, defineProps, onMounted } from 'vue'
import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
import axios from 'axios'

defineProps({
  limit: Number,
  showButton: {
    type: Boolean,
    default: false,
  },
})

const state = reactive({
  quizzes: [],
  isLoading: true,
})

onMounted(async () => {
  try {
    const response = await axios.get('/api/quizzes')
    state.quizzes = response.data
  } catch (error) {
    console.error('Error fetching quizzes', error)
  } finally {
    state.isLoading = false
  }
})
</script>

<template>
  <section class="bg-purple-50 px-4 py-10">
    <div class="container-xl lg:container m-auto">
      <h2 class="text-3xl font-bold text-purple-500 mb-6 text-center">Browse Quizzes</h2>
      <!-- Show loading spinner while loading is true -->
      <div v-if="state.isLoading" class="text-center text-gray-500 py-6">
        <PulseLoader />
      </div>

      <!-- Show quiz listing when done loading-->
      <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <JobListing
          v-for="quizItem in state.quizzes.slice(0, limit || state.quizzes.length)"
          :key="quizItem.Quiz.id"
          :quiz="quizItem.Quiz"
        />
      </div>
    </div>
  </section>

  <section v-id="showButton" class="m-auto max-w-lg my-10 px-6">
    <RouterLink
      to="/quizzes"
      class="block bg-purple-900 text-white text-center py-4 px-6 rounded-xl hover:bg-gray-700"
      >View All Quizzes</RouterLink
    >
  </section>
</template>
