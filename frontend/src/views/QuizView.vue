<script setup>
import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
import BackButton from '@/components/BackButton.vue'
import { reactive, onMounted, computed } from 'vue'
import { useRoute, RouterLink, useRouter } from 'vue-router'
import { useToast } from 'vue-toastification'
import { quizAPI } from '@/services/api'
import { favouriteAPI } from '@/services/api'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const quizId = route.params.id

const state = reactive({
  quiz: {},
  questions: [],
  isLoading: true,
  isFavourite: false,
})

const toggleFavourite = async () => {
  try {
    if (state.isFavourite) {
      await favouriteAPI.remove(quizId)
      state.isFavourite = false
      toast.success('Removed from favourites')
    } else {
      await favouriteAPI.add(quizId)
      state.isFavourite = true
      toast.success('Added to favourites')
    }
  } catch (error) {
    console.error('Error toggling favourite:', error)
    toast.error('Failed to update favourites')
  }
}

const isMyQuiz = computed(() => {
  return state.quiz.owner?.email === localStorage.getItem('userEmail')
})

const copyQuizLink = async () => {
  try {
    await navigator.clipboard.writeText(window.location.href)
    toast.success('Quiz link copied to clipboard!')
  } catch (error) {
    console.error('Failed to copy:', error)
    toast.error('Failed to copy link')
  }
}

const deleteQuiz = async () => {
  try {
    const confirm = window.confirm('Are you sure you want to delete this quiz?')
    if (confirm) {
      await quizAPI.delete(quizId)
      toast.success('Quiz Deleted Successfully')
      router.push('/quizzes')
    }
  } catch (error) {
    console.error('Error deleting quiz', error)
    toast.error('Quiz Not Deleted')
  }
}

const startQuiz = () => {
  router.push(`/play/${quizId}`)
}

