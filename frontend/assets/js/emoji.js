// 常用 emoji 對照表(涵蓋 iOS 最常用的表情/手勢/符號),shortcode -> 實際 emoji
// 字元。給 markdown.js 的 :shortcode: 語法用 - 純文字替換,不需要額外圖檔。
// 使用者自己上傳的 PNG emoji走另一條路(見 markdown.js 的 setCustomEmoji),
// 兩邊共用同一個 :shortcode: 語法,自訂的優先。
export const EMOJI_MAP = {
  // --- Smileys / emotions ---
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

  // --- Hearts ---
  heart: "❤️", orange_heart: "🧡", yellow_heart: "💛", green_heart: "💚",
  blue_heart: "💙", purple_heart: "💜", black_heart: "🖤", white_heart: "🤍",
  brown_heart: "🤎", broken_heart: "💔", two_hearts: "💕",
  sparkling_heart: "💖", heartpulse: "💗", heartbeat: "💓",
  revolving_hearts: "💞", cupid: "💘", gift_heart: "💝", heart_exclamation: "❣️",

  // --- Hands / gestures ---
  thumbsup: "👍", "+1": "👍", thumbsdown: "👎", "-1": "👎", ok_hand: "👌",
  v: "✌️", crossed_fingers: "🤞", love_you_gesture: "🤟", call_me_hand: "🤙",
  wave: "👋", raised_hand: "✋", vulcan: "🖖", clap: "👏", pray: "🙏",
  muscle: "💪", point_up: "☝️", point_up_2: "👆", point_down: "👇",
  point_left: "👈", point_right: "👉", raised_hands: "🙌", open_hands: "👐",
  handshake: "🤝", fist: "✊", punch: "👊", writing_hand: "✍️",
  nail_care: "💅", middle_finger: "🖕", ok: "🆗",

  // --- Celebration / symbols ---
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

  // --- Food ---
  coffee: "☕", tea: "🍵", beer: "🍺", beers: "🍻", wine_glass: "🍷",
  cocktail: "🍸", pizza: "🍕", hamburger: "🍔", fries: "🍟", cake: "🍰",
  birthday: "🎂", cookie: "🍪", apple: "🍎", watermelon: "🍉", banana: "🍌",

  // --- Animals ---
  dog: "🐶", cat: "🐱", panda: "🐼", koala: "🐨", unicorn: "🦄",
  rabbit: "🐰", bear: "🐻", monkey: "🐵", fox: "🦊",

  // --- People ---
  man: "👨", woman: "👩", baby: "👶", boy: "👦", girl: "👧",
  older_man: "👴", older_woman: "👵",
};
