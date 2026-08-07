const { ref, computed } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";
import { renderMarkdown } from "../markdown.js";
import ColorPicker from "./ColorPicker.js";
import TagPicker from "./TagPicker.js";

const MARKDOWN_HELP = `
  <div><code># Heading</code></div>
  <div><code>**bold**</code> &nbsp; <code>*italic*</code></div>
  <div><code>- list item</code></div>
  <div><code>1. numbered item</code></div>
  <div><code>- [ ] todo</code> &nbsp; <code>- [x] done</code></div>
  <div><code>[text](url)</code></div>
  <div><code>\`inline code\`</code></div>
  <div><code>&gt; quote</code></div>
  <div><code>:smile:</code> emoji(自訂的也可以,見 Manage 頁的 Emoji Manage)</div>
  <div><code>==peach:text==</code> / <code>==sage:text==</code> / <code>==sky:text==</code> 底色</div>
`;

export default {
  components: { ColorPicker, TagPicker },
  setup() {
    // 這頁預設一律顯示全部筆記列表;側欄的「Template Manage」按鈕
    // (Sidebar.js 的 'notes' 分支)會把整個主畫面切換成 Template Manage 畫面
    // (見下面的 store.templateManageOpen)。

    const sortMode = ref("date"); // "date" | "tag"

    async function pickTagFilter(tag) {
      store.notesTagFilter = store.notesTagFilter === tag ? null : tag;
      await store.loadAllNotes();
    }

    // notesTagFilter 是套在 store.allNotes 上的伺服器端篩選,By Date/By Tag
    // 兩種排序都是從同一份 allNotes 算出來的 - 切走 By Tag 模式時如果篩選還
    // 留著,By Date 就會漏掉沒套用那個 tag 的筆記,看起來像當天筆記不見了。
    // 所以離開 By Tag 就把篩選清掉。
    async function setSortMode(mode) {
      sortMode.value = mode;
      if (mode !== "tag" && store.notesTagFilter) {
        store.notesTagFilter = null;
        await store.loadAllNotes();
      }
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

    // Tag 的建立/改名/刪除都搬到 Manage 畫面的 Tag Manage 區塊了(見下面)- 這裡
    // 的篩選 chips 純粹拿來篩選,不再放刪除按鈕。新 tag 名稱只要直接打在某則
    // 筆記的 Tags 欄位存檔就會自動註冊(見 store.createNote/updateNote 的
    // ensureNoteTags),不需要另外的「新增 tag」入口。

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
    const newNoteTemplateId = ref("");
    const savingNewNote = ref(false);

    function toggleNewNote() {
      store.viewingTemplate = null; // the "+" always means "add a note", regardless of what's showing
      showNewNote.value = !showNewNote.value;
      newNoteTitle.value = "";
      newNoteContent.value = "";
      newNoteTags.value = "";
      newNoteColor.value = "";
      newNoteTemplateId.value = "";
    }

    // 從已存的 template 帶入草稿內容(見 Manage 畫面)- 只是單次複製,筆記
    // 不會跟這個 template 保持關聯。
    function applyNoteTemplate() {
      const t = store.noteTemplates.find((x) => x.id === Number(newNoteTemplateId.value));
      if (!t) return;
      newNoteContent.value = t.content;
      if (t.tags && t.tags.length) newNoteTags.value = t.tags.join(", ");
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

    async function openNote(id, siblingIds) {
      editingNote.value = false;
      await store.openNoteView(id, siblingIds);
    }

    // 左右瀏覽同一組(同一天或同一個 tag,看 store.viewingNoteSiblings 是哪個
    // list 傳進來的)裡的上一則/下一則。
    const canStepNotePrev = computed(() => {
      const ids = store.viewingNoteSiblings;
      return !!store.viewingNote && ids.indexOf(store.viewingNote.id) > 0;
    });
    const canStepNoteNext = computed(() => {
      const ids = store.viewingNoteSiblings;
      if (!store.viewingNote) return false;
      const idx = ids.indexOf(store.viewingNote.id);
      return idx >= 0 && idx < ids.length - 1;
    });

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

    // --- Template Manage 畫面(見 Sidebar.js 的「Template Manage」按鈕、
    // store.templateManageOpen)- 預設是純清單(每一列自己有 Edit/Delete),
    // 下面一個「+」新增。名稱/tags/內容表單只有在點「+」或某一列的 Edit
    // 才會出現(showTemplateForm)。store.viewingTemplate 同時也代表
    // 「表單目前載入的是哪一個」(null = 空白、準備新增)。 ---

    const showTemplateForm = ref(false);
    const tmName = ref("");
    const tmContent = ref("");
    const tmTags = ref("");
    const tmSaving = ref(false);

    function selectTemplate(t) {
      store.viewingTemplate = t;
      tmName.value = t.name;
      tmContent.value = t.content;
      tmTags.value = (t.tags || []).join(", ");
    }

    function startNewTemplate() {
      store.viewingTemplate = null;
      tmName.value = "";
      tmContent.value = "";
      tmTags.value = "";
      showTemplateForm.value = true;
    }

    function editTemplateRow(t) {
      selectTemplate(t);
      showTemplateForm.value = true;
    }

    function cancelTemplateForm() {
      showTemplateForm.value = false;
    }

    async function saveTemplate() {
      if (!tmName.value.trim()) return;
      tmSaving.value = true;
      try {
        const tags = tmTags.value.split(",").map((t) => t.trim()).filter(Boolean);
        if (store.viewingTemplate) {
          await store.updateNoteTemplate(store.viewingTemplate.id, { name: tmName.value.trim(), content: tmContent.value, tags });
        } else {
          const t = await store.createNoteTemplate(tmName.value.trim(), tmContent.value, tags);
          selectTemplate(t);
          store.showNotice("Template created");
        }
        showTemplateForm.value = false;
      } catch (err) {
        store.showNotice("Couldn't save template", "error");
      } finally {
        tmSaving.value = false;
      }
    }

    async function deleteTemplateRow(t) {
      if (confirm(`Delete template "${t.name}"?`)) {
        await store.deleteNoteTemplate(t.id);
      }
    }

    function closeTemplateManage() {
      store.templateManageOpen = false;
      store.viewingTemplate = null;
      showTemplateForm.value = false;
    }

    // --- Tag Manage(同一個 Manage 畫面裡的第二個區塊)---

    async function promptNewTag() {
      const name = prompt("Tag name");
      if (name && name.trim()) {
        try {
          await store.ensureNoteTags([name.trim()]);
          store.showNotice("Tag created");
        } catch (err) {
          store.showNotice("Couldn't create tag", "error");
        }
      }
    }

    async function renameTag(t) {
      const name = prompt("Tag name", t.name);
      if (name && name.trim() && name.trim() !== t.name) {
        try {
          await store.updateNoteTag(t.id, name.trim());
        } catch (err) {
          store.showNotice("Couldn't rename tag", "error");
        }
      }
    }

    async function deleteTagRow(t) {
      if (confirm(`Delete tag "${t.name}"? Notes already tagged with it keep the tag text - this only removes it from the saved list.`)) {
        await store.deleteNoteTag(t.id);
      }
    }

    // --- Emoji Manage(同一個 Manage 畫面裡的第三個區塊)- 上傳自訂
    // :shortcode: emoji,見 markdown.js。圖片本身的縮圖處理在後端做
    // (routers/emoji.py),前端只負責選檔案跟叫 API。---

    const newEmojiShortcode = ref("");
    const newEmojiFile = ref(null);
    const uploadingEmoji = ref(false);

    function onEmojiFileChange(e) {
      newEmojiFile.value = e.target.files[0] || null;
    }

    async function uploadEmoji() {
      const shortcode = newEmojiShortcode.value.trim().toLowerCase();
      if (!shortcode || !newEmojiFile.value) return;
      uploadingEmoji.value = true;
      try {
        await store.uploadCustomEmoji(shortcode, newEmojiFile.value);
        store.showNotice("Emoji created");
        newEmojiShortcode.value = "";
        newEmojiFile.value = null;
      } catch (err) {
        store.showNotice("Couldn't create emoji", "error");
      } finally {
        uploadingEmoji.value = false;
      }
    }

    async function deleteEmojiRow(e) {
      if (confirm(`Delete emoji ":${e.shortcode}:"?`)) {
        await store.deleteCustomEmoji(e.id);
      }
    }

    return {
      store, icons, renderMarkdown, MARKDOWN_HELP,
      sortMode, setSortMode, pickTagFilter, allNotesByTag,
      fmtDateShort, fmtDateLabel,
      showNewNote, newNoteTitle, newNoteContent, newNoteTags, newNoteColor, newNoteTemplateId, savingNewNote,
      toggleNewNote, saveNewNote, applyNoteTemplate,
      editingNote, editNoteTitle, editNoteContent, editNoteTags, editNoteColor, editNotePreview, editNoteHelp, savingNoteEdit,
      openNote, closeNote, startEditNote, cancelEditNote, saveNoteEdit, removeNote,
      canStepNotePrev, canStepNoteNext,
      showTemplateForm, tmName, tmContent, tmTags, tmSaving,
      startNewTemplate, editTemplateRow, cancelTemplateForm, saveTemplate, deleteTemplateRow, closeTemplateManage,
      promptNewTag, renameTag, deleteTagRow,
      newEmojiShortcode, uploadingEmoji, onEmojiFileChange, uploadEmoji, deleteEmojiRow,
    };
  },
  template: `
  <div class="main-panel notes-panel">
    <template v-if="store.templateManageOpen">
      <div class="template-manage">
        <div class="template-manage-header row between">
          <h1 class="page-title">MANAGE</h1>
          <button class="icon-btn" title="Back to notes" @click="closeTemplateManage" v-html="icons.close"></button>
        </div>

        <template v-if="!showTemplateForm">
          <div class="manage-section">
            <div class="manage-section-header row between">
              <h3>Template List</h3>
              <button class="icon-btn" title="New template" @click="startNewTemplate" v-html="icons.plus"></button>
            </div>
            <div class="manage-card-grid">
              <div v-for="t in store.noteTemplates" :key="t.id" class="manage-card" @click="editTemplateRow(t)">
                <button class="mini-icon-btn manage-card-delete" title="Delete" @click.stop="deleteTemplateRow(t)" v-html="icons.trash"></button>
                <div class="manage-card-title">{{ t.name }}</div>
                <div v-if="t.tags && t.tags.length" class="tag-row">
                  <span class="tag" v-for="tg in t.tags" :key="tg">{{ tg }}</span>
                </div>
              </div>
              <div v-if="!store.noteTemplates.length" class="empty-state">No templates yet</div>
            </div>
          </div>

          <div class="manage-section">
            <div class="manage-section-header row between">
              <h3>Tag Manage</h3>
              <button class="icon-btn" title="New tag" @click="promptNewTag" v-html="icons.plus"></button>
            </div>
            <div class="tag-row">
              <span v-for="t in store.noteTags" :key="t.id" class="tag notes-tag-manage">
                <span class="clickable" @click="renameTag(t)">{{ t.name }}</span>
                <button class="mini-icon-btn" title="Delete" @click="deleteTagRow(t)">×</button>
              </span>
              <div v-if="!store.noteTags.length" class="empty-state">No tags yet</div>
            </div>
          </div>

          <div class="manage-section">
            <div class="manage-section-header">
              <h3>Emoji Manage</h3>
            </div>
            <div class="emoji-upload-row">
              <input type="text" v-model="newEmojiShortcode" class="note-editor-title-input" style="margin-bottom:0; max-width:160px;" placeholder="shortcode" />
              <input type="file" accept="image/*" @change="onEmojiFileChange" />
              <button class="btn" :disabled="uploadingEmoji || !newEmojiShortcode.trim()" @click="uploadEmoji">
                <span v-if="uploadingEmoji" class="spinner"></span>{{ uploadingEmoji ? ' Uploading…' : 'Add emoji' }}
              </button>
            </div>
            <div class="emoji-grid">
              <div v-for="e in store.customEmoji" :key="e.id" class="emoji-card">
                <button class="mini-icon-btn emoji-card-delete" title="Delete" @click="deleteEmojiRow(e)">×</button>
                <img class="emoji-card-img" :src="e.url" alt="" />
                <div class="emoji-card-code">:{{ e.shortcode }}:</div>
              </div>
              <div v-if="!store.customEmoji.length" class="empty-state">No custom emoji yet</div>
            </div>
          </div>
        </template>

        <div v-else class="template-manage-form">
          <input type="text" v-model="tmName" class="note-editor-title-input" placeholder="Template name" />
          <div class="row" style="gap:8px; align-items:center; margin-bottom:8px;">
            <input type="text" v-model="tmTags" class="note-editor-title-input" style="flex:1; margin-bottom:0;" placeholder="Tags (comma separated)" />
            <TagPicker v-model="tmTags" :options="store.noteTags" />
          </div>
          <textarea v-model="tmContent" class="note-editor-textarea" rows="12" placeholder="Template content (Markdown)…"></textarea>
          <div class="drawer-actions">
            <button class="btn" :disabled="tmSaving || !tmName.trim()" @click="saveTemplate">
              <span v-if="tmSaving" class="spinner"></span>{{ tmSaving ? ' Saving…' : (store.viewingTemplate ? 'Save' : 'Create template') }}
            </button>
            <button class="btn secondary" :disabled="tmSaving" @click="cancelTemplateForm">Cancel</button>
          </div>
        </div>
      </div>
    </template>

    <template v-else-if="store.loadingNoteView || store.viewingNote">
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
          <textarea v-if="!editNotePreview" v-model="editNoteContent" class="note-editor-textarea note-write-textarea" rows="10"></textarea>
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
              <button class="icon-btn" title="Previous" :disabled="!canStepNotePrev" @click="store.stepNote(-1)" v-html="icons.chevronLeft"></button>
              <button class="icon-btn" title="Next" :disabled="!canStepNoteNext" @click="store.stepNote(1)" v-html="icons.chevronRight"></button>
              <button class="icon-btn" title="Edit" @click="startEditNote" v-html="icons.edit"></button>
              <button class="icon-btn favorite-btn" :class="{active: store.viewingNote.is_favorited}" title="Favorite"
                      @click="store.toggleNoteFavorite(store.viewingNote.id)"
                      v-html="store.viewingNote.is_favorited ? icons.bookmarkFilled : icons.bookmark"></button>
              <button class="icon-btn" title="Delete" @click="removeNote" v-html="icons.trash"></button>
              <button class="icon-btn" title="Back to notes" @click="closeNote" v-html="icons.close"></button>
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
    </template>

    <template v-else>
      <h1 class="page-title">NOTES</h1>
      <div class="wiki-toolbar">
        <button class="icon-btn" title="New note" @click="toggleNewNote" v-html="icons.plus"></button>
        <div class="notes-tabs">
          <button class="notes-tab" :class="{active: sortMode === 'date'}" @click="setSortMode('date')">
            <span v-html="icons.calendar"></span> By Date
          </button>
          <button class="notes-tab" :class="{active: sortMode === 'tag'}" @click="setSortMode('tag')">
            <span v-html="icons.tag"></span> By Tag
          </button>
        </div>
      </div>

      <div v-if="showNewNote" class="note-editor">
        <input type="text" v-model="newNoteTitle" class="note-editor-title-input" placeholder="Note title" />
        <div class="row" style="gap:8px; align-items:center; margin-bottom:8px;">
          <input type="text" v-model="newNoteTags" class="note-editor-title-input" style="flex:1; margin-bottom:0;" placeholder="Tags (comma separated)" />
          <TagPicker v-model="newNoteTags" :options="store.noteTags" />
          <ColorPicker v-model="newNoteColor" />
        </div>
        <select v-if="store.noteTemplates.length" class="note-template-select" v-model="newNoteTemplateId" @change="applyNoteTemplate">
          <option value="" disabled>Apply template…</option>
          <option v-for="t in store.noteTemplates" :key="t.id" :value="t.id">{{ t.name }}</option>
        </select>
        <textarea v-model="newNoteContent" class="note-editor-textarea note-write-textarea" rows="8" placeholder="Write your note in Markdown…"></textarea>
        <button class="btn" :disabled="savingNewNote || !newNoteTitle.trim()" @click="saveNewNote">
          <span v-if="savingNewNote" class="spinner"></span>{{ savingNewNote ? ' Saving…' : 'Save note' }}
        </button>
      </div>

      <div v-if="sortMode === 'tag' && store.noteTags.length" class="tag-row notes-tag-filter">
        <span v-for="t in store.noteTags" :key="t.id" class="tag clickable" :class="{active: store.notesTagFilter === t.name}" @click="pickTagFilter(t.name)">{{ t.name }}</span>
      </div>

      <template v-if="sortMode === 'date'">
        <template v-for="group in store.allNotesByDate" :key="group.date">
          <div class="notes-date-sep">{{ fmtDateLabel(group.date) }}</div>
          <div class="notes-grid">
            <div v-for="n in group.notes" :key="n.id" class="card clickable" :class="n.color ? 'note-color-' + n.color : ''" @click="openNote(n.id, group.notes.map(x => x.id))">
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
            <div v-for="n in group.notes" :key="n.id" class="card clickable" :class="n.color ? 'note-color-' + n.color : ''" @click="openNote(n.id, group.notes.map(x => x.id))">
              <div class="day-card-title">{{ n.title }}</div>
            </div>
          </div>
        </template>
      </template>
      <div v-if="!store.allNotes.length" class="empty-state">No notes yet</div>
    </template>
  </div>
  `,
};
