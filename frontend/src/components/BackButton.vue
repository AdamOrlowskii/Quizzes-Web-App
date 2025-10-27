<script setup>
import { RouterLink } from 'vue-router'
</script>

<template>
  <section>
    <div class="container m-auto py-6 px-6">
      <RouterLink to="/quizzes" class="text-purple-500 hover:text-purple-600 flex items-center">
        <i class="pi pi-arrow-circle-left mr-2"></i> Back to Quiz Listings
      </RouterLink>
    </div>
  </section>
</template>
