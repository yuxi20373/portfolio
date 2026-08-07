// Relies on the global `marked` and `DOMPurify` UMD builds loaded via
// <script> tags in index.html (kept as plain globals so this stays a
// dependency-free ES module).

import { EMOJI_MAP, LINE_ICON_MAP } from "./emoji.js";
import { icons } from "./icons.js";

// 使用者自訂的 PNG emoji(見 store.js 的 loadCustomEmoji)- shortcode -> 圖片
// URL,模組層級的一份快取,renderMarkdown 每次呼叫都會用到,不用元件自己傳。
let customEmoji = {};

export function setCustomEmoji(list) {
  customEmoji = {};
  for (const e of list || []) customEmoji[e.shortcode] = e.url;
}

// :shortcode: -> 自訂 PNG > 單線條 icon(LINE_ICON_MAP)> 內建 emoji 字元,
// 依序找,都找不到就原樣保留,不強制它一定要是合法 emoji 名稱。
const SHORTCODE_RE = /:([a-zA-Z0-9_+-]+):/g;

function applyEmoji(text) {
  return text.replace(SHORTCODE_RE, (match, code) => {
    if (customEmoji[code]) {
      return `<img class="md-emoji" src="${customEmoji[code]}" alt=":${code}:" />`;
    }
    if (LINE_ICON_MAP[code]) {
      return `<span class="md-emoji md-icon-emoji">${icons[LINE_ICON_MAP[code]]}</span>`;
    }
    if (EMOJI_MAP[code]) return EMOJI_MAP[code];
    return match;
  });
}

// ::b:文字:: / ::g:文字:: / ::p:文字:: - 底色語法,固定三個顏色(藍/綠/橘)。
// 例如 ::b:重要::。顏色是獨立定義(見 style.css 的 --highlight-*),沒有沿用
// note-color-sky/sage 那組筆記卡片底色 - 那組是設計給大面積底色用的極淡色調,
// 拿來當一小段文字的底色反而太淡、跟白色背景幾乎分不出來。
const HIGHLIGHT_COLORS = { b: "blue", g: "green", p: "orange" };
const HIGHLIGHT_RE = /::(b|g|p):(.+?)::/g;

function applyHighlight(text) {
  return text.replace(HIGHLIGHT_RE, (match, letter, inner) => `<mark class="md-highlight md-highlight-${HIGHLIGHT_COLORS[letter]}">${inner}</mark>`);
}

export function renderMarkdown(mdText) {
  if (!mdText) return "";
  // Emoji/highlight 都是在丟給 marked 之前,直接替換原始 Markdown 文字裡的
  // 語法 - 這樣裡面還是可以正常套用其他 Markdown 格式(例如 ==sky:**粗體**==)。
  // 已知取捨:這個替換不會避開 code block/inline code,所以如果真的需要在
  // 程式碼裡打出 :xxx: 這種文字,顯示上還是會被換成 emoji。
  let text = applyEmoji(mdText);
  text = applyHighlight(text);

  const rawHtml = window.marked.parse(text, { breaks: true });
  // marked's GFM task lists (- [ ]/- [x]) render as <input type="checkbox">,
  // but DOMPurify's default allow-list doesn't include <input> (it's
  // normally a form/XSS-relevant tag) - without ADD_TAGS/ADD_ATTR the
  // checkboxes just silently vanish.
  return window.DOMPurify.sanitize(rawHtml, {
    ADD_TAGS: ["input", "mark"],
    ADD_ATTR: ["type", "checked", "disabled", "class"],
  });
}
