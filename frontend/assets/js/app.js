const { createApp, watch } = window.Vue;
import { store } from "./store.js";
import { icons } from "./icons.js";
import LoginView from "./components/LoginView.js";
import Sidebar from "./components/Sidebar.js";
import HomeView from "./components/HomeView.js";
import ChatView from "./components/ChatView.js";
import WikiView from "./components/WikiView.js";
import CalendarView from "./components/CalendarView.js";
import NewsView from "./components/NewsView.js";

function loadAccountData() {
  store.loadSessions();
  store.loadModels();
}

const App = {
  components: { LoginView, Sidebar, HomeView, ChatView, WikiView, CalendarView, NewsView },
  setup() {
    store.initTheme();
    if (store.loggedIn) loadAccountData();
    // Covers both directions: logging in (start loading this account's
    // data) and getting logged out elsewhere (see store.handleUnauthorized) -
    // nothing else needs to react to loggedIn changing.
    watch(() => store.loggedIn, (loggedIn) => {
      if (loggedIn) loadAccountData();
    });

    // Same graceful-fallback pattern as HomeView.js's decorative images -
    // if the PNG isn't there yet, just hide the broken <img>.
    function onCornerMascotError(e) {
      e.target.style.display = "none";
    }

    return { store, icons, onCornerMascotError };
  },
  template: `
  <LoginView v-if="!store.loggedIn" />
  <div v-else class="app-shell">
    <button class="mobile-menu-btn" title="Menu" @click="store.toggleSidebar()" v-html="store.sidebarOpen ? icons.close : icons.menu"></button>
    <div v-if="store.sidebarOpen" class="sidebar-backdrop" @click="store.closeSidebar()"></div>
    <Sidebar />
    <HomeView v-if="store.view === 'home'" />
    <ChatView v-else-if="store.view === 'chat'" />
    <WikiView v-else-if="store.view === 'wiki'" />
    <CalendarView v-else-if="store.view === 'calendar'" />
    <NewsView v-else-if="store.view === 'news'" />

    <img class="corner-mascot" src="assets/images/corner.png" alt="" @error="onCornerMascotError" />
  </div>
  `,
};

createApp(App).mount("#app");
