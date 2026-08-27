import json
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


# 请求第一页完整数据
url = primary_source["detail_api"]

print(f"正在获取：{primary_source['name']}")

response = requests.get(
    url,
    timeout=30
)

response.raise_for_status()

data = response.json()

movies = data.get("list", [])

print(f"获取到 {len(movies)} 部影视")


# 清洗数据
result = []

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


# 保存
output_file = "movies.json"

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


print(f"\n成功生成 {output_file}")

print("\n第一部影视：")

if result:
    print(json.dumps(
        result[0],
        ensure_ascii=False,
        indent=2
    ))
