<script setup>
import PulseLoader from 'vue-spinner/src/PulseLoader.vue'
import BackButton from '@/components/BackButton.vue'
import { reactive, onMounted, computed, ref } from 'vue'
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

const isDownloading = ref(false)

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

const downloadJSON = async () => {
  isDownloading.value = true
  try {
    const response = await quizAPI.exportJSON(quizId) // ← Poprawione z props.quiz.id
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${state.quiz.title}_questions.json`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    toast.success('JSON downloaded!')
  } catch (error) {
    console.error('Download error:', error)
    toast.error('Download failed')
  } finally {
    isDownloading.value = false
  }
}

const downloadPDF = async () => {
  isDownloading.value = true
  try {
    const response = await quizAPI.exportPDF(quizId) // ← Poprawione z props.quiz.id
    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${state.quiz.title}_test.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    toast.success('PDF downloaded!')
  } catch (error) {
    console.error('Download error:', error)
    toast.error('Download failed')
  } finally {
    isDownloading.value = false
  }
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

              <!-- Questions Preview (if loaded) -->
              <div v-if="state.questions.length > 0" class="mb-6">
                <h2 class="text-lg font-semibold mb-3 text-gray-700">
                  Questions ({{ state.questions.length }})
                </h2>
                <div class="space-y-3 max-h-140 overflow-y-auto">
                  <div
                    v-for="(question, index) in state.questions.slice(0, 6)"
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
                  <p v-if="state.questions.length > 6" class="text-sm text-gray-500 italic">
                    And {{ state.questions.length - 6 }} more questions...
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
          <aside class="space-y-6">
            <!-- Quiz Statistics -->
            <div class="bg-white rounded-xl shadow-lg overflow-hidden">
              <div class="bg-gradient-to-r from-purple-500 to-purple-600 p-4">
                <h3 class="text-lg font-bold text-white flex items-center gap-2">
                  <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                  Statistics
                </h3>
              </div>

              <div class="p-5">
                <div
                  class="flex items-center justify-between p-4 bg-gradient-to-r from-purple-50 to-purple-50 rounded-lg"
                >
                  <div class="flex items-center gap-3">
                    <div
                      class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center"
                    >
                      <svg
                        class="w-6 h-6 text-purple-600"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          stroke-linecap="round"
                          stroke-linejoin="round"
                          stroke-width="2"
                          d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </div>
                    <div>
                      <p class="text-sm text-gray-600 font-medium">Total Questions</p>
                      <p class="text-2xl font-bold text-gray-800">
                        {{ state.questions.length || 0 }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Manage Quiz -->
            <div v-if="isMyQuiz" class="bg-white rounded-xl shadow-lg overflow-hidden">
              <div class="bg-gradient-to-r from-purple-500 to-purple-600 p-4">
                <h3 class="text-lg font-bold text-white flex items-center gap-2">
                  <span class="text-xl">⚙️</span>
                  Manage Quiz
                </h3>
              </div>

              <div class="p-5 space-y-3">
                <RouterLink
                  :to="`/quizzes/edit/${quizId}`"
                  class="flex items-center gap-3 w-full p-3 rounded-lg border-2 border-green-200 hover:border-green-400 hover:bg-green-50 transition-all group"
                >
                  <div
                    class="flex-shrink-0 w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center group-hover:bg-green-200 transition-colors"
                  >
                    <svg
                      class="w-5 h-5 text-green-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                  </div>
                  <div class="flex-1 text-left">
                    <div class="font-semibold text-gray-800">Edit Quiz</div>
                    <div class="text-xs text-gray-500">Modify questions</div>
                  </div>
                  <svg
                    class="w-5 h-5 text-gray-400 group-hover:text-green-500 transition-colors"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </RouterLink>

                <button
                  @click="deleteQuiz"
                  class="flex items-center gap-3 w-full p-3 rounded-lg border-2 border-red-200 hover:border-red-400 hover:bg-red-50 transition-all group"
                >
                  <div
                    class="flex-shrink-0 w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center group-hover:bg-red-200 transition-colors"
                  >
                    <svg
                      class="w-5 h-5 text-red-600"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                      />
                    </svg>
                  </div>
                  <div class="flex-1 text-left">
                    <div class="font-semibold text-gray-800">Delete Quiz</div>
                    <div class="text-xs text-gray-500">Remove permanently</div>
                  </div>
                  <svg
                    class="w-5 h-5 text-gray-400 group-hover:text-red-500 transition-colors"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      stroke-width="2"
                      d="M9 5l7 7-7 7"
                    />
                  </svg>
                </button>
              </div>
            </div>

            <!-- Share Quiz -->
            <div class="bg-white rounded-xl shadow-lg overflow-hidden">
              <div class="bg-gradient-to-r from-purple-500 to-purple-600 p-4">
                <h3 class="text-lg font-bold text-white flex items-center gap-2">
                  <span class="text-xl">🔗</span>
                  Share Quiz
                </h3>
              </div>

              <div class="p-5">
                <!-- Downloads -->
                <div class="space-y-3 mb-5">
                  <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Download
                  </h4>

                  <button
                    @click="downloadJSON"
                    :disabled="isDownloading"
                    class="flex items-center gap-3 w-full p-3 rounded-lg border-2 border-blue-200 hover:border-blue-400 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all group"
                  >
                    <div
                      class="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center group-hover:bg-blue-200 transition-colors"
                    >
                      <span v-if="isDownloading" class="animate-spin">⏳</span>
                      <span v-else class="text-xl">📋</span>
                    </div>
                    <div class="flex-1 text-left">
                      <div class="font-semibold text-gray-800">JSON Format</div>
                      <div class="text-xs text-gray-500">Machine-readable data</div>
                    </div>
                    <svg
                      class="w-5 h-5 text-gray-400 group-hover:text-blue-500 transition-colors"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                  </button>

                  <button
                    @click="downloadPDF"
                    :disabled="isDownloading"
                    class="flex items-center gap-3 w-full p-3 rounded-lg border-2 border-red-200 hover:border-red-400 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-all group"
                  >
                    <div
                      class="flex-shrink-0 w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center group-hover:bg-red-200 transition-colors"
                    >
                      <span v-if="isDownloading" class="animate-spin">⏳</span>
                      <span v-else class="text-xl">📄</span>
                    </div>
                    <div class="flex-1 text-left">
                      <div class="font-semibold text-gray-800">PDF Test</div>
                      <div class="text-xs text-gray-500">Ready to print</div>
                    </div>
                    <svg
                      class="w-5 h-5 text-gray-400 group-hover:text-red-500 transition-colors"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                  </button>
                </div>

                <!-- Share Link -->
                <div class="space-y-3">
                  <h4 class="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Share Link
                  </h4>

                  <button
                    @click="copyQuizLink"
                    class="flex items-center justify-center gap-2 w-full p-3 bg-gradient-to-r from-purple-500 to-purple-600 hover:from-purple-600 hover:to-purple-700 text-white font-semibold rounded-lg transition-all transform hover:scale-105 shadow-md hover:shadow-lg"
                  >
                    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M8 3a1 1 0 011-1h2a1 1 0 110 2H9a1 1 0 01-1-1z" />
                      <path
                        d="M6 3a2 2 0 00-2 2v11a2 2 0 002 2h8a2 2 0 002-2V5a2 2 0 00-2-2 3 3 0 01-3 3H9a3 3 0 01-3-3z"
                      />
                    </svg>
                    <span>Copy Link</span>
                  </button>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  </section>
</template>
