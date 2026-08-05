const { reactive } = window.Vue;
import { api } from "./api.js";

export const store = reactive({
  // login: token has no expiry (see backend/app/models/auth.py) - it's
  // valid until logout() explicitly deletes it, so staying logged in
  // across reloads/devices is just "is there a token in localStorage".
  loggedIn: !!localStorage.getItem("auth_token"),
  username: localStorage.getItem("auth_username") || null,

  // view: "home" | "chat" | "wiki" | "calendar" | "news"
  view: "home",

  // Mobile-only drawer state for the sidebar (see the hamburger button in
  // app.js and the "open" class on .sidebar in style.css). Meaningless on
  // desktop - the sidebar is always visible there regardless of this flag.
  sidebarOpen: false,

  // light/dark mode, persisted to localStorage (this is a real deployed
  // site, not a sandboxed preview, so localStorage is the right tool here)
  theme: "light",

  // chat
  sessions: [],
  currentSessionId: null,
  messages: [],
  sending: false,
  loadingMessages: false,
  models: [], // catalog from GET /api/models, recommended one first (see model_catalog.py)

  // sidebar filters (conversations)
  dateFilter: null, // "YYYY-MM-DD" | null
  sessionFavoritesOnly: false,

  // Set by the home page's mini calendar (see NoteMiniCalendar.js) to tell
  // CalendarView which date to jump to and select on mount; cleared once consumed.
  pendingCalendarDate: null,
  searchQuery: "",
  searchResultIds: null, // null = no active search
  searching: false,

  // wiki
  wikiEntries: [],
  currentWikiId: null,
  currentWikiEntry: null,
  wikiSearchQuery: "",
  wikiFolders: [], // user-created folders (manual organization, not LLM-assigned)
  wikiFavoritesOnly: false,

  // notes (calendar page's sidebar "Favorites" list, and the shared
  // note-viewing drawer - see CalendarView.js and Sidebar.js's calendar branch)
  favoritedNotes: [], // flat list, newest first - grouped by date in the sidebar
  viewingNote: null,
  loadingNoteView: false,
  noteTemplates: [],
  noteTags: [],
  allNotes: [], // standalone Notes page's full list (see loadAllNotes)
  notesTagFilter: null, // tag name | null - standalone Notes page's filter

  // news
  newsSources: [], // [{key, name, enabled, pinned}, ...]
  newsSelectedSource: null, // key of the source currently shown, or "__favorites__"
  newsOverview: null, // { featured_date, featured: [...], other_days: [{date, articles}] }
  newsWeek: null, // { start, end, days: [{date, articles}] } - set when browsing a specific week instead of the default recent timeline
  newsLoading: false,
  newsFeaturedIndex: 0,
  newsCurrentArticle: null,
  newsArticleLoading: false,
  newsArticleSiblings: [], // ids of the same day's articles, for detail-view prev/next

  get currentSession() {
    return this.sessions.find((s) => s.id === this.currentSessionId) || null;
  },

  get visibleSessions() {
    let list = this.sessions;
    if (this.searchResultIds !== null) {
      const order = this.searchResultIds;
      list = list.filter((s) => order.includes(s.id));
      list = [...list].sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));
    }
    if (this.dateFilter) {
      list = list.filter((s) => (s.created_at || "").slice(0, 10) === this.dateFilter);
    }
    if (this.sessionFavoritesOnly) {
      list = list.filter((s) => s.is_favorited);
    }
    return list;
  },

  // Plain text match (title/tags), not semantic - separate from conversation search
  get visibleWikiEntries() {
    let list = this.wikiEntries;
    const q = this.wikiSearchQuery.trim().toLowerCase();
    if (q) {
      list = list.filter(
        (w) => w.title.toLowerCase().includes(q) || (w.tags || []).some((t) => t.toLowerCase().includes(q))
      );
    }
    if (this.wikiFavoritesOnly) {
      list = list.filter((w) => w.is_favorited);
    }
    return list;
  },

  // dateStr -> [note, ...], newest date first - for the calendar sidebar's
  // date-grouped, separator-divided Favorites list (see Sidebar.js).
  get favoritedNotesByDate() {
    const groups = {};
    const order = [];
    for (const n of this.favoritedNotes) {
      const d = (n.created_at || "").slice(0, 10);
      if (!groups[d]) {
        groups[d] = [];
        order.push(d);
      }
      groups[d].push(n);
    }
    return order.map((date) => ({ date, notes: groups[date] }));
  },

  async loadSessions() {
    this.sessions = await api.get("/api/sessions");
  },

  async selectSession(id) {
    this.currentSessionId = id;
    this.loadingMessages = true;
    this.sidebarOpen = false; // no-op on desktop; closes the mobile drawer after picking one
    try {
      this.messages = await api.get(`/api/sessions/${id}/messages`);
    } finally {
      this.loadingMessages = false;
    }
  },

  async newSession() {
    const s = await api.post("/api/sessions", {});
    await this.loadSessions();
    await this.selectSession(s.id);
  },

  async renameSession(id, title) {
    await api.patch(`/api/sessions/${id}`, { title });
    await this.loadSessions();
  },

  async toggleSessionFavorite(id) {
    const s = this.sessions.find((x) => x.id === id);
    if (!s) return;
    const next = !s.is_favorited;
    await api.patch(`/api/sessions/${id}/favorite`, { favorited: next });
    s.is_favorited = next;
  },

  async loadModels() {
    this.models = await api.get("/api/models");
  },

  async switchModel(id, modelId) {
    await api.patch(`/api/sessions/${id}`, { model: modelId });
    await this.loadSessions();
  },

  async deleteSession(id) {
    await api.del(`/api/sessions/${id}`);
    if (this.currentSessionId === id) {
      this.currentSessionId = null;
      this.messages = [];
    }
    await this.loadSessions();
  },

  async sendMessage(text) {
    if (!text.trim()) return;
    if (!this.currentSessionId) await this.newSession();
    this.messages.push({ id: "tmp-" + Date.now(), role: "user", content: text });
    this.sending = true;
    try {
      await api.post(`/api/sessions/${this.currentSessionId}/chat`, { message: text });
      this.messages = await api.get(`/api/sessions/${this.currentSessionId}/messages`);
      await this.loadSessions();
    } catch (e) {
      this.messages.push({ id: "err-" + Date.now(), role: "assistant", content: "Error: " + e.message });
    } finally {
      this.sending = false;
    }
  },

  async runSearch(query) {
    this.searchQuery = query;
    if (!query.trim()) {
      this.searchResultIds = null;
      return;
    }
    this.searching = true;
    try {
      const res = await api.post("/api/search", { query });
      this.searchResultIds = res.session_ids || [];
    } finally {
      this.searching = false;
    }
  },

  clearSearch() {
    this.searchQuery = "";
    this.searchResultIds = null;
  },

  toggleDateFilter(dateStr) {
    this.dateFilter = this.dateFilter === dateStr ? null : dateStr;
  },

  openCalendarDate(dateStr) {
    this.pendingCalendarDate = dateStr;
    this.view = "calendar";
    this.sidebarOpen = false;
  },

  async loadWikiEntries() {
    this.wikiEntries = await api.get("/api/wiki");
  },

  async selectWikiEntry(id) {
    this.currentWikiId = id;
    this.sidebarOpen = false;
    this.currentWikiEntry = await api.get(`/api/wiki/${id}`);
  },

  async deleteWikiEntry(id) {
    await api.del(`/api/wiki/${id}`);
    if (this.currentWikiId === id) {
      this.currentWikiId = null;
      this.currentWikiEntry = null;
    }
    await this.loadWikiEntries();
  },

  // keyword: search-engine-style terms. question: what the user wants to know & save.
  async searchIntoWiki(keyword, question) {
    const entry = await api.post("/api/wiki/search", { keyword, question });
    await this.loadWikiEntries();
    this.currentWikiId = entry.id;
    this.currentWikiEntry = entry;
  },

  // Applies an already-approved draft from the Adjust drawer (preview call
  // itself goes straight through api.js since it's transient, per-drawer state)
  async applyWikiAdjustment(id, summary, content) {
    this.currentWikiEntry = await api.post(`/api/wiki/${id}/adjust/apply`, { summary, content });
    await this.loadWikiEntries();
  },

  // Direct manual edit - no LLM involved. `patch` is any subset of
  // {title, entry_type, summary, content, tags}.
  async updateWikiEntry(id, patch) {
    this.currentWikiEntry = await api.patch(`/api/wiki/${id}`, patch);
    await this.loadWikiEntries();
  },

  async toggleWikiEntryFavorite(id) {
    const w = this.wikiEntries.find((x) => x.id === id);
    const next = !(w ? w.is_favorited : this.currentWikiEntry && this.currentWikiEntry.is_favorited);
    await api.patch(`/api/wiki/${id}/favorite`, { favorited: next });
    if (w) w.is_favorited = next;
    if (this.currentWikiEntry && this.currentWikiEntry.id === id) this.currentWikiEntry.is_favorited = next;
  },

  // --- Folders: user-created, manual organization only ---

  async loadWikiFolders() {
    this.wikiFolders = await api.get("/api/wiki-folders");
  },

  async createWikiFolder(name) {
    await api.post("/api/wiki-folders", { name });
    await this.loadWikiFolders();
  },

  async renameWikiFolder(id, name) {
    await api.patch(`/api/wiki-folders/${id}`, { name });
    await this.loadWikiFolders();
  },

  async deleteWikiFolder(id) {
    await api.del(`/api/wiki-folders/${id}`);
    await this.loadWikiFolders();
    await this.loadWikiEntries();
  },

  // folderId = null moves the entry back to "Uncategorized"
  async moveWikiEntry(entryId, folderId) {
    if (folderId == null) {
      await api.patch(`/api/wiki/${entryId}`, { clear_folder: true });
    } else {
      await api.patch(`/api/wiki/${entryId}`, { folder_id: folderId });
    }
    await this.loadWikiEntries();
    if (this.currentWikiId === entryId) {
      this.currentWikiEntry = await api.get(`/api/wiki/${entryId}`);
    }
  },

  // --- News ---

  async loadNewsSources() {
    this.newsSources = await api.get("/api/news/sources");
    if (!this.newsSelectedSource && this.newsSources.length) {
      this.newsSelectedSource = this.newsSources[0].key;
    }
  },

  async selectNewsSource(key) {
    this.newsSelectedSource = key;
    this.newsCurrentArticle = null;
    this.newsOverview = null;
    this.newsWeek = null;
    this.sidebarOpen = false;
    await this.loadNewsOverview();
  },

  async toggleNewsSourceSchedule(key) {
    const src = this.newsSources.find((s) => s.key === key);
    if (!src) return;
    const next = !src.enabled;
    await api.patch(`/api/news/sources/${key}`, { enabled: next });
    src.enabled = next;
  },

  async toggleNewsSourcePin(key) {
    const src = this.newsSources.find((s) => s.key === key);
    if (!src) return;
    const next = !src.pinned;
    await api.patch(`/api/news/sources/${key}`, { pinned: next });
    src.pinned = next;
  },

  async loadNewsOverview() {
    if (!this.newsSelectedSource) await this.loadNewsSources();
    if (!this.newsSelectedSource) return;
    this.newsLoading = true;
    try {
      const path =
        this.newsSelectedSource === "__favorites__"
          ? "/api/news/favorites"
          : `/api/news/overview?source=${this.newsSelectedSource}`;
      this.newsOverview = await api.get(path);
      this.newsFeaturedIndex = 0;
    } finally {
      this.newsLoading = false;
    }
  },

  // dateStr: any day in the target week - the backend always resolves it to
  // that week's Monday-Sunday range.
  async loadNewsWeek(dateStr) {
    if (!this.newsSelectedSource) return;
    this.newsLoading = true;
    try {
      const path =
        this.newsSelectedSource === "__favorites__"
          ? `/api/news/favorites/week?date=${dateStr}`
          : `/api/news/week?source=${this.newsSelectedSource}&date=${dateStr}`;
      this.newsWeek = await api.get(path);
    } finally {
      this.newsLoading = false;
    }
  },

  clearNewsWeek() {
    this.newsWeek = null;
  },

  stepNewsFeatured(delta) {
    if (!this.newsOverview || !this.newsOverview.featured.length) return;
    const len = this.newsOverview.featured.length;
    this.newsFeaturedIndex = (this.newsFeaturedIndex + delta + len) % len;
  },

  // siblingIds: the id list of the same day's articles the user opened this
  // one from (featured carousel or a timeline day's cards) - prev/next stay
  // within that list, i.e. within that one day, not across all news.
  async openNewsArticle(id, siblingIds) {
    this.newsArticleSiblings = siblingIds || [id];
    this.newsArticleLoading = true;
    try {
      this.newsCurrentArticle = await api.get(`/api/news/articles/${id}`);
    } finally {
      this.newsArticleLoading = false;
    }
  },

  async stepNewsArticle(delta) {
    if (!this.newsCurrentArticle) return;
    const ids = this.newsArticleSiblings;
    const idx = ids.indexOf(this.newsCurrentArticle.id);
    const nextIdx = idx + delta;
    if (nextIdx < 0 || nextIdx >= ids.length) return; // boundary = that day's articles, no wraparound
    await this.openNewsArticle(ids[nextIdx], ids);
  },

  async toggleNewsArticleFavorite() {
    if (!this.newsCurrentArticle) return;
    const next = !this.newsCurrentArticle.is_favorited;
    await api.patch(`/api/news/articles/${this.newsCurrentArticle.id}/favorite`, { favorited: next });
    this.newsCurrentArticle.is_favorited = next;
  },

  closeNewsArticle() {
    this.newsCurrentArticle = null;
    this.newsArticleSiblings = [];
  },

  // --- Notes: shared viewing drawer (CalendarView.js renders it, both its
  // own day-detail list and Sidebar.js's calendar-branch Favorites list open
  // notes through these same two functions) ---

  async openNoteView(id) {
    this.loadingNoteView = true;
    this.viewingNote = null;
    try {
      this.viewingNote = await api.get(`/api/notes/${id}`);
    } finally {
      this.loadingNoteView = false;
    }
  },

  closeNoteView() {
    this.viewingNote = null;
  },

  // patch: any subset of {title, content, tags}
  async updateNote(id, patch) {
    const updated = await api.patch(`/api/notes/${id}`, patch);
    if (this.viewingNote && this.viewingNote.id === id) this.viewingNote = updated;
    const idx = this.favoritedNotes.findIndex((n) => n.id === id);
    if (idx !== -1) {
      if (updated.is_favorited) this.favoritedNotes[idx] = updated;
      else this.favoritedNotes.splice(idx, 1);
    }
    return updated;
  },

  async deleteNote(id) {
    await api.del(`/api/notes/${id}`);
    if (this.viewingNote && this.viewingNote.id === id) this.viewingNote = null;
    this.favoritedNotes = this.favoritedNotes.filter((n) => n.id !== id);
  },

  async toggleNoteFavorite(id) {
    const target = this.viewingNote && this.viewingNote.id === id ? this.viewingNote : null;
    const inFavList = this.favoritedNotes.find((n) => n.id === id);
    const next = !((target && target.is_favorited) || (inFavList && inFavList.is_favorited));
    await api.patch(`/api/notes/${id}/favorite`, { favorited: next });
    if (target) target.is_favorited = next;
    if (inFavList) inFavList.is_favorited = next;
    else if (next) await this.loadFavoritedNotes();
    if (!next) this.favoritedNotes = this.favoritedNotes.filter((n) => n.id !== id);
  },

  async loadFavoritedNotes() {
    this.favoritedNotes = await api.get("/api/notes?favorited=true");
  },

  // Standalone Notes page's full browser - optionally filtered by tag (see
  // notesTagFilter, set via the page's tag chips).
  async loadAllNotes() {
    const path = this.notesTagFilter ? `/api/notes?tag=${encodeURIComponent(this.notesTagFilter)}` : "/api/notes";
    this.allNotes = await api.get(path);
  },

  // --- Notes: templates & tags (standalone Notes page) ---

  async loadNoteTemplates() {
    this.noteTemplates = await api.get("/api/notes/templates");
  },

  async createNoteTemplate(name, content) {
    await api.post("/api/notes/templates", { name, content });
    await this.loadNoteTemplates();
  },

  async updateNoteTemplate(id, patch) {
    await api.patch(`/api/notes/templates/${id}`, patch);
    await this.loadNoteTemplates();
  },

  async deleteNoteTemplate(id) {
    await api.del(`/api/notes/templates/${id}`);
    await this.loadNoteTemplates();
  },

  async loadNoteTags() {
    this.noteTags = await api.get("/api/notes/tags");
  },

  async createNoteTag(name) {
    await api.post("/api/notes/tags", { name });
    await this.loadNoteTags();
  },

  async deleteNoteTag(id) {
    await api.del(`/api/notes/tags/${id}`);
    await this.loadNoteTags();
  },

  // --- Mobile sidebar drawer ---

  toggleSidebar() {
    this.sidebarOpen = !this.sidebarOpen;
  },

  closeSidebar() {
    this.sidebarOpen = false;
  },

  // --- Theme (light/dark) ---

  initTheme() {
    const saved = localStorage.getItem("theme");
    this.theme = saved === "dark" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", this.theme);
  },

  toggleTheme() {
    this.theme = this.theme === "dark" ? "light" : "dark";
    localStorage.setItem("theme", this.theme);
    document.documentElement.setAttribute("data-theme", this.theme);
  },

  // --- Login (no auto-logout - see AuthToken in backend/app/models/auth.py) ---

  async login(username, password) {
    const res = await api.post("/api/auth/login", { username, password });
    localStorage.setItem("auth_token", res.token);
    localStorage.setItem("auth_username", res.username);
    this.username = res.username;
    this.loggedIn = true;
  },

  async logout() {
    try {
      await api.post("/api/auth/logout", {});
    } catch (e) {
      // ignore - clearing local state regardless
    }
    this.handleUnauthorized();
  },

  // Also called when any API call comes back 401 (see the auth:unauthorized
  // listener below) - e.g. the token got invalidated by logging out
  // elsewhere. Clears everything scoped to the account so a different login
  // never flashes the previous account's data.
  handleUnauthorized() {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_username");
    this.loggedIn = false;
    this.username = null;
    this.sessions = [];
    this.currentSessionId = null;
    this.messages = [];
    this.wikiEntries = [];
    this.currentWikiId = null;
    this.currentWikiEntry = null;
    this.wikiFolders = [];
    this.favoritedNotes = [];
    this.viewingNote = null;
    this.noteTemplates = [];
    this.noteTags = [];
    this.allNotes = [];
    this.notesTagFilter = null;
  },
});

window.addEventListener("auth:unauthorized", () => store.handleUnauthorized());
