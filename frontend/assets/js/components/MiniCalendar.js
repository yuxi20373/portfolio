const { ref, computed } = window.Vue;
import { store } from "../store.js";

export default {
  setup() {
    const today = new Date();
    const year = ref(today.getFullYear());
    const month = ref(today.getMonth() + 1); // 1-12
    const todayStr = today.toISOString().slice(0, 10);

    const daysWithSessions = computed(() => {
      const set = new Set();
      for (const s of store.sessions) set.add((s.created_at || "").slice(0, 10));
      return set;
    });

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
          hasSession: daysWithSessions.value.has(dateStr),
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
      store.toggleDateFilter(dateStr);
    }

    return { year, month, cells, prevMonth, nextMonth, pick, store };
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
            :class="{empty: !c, 'has-session': c && c.hasSession, today: c && c.isToday, selected: c && c.dateStr === store.dateFilter}"
            @click="c && pick(c.dateStr)">{{ c ? c.day : '' }}</span>
    </div>
    <div v-if="store.dateFilter" class="mini-cal-clear" @click="store.toggleDateFilter(store.dateFilter)">
      Clear date filter
    </div>
  </div>
  `,
};
