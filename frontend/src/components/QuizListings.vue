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
  currentPage: 1,
  itemsPerPage: 9,
  totalQuizzes: 0,
})

const skip = computed(() => (state.currentPage - 1) * state.itemsPerPage)
const totalPages = computed(() => Math.ceil(state.totalQuizzes / state.itemsPerPage))
const hasPrevPage = computed(() => state.currentPage > 1)
const hasNextPage = computed(() => state.currentPage < totalPages.value)
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
      response = await quizAPI.getMyQuizzes(state.itemsPerPage, skip.value)
    } else if (route.path === '/quizzes/my_favourite_quizzes') {
      response = await quizAPI.getMyFavouriteQuizzes(state.itemsPerPage, skip.value)
    } else {
      response = await quizAPI.getAll(state.itemsPerPage, skip.value)
    }

    console.log('Quizzes loaded:', response.data)
    state.quizzes = response.data.items

    state.totalQuizzes = response.data.total
  } catch (error) {
    console.error('Error fetching quizzes', error)
  } finally {
    state.isLoading = false
  }
}

const goToPage = page => {
  if (page < 1 || page > totalPages.value) return
  state.currentPage = page
  fetchQuizzes()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const nextPage = () => hasNextPage.value && goToPage(state.currentPage + 1)
const prevPage = () => hasPrevPage.value && goToPage(state.currentPage - 1)

onMounted(() => {
  fetchQuizzes()
})

watch(
  () => route.path,
  () => {
    state.currentPage = 1
    fetchQuizzes()
  }
)
</script>

<template>
  <section class="bg-purple-50 px-4 py-10">
    <div class="container-xl lg:container m-auto">
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
      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex justify-center items-center gap-2 mt-8">
        <button
          @click="prevPage"
          :disabled="!hasPrevPage"
          :class="
            hasPrevPage
              ? 'bg-purple-500 text-white hover:bg-purple-600'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          "
          class="px-4 py-2 rounded-lg font-medium"
        >
          Previous
        </button>

        <button
          v-for="page in totalPages"
          :key="page"
          @click="goToPage(page)"
          :class="
            page === state.currentPage
              ? 'bg-purple-500 text-white'
              : 'bg-white text-purple-500 hover:bg-purple-100'
          "
          class="px-4 py-2 rounded-lg font-medium"
        >
          {{ page }}
        </button>

        <button
          @click="nextPage"
          :disabled="!hasNextPage"
          :class="
            hasNextPage
              ? 'bg-purple-500 text-white hover:bg-purple-600'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          "
          class="px-4 py-2 rounded-lg font-medium"
        >
          Next
        </button>
      </div>
    </div>
  </section>

  <section v-if="showButton" class="m-auto max-w-lg my-10 px-6">
    <RouterLink
      to="/quizzes"
      class="block bg-purple-600 text-white text-center py-4 px-6 rounded-xl hover:bg-gray-700"
    >
      View All Quizzes
    </RouterLink>
  </section>
</template>
