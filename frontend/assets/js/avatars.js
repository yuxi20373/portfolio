// 頭貼是固定的一組預設圖片,使用者自己準備 PNG 丟進
// assets/images/avatars/(見該資料夾的 README.md),不開放使用者上傳自己的
// 圖片。跟首頁那套會隨 image theme 切換的裝飾圖片不一樣 - 頭貼代表的是
// 「這個人是誰」,跟目前選的視覺主題無關,所以固定同一份,路徑不走
// store.img()(那個會依 store.imageTheme 換資料夾)。
export const AVATAR_PRESETS = Array.from({ length: 20 }, (_, i) => `avatar-${i + 1}.png`);

// avatar 是存在 User.avatar 的 preset 檔名(或 null/未設定)。回傳空字串時
// 呼叫端應該顯示 fallback SVG(見 icons.js 的 icons.user),不要塞一個
// 空的 <img src>。
export function avatarSrc(avatar) {
  return avatar ? `assets/images/avatars/${avatar}` : "";
}
