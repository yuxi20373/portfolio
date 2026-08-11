const { ref } = window.Vue;
import { api } from "../api.js";
import { store } from "../store.js";
import { renderMarkdown } from "../markdown.js";
import DrawerShell from "./DrawerShell.js";

export default {
  components: { DrawerShell },
  props: ["entry"],
  emits: ["close"],
  setup(props, { emit }) {
    const instruction = ref("");
    const loading = ref(false);
    const proposal = ref(null); // {summary, content} - not yet saved
    const composing = ref(false);

    function onCompositionStart() {
      composing.value = true;
    }
    function onCompositionEnd() {
      composing.value = false;
    }

    async function onKeydown(e) {
      if (e.key !== "Enter" || e.shiftKey) return;
      if (composing.value || e.isComposing || e.keyCode === 229) return;
      e.preventDefault();
      await submitInstruction();
    }

    async function submitInstruction() {
      const text = instruction.value.trim();
      if (!text) return;
      loading.value = true;
      try {
        const base = proposal.value; // keep refining the latest proposal if there is one
        proposal.value = await api.post(`/api/wiki/${props.entry.id}/adjust/preview`, {
          instruction: text,
          base_content: base ? base.content : null,
          base_summary: base ? base.summary : null,
        });
        // 只有成功才清空 - 這支 API 會做即時網路搜尋+LLM 生成,偶爾會逾時/失敗,
        // 之前是不管成功失敗都先清空,失敗時使用者打的字就整個不見、畫面又
        // 退回空白提示,看起來像抽屜整個被收起來重置了,其實只是沒顯示錯誤。
        instruction.value = "";
      } catch (e) {
        store.showNotice(e.message || "Adjust failed, please try again", "error");
      } finally {
        loading.value = false;
      }
    }

    async function applyProposal() {
      if (!proposal.value) return;
      loading.value = true;
      try {
        await store.applyWikiAdjustment(props.entry.id, proposal.value.summary, proposal.value.content);
        emit("close");
      } finally {
        loading.value = false;
      }
    }

    function discardProposal() {
      proposal.value = null;
    }

    return {
      instruction,
      loading,
      proposal,
      onCompositionStart,
      onCompositionEnd,
      onKeydown,
      submitInstruction,
      applyProposal,
      discardProposal,
      renderMarkdown,
    };
  },
  template: `
  <DrawerShell :title="'Adjust: ' + entry.title" @close="$emit('close')">
    <div v-if="!proposal && !loading" class="hint">
      Describe how you'd like this entry's headings or content changed - e.g.
      "merge the History and Trends sections" or "add more detail under Care and Keeping".
    </div>

    <div v-if="proposal" class="adjust-preview">
      <div class="adjust-preview-label">Proposed changes</div>
      <div class="markdown-body" v-html="renderMarkdown(proposal.content)"></div>
      <div class="drawer-actions">
        <button class="btn" :disabled="loading" @click="applyProposal">
          <span v-if="loading" class="spinner"></span>{{ loading ? ' Applying…' : 'Apply changes' }}
        </button>
        <button class="btn secondary" :disabled="loading" @click="discardProposal">Discard, try again</button>
      </div>
    </div>

    <div v-if="loading && !proposal" class="loading-row"><span class="spinner"></span> Thinking…</div>

    <template #footer>
      <textarea v-model="instruction" rows="2" placeholder="Type an instruction…"
                @keydown="onKeydown" @compositionstart="onCompositionStart" @compositionend="onCompositionEnd"></textarea>
      <button class="btn" :disabled="loading || !instruction.trim()" @click="submitInstruction">Send</button>
    </template>
  </DrawerShell>
  `,
};
