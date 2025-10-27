<script setup>
import { RouterLink } from 'vue-router'
import Card from '@/components/Card.vue'
</script>

<template>
  <section class="py-4">
    <div class="container-xl lg:container m-auto">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-lg">
        <Card>
          <h2 class="text-2xl font-bold">Take already existing quiz</h2>
          <p class="mt-2 mb-4">Browse thousands of quizzes created by other users</p>
          <RouterLink
            to="/quizzes"
            class="inline-block bg-purple-500 text-white rounded-lg px-4 py-2 hover:bg-purple-600"
          >
            Browse Quizzes
          </RouterLink>
        </Card>
        <Card>
          <h2 class="text-2xl font-bold">Create quiz</h2>
          <p class="mt-2 mb-4">Create your own quiz and learn from your own materials</p>
          <RouterLink
            to="/quizzes/add"
            class="inline-block bg-purple-500 text-white rounded-lg px-4 py-2 hover:bg-purple-600"
          >
            Add Quiz
          </RouterLink>
        </Card>
      </div>
    </div>
  </section>
</template>
