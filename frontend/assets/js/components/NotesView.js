const { ref, computed } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";
import { renderMarkdown } from "../markdown.js";
import DrawerShell from "./DrawerShell.js";
import ColorPicker from "./ColorPicker.js";
import TagPicker from "./TagPicker.js";

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
  components: { DrawerShell, ColorPicker, TagPicker },
  setup() {
    // No more Notes/Templates tab switcher - this page always defaults to
    // the all-notes list; templates are listed/created in the sidebar (see
    // Sidebar.js's 'notes' branch) and, once picked, take over this main
    // panel via store.viewingTemplate (cleared to fall back to the list).

    const sortMode = ref("date"); // "date" | "tag"

    async function pickTagFilter(tag) {
      store.notesTagFilter = store.notesTagFilter === tag ? null : tag;
      await store.loadAllNotes();
    }

    // Only meaningful in "tag" sort mode - buckets every note under each of
    // its own tags (so a multi-tagged note shows up more than once), plus an
    // "Untagged" bucket. Unrelated to notesTagFilter, which is a plain list filter.
    const allNotesByTag = computed(() => {
      const groups = {};
      const order = [];
      for (const n of store.allNotes) {
        const tags = n.tags && n.tags.length ? n.tags : ["Untagged"];
        for (const t of tags) {
          if (!groups[t]) {
            groups[t] = [];
            order.push(t);
          }
          groups[t].push(n);
        }
      }
      order.sort((a, b) => (a === "Untagged" ? 1 : 0) - (b === "Untagged" ? 1 : 0) || a.localeCompare(b));
      return order.map((tag) => ({ tag, notes: groups[tag] }));
    });

    // Tags are no longer registered through a dedicated "add tag" box - new
    // tag names typed straight into a note's Tags field get auto-registered
    // on save (see store.createNote/updateNote's ensureNoteTags call), so
    // they show up here and in TagPicker's checklist without an extra step.
    async function removeTag(t) {
      if (confirm(`Delete tag "${t.name}"? Notes already tagged with it keep the tag text - this only removes it from the saved list.`)) {
        await store.deleteNoteTag(t.id);
      }
    }

    // "2026-08-05T12:00:00" -> "2026/8/5" (drawer's full-timestamp display)
    function fmtDateShort(d) {
      const dt = new Date(d);
      return `${dt.getFullYear()}/${dt.getMonth() + 1}/${dt.getDate()}`;
    }

    // "2026-08-05" -> "2026/8/5" - date-only string, for the grouped list's
    // separators (see allNotesByDate) - avoids new Date() re-interpreting a
    // bare date string in the local timezone and shifting it a day.
    function fmtDateLabel(dateStr) {
      const [y, m, d] = dateStr.split("-").map(Number);
      return `${y}/${m}/${d}`;
    }

    // --- New note (this page didn't have a create entry point before - it
    // relied entirely on the calendar page. Dated today, same as omitting
    // `date` on the calendar's own create call.) ---

    const showNewNote = ref(false);
    const newNoteTitle = ref("");
    const newNoteContent = ref("");
    const newNoteTags = ref("");
    const newNoteColor = ref("");
    const savingNewNote = ref(false);

    function toggleNewNote() {
      store.viewingTemplate = null; // the "+" always means "add a note", regardless of what's showing
      showNewNote.value = !showNewNote.value;
      newNoteTitle.value = "";
      newNoteContent.value = "";
      newNoteTags.value = "";
      newNoteColor.value = "";
    }

    async function saveNewNote() {
      if (!newNoteTitle.value.trim()) return;
      savingNewNote.value = true;
      try {
        await store.createNote({
          title: newNoteTitle.value.trim(),
          content: newNoteContent.value,
          tags: newNoteTags.value.split(",").map((t) => t.trim()).filter(Boolean),
          color: newNoteColor.value,
        });
        toggleNewNote();
      } finally {
        savingNewNote.value = false;
      }
    }

    // --- Note view/edit drawer (same store.viewingNote state CalendarView.js
    // uses, so this page and the calendar's Favorites list never fight over it) ---

    const editingNote = ref(false);
    const editNoteTitle = ref("");
    const editNoteContent = ref("");
    const editNoteTags = ref("");
    const editNoteColor = ref("");
    const editNotePreview = ref(false);
    const editNoteHelp = ref(false);
    const savingNoteEdit = ref(false);

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
        await store.loadAllNotes();
      } finally {
        savingNoteEdit.value = false;
      }
    }

    async function removeNote() {
      if (!store.viewingNote) return;
      if (confirm(`Delete note "${store.viewingNote.title}"? This can't be undone.`)) {
        await store.deleteNote(store.viewingNote.id);
        closeNote();
        await store.loadAllNotes();
      }
    }

    // --- Template viewer/editor - takes over this main panel whenever
    // store.viewingTemplate is set (from Sidebar.js's template list).
    // Same view/edit/delete pattern as note-detail above. ---

    const editingTemplate = ref(false);
    const editTemplateName = ref("");
    const editTemplateContent = ref("");
    const editTemplateTags = ref("");
    const savingTemplateEdit = ref(false);

    function startEditTemplate() {
      if (!store.viewingTemplate) return;
      editTemplateName.value = store.viewingTemplate.name;
      editTemplateContent.value = store.viewingTemplate.content;
      editTemplateTags.value = (store.viewingTemplate.tags || []).join(", ");
      editingTemplate.value = true;
    }

    function cancelEditTemplate() {
      editingTemplate.value = false;
    }

    async function saveEditTemplate() {
      if (!store.viewingTemplate || !editTemplateName.value.trim()) return;
      savingTemplateEdit.value = true;
      try {
        await store.updateNoteTemplate(store.viewingTemplate.id, {
          name: editTemplateName.value.trim(),
          content: editTemplateContent.value,
          tags: editTemplateTags.value.split(",").map((t) => t.trim()).filter(Boolean),
        });
        editingTemplate.value = false;
      } finally {
        savingTemplateEdit.value = false;
      }
    }

    async function removeViewingTemplate() {
      if (!store.viewingTemplate) return;
      if (confirm(`Delete template "${store.viewingTemplate.name}"?`)) {
        await store.deleteNoteTemplate(store.viewingTemplate.id);
        editingTemplate.value = false;
      }
    }

    function closeTemplateView() {
      store.viewingTemplate = null;
      editingTemplate.value = false;
    }

    return {
      store, icons, renderMarkdown, MARKDOWN_HELP,
      sortMode, pickTagFilter, allNotesByTag, removeTag,
      fmtDateShort, fmtDateLabel,
      showNewNote, newNoteTitle, newNoteContent, newNoteTags, newNoteColor, savingNewNote,
      toggleNewNote, saveNewNote,
      editingNote, editNoteTitle, editNoteContent, editNoteTags, editNoteColor, editNotePreview, editNoteHelp, savingNoteEdit,
      openNote, closeNote, startEditNote, cancelEditNote, saveNoteEdit, removeNote,
      editingTemplate, editTemplateName, editTemplateContent, editTemplateTags, savingTemplateEdit,
      startEditTemplate, cancelEditTemplate, saveEditTemplate, removeViewingTemplate, closeTemplateView,
    };
  },
  template: `
  <div class="main-panel notes-panel">
    <div class="wiki-toolbar" style="justify-content:flex-end;">
      <button class="icon-btn" title="New note" @click="toggleNewNote" v-html="icons.plus"></button>
    </div>

    <template v-if="store.viewingTemplate">
      <div v-if="editingTemplate" class="note-editor">
        <input type="text" v-model="editTemplateName" class="note-editor-title-input" placeholder="Template name" />
        <input type="text" v-model="editTemplateTags" class="note-editor-title-input" placeholder="Tags (comma separated)" />
        <textarea v-model="editTemplateContent" class="note-editor-textarea" rows="10"></textarea>
        <div class="drawer-actions">
          <button class="btn" :disabled="savingTemplateEdit || !editTemplateName.trim()" @click="saveEditTemplate">
            <span v-if="savingTemplateEdit" class="spinner"></span>{{ savingTemplateEdit ? ' Saving…' : 'Save' }}
          </button>
          <button class="btn secondary" :disabled="savingTemplateEdit" @click="cancelEditTemplate">Cancel</button>
        </div>
      </div>

      <div v-else class="note-detail">
        <div class="note-detail-header">
          <h2>{{ store.viewingTemplate.name }}</h2>
          <div class="note-detail-actions">
            <button class="icon-btn" title="Edit" @click="startEditTemplate" v-html="icons.edit"></button>
            <button class="icon-btn" title="Delete" @click="removeViewingTemplate" v-html="icons.trash"></button>
            <button class="icon-btn" title="Back to notes" @click="closeTemplateView" v-html="icons.close"></button>
          </div>
        </div>
        <div v-if="store.viewingTemplate.tags && store.viewingTemplate.tags.length" class="tag-row">
          <span class="tag" v-for="t in store.viewingTemplate.tags" :key="t">{{ t }}</span>
        </div>
        <hr class="note-divider" />
        <div class="markdown-body note-editor-preview">{{ store.viewingTemplate.content }}</div>
      </div>
    </template>

    <template v-else>
      <div class="row" style="gap:10px; margin-bottom:10px; flex-wrap:wrap;">
        <span class="notes-sort-toggle">
          <button class="icon-btn" title="Sort by date" :class="{active: sortMode === 'date'}" @click="sortMode = 'date'" v-html="icons.calendar"></button>
          <button class="icon-btn" title="Sort by tag" :class="{active: sortMode === 'tag'}" @click="sortMode = 'tag'" v-html="icons.tag"></button>
        </span>
      </div>

      <div v-if="showNewNote" class="note-editor">
        <input type="text" v-model="newNoteTitle" class="note-editor-title-input" placeholder="Note title" />
        <div class="row" style="gap:8px; align-items:center; margin-bottom:8px;">
          <input type="text" v-model="newNoteTags" class="note-editor-title-input" style="flex:1; margin-bottom:0;" placeholder="Tags (comma separated)" />
          <TagPicker v-model="newNoteTags" :options="store.noteTags" />
          <ColorPicker v-model="newNoteColor" />
        </div>
        <textarea v-model="newNoteContent" class="note-editor-textarea" rows="8" placeholder="Write your note in Markdown…"></textarea>
        <button class="btn" :disabled="savingNewNote || !newNoteTitle.trim()" @click="saveNewNote">
          <span v-if="savingNewNote" class="spinner"></span>{{ savingNewNote ? ' Saving…' : 'Save note' }}
        </button>
      </div>

      <div v-if="store.noteTags.length" class="tag-row notes-tag-filter">
        <span v-for="t in store.noteTags" :key="t.id" class="tag notes-tag-manage" :class="{active: store.notesTagFilter === t.name}">
          <span class="clickable" @click="pickTagFilter(t.name)">{{ t.name }}</span>
          <button class="mini-icon-btn" title="Delete tag" @click="removeTag(t)">×</button>
        </span>
      </div>

      <template v-if="sortMode === 'date'">
        <template v-for="group in store.allNotesByDate" :key="group.date">
          <div class="notes-date-sep">{{ fmtDateLabel(group.date) }}</div>
          <div class="notes-grid">
            <div v-for="n in group.notes" :key="n.id" class="card clickable" :class="n.color ? 'note-color-' + n.color : ''" @click="openNote(n.id)">
              <div class="day-card-title">{{ n.title }}</div>
              <div v-if="n.tags && n.tags.length" class="tag-row">
                <span class="tag tag-solid" v-for="t in n.tags" :key="t">{{ t }}</span>
              </div>
            </div>
          </div>
        </template>
      </template>
      <template v-else>
        <template v-for="group in allNotesByTag" :key="group.tag">
          <div class="notes-date-sep">{{ group.tag }}</div>
          <div class="notes-grid">
            <div v-for="n in group.notes" :key="n.id" class="card clickable" :class="n.color ? 'note-color-' + n.color : ''" @click="openNote(n.id)">
              <div class="day-card-title">{{ n.title }}</div>
            </div>
          </div>
        </template>
      </template>
      <div v-if="!store.allNotes.length" class="empty-state">No notes yet</div>
    </template>

    <!-- Note view/edit drawer - same store.viewingNote the calendar page uses -->
    <DrawerShell v-if="store.loadingNoteView || store.viewingNote" title="Note" wide @close="closeNote">
      <div v-if="store.loadingNoteView" class="loading-row"><span class="spinner"></span> Loading…</div>

      <template v-else-if="store.viewingNote">
        <div v-if="editingNote" class="note-editor">
          <input type="text" v-model="editNoteTitle" class="note-editor-title-input" placeholder="Note title" />
          <div class="row" style="gap:8px; align-items:center; margin-bottom:8px;">
            <input type="text" v-model="editNoteTags" class="note-editor-title-input" style="flex:1; margin-bottom:0;" placeholder="Tags (comma separated)" />
            <TagPicker v-model="editNoteTags" :options="store.noteTags" />
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
