// test_agent 的 skill 檔案管理頁 - 內容存在 Postgres(見後端
// app/agent/test_agent/skill_store.py),不是本地檔案,這裡存檔立刻對
// Test Agent 頁面生效,不用改本地檔案、不用重新部署。fab/role 兩個欄位
// 也是自由輸入 - 建一個全新的 fab 或 function,存檔後就會出現在 Test
// Agent 頁面的身分選擇器裡(見 store.createSkillFile)。
const { ref, computed, onMounted } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";

export default {
  setup() {
    const selected = ref(null); // {fab, role, skill_name} | null
    const editContent = ref("");
    const loadingContent = ref(false);
    const saving = ref(false);

    const creatingNew = ref(false);
    const newFab = ref("");
    const newRole = ref("");
    const newSkillName = ref("");
    const newContent = ref("");
    const creating = ref(false);

    onMounted(() => {
      store.loadSkillFiles();
    });

    // fab -> [{fab, role, skill_name, updated_at}, ...], role="_shared" 排最前面
    const groupedByFab = computed(() => {
      const groups = {};
      for (const f of store.skillFiles) {
        (groups[f.fab] ||= []).push(f);
      }
      for (const fab in groups) {
        groups[fab].sort((a, b) => {
          if (a.role === "_shared" && b.role !== "_shared") return -1;
          if (b.role === "_shared" && a.role !== "_shared") return 1;
          return a.role.localeCompare(b.role) || a.skill_name.localeCompare(b.skill_name);
        });
      }
      return groups;
    });
    const fabs = computed(() => Object.keys(groupedByFab.value).sort());

    function isSelected(entry) {
      return !!selected.value && selected.value.fab === entry.fab && selected.value.role === entry.role && selected.value.skill_name === entry.skill_name;
    }

    async function selectSkill(entry) {
      creatingNew.value = false;
      selected.value = entry;
      loadingContent.value = true;
      try {
        editContent.value = await store.loadSkillContent(entry.fab, entry.role, entry.skill_name);
      } finally {
        loadingContent.value = false;
      }
    }

    async function saveContent() {
      if (!selected.value) return;
      saving.value = true;
      try {
        await store.saveSkillContent(selected.value.fab, selected.value.role, selected.value.skill_name, editContent.value);
      } finally {
        saving.value = false;
      }
    }

    async function removeSkill(entry) {
      if (!confirm(`Delete skill "${entry.fab}/${entry.role}/${entry.skill_name}"? This can't be undone.`)) return;
      await store.deleteSkillFile(entry.fab, entry.role, entry.skill_name);
      if (isSelected(entry)) {
        selected.value = null;
        editContent.value = "";
      }
    }

    function startNewSkill() {
      selected.value = null;
      creatingNew.value = true;
      newFab.value = "";
      newRole.value = "";
      newSkillName.value = "";
      newContent.value = "---\nname: \ndescription: \n---\n\n";
    }

    function cancelNewSkill() {
      creatingNew.value = false;
    }

    const canCreate = computed(() => newFab.value.trim() && newRole.value.trim() && newSkillName.value.trim());

    async function confirmCreate() {
      if (!canCreate.value) return;
      creating.value = true;
      try {
        await store.createSkillFile(newFab.value.trim(), newRole.value.trim(), newSkillName.value.trim(), newContent.value);
        creatingNew.value = false;
        await selectSkill({ fab: newFab.value.trim(), role: newRole.value.trim(), skill_name: newSkillName.value.trim() });
      } finally {
        creating.value = false;
      }
    }

    function fmtDate(iso) {
      if (!iso) return "";
      return new Date(iso).toLocaleString();
    }

    return {
      icons, store, fabs, groupedByFab, selected, editContent, loadingContent, saving,
      isSelected, selectSkill, saveContent, removeSkill,
      creatingNew, newFab, newRole, newSkillName, newContent, canCreate, creating,
      startNewSkill, cancelNewSkill, confirmCreate, fmtDate,
    };
  },
  template: `
  <div class="main-panel skill-manage-panel">
    <div class="skill-manage-toolbar">
      <h1 class="page-title" style="margin:0;">SKILL MANAGE</h1>
      <div class="row" style="gap:8px;">
        <button class="btn" @click="startNewSkill" v-html="icons.plus"></button>
        <button class="icon-btn" title="Back to Test Agent" @click="store.skillManageOpen = false" v-html="icons.close"></button>
      </div>
    </div>

    <div class="skill-manage-body">
      <div class="skill-manage-list">
        <div v-for="fab in fabs" :key="fab" class="skill-manage-fab-group">
          <div class="skill-manage-fab-label">{{ fab }}</div>
          <div v-for="entry in groupedByFab[fab]" :key="entry.role + '/' + entry.skill_name"
               class="session-item" :class="{active: isSelected(entry)}" @click="selectSkill(entry)">
            <span class="session-title">{{ entry.role }} / {{ entry.skill_name }}</span>
            <span class="session-actions">
              <button class="mini-icon-btn" title="Delete" @click.stop="removeSkill(entry)" v-html="icons.trash"></button>
            </span>
          </div>
        </div>
        <div v-if="!store.skillFiles.length" class="empty-state">No skills yet - click + to create one</div>
      </div>

      <div class="skill-manage-editor">
        <template v-if="creatingNew">
          <div class="skill-manage-new-form">
            <div class="hint">新的 fab 或 function 存檔後會立刻出現在 Test Agent 的身分選擇器裡</div>
            <input class="note-editor-title-input" v-model="newFab" placeholder="Fab (e.g. L8A)" />
            <input class="note-editor-title-input" v-model="newRole" placeholder="Role: _shared 或 function 名稱 (e.g. Cell)" />
            <input class="note-editor-title-input" v-model="newSkillName" placeholder="Skill name (e.g. generate-report)" />
            <textarea v-model="newContent" class="wiki-edit-textarea" rows="16" placeholder="SKILL.md content"></textarea>
            <div class="row" style="gap:8px;">
              <button class="btn" :disabled="!canCreate || creating" @click="confirmCreate">
                <span v-if="creating" class="spinner"></span>{{ creating ? ' Creating…' : 'Create' }}
              </button>
              <button class="btn secondary" @click="cancelNewSkill">Cancel</button>
            </div>
          </div>
        </template>
        <template v-else-if="selected">
          <div class="skill-manage-editor-header">
            {{ selected.fab }} / {{ selected.role }} / {{ selected.skill_name }}
            <span v-if="selected.updated_at" class="msg-meta">Updated {{ fmtDate(selected.updated_at) }}</span>
          </div>
          <div v-if="loadingContent" class="hint">Loading…</div>
          <template v-else>
            <textarea v-model="editContent" class="wiki-edit-textarea" rows="20"></textarea>
            <div class="row" style="gap:8px;">
              <button class="btn" :disabled="saving" @click="saveContent">
                <span v-if="saving" class="spinner"></span>{{ saving ? ' Saving…' : 'Save' }}
              </button>
            </div>
          </template>
        </template>
        <div v-else class="empty-state">Select a skill to edit, or click + to create a new one</div>
      </div>
    </div>
  </div>
  `,
};
