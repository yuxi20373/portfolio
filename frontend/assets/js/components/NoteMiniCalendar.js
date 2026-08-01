const { ref, computed, onMounted, watch } = window.Vue;
import { api } from "../api.js";
import { store } from "../store.js";

// Same layout as MiniCalendar.js, but shows a dot for days with a note
// (instead of a bordered circle for days with a chat session), and clicking
// a day jumps to that date in the Calendar view instead of filtering chat.
export default {
  setup() {
    const today = new Date();
    const year = ref(today.getFullYear());
    const month = ref(today.getMonth() + 1); // 1-12
    const todayStr = today.toISOString().slice(0, 10);
    const notesByDay = ref({}); // dateStr -> [title, ...]

    async function loadMonth() {
      const res = await api.get(`/api/calendar?year=${year.value}&month=${month.value}`);
      notesByDay.value = res.notes || {};
    }

    const cells = computed(() => {
      const first = new Date(year.value, month.value - 1, 1);
      const daysInMonth = new Date(year.value, month.value, 0).getDate();
      const startWeekday = first.getDay();
      const arr = [];
      for (let i = 0; i < startWeekday; i++) arr.push(null);
      for (let d = 1; d <= daysInMonth; d++) {
        const dateStr = `${year.value}-${String(month.value).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
        arr.push({
          day: d,
          dateStr,
          hasNote: !!(notesByDay.value[dateStr] || []).length,
          isToday: dateStr === todayStr,
        });
      }
      return arr;
    });

    function prevMonth() {
      month.value--;
      if (month.value < 1) { month.value = 12; year.value--; }
    }
    function nextMonth() {
      month.value++;
      if (month.value > 12) { month.value = 1; year.value++; }
    }
    function pick(dateStr) {
      store.openCalendarDate(dateStr);
    }

    onMounted(loadMonth);
    watch([year, month], loadMonth);

    return { year, month, cells, prevMonth, nextMonth, pick };
  },
  template: `
  <div class="mini-calendar">
    <div class="mini-cal-header">
      <button class="mini-cal-nav" @click="prevMonth">‹</button>
      <span>{{ year }}-{{ String(month).padStart(2,'0') }}</span>
      <button class="mini-cal-nav" @click="nextMonth">›</button>
    </div>
    <div class="mini-cal-grid">
      <span v-for="d in ['S','M','T','W','T','F','S']" :key="d" class="mini-cal-dow">{{ d }}</span>
      <span v-for="(c, i) in cells" :key="i"
            class="mini-cal-day"
            :class="{empty: !c, today: c && c.isToday}"
            @click="c && pick(c.dateStr)">{{ c ? c.day : '' }}<span v-if="c && c.hasNote" class="mini-cal-dot"></span></span>
    </div>
  </div>
  `,
};
