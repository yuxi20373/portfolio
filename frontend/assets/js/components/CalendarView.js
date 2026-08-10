const { ref, computed, onMounted } = window.Vue;
import { api } from "../api.js";
import { store } from "../store.js";
import { icons } from "../icons.js";
import { renderMarkdown } from "../markdown.js";

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
    const monthEvents = ref({}); // dateStr -> [{title, kind}, ...] - already excludes expired reminders, see routers/calendar.py

    const selectedDate = ref(null);
    const dayNotes = ref([]);
    const dayEvents = ref([]); // [{id, title, kind, remind_at, expired}, ...] - includes expired reminders (grayed out, sorted last)

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
      monthEvents.value = res.events || {};
      if (selectedDate.value) await selectDay(selectedDate.value);
    }

    async function selectDay(dateStr) {
      selectedDate.value = dateStr;
      store.closeNoteView();
      cancelAddEvent();
      weatherLoading.value = true;
      weather.value = null;

      const [dayRes, weatherRes] = await Promise.all([
        api.get(`/api/calendar/day?date_str=${dateStr}`),
        api.get(`/api/weather?date=${dateStr}`).catch(() => null),
      ]);

      dayNotes.value = dayRes.notes || [];
      dayEvents.value = dayRes.events || [];
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

    // 點 Notes 的小標題才會跳轉頁面;點裡面個別筆記只在本頁顯示內容(下面
    // 的 inline preview),不跳走。日曆頁不再顯示對話/wiki 了(只做資料
    // 呈現,集中看 Notes)。
    // 筆記預覽沿用 store.viewingNote(跟 Notes 頁、Sidebar 的 Favorites
    // 清單共用同一份狀態,見 store.openNoteView/closeNoteView)。
    function openNote(id) {
      store.openNoteView(id);
    }

    // --- Event / Reminder ---

    const showAddEvent = ref(false);
    const newEventTitle = ref("");
    const newEventKind = ref("event"); // "event" | "reminder"
    const newEventTime = ref(""); // "HH:MM",只有 reminder 用得到
    const savingEvent = ref(false);

    function toggleAddEvent() {
      showAddEvent.value = !showAddEvent.value;
      newEventTitle.value = "";
      newEventKind.value = "event";
      newEventTime.value = "";
    }

    function cancelAddEvent() {
      showAddEvent.value = false;
    }

    async function saveEvent() {
      if (!newEventTitle.value.trim() || !selectedDate.value) return;
      if (newEventKind.value === "reminder" && !newEventTime.value) return;
      savingEvent.value = true;
      try {
        const payload = {
          title: newEventTitle.value.trim(),
          kind: newEventKind.value,
          event_date: selectedDate.value,
        };
        if (newEventKind.value === "reminder") {
          payload.remind_at = `${selectedDate.value}T${newEventTime.value}:00`;
        }
        await store.createEvent(payload);
        store.showNotice(newEventKind.value === "event" ? "Event created" : "Reminder created");
        toggleAddEvent();
        await refresh(); // 月曆格子的小方框跟當天清單都要跟著更新
      } catch (err) {
        store.showNotice("Couldn't create", "error");
      } finally {
        savingEvent.value = false;
      }
    }

    async function removeEvent(id) {
      if (confirm("Delete this?")) {
        await store.deleteEvent(id);
        await refresh();
      }
    }

    // 還沒過期的(event 跟未過期 reminder)排前面,過期的 reminder 沉到最下面。
    const sortedDayEvents = computed(() => {
      return [...dayEvents.value].sort((a, b) => (a.expired === b.expired ? 0 : a.expired ? 1 : -1));
    });

    // "2026-08-10T14:30:00" -> "2:30 PM"
    function fmtEventTime(iso) {
      const dt = new Date(iso);
      let h = dt.getHours();
      const ampm = h >= 12 ? "PM" : "AM";
      h = h % 12;
      if (h === 0) h = 12;
      const min = String(dt.getMinutes()).padStart(2, "0");
      return `${h}:${min} ${ampm}`;
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
      year, month, counts, monthNotes, monthEvents, cells,
      selectedDate, dayNotes, dayEvents, sortedDayEvents,
      weather, weatherLoading, weatherHasData,
      icons, renderMarkdown,
      refresh, selectDay, prevMonth, nextMonth, openNote,
      showAddEvent, newEventTitle, newEventKind, newEventTime, savingEvent,
      toggleAddEvent, cancelAddEvent, saveEvent, removeEvent, fmtEventTime,
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
          <div class="cal-cell-notes" v-if="monthEvents[cell.dateStr] && monthEvents[cell.dateStr].length">
            <div v-for="(ev, idx) in monthEvents[cell.dateStr].slice(0, 2)" :key="idx" class="cal-event-chip" :class="ev.kind">{{ ev.title }}</div>
            <div v-if="monthEvents[cell.dateStr].length > 2" class="cal-note-more">...</div>
          </div>
        </template>
      </div>
    </div>

    <!-- 跟 .day-detail 平行(不放在它裡面)- 從側欄 Favorites 點筆記時,
         就算還沒選任何一天(selectedDate 是 null),預覽還是要顯示得出來。 -->
    <div v-if="store.loadingNoteView || store.viewingNote" class="cal-inline-preview">
      <div v-if="store.loadingNoteView" class="loading-row"><span class="spinner"></span> Loading…</div>
      <template v-else>
        <div class="note-detail-header">
          <h2>{{ store.viewingNote.title }}</h2>
          <button class="icon-btn" title="Close" @click="store.closeNoteView()" v-html="icons.close"></button>
        </div>
        <div v-if="store.viewingNote.tags && store.viewingNote.tags.length" class="tag-row">
          <span class="tag" v-for="t in store.viewingNote.tags" :key="t">{{ t }}</span>
        </div>
        <hr class="note-divider" />
        <div class="markdown-body" v-html="renderMarkdown(store.viewingNote.content)"></div>
      </template>
    </div>

    <div v-if="selectedDate" class="day-detail">
      <h3 class="day-detail-heading row between">
        <span>Events</span>
        <button class="icon-btn" title="Add event/reminder" @click="toggleAddEvent" v-html="icons.plus"></button>
      </h3>

      <div v-if="showAddEvent" class="note-editor">
        <input type="text" v-model="newEventTitle" class="note-editor-title-input" placeholder="Title" />
        <div class="row" style="gap:16px; margin-bottom:8px;">
          <label class="row" style="gap:4px;"><input type="radio" value="event" v-model="newEventKind" /> Event</label>
          <label class="row" style="gap:4px;"><input type="radio" value="reminder" v-model="newEventKind" /> Reminder</label>
        </div>
        <input v-if="newEventKind === 'reminder'" type="time" v-model="newEventTime" class="note-editor-title-input" style="max-width:160px;" />
        <div class="drawer-actions">
          <button class="btn" :disabled="savingEvent || !newEventTitle.trim() || (newEventKind === 'reminder' && !newEventTime)" @click="saveEvent">
            <span v-if="savingEvent" class="spinner"></span>{{ savingEvent ? ' Saving…' : 'Save' }}
          </button>
          <button class="btn secondary" :disabled="savingEvent" @click="cancelAddEvent">Cancel</button>
        </div>
      </div>

      <div v-if="!sortedDayEvents.length && !showAddEvent" class="hint">No events on this day</div>
      <div v-for="ev in sortedDayEvents" :key="ev.id" class="event-card" :class="[ev.kind, {expired: ev.expired}]">
        <span class="event-card-title">{{ ev.title }}</span>
        <span v-if="ev.kind === 'reminder' && ev.remind_at" class="event-card-time">{{ fmtEventTime(ev.remind_at) }}</span>
        <button class="mini-icon-btn" title="Delete" @click="removeEvent(ev.id)">×</button>
      </div>

      <h3 class="day-detail-heading clickable" title="Open the Notes page" @click="store.view = 'notes'">Notes</h3>
      <div v-if="!dayNotes.length" class="hint">No notes on this day</div>
      <div v-for="n in dayNotes" :key="n.id" class="day-card clickable" :class="n.color ? 'note-color-' + n.color : ''" @click="openNote(n.id)">
        <div class="day-card-title">{{ n.title }}</div>
      </div>
    </div>
  </div>
  `,
};
