const { ref } = window.Vue;
import { store } from "../store.js";

export default {
  setup() {
    const username = ref("");
    const password = ref("");
    const loading = ref(false);
    const error = ref("");

    async function submit() {
      if (!username.value.trim() || !password.value || loading.value) return;
      loading.value = true;
      error.value = "";
      try {
        await store.login(username.value.trim(), password.value);
      } catch (e) {
        error.value = "Invalid username or password.";
      } finally {
        loading.value = false;
      }
    }

    return { username, password, loading, error, submit };
  },
  template: `
  <div class="login-screen">
    <form class="login-card" @submit.prevent="submit">
      <h1>Knowledge Chatbot</h1>
      <input v-model="username" type="text" placeholder="Username" autocomplete="username" autofocus />
      <input v-model="password" type="password" placeholder="Password" autocomplete="current-password" />
      <div v-if="error" class="login-error">{{ error }}</div>
      <button class="btn" type="submit" :disabled="loading || !username.trim() || !password">
        <span v-if="loading" class="spinner"></span>{{ loading ? ' Logging in…' : 'Log in' }}
      </button>
    </form>
  </div>
  `,
};
