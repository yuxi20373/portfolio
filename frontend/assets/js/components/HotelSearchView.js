const { ref, computed } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";

// 測試/串接 Airbnb(Bright Data Dataset API,discover_by=location)訂房搜尋
// 用的頁面 - 見 store.js 的 startAirbnbSearch / backend/app/routers/airbnb_search.py。
// AsiaYo 那個來源先暫時拿掉(store.js 的 hotelSearch* 那組還在,之後要加回來
// 直接復用即可),目前只剩 Airbnb 這條路線。
// 顯示邏輯:一次最多抓 settings.airbnb_search_total_limit(後端目前 200)筆,
// 前端先套用價格區間篩選,篩完的裡面依評價由高到低排序,只顯示前 TOP_N 筆
// (不是「篩選」跟「取前 30」是分開兩個動作給使用者選 - 使用者要的就是
// 「金額符合的條件裡,評價最高的前 30」這個固定邏輯)。
const STATUS_LABELS = { pending: "等待中", scraping: "爬蟲抓取中", done: "完成", failed: "失敗" };
const TOP_N = 30;

// 台灣縣市快速勾選用(見下面的 showLocationPicker)- Bright Data 吃的是自由
// 文字的 "City, Country" 格式,這份清單是自己定義的,跟 AsiaYo 那邊固定的
// 14 個縣市無關(那個列表本來就缺南投,這裡不受它限制)。
const TAIWAN_LOCATIONS = [
  { label: "台北市", value: "Taipei, Taiwan" },
  { label: "新北市", value: "New Taipei, Taiwan" },
  { label: "桃園市", value: "Taoyuan, Taiwan" },
  { label: "台中市", value: "Taichung, Taiwan" },
  { label: "台南市", value: "Tainan, Taiwan" },
  { label: "高雄市", value: "Kaohsiung, Taiwan" },
  { label: "基隆市", value: "Keelung, Taiwan" },
  { label: "新竹市", value: "Hsinchu, Taiwan" },
  { label: "新竹縣", value: "Hsinchu County, Taiwan" },
  { label: "苗栗縣", value: "Miaoli, Taiwan" },
  { label: "彰化縣", value: "Changhua, Taiwan" },
  { label: "南投縣", value: "Nantou, Taiwan" },
  { label: "雲林縣", value: "Yunlin, Taiwan" },
  { label: "嘉義市", value: "Chiayi, Taiwan" },
  { label: "嘉義縣", value: "Chiayi County, Taiwan" },
  { label: "屏東縣", value: "Pingtung, Taiwan" },
  { label: "宜蘭縣", value: "Yilan, Taiwan" },
  { label: "花蓮縣", value: "Hualien, Taiwan" },
  { label: "台東縣", value: "Taitung, Taiwan" },
  { label: "澎湖縣", value: "Penghu, Taiwan" },
  { label: "金門縣", value: "Kinmen, Taiwan" },
  { label: "連江縣", value: "Lienchiang, Taiwan" },
];

