const { ref, computed, onMounted } = window.Vue;
import { api } from "../api.js";
import { store } from "../store.js";
import { icons } from "../icons.js";
import { renderMarkdown } from "../markdown.js";
import DrawerShell from "./DrawerShell.js";
import ColorPicker from "./ColorPicker.js";

const MARKDOWN_HELP = `
  <div><code># Heading</code></div>
  <div><code>**bold**</code> &nbsp; <code>*italic*</code></div>
  <div><code>- list item</code></div>
  <div><code>1. numbered item</code></div>
  <div><code>[text](url)</code></div>
  <div><code>\`inline code\`</code></div>
  <div><code>&gt; quote</code></div>
`;

export default {
  components: { DrawerShell, ColorPicker },
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

    // --- Add note panel ---
    const showAddNote = ref(false);
    const newNoteTitle = ref("");
    const newNoteContent = ref("");
    const newNoteTags = ref("");
    const newNoteColor = ref("");
    const newNotePreview = ref(false);
    const newNoteHelp = ref(false);
    const savingNote = ref(false);
    const newNoteTemplateId = ref("");

    // --- Note view: right-side drawer (state lives in store.js - viewingNote/
    // loadingNoteView - so Sidebar.js's Favorites list can open the same
    // drawer this component renders; see openNote/closeNote below) ---

    // --- Note edit (within the same drawer) ---
    const editingNote = ref(false);
    const editNoteTitle = ref("");
    const editNoteContent = ref("");
    const editNoteTags = ref("");
    const editNoteColor = ref("");
    const editNotePreview = ref(false);
    const editNoteHelp = ref(false);
    const savingNoteEdit = ref(false);

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
      showAddNote.value = false;

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

    function toggleAddNote() {
      showAddNote.value = !showAddNote.value;
      newNoteTitle.value = "";
      newNoteContent.value = "";
      newNoteTags.value = "";
      newNoteColor.value = "";
      newNotePreview.value = false;
      newNoteHelp.value = false;
      newNoteTemplateId.value = "";
    }

    // Prefills the draft content from a saved template (see the standalone
    // Notes page) - just a one-time copy, the note isn't linked back to it.
    function applyNoteTemplate() {
      const t = store.noteTemplates.find((x) => x.id === Number(newNoteTemplateId.value));
      if (!t) return;
      newNoteContent.value = t.content;
      if (t.tags && t.tags.length) newNoteTags.value = t.tags.join(", ");
    }

    async function saveNote() {
      if (!newNoteTitle.value.trim() || !selectedDate.value) return;
      savingNote.value = true;
      try {
        await api.post("/api/notes", {
          title: newNoteTitle.value.trim(),
          content: newNoteContent.value,
          tags: newNoteTags.value.split(",").map((t) => t.trim()).filter(Boolean),
          color: newNoteColor.value,
          date: selectedDate.value,
        });
        showAddNote.value = false;
        await refresh();
      } finally {
        savingNote.value = false;
      }
    }

    // Notes open in a right-side drawer (same visual pattern as the wiki
    // Adjust drawer) - the open/loading state lives in store.js so
    // Sidebar.js's calendar-branch Favorites list can open this same drawer.
    async function openNote(id) {
      editingNote.value = false;
      await store.openNoteView(id);
    }

    function closeNote() {
      store.closeNoteView();
      editingNote.value = false;
    }

    function startEditNote() {
      if (!store.viewingNote) return;
      editNoteTitle.value = store.viewingNote.title;
      editNoteContent.value = store.viewingNote.content;
      editNoteTags.value = (store.viewingNote.tags || []).join(", ");
      editNoteColor.value = store.viewingNote.color || "";
      editNotePreview.value = false;
      editNoteHelp.value = false;
      editingNote.value = true;
    }

    function cancelEditNote() {
      editingNote.value = false;
    }

    async function saveNoteEdit() {
      if (!store.viewingNote || !editNoteTitle.value.trim()) return;
      savingNoteEdit.value = true;
      try {
        await store.updateNote(store.viewingNote.id, {
          title: editNoteTitle.value.trim(),
          content: editNoteContent.value,
          tags: editNoteTags.value.split(",").map((t) => t.trim()).filter(Boolean),
          color: editNoteColor.value,
        });
        editingNote.value = false;
        await refresh(); // title may have changed - update month grid / day list too
      } finally {
        savingNoteEdit.value = false;
      }
    }

    async function removeNote() {
      if (!store.viewingNote) return;
      if (confirm(`Delete note "${store.viewingNote.title}"? This can't be undone.`)) {
        await store.deleteNote(store.viewingNote.id);
        closeNote();
        await refresh();
      }
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

    function fmtDateShort(d) {
      const dt = new Date(d);
      return `${dt.getFullYear()}/${dt.getMonth() + 1}/${dt.getDate()}`;
    }

    const weatherHasData = computed(() => !!weather.value && weather.value.will_rain !== null);

    onMounted(async () => {
      await refresh();
      if (jumpDate) {
        await selectDay(jumpDate);
        store.pendingCalendarDate = null;
      }
      if (!store.noteTemplates.length) store.loadNoteTemplates();
    });

    return {
      store,
      year, month, counts, monthNotes, cells,
      selectedDate, daySessions, dayWikiEntries, dayNotes,
      weather, weatherLoading, weatherHasData,
      showAddNote, newNoteTitle, newNoteContent, newNoteTags, newNoteColor, newNotePreview, newNoteHelp, savingNote,
      newNoteTemplateId, applyNoteTemplate,
      editingNote, editNoteTitle, editNoteContent, editNoteTags, editNoteColor, editNotePreview, editNoteHelp, savingNoteEdit,
      icons, renderMarkdown, MARKDOWN_HELP,
      refresh, selectDay, prevMonth, nextMonth, openSession, openWikiEntry,
      toggleAddNote, saveNote, openNote, closeNote,
      startEditNote, cancelEditNote, saveNoteEdit, removeNote,
      fmtCompact, fmtDateShort,
    };
  },
  template: `
  <div class="main-panel calendar-panel">
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
      <h3 class="day-detail-heading row between">
        <span>Notes</span>
        <button class="icon-btn" title="Add note" @click="toggleAddNote" v-html="icons.plus"></button>
      </h3>

      <div v-if="showAddNote" class="note-editor">
        <input type="text" v-model="newNoteTitle" class="note-editor-title-input" placeholder="Note title" />
        <div class="row" style="gap:8px; align-items:center; margin-bottom:8px;">
          <input type="text" v-model="newNoteTags" class="note-editor-title-input" style="flex:1; margin-bottom:0;" placeholder="Tags (comma separated)" />
          <ColorPicker v-model="newNoteColor" />
        </div>
        <div class="note-editor-toolbar">
          <select v-if="store.noteTemplates.length" class="note-template-select" v-model="newNoteTemplateId" @change="applyNoteTemplate">
            <option value="" disabled>Apply template…</option>
            <option v-for="t in store.noteTemplates" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <button class="icon-btn" title="Preview" :class="{active: newNotePreview}" @click="newNotePreview = !newNotePreview" v-html="icons.eye"></button>
          <div class="note-help-wrap">
            <button class="icon-btn" title="Markdown syntax help" @click="newNoteHelp = !newNoteHelp">?</button>
            <div v-if="newNoteHelp" class="note-help-popover" v-html="MARKDOWN_HELP"></div>
          </div>
        </div>
        <textarea v-if="!newNotePreview" v-model="newNoteContent" class="note-editor-textarea" rows="10"
                  placeholder="Write your note in Markdown…"></textarea>
        <div v-else class="markdown-body note-editor-preview" v-html="renderMarkdown(newNoteContent)"></div>
        <button class="btn" :disabled="savingNote || !newNoteTitle.trim()" @click="saveNote">
          <span v-if="savingNote" class="spinner"></span>{{ savingNote ? ' Saving…' : 'Save note' }}
        </button>
      </div>

      <div v-if="!showAddNote && !dayNotes.length" class="hint">No notes on this day</div>
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

    <!-- Note view, right-side drawer (100vw full-page on mobile - see
         .drawer-panel's mobile override in style.css): plain view, edit,
         or delete. viewingNote lives in store.js so Sidebar.js's calendar
         Favorites list can open the same drawer. -->
    <DrawerShell v-if="store.loadingNoteView || store.viewingNote" title="Note" wide @close="closeNote">
      <div v-if="store.loadingNoteView" class="loading-row"><span class="spinner"></span> Loading…</div>

      <template v-else-if="store.viewingNote">
        <div v-if="editingNote" class="note-editor">
          <input type="text" v-model="editNoteTitle" class="note-editor-title-input" placeholder="Note title" />
          <div class="row" style="gap:8px; align-items:center; margin-bottom:8px;">
            <input type="text" v-model="editNoteTags" class="note-editor-title-input" style="flex:1; margin-bottom:0;" placeholder="Tags (comma separated)" />
            <ColorPicker v-model="editNoteColor" />
          </div>
          <div class="note-editor-toolbar">
            <button class="icon-btn" title="Preview" :class="{active: editNotePreview}" @click="editNotePreview = !editNotePreview" v-html="icons.eye"></button>
            <div class="note-help-wrap">
              <button class="icon-btn" title="Markdown syntax help" @click="editNoteHelp = !editNoteHelp">?</button>
              <div v-if="editNoteHelp" class="note-help-popover" v-html="MARKDOWN_HELP"></div>
            </div>
          </div>
          <textarea v-if="!editNotePreview" v-model="editNoteContent" class="note-editor-textarea" rows="10"></textarea>
          <div v-else class="markdown-body note-editor-preview" v-html="renderMarkdown(editNoteContent)"></div>
          <div class="drawer-actions">
            <button class="btn" :disabled="savingNoteEdit || !editNoteTitle.trim()" @click="saveNoteEdit">
              <span v-if="savingNoteEdit" class="spinner"></span>{{ savingNoteEdit ? ' Saving…' : 'Save' }}
            </button>
            <button class="btn secondary" :disabled="savingNoteEdit" @click="cancelEditNote">Cancel</button>
          </div>
        </div>

        <div v-else class="note-detail">
          <div class="note-detail-header">
            <h2>{{ store.viewingNote.title }}</h2>
            <div class="note-detail-actions">
              <button class="icon-btn" title="Edit" @click="startEditNote" v-html="icons.edit"></button>
              <button class="icon-btn favorite-btn" :class="{active: store.viewingNote.is_favorited}" title="Favorite"
                      @click="store.toggleNoteFavorite(store.viewingNote.id)"
                      v-html="store.viewingNote.is_favorited ? icons.bookmarkFilled : icons.bookmark"></button>
              <button class="icon-btn" title="Delete" @click="removeNote" v-html="icons.trash"></button>
            </div>
          </div>
          <div class="note-detail-date">{{ fmtDateShort(store.viewingNote.created_at) }}</div>
          <div v-if="store.viewingNote.tags && store.viewingNote.tags.length" class="tag-row">
            <span class="tag" v-for="t in store.viewingNote.tags" :key="t">{{ t }}</span>
          </div>
          <hr class="note-divider" />
          <div class="markdown-body" v-html="renderMarkdown(store.viewingNote.content)"></div>
        </div>
      </template>
    </DrawerShell>
  </div>
  `,
};
