import { store } from "../store.js";
import { icons } from "../icons.js";
import DrawerShell from "./DrawerShell.js";

export default {
  components: { DrawerShell },
  props: ["sessionId", "activeModel"],
  emits: ["close"],
  setup(props, { emit }) {
    function fmtContext(n) {
      if (!n) return "—";
      if (n >= 1_000_000) return (n / 1_000_000).toFixed(2).replace(/\.?0+$/, "") + "M";
      return Math.round(n / 1000) + "K";
    }

    function fmtPrice(n) {
      return "$" + n.toFixed(2);
    }

    async function use(modelId) {
      await store.switchModel(props.sessionId, modelId);
      emit("close");
    }

    return { store, icons, fmtContext, fmtPrice, use };
  },
  template: `
  <DrawerShell title="Compare models" @close="$emit('close')">
    <p class="hint">
      Non-codex models, GPT-4o and newer only. Prices are USD per 1M tokens.
      ★ marks the recommended default for everyday chat and summarization.
    </p>
    <div class="compare-table-wrap">
      <table class="compare-table">
        <thead>
          <tr>
            <th></th>
            <th>Model</th>
            <th>Input</th>
            <th>Output</th>
            <th>Context</th>
            <th>Cutoff</th>
            <th>Best for</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in store.models" :key="m.id" :class="{ recommended: m.recommended, active: m.id === activeModel }">
            <td class="compare-star" v-html="m.recommended ? icons.star : ''"></td>
            <td>{{ m.name }}</td>
            <td>{{ fmtPrice(m.input_price) }}</td>
            <td>{{ fmtPrice(m.output_price) }}</td>
            <td>{{ fmtContext(m.context_window) }}</td>
            <td>{{ m.knowledge_cutoff || '—' }}</td>
            <td class="compare-blurb">{{ m.blurb }}</td>
            <td>
              <button class="btn secondary" :disabled="m.id === activeModel" @click="use(m.id)">
                {{ m.id === activeModel ? 'Current' : 'Use' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </DrawerShell>
  `,
};
