# update_news.py
import re
import requests
import json
import os
from gtts import gTTS
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List
from google import genai
from google.genai import types
import xml.etree.ElementTree as ET # Added for Entrez
import time # Added for Entrez

NEWS_PATH = "news.jsonl"
PROCESSED_IDS_PATH = "processed_ids.txt"

# 特殊標記，用於獲取最新的 PubMed 文章，不指定醫學關鍵詞
GET_LATEST_PUBMED_FLAG = "__GET_LATEST_PUBMED_ARTICLES__"

QUERY = [
    "artificial intelligence", 
    "machine learning", 
    "deep learning", 
    "cancer treatment", 
    "diabetes management",
    GET_LATEST_PUBMED_FLAG # 加入特殊標記以獲取最新文章
] 

# === Entrez API Constants ===
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
# API_KEY = None # Consider using an API key for higher request rates

# === 設定 Gemini API 金鑰 ===
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# === 定義結構化輸出的 Pydantic 模型 ===
class ArticleTranslation(BaseModel):
    """研究文章翻譯結果的結構化模型"""
    title_zh: str = Field(description="研究文章的繁體中文標題")
    summary_zh: str = Field(description="適合收聽的簡明中文摘要")
    applications: List[str] = Field(
        description="三個應用場景的描述",
        min_items=3,
        max_items=3
    )
    # pitch field is intentionally omitted as per user's latest news_update.py

# === 輔助函式：讀取與儲存已處理的 ID ===
def load_processed_ids(path=PROCESSED_IDS_PATH):
    if not os.path.exists(path):
        return set()
    with open(path, "r") as f:
        return set(line.strip() for line in f.readlines())

def save_processed_ids(ids, path=PROCESSED_IDS_PATH):
    with open(path, "w") as f:
        f.write("\n".join(ids))

# === Entrez API 輔助函式 ===
def search_pubmed(query, retmax=5, api_key=None):
    """使用 ESearch 搜尋 PubMed 文章 ID (PMID)"""
    
    search_term = query
    if query == GET_LATEST_PUBMED_FLAG:
        print(f"正在使用 ESearch 搜尋 PubMed 最新文章 (無特定關鍵詞)...")
        search_term = "pubmed[sb]" # "pubmed[sb]" 或 "journal article[ptyp]" 是常用的通用查詢
    else:
        print(f"正在使用 ESearch 搜尋 PubMed，查詢：'{query}'")

    params = {
        "db": "pubmed",
        "term": search_term,
        "retmode": "json",
        "retmax": retmax,
        "sort": "date" # 確保按日期排序以獲取最新
    }
    if api_key:
        params["api_key"] = api_key

    try:
        response = requests.get(f"{EUTILS_BASE_URL}esearch.fcgi", params=params)
        response.raise_for_status() 
        data = response.json()
        
        pmids = data.get("esearchresult", {}).get("idlist", [])
        if pmids:
            print(f"ESearch 找到 {len(pmids)} 個 PMID。")
        else:
            print(f"ESearch 未找到任何 PMID (查詢詞: '{search_term}')。")
        return pmids
    except requests.exceptions.RequestException as e:
        print(f"ESearch 請求失敗 (查詢詞: '{search_term}'): {e}")
    except json.JSONDecodeError:
        print(f"ESearch 回應 JSON 解碼失敗 (查詢詞: '{search_term}')。回應內容：\n{response.text}")
    return []

