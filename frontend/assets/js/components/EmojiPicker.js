const { ref, computed } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";
import { EMOJI_CATEGORIES, LINE_ICON_MAP } from "../emoji.js";

// 讓使用者用點的插入 :shortcode:,不用自己記/打語法 - 用在有 textarea 的地方
// (目前是 NotesView.js 的筆記編輯器),點下去會 emit 'pick' 把 shortcode
// 字串丟給外層,由外層決定怎麼插入游標位置(這裡不碰 textarea DOM)。
export default {
  emits: ["pick"],
  setup(props, { emit }) {
    const filter = ref("");

    const allCategories = computed(() => {
      const cats = [{ name: "Icons", icon: true, items: LINE_ICON_MAP }, ...EMOJI_CATEGORIES];
      if (store.customEmoji.length) {
        cats.unshift({
          name: "Custom",
          custom: true,
          items: Object.fromEntries(store.customEmoji.map((e) => [e.shortcode, e.url])),
        });
      }
      return cats;
    });

    const filteredCategories = computed(() => {
      const f = filter.value.trim().toLowerCase();
      if (!f) return allCategories.value;
      return allCategories.value
        .map((c) => ({ ...c, items: Object.fromEntries(Object.entries(c.items).filter(([code]) => code.toLowerCase().includes(f))) }))
        .filter((c) => Object.keys(c.items).length);
    });

    function pick(code) {
      emit("pick", code);
    }

    return { filter, icons, filteredCategories, pick };
  },
  template: `
  <div class="emoji-picker">
    <input type="text" v-model="filter" class="emoji-picker-search" placeholder="Search shortcode…" />
    <div class="emoji-picker-body">
      <div v-for="cat in filteredCategories" :key="cat.name" class="emoji-picker-cat">
        <div class="emoji-picker-cat-name">{{ cat.name }}</div>
        <div class="emoji-picker-grid">
          <button v-for="(val, code) in cat.items" :key="code" type="button" class="emoji-picker-item" :title="':' + code + ':'" @click="pick(code)">
            <img v-if="cat.custom" :src="val" alt="" class="emoji-picker-item-img" />
            <span v-else-if="cat.icon" class="emoji-picker-item-icon" v-html="icons[val]"></span>
            <span v-else>{{ val }}</span>
          </button>
        </div>
      </div>
      <div v-if="!filteredCategories.length" class="empty-state">No match</div>
    </div>
  </div>
  `,
};
