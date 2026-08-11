const { ref, computed, nextTick, watch } = window.Vue;
import { store } from "../store.js";
import { renderMarkdown } from "../markdown.js";
import { icons } from "../icons.js";
import CompareModelsDrawer from "./CompareModelsDrawer.js";

export default {
  components: { CompareModelsDrawer },
  setup() {
    const draft = ref("");
    const chatWindow = ref(null);
    const draftInput = ref(null);
    const showCompare = ref(false);

    async function onModelChange(modelId) {
      if (!store.currentSessionId || !modelId) return;
      await store.switchModel(store.currentSessionId, modelId);
    }

    // 三種模式的徽章顯示 - experimental_agent 優先於 agent_mode(兩者在後端
    // 是互斥的,見 chat_service.py 的 _switch_mode/_switch_experimental_agent),
    // 之後多加別種實驗性 agent,這裡不用改,名稱直接顯示 experimental_agent
    // 的值。
    const modeBadge = computed(() => {
      const s = store.currentSession;
      if (!s) return null;
      if (s.experimental_agent) {
        return {
          cls: "experimental",
          icon: icons.flame,
          label: s.experimental_agent,
          title: `Experimental deep agent (${s.experimental_agent}): full history + tools, may write files to a virtual /results/. Type /normal to switch back.`,
        };
      }
      if (s.agent_mode) {
        return {
          cls: "agent",
          icon: icons.bot,
          label: "Deep Agent",
          title: "Deep agent: full history + web search / wiki tools",
        };
      }
      return {
        cls: "",
        icon: icons.chat,
        label: "Normal",
        title: "Normal chat: single-turn, no tools. Type /agent to switch.",
      };
    });

    async function scrollDown() {
      await nextTick();
      if (chatWindow.value) chatWindow.value.scrollTop = chatWindow.value.scrollHeight;
    }

    // Textarea grows with its content instead of a fixed height / manual
    // drag-resize handle - CSS max-height still caps it and lets it scroll
    // past that.
    function autoGrow(e) {
      const el = e.target;
      el.style.height = "auto";
      el.style.height = el.scrollHeight + "px";
    }

    async function send() {
      const text = draft.value;
      if (!text.trim()) return;
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
      fmtTokens, fmtCost, showCompare, onModelChange, modeBadge,
    };
  },
  template: `
  <div class="main-panel chat-panel">
    <div class="chat-toolbar" v-if="store.currentSession">
      <span class="mode-badge" :class="modeBadge.cls" :title="modeBadge.title">
        <span class="mode-badge-icon" v-html="modeBadge.icon"></span>
        {{ modeBadge.label }}
      </span>
      <select class="model-select" :value="store.currentSession.model" @change="onModelChange($event.target.value)">
        <option v-for="m in store.models" :key="m.id" :value="m.id">{{ m.recommended ? '★ ' : '' }}{{ m.name }}</option>
      </select>
      <button class="icon-btn compare-btn" title="Compare models" @click="showCompare = true" v-html="icons.compare"></button>
      <button class="icon-btn favorite-btn" :class="{active: store.currentSession.is_favorited}" title="Favorite this conversation"
              @click="store.toggleSessionFavorite(store.currentSessionId)"
              v-html="store.currentSession.is_favorited ? icons.bookmarkFilled : icons.bookmark"></button>
    </div>
    <div class="chat-window" ref="chatWindow">
      <div v-if="!store.currentSessionId" class="empty-state">Select or start a conversation</div>
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
    <CompareModelsDrawer v-if="showCompare && store.currentSession"
                          :sessionId="store.currentSessionId"
                          :activeModel="store.currentSession.model"
                          @close="showCompare = false" />
  </div>
  `,
};
