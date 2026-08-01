const { ref, nextTick, watch } = window.Vue;
import { store } from "../store.js";
import { renderMarkdown } from "../markdown.js";

export default {
  setup() {
    const draft = ref("");
    const chatWindow = ref(null);
    const composing = ref(false);

    async function scrollDown() {
      await nextTick();
      if (chatWindow.value) chatWindow.value.scrollTop = chatWindow.value.scrollHeight;
    }

    function onCompositionStart() {
      composing.value = true;
    }
    function onCompositionEnd() {
      composing.value = false;
    }

    async function onKeydown(e) {
      if (e.key !== "Enter" || e.shiftKey) return;
      // Don't send while an IME (e.g. Chinese/Japanese input) is still
      // composing - that Enter is confirming a candidate, not "send".
      if (composing.value || e.isComposing || e.keyCode === 229) return;
      e.preventDefault();
      await send();
    }

    async function send() {
      const text = draft.value;
      if (!text.trim()) return;
      draft.value = "";
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
      store, draft, chatWindow, onKeydown, onCompositionStart, onCompositionEnd, send, renderMarkdown,
      fmtTokens, fmtCost,
    };
  },
  template: `
  <div class="main-panel chat-panel">
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
      <textarea v-model="draft"
                placeholder="Type a message… (Enter to send, Shift+Enter for a new line)"
                @keydown="onKeydown"
                @compositionstart="onCompositionStart"
                @compositionend="onCompositionEnd"></textarea>
      <button class="btn" :disabled="store.sending || !draft.trim()" @click="send">
        <span v-if="store.sending" class="spinner"></span>{{ store.sending ? ' Sending…' : 'Send' }}
      </button>
    </div>
  </div>
  `,
};
