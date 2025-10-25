<script setup>
import { RouterLink, useRoute } from 'vue-router'
import QuizCard from '@/components/QuizCard.vue'
import { reactive, defineProps, onMounted, watch, computed } from 'vue'
import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
import { quizAPI } from '@/services/api'

const route = useRoute()

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

const pageTitle = computed(() => {
  if (route.path === '/quizzes/my_quizzes') return 'My Quizzes'
  if (route.path === '/quizzes/my_favourite_quizzes') return 'My Favourite Quizzes'
  return 'Browse Quizzes'
})

const fetchQuizzes = async () => {
  state.isLoading = true

  try {
    let response

    if (route.path === '/quizzes/my_quizzes') {
      response = await quizAPI.getMyQuizzes()
    } else if (route.path === '/quizzes/my_favourite_quizzes') {
      response = await quizAPI.getMyFavouriteQuizzes()
    } else {
      response = await quizAPI.getAll()
    }

    console.log('Quizzes loaded:', response.data)
    state.quizzes = response.data
  } catch (error) {
    console.error('Error fetching quizzes', error)
  } finally {
    state.isLoading = false
  }
}

onMounted(() => {
  fetchQuizzes()
})

watch(
  () => route.path,
  () => {
    fetchQuizzes()
  }
)
</script>

<template>
  <section class="bg-purple-50 px-4 py-10">
    <div class="container-xl lg:container m-auto">
      <!-- ✅ Użyj computed pageTitle -->
      <h2 class="text-3xl font-bold text-purple-500 mb-6 text-center">
        {{ pageTitle }}
      </h2>

      <div v-if="state.isLoading" class="text-center text-gray-500 py-6">
        <PulseLoader :color="'#9333ea'" />
      </div>

      <div v-else-if="state.quizzes.length === 0" class="text-center text-gray-500 py-6">
        <p>No quizzes found.</p>
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <QuizCard
          v-for="(quizItem, index) in state.quizzes.slice(0, limit || state.quizzes.length)"
          :key="index"
          :quiz="quizItem.Quiz || quizItem[0] || quizItem"
        />
      </div>
    </div>
  </section>

  <section v-if="showButton" class="m-auto max-w-lg my-10 px-6">
    <RouterLink
      to="/quizzes"
      class="block bg-purple-900 text-white text-center py-4 px-6 rounded-xl hover:bg-gray-700"
    >
      View All Quizzes
    </RouterLink>
  </section>
</template>
