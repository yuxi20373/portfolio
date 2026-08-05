const { ref, computed } = window.Vue;
import { icons } from "../icons.js";

// "list" icon-triggered checklist for picking from the existing (registered)
// tags - sits beside ColorPicker next to every note's Tags field. Reuses
// NotesView.js's .note-help-wrap/.note-help-popover pattern (same look as
// the Markdown help "?" popover).
export default {
  props: {
    modelValue: { type: String, default: "" }, // comma-separated tags string
    options: { type: Array, default: () => [] }, // [{id, name}]
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const open = ref(false);

    const selected = computed(() => props.modelValue.split(",").map((t) => t.trim()).filter(Boolean));

    function toggle(name) {
      const names = selected.value.includes(name)
        ? selected.value.filter((n) => n !== name)
        : [...selected.value, name];
      emit("update:modelValue", names.join(", "));
    }

    return { open, selected, toggle, icons };
  },
  template: `
  <span class="note-help-wrap">
    <button type="button" class="icon-btn" title="Pick from existing tags" @click="open = !open" v-html="icons.list"></button>
    <div v-if="open" class="note-help-popover tag-picker-popover">
      <label v-for="t in options" :key="t.id" class="tag-picker-item">
        <input type="checkbox" :checked="selected.includes(t.name)" @change="toggle(t.name)" />
        {{ t.name }}
      </label>
      <div v-if="!options.length" class="tag-picker-empty">No tags yet</div>
    </div>
  </span>
  `,
};
