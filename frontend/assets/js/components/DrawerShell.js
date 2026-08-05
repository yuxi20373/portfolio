const { ref, onBeforeUnmount } = window.Vue;

const DEFAULT_WIDTH = 420;
const MIN_WIDTH = 340;

export default {
  props: {
    title: { type: String, default: "" },
    // Starts at ~half the viewport width instead of DEFAULT_WIDTH - used by
    // the Note drawer (CalendarView.js/NotesView.js); still respects the
    // same maxWidth()/MIN_WIDTH resize bounds as every other drawer.
    wide: { type: Boolean, default: false },
  },
  emits: ["close"],
  setup(props, { emit }) {
    function maxWidth() {
      return Math.min(window.innerWidth - 80, 900);
    }

    const width = ref(props.wide ? Math.min(window.innerWidth / 2, maxWidth()) : DEFAULT_WIDTH);
    const resizing = ref(false);
    let startX = 0;
    let startWidth = 0;

    function onResizeStart(e) {
      resizing.value = true;
      startX = e.clientX;
      startWidth = width.value;
      window.addEventListener("mousemove", onResizeMove);
      window.addEventListener("mouseup", onResizeEnd);
      e.preventDefault();
    }

    function onResizeMove(e) {
      // Panel is anchored to the right edge, so dragging left grows it.
      const delta = startX - e.clientX;
      const next = startWidth + delta;
      width.value = Math.min(Math.max(next, MIN_WIDTH), maxWidth());
    }

    function onResizeEnd() {
      resizing.value = false;
      window.removeEventListener("mousemove", onResizeMove);
      window.removeEventListener("mouseup", onResizeEnd);
    }

    onBeforeUnmount(() => {
      window.removeEventListener("mousemove", onResizeMove);
      window.removeEventListener("mouseup", onResizeEnd);
    });

    return { width, resizing, onResizeStart };
  },
  template: `
  <div class="drawer-backdrop" @click.self="$emit('close')">
    <div class="drawer-panel" :style="{ width: width + 'px' }">
      <div class="drawer-resize-handle" :class="{active: resizing}" @mousedown="onResizeStart" title="Drag to resize"></div>
      <div class="drawer-header">
        <h3>{{ title }}</h3>
        <button class="icon-btn" @click="$emit('close')">✕</button>
      </div>
      <div class="drawer-body"><slot /></div>
      <div class="drawer-input" v-if="$slots.footer"><slot name="footer" /></div>
    </div>
  </div>
  `,
};
