const { ref, computed, onMounted } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";
import { api } from "../api.js";

export default {
  setup() {
    function goWiki() {
      store.view = "wiki";
    }
    function goCalendar() {
      store.view = "calendar";
    }
    function goNews() {
      store.view = "news";
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
    // The light/dark toggle's :src swaps between two files on click (see
    // template below) - if one of the two was hidden by onImgError, undo
    // that once the OTHER one loads fine, or it'd stay hidden forever.
    function onImgLoad(e) {
      e.target.style.display = "";
    }
    function onHeroError(e) {
      e.target.style.display = "none";
      e.target.parentElement.classList.add("home-hero-fallback");
    }

    // Today's weather, fetched once on load - drives the hero art and the
    // weather float's background (see isRaining/heroSrc below). Same
    // will_rain/weather_code shape as CalendarView.js's weather widget;
    // not shared via the store since this is the only other place that
    // needs it and only for a one-off "today" lookup.
    const weather = ref(null);
    onMounted(async () => {
      const d = new Date();
      const todayStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
      weather.value = await api.get(`/api/weather?date=${todayStr}`).catch(() => null);
    });

    const isRaining = computed(() => !!weather.value && weather.value.will_rain === true);
    // WMO 0/1 = clear / mainly clear
    const isSunny = computed(
      () => !!weather.value && !isRaining.value && [0, 1].includes(weather.value.weather_code),
    );
    const heroSrc = computed(() => {
      if (isRaining.value) return "assets/images/rainy.png";
      if (isSunny.value) return "assets/images/sunny.png";
      return "assets/images/hero.png";
    });

    return {
      store,
      icons,
      goWiki,
      goCalendar,
      goNews,
      goChat,
      onImgError,
      onImgLoad,
      onHeroError,
      isRaining,
      heroSrc,
    };
  },
  template: `
  <div class="main-panel home-panel">
    <div class="home-hero-wrap">
      <img class="home-hero-img" :src="heroSrc" alt="" @error="onHeroError" />

      <img class="home-sticker home-sticker-1" src="assets/images/sticker-1.png" alt=""
           style="--x: -6%; --y: 4%; --size: 40px; --rotate: -12deg; --delay: .2s"
           @error="onImgError" />
      <img class="home-sticker home-sticker-2" src="assets/images/sticker-2.png" alt=""
           style="--x: 92%; --y: 40%; --size: 36px; --rotate: 10deg; --delay: 1.4s"
           @error="onImgError" />
      <img class="home-sticker home-sticker-3" src="assets/images/sticker-3.png" alt=""
           style="--x: 6%; --y: 90%; --size: 44px; --rotate: -6deg; --delay: 2.4s"
           @error="onImgError" />

      <button class="home-float home-float-light" title="Toggle light / dark mode" @click="store.toggleTheme()">
        <span class="home-float-inner">
          <span class="home-float-fallback" v-html="store.theme === 'dark' ? icons.sun : icons.moon"></span>
          <img :src="store.theme === 'dark' ? 'assets/images/dark.png' : 'assets/images/light.png'" alt="" @error="onImgError" @load="onImgLoad" />
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

      <button class="home-float home-float-news" title="Check the news" @click="goNews">
        <span class="home-float-inner">
          <span class="home-float-fallback" v-html="icons.news"></span>
          <img src="assets/images/icon-news.png" alt="" @error="onImgError" />
        </span>
      </button>

      <button class="home-float home-float-weather" :class="{ 'home-float-weather-rain': isRaining }" title="Check today's weather" @click="goCalendar">
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
