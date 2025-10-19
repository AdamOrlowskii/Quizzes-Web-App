<script setup>
import router from '@/router'
import { reactive, ref } from 'vue'
import { useToast } from 'vue-toastification'
import { quizAPI } from '@/services/api'

const form = reactive({
  title: '',
  file: null,
  published: true,
})

const uploading = ref(false)
const toast = useToast()

const handleFileChange = event => {
  const file = event.target.files[0]
  if (file) {
    form.file = file
  }
}

const handleSubmit = async () => {
  if (!form.file) {
    toast.error('Please select a file')
    return
  }

  if (!form.title.trim()) {
    toast.error('Please enter a quiz title')
    return
  }

  uploading.value = true

  try {
    const response = await quizAPI.create(form.file, form.title, form.published)

    toast.success('Quiz Added Successfully')
    router.push(`/quizzes/${response.data.id}`)
  } catch (error) {
    console.error('Error creating quiz:', error)
    const errorMessage = error.response?.data?.detail || 'Quiz Was Not Added'
    toast.error(errorMessage)
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <section class="bg-purple-50">
    <div class="container m-auto max-w-2xl py-24">
      <div class="bg-white px-6 py-8 mb-4 shadow-md rounded-md border m-4 md:m-0">
        <form @submit.prevent="handleSubmit">
          <h2 class="text-3xl text-center font-semibold mb-6">Add Quiz</h2>

          <div class="mb-4">
            <label class="block text-gray-700 font-bold mb-2">Quiz Title</label>
            <input
              type="text"
              v-model="form.title"
              class="border rounded w-full py-2 px-3 mb-2"
              placeholder="eg. Quiz 1"
              :disabled="uploading"
              required
            />
          </div>

          <div class="mb-4">
            <label class="block text-gray-700 font-bold mb-2">Upload File</label>
            <input
              type="file"
              accept=".pdf,.txt"
              @change="handleFileChange"
              class="border rounded w-full py-2 px-3 mb-2"
              :disabled="uploading"
              required
            />
            <p class="text-gray-600 text-sm">Upload a PDF or TXT file</p>
          </div>

          <div class="mb-4">
            <label class="flex items-center">
              <input
                type="checkbox"
                v-model="form.published"
                :disabled="uploading"
                class="mr-2 h-4 w-4"
              />
              <span class="text-gray-700">Make it public</span>
            </label>
          </div>

          <div>
            <button
              class="bg-purple-500 hover:bg-purple-600 text-white font-bold py-2 px-4 rounded-full w-full focus:outline-none focus:shadow-outline disabled:bg-gray-400 disabled:cursor-not-allowed"
              type="submit"
              :disabled="uploading"
            >
              {{ uploading ? 'Creating Quiz...' : 'Add Quiz' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>