export default {
  setup() {
    const locationsText = ref("");
    const checkInDate = ref("");
    const checkOutDate = ref("");
    const adults = ref(1);

    // --- 台灣縣市勾選 popover - 跟 TagPicker.js 同一套邏輯(勾/取消勾就是
    // 從 locationsText 這個以換行分隔的文字裡加一行/刪一行),只是 TagPicker
    // 用逗號分隔,這裡改用換行(因為 "City, Country" 格式本身就有逗號,不能
    // 拿來當分隔符)。手動輸入的地點(不在 TAIWAN_LOCATIONS 裡的那些行)不受
    // 影響,勾選只加減自己對應的那一行。 ---
    const showLocationPicker = ref(false);

    function locationLines() {
      return locationsText.value.split("\n").map((s) => s.trim()).filter(Boolean);
    }

    const selectedTaiwanLocations = computed(() => {
      const lines = locationLines();
      return TAIWAN_LOCATIONS.filter((c) => lines.includes(c.value)).map((c) => c.value);
    });

    function toggleTaiwanLocation(value) {
      const lines = locationLines();
      const idx = lines.indexOf(value);
      if (idx >= 0) lines.splice(idx, 1);
      else lines.push(value);
      locationsText.value = lines.join("\n");
    }

    function onCheckInChange() {
      if (checkOutDate.value && checkOutDate.value <= checkInDate.value) {
        const d = new Date(checkInDate.value);
        d.setDate(d.getDate() + 1);
        checkOutDate.value = d.toISOString().slice(0, 10);
      }
    }

    const canSearch = computed(
      () => !!locationsText.value.trim() && !!checkInDate.value && !!checkOutDate.value && !store.airbnbSearchPolling,
    );

    function search() {
      if (!canSearch.value) return;
      const locations = locationsText.value
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean);
      store.startAirbnbSearch({
        locations,
        check_in_date: checkInDate.value,
        check_out_date: checkOutDate.value,
        adults: Number(adults.value) || 1,
      });
    }

    const activeJob = computed(() => store.airbnbSearchJob);
    const isBusy = computed(() => {
      const s = activeJob.value?.status;
      return s === "pending" || s === "scraping";
    });

    // --- 價錢/評價篩選(見上面 TOP_N 的說明)---
    const filterMinPrice = ref("");
    const filterMaxPrice = ref("");

    function priceOf(h) {
      return h.price_per_night ?? h.total_price;
    }
    function ratingOf(h) {
      return h.rating;
    }

    const allResults = computed(() => activeJob.value?.results || []);

    // 符合價格條件的(還沒套 TOP_N)- 用來在畫面上顯示「符合條件幾筆」。
    const matchedResults = computed(() => {
      const min = filterMinPrice.value !== "" ? Number(filterMinPrice.value) : null;
      const max = filterMaxPrice.value !== "" ? Number(filterMaxPrice.value) : null;
      if (min === null && max === null) return allResults.value;
      return allResults.value.filter((h) => {
        const p = priceOf(h);
        if (min !== null && (p == null || p < min)) return false;
        if (max !== null && (p == null || p > max)) return false;
        return true;
      });
    });

    // null/undefined 一律排到最後(不管遞增還遞減),其餘照 dir 比大小。
    function cmp(a, b, dir) {
      if (a == null && b == null) return 0;
      if (a == null) return 1;
      if (b == null) return -1;
      return dir === "asc" ? a - b : b - a;
    }

    // 排序優先順序:價錢低到高 > 評價高到低(價錢相同時)> 評論數多到少
    // (評價也相同時)。符合價格條件的裡面排完,取前 TOP_N 筆顯示。
    const displayResults = computed(() =>
      matchedResults.value
        .slice()
        .sort(
          (a, b) =>
            cmp(priceOf(a), priceOf(b), "asc") ||
            cmp(ratingOf(a), ratingOf(b), "desc") ||
            cmp(a.review_count, b.review_count, "desc"),
        )
        .slice(0, TOP_N),
    );

    function onImgError(e) {
      e.target.style.display = "none";
    }

    return {
      store, icons, STATUS_LABELS, TOP_N, TAIWAN_LOCATIONS,
      locationsText, checkInDate, checkOutDate, adults, onCheckInChange,
      showLocationPicker, selectedTaiwanLocations, toggleTaiwanLocation,
      canSearch, search,
      activeJob, isBusy,
      filterMinPrice, filterMaxPrice,
      allResults, matchedResults, displayResults,
      onImgError,
    };
  },
  template: `
  <div class="main-panel hotel-search-panel">
    <h1 class="page-title">HOTELS</h1>

    <div class="hotel-search-card">
      <div class="hotel-search-field hotel-search-field-wide">
        <label>Locations</label>
        <div class="hotel-locations-row">
          <textarea v-model="locationsText" class="note-editor-textarea" rows="3" placeholder="Taipei, Taiwan&#10;Tainan, Taiwan"></textarea>
          <span class="note-help-wrap">
            <button type="button" class="icon-btn" title="選擇台灣縣市" @click="showLocationPicker = !showLocationPicker" v-html="icons.pin"></button>
            <div v-if="showLocationPicker" class="note-help-popover tag-picker-popover">
              <label v-for="c in TAIWAN_LOCATIONS" :key="c.value" class="tag-picker-item">
                <input type="checkbox" :checked="selectedTaiwanLocations.includes(c.value)" @change="toggleTaiwanLocation(c.value)" />
                {{ c.label }}
              </label>
            </div>
          </span>
        </div>
      </div>
      <div class="hotel-search-field">
        <label>Check-in</label>
        <input type="date" v-model="checkInDate" class="note-editor-title-input" @change="onCheckInChange" />
      </div>
      <div class="hotel-search-field">
        <label>Check-out</label>
        <input type="date" v-model="checkOutDate" class="note-editor-title-input" :min="checkInDate" />
      </div>
      <div class="hotel-search-field hotel-search-field-narrow">
        <label>Adults</label>
        <input type="number" min="1" v-model="adults" class="note-editor-title-input" />
      </div>
      <button class="btn hotel-search-btn" :disabled="!canSearch" @click="search">
        <span v-if="store.airbnbSearchPolling" class="spinner"></span>
        <span v-else v-html="icons.search"></span>
        {{ store.airbnbSearchPolling ? 'Searching…' : 'Search' }}
      </button>
    </div>

    <div v-if="store.airbnbSearchError" class="empty-state">{{ store.airbnbSearchError }}</div>

    <template v-if="activeJob">
      <div class="hotel-status-row">
        <span class="hotel-status-badge" :class="activeJob.status">
          <span v-if="isBusy" class="spinner"></span>
          {{ STATUS_LABELS[activeJob.status] || activeJob.status }}
        </span>
        <span v-if="activeJob.status === 'done'" class="hotel-result-count">
          顯示前 {{ displayResults.length }} 名(符合條件 {{ matchedResults.length }} / 共 {{ allResults.length }} 筆)
        </span>
      </div>

      <div v-if="activeJob.status === 'failed'" class="empty-state">{{ activeJob.error_message }}</div>

      <div v-if="activeJob.status === 'done' && allResults.length" class="hotel-filter-row">
        <div class="hotel-search-field hotel-search-field-narrow">
          <label>Min price</label>
          <input type="number" min="0" v-model="filterMinPrice" class="note-editor-title-input" placeholder="不限" />
        </div>
        <div class="hotel-search-field hotel-search-field-narrow">
          <label>Max price</label>
          <input type="number" min="0" v-model="filterMaxPrice" class="note-editor-title-input" placeholder="不限" />
        </div>
        <button v-if="filterMinPrice || filterMaxPrice" class="btn secondary" @click="filterMinPrice = ''; filterMaxPrice = ''">清除篩選</button>
      </div>

      <div v-if="isBusy" class="hotel-grid">
        <div v-for="i in 6" :key="i" class="hotel-card hotel-card-skeleton"></div>
      </div>

      <div v-else-if="activeJob.status === 'done'" class="hotel-grid">
        <div v-for="h in displayResults" :key="h.property_id" class="hotel-card">
          <img v-if="h.image" :src="h.image" alt="" class="hotel-card-img" @error="onImgError" />
          <div v-else class="hotel-card-img hotel-card-img-fallback" v-html="icons.hotel"></div>
          <div class="hotel-card-body">
            <div class="hotel-card-name">
              {{ h.name }}
              <span v-if="h.is_superhost" class="hotel-card-badge">Superhost</span>
            </div>
            <div class="hotel-card-meta">
              <span class="hotel-card-district" v-if="h.discovery_location">{{ h.discovery_location }}</span>
              <span class="hotel-card-rating"><span v-html="icons.star"></span> {{ h.rating ?? '—' }}<span v-if="h.review_count"> ({{ h.review_count }})</span></span>
            </div>
            <div class="hotel-card-footer">
              <div class="hotel-card-price">{{ h.currency }} {{ h.price_per_night ?? h.total_price }}<span v-if="h.price_per_night"> /晚</span></div>
              <a :href="h.url" target="_blank" rel="noopener" class="btn secondary hotel-card-link">查看詳情</a>
            </div>
          </div>
        </div>
        <div v-if="!displayResults.length" class="empty-state">{{ allResults.length ? '沒有符合篩選條件的房源' : '沒有找到符合的房源' }}</div>
      </div>
    </template>
  </div>
  `,
};
