# Knowledge Chatbot - 後端

FastAPI + 一個 LangGraph deep agent(`deepagents`),搭配 SQLite。獨立
部署在 **Render** 上;前端(Vercel)透過 HTTP/CORS 跟這裡溝通,並不是由
這裡提供服務。

## 架構

```
backend/
├── run.py                  # 開發用進入點:python run.py
├── render.yaml              # Render 藍圖(build/start 指令、環境變數清單)
├── requirements.txt
├── .env.example
└── app/
    ├── main.py               # FastAPI app、routers、CORS、健康檢查
    ├── config.py              # env/.env 設定(pydantic-settings)
    ├── database.py            # SQLAlchemy engine/session
    ├── models/                # ORM models(chat.py、wiki.py 含 WikiFolder、note.py)
    ├── schemas/                # Pydantic 請求/回應 models
    ├── agent/                  # deep agent 本體(LangGraph / deepagents)
    │   ├── agent_factory.py     # 建立並快取 agent、模型/provider 的選擇邏輯
    │   ├── memory_manager.py    # 滾動式短期記憶壓縮
    │   ├── runner.py            # 執行一次 agent 回合,並整理回覆格式
    │   ├── skills/               # 相關時才會載入的 SKILL.md 檔案
    │   └── tools/                 # web_search、update_wiki
    ├── services/                # 商業邏輯(chat、wiki 搜尋/調整、search、標題產生、天氣)
    ├── routers/                 # 輕量的 FastAPI 路由 handler
    ├── integrations/            # groq/openai/langfuse/line 的客戶端
    └── utils/                   # 小型共用工具函式
```

## 本機開發

```bash
conda create -n knowledge-chatbot python=3.11 -y
conda activate knowledge-chatbot
pip install -r requirements.txt

cp .env.example .env
# 至少要設定 GROQ_API_KEY(免費取得:https://console.groq.com/keys)

python run.py   # -> http://localhost:8000
```

可以試著 `curl http://localhost:8000/`——應該會回傳 `{"status": "ok", ...}`。

## 部署到 Render

1. 把這個 repo push 到 GitHub/GitLab。
2. Render dashboard -> **New +** -> **Blueprint** -> 指向這個 repo。
   Render 會讀取 `render.yaml`(裡面已經把 root directory 設成
   `backend` 了)。或者也可以手動建立一個 **Web Service**,root
   directory 設 `backend`,build command 設
   `pip install -r requirements.txt`,start command 設
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`。
3. 在該 service 的 **Environment** 分頁,至少要填入 `GROQ_API_KEY` 的
   真實值(blueprint 裡把敏感資訊標成 `sync: false`,所以要在 Dashboard
   上輸入,不會寫進 git)。
4. 部署完成後,複製部署出來的網址(例如
   `https://knowledge-chatbot-backend.onrender.com`)——前端的
   `API_BASE_URL` 環境變數(見 `frontend/README.md`)會需要用到。
5. 等前端也部署完成之後,回來把 `CORS_ALLOWED_ORIGINS` 設成那個 Vercel
   網址,取代預設的 `*`。

**SQLite 資料持久性**:Render 免費方案的檔案系統是暫時性的——每次重新
部署/重啟,你的資料(`data.db`)都會被清空。如果要長期正式使用,可以
升級方案並掛載一個[持久化硬碟](https://render.com/docs/disks)(見
`render.yaml` 裡註解掉的 `disk:` 區塊,並把 `DATABASE_URL` 改成指向
掛載路徑),或是改用受管理的 Postgres 服務。

## 環境變數

