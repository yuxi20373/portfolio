const { ref, watch, onMounted } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";
import { renderMarkdown } from "../markdown.js";
import AdjustDrawer from "./AdjustDrawer.js";

export default {
  components: { AdjustDrawer },
  setup() {
    // --- Search panel: keyword (search-engine style) + question (what to save) ---
    const showSearchBox = ref(false);
    const searchKeyword = ref("");
    const searchQuestion = ref("");
    const searching = ref(false);
    const composing = ref(false); // shared IME-composition guard for both fields
    const searchToggleImgOk = ref(true); // 外層「Search」按鈕的 search.png 讀取失敗就換成 SVG+文字備援

    // --- Adjust drawer (right-side, propose-then-confirm) ---
    const showAdjustDrawer = ref(false);

    // --- Manual edit (no LLM at all) ---
    const editing = ref(false);
    const editTitle = ref("");
    const editTags = ref(""); // comma-separated in the UI, array in the API
    const editContent = ref("");
    const saving = ref(false);

    onMounted(() => {
      if (store.wikiEntries.length === 0) store.loadWikiEntries();
    });

    // Don't let a stale edit form bleed into a different entry
    watch(
      () => store.currentWikiId,
      () => {
        editing.value = false;
      }
    );

    function onCompositionStart() {
      composing.value = true;
    }
    function onCompositionEnd() {
      composing.value = false;
    }

    // Same graceful-fallback pattern as HomeView.js's decorative images -
    // if the PNG isn't there yet, just hide the broken <img>.
    function onIconError(e) {
      e.target.style.display = "none";
    }

    async function onSearchFieldKeydown(e) {
      if (e.key !== "Enter") return;
      // Don't submit while an IME (e.g. typing Chinese) is still composing a candidate
      if (composing.value || e.isComposing || e.keyCode === 229) return;
      e.preventDefault();
      await runSearch();
    }

    async function runSearch() {
      const keyword = searchKeyword.value.trim();
      const question = searchQuestion.value.trim();
      if (!keyword || !question) return;
      searching.value = true;
      try {
        await store.searchIntoWiki(keyword, question);
        searchKeyword.value = "";
        searchQuestion.value = "";
        showSearchBox.value = false;
      } finally {
        searching.value = false;
      }
    }

    function startEdit() {
      if (!store.currentWikiEntry) return;
      editTitle.value = store.currentWikiEntry.title;
      editTags.value = (store.currentWikiEntry.tags || []).join(", ");
      editContent.value = store.currentWikiEntry.content;
      editing.value = true;
    }

    function cancelEdit() {
      editing.value = false;
    }

    async function saveEdit() {
      if (!store.currentWikiId || !editTitle.value.trim()) return;
      saving.value = true;
      try {
        const tags = editTags.value
          .split(",")
          .map((t) => t.trim())
          .filter(Boolean);
        await store.updateWikiEntry(store.currentWikiId, {
          title: editTitle.value.trim(),
          tags,
          content: editContent.value,
        });
        editing.value = false;
      } finally {
        saving.value = false;
      }
    }

    async function removeEntry() {
      if (!store.currentWikiEntry) return;
      if (confirm(`Delete "${store.currentWikiEntry.title}"? This can't be undone.`)) {
        await store.deleteWikiEntry(store.currentWikiId);
      }
    }

    return {
      store,
      icons,
      renderMarkdown,
      showSearchBox,
      searchKeyword,
      searchQuestion,
      searching,
      searchToggleImgOk,
      onIconError,
      onCompositionStart,
      onCompositionEnd,
      onSearchFieldKeydown,
      runSearch,
      showAdjustDrawer,
      editing,
      editTitle,
      editTags,
      editContent,
      saving,
      startEdit,
      cancelEdit,
      saveEdit,
      removeEntry,
    };
  },
  template: `
  <div class="main-panel wiki-panel">
    <h1 class="page-title">WIKI</h1>
    <div class="wiki-toolbar">
      <button class="btn search-toggle-btn" @click="showSearchBox = !showSearchBox">
        <img v-if="searchToggleImgOk" :src="store.img('search.png')" alt="Search" @error="searchToggleImgOk = false" />
        <span v-else class="search-submit-fallback"><span v-html="icons.search"></span> Search</span>
      </button>
      <template v-if="store.currentWikiEntry && !editing">
        <button class="icon-btn" title="Edit" @click="startEdit" v-html="icons.edit"></button>
        <button class="icon-btn" title="Adjust" @click="showAdjustDrawer = true" v-html="icons.sliders"></button>
        <button class="icon-btn favorite-btn" :class="{active: store.currentWikiEntry.is_favorited}" title="Favorite this entry"
                @click="store.toggleWikiEntryFavorite(store.currentWikiEntry.id)"
                v-html="store.currentWikiEntry.is_favorited ? icons.bookmarkFilled : icons.bookmark"></button>
        <button class="icon-btn" title="Delete entry" @click="removeEntry" v-html="icons.trash"></button>
      </template>
    </div>

    <div v-if="showSearchBox" class="search-panel">
      <img class="wiki-search-icon" :src="store.img('icon-search.png')" alt="" @error="onIconError" />
      <div class="search-panel-fields">
        <label class="search-panel-label">Keyword
          <span class="search-panel-help">
            <span class="search-panel-help-icon" v-html="icons.help"></span>
            <span class="search-panel-help-tip">like what you'd type into a search engine — e.g. 軟體開發 RD</span>
          </span>
        </label>
        <input type="text" v-model="searchKeyword" class="search-panel-input"
               @compositionstart="onCompositionStart" @compositionend="onCompositionEnd"
               @keydown="onSearchFieldKeydown" />
        <label class="search-panel-label">Your question
          <span class="search-panel-help">
            <span class="search-panel-help-icon" v-html="icons.help"></span>
            <span class="search-panel-help-tip">what you want to know & save to the wiki — e.g. RD 的主要工作內容有什麼？怎麼定義 RD？</span>
          </span>
        </label>
        <input type="text" v-model="searchQuestion" class="search-panel-input"
               @compositionstart="onCompositionStart" @compositionend="onCompositionEnd"
               @keydown="onSearchFieldKeydown" />
        <button class="btn" :disabled="searching || !searchKeyword.trim() || !searchQuestion.trim()" @click="runSearch">
          <span v-if="searching" class="spinner"></span>{{ searching ? ' Searching…' : 'Search & add to wiki' }}
        </button>
      </div>
    </div>

    <div v-if="editing" class="wiki-edit-form">
      <label class="search-panel-label">Title</label>
      <input type="text" v-model="editTitle" class="search-panel-input" />
      <label class="search-panel-label">Tags (comma separated)</label>
      <input type="text" v-model="editTags" class="search-panel-input" placeholder="e.g. fish, aquarium, pet" />
      <label class="search-panel-label">Content (Markdown)</label>
      <textarea v-model="editContent" class="wiki-edit-textarea" rows="18"></textarea>
      <div class="drawer-actions">
        <button class="btn" :disabled="saving || !editTitle.trim()" @click="saveEdit">
          <span v-if="saving" class="spinner"></span>{{ saving ? ' Saving…' : 'Save' }}
        </button>
        <button class="btn secondary" :disabled="saving" @click="cancelEdit">Cancel</button>
      </div>
    </div>

    <div v-else-if="store.currentWikiEntry" class="wiki-detail">
      <div v-if="store.currentWikiEntry.entry_type" class="entry-type-badge">{{ store.currentWikiEntry.entry_type }}</div>
      <h2>{{ store.currentWikiEntry.title }}</h2>
      <div class="tag-row">
        <span class="tag" v-for="t in store.currentWikiEntry.tags" :key="t">{{ t }}</span>
      </div>
      <div class="markdown-body" v-html="renderMarkdown(store.currentWikiEntry.content)"></div>

      <div v-if="store.currentWikiEntry.related && store.currentWikiEntry.related.length" class="related-section">
        <h3>See also</h3>
        <div v-for="r in store.currentWikiEntry.related" :key="r.id"
             class="card clickable" @click="store.selectWikiEntry(r.id)">
          {{ r.title }}
        </div>
      </div>
    </div>
    <div v-else class="empty-state">Select an entry from the list, or use Search to add one</div>

    <AdjustDrawer v-if="showAdjustDrawer && store.currentWikiEntry" :entry="store.currentWikiEntry" @close="showAdjustDrawer = false" />
  </div>
  `,
};
