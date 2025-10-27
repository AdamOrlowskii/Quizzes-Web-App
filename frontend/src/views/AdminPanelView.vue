<script setup>
import { reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { adminAPI } from '@/services/api'
import { useToast } from 'vue-toastification'
import PulseLoader from 'vue-spinner/src/PulseLoader.vue'

const router = useRouter()
const toast = useToast()

const state = reactive({
  users: [],
  quizzes: [],
  isLoadingUsers: true,
  isLoadingQuizzes: true,
  activeTab: 'users',
})

const loadUsers = async () => {
  state.isLoadingUsers = true
  try {
    const response = await adminAPI.getAllUsers()
    state.users = response.data
  } catch (error) {
    if (error.response?.status === 403) {
      toast.error('Admin access required')
      router.push('/')
    } else {
      console.error('Error loading users:', error)
      toast.error('Failed to load users')
    }
  } finally {
    state.isLoadingUsers = false
  }
}

const loadQuizzes = async () => {
  state.isLoadingQuizzes = true
  try {
    const response = await adminAPI.getAllQuizzes(1000, 0)

    state.quizzes = response.data.items
  } catch (error) {
    console.error('Error loading quizzes:', error)
    toast.error('Failed to load quizzes')
  } finally {
    state.isLoadingQuizzes = false
  }
}

const deleteUser = async (userId, userEmail) => {
  if (!confirm(`Are you sure you want to delete user: ${userEmail}?`)) return

  try {
    await adminAPI.deleteUser(userId)
    toast.success('User deleted successfully')
    state.users = state.users.filter(u => u.id !== userId)
  } catch (error) {
    console.error('Error deleting user:', error)
    toast.error('Failed to delete user')
  }
}

const deleteQuiz = async (quizId, quizTitle) => {
  if (!confirm(`Are you sure you want to delete quiz: ${quizTitle}?`)) return

  try {
    await adminAPI.deleteQuiz(quizId)
    toast.success('Quiz deleted successfully')
    await loadQuizzes()
  } catch (error) {
    console.error('Error deleting quiz:', error)
    toast.error('Failed to delete quiz')
  }
}

const switchTab = tab => {
  state.activeTab = tab
  if (tab === 'quizzes' && state.quizzes.length === 0) {
    loadQuizzes()
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<template>
  <section class="min-h-screen bg-purple-50 py-8">
    <div class="container mx-auto max-w-6xl px-4">
      <!-- Header -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-800 mb-2">Admin Panel</h1>
        <p class="text-gray-600">Manage users and quizzes</p>
      </div>

      <!-- Tabs -->
      <div class="bg-white rounded-lg shadow-md mb-6">
        <div class="flex border-b">
          <button
            @click="switchTab('users')"
            :class="[
              'flex-1 py-4 px-6 font-semibold transition-colors',
              state.activeTab === 'users'
                ? 'bg-purple-500 text-white'
                : 'text-gray-600 hover:bg-gray-50',
            ]"
          >
            Users ({{ state.users.length }})
          </button>
          <button
            @click="switchTab('quizzes')"
            :class="[
              'flex-1 py-4 px-6 font-semibold transition-colors',
              state.activeTab === 'quizzes'
                ? 'bg-purple-500 text-white'
                : 'text-gray-600 hover:bg-gray-50',
            ]"
          >
            Quizzes ({{ state.quizzes.length }})
          </button>
        </div>
      </div>

      <!-- Users Tab -->
      <div v-if="state.activeTab === 'users'" class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-2xl font-bold mb-4">All Users</h2>

        <div v-if="state.isLoadingUsers" class="text-center py-12">
          <PulseLoader :color="'#9333ea'" />
        </div>

        <div v-else-if="state.users.length === 0" class="text-center py-12 text-gray-500">
          No users found
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Email
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Created
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Admin
                </th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr v-for="user in state.users" :key="user.id" class="hover:bg-gray-50">
                <td class="px-6 py-4 text-sm text-gray-900">{{ user.id }}</td>
                <td class="px-6 py-4 text-sm text-gray-900">{{ user.email }}</td>
                <td class="px-6 py-4 text-sm text-gray-500">
                  {{ new Date(user.created_at).toLocaleDateString() }}
                </td>
                <td class="px-6 py-4 text-sm">
                  <span v-if="user.is_admin" class="text-yellow-600 font-semibold">Admin</span>
                  <span v-else class="text-gray-400">User</span>
                </td>
                <td class="px-6 py-4 text-sm">
                  <button
                    v-if="!user.is_admin"
                    @click="deleteUser(user.id, user.email)"
                    class="text-red-600 hover:text-red-800 font-medium"
                  >
                    Delete
                  </button>
                  <span v-else class="text-gray-400 text-xs">Protected</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Quizzes Tab -->
      <div v-if="state.activeTab === 'quizzes'" class="bg-white rounded-lg shadow-md p-6">
        <h2 class="text-2xl font-bold mb-4">All Quizzes</h2>

        <div v-if="state.isLoadingQuizzes" class="text-center py-12">
          <PulseLoader :color="'#9333ea'" />
        </div>

        <div v-else-if="state.quizzes.length === 0" class="text-center py-12 text-gray-500">
          No quizzes found
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div
            v-for="quizItem in state.quizzes"
            :key="quizItem.Quiz?.id || quizItem[0]?.id"
            class="border rounded-lg p-4 hover:shadow-md transition"
          >
            <div class="flex justify-between items-start mb-2">
              <h3 class="font-semibold text-lg">
                {{ quizItem.Quiz?.title || quizItem[0]?.title }}
              </h3>
              <span
                :class="[
                  'px-2 py-1 text-xs rounded-full',
                  quizItem.Quiz?.published || quizItem[0]?.published
                    ? 'bg-green-100 text-green-800'
                    : 'bg-yellow-100 text-yellow-800',
                ]"
              >
                {{ quizItem.Quiz?.published || quizItem[0]?.published ? 'Public' : 'Private' }}
              </span>
            </div>

            <p class="text-sm text-gray-600 mb-2">
              By: {{ quizItem.Quiz?.owner?.email || quizItem[0]?.owner?.email || 'Unknown' }}
            </p>

            <p class="text-xs text-gray-500 mb-3">
              Created:
              {{
                new Date(quizItem.Quiz?.created_at || quizItem[0]?.created_at).toLocaleDateString()
              }}
            </p>

            <div class="flex gap-2">
              <RouterLink
                :to="`/quizzes/${quizItem.Quiz?.id || quizItem[0]?.id}`"
                class="flex-1 text-center bg-purple-500 hover:bg-purple-600 text-white text-sm py-2 px-4 rounded"
              >
                View
              </RouterLink>
              <button
                @click="
                  deleteQuiz(
                    quizItem.Quiz?.id || quizItem[0]?.id,
                    quizItem.Quiz?.title || quizItem[0]?.title
                  )
                "
                class="bg-red-500 hover:bg-red-600 text-white text-sm py-2 px-4 rounded"
              >
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
