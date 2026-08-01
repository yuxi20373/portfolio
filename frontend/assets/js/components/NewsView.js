const { ref, computed, onMounted } = window.Vue;
import { store } from "../store.js";
import { icons } from "../icons.js";
import { renderMarkdown } from "../markdown.js";

// "2026-07-25" -> "7月25日"; falls back to the raw date string on parse failure
function fmtDayLabel(dateStr) {
    const d = new Date(dateStr + "T00:00:00");
    if (isNaN(d)) return dateStr;
    return `${d.getMonth() + 1}月${d.getDate()}日`;
}

// full timestamp for the small gray byline, e.g. "2026/7/25 19:07"
function fmtTime(d) {
    const dt = new Date(d);
    if (isNaN(dt)) return "";
    const h = String(dt.getHours()).padStart(2, "0");
    const min = String(dt.getMinutes()).padStart(2, "0");
    return `${dt.getFullYear()}/${dt.getMonth() + 1}/${dt.getDate()} ${h}:${min}`;
}

export default {
    setup() {
        onMounted(() => {
            if (!store.newsOverview) store.loadNewsOverview();
        });

        const featuredArticle = computed(() => {
            const ov = store.newsOverview;
            if (!ov || !ov.featured.length) return null;
            return ov.featured[store.newsFeaturedIndex];
        });

        // Timeline below the featured card: either the default recent-days
        // window (newsOverview.other_days) or a specific picked week.
        const timelineDays = computed(() => {
            if (store.newsWeek) return store.newsWeek.days;
            return store.newsOverview ? store.newsOverview.other_days : [];
        });

        // --- Week-picker popover (borderless calendar button) ---
        const showWeekPicker = ref(false);
        const today = new Date();
        const wpYear = ref(today.getFullYear());
        const wpMonth = ref(today.getMonth() + 1); // 1-12

        const wpCells = computed(() => {
            const first = new Date(wpYear.value, wpMonth.value - 1, 1);
            const daysInMonth = new Date(wpYear.value, wpMonth.value, 0).getDate();
            const startWeekday = first.getDay();
            const arr = [];
            for (let i = 0; i < startWeekday; i++) arr.push(null);
            for (let d = 1; d <= daysInMonth; d++) {
                const dateStr = `${wpYear.value}-${String(wpMonth.value).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
                arr.push({ day: d, dateStr });
            }
            return arr;
        });

        function wpPrevMonth() {
            wpMonth.value--;
            if (wpMonth.value < 1) { wpMonth.value = 12; wpYear.value--; }
        }
        function wpNextMonth() {
            wpMonth.value++;
            if (wpMonth.value > 12) { wpMonth.value = 1; wpYear.value++; }
        }
        function pickWeek(dateStr) {
            showWeekPicker.value = false;
            store.loadNewsWeek(dateStr);
        }
        function backToRecent() {
            store.clearNewsWeek();
        }

        function openArticle(id, siblingIds) {
            store.openNewsArticle(id, siblingIds);
        }

        function backToOverview() {
            store.closeNewsArticle();
        }

        const canStepPrev = computed(() => {
            const ids = store.newsArticleSiblings;
            return !!store.newsCurrentArticle && ids.indexOf(store.newsCurrentArticle.id) > 0;
        });
        const canStepNext = computed(() => {
            const ids = store.newsArticleSiblings;
            if (!store.newsCurrentArticle) return false;
            const idx = ids.indexOf(store.newsCurrentArticle.id);
            return idx >= 0 && idx < ids.length - 1;
        });

        return {
            store,
            icons,
            renderMarkdown,
            fmtDayLabel,
            fmtTime,
            featuredArticle,
            timelineDays,
            showWeekPicker,
            wpYear,
            wpMonth,
            wpCells,
            wpPrevMonth,
            wpNextMonth,
            pickWeek,
            backToRecent,
            openArticle,
            backToOverview,
            canStepPrev,
            canStepNext,
        };
    },
    template: `
  <div class="main-panel news-panel">

    <!-- Detail view: full summary for one article, back arrow returns to overview -->
    <template v-if="store.newsCurrentArticle || store.newsArticleLoading">
      <div class="news-detail-header">
        <button class="icon-btn news-back-btn" title="Back to overview" @click="backToOverview" v-html="icons.arrowLeft"></button>
        <button class="icon-btn" title="Previous article" :disabled="!canStepPrev" @click="store.stepNewsArticle(-1)" v-html="icons.chevronLeft"></button>
        <button class="icon-btn" title="Next article" :disabled="!canStepNext" @click="store.stepNewsArticle(1)" v-html="icons.chevronRight"></button>
        <button v-if="store.newsCurrentArticle" class="icon-btn news-favorite-btn" title="Favorite this article" @click="store.toggleNewsArticleFavorite()" v-html="store.newsCurrentArticle.is_favorited ? icons.bookmarkFilled : icons.bookmark"></button>
      </div>
      <div v-if="store.newsArticleLoading" class="loading-row"><span class="spinner"></span> Loading…</div>
      <div v-else class="news-detail-body">
        <h2 class="news-detail-title">{{ store.newsCurrentArticle.title }}</h2>
        <div class="news-time">{{ store.newsCurrentArticle.source_name }} · {{ fmtTime(store.newsCurrentArticle.published_at) }}</div>
        <div class="markdown-body news-summary" v-html="renderMarkdown(store.newsCurrentArticle.summary_md)"></div>
        <a v-if="store.newsCurrentArticle.source_url" class="news-source-link" :href="store.newsCurrentArticle.source_url" target="_blank" rel="noopener">
          原文連結（{{ store.newsCurrentArticle.source_name }}）↗
        </a>
      </div>
    </template>

    <!-- Overview: featured carousel (today / latest day) + timeline below -->
    <template v-else>
      <div v-if="store.newsLoading && !store.newsOverview" class="loading-row"><span class="spinner"></span> Loading…</div>

      <template v-else-if="store.newsOverview && featuredArticle">
        <div class="news-featured-card">
          <button class="news-carousel-arrow left" title="Previous" :disabled="store.newsOverview.featured.length < 2" @click="store.stepNewsFeatured(-1)" v-html="icons.chevronLeft"></button>

          <div class="news-featured-content" @click="openArticle(featuredArticle.id, store.newsOverview.featured.map(a => a.id))">
            <div class="news-featured-date">{{ fmtDayLabel(store.newsOverview.featured_date) }}</div>
            <div class="news-featured-title">{{ featuredArticle.title }}</div>
            <div class="markdown-body news-summary" v-html="renderMarkdown(featuredArticle.summary_md)"></div>
            <div class="news-time">{{ featuredArticle.source_name }} · {{ fmtTime(featuredArticle.published_at) }}</div>
          </div>

          <button class="news-carousel-arrow right" title="Next" :disabled="store.newsOverview.featured.length < 2" @click="store.stepNewsFeatured(1)" v-html="icons.chevronRight"></button>
        </div>
        <div v-if="store.newsOverview.featured.length > 1" class="news-carousel-dots">
          <span v-for="(a, i) in store.newsOverview.featured" :key="a.id" class="news-dot" :class="{active: i === store.newsFeaturedIndex}" @click="store.newsFeaturedIndex = i"></span>
        </div>

        <!-- Week picker: borderless button between the featured card and the timeline -->
        <div class="news-week-bar">
          <button class="icon-btn news-week-btn" title="Browse by week" @click="showWeekPicker = !showWeekPicker" v-html="icons.calendar"></button>
          <span v-if="store.newsWeek" class="news-week-label">
            {{ fmtDayLabel(store.newsWeek.start) }} – {{ fmtDayLabel(store.newsWeek.end) }}
            <button class="mini-icon-btn" title="Back to recent" @click="backToRecent">×</button>
          </span>

          <div v-if="showWeekPicker" class="news-week-popover">
            <div class="mini-cal-header">
              <button class="mini-cal-nav" @click="wpPrevMonth">‹</button>
              <span>{{ wpYear }}-{{ String(wpMonth).padStart(2,'0') }}</span>
              <button class="mini-cal-nav" @click="wpNextMonth">›</button>
            </div>
            <div class="mini-cal-grid">
              <span v-for="d in ['S','M','T','W','T','F','S']" :key="d" class="mini-cal-dow">{{ d }}</span>
              <span v-for="(c, i) in wpCells" :key="i" class="mini-cal-day" :class="{empty: !c}" @click="c && pickWeek(c.dateStr)">{{ c ? c.day : '' }}</span>
            </div>
          </div>
        </div>

        <div v-if="timelineDays.length" class="news-timeline">
          <div v-for="day in timelineDays" :key="day.date" class="news-timeline-row">
            <div class="news-timeline-rail"><span class="news-timeline-dot"></span></div>
            <div class="news-timeline-content">
              <div class="news-day-label">{{ fmtDayLabel(day.date) }}</div>
              <div class="news-card-grid">
                <div v-for="a in day.articles" :key="a.id" class="news-card clickable" @click="openArticle(a.id, day.articles.map(x => x.id))">
                  <div class="news-card-title">{{ a.title }}</div>
                  <div class="news-time">{{ a.source_name }} · {{ fmtTime(a.published_at) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="store.newsWeek" class="empty-state">No articles in this week.</div>
      </template>

      <div v-else class="empty-state">
        No articles yet - the daily scrape hasn't run. It kicks off automatically the next time this page loads after the scheduled hour.
      </div>
    </template>
  </div>
  `,
};
