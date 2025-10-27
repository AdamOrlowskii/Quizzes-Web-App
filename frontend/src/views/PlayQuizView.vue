<script setup>
import { reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { quizAPI } from '@/services/api'
import { useToast } from 'vue-toastification'
import PulseLoader from 'vue-spinner/src/PulseLoader.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const quizId = route.params.id

const state = reactive({
  quiz: null,
  questions: [],
  currentQuestionIndex: 0,
  selectedAnswer: null,
  userAnswers: [],
  isLoading: true,
  showResults: false,
  score: 0,
})

const currentQuestion = computed(() => {
  return state.questions[state.currentQuestionIndex]
})

const progress = computed(() => {
  return ((state.currentQuestionIndex + 1) / state.questions.length) * 100
})

const selectAnswer = answerKey => {
  state.selectedAnswer = answerKey
}

const nextQuestion = () => {
  if (!state.selectedAnswer) {
    toast.warning('Please select an answer')
    return
  }

  state.userAnswers.push({
    questionId: currentQuestion.value.id,
    selectedAnswer: state.selectedAnswer,
    correctAnswer: currentQuestion.value.correct_answer,
    isCorrect: state.selectedAnswer === currentQuestion.value.correct_answer,
  })

  if (state.selectedAnswer === currentQuestion.value.correct_answer) {
    state.score++
  }

  state.selectedAnswer = null

  if (state.currentQuestionIndex < state.questions.length - 1) {
    state.currentQuestionIndex++
  } else {
    state.showResults = true
  }
}

const restartQuiz = () => {
  state.currentQuestionIndex = 0
  state.selectedAnswer = null
  state.userAnswers = []
  state.showResults = false
  state.score = 0
}

const goBack = () => {
  router.push(`/quizzes/${quizId}`)
}

onMounted(async () => {
  try {
    const quizResponse = await quizAPI.getById(quizId)
    state.quiz = quizResponse.data.Quiz || quizResponse.data[0] || quizResponse.data

    const questionsResponse = await quizAPI.getQuestions(quizId)
    state.questions = questionsResponse.data

    if (state.questions.length === 0) {
      toast.error('This quiz has no questions')
      router.push(`/quizzes/${quizId}`)
    }
  } catch (error) {
    console.error('Error loading quiz:', error)
    toast.error('Failed to load quiz')
    router.push('/quizzes')
  } finally {
    state.isLoading = false
  }
})
</script>

<template>
  <section class="bg-purple-50 min-h-screen py-8">
    <div class="container m-auto max-w-3xl px-4">
      <!-- Loading -->
      <div v-if="state.isLoading" class="text-center py-12">
        <PulseLoader />
      </div>

      <!-- Quiz Playing -->
      <div v-else-if="!state.showResults" class="bg-white rounded-lg shadow-lg p-8">
        <!-- Header -->
        <div class="mb-6">
          <h1 class="text-2xl font-bold text-gray-800 mb-2">{{ state.quiz?.title }}</h1>
          <div class="flex justify-between text-sm text-gray-600 mb-4">
            <span
              >Question {{ state.currentQuestionIndex + 1 }} / {{ state.questions.length }}</span
            >
            <span>Score: {{ state.score }} / {{ state.currentQuestionIndex }}</span>
          </div>
          <!-- Progress Bar -->
          <div class="w-full bg-gray-200 rounded-full h-2">
            <div
              class="bg-purple-500 h-2 rounded-full transition-all duration-300"
              :style="{ width: progress + '%' }"
            ></div>
          </div>
        </div>

        <!-- Question -->
        <div v-if="currentQuestion" class="mb-8">
          <h2 class="text-xl font-semibold text-gray-800 mb-6">
            {{ currentQuestion.question_text }}
          </h2>

          <!-- Answers -->
          <div class="space-y-3">
            <button
              v-for="(answer, key) in currentQuestion.answers"
              :key="key"
              @click="selectAnswer(key)"
              :class="[
                'w-full text-left p-4 rounded-lg border-2 transition-all',
                state.selectedAnswer === key
                  ? 'border-purple-500 bg-purple-50'
                  : 'border-gray-300 hover:border-purple-300 hover:bg-gray-50',
              ]"
            >
              <span class="font-semibold mr-3">{{ key }}.</span>
              {{ answer }}
            </button>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex justify-between">
          <button
            @click="goBack"
            class="px-6 py-3 bg-gray-500 hover:bg-gray-600 text-white rounded-lg"
          >
            Exit Quiz
          </button>
          <button
            @click="nextQuestion"
            :disabled="!state.selectedAnswer"
            class="px-6 py-3 bg-purple-500 hover:bg-purple-600 disabled:bg-gray-400 text-white rounded-lg"
          >
            {{ state.currentQuestionIndex < state.questions.length - 1 ? 'Next' : 'Finish' }}
          </button>
        </div>
      </div>

      <!-- Results -->
      <div v-else class="bg-white rounded-lg shadow-lg p-8 text-center">
        <h1 class="text-3xl font-bold text-gray-800 mb-4">Quiz Complete! 🎉</h1>

        <div class="mb-8">
          <div class="text-6xl font-bold text-purple-500 mb-2">
            {{ state.score }} / {{ state.questions.length }}
          </div>
          <div class="text-2xl text-gray-600">
            {{ Math.round((state.score / state.questions.length) * 100) }}%
          </div>
          <p class="text-gray-600 mt-4">
            {{
              state.score === state.questions.length
                ? 'Perfect score!'
                : state.score >= state.questions.length * 0.7
                  ? 'Great job!'
                  : state.score >= state.questions.length * 0.5
                    ? 'Good effort!'
                    : 'Keep practicing!'
            }}
          </p>
        </div>

        <!-- Review Answers -->
        <div class="mb-8 text-left">
          <h3 class="text-xl font-semibold mb-4">Review Your Answers</h3>
          <div class="space-y-4">
            <div
              v-for="(answer, index) in state.userAnswers"
              :key="index"
              :class="[
                'p-4 rounded-lg border-2',
                answer.isCorrect ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50',
              ]"
            >
              <div class="flex items-center mb-2">
                <span
                  :class="['font-semibold', answer.isCorrect ? 'text-green-600' : 'text-red-600']"
                >
                  Question {{ index + 1 }}:
                  {{ answer.isCorrect ? '✓ Correct' : '✗ Incorrect' }}
                </span>
              </div>
              <p class="text-sm text-gray-700 mb-1">
                Your answer: <strong>{{ answer.selectedAnswer }}</strong>
              </p>
              <p v-if="!answer.isCorrect" class="text-sm text-gray-700">
                Correct answer: <strong>{{ answer.correctAnswer }}</strong>
              </p>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-4 justify-center">
          <button
            @click="restartQuiz"
            class="px-6 py-3 bg-purple-500 hover:bg-purple-600 text-white rounded-lg"
          >
            Try Again
          </button>
          <button
            @click="goBack"
            class="px-6 py-3 bg-gray-500 hover:bg-gray-600 text-white rounded-lg"
          >
            Back to Quiz
          </button>
        </div>
      </div>
    </div>
  </section>
</template>
