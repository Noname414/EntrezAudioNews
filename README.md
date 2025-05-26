# Listen Research News

這是一個自動抓取、翻譯和朗讀 EuropePMC 生醫研究文章摘要的網站專案。

網站連結：[https://noname414.github.io/listen-research-news/](https://noname414.github.io/listen-research-news/)

## 功能特色

- 自動抓取 EuropePMC 最新生醫研究文章
- 使用最新的 **Gemini 2.0 Flash** 和 **結構化輸出** 翻譯研究摘要為繁體中文
- 生成生活化應用場景和創投推銷內容
- 生成中文語音朗讀檔
- 使用 JSONL 格式儲存資料，支援增量更新
- 響應式前端設計，支援中英文切換
- 整合 APlayer 音訊播放器
- GitHub Actions 自動排程更新和部署到 GitHub Pages

## 技術亮點

### 🚀 最新 Gemini API 整合

- 使用新的 `google-genai` Python SDK
- 採用 **結構化輸出 (Structured Output)** 功能
- 使用 Pydantic 模型定義回應格式，確保資料一致性
- 支援錯誤處理和回退機制

### 📊 結構化資料處理

```python
class ArticleTranslation(BaseModel):
    title_zh: str = Field(description="研究文章的繁體中文標題")
    summary_zh: str = Field(description="適合收聽的簡明中文摘要")
    applications: List[str] = Field(description="三個生活化應用場景的描述")
    pitch: str = Field(description="向創投或天使基金推銷的內容")
```

## 使用方法

1. Clone 本儲存庫
2. 安裝 Python 依賴：`pip install -r requirements.txt`
3. 設定 `GEMINI_API_KEY` 環境變數
4. 執行 `python news_update.py` 抓取並更新研究文章
5. 開啟 `index.html` 查看網站 (本地測試) 或部屬到網頁伺服器

### 測試功能

執行測試腳本來驗證翻譯功能：

```bash
python test_translation.py
```

## 依賴項目

- `requests` - HTTP 請求庫，用於調用 EuropePMC API
- `gtts` - 文字轉語音
- `google-genai` - 新版 Google GenAI SDK
- `pydantic` - 資料驗證和結構化輸出

## GitHub Actions 自動更新與部署

專案設定了 GitHub Actions，會自動執行以下任務：

- **每小時**抓取最新的 EuropePMC 生醫研究文章
- 使用 Gemini 2.0 Flash 生成結構化的中文翻譯和語音檔
- 將更新的資料提交回 `main` 分支
- 將網站檔案部署到 `gh-pages` 分支，供 GitHub Pages 展示

網站部屬在 GitHub Pages，連結為：[https://noname414.github.io/EntrezAudioNews/](https://noname414.github.io/EntrezAudioNews/)

## 更新日誌

### v2.0 - 結構化輸出重構

- 🔄 升級到新的 `google-genai` SDK
- 📊 採用 Gemini API 結構化輸出功能
- 🛡️ 使用 Pydantic 模型確保資料一致性
- 🔧 改進錯誤處理和回退機制
- ✅ 新增測試腳本驗證功能
