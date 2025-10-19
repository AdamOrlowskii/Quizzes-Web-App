<script setup>
import router from '@/router'
import { reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useToast } from 'vue-toastification'
import { quizAPI } from '@/services/api'

const route = useRoute()
const quizId = route.params.id
const toast = useToast()

const form = reactive({
  title: '',
  published: true, // ✅ Dodaj to
  questions: [],
})

const state = reactive({
  quiz: {},
  isLoading: true,
  isSaving: false,
})

const addQuestion = () => {
  form.questions.push({
    question_text: '',
    answers: {
      1: '',
      2: '',
      3: '',
      4: '',
    },
    correct_answer: '1',
    quiz_id: parseInt(quizId),
  })
}

const removeQuestion = index => {
  if (confirm('Are you sure you want to delete this question?')) {
    form.questions.splice(index, 1)
  }
}

const handleSubmit = async () => {
  for (let i = 0; i < form.questions.length; i++) {
    const q = form.questions[i]
    if (!q.question_text.trim()) {
      toast.error(`Question ${i + 1} is missing question text`)
      return
    }
    if (!q.correct_answer) {
      toast.error(`Question ${i + 1} needs a correct answer selected`)
      return
    }

    for (let key in q.answers) {
      if (!q.answers[key].trim()) {
        toast.error(`Question ${i + 1}, Answer ${key} is empty`)
        return
      }
    }
  }

  state.isSaving = true

  try {
    await quizAPI.update(quizId, {
      title: form.title,
      content: state.quiz.content,
      published: form.published, // ✅ Użyj form.published
    })

    if (form.questions.length > 0) {
      await quizAPI.updateQuestions(quizId, form.questions)
    }

    toast.success('Quiz Updated Successfully')
    router.push(`/quizzes/${quizId}`)
  } catch (error) {
    console.error('Error updating quiz', error)
    const errorMessage = error.response?.data?.detail || 'Failed to update quiz'
    toast.error(errorMessage)
  } finally {
    state.isSaving = false
  }
}

onMounted(async () => {
  try {
    const quizResponse = await quizAPI.getById(quizId)

    let quizData = quizResponse.data

    if (quizData.Quiz) {
      quizData = quizData.Quiz
    } else if (Array.isArray(quizData)) {
      quizData = quizData[0]
    }

    state.quiz = quizData
    form.title = quizData.title
    form.published = quizData.published

    try {
      const questionsResponse = await quizAPI.getQuestions(quizId)
      form.questions = questionsResponse.data
    } catch (err) {
      console.warn('No questions found:', err)
      form.questions = []
    }
  } catch (error) {
    console.error('Error fetching quiz data', error)
    toast.error('Failed to load quiz')
  } finally {
    state.isLoading = false
  }
})
</script>

<template>
  <section class="bg-purple-50 min-h-screen py-8">
    <div class="container m-auto max-w-4xl">
      <div class="bg-white px-6 py-8 mb-4 shadow-md rounded-md">
        <form @submit.prevent="handleSubmit">
          <h2 class="text-3xl text-center font-semibold mb-6">Edit Quiz</h2>

          <!-- Loading state -->
          <div v-if="state.isLoading" class="text-center py-8">
            <p>Loading quiz...</p>
          </div>

          <div v-else>
            <!-- Quiz Title -->
            <div class="mb-6">
              <label class="block text-gray-700 font-bold mb-2"> Quiz Title </label>
              <input
                v-model="form.title"
                type="text"
                class="border rounded w-full py-2 px-3 focus:outline-none focus:border-purple-500"
                placeholder="Enter quiz title"
                required
              />
            </div>

            <div class="mb-6">
              <label class="flex items-center">
                <input
                  type="checkbox"
                  v-model="form.published"
                  :disabled="state.isSaving"
                  class="mr-2 h-4 w-4"
                />
                <span class="text-gray-700 font-bold"
                  >Publish quiz (make it visible to everyone)</span
                >
              </label>
            </div>

            <!-- Questions Section -->
            <div class="mb-6">
              <h3 class="text-xl font-semibold mb-4 text-gray-700">Questions</h3>

              <!-- Each Question -->
              <div
                v-for="(question, qIndex) in form.questions"
                :key="qIndex"
                class="mb-6 p-4 border rounded-lg bg-gray-50"
              >
                <!-- Question Header -->
                <div class="flex justify-between items-center mb-3">
                  <h4 class="font-semibold text-lg">Question {{ qIndex + 1 }}</h4>
                  <button
                    type="button"
                    @click="removeQuestion(qIndex)"
                    class="text-red-500 hover:text-red-700"
                    title="Delete question"
                  >
                    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fill-rule="evenodd"
                        d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                        clip-rule="evenodd"
                      />
                    </svg>
                  </button>
                </div>

                <!-- Question Text -->
                <div class="mb-4">
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    Question Text
                  </label>
                  <textarea
                    v-model="question.question_text"
                    rows="2"
                    class="w-full border rounded px-3 py-2 focus:outline-none focus:border-purple-500"
                    placeholder="Enter your question..."
                    required
                  ></textarea>
                </div>

                <!-- Answer Options -->
                <div class="mb-3">
                  <label class="block text-sm font-medium text-gray-700 mb-2">
                    Answer Options
                  </label>
                  <div class="space-y-2">
                    <div
                      v-for="answerKey in ['1', '2', '3', '4']"
                      :key="answerKey"
                      class="flex items-center space-x-2"
                    >
                      <!-- Radio for correct answer -->
                      <input
                        type="radio"
                        :name="`correct_${qIndex}`"
                        :value="answerKey"
                        v-model="question.correct_answer"
                        class="text-green-500 focus:ring-green-500"
                      />

                      <!-- Answer input -->
                      <div class="flex items-center flex-1">
                        <span class="font-semibold mr-2 w-6">{{ answerKey }}.</span>
                        <input
                          v-model="question.answers[answerKey]"
                          type="text"
                          class="flex-1 border rounded px-3 py-1 focus:outline-none focus:border-purple-500"
                          :placeholder="`Answer option ${answerKey}`"
                          required
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Show selected correct answer -->
                <div class="text-sm text-green-600 flex items-center">
                  <svg class="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                    <path
                      fill-rule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clip-rule="evenodd"
                    />
                  </svg>
                  Correct answer: Option {{ question.correct_answer }}
                </div>
              </div>

              <!-- Add Question Button -->
              <button
                type="button"
                @click="addQuestion"
                class="w-full py-3 border-2 border-dashed border-purple-300 rounded-lg text-purple-600 hover:border-purple-500 hover:bg-purple-50 transition"
              >
                + Add New Question
              </button>
            </div>

            <!-- Action Buttons -->
            <div class="flex justify-between">
              <button
                type="button"
                @click="router.back()"
                class="bg-gray-500 hover:bg-gray-600 text-white font-bold py-2 px-6 rounded-full"
              >
                Cancel
              </button>
              <button
                type="submit"
                :disabled="state.isSaving || form.questions.length === 0"
                class="bg-purple-500 hover:bg-purple-600 disabled:bg-gray-400 text-white font-bold py-2 px-6 rounded-full focus:outline-none focus:shadow-outline"
              >
                {{ state.isSaving ? 'Saving...' : 'Update Quiz' }}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
input[type='radio']:checked {
  background-color: #c054d6;
}
</style>
