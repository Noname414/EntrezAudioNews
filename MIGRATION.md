# 遷移指南：升級到結構化輸出版本

本指南說明如何從舊版本的 `google-generativeai` SDK 升級到新版本的 `google-genai` SDK 和結構化輸出功能。

## 主要變更

### 1. SDK 更換

- **舊版**: `google-generativeai`
- **新版**: `google-genai`

### 2. API 調用方式變更

#### 舊版本

```python
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")
response = model.generate_content(prompt)
text = response.text.strip()
result = json.loads(text)  # 手動解析 JSON
```

#### 新版本

```python
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

class PaperTranslation(BaseModel):
    title_zh: str = Field(description="論文的繁體中文標題")
    # ... 其他欄位

response = client.models.generate_content(
    model='gemini-2.0-flash-001',
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type='application/json',
        response_schema=PaperTranslation,
    ),
)
result = response.parsed  # 直接獲得結構化物件
```

## 升級步驟

### 1. 更新依賴項

```bash
pip uninstall google-generativeai
pip install google-genai pydantic
```

### 2. 更新 requirements.txt

```
arxiv
gtts
google-genai
pydantic
```

### 3. 更新代碼

參考 `news_update.py` 中的新實現方式。

### 4. 測試功能

```bash
python test_translation.py
```

## 優勢

### 🎯 結構化輸出

- 不再需要手動解析 JSON
- 自動驗證資料格式
- 減少解析錯誤

### 🛡️ 類型安全

- 使用 Pydantic 模型確保資料一致性
- 編譯時類型檢查
- 更好的 IDE 支援

### 🔧 錯誤處理

- 內建錯誤處理機制
- 回退策略
- 更穩定的運行

### 📊 更好的可維護性

- 清晰的資料結構定義
- 易於擴展和修改
- 更好的代碼可讀性

## 注意事項

1. **API 金鑰**: 環境變數名稱保持不變 (`GEMINI_API_KEY`)
2. **模型名稱**: 使用 `gemini-2.0-flash-001` 而非 `gemini-2.0-flash`
3. **回應格式**: 現在直接獲得結構化物件，而非需要解析的字串
4. **錯誤處理**: 新版本有更好的錯誤處理機制

## 疑難排解

### 常見問題

**Q: 安裝新 SDK 時出現衝突**
A: 先完全卸載舊版本：

```bash
pip uninstall google-generativeai google-ai-generativelanguage
pip install google-genai
```

**Q: 結構化輸出不工作**
A: 確保：

- 使用正確的模型名稱 (`gemini-2.0-flash-001`)
- 設定了 `response_mime_type='application/json'`
- 提供了有效的 Pydantic 模型

**Q: 回應格式不正確**
A: 檢查 Pydantic 模型定義是否正確，特別是 Field 描述和約束。

## 參考資源

- [Google GenAI Python SDK 文檔](https://github.com/googleapis/python-genai)
- [Gemini API 結構化輸出文檔](https://ai.google.dev/gemini-api/docs/structured-output)
- [Pydantic 文檔](https://docs.pydantic.dev/)
