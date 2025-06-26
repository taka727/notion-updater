import requests
import os
from datetime import datetime
from dotenv import load_dotenv
import re
from dateutil import parser

def get_env(name):
    if os.getenv("AWS_EXECUTION_ENV"):
        # Lambda上（.envは使えない）
        return os.getenv(name)
    else:
        load_dotenv()
        return os.getenv(name)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("DATABASE_ID")
PARENT_PAGE_ID = os.getenv("PARENT_PAGE_ID")

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def extract_english_terms(title: str) -> str:
    words = re.findall(r'[A-Za-z0-9]+', title)
    return '-'.join(words)

def get_child_pages_from_column_lists(parent_id):
    url = f"https://api.notion.com/v1/blocks/{parent_id}/children?page_size=100"
    res = requests.get(url, headers=headers)
    blocks = res.json().get("results", [])
    found_pages = []

    for block in blocks:
        if block["type"] == "column_list" and block.get("has_children", False):
            # column_listを深掘り
            column_blocks = get_child_pages_recursively(block["id"])

            for column in column_blocks:
                found_pages.append({
                    "title": column["title"],
                    "id": column["id"],
                    "created_time": column["created_time"],
                    "last_edited_time": column["last_edited_time"]
                })
    return found_pages

# 1. データベースの全ページ（行）を取得
def get_all_pages(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    res = requests.post(url, headers=headers)
    return res.json().get("results", [])

# ヘルパー関数：ブロックの子要素を取得
def get_child_pages_recursively(parent_id):
    url = f"https://api.notion.com/v1/blocks/{parent_id}/children?page_size=100"
    res = requests.get(url, headers=headers)
    blocks = res.json().get("results", [])
    found_pages = []

    for block in blocks:
        block_type = block.get("type")

        if block_type == "child_page":
            found_pages.append({
                "title": block["child_page"]["title"],
                "id": block["id"],
                "created_time": block["created_time"],
                "last_edited_time": block["last_edited_time"]
            })

        elif block.get("has_children", False):
            # deeper recursion into nested structures (column, toggle, etc.)
            found_pages.extend(get_child_pages_recursively(block["id"]))

    return found_pages
  
def add_to_database(page_title, page_id, created_time, last_edited_time):
    url = "https://api.notion.com/v1/pages"
    format_title = extract_english_terms(page_title)
    format_page_id = page_id.replace('-', '')
    page_url = "https://www.notion.so/" +format_title+"-"+format_page_id
    data = {
        "parent": { "database_id": DATABASE_ID },
        "properties": {
            "ページ名": {
                "title": [{
                    "text": { "content": page_title }
                }]
            },
            "URL" : {
                "url" : page_url
            },
            "作成日": {
                "date": { "start": created_time }
            },
            "最終更新日": {
                "date": { "start": last_edited_time }
            },
            "比較用更新日": {
                "date": { "start": last_edited_time }
            },
            "更新回数" : {
                "number": 0
            },
            "ステータス" : {
                "status":{
                    "name": "未復習",
                }
            }
        }
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code != 200:
        print(f"Error: {res.text}")
    else:
        print(f"✅ 登録済: {page_title} 作成日：{created_time} 最終更新日：{last_edited_time}")

def update_page(notion_page_id, page_title, page_url, created_time, last_edited_time,count,status):
    url = f"https://api.notion.com/v1/pages/{notion_page_id}"
    data = {
        "properties": {
            "ページ名": {
                "title": [{
                    "text": { "content": page_title }
                }]
            },
            "URL": { "url": page_url },
            "作成日": { "date": { "start": created_time } },
            "最終更新日": { "date": { "start": last_edited_time } },
            "更新回数": { "number" : count},
            "ステータス":{
                "status":{
                    "name": status
                }
            }
        }
    }
    res = requests.patch(url, headers=headers, json=data)
    if res.status_code != 200:
        print(f"❌ 更新失敗: {page_title} | {res.text}")
    else:
        print(f"🔄 更新済: {page_title}")

def main():
    existing_pages = get_all_pages(DATABASE_ID)
    existing_title_map = {}
    for page in existing_pages:
        props = page["properties"]
        title = props["ページ名"]["title"][0]["text"]["content"]
        update_count = props["更新回数"]["number"] if "更新回数" in props else 0
        elapsed_days = props["経過日数"]["formula"]["number"]
        status = props["ステータス"]["status"]["name"]
        compar = props["比較用更新日"]["date"]["start"]
        existing_title_map[title] = {
            "id": page["id"],
            "count": update_count,
            "elapsed_days" : elapsed_days,
            "date_for_comparison" : compar,
            "status":status,
        }
    pages = get_child_pages_from_column_lists(PARENT_PAGE_ID)
    for page in pages:
        page_id = page["id"]
        title = page["title"]
        created = page["created_time"]
        edited = page["last_edited_time"]
        format_title = extract_english_terms(title)
        format_page_id = page_id.replace('-', '')
        page_url = f"https://www.notion.so/{format_title}-{format_page_id}"

        if title in existing_title_map:
            exist_date_time = parser.parse(existing_title_map[title]["date_for_comparison"])
            edited_date_time = parser.parse(edited)
            new_elapsed = existing_title_map[title]["elapsed_days"] + 1
            status = existing_title_map[title]["status"]
            count = existing_title_map[title]["count"]
            if existing_title_map[title]["count"] == 0 :
                if new_elapsed == 1:
                    status = "第一復習"
                    is_update = True
            elif existing_title_map[title]["count"] == 2:
                if new_elapsed == 3:
                    status = "第二復習"
                    is_update = True
            elif existing_title_map[title]["count"] == 3 :
                if new_elapsed == 4:
                    status = "第三復習"
                    is_update = True
            elif existing_title_map[title]["count"] == 4:
                if new_elapsed == 5:
                    status == "定着確認"
                    is_update = True
            else:
                status = "完了"
                is_update = True
            if exist_date_time < edited_date_time :
                count = count + 1
                is_update = True

            if is_update:
                update_page(existing_title_map[title]["id"],title,page_url,created,edited,count,status)
        else:
            add_to_database(title, page_id, created, edited)

if __name__ == "__main__":
    main()