<script setup>
import router from '@/router'
import { reactive } from 'vue'
import { useToast } from 'vue-toastification'
import axios from 'axios'

const form = reactive({
  title: '',
  file: null,
})

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

  const formData = new FormData()
  formData.append('title', form.title)
  formData.append('file', form.file)

  try {
    const response = await axios.post(`/api/quizzes`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })

    toast.success('Quiz Added Successfully')
    router.push(`/quizzes/${response.data.id}`)
  } catch (error) {
    console.error('Error fetching quiz', error)
    toast.error('Quiz Was Not Added')
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
              id="name"
              name="name"
              class="border rounded w-full py-2 px-3 mb-2"
              placeholder="eg. Quiz 1"
              required
            />
          </div>

          <div>
            <label class="block text-gray-700 font-bold mb-2">Upload File</label>
            <input
              type="file"
              accept=".pdf,.txt."
              @change="handleFileChange"
              class="border rounded w-full py-2 px-3 mb-2"
              required
            />
            <p class="text-gray-600 text-sm">Upload a PDF or TXT file</p>
          </div>

          <div>
            <button
              class="bg-purple-500 hover:bg-purple-600 text-white font-bold py-2 px-4 rounded-full w-full focus:outline-none focus:shadow-outline"
              type="submit"
            >
              Add Quiz
            </button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>
