const { ref, computed } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";
import { api } from "../api.js";

// Decorative stickers around the hero (see .home-sticker-wrap/.home-sticker
// in style.css). x/y/size are numbers (percent / px) rather than
// pre-built CSS strings so handlePointerMove below can do distance math
// against them directly.
// Stickers 1-3 have a dark-mode variant (darkSrc); sticker 4 doesn't, so it
// keeps its light-mode image in both themes. See stickerSrc() below.
const STICKERS = [
  { id: 1, src: "assets/images/sticker-1.png", darkSrc: "assets/images/sticker-1-dark.png", x: 80, y: -2, size: 192, rotate: -12, delay: 0.2 }, // 160 * 1.2
  { id: 2, src: "assets/images/sticker-2.png", darkSrc: "assets/images/sticker-2-dark.png", x: -14, y: 55, size: 144, rotate: 10, delay: 1.4 }, // 180 * 0.8
  { id: 3, src: "assets/images/sticker-3.png", darkSrc: "assets/images/sticker-3-dark.png", x: 40, y: 80, size: 176, rotate: -6, delay: 2.4 },
  { id: 4, src: "assets/images/sticker-4.png", x: 8, y: 40, size: 140, rotate: 14, delay: 3.2 },
];

// How close the pointer has to get (px, measured from the sticker's own
// anchor point) before it starts sliding away, and how far it slides at
// maximum closeness. Push strength ramps smoothly between the two.
const PROXIMITY_RADIUS = 110;
const PUSH_DISTANCE = 60;

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
    function stickerSrc(s) {
      return store.theme === "dark" && s.darkSrc ? s.darkSrc : s.src;
    }
    // Dark-mode sticker art reads much bigger than the light-mode originals
    // at the same --size, so it's shrunk to 40% of the light-mode size.
    function stickerSize(s) {
      return store.theme === "dark" && s.darkSrc ? s.size * 0.4 : s.size;
    }
    function onHeroError(e) {
      e.target.style.display = "none";
      e.target.parentElement.classList.add("home-hero-fallback");
    }

    // Today's weather - NOT fetched automatically. Nothing about the hero
    // or the weather float changes until the user clicks the weather float
    // (onWeatherClick below), which fetches once and then reveals it.
    const weather = ref(null);
    const weatherRevealed = ref(false);

    // Repeated clicks toggle: reveal the weather hero, then click again to
    // go back to the default (quokka) hero - doesn't refetch once weather
    // has already been loaded once.
    async function onWeatherClick() {
      if (weatherRevealed.value) {
        weatherRevealed.value = false;
        return;
      }
      if (!weather.value) {
        const d = new Date();
        const todayStr = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
        weather.value = await api.get(`/api/weather?date=${todayStr}`).catch(() => null);
      }
      weatherRevealed.value = true;
    }

    const isRaining = computed(() => weatherRevealed.value && !!weather.value && weather.value.will_rain === true);
    // WMO 0/1 = clear / mainly clear
    const isSunny = computed(
      () =>
        weatherRevealed.value &&
        !!weather.value &&
        !isRaining.value &&
        [0, 1].includes(weather.value.weather_code),
    );
    // Weather states win regardless of theme; otherwise the default (quokka)
    // hero has its own dark-mode variant, same idea as the stickers.
    const heroSrc = computed(() => {
      if (isRaining.value) return "assets/images/rainy.png";
      if (isSunny.value) return "assets/images/sunny.png";
      if (store.theme === "dark") return "assets/images/night.png";
      return "assets/images/hero.png";
    });

    // "Slide away when the pointer gets close" - pointermove covers mouse
    // hover AND touch-drag in one listener, but touch has no true
    // pre-contact "approaching" concept on the web (no event fires until
    // the finger actually lands and moves), so on mobile this triggers as
    // soon as a touch starts near a sticker rather than truly beforehand.
    const heroWrap = ref(null);
    const pushOffsets = ref(STICKERS.map(() => ({ x: 0, y: 0 })));

    function handlePointerMove(e) {
      const wrap = heroWrap.value;
      if (!wrap) return;
      const rect = wrap.getBoundingClientRect();
      const px = e.clientX - rect.left;
      const py = e.clientY - rect.top;

      STICKERS.forEach((s, i) => {
        const sx = (s.x / 100) * rect.width;
        const sy = (s.y / 100) * rect.height;
        const dx = sx - px;
        const dy = sy - py;
        const dist = Math.hypot(dx, dy) || 0.001;
        if (dist < PROXIMITY_RADIUS) {
          const strength = 1 - dist / PROXIMITY_RADIUS;
          pushOffsets.value[i] = { x: (dx / dist) * PUSH_DISTANCE * strength, y: (dy / dist) * PUSH_DISTANCE * strength };
        } else {
          pushOffsets.value[i] = { x: 0, y: 0 };
        }
      });
    }

    function resetPush() {
      pushOffsets.value = STICKERS.map(() => ({ x: 0, y: 0 }));
    }

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
      onWeatherClick,
      isRaining,
      heroSrc,
      stickers: STICKERS,
      stickerSrc,
      stickerSize,
      heroWrap,
      pushOffsets,
      handlePointerMove,
      resetPush,
    };
  },
  template: `
  <div class="main-panel home-panel">
    <div class="home-welcome">Welcome, {{ store.username }}</div>
    <div class="home-hero-wrap" ref="heroWrap" @pointermove="handlePointerMove" @pointerleave="resetPush">
      <img class="home-hero-img" :src="heroSrc" alt="" @error="onHeroError" />

      <span v-for="(s, i) in stickers" :key="s.id" class="home-sticker-wrap"
            :style="{ '--x': s.x + '%', '--y': s.y + '%', '--push-x': pushOffsets[i].x + 'px', '--push-y': pushOffsets[i].y + 'px' }">
        <img class="home-sticker" :src="stickerSrc(s)" alt=""
             :style="{ '--size': stickerSize(s) + 'px', '--rotate': s.rotate + 'deg', '--delay': s.delay + 's' }"
             @error="onImgError" @load="onImgLoad" />
      </span>

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

      <button class="home-float home-float-weather" :class="{ 'home-float-weather-rain': isRaining }" title="Check today's weather" @click="onWeatherClick">
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
