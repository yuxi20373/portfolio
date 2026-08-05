const { ref } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";
import { renderMarkdown } from "../markdown.js";
import DrawerShell from "./DrawerShell.js";

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
  components: { DrawerShell },
  setup() {
    const tab = ref("notes"); // "notes" | "templates" | "tags"

    // --- Notes tab ---

    async function pickTagFilter(tag) {
      store.notesTagFilter = store.notesTagFilter === tag ? null : tag;
      await store.loadAllNotes();
    }

    // "2026-08-05" -> "2026/8/5"
    function fmtDateShort(d) {
      const dt = new Date(d);
      return `${dt.getFullYear()}/${dt.getMonth() + 1}/${dt.getDate()}`;
    }

    // --- Note view/edit drawer (same store.viewingNote state CalendarView.js
    // uses, so this page and the calendar's Favorites list never fight over it) ---

    const editingNote = ref(false);
    const editNoteTitle = ref("");
    const editNoteContent = ref("");
    const editNoteTags = ref("");
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
    const savingTemplate = ref(false);
    const editingTemplateId = ref(null);
    const editTemplateName = ref("");
    const editTemplateContent = ref("");

    function toggleNewTemplate() {
      showNewTemplate.value = !showNewTemplate.value;
      newTemplateName.value = "";
      newTemplateContent.value = "";
    }

    async function saveNewTemplate() {
      if (!newTemplateName.value.trim()) return;
      savingTemplate.value = true;
      try {
        await store.createNoteTemplate(newTemplateName.value.trim(), newTemplateContent.value);
        toggleNewTemplate();
      } finally {
        savingTemplate.value = false;
      }
    }

    function startEditTemplate(t) {
      editingTemplateId.value = t.id;
      editTemplateName.value = t.name;
      editTemplateContent.value = t.content;
    }

    function cancelEditTemplate() {
      editingTemplateId.value = null;
    }

    async function saveEditTemplate() {
      if (!editTemplateName.value.trim()) return;
      await store.updateNoteTemplate(editingTemplateId.value, {
        name: editTemplateName.value.trim(),
        content: editTemplateContent.value,
      });
      editingTemplateId.value = null;
    }

    async function removeTemplate(t) {
      if (confirm(`Delete template "${t.name}"?`)) {
        await store.deleteNoteTemplate(t.id);
      }
    }

    // --- Tags tab ---

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

    return {
      store, icons, renderMarkdown, MARKDOWN_HELP,
      tab, pickTagFilter, fmtDateShort,
      editingNote, editNoteTitle, editNoteContent, editNoteTags, editNotePreview, editNoteHelp, savingNoteEdit,
      openNote, closeNote, startEditNote, cancelEditNote, saveNoteEdit, removeNote,
      showNewTemplate, newTemplateName, newTemplateContent, savingTemplate,
      toggleNewTemplate, saveNewTemplate,
      editingTemplateId, editTemplateName, editTemplateContent,
      startEditTemplate, cancelEditTemplate, saveEditTemplate, removeTemplate,
      newTagName, savingTag, addTag, removeTag,
    };
  },
  template: `
  <div class="main-panel notes-panel">
    <div class="wiki-toolbar">
      <button class="btn secondary" :class="{active: tab === 'notes'}" @click="tab = 'notes'">Notes</button>
      <button class="btn secondary" :class="{active: tab === 'templates'}" @click="tab = 'templates'">Templates</button>
      <button class="btn secondary" :class="{active: tab === 'tags'}" @click="tab = 'tags'">Tags</button>
    </div>

    <template v-if="tab === 'notes'">
      <div v-if="store.noteTags.length" class="tag-row notes-tag-filter">
        <span v-for="t in store.noteTags" :key="t.id" class="tag clickable" :class="{active: store.notesTagFilter === t.name}" @click="pickTagFilter(t.name)">{{ t.name }}</span>
      </div>

      <div class="notes-grid">
        <div v-for="n in store.allNotes" :key="n.id" class="card clickable" @click="openNote(n.id)">
          <div class="day-card-title">{{ n.title }}</div>
          <div class="news-time">{{ fmtDateShort(n.created_at) }}</div>
          <div v-if="n.tags && n.tags.length" class="tag-row">
            <span class="tag" v-for="t in n.tags" :key="t">{{ t }}</span>
          </div>
        </div>
      </div>
      <div v-if="!store.allNotes.length" class="empty-state">No notes yet - add one from the calendar page.</div>
    </template>

    <template v-else-if="tab === 'templates'">
      <div class="new-chat-row" @click="toggleNewTemplate">
        <span class="icon-btn" v-html="icons.plus"></span>
        <span class="new-chat-label">New template</span>
      </div>

      <div v-if="showNewTemplate" class="note-editor">
        <input type="text" v-model="newTemplateName" class="note-editor-title-input" placeholder="Template name" />
        <textarea v-model="newTemplateContent" class="note-editor-textarea" rows="8" placeholder="Markdown content applied when this template is picked…"></textarea>
        <button class="btn" :disabled="savingTemplate || !newTemplateName.trim()" @click="saveNewTemplate">
          <span v-if="savingTemplate" class="spinner"></span>{{ savingTemplate ? ' Saving…' : 'Save template' }}
        </button>
      </div>

      <div class="notes-grid">
        <div v-for="t in store.noteTemplates" :key="t.id" class="card">
          <template v-if="editingTemplateId === t.id">
            <input type="text" v-model="editTemplateName" class="note-editor-title-input" placeholder="Template name" />
            <textarea v-model="editTemplateContent" class="note-editor-textarea" rows="8"></textarea>
            <div class="drawer-actions">
              <button class="btn" @click="saveEditTemplate">Save</button>
              <button class="btn secondary" @click="cancelEditTemplate">Cancel</button>
            </div>
          </template>
          <template v-else>
            <div class="day-card-title">{{ t.name }}</div>
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

    <template v-else-if="tab === 'tags'">
      <div class="row" style="gap:8px; margin-bottom:14px;">
        <input type="text" v-model="newTagName" class="note-editor-title-input" style="margin-bottom:0;" placeholder="New tag name" @keydown.enter.prevent="addTag" />
        <button class="btn" :disabled="savingTag || !newTagName.trim()" @click="addTag">Add tag</button>
      </div>

      <div class="tag-row">
        <span v-for="t in store.noteTags" :key="t.id" class="tag notes-tag-manage">
          {{ t.name }}
          <button class="mini-icon-btn" title="Delete tag" @click="removeTag(t)">×</button>
        </span>
      </div>
      <div v-if="!store.noteTags.length" class="empty-state">No tags yet</div>
    </template>

    <!-- Note view/edit drawer - same store.viewingNote the calendar page uses -->
    <DrawerShell v-if="store.loadingNoteView || store.viewingNote" title="Note" @close="closeNote">
      <div v-if="store.loadingNoteView" class="loading-row"><span class="spinner"></span> Loading…</div>

      <template v-else-if="store.viewingNote">
        <div v-if="!editingNote" class="row" style="gap:8px; margin-bottom:16px;">
          <button class="btn secondary" @click="startEditNote">Edit</button>
          <button class="icon-btn" :class="{active: store.viewingNote.is_favorited}" title="Favorite"
                  @click="store.toggleNoteFavorite(store.viewingNote.id)"
                  v-html="store.viewingNote.is_favorited ? icons.bookmarkFilled : icons.bookmark"></button>
          <button class="btn danger" @click="removeNote">
            <span v-html="icons.trash"></span> Delete
          </button>
        </div>

        <div v-if="editingNote" class="note-editor">
          <input type="text" v-model="editNoteTitle" class="note-editor-title-input" placeholder="Note title" />
          <input type="text" v-model="editNoteTags" class="note-editor-title-input" placeholder="Tags (comma separated)" />
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
            <span class="note-detail-date">{{ fmtDateShort(store.viewingNote.created_at) }}</span>
          </div>
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
