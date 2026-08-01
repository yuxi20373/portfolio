const { createApp } = window.Vue;
import { store } from "./store.js";
import Sidebar from "./components/Sidebar.js";
import HomeView from "./components/HomeView.js";
import ChatView from "./components/ChatView.js";
import WikiView from "./components/WikiView.js";
import CalendarView from "./components/CalendarView.js";
import NewsView from "./components/NewsView.js";

const App = {
  components: { Sidebar, HomeView, ChatView, WikiView, CalendarView, NewsView },
  setup() {
    store.initTheme();
    store.loadSessions();
    return { store };
  },
  template: `
  <div class="app-shell">
    <Sidebar />
    <HomeView v-if="store.view === 'home'" />
    <ChatView v-else-if="store.view === 'chat'" />
    <WikiView v-else-if="store.view === 'wiki'" />
    <CalendarView v-else-if="store.view === 'calendar'" />
    <NewsView v-else-if="store.view === 'news'" />
  </div>
  `,
};

createApp(App).mount("#app");