const formatDate = dateString => {
  if (!dateString) return 'N/A'
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(async () => {
  try {
    const response = await quizAPI.getById(quizId)
    let quizData = response.data

    if (quizData.Quiz) {
      quizData = quizData.Quiz
    } else if (Array.isArray(quizData)) {
      quizData = quizData[0]
    }

    state.quiz = quizData

    try {
      const favourites = await favouriteAPI.getMyFavourites()
      state.isFavourite = favourites.data.some(
        item => (item.Quiz?.id || item[0]?.id) === parseInt(quizId)
      )
    } catch (err) {
      console.warn('Could not load favourites:', err)
    }

    try {
      const questionsResponse = await quizAPI.getQuestions(quizId)
      state.questions = questionsResponse.data
    } catch (err) {
      console.warn('No questions available:', err)
      state.questions = []
    }
  } catch (error) {
    console.error('Error fetching quiz', error)
  } finally {
    state.isLoading = false
  }
})
</script>

<template>
  <section class="min-h-screen bg-purple-50">
    <div class="container m-auto py-6 px-6">
      <BackButton />

      <!-- Loading State -->
      <div v-if="state.isLoading" class="text-center text-gray-500 py-12">
        <PulseLoader :color="'#9333ea'" />
      </div>

      <!-- Quiz Content -->
      <div v-else class="mt-6">
        <div class="grid grid-cols-1 md:grid-cols-70/30 w-full gap-6">
          <!-- Main Content -->
          <main>
            <!-- Quiz Details Card -->
            <div class="bg-white p-6 rounded-lg shadow-md">
              <!-- Quiz Header -->
              <div class="mb-6">
                <div class="flex justify-between items-start">
                  <h1 class="text-3xl font-bold text-gray-800 mb-2">
                    {{ state.quiz.title }}
                  </h1>
                  <span
                    :class="
                      state.quiz.published ? 'bg-green-100 text-black' : 'bg-red-100 text-black'
                    "
                    class="px-3 py-1 rounded-full text-sm font-medium"
                  >
                    {{ state.quiz.published ? 'Published' : 'Private' }}
                  </span>
                </div>

                <!-- Quiz Meta Info -->
                <div class="text-sm text-gray-600 space-y-1">
                  <div class="flex items-center">
                    <svg class="w-4 h-4 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fill-rule="evenodd"
                        d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z"
                        clip-rule="evenodd"
                      />
                    </svg>
                    Created: {{ formatDate(state.quiz.created_at) }}
                  </div>
                </div>
              </div>

              <!-- Quiz Content/Description -->
              <div class="mb-6">
                <h2 class="text-lg font-semibold mb-2 text-gray-700">Description</h2>
                <p class="text-gray-600 bg-gray-50 p-4 rounded">
                  {{ state.quiz.content || 'No description available.' }}
                </p>
              </div>

              <!-- Questions Preview (if loaded) -->
              <div v-if="state.questions.length > 0" class="mb-6">
                <h2 class="text-lg font-semibold mb-3 text-gray-700">
                  Questions ({{ state.questions.length }})
                </h2>
                <div class="space-y-3 max-h-96 overflow-y-auto">
                  <div
                    v-for="(question, index) in state.questions.slice(0, 5)"
                    :key="question.id"
                    class="bg-gray-50 p-3 rounded"
                  >
                    <p class="font-medium text-sm">{{ index + 1 }}. {{ question.question_text }}</p>
                    <div class="grid grid-cols-2 gap-2 mt-2">
                      <div
                        v-for="(answer, key) in question.answers"
                        :key="key"
                        class="text-xs text-gray-600"
                        :class="{ 'text-green-600 font-semibold': question.correct_answer === key }"
                      >
                        {{ key }}. {{ answer }}
                        <span v-if="question.correct_answer === key"> ✓</span>
                      </div>
                    </div>
                  </div>
                  <p v-if="state.questions.length > 5" class="text-sm text-gray-500 italic">
                    And {{ state.questions.length - 5 }} more questions...
                  </p>
                </div>
              </div>

              <!-- Action Buttons -->
              <div class="flex gap-4">
                <button
                  @click="toggleFavourite"
                  class="bg-yellow-500 hover:bg-yellow-600 text-white font-bold py-3 px-6 rounded-lg transition duration-200"
                >
                  {{ state.isFavourite ? '⭐ Remove from Favourites' : '☆ Add to Favourites' }}
                </button>

                <button
                  @click="startQuiz"
                  class="flex-1 bg-purple-500 hover:bg-purple-600 text-white font-bold py-3 px-6 rounded-lg transition duration-200"
                >
                  <svg class="w-5 h-5 inline mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fill-rule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  Start Quiz
                </button>
              </div>
            </div>
          </main>

          <!-- Sidebar -->
          <aside>
            <div class="bg-white p-6 rounded-lg shadow-md">
              <h3 class="text-xl font-bold mb-4">Quiz Statistics</h3>
              <div class="space-y-3">
                <div class="flex justify-between">
                  <span class="text-gray-600">Questions:</span>
                  <span class="font-semibold">{{ state.questions.length || 'N/A' }}</span>
                </div>
              </div>
            </div>

            <div v-if="isMyQuiz" class="bg-white p-6 rounded-lg shadow-md mt-6">
              <h3 class="text-xl font-bold mb-4">Manage Quiz</h3>
              <RouterLink
                :to="`/quizzes/edit/${quizId}`"
                class="bg-purple-500 hover:bg-purple-600 text-white text-center font-bold py-2 px-4 rounded-full w-full focus:outline-none focus:shadow-outline block"
              >
                <svg class="w-4 h-4 inline mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"
                  />
                </svg>
                Edit Quiz
              </RouterLink>
              <button
                @click="deleteQuiz"
                class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded-full w-full focus:outline-none focus:shadow-outline mt-3 block"
              >
                <svg class="w-4 h-4 inline mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fill-rule="evenodd"
                    d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                    clip-rule="evenodd"
                  />
                </svg>
                Delete Quiz
              </button>
            </div>

            <div class="bg-white p-6 rounded-lg shadow-md mt-6">
              <h3 class="text-xl font-bold mb-4">Share Quiz</h3>
              <button
                @click="copyQuizLink"
                class="bg-blue-500 hover:bg-blue-600 text-white text-center font-bold py-2 px-4 rounded-full w-full"
              >
                <svg class="w-4 h-4 inline mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
                  <path
                    d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z"
                  />
                </svg>
                Copy Link
              </button>
            </div>
          </aside>
        </div>
      </div>
    </div>
  </section>
</template>
