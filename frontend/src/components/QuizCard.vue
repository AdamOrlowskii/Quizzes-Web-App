<script setup>
import { RouterLink } from 'vue-router'
import { defineProps } from 'vue'

// eslint-disable-next-line no-unused-vars
const props = defineProps({
  quiz: Object,
})
</script>

<template>
  <div class="bg-white rounded-xl shadow-md relative">
    <div class="p-4">
      <div class="mb-6">
        <div class="text-black-900 my-2">Quiz Title: {{ quiz.title }}</div>
      </div>

      <h3 class="text-purple-500 mb-2">Published: {{ quiz.published }}</h3>
      <div class="border border-gray-100 mb-5"></div>

      <div class="flex flex-col lg:flex-row justify-between mb-4">
        <div class="text-pink-400 mb-3">Quiz number: {{ quiz.id }}</div>
        <RouterLink
          :to="'/quizzes/' + quiz.id"
          class="h-[36px] bg-purple-500 hover:bg-purple-600 text-white px-4 py-2 rounded-lg text-center text-sm"
        >
          Read More
        </RouterLink>
      </div>
    </div>
  </div>
</template>
