# 建立計畫提示詞

建立 PTT 爬蟲工具，支援依分類篩選文章並使用 Firecrawl library 爬取內容，Firecrawl 需要可以支援自架或雲端兩種方案。此系統將實現兩階段爬取流程：首先進入特定看版取得文章列表並進行篩選，再爬取完整 Markdown 格式的文章內容，最終儲存至 PostgreSQL 資料庫內，資料表需要以看板名稱作為區分(e.g. Stock 存放 Stock 看板的文章)。專案採用 uv 管理套件，使用 typer 作為 CLI 工具，使用 dotnet 與 .env檔案設定與管理環境變數並將環境變數集中於 config.py ，並遵循增量爬取和狀態持久化原則。