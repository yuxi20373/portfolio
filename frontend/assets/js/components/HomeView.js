import { store } from "../store.js";
import { icons } from "../icons.js";

export default {
  setup() {
    function goWiki() {
      store.view = "wiki";
    }
    function goCalendar() {
      store.view = "calendar";
    }
    function goChat() {
      store.view = "chat";
    }

    // Graceful fallback: if a PNG hasn't been dropped into assets/images/
    // yet, just hide the broken <img> so the SVG icon underneath shows
    // through instead of a broken-image glyph.
    function onImgError(e) {
      e.target.style.display = "none";
    }
    function onHeroError(e) {
      e.target.style.display = "none";
      e.target.parentElement.classList.add("home-hero-fallback");
    }

    return { store, icons, goWiki, goCalendar, goChat, onImgError, onHeroError };
  },
  template: `
  <div class="main-panel home-panel">
    <div class="home-hero-wrap">
      <img class="home-hero-img" src="assets/images/hero.png" alt="" @error="onHeroError" />

      <button class="home-float home-float-light" title="Toggle light / dark mode" @click="store.toggleTheme()">
        <span class="home-float-inner">
          <span class="home-float-fallback" v-html="store.theme === 'dark' ? icons.sun : icons.moon"></span>
          <img src="assets/images/icon-light.png" alt="" @error="onImgError" />
        </span>
      </button>

      <button class="home-float home-float-wiki" title="Open the knowledge base" @click="goWiki">
        <span class="home-float-inner">
          <span class="home-float-fallback" v-html="icons.wiki"></span>
          <img src="assets/images/icon-wiki.png" alt="" @error="onImgError" />
        </span>
      </button>

      <button class="home-float home-float-calendar" title="Open the calendar" @click="goCalendar">
        <span class="home-float-inner">
          <span class="home-float-fallback" v-html="icons.calendar"></span>
          <img src="assets/images/icon-calendar.png" alt="" @error="onImgError" />
        </span>
      </button>

      <button class="home-float home-float-weather" title="Check today's weather" @click="goCalendar">
        <span class="home-float-inner">
          <span class="home-float-fallback" v-html="icons.cloud"></span>
          <img src="assets/images/icon-weather.png" alt="" @error="onImgError" />
        </span>
      </button>
    </div>

    <div class="home-cta">
      <button class="btn" @click="goChat">Start chatting →</button>
    </div>
  </div>
  `,
};
