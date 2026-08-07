// 常用 emoji 對照表(涵蓋 iOS 最常用的表情/手勢/符號),shortcode -> 實際 emoji
// 字元。給 markdown.js 的 :shortcode: 語法用 - 純文字替換,不需要額外圖檔。
// 使用者自己上傳的 PNG emoji走另一條路(見 markdown.js 的 setCustomEmoji),
// 三者(自訂 PNG / 單線條 icon / 內建 emoji)共用同一個 :shortcode: 語法,
// 優先順序見 markdown.js 的 applyEmoji:自訂 > 單線條 icon > 內建 emoji。
//
// 分類成陣列(而不是單一個大 object)是為了讓 EmojiPicker.js / 首頁的語法
// 說明視窗可以照分類分組顯示,而不是把 200 個 shortcode 全部攤平列出來。
export const EMOJI_CATEGORIES = [
  {
    name: "Smileys",
    items: {
      smile: "😄", smiley: "😃", grin: "😁", laughing: "😆", satisfied: "😆",
      sweat_smile: "😅", joy: "😂", rofl: "🤣", relaxed: "☺️", blush: "😊",
      innocent: "😇", wink: "😉", slight_smile: "🙂", upside_down: "🙃",
      heart_eyes: "😍", kissing_heart: "😘", yum: "😋", stuck_out_tongue: "😛",
      stuck_out_tongue_winking_eye: "😜", zany_face: "🤪", star_struck: "🤩",
      thinking: "🤔", face_with_raised_eyebrow: "🤨", neutral_face: "😐",
      expressionless: "😑", no_mouth: "😶", smirk: "😏", unamused: "😒",
      roll_eyes: "🙄", rolling_eyes: "🙄", grimacing: "😬", lying_face: "🤥",
      relieved: "😌", pensive: "😔", sleepy: "😪", drooling_face: "🤤",
      sleeping: "😴", mask: "😷", face_with_thermometer: "🤒",
      face_with_head_bandage: "🤕", nauseated_face: "🤢", vomiting: "🤮",
      sneezing_face: "🤧", hot_face: "🥵", cold_face: "🥶", woozy_face: "🥴",
      dizzy_face: "😵", exploding_head: "🤯", cowboy: "🤠", partying_face: "🥳",
      disguised_face: "🥸", sunglasses: "😎", nerd_face: "🤓",
      monocle_face: "🧐", confused: "😕", worried: "😟", slightly_frowning: "🙁",
      frowning: "☹️", open_mouth: "😮", hushed: "😯", astonished: "😲",
      flushed: "😳", pleading_face: "🥺", frowning_person: "😦",
      anguished: "😧", fearful: "😨", cold_sweat: "😰", disappointed_relieved: "😥",
      cry: "😢", sob: "😭", scream: "😱", confounded: "😖", persevere: "😣",
      disappointed: "😞", sweat: "😓", weary: "😩", tired_face: "😫",
      yawning_face: "🥱", triumph: "😤", angry: "😠", rage: "😡",
      face_with_symbols: "🤬", smiling_imp: "😈", imp: "👿",
      skull: "💀", ghost: "👻", alien: "👽", robot: "🤖", poop: "💩",
      clown_face: "🤡", shushing_face: "🤫", zipper_mouth_face: "🤐",
      face_with_hand_over_mouth: "🤭", raised_eyebrow: "🤨",
    },
  },
  {
    name: "Hearts",
    items: {
      heart: "❤️", orange_heart: "🧡", yellow_heart: "💛", green_heart: "💚",
      blue_heart: "💙", purple_heart: "💜", black_heart: "🖤", white_heart: "🤍",
      brown_heart: "🤎", broken_heart: "💔", two_hearts: "💕",
      sparkling_heart: "💖", heartpulse: "💗", heartbeat: "💓",
      revolving_hearts: "💞", cupid: "💘", gift_heart: "💝", heart_exclamation: "❣️",
    },
  },
  {
    name: "Hands / gestures",
    items: {
      thumbsup: "👍", "+1": "👍", thumbsdown: "👎", "-1": "👎", ok_hand: "👌",
      v: "✌️", crossed_fingers: "🤞", love_you_gesture: "🤟", call_me_hand: "🤙",
      wave: "👋", raised_hand: "✋", vulcan: "🖖", clap: "👏", pray: "🙏",
      muscle: "💪", point_up: "☝️", point_up_2: "👆", point_down: "👇",
      point_left: "👈", point_right: "👉", raised_hands: "🙌", open_hands: "👐",
      handshake: "🤝", fist: "✊", punch: "👊", writing_hand: "✍️",
      nail_care: "💅", middle_finger: "🖕", ok: "🆗",
    },
  },
  {
    name: "Celebration / symbols",
    items: {
      fire: "🔥", "100": "💯", star: "⭐", star2: "🌟", sparkles: "✨",
      zap: "⚡", boom: "💥", collision: "💥", tada: "🎉", confetti_ball: "🎊",
      balloon: "🎈", gift: "🎁", trophy: "🏆", medal: "🏅", first_place: "🥇",
      crown: "👑", gem: "💎", moneybag: "💰", money_with_wings: "💸",
      bulb: "💡", warning: "⚠️", exclamation: "❗", question: "❓",
      white_check_mark: "✅", heavy_check_mark: "✔️", x: "❌",
      heavy_multiplication_x: "✖️", no_entry: "⛔", recycle: "♻️",
      hourglass: "⌛", hourglass_flowing_sand: "⏳", alarm_clock: "⏰",
      clock: "🕐", calendar: "📅", date: "📆", pushpin: "📌",
      round_pushpin: "📍", link: "🔗", lock: "🔒", unlock: "🔓", key: "🔑",
      mag: "🔍", bell: "🔔", no_bell: "🔕", speech_balloon: "💬",
      thought_balloon: "💭", eyes: "👀", email: "📧", envelope: "✉️",
      phone: "📞", computer: "💻", iphone: "📱", camera: "📷", tv: "📺",
      video_game: "🎮", headphones: "🎧", musical_note: "🎵", notes: "🎶",
      book: "📖", books: "📚", pencil2: "✏️", memo: "📝",
      chart_up: "📈", chart_down: "📉", rocket: "🚀", airplane: "✈️",
      car: "🚗", house: "🏠", office: "🏢", sunny: "☀️", cloud: "☁️",
      rainbow: "🌈", umbrella: "☔", snowflake: "❄️", earth: "🌍",
    },
  },
  {
    name: "Food",
    items: {
      coffee: "☕", tea: "🍵", beer: "🍺", beers: "🍻", wine_glass: "🍷",
      cocktail: "🍸", pizza: "🍕", hamburger: "🍔", fries: "🍟", cake: "🍰",
      birthday: "🎂", cookie: "🍪", apple: "🍎", watermelon: "🍉", banana: "🍌",
    },
  },
  {
    name: "Animals",
    items: {
      dog: "🐶", cat: "🐱", panda: "🐼", koala: "🐨", unicorn: "🦄",
      rabbit: "🐰", bear: "🐻", monkey: "🐵", fox: "🦊",
    },
  },
  {
    name: "People",
    items: {
      man: "👨", woman: "👩", baby: "👶", boy: "👦", girl: "👧",
      older_man: "👴", older_woman: "👵",
    },
  },
];

// 扁平化版本(shortcode -> emoji 字元),markdown.js 直接查表用,不用每次
// 都跑一次分類陣列。
export const EMOJI_MAP = Object.assign({}, ...EMOJI_CATEGORIES.map((c) => c.items));

// 單線條 SVG icon 版的「emoji」- shortcode -> icons.js 的 icon key,渲染出來
// 是跟著目前文字顏色走的線條圖案,不是像色彩繽紛的 emoji 字元(不同裝置/
// 瀏覽器對 emoji 字元的畫法常常不一致,線條 icon 則保證跟 App 其他地方的
// icon 長得一樣)。全部加上 icon_ 前綴,避免跟上面的 emoji shortcode 撞名。
export const LINE_ICON_MAP = {
  icon_pin: "pin",
  icon_star: "star",
  icon_flag: "flag",
  icon_heart: "heartLine",
  icon_target: "target",
  icon_idea: "idea",
  icon_thumbup: "thumbUp",
  icon_flame: "flame",
  icon_bookmark: "bookmark",
  icon_clock: "clock",
  icon_check: "check",
  icon_tag: "tag",
  icon_calendar: "calendar",
  icon_alert: "alertCircle",
  icon_help: "help",
};
