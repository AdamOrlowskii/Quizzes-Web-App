<script setup>
import Hero from '@/components/Hero.vue'
import HomeCards from '@/components/HomeCards.vue'
import JobListings from '@/components/QuizListings.vue'
</script>

<template>
  <Hero />
  <HomeCards />
  <JobListings :limit="3" :show-button="true" />
</template>
