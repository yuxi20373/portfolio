const { ref, computed, nextTick, onMounted } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";
import MiniCalendar from "./MiniCalendar.js";
import NoteMiniCalendar from "./NoteMiniCalendar.js";

export default {
  components: { MiniCalendar, NoteMiniCalendar },
  setup() {
    const editingId = ref(null);
    const editingTitle = ref("");
    const expandedGroups = ref(new Set()); // membership = collapsed

    const editingFolderId = ref(null);
    const editingFolderName = ref("");
    const movingEntryId = ref(null);

    const notesFavoritesOpen = ref(false);

    onMounted(() => {
      store.loadWikiFolders();
      store.loadMemoItems();
    });

    // --- Memo checklist(首頁側欄,桌機限定 - 手機版首頁本來就沒有側欄可看)---
    const addingMemo = ref(false);
    const newMemoText = ref("");

    function startAddMemo() {
      addingMemo.value = true;
      newMemoText.value = "";
    }

    async function confirmAddMemo() {
      const text = newMemoText.value.trim();
      addingMemo.value = false;
      if (text) await store.createMemoItem(text);
    }

    function cancelAddMemo() {
      addingMemo.value = false;
    }

    // Same graceful-fallback pattern as HomeView.js's decorative images -
    // if the PNG isn't there yet, just hide the broken <img>.
    function onIconError(e) {
      e.target.style.display = "none";
    }

    async function toggleNotesFavorites() {
      notesFavoritesOpen.value = !notesFavoritesOpen.value;
      if (notesFavoritesOpen.value) await store.loadFavoritedNotes();
    }

    // "2026-08-05" -> "2026/8/5"
    function fmtDateLabel(dateStr) {
      const [y, m, d] = dateStr.split("-").map(Number);
      return `${y}/${m}/${d}`;
    }

    function setView(v) {
      store.view = v;
      store.closeSidebar(); // no-op on desktop; closes the mobile drawer after navigating
      if (v === "wiki") {
        if (store.wikiEntries.length === 0) store.loadWikiEntries();
        if (store.wikiFolders.length === 0) store.loadWikiFolders();
      }
      if (v === "news" && store.newsSources.length === 0) store.loadNewsSources();
      if (v === "notes") {
        store.loadAllNotes();
        if (!store.noteTemplates.length) store.loadNoteTemplates();
        if (!store.noteTags.length) store.loadNoteTags();
        store.templateManageOpen = false;
      }
    }

    function onSearchInput(e) {
      store.runSearch(e.target.value);
    }

    async function startRename(s) {
      editingId.value = s.id;
      editingTitle.value = s.title;
      await nextTick();
      const el = document.getElementById("rename-input-" + s.id);
      if (el) el.focus();
    }

    async function confirmRename() {
      const id = editingId.value;
      const title = editingTitle.value.trim();
      editingId.value = null;
      if (id != null && title) {
        await store.renameSession(id, title);
      }
    }

    function cancelRename() {
      editingId.value = null;
    }

    async function removeSession(s) {
      if (confirm(`Delete "${s.title}"? This can't be undone.`)) {
        await store.deleteSession(s.id);
      }
    }

    // Group wiki entries by user-created folder (never LLM-assigned). Every
    // folder is always shown, even empty, so there's somewhere to move
    // entries into; "Uncategorized" is the catch-all for entries with no folder.
    const wikiGroups = computed(() => {
      const byFolder = {};
      for (const w of store.visibleWikiEntries) {
        const key = w.folder_id != null ? w.folder_id : "uncategorized";
        if (!byFolder[key]) byFolder[key] = [];
        byFolder[key].push(w);
      }
      const groups = store.wikiFolders.map((f) => ({
        key: "f" + f.id,
        id: f.id,
        label: f.name,
        entries: byFolder[f.id] || [],
      }));
      groups.push({
        key: "uncategorized",
        id: null,
        label: "Uncategorized",
        entries: byFolder["uncategorized"] || [],
      });
      return groups;
    });

    function toggleGroup(key) {
      const s = new Set(expandedGroups.value);
      if (s.has(key)) s.delete(key);
      else s.add(key);
      expandedGroups.value = s;
    }
    function groupCollapsed(key) {
      return expandedGroups.value.has(key);
    }

    async function promptNewFolder() {
      const name = prompt("Folder name");
      if (name && name.trim()) {
        await store.createWikiFolder(name.trim());
      }
    }

    // Template 的列表/新增/編輯/刪除現在都在主畫面的 Template Manage 畫面裡
    // (見 NotesView.js),這個按鈕只是負責打開它。
    function openTemplateManage() {
      store.templateManageOpen = true;
      store.viewingTemplate = null;
    }

    async function startFolderRename(group) {
      editingFolderId.value = group.id;
      editingFolderName.value = group.label;
      await nextTick();
      const el = document.getElementById("folder-rename-" + group.id);
      if (el) el.focus();
    }

    async function confirmFolderRename() {
      const id = editingFolderId.value;
      const name = editingFolderName.value.trim();
      editingFolderId.value = null;
      if (id != null && name) {
        await store.renameWikiFolder(id, name);
      }
    }

    function cancelFolderRename() {
      editingFolderId.value = null;
    }

    async function removeFolder(group) {
      if (confirm(`Delete folder "${group.label}"? Entries inside will become Uncategorized, not deleted.`)) {
        await store.deleteWikiFolder(group.id);
      }
    }

    function toggleMoveMenu(entryId) {
      movingEntryId.value = movingEntryId.value === entryId ? null : entryId;
    }

    async function doMove(entryId, folderId) {
      movingEntryId.value = null;
      await store.moveWikiEntry(entryId, folderId);
    }

    // Pinned sources first (stable order otherwise) - see the pin icon in the source row.
    const sortedNewsSources = computed(() => {
      return [...store.newsSources].sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));
    });

    return {
      store,
      icons,
      editingId,
      editingTitle,
      setView,
      onSearchInput,
      startRename,
      confirmRename,
      cancelRename,
      removeSession,
      wikiGroups,
      toggleGroup,
      groupCollapsed,
      promptNewFolder,
      openTemplateManage,
      editingFolderId,
      editingFolderName,
      startFolderRename,
      confirmFolderRename,
      cancelFolderRename,
      removeFolder,
      movingEntryId,
      toggleMoveMenu,
      doMove,
      sortedNewsSources,
      onIconError,
      notesFavoritesOpen,
      toggleNotesFavorites,
      fmtDateLabel,
      addingMemo,
      newMemoText,
      startAddMemo,
      confirmAddMemo,
      cancelAddMemo,
    };
  },
  template: `
  <aside class="sidebar" :class="{open: store.sidebarOpen}">
    <div class="icon-nav">
      <button class="icon-btn icon-btn-home" :class="{active: store.view==='home'}" @click="setView('home')" title="Home">
        <span v-html="icons.home"></span>
        <img src="assets/images/home.png" alt="" @error="onIconError" />
      </button>
      <button class="icon-btn" :class="{active: store.view==='chat'}" @click="setView('chat')" title="Chat" v-html="icons.chat"></button>
      <button class="icon-btn" :class="{active: store.view==='wiki'}" @click="setView('wiki')" title="Knowledge base" v-html="icons.wiki"></button>
      <button class="icon-btn" :class="{active: store.view==='calendar'}" @click="setView('calendar')" title="Calendar" v-html="icons.calendar"></button>
      <button class="icon-btn" :class="{active: store.view==='notes'}" @click="setView('notes')" title="Notes" v-html="icons.notes"></button>
      <button class="icon-btn" :class="{active: store.view==='news'}" @click="setView('news')" title="News" v-html="icons.news"></button>
    </div>

    <template v-if="store.view === 'chat'">
      <div class="search-box">
        <span class="search-icon" v-html="icons.search"></span>
        <input type="text" placeholder="Search conversations…" :value="store.searchQuery" @input="onSearchInput" />
        <button v-if="store.searchQuery" class="clear-search" @click="store.clearSearch()">×</button>
      </div>

      <div class="session-item favorites-row" :class="{active: store.sessionFavoritesOnly}"
           @click="store.sessionFavoritesOnly = !store.sessionFavoritesOnly">
        <span class="favorites-row-icon">
          <span v-html="icons.bookmarkFilled"></span>
          <img src="assets/images/star.png" alt="" @error="onIconError" />
        </span>
        <span class="session-title favorites-row-label">Favorites</span>
      </div>

      <button class="icon-btn new-item-btn" title="New conversation" @click="store.newSession()" v-html="icons.plus"></button>

      <div class="session-list">
        <div v-if="store.searching" class="hint">Searching…</div>
        <div v-for="s in store.visibleSessions" :key="s.id"
             class="session-item" :class="{active: s.id === store.currentSessionId}">
          <template v-if="editingId === s.id">
            <input class="session-rename-input"
                   :id="'rename-input-' + s.id"
                   v-model="editingTitle"
                   @keydown.enter.prevent="confirmRename"
                   @keydown.esc.prevent="cancelRename"
                   @blur="confirmRename"
                   @click.stop />
          </template>
          <template v-else>
            <span class="session-title" @click="store.selectSession(s.id)">{{ s.title }}</span>
            <span class="session-actions">
              <button class="mini-icon-btn" :class="{active: s.is_favorited}" title="Favorite" @click.stop="store.toggleSessionFavorite(s.id)" v-html="s.is_favorited ? icons.bookmarkFilled : icons.bookmark"></button>
              <button class="mini-icon-btn" title="Rename" @click.stop="startRename(s)" v-html="icons.edit"></button>
              <button class="mini-icon-btn" title="Delete" @click.stop="removeSession(s)" v-html="icons.trash"></button>
            </span>
          </template>
        </div>
        <div v-if="!store.searching && !store.visibleSessions.length" class="hint">No conversations</div>
      </div>

      <MiniCalendar />
    </template>

    <template v-else-if="store.view === 'wiki'">
      <div class="search-box wiki-search-box">
        <span class="search-icon" v-html="icons.search"></span>
        <input type="text" placeholder="Search wiki entries…" v-model="store.wikiSearchQuery" />
        <button v-if="store.wikiSearchQuery" class="clear-search" @click="store.wikiSearchQuery = ''">×</button>
      </div>

      <div class="session-item favorites-row" :class="{active: store.wikiFavoritesOnly}"
           @click="store.wikiFavoritesOnly = !store.wikiFavoritesOnly">
        <span class="favorites-row-icon">
          <span v-html="icons.bookmarkFilled"></span>
          <img src="assets/images/star.png" alt="" @error="onIconError" />
        </span>
        <span class="session-title favorites-row-label">Favorites</span>
      </div>

      <button class="icon-btn new-item-btn" title="New folder" @click="promptNewFolder" v-html="icons.plus"></button>

      <div class="wiki-list">
        <div v-for="group in wikiGroups" :key="group.key" class="wiki-group">
          <div class="wiki-group-header" @click="toggleGroup(group.key)">
            <span class="wiki-group-chevron" :class="{collapsed: groupCollapsed(group.key)}">▾</span>
            <template v-if="editingFolderId === group.id && group.id != null">
              <input class="session-rename-input"
                     :id="'folder-rename-' + group.id"
                     v-model="editingFolderName"
                     @keydown.enter.prevent="confirmFolderRename"
                     @keydown.esc.prevent="cancelFolderRename"
                     @blur="confirmFolderRename"
                     @click.stop />
            </template>
            <template v-else>
              <span class="wiki-group-label">{{ group.label }}</span>
            </template>
            <span class="wiki-group-count">{{ group.entries.length }}</span>
            <span v-if="group.id != null" class="wiki-group-actions" @click.stop>
              <button class="mini-icon-btn" title="Rename folder" @click="startFolderRename(group)" v-html="icons.edit"></button>
              <button class="mini-icon-btn" title="Delete folder" @click="removeFolder(group)" v-html="icons.trash"></button>
            </span>
          </div>

          <div v-show="!groupCollapsed(group.key)">
            <div v-for="w in group.entries" :key="w.id"
                 class="wiki-item" :class="{active: w.id === store.currentWikiId}">
              <span class="wiki-item-icon" v-html="icons.doc"></span>
              <span class="wiki-item-title" @click="store.selectWikiEntry(w.id)">{{ w.title }}</span>
              <span class="wiki-item-actions">
                <button class="mini-icon-btn" :class="{active: w.is_favorited}" title="Favorite" @click.stop="store.toggleWikiEntryFavorite(w.id)" v-html="w.is_favorited ? icons.bookmarkFilled : icons.bookmark"></button>
                <div class="move-wrap">
                  <button class="mini-icon-btn" title="Move to folder" @click.stop="toggleMoveMenu(w.id)" v-html="icons.move"></button>
                  <div v-if="movingEntryId === w.id" class="move-popover" @click.stop>
                    <div v-if="!store.wikiFolders.length" class="hint">No folders yet</div>
                    <div v-for="f in store.wikiFolders" :key="f.id" class="move-popover-item" @click="doMove(w.id, f.id)">{{ f.name }}</div>
                    <div class="move-popover-item" @click="doMove(w.id, null)">Uncategorized</div>
                  </div>
                </div>
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <template v-else-if="store.view === 'notes'">
      <div class="session-list">
        <div class="session-item favorites-row" :class="{active: store.templateManageOpen}" @click="openTemplateManage">
          <span class="favorites-row-icon">
            <span v-html="icons.doc"></span>
            <img src="assets/images/manager.png" alt="" @error="onIconError" />
          </span>
          <span class="session-title favorites-row-label">Manage</span>
        </div>

        <div class="session-item favorites-row" :class="{active: notesFavoritesOpen}" @click="toggleNotesFavorites">
          <span class="favorites-row-icon">
            <span v-html="icons.bookmarkFilled"></span>
            <img src="assets/images/star.png" alt="" @error="onIconError" />
          </span>
          <span class="session-title favorites-row-label">Favorites</span>
        </div>

        <template v-if="notesFavoritesOpen">
          <template v-for="group in store.favoritedNotesByDate" :key="group.date">
            <div class="notes-favorites-date">{{ fmtDateLabel(group.date) }}</div>
            <div v-for="n in group.notes" :key="n.id" class="session-item" @click="store.openNoteView(n.id)">
              <span v-if="n.color" class="note-color-dot" :class="'note-color-' + n.color"></span>
              <span class="session-title">{{ n.title }}</span>
            </div>
          </template>
          <div v-if="!store.favoritedNotesByDate.length" class="hint">No favorited notes yet</div>
        </template>
      </div>
    </template>

    <template v-else-if="store.view === 'news'">
      <div class="session-list">
        <div class="session-item favorites-row" :class="{active: store.newsSelectedSource === '__favorites__'}"
             @click="store.selectNewsSource('__favorites__')">
          <span class="favorites-row-icon">
            <span v-html="icons.bookmarkFilled"></span>
            <img src="assets/images/star.png" alt="" @error="onIconError" />
          </span>
          <span class="session-title favorites-row-label">Favorites</span>
        </div>

        <div v-for="s in sortedNewsSources" :key="s.key"
             class="session-item" :class="{active: s.key === store.newsSelectedSource}"
             @click="store.selectNewsSource(s.key)">
          <span class="session-title">{{ s.name }}</span>
          <button class="mini-icon-btn" :class="{active: s.pinned}" :title="s.pinned ? 'Unpin' : 'Pin to top'" @click.stop="store.toggleNewsSourcePin(s.key)" v-html="s.pinned ? icons.pinFilled : icons.pin"></button>
          <span class="schedule-toggle-wrap" :title="s.enabled ? 'Daily auto-scrape: on' : 'Daily auto-scrape: off'" @click.stop>
            <span class="schedule-toggle-icon" v-html="icons.clock"></span>
            <button class="schedule-switch" :class="{on: s.enabled}" @click="store.toggleNewsSourceSchedule(s.key)">
              <span class="schedule-switch-knob"></span>
            </button>
          </span>
        </div>
        <div v-if="!store.newsSources.length" class="hint">Loading sources…</div>
      </div>
    </template>

    <template v-else-if="store.view === 'calendar'">
      <div class="session-list">
        <div class="session-item favorites-row" :class="{active: notesFavoritesOpen}" @click="toggleNotesFavorites">
          <span class="favorites-row-icon">
            <span v-html="icons.bookmarkFilled"></span>
            <img src="assets/images/star.png" alt="" @error="onIconError" />
          </span>
          <span class="session-title favorites-row-label">Favorites</span>
        </div>

        <template v-if="notesFavoritesOpen">
          <template v-for="group in store.favoritedNotesByDate" :key="group.date">
            <div class="notes-favorites-date">{{ fmtDateLabel(group.date) }}</div>
            <div v-for="n in group.notes" :key="n.id" class="session-item" @click="store.openNoteView(n.id)">
              <span v-if="n.color" class="note-color-dot" :class="'note-color-' + n.color"></span>
              <span class="session-title">{{ n.title }}</span>
            </div>
          </template>
          <div v-if="!store.favoritedNotesByDate.length" class="hint">No favorited notes yet</div>
        </template>
      </div>
    </template>

    <template v-else-if="store.view === 'home'">
      <div class="memo-box">
        <div class="memo-box-title row between">
          <span>Memo</span>
          <button v-if="!addingMemo" class="icon-btn" title="Add item" @click="startAddMemo" v-html="icons.plus"></button>
        </div>

        <div v-for="m in store.memoItems" :key="m.id" class="memo-item">
          <label class="memo-checkbox">
            <input type="checkbox" :checked="m.done" @change="store.toggleMemoItem(m.id)" />
            <span class="memo-checkbox-box"></span>
          </label>
          <span class="memo-text" :class="{done: m.done}">{{ m.text }}</span>
          <button class="mini-icon-btn" title="Delete" @click="store.deleteMemoItem(m.id)">×</button>
        </div>

        <input v-if="addingMemo" type="text" v-model="newMemoText" class="session-rename-input memo-input"
               placeholder="New memo…" autofocus
               @keydown.enter.prevent="confirmAddMemo" @keydown.esc.prevent="cancelAddMemo" @blur="confirmAddMemo" />
      </div>

      <div class="home-sidebar-spacer"></div>
      <NoteMiniCalendar />
    </template>
  </aside>
  `,
};
