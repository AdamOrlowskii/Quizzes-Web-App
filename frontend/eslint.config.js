import js from '@eslint/js'
import globals from 'globals'
import pluginVue from 'eslint-plugin-vue'
import pluginPrettier from 'eslint-plugin-prettier'
import { defineConfig } from 'eslint/config'

export default defineConfig([
  // reguły dla JS
  {
    files: ['**/*.{js,mjs,cjs}'],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      ...js.configs.recommended.rules,
    },
  },

  // reguły dla Vue i HTML
  {
    files: ['**/*.{vue,html}'],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      ...pluginVue.configs['vue3-recommended'].rules,
    },
  },

  // reguły Prettiera (działa globalnie)
  {
    plugins: { prettier: pluginPrettier },
    rules: {
      'prettier/prettier': 'error', // każdy błąd formatowania = error w ESLint
    },
  },
])
