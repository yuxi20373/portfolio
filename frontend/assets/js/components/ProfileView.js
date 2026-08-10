const { ref, onMounted } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";
import { AVATAR_PRESETS, avatarSrc } from "../avatars.js";

// 編輯帳號畫面 - 唯一入口是首頁點主視覺圖片(見 HomeView.js 的
// onHeroClick),不是側欄常駐的一個分頁。username/密碼不能在這裡改(只能
// 透過後端的 create_user.py script),這裡只開放 display_name/avatar/status
// 三個自我可編輯欄位。
export default {
  setup() {
    const displayName = ref("");
    const avatar = ref("");
    const status = ref("");
    const saving = ref(false);

    onMounted(async () => {
      if (!store.profile) await store.loadProfile();
      displayName.value = store.profile?.display_name || "";
      avatar.value = store.profile?.avatar || "";
      status.value = store.profile?.status || "";
    });

    function pickAvatar(a) {
      avatar.value = a;
    }

    async function save() {
      saving.value = true;
      try {
        await store.updateProfile({
          display_name: displayName.value.trim(),
          avatar: avatar.value,
          status: status.value.trim(),
        });
        store.view = "home";
      } finally {
        saving.value = false;
      }
    }

    function back() {
      store.view = "home";
    }

    // 圖檔還沒放進 assets/images/avatars/ 之前優雅退回 icons.user,不顯示破圖。
    function onAvatarImgError(e) {
      e.target.style.display = "none";
    }

    return {
      store, icons, AVATAR_PRESETS, avatarSrc,
      displayName, avatar, status, saving,
      pickAvatar, save, back, onAvatarImgError,
    };
  },
  template: `
  <div class="main-panel profile-panel">
    <h1 class="page-title">EDIT ACCOUNT</h1>

    <div class="profile-field">
      <label>Username</label>
      <div class="profile-username">{{ store.username }}</div>
    </div>

    <div class="profile-field">
      <label>Display name</label>
      <input type="text" v-model="displayName" class="note-editor-title-input" placeholder="怎麼稱呼你" maxlength="50" />
    </div>

    <div class="profile-field">
      <label>Status</label>
      <input type="text" v-model="status" class="note-editor-title-input" placeholder="自訂狀態" maxlength="140" />
    </div>

    <div class="profile-field">
      <label>Avatar</label>
      <div class="avatar-grid">
        <button v-for="a in AVATAR_PRESETS" :key="a" type="button" class="avatar-option" :class="{active: avatar === a}" @click="pickAvatar(a)">
          <img :src="avatarSrc(a)" alt="" @error="onAvatarImgError" />
        </button>
      </div>
    </div>

    <div class="drawer-actions">
      <button class="btn" :disabled="saving" @click="save">
        <span v-if="saving" class="spinner"></span>{{ saving ? ' Saving…' : 'Save' }}
      </button>
      <button class="btn secondary" :disabled="saving" @click="back">Back</button>
    </div>
  </div>
  `,
};
