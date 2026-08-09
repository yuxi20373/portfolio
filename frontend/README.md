# Knowledge Chatbot - 前端

用 Vue 3 打造的單頁應用程式,直接透過 CDN 載入——本機開發不需要打包工具、
不需要 `node_modules`、不需要建置步驟。獨立部署在 **Vercel** 上;透過
HTTP 跟另外部署在 Render 上的後端溝通。

## 架構

```
frontend/
├── index.html                  # SPA 的外殼
├── build.js                     # 只有 Vercel 部署時會用到:把 API_BASE_URL 寫進 config.js
├── package.json                  # 剛好夠讓 Vercel 執行 build.js
├── vercel.json                    # Vercel 用的 buildCommand/outputDirectory 設定
└── assets/
    ├── css/style.css            # 含淺色/深色主題的 CSS 變數
    ├── images/                   # 放你自己的 PNG 圖片 - 見 images/README.md
    └── js/
        ├── config.js              # window.API_BASE_URL(Vercel 上由 build.js 產生)
        ├── app.js                 # 根元件,掛載整個 app
        ├── store.js               # 共用的 reactive 狀態 + actions(含主題)
        ├── api.js                 # fetch 包裝,請求會自動加上 API_BASE_URL 前綴
        ├── icons.js / markdown.js
        └── components/
            ├── Sidebar.js         # icon 導覽列(含首頁)+ 搜尋 + 對話紀錄 + wiki 資料夾 + 迷你行事曆
            ├── HomeView.js        # 有主題風格的首頁:主視覺圖片 + 浮動可點擊圖示
            ├── ChatView.js
            ├── WikiView.js        # 條目詳情、手動編輯、刪除、Search 面板、Adjust 觸發按鈕
            ├── AdjustDrawer.js    # 右側「先提案再確認」的 wiki 編輯面板
            ├── DrawerShell.js     # 共用的可調整寬度右側面板外殼
            ├── CalendarView.js    # 月曆格狀檢視 + 當日詳情 + 筆記(新增/編輯/刪除)+ 天氣小工具
            └── MiniCalendar.js
```

## 本機開發

不需要安裝步驟——單純用靜態伺服器提供這個資料夾,並指向一個正在執行的
後端就好。

```bash
cd frontend
python -m http.server 5500   # -> http://localhost:5500
```

預設情況下 `assets/js/config.js` 裡的 `window.API_BASE_URL = ""`,代表
請求會送到「提供這個頁面的來源」。如果你的後端在本機用不同的 port(例如
`python run.py` 跑在 :8000,這裡跑在 :5500),可以:
- 直接打開 `frontend/index.html`,並把 `assets/js/config.js` 改成
  `window.API_BASE_URL = "http://localhost:8000";` 做本機測試用(測完
  不要把這個改動 commit 進去),或者
- 直接讓兩邊用同一個來源/proxy 提供服務。

## 部署到 Vercel

1. 把這個 repo push 到 GitHub/GitLab。
2. Vercel dashboard -> **Add New** -> **Project** -> 匯入這個 repo。
3. 把 **Root Directory** 設成 `frontend`。
4. Framework preset 選「Other」(Vercel 應該會自動抓到 `vercel.json`,
   裡面已經設定好 build command 是 `npm run build`、輸出目錄是 `.`)。
5. 新增一個環境變數:`API_BASE_URL` = 你的 Render 後端網址(例如
   `https://knowledge-chatbot-backend.onrender.com`)——**在後端還沒
   部署、還沒拿到網址之前先留空。**
6. 部署。`build.js` 會在 Vercel build 過程中執行,把 `API_BASE_URL`
   寫進 `assets/js/config.js`,整個 app 執行時都是讀這裡的值。
7. 之後如果要改 `API_BASE_URL`,要重新觸發一次部署(環境變數的變動不會
   馬上生效,因為它是在 build 時就寫死進去,不是每次請求時才讀取)。

## 補充說明

- **首頁圖片**:首頁(`components/HomeView.js`)會去 `assets/images/`
  找 PNG 圖片(`hero.png`、`icon-light.png`、`icon-wiki.png`、
  `icon-calendar.png`、`icon-weather.png`),缺少的部分會自動退回成純
  SVG icon,所以在你放上自己的美術素材之前,頁面也不會壞掉。確切的
  檔名/尺寸見 `assets/images/README.md`。
- **深色模式**:點擊首頁主視覺圖片上方的浮動按鈕即可切換
  (`store.toggleTheme()`),狀態會存進 `localStorage`,實際套用方式是
  在 `<html>` 上加一個 `data-theme="dark"` 屬性,翻轉 `style.css` 裡的
  CSS 變數。
- 刻意做到完全沒有任何依賴套件——`build.js` 只用了 Node 內建的
  `fs`/`path`。如果之後真的想加入正式的打包工具,這會是一個很自然的
  切入點,但目前所有功能都不需要它。
- Markdown 渲染用的 `marked` 跟 `DOMPurify`,還有 Vue 本身,都是在
  `index.html` 裡用單純的 `<script>` 標籤從 CDN 載入——如果你需要鎖定
  版本或改成自行架設,就是改這裡。