def fetch_pubmed_articles_details(pmids, api_key=None):
    """使用 EFetch 根據 PMID 列表取得文章詳細資訊 (摘要)"""
    if not pmids:
        return []

    print(f"正在使用 EFetch 取得 {len(pmids)} 篇文章的詳細資訊...")
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract"
    }
    if api_key:
        params["api_key"] = api_key

    articles_data = []
    try:
        response = requests.get(f"{EUTILS_BASE_URL}efetch.fcgi", params=params)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        for pubmed_article in root.findall(".//PubmedArticle"):
            article_info = {}
            pmid_node = pubmed_article.find(".//PMID")
            if pmid_node is not None:
                article_info["pmid"] = pmid_node.text
            
            title_node = pubmed_article.find(".//ArticleTitle")
            if title_node is not None:
                article_info["title"] = "".join(title_node.itertext()).strip()
            else:
                article_info["title"] = "無標題"

            abstract_parts = []
            for part_node in pubmed_article.findall(".//Abstract/AbstractText"):
                text_content = "".join(part_node.itertext()).strip()
                if text_content:
                    label = part_node.get("Label")
                    if label:
                        abstract_parts.append(f"{label}: {text_content}")
                    else:
                        abstract_parts.append(text_content)
            
            if abstract_parts:
                article_info["abstract"] = "\n".join(abstract_parts)
            else:
                article_info["abstract"] = "無摘要"
            
            articles_data.append(article_info)
        
        print(f"EFetch 成功解析 {len(articles_data)} 篇文章的資訊。")
        return articles_data
        
    except requests.exceptions.RequestException as e:
        print(f"EFetch 請求失敗：{e}")
    except ET.ParseError as e:
        print(f"EFetch XML 解析失敗：{e}\n回應內容：\n{response.text[:500]}...")
    return []

# === 抓取 Entrez PubMed 研究文章 (適用於 news_update.py) ===
def fetch_entrez_articles_for_news_update(query_term, articles_per_query=1):
    processed_ids = load_processed_ids()
    
    display_query_term = query_term
    if query_term == GET_LATEST_PUBMED_FLAG:
        display_query_term = "最新 PubMed 文章 (無特定關鍵詞)"
    print(f"為查詢 '{display_query_term}' 從 PubMed 抓取文章...")

    pmids_to_search = articles_per_query + 15 
    
    all_found_pmids = search_pubmed(query_term, retmax=pmids_to_search)
    
    if not all_found_pmids:
        return []

    new_pmids_to_fetch_details = []
    for pmid in all_found_pmids:
        if pmid not in processed_ids:
            new_pmids_to_fetch_details.append(pmid)
            if len(new_pmids_to_fetch_details) >= articles_per_query:
                break
    
    if not new_pmids_to_fetch_details:
        print(f"沒有為查詢 '{display_query_term}' 找到新的、未處理的 PMID。")
        return []

    time.sleep(0.4) 
    
    raw_articles_details = fetch_pubmed_articles_details(new_pmids_to_fetch_details)

    formatted_articles = []
    for raw_article in raw_articles_details:
        pmid = raw_article.get("pmid")
        if not pmid:
            continue

        title = raw_article.get("title", "無標題")
        summary = raw_article.get("abstract", "無摘要")

        if not summary or len(summary.strip()) < 50:
            print(f"PMID {pmid} ('{title}') 的摘要過短或不存在，跳過。")
            continue
        
        article_query_source = query_term
        if query_term == GET_LATEST_PUBMED_FLAG:
            article_query_source = "Latest PubMed Articles" # Store a meaningful query source

        article_data = {
            "query": article_query_source,
            "id": pmid,
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "title": title,
            "summary": summary,
            "authors": ["作者資訊需擴展 EFetch 解析"],
            "published_date": "日期需擴展 EFetch 解析", 
            "journal": "期刊需擴展 EFetch 解析",
            "doi": "DOI 需擴展 EFetch 解析",
            "source": "PubMed"
        }
        formatted_articles.append(article_data)
        processed_ids.add(pmid) 
    
    save_processed_ids(processed_ids)
    
    return formatted_articles

