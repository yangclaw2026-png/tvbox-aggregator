import json
import os
import time
import requests


# 读取源配置
with open("sources.json", "r", encoding="utf-8") as f:
    config = json.load(f)


# 找到主源
primary_source = next(
    source
    for source in config["cms_sources"]
    if source.get("primary") is True
)

base_url = primary_source["detail_api"]

print(f"正在获取：{primary_source['name']}")

# 先测试抓取前 3 页
MAX_PAGES = 3

result = []

for page in range(1, MAX_PAGES + 1):

    # 第 1 页使用原始地址
    # 后面的页追加 pg 参数
    separator = "&" if "?" in base_url else "?"
    url = f"{base_url}{separator}pg={page}"

    print(f"\n正在获取第 {page} 页：{url}")

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    movies = data.get("list", [])

    print(f"第 {page} 页获取到 {len(movies)} 部影视")

    if not movies:
        print("没有更多数据，停止。")
        break

    for movie in movies:

        item = {
            "id": movie.get("vod_id"),
            "name": movie.get("vod_name"),
            "type": movie.get("type_name"),
            "year": movie.get("vod_year"),
            "area": movie.get("vod_area"),
            "language": movie.get("vod_lang"),
            "category": movie.get("vod_class"),

            "poster": movie.get("vod_pic"),

            "douban_id": movie.get("vod_douban_id"),
            "score": movie.get("vod_douban_score"),

            "remarks": movie.get("vod_remarks"),
            "content": movie.get("vod_content"),

            "play_from": movie.get("vod_play_from"),
            "play_url": movie.get("vod_play_url"),

            "update_time": movie.get("vod_time")
        }

        result.append(item)

    # 稍微停一下，避免连续请求太快
    time.sleep(1)


# 确保 data 文件夹存在
os.makedirs("data", exist_ok=True)


# 保存数据
output_file = "data/movies.json"

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


print("\n==============================")
print(f"总共获取 {len(result)} 部影视")
print(f"成功生成 {output_file}")
print("==============================")
