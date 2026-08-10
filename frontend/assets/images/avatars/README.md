# 頭貼預設圖片

把 8 張 PNG 圖片放在這裡,檔名固定是:

```
avatar-1.png
avatar-2.png
avatar-3.png
avatar-4.png
avatar-5.png
avatar-6.png
avatar-7.png
avatar-8.png
```

建議尺寸約 200×200,正方形,透明背景或有自己的背景都可以(顯示時會被裁成
圓形)。這份清單定義在 `frontend/assets/js/avatars.js`(`AVATAR_PRESETS`),
使用者在「編輯帳號」畫面裡從這 8 張裡挑一張當頭貼,不能自己上傳圖片。

跟首頁圖片同一套規則:還沒放圖片之前,對應的頭貼選項會優雅地退回成一個
簡單的人形 SVG icon(見 `icons.js` 的 `icons.user`),不會顯示破圖,所以
可以一張一張慢慢補。