# === 使用 Gemini 結構化輸出進行翻譯 ===
def summarize_to_chinese(title, summary):
    """使用新的 Google GenAI SDK 和結構化輸出進行研究文章翻譯"""
    prompt = (
        f"請將以下生醫研究文章標題與摘要翻譯成繁體中文，並完成以下任務：\n"
        f"1. 將摘要濃縮成適合收聽且簡明扼要的中文摘要（約100-150字）。\n"
        f"2. 設想3個應用場景，用簡單易懂的口語描述，讓一般人能理解這項研究的價值。\n"
        f"英文標題：{title}\n"
        f"英文摘要：{summary}\n"
    )
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=ArticleTranslation,
                temperature=0.7,
                max_output_tokens=2000,
            ),
        )
        
        result = response.parsed
        
        return {
            "title_zh": result.title_zh,
            "summary_zh": result.summary_zh,
            "applications": result.applications
            # pitch is not included as per user's latest ArticleTranslation model
        }
        
    except Exception as e:
        print(f"翻譯過程中發生錯誤: {e}")
        return {
            "title_zh": f"[翻譯失敗] {title}",
            "summary_zh": f"摘要翻譯失敗：{str(e)}",
            "applications": ["應用場景1：翻譯失敗", "應用場景2：翻譯失敗", "應用場景3：翻譯失敗"]
            # pitch is not included
        }

# === 將摘要轉成語音檔 ===
def save_audio(text, filename):
    try:
        tts = gTTS(text, lang='zh-tw')
        tts.save(filename)
    except Exception as e:
        print(f"語音生成失敗: {e}")

# === 主流程 ===
def main():
    os.makedirs("audios", exist_ok=True)

    articles_collection = [] # Renamed to avoid confusion with 'articles' inside the loop
    for query_idx, query_term in enumerate(QUERY):
        display_query_log = query_term
        if query_term == GET_LATEST_PUBMED_FLAG:
            display_query_log = "最新 PubMed 文章 (無特定關鍵詞)"
        
        print(f"======== 正在處理查詢: {display_query_log} ========")
        if query_idx > 0:
            print("在處理下一個查詢前，暫停1秒以遵守API速率限制...")
            time.sleep(1) 

        # Fetch 1 new article per query term
        newly_fetched = fetch_entrez_articles_for_news_update(query_term, articles_per_query=1)
        
        if newly_fetched:
            articles_collection.extend(newly_fetched)
            # It's possible newly_fetched has more than one if articles_per_query was > 1
            # and multiple new ones were found. For now, print the last one from the extended list.
            if articles_collection:
                 print(f"已抓取 '{articles_collection[-1]['title']}' (來源: {display_query_log})")
    
    print(f"======== 總共抓取到 {len(articles_collection)} 篇文章 ========")
    
    if not articles_collection:
        print("沒有抓到任何新文章，本次無更新。")
        return
        
    for i, article_detail in enumerate(articles_collection): # Renamed to avoid confusion
        print(f"======== 正在處理已抓取的第 {i+1} 篇文章: {article_detail['title']} ========")
        translation_result = summarize_to_chinese(article_detail['title'], article_detail['summary'])
        
        audio_content = (
            f"{translation_result['title_zh']}\n\n"
            f"{translation_result['summary_zh']}\n\n"
            f"這項研究的應用場景：\n"
            f"第一，{translation_result['applications'][0]}\n"
            f"第二，{translation_result['applications'][1]}\n" 
            f"第三，{translation_result['applications'][2]}\n\n"
        )
        
        audio_path = f"audios/{article_detail['id']}.mp3" # Use PMID for filename
        save_audio(audio_content, audio_path)

        article_data_to_save = article_detail.copy()
        article_data_to_save.update({
            "title_zh": translation_result['title_zh'],
            "summary_zh": translation_result['summary_zh'],
            "applications": translation_result['applications'],
            # "pitch": translation_result.get('pitch', 'N/A'), # pitch is not in translation_result
            "audio": audio_path,
            "timestamp": datetime.now().isoformat()
        })
        
        with open(NEWS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(article_data_to_save, ensure_ascii=False) + "\n")

    print("✅ 更新完成：news.jsonl 和 MP3 音檔已產生")

if __name__ == "__main__":
    main()
