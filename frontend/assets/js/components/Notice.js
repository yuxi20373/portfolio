import { store } from "../store.js";
import { icons } from "../icons.js";

// 頂部通知框,由 store.showNotice() 觸發、3秒後自動消失(見 store.js 該方法上面
// 的註解)。在 app-shell 層級掛載一次(見 app.js),PNG/SVG 容錯規則跟其他地方一樣。
export default {
  setup() {
    function onImgError(e) {
      e.target.style.display = "none";
    }
    return { store, icons, onImgError };
  },
  template: `
  <div v-if="store.notice" class="notice-toast" :class="'notice-' + store.notice.type" :key="store.notice.message">
    <span class="notice-toast-icon">
      <span v-html="store.notice.type === 'error' ? icons.alertCircle : icons.check"></span>
      <img :src="store.notice.type === 'error' ? 'assets/images/notice-failed.png' : 'assets/images/notice-check.png'" alt="" @error="onImgError" />
    </span>
    <span class="notice-toast-text">{{ store.notice.message }}</span>
  </div>
  `,
};
