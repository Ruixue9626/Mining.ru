# 🪨 Mining-ru Discord Bot

一款具備礦業經濟系統、每日簽到、AI 問答與 YouTube 影片下載功能的 Discord 機器人！
[`Discord官方群組`](https://discord.gg/57BMuH6d3X)
[`官方網站`](https://sites.google.com/view/mining-ru/)
[`官方Threads帳號`](https://www.threads.net/@mining.ru_discordbot)

## 🎮 功能簡介

| 指令 | 說明 |
|------|------|
| `/hi` | 和機器人打招呼 👋 |
| `/daily` | 每日簽到領取 20 原礦 |
| `/cu` | 挖掘隨機 1~10 顆銅礦原礦 |
| `/fire <數量>` | 將原礦煉成煉好銅 |
| `/sell <數量> <價格>` | 販售煉好銅，獲得金錢 |
| `/see [@用戶]` | 查看自己或他人的資產狀況 |
| `/say <訊息>` | 讓機器人幫你說話 |
| `/yt <YouTube連結>` | 使用 `yt-dlp` 下載影片 |
| `/ai <訊息>` | 使用 Cohere AI 問問題 |
| `/gift <類型> <@對象> <數量>` | 贈送原礦、煉好銅或金錢給其他用戶 |
| `&gv100 000325` | 限一次領取 100 原礦活動，密碼限定 |

## 💾 玩家資料儲存

- 使用 JSON 存檔保存玩家的礦石、煉好銅與金錢資訊。
- 資料自動在每次操作後儲存。

## 🧠 AI 功能

- 內建 [`Cohere`](https://cohere.com/) 語言模型，能進行簡單的問答對話。
- 使用 `/ai` 指令輸入問題即可獲得 AI 回答。

## 📽️ 影片下載功能

- 利用 `yt-dlp` 下載 YouTube 影片。
- 注意：需先安裝 `yt-dlp` 及系統可用的 `ffmpeg`。

## ⚙️ 安裝與部署

1. 安裝依賴：
   ```bash
   pip install discord cohere
