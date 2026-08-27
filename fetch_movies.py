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


# 数据文件
output_file = "data/movies.json"


# 读取旧数据
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8") as f:
        old_movies = json.load(f)

    print(f"读取到旧数据：{len(old_movies)} 部影视")

else:
    old_movies = []
    print("没有旧数据，将创建新的影视库")


# 用 ID 建立索引
movies_dict = {
    str(movie["id"]): movie
    for movie in old_movies
}


# 统计
new_count = 0
updated_count = 0


# 抓取数据
for page in range(1, MAX_PAGES + 1):

    separator = "&" if "?" in base_url else "?"
    url = f"{base_url}{separator}pg={page}"

    print(f"\n正在获取第 {page} 页")

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

        movie_id = str(movie.get("vod_id"))

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


        # 新电影
        if movie_id not in movies_dict:
            new_count += 1

        # 已有电影，但数据更新
        elif movies_dict[movie_id] != item:
            updated_count += 1


        # 无论新增还是更新，都覆盖成最新数据
        movies_dict[movie_id] = item


    # 避免请求太快
    time.sleep(1)


# 转回列表
result = list(movies_dict.values())


# 按更新时间倒序排列
result.sort(
    key=lambda x: x.get("update_time") or "",
    reverse=True
)


# 保存
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


print("\n==============================")
print(f"新增影视：{new_count}")
print(f"更新影视：{updated_count}")
print(f"影视库总数：{len(result)}")
print(f"成功保存：{output_file}")
print("==============================")
