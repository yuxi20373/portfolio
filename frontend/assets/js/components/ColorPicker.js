const { ref } = window.Vue;
import { icons } from "../icons.js";
import { NOTE_COLORS } from "../noteColors.js";

// "+"-triggered swatch row for picking a note's color (see Note.color) -
// sits beside the Tags field in every note create/edit form. Collapsed by
// default; clicking the selected swatch again clears the color.
export default {
  props: {
    modelValue: { type: String, default: "" },
  },
  emits: ["update:modelValue"],
  setup(props, { emit }) {
    const open = ref(false);

    function pick(key) {
      emit("update:modelValue", props.modelValue === key ? "" : key);
    }

    return { open, pick, icons, NOTE_COLORS };
  },
  template: `
  <span class="note-color-row">
    <button type="button" class="icon-btn" title="Choose a color" @click="open = !open" v-html="icons.plus"></button>
    <template v-if="open">
      <button type="button" v-for="c in NOTE_COLORS" :key="c.key"
              class="color-swatch" :class="['note-color-' + c.key, { selected: modelValue === c.key }]"
              :title="c.label" @click="pick(c.key)"></button>
    </template>
  </span>
  `,
};
