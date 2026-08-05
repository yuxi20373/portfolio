const { createApp, computed, watch } = window.Vue;
import { store } from "./store.js";
import { icons } from "./icons.js";
import LoginView from "./components/LoginView.js";
import Sidebar from "./components/Sidebar.js";
import HomeView from "./components/HomeView.js";
import ChatView from "./components/ChatView.js";
import WikiView from "./components/WikiView.js";
import CalendarView from "./components/CalendarView.js";
import NewsView from "./components/NewsView.js";
import NotesView from "./components/NotesView.js";
import Notice from "./components/Notice.js";

function loadAccountData() {
  store.loadSessions();
  store.loadModels();
}

const App = {
  components: { LoginView, Sidebar, HomeView, ChatView, WikiView, CalendarView, NewsView, NotesView, Notice },
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
    function onCornerImgError(e) {
      e.target.style.display = "none";
    }
    // cornerSrc's :src changes on every view switch (unlike the logout
    // button's static image) - if an earlier view's image 404'd and got
    // hidden, undo that once a later view's image loads fine, same as
    // the light/dark toggle button below.
    function onCornerImgLoad(e) {
      e.target.style.display = "";
    }

    // One corner image per view (store.view is "home"/"chat"/"wiki"/
    // "calendar"/"notes"/"news") instead of a single shared corner.png -
    // naming the files corner-<view>.png means a new view automatically
    // gets a slot here with no code change. Calendar is the one exception:
    // it cycles through month-01.png..month-12.png (see store.calendarMonth,
    // kept in sync by CalendarView.js) instead of a static corner-calendar.png.
    const cornerSrc = computed(() => {
      if (store.view === "calendar" && store.calendarMonth) {
        return `assets/images/month-${String(store.calendarMonth).padStart(2, "0")}.png`;
      }
      return `assets/images/corner-${store.view}.png`;
    });

    // Quick logout from anywhere, without opening the sidebar drawer first
    // (same confirm() the sidebar's own logout button uses).
    function onLogoutClick() {
      if (confirm("Log out?")) store.logout();
    }

    return { store, icons, onCornerImgError, onCornerImgLoad, cornerSrc, onLogoutClick };
  },
  template: `
  <LoginView v-if="!store.loggedIn" />
  <div v-else class="app-shell">
    <Notice />
    <button v-if="store.view !== 'home'" class="mobile-menu-btn" :class="{ open: store.sidebarOpen }" title="Menu" @click="store.toggleSidebar()" v-html="store.sidebarOpen ? icons.chevronLeft : icons.chevronRight"></button>
    <div v-if="store.sidebarOpen" class="sidebar-backdrop" @click="store.closeSidebar()"></div>
    <Sidebar />
    <HomeView v-if="store.view === 'home'" />
    <ChatView v-else-if="store.view === 'chat'" />
    <WikiView v-else-if="store.view === 'wiki'" />
    <CalendarView v-else-if="store.view === 'calendar'" />
    <NotesView v-else-if="store.view === 'notes'" />
    <NewsView v-else-if="store.view === 'news'" />

    <img class="corner-mascot" :src="cornerSrc" alt="" @error="onCornerImgError" @load="onCornerImgLoad" />

    <button class="home-float corner-logout" title="Log out" @click="onLogoutClick">
      <span class="home-float-inner">
        <span class="home-float-fallback" v-html="icons.logout"></span>
        <img src="assets/images/logout.png" alt="" @error="onCornerImgError" />
      </span>
    </button>
  </div>
  `,
};

createApp(App).mount("#app");
