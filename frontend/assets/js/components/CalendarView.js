const { ref, computed, onMounted } = window.Vue;
import { api } from "../api.js";
import { store } from "../store.js";
import { icons } from "../icons.js";

export default {
  setup() {
    // If the home page's note mini calendar asked to jump to a specific
    // date, open that date's month instead of the current month.
    const jumpDate = store.pendingCalendarDate;
    const initial = jumpDate ? new Date(jumpDate + "T00:00:00") : new Date();
    const today = new Date();
    const year = ref(initial.getFullYear());
    const month = ref(initial.getMonth() + 1);
    const counts = ref({});
    const monthNotes = ref({}); // dateStr -> [title, ...]

    const selectedDate = ref(null);
    const daySessions = ref([]);
    const dayWikiEntries = ref([]);
    const dayNotes = ref([]);

    // --- Weather (Taichung) for the selected day, top-right corner ---
    const weather = ref(null);
    const weatherLoading = ref(false);

    const cells = computed(() => {
      const first = new Date(year.value, month.value - 1, 1);
      const daysInMonth = new Date(year.value, month.value, 0).getDate();
      const startWeekday = first.getDay();
      const arr = [];
      for (let i = 0; i < startWeekday; i++) arr.push(null);
      for (let d = 1; d <= daysInMonth; d++) {
        const dateStr = `${year.value}-${String(month.value).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
        arr.push({ day: d, dateStr, isToday: dateStr === today.toISOString().slice(0, 10) });
      }
      return arr;
    });

    async function refresh() {
      store.calendarMonth = month.value;
      const res = await api.get(`/api/calendar?year=${year.value}&month=${month.value}`);
      counts.value = res.counts || {};
      monthNotes.value = res.notes || {};
      if (selectedDate.value) await selectDay(selectedDate.value);
    }

    async function selectDay(dateStr) {
      selectedDate.value = dateStr;
      weatherLoading.value = true;
      weather.value = null;

      const [dayRes, weatherRes] = await Promise.all([
        api.get(`/api/calendar/day?date_str=${dateStr}`),
        api.get(`/api/weather?date=${dateStr}`).catch(() => null),
      ]);

      daySessions.value = dayRes.sessions || [];
      dayWikiEntries.value = dayRes.wiki_entries || [];
      dayNotes.value = dayRes.notes || [];
      weather.value = weatherRes;
      weatherLoading.value = false;
    }

    function prevMonth() {
      month.value--;
      if (month.value < 1) { month.value = 12; year.value--; }
      refresh();
    }
    function nextMonth() {
      month.value++;
      if (month.value > 12) { month.value = 1; year.value++; }
      refresh();
    }

    function openSession(id) {
      store.view = "chat";
      store.selectSession(id);
    }

    function openWikiEntry(id) {
      store.view = "wiki";
      store.selectWikiEntry(id);
    }

    // 日曆頁只做資料呈現,不在頁面內開筆記 - 點了直接跳去 Notes 頁顯示,跟
    // openSession/openWikiEntry 同一套邏輯。
    function openNote(id) {
      store.view = "notes";
      store.openNoteView(id);
    }

    // Compact "2026/7/24 AM 11:05" style timestamp
    function fmtCompact(d) {
      const dt = new Date(d);
      const y = dt.getFullYear();
      const m = dt.getMonth() + 1;
      const day = dt.getDate();
      let h = dt.getHours();
      const ampm = h >= 12 ? "PM" : "AM";
      h = h % 12;
      if (h === 0) h = 12;
      const min = String(dt.getMinutes()).padStart(2, "0");
      return `${y}/${m}/${day} ${ampm} ${h}:${min}`;
    }

    const weatherHasData = computed(() => !!weather.value && weather.value.will_rain !== null);

    onMounted(async () => {
      await refresh();
      if (jumpDate) {
        await selectDay(jumpDate);
        store.pendingCalendarDate = null;
      }
    });

    return {
      store,
      year, month, counts, monthNotes, cells,
      selectedDate, daySessions, dayWikiEntries, dayNotes,
      weather, weatherLoading, weatherHasData,
      icons,
      refresh, selectDay, prevMonth, nextMonth, openSession, openWikiEntry, openNote,
      fmtCompact,
    };
  },
  template: `
  <div class="main-panel calendar-panel">
    <h1 class="page-title">CALENDAR</h1>
    <div class="row between">
      <div class="row">
        <button class="btn secondary" @click="prevMonth">‹</button>
        <h2>{{ year }}-{{ String(month).padStart(2,'0') }}</h2>
        <button class="btn secondary" @click="nextMonth">›</button>
      </div>

      <div v-if="selectedDate && (weatherLoading || weatherHasData)" class="weather-widget" :title="weather && weather.precipitation_probability != null ? 'Taichung · ' + weather.precipitation_probability + '% chance of rain' : 'Taichung'">
        <div v-if="weatherLoading" class="weather-icon"><span class="spinner"></span></div>
        <div v-else-if="weather.will_rain === true" class="weather-icon weather-rain">
          <span v-html="icons.cloud"></span>
          <span class="raindrop"></span><span class="raindrop"></span><span class="raindrop"></span>
        </div>
        <div v-else-if="[2, 3].includes(weather.weather_code)" class="weather-icon weather-cloudy">
          <span v-html="icons.cloud"></span>
        </div>
        <div v-else class="weather-icon weather-sunny">
          <span v-html="icons.sun"></span>
        </div>
        <span class="weather-label">Taichung</span>
      </div>
    </div>

    <div class="calendar-grid">
      <div v-for="d in ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']" :key="d" class="cal-dow">{{ d }}</div>
      <div v-for="(cell, i) in cells" :key="i"
           class="cal-cell" :class="{empty: !cell, today: cell && cell.isToday, selected: cell && cell.dateStr === selectedDate}"
           @click="cell && selectDay(cell.dateStr)">
        <template v-if="cell">
          <div class="cal-cell-top">
            <span>{{ cell.day }}</span>
            <span v-if="counts[cell.dateStr]" class="cal-count">{{ counts[cell.dateStr] }}</span>
          </div>
          <div class="cal-cell-notes" v-if="monthNotes[cell.dateStr] && monthNotes[cell.dateStr].length">
            <div v-for="t in monthNotes[cell.dateStr].slice(0, 2)" :key="t" class="cal-note-chip">{{ t }}</div>
            <div v-if="monthNotes[cell.dateStr].length > 2" class="cal-note-more">...</div>
          </div>
        </template>
      </div>
    </div>

    <div v-if="selectedDate" class="day-detail">
      <h3 class="day-detail-heading">Notes</h3>
      <div v-if="!dayNotes.length" class="hint">No notes on this day</div>
      <div v-for="n in dayNotes" :key="n.id" class="day-card clickable" :class="n.color ? 'note-color-' + n.color : ''" @click="openNote(n.id)">
        <div class="day-card-title">{{ n.title }}</div>
      </div>

      <h3 class="day-detail-heading">Conversations</h3>
      <div v-if="!daySessions.length" class="hint">No conversations created on this day</div>
      <div v-for="s in daySessions" :key="s.id" class="day-card clickable" @click="openSession(s.id)">
        <div class="day-card-title">{{ s.title }}</div>
        <div class="day-card-meta">Last Message: {{ fmtCompact(s.last_message_at) }}</div>
      </div>

      <template v-if="dayWikiEntries.length">
        <h3 class="day-detail-heading">Wiki</h3>
        <div v-for="w in dayWikiEntries" :key="w.id" class="day-card clickable" @click="openWikiEntry(w.id)">
          <div class="day-card-title">{{ w.title }}</div>
        </div>
      </template>
    </div>
  </div>
  `,
};
