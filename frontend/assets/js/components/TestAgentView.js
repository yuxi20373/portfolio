// 跟 ChatView.js 幾乎一樣(訊息列表、輸入框、send 邏輯全部重用
// store.sendMessage,跟一般聊天是同一套 ChatSession/ChatMessage),差別只在
// 開始聊天之前要先選好要模擬的 fab/function 身分(可以選多個,測試跨身分
// 委派 - 見 store.js 的 createTestAgentSession)。不像 /test-subagent、
// /test-pa 那樣用聊天指令切換,因為身分是「建立這個 session 時就決定」的
// 設定,不是聊天中隨時能改的模式。
const { ref, computed, nextTick, watch, onMounted } = window.Vue;
import { store } from "../store.js";
import { renderMarkdown } from "../markdown.js";
import { icons } from "../icons.js";

export default {
  setup() {
    const draft = ref("");
    const chatWindow = ref(null);
    const draftInput = ref(null);

    onMounted(() => {
      if (!store.testAgentIdentityOptions.length) store.loadTestAgentIdentityOptions();
    });

    // --- 身分選擇器 - 一列一個 (fab, function),可以加多列測試多重身分 ---
    const pickerRows = ref([{ fab: "", function: "" }]);

    function functionsFor(fab) {
      const opt = store.testAgentIdentityOptions.find((o) => o.fab === fab);
      return opt ? opt.functions : [];
    }

    function addIdentityRow() {
      pickerRows.value.push({ fab: "", function: "" });
    }
    function removeIdentityRow(i) {
      pickerRows.value.splice(i, 1);
    }
    // 換 fab 要把 function 重置掉 - 舊 fab 選的 function 名稱換了 fab 不一定存在
    function onFabChange(row) {
      row.function = "";
    }

    const canStart = computed(
      () => pickerRows.value.length > 0 && pickerRows.value.every((r) => r.fab && r.function)
    );

    const startingSession = ref(false);
    async function startTestSession() {
      if (!canStart.value) return;
      startingSession.value = true;
      try {
        const identities = pickerRows.value.map((r) => ({ fab: r.fab, function: r.function }));
        await store.createTestAgentSession(identities);
        pickerRows.value = [{ fab: "", function: "" }];
      } finally {
        startingSession.value = false;
      }
    }

    // 目前是不是正看著一個已經建立好的 test_agent session(而不是還在選身分)
    const inTestSession = computed(
      () => !!store.currentSession && store.currentSession.experimental_agent === "test_agent"
    );

    // 回到身分選擇畫面,開一個新的測試組合 - 不刪掉舊 session,舊的還在側欄
    // 抽屜列表裡,可以隨時點回去繼續(見 Sidebar.js 的 test-agent 分支)。
    const newTestSession = store.resetTestAgentSelection.bind(store);

    const identitiesLabel = computed(() => {
      const s = store.currentSession;
      if (!s || !s.test_agent_identities) return "";
      return s.test_agent_identities.map((i) => `${i.fab}/${i.function}`).join("、");
    });

    async function scrollDown() {
      await nextTick();
      if (chatWindow.value) chatWindow.value.scrollTop = chatWindow.value.scrollHeight;
    }

    function autoGrow(e) {
      const el = e.target;
      el.style.height = "auto";
      el.style.height = el.scrollHeight + "px";
    }

    async function send() {
      const text = draft.value;
      if (!text.trim() || !inTestSession.value) return;
      draft.value = "";
      if (draftInput.value) draftInput.value.style.height = "";
      await store.sendMessage(text);
      await scrollDown();
    }

    watch(() => store.currentSessionId, scrollDown);

    function fmtTokens(n) {
      if (n == null) return "0";
      if (n >= 1000) {
        const k = n / 1000;
        return (Number.isInteger(k) ? k : k.toFixed(1)) + "k";
      }
      return String(n);
    }

    function fmtCost(c) {
      if (c == null) return "N/A";
      return "$" + c.toFixed(4);
    }

    return {
      store, icons, draft, chatWindow, draftInput, autoGrow, send, renderMarkdown,
      fmtTokens, fmtCost,
      pickerRows, functionsFor, addIdentityRow, removeIdentityRow, onFabChange,
      canStart, startingSession, startTestSession, inTestSession, newTestSession, identitiesLabel,
    };
  },
  template: `
  <div class="main-panel chat-panel test-agent-panel">
    <div class="test-agent-toolbar">
      <h1 class="page-title" style="margin:0;">TEST AGENT</h1>
      <button v-if="inTestSession" class="btn secondary" @click="newTestSession">New test session</button>
    </div>

    <div v-if="!inTestSession" class="test-agent-picker">
      <div class="hint">選擇要模擬的 fab/function 身分(可以加多個,測試問題橫跨多個身分時 agent 會不會分別委派)</div>
      <div v-for="(row, i) in pickerRows" :key="i" class="test-agent-identity-row">
        <select v-model="row.fab" class="note-editor-title-input" @change="onFabChange(row)">
          <option value="" disabled>Fab</option>
          <option v-for="o in store.testAgentIdentityOptions" :key="o.fab" :value="o.fab">{{ o.fab }}</option>
        </select>
        <select v-model="row.function" class="note-editor-title-input" :disabled="!row.fab">
          <option value="" disabled>Function</option>
          <option v-for="f in functionsFor(row.fab)" :key="f" :value="f">{{ f }}</option>
        </select>
        <button v-if="pickerRows.length > 1" class="mini-icon-btn" title="Remove identity" @click="removeIdentityRow(i)">×</button>
      </div>
      <div class="row" style="gap:8px;">
        <button class="icon-btn" title="Add another identity" @click="addIdentityRow" v-html="icons.plus"></button>
        <button class="btn" :disabled="!canStart || startingSession" @click="startTestSession">
          <span v-if="startingSession" class="spinner"></span>{{ startingSession ? ' Starting…' : 'Start test session' }}
        </button>
      </div>
      <div v-if="!store.testAgentIdentityOptions.length" class="empty-state">No skill folders found under process_agent/skills/{FAB}/{FUNCTION}/</div>
    </div>

    <template v-else>
      <div class="chat-toolbar">
        <span class="mode-badge experimental" title="test_agent 沙盒模式 - 身分固定在建立 session 時就決定">
          <span class="mode-badge-icon" v-html="icons.flame"></span>
          {{ identitiesLabel }}
        </span>
      </div>
      <div class="chat-window" ref="chatWindow">
        <div v-for="m in store.messages" :key="m.id" class="msg" :class="m.role">
          <div v-if="m.role === 'assistant'" v-html="renderMarkdown(m.content)"></div>
          <div v-else>{{ m.content }}</div>
          <div v-if="m.role === 'assistant' && m.model" class="msg-meta">
            {{ m.model }} · {{ fmtTokens((m.input_tokens || 0) + (m.output_tokens || 0)) }} tokens · {{ fmtCost(m.cost_usd) }}
          </div>
        </div>
        <div v-if="store.sending" class="msg assistant hint-msg"><span class="spinner"></span> Thinking…</div>
      </div>
      <div class="chat-input">
        <textarea ref="draftInput" v-model="draft"
                  placeholder="Type a message… (Enter for a new line, click Send to send)"
                  @input="autoGrow"></textarea>
        <button class="btn" :disabled="store.sending || !draft.trim()" @click="send">
          <span v-if="store.sending" class="spinner"></span>{{ store.sending ? ' Sending…' : 'Send' }}
        </button>
      </div>
    </template>
  </div>
  `,
};