| 變數 | 用途 |
|---|---|
| `GROQ_API_KEY` / `GROQ_MODEL` / `GROQ_SUMMARIZE_MODEL` | Groq(免費方案) |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | OpenAI(選用的替代方案) |
| `LLM_PROVIDER` | `groq` \| `openai` - 一次性呼叫用(標題產生/搜尋/調整/記憶壓縮) |
| `AGENT_MODEL_PROVIDER` | `groq` \| `openai` - 互動式 deep agent 用 |
| `TAVILY_API_KEY` | 選填,搜尋品質較好;不設定則退回不需金鑰的 DuckDuckGo |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` | 選填;每則回覆的 token/花費追蹤 |
| `DATABASE_URL` | 預設是 SQLite;持久性相關說明見上方 |
| `SESSION_TIMEOUT_MINUTES` | LINE 等沒有明確對話邊界的頻道:多久沒動作後開始新的一個 session |
| `MEMORY_RECENT_WINDOW` / `MEMORY_COMPACT_TRIGGER` | 短期記憶壓縮的門檻值 |
| `LINE_CHANNEL_SECRET` / `LINE_CHANNEL_ACCESS_TOKEN` | LINE Bot 用 |
| `CORS_ALLOWED_ORIGINS` | 逗號分隔的允許來源清單;預設是 `*` |

## 運作原理

**是 deep agent,不是單純的對話迴圈。** `app/agent/agent_factory.py` 用
`deepagents.create_deep_agent()`(基於 LangGraph,內建規劃與工具呼叫
能力)組出這個助理。`chat_service.py` 從不直接呼叫 LLM——它負責組出
context,再呼叫 `app/agent/runner.py`。狀態管理沒有用 LangGraph 的
checkpointer,SQL 資料庫才是對話歷史唯一的真實來源,因為行事曆/改名/
刪除功能本來就依賴它——每個回合都會重新組出一份完整的訊息清單。

**工具**:`web_search`(有設定 `TAVILY_API_KEY` 就用 Tavily,否則用不需
金鑰的 DuckDuckGo)跟 `update_wiki`(讓 agent 可以在對話中儲存/更新
wiki 條目,但只有在你明確要求時才會做——見
`app/agent/skills/wiki-management/SKILL.md`)。另外還有一個
`tool-calling-format` skill,協助能力較弱/較小的模型更容易產生格式
正確的工具呼叫。

**短期記憶**:`app/agent/memory_manager.py` 會保留最近
`MEMORY_RECENT_WINDOW` 則訊息的原文,一旦未摘要的訊息累積超過
`MEMORY_COMPACT_TRIGGER` 則,更早的內容就會被摺進一段持續更新的
`ChatSession.memory_summary` 裡——在不遺失早期脈絡的前提下,壓低每個
回合的輸入 token 量。原始訊息本身不會被刪除。

**Wiki**:條目只會在明確動作下才建立/更新——絕對不會有自動背景摘要器在
跑。三條有 LLM 輔助的路徑(聊天裡的 `update_wiki` 工具、Search 面板的
「網路搜尋+你的問題」流程,以及 Adjust 側欄「先提案再確認」的自然語言
編輯)都是用同一套 `entry_type` 段落樣板(`app/services/wiki_templates.py`)
跟共用的排版指引來寫入結構化內容,鼓勵用表格/箭頭/`<mark>` 標記,而不是
一大段散文。Search 這條路徑一律只做「新增」(絕不會移除既有內容);只有
Adjust 這條路徑允許刪減/重新調整結構,而且只會在你明確下指令、並在儲存
前親自確認過才會執行。條目也可以直接手動編輯(不經過 LLM),並整理進
你自己建立的資料夾、自己手動搬移——`entry_type` 只會影響內容(重新)
產生時要用哪些標題,跟資料夾的整理方式無關。

**行事曆**:`/api/calendar` 跟 `/api/calendar/day` 會依建立日期把對話、
wiki 條目跟筆記分組。`/api/weather?date=YYYY-MM-DD`
(`app/services/weather_service.py`)透過
[Open-Meteo](https://open-meteo.com) 回傳台中地區簡單的下雨/不下雨
訊號——免費、不需金鑰、不需額外設定。它會先嘗試一般預報端點(涵蓋最近的
過去到大約 16 天後),找不到資料才會退回歷史檔案端點;如果兩邊都沒有
資料,會回傳 `will_rain: null`,而不是用猜的。前端只需要一個大略的
布林訊號來挑選對應的動畫圖示,所以這裡就只回傳這些——想看更多細節
(氣溫等)可以自己看這個函式。

**花費追蹤**:`app/integrations/langfuse_client.py` 會替每個 agent 回合
掛上一個 Langfuse callback,並在之後盡力去查詢那個回合的花費(Langfuse
是非同步寫入資料的,所以有時候如果資料還沒準備好,畫面上可能會顯示
「N/A」——不過不論如何,追蹤紀錄本身都會出現在你的 Langfuse dashboard
上)。Token 數量是直接從 LLM 回應裡拿的,所以永遠是即時的,不受這個
影響。

**LINE Bot**:`routers/line.py` 重複使用跟網頁版完全一樣的
`chat_service.get_or_create_session` / `process_chat_message`。要串接
的話見下面的 LINE 章節。

## 串接 LINE Bot

1. 在 [LINE Developers Console](https://developers.line.biz/) 建立一個
   **Messaging API** channel,取得 **Channel secret** 跟一組
   **Channel access token(長期有效)**,並把它們設成環境變數。
2. 把 webhook URL 設成 `https://<你的-render-網址>/api/line/webhook`,
   並開啟「Use webhook」。
3. 傳訊息給這個 bot——它會驗證簽章、找出/建立該使用者的 session
   (閒置超過 `SESSION_TIMEOUT_MINUTES` 後會自動開始新的一個),並透過
   deep agent 回覆。

## 補充說明

- API 本身沒有驗證機制——個人使用、網址不公開的情況下沒問題,但不適合
  公開分享。要公開網址前記得先加上驗證機制。
- `langgraph`、`deepagents`、`langchain-core`、`langchain-groq`、
  `langchain-openai` 這幾個套件更新很快,`requirements.txt` 裡刻意沒有
  鎖定版本;如果 `pip install` 抓到有 breaking change 的版本,這個專案
  實際用到的範圍(`create_deep_agent`、`@tool`、`ChatGroq`/`ChatOpenAI`)
  不大,而且都集中在 `app/agent/` 裡。
- Groq 的免費方案跟模型名稱會隨時間變動;如果遇到 429 或是「模型不
  存在」的錯誤,可以查一下 https://console.groq.com。
