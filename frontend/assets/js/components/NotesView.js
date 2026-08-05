const { ref, computed } = window.Vue;
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
    const tab = ref("notes"); // "notes" | "templates"

    // --- Notes tab: sort/group mode + tag filter/management (merged in
    // from what used to be a separate "Tags" tab) ---

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

    const newTagName = ref("");
    const savingTag = ref(false);

    async function addTag() {
      const name = newTagName.value.trim();
      if (!name) return;
      savingTag.value = true;
      try {
        await store.createNoteTag(name);
        newTagName.value = "";
      } finally {
        savingTag.value = false;
      }
    }

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

    // --- Templates tab ---

    const showNewTemplate = ref(false);
    const newTemplateName = ref("");
    const newTemplateContent = ref("");
    const newTemplateTags = ref("");
    const savingTemplate = ref(false);
    const editingTemplateId = ref(null);
    const editTemplateName = ref("");
    const editTemplateContent = ref("");
    const editTemplateTags = ref("");

    function toggleNewTemplate() {
      showNewTemplate.value = !showNewTemplate.value;
      newTemplateName.value = "";
      newTemplateContent.value = "";
      newTemplateTags.value = "";
    }

    async function saveNewTemplate() {
      if (!newTemplateName.value.trim()) return;
      savingTemplate.value = true;
      try {
        await store.createNoteTemplate(
          newTemplateName.value.trim(),
          newTemplateContent.value,
          newTemplateTags.value.split(",").map((t) => t.trim()).filter(Boolean),
        );
        toggleNewTemplate();
      } finally {
        savingTemplate.value = false;
      }
    }

    function startEditTemplate(t) {
      editingTemplateId.value = t.id;
      editTemplateName.value = t.name;
      editTemplateContent.value = t.content;
      editTemplateTags.value = (t.tags || []).join(", ");
    }

    function cancelEditTemplate() {
      editingTemplateId.value = null;
    }

    async function saveEditTemplate() {
      if (!editTemplateName.value.trim()) return;
      await store.updateNoteTemplate(editingTemplateId.value, {
        name: editTemplateName.value.trim(),
        content: editTemplateContent.value,
        tags: editTemplateTags.value.split(",").map((t) => t.trim()).filter(Boolean),
      });
      editingTemplateId.value = null;
    }

    async function removeTemplate(t) {
      if (confirm(`Delete template "${t.name}"?`)) {
        await store.deleteNoteTemplate(t.id);
      }
    }

    // --- Unified "+" (top-right) - choose whether to add a note or a template ---
    const showAddMenu = ref(false);

    function pickAddNote() {
      showAddMenu.value = false;
      tab.value = "notes";
      if (!showNewNote.value) toggleNewNote();
    }

    function pickAddTemplate() {
      showAddMenu.value = false;
      tab.value = "templates";
      if (!showNewTemplate.value) toggleNewTemplate();
    }

    return {
      store, icons, renderMarkdown, MARKDOWN_HELP,
      tab, sortMode, pickTagFilter, allNotesByTag, newTagName, savingTag, addTag, removeTag,
      showAddMenu, pickAddNote, pickAddTemplate,
      fmtDateShort, fmtDateLabel,
      showNewNote, newNoteTitle, newNoteContent, newNoteTags, newNoteColor, savingNewNote,
      toggleNewNote, saveNewNote,
      editingNote, editNoteTitle, editNoteContent, editNoteTags, editNoteColor, editNotePreview, editNoteHelp, savingNoteEdit,
      openNote, closeNote, startEditNote, cancelEditNote, saveNoteEdit, removeNote,
      showNewTemplate, newTemplateName, newTemplateContent, newTemplateTags, savingTemplate,
      toggleNewTemplate, saveNewTemplate,
      editingTemplateId, editTemplateName, editTemplateContent, editTemplateTags,
      startEditTemplate, cancelEditTemplate, saveEditTemplate, removeTemplate,
    };
  },
  template: `
  <div class="main-panel notes-panel">
    <div class="wiki-toolbar row between">
      <div class="row" style="gap:10px;">
        <button class="btn secondary" :class="{active: tab === 'notes'}" @click="tab = 'notes'">Notes</button>
        <button class="btn secondary" :class="{active: tab === 'templates'}" @click="tab = 'templates'">Templates</button>
      </div>
      <div class="notes-add-menu-wrap">
        <button class="icon-btn" title="Add" @click="showAddMenu = !showAddMenu" v-html="icons.plus"></button>
        <div v-if="showAddMenu" class="notes-add-menu">
          <div class="notes-add-menu-item" @click="pickAddNote">Add note</div>
          <div class="notes-add-menu-item" @click="pickAddTemplate">Add template</div>
        </div>
      </div>
    </div>

    <template v-if="tab === 'notes'">
      <div class="row" style="gap:10px; margin-bottom:10px; flex-wrap:wrap;">
        <span class="notes-sort-toggle">
          <button class="btn secondary" :class="{active: sortMode === 'date'}" @click="sortMode = 'date'">By Date</button>
          <button class="btn secondary" :class="{active: sortMode === 'tag'}" @click="sortMode = 'tag'">By Tag</button>
        </span>
      </div>

      <div v-if="showNewNote" class="note-editor">
        <input type="text" v-model="newNoteTitle" class="note-editor-title-input" placeholder="Note title" />
        <div class="row" style="gap:8px; align-items:center; margin-bottom:8px;">
          <input type="text" v-model="newNoteTags" class="note-editor-title-input" style="flex:1; margin-bottom:0;" placeholder="Tags (comma separated)" />
          <ColorPicker v-model="newNoteColor" />
        </div>
        <textarea v-model="newNoteContent" class="note-editor-textarea" rows="8" placeholder="Write your note in Markdown…"></textarea>
        <button class="btn" :disabled="savingNewNote || !newNoteTitle.trim()" @click="saveNewNote">
          <span v-if="savingNewNote" class="spinner"></span>{{ savingNewNote ? ' Saving…' : 'Save note' }}
        </button>
      </div>

      <div class="row" style="gap:8px; align-items:center; margin-bottom:10px;">
        <input type="text" v-model="newTagName" class="note-editor-title-input" style="margin-bottom:0; max-width:200px;" placeholder="New tag name" @keydown.enter.prevent="addTag" />
        <button class="btn secondary" :disabled="savingTag || !newTagName.trim()" @click="addTag">Add tag</button>
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

    <template v-else-if="tab === 'templates'">
      <div v-if="showNewTemplate" class="note-editor">
        <input type="text" v-model="newTemplateName" class="note-editor-title-input" placeholder="Template name" />
        <input type="text" v-model="newTemplateTags" class="note-editor-title-input" placeholder="Tags applied to every note made from this template (comma separated)" />
        <textarea v-model="newTemplateContent" class="note-editor-textarea" rows="8" placeholder="Markdown content applied when this template is picked…"></textarea>
        <button class="btn" :disabled="savingTemplate || !newTemplateName.trim()" @click="saveNewTemplate">
          <span v-if="savingTemplate" class="spinner"></span>{{ savingTemplate ? ' Saving…' : 'Save template' }}
        </button>
      </div>

      <div class="notes-grid">
        <div v-for="t in store.noteTemplates" :key="t.id" class="card">
          <template v-if="editingTemplateId === t.id">
            <input type="text" v-model="editTemplateName" class="note-editor-title-input" placeholder="Template name" />
            <input type="text" v-model="editTemplateTags" class="note-editor-title-input" placeholder="Tags (comma separated)" />
            <textarea v-model="editTemplateContent" class="note-editor-textarea" rows="8"></textarea>
            <div class="drawer-actions">
              <button class="btn" @click="saveEditTemplate">Save</button>
              <button class="btn secondary" @click="cancelEditTemplate">Cancel</button>
            </div>
          </template>
          <template v-else>
            <div class="day-card-title">{{ t.name }}</div>
            <div v-if="t.tags && t.tags.length" class="tag-row">
              <span class="tag" v-for="tg in t.tags" :key="tg">{{ tg }}</span>
            </div>
            <div class="markdown-body note-editor-preview">{{ t.content }}</div>
            <div class="row" style="gap:8px; margin-top:10px;">
              <button class="mini-icon-btn" title="Rename / edit" @click="startEditTemplate(t)" v-html="icons.edit"></button>
              <button class="mini-icon-btn" title="Delete" @click="removeTemplate(t)" v-html="icons.trash"></button>
            </div>
          </template>
        </div>
      </div>
      <div v-if="!store.noteTemplates.length && !showNewTemplate" class="empty-state">No templates yet</div>
    </template>

    <!-- Note view/edit drawer - same store.viewingNote the calendar page uses -->
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
