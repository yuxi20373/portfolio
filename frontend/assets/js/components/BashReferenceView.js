// Bash 指令查詢頁 - 兩個獨立功能:
// 1. 上面的搜尋框:輸入指令,底下即時列出字典裡符合的條目(見後端
//    routers/bash_reference.py 的 /search,資料存在 bash_commands 表,
//    見 backend/scripts/import_bash_commands.py 的批次匯入方式)。
// 2. 下面的欄位:貼一整串指令,交給 LLM 解析整體作用(/parse,不查字典,
//    純粹一次性呼叫,見 bash_reference_service.py)。
const { ref } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";
import { renderMarkdown } from "../markdown.js";
import { api } from "../api.js";

export default {
  setup() {
    const searchQuery = ref("");
    const results = ref([]);
    const searching = ref(false);

    async function onSearchInput() {
      const q = searchQuery.value.trim();
      if (!q) {
        results.value = [];
        return;
      }
      searching.value = true;
      try {
        results.value = await api.get(`/api/bash-reference/search?q=${encodeURIComponent(q)}`);
      } finally {
        searching.value = false;
      }
    }

    const parseInput = ref("");
    const parseResult = ref("");
    const parsing = ref(false);

    async function doParse() {
      const command = parseInput.value.trim();
      if (!command) return;
      parsing.value = true;
      parseResult.value = "";
      try {
        const r = await api.post("/api/bash-reference/parse", { command });
        parseResult.value = r.explanation;
      } finally {
        parsing.value = false;
      }
    }

    return {
      icons, renderMarkdown, store,
      searchQuery, results, searching, onSearchInput,
      parseInput, parseResult, parsing, doParse,
    };
  },
  template: `
  <div class="main-panel bash-ref-panel">
    <h1 class="page-title">BASH REFERENCE</h1>

    <div class="bash-ref-section">
      <h3>查指令</h3>
      <input type="text" class="note-editor-title-input" v-model="searchQuery" @input="onSearchInput"
             placeholder="輸入指令,例如 grep、chmod、find -name…" />
      <div class="bash-ref-results">
        <div v-for="r in results" :key="r.command" class="bash-ref-result">
          <div class="bash-ref-result-command">{{ r.command }}</div>
          <div class="bash-ref-result-desc">{{ r.description }}</div>
        </div>
        <div v-if="searching" class="hint">Searching…</div>
        <div v-else-if="searchQuery.trim() && !results.length" class="hint">No matches</div>
      </div>
    </div>

    <div class="bash-ref-section">
      <h3>解析整串指令</h3>
      <textarea v-model="parseInput" class="wiki-edit-textarea" rows="4"
                placeholder="貼上一整串指令(可以包含 | && || 等),讓 LLM 解釋整體作用…"></textarea>
      <button class="btn" :disabled="!parseInput.trim() || parsing" @click="doParse">
        <span v-if="parsing" class="spinner"></span>{{ parsing ? ' Parsing…' : 'Parse' }}
      </button>
      <div v-if="parseResult" class="bash-ref-parse-result" v-html="renderMarkdown(parseResult)"></div>
    </div>
  </div>
  `,
};
