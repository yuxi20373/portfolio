# Knowledge Chatbot(知識型聊天機器人)

一個結合 LangGraph deep agent(工具呼叫 + 短期記憶壓縮)、使用者自主維護的
Wiki 知識庫,以及對話/wiki 條目/Markdown 筆記行事曆的聊天機器人。

前端(透過 CDN 引入的 Vue 3,無需建置工具)跟後端(FastAPI)可以獨立部署——
前端部署在 **Vercel**、後端部署在 **Render**——但兩者都放在同一個 repo
裡,以相鄰資料夾的方式共存。

```
knowledge-chatbot/
├── backend/    FastAPI + LangGraph deep agent + SQLite  -> 部署在 Render
│   └── README.md   完整的安裝、架構與 Render 部署說明
└── frontend/   Vue 3(CDN)SPA,不需要建置步驟   -> 部署在 Vercel
    └── README.md   本機開發與 Vercel 部署說明
```

## 快速本機開發

```bash
# 後端
cd backend
conda create -n knowledge-chatbot python=3.11 -y && conda activate knowledge-chatbot
pip install -r requirements.txt
cp .env.example .env   # 至少要設定 GROQ_API_KEY
python run.py          # -> http://localhost:8000

# 前端(另開一個終端機)- 任何靜態檔案伺服器都可以
cd frontend
python -m http.server 5500   # -> http://localhost:5500
```

預設情況下,前端會直接對「載入這個頁面的來源」發送請求(`window.API_BASE_URL`
是空字串)。如果本機開發時前端跟後端用不同的 port,可以選擇讓兩者共用同一個
來源(origin),或是直接在 `frontend/assets/js/config.js` 裡設定
`window.API_BASE_URL = "http://localhost:8000"` 做測試用。

## 正式部署(Vercel + Render)

1. **先部署後端**——見 `backend/README.md`。部署到 Render(根目錄設為
   `backend`),在那邊把你的 API 金鑰設成環境變數,並記下部署後的網址
   (例如 `https://your-backend.onrender.com`)。
2. **部署前端**——見 `frontend/README.md`。部署到 Vercel(根目錄設為
   `frontend`),並把 `API_BASE_URL` 環境變數設成步驟 1 拿到的 Render
   網址。
3. 回到 Render,把 `CORS_ALLOWED_ORIGINS` 設成你的 Vercel 網址(比預設的
   「允許所有來源」更嚴謹)。

每個 README 裡都有詳細的 Dashboard 操作步驟。

## 功能亮點

- **首頁**——一個有主題風格的首頁,中央有主視覺圖片,周圍浮動著可點擊的
  圖示(把你自己的透明背景 PNG 放進 `frontend/assets/images/` 即可——放圖片
  之前會先用純 SVG icon 頂著),可以連到 Wiki/行事曆頁面,也能切換淺色/
  深色主題。
- **是 deep agent,不是單純的對話迴圈**——用 `deepagents`(基於
  LangGraph),搭配一個 `web_search` 工具,以及一個 `update_wiki` 工具,
  只有在你明確要求它儲存內容時才會呼叫。
- **短期記憶壓縮**——比較早的對話回合會被摺疊成一段持續更新的摘要,而
  不是每次都把完整歷史重新送出,藉此壓低輸入 token 用量。
- **使用者主導的 wiki,不是自動生成**——條目只會透過聊天、Search 面板
  (網路搜尋+你的問題)、Adjust 側欄(先提案、你確認後才套用的自然語言
  編輯),或是直接手動編輯來建立/更新。你可以自己建立資料夾來整理條目,
  並手動搬移。
- **行事曆**——月曆格狀檢視 + 當日詳情,顯示對話、wiki 條目跟 Markdown
  筆記(各自有自己的編輯器/預覽跟編輯/刪除功能),角落還有台中的
  下雨/不下雨天氣圖示,會隨著選取的日期變化。
- **透過 Langfuse 追蹤 token/花費**,顯示在每則回覆的角落。
- **LINE Bot 隨時可接**——同一套 agent/session 邏輯也支援 LINE webhook。

完整細節、環境變數說明跟疑難排解都在 `backend/README.md`。
