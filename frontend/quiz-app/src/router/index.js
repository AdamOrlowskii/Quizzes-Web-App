import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import JobsView from '@/views/JobsView.vue'
import NotFoundView from '@/views/NotFoundView.vue'
import JobView from '@/views/JobView.vue'
import AddJobView from '@/views/AddJobView.vue'
import EditJobView from '@/views/EditJobView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/quizzes',
      name: 'quizzes',
      component: JobsView,
    },
    {
      path: '/quizzes/:id',
      name: 'quiz',
      component: JobView,
    },
    {
      path: '/quizzes/add',
      name: 'add-quiz',
      component: AddJobView,
    },
    {
      path: '/quizzes/edit/:id',
      name: 'edit-quiz',
      component: EditJobView,
    },
    {
      path: '/:catchAll(.*)',
      name: 'not-found',
      component: NotFoundView,
    },
  ],
})

export default router
