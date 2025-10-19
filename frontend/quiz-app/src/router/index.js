import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '@/views/HomeView.vue'
import QuizzesView from '@/views/QuizzesView.vue'
import NotFoundView from '@/views/NotFoundView.vue'
import QuizView from '@/views/QuizView.vue'
import AddQuizView from '@/views/AddQuizView.vue'
import EditQuizView from '@/views/EditQuizView.vue'
import LoginView from '@/views/LoginView.vue'
import SignUpView from '@/views/SignUpView.vue'
import PlayQuizView from '@/views/PlayQuizView.vue'

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
      component: QuizzesView,
    },
    {
      path: '/quizzes/my_quizzes',
      name: 'my-quizzes',
      component: QuizzesView,
    },
    {
      path: '/quizzes/add',
      name: 'add-quiz',
      component: AddQuizView,
    },
    {
      path: '/quizzes/edit/:id',
      name: 'edit-quiz',
      component: EditQuizView,
    },
    {
      path: '/quizzes/:id',
      name: 'quiz',
      component: QuizView,
    },
    {
      path: '/play/:id',
      name: 'play-quiz',
      component: PlayQuizView,
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
    },
    {
      path: '/signup',
      name: 'signup',
      component: SignUpView,
    },
    {
      path: '/:catchAll(.*)',
      name: 'not-found',
      component: NotFoundView,
    },
  ],
})

export default router
