import json
import os
import time
import requests


# ==============================
# 配置
# ==============================

# 每次运行抓多少页
PAGES_PER_RUN = 100

# 数据文件
output_file = "data/movies.json"

# 进度文件
progress_file = "data/progress.json"


# ==============================
# 读取源配置
# ==============================

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


# ==============================
# 读取旧影视数据
# ==============================

if os.path.exists(output_file):

    with open(output_file, "r", encoding="utf-8") as f:
        old_movies = json.load(f)

    print(f"读取到旧数据：{len(old_movies)} 部影视")

else:

    old_movies = []

    print("没有旧数据，将创建新的影视库")


# 用 vod_id 建立索引，避免重复
movies_dict = {
    str(movie["id"]): movie
    for movie in old_movies
}


# ==============================
# 读取抓取进度
# ==============================

with open(progress_file, "r", encoding="utf-8") as f:
    progress = json.load(f)


last_page = progress.get("last_page", 0)
total_pages = progress.get("total_pages", 0)
completed = progress.get("completed", False)


print(f"当前已抓到第 {last_page} 页")
print(f"总页数：{total_pages}")


# 如果已经完成
if completed:

    print("历史数据已经全部抓取完成。")

    exit()


# ==============================
# 计算本次抓取范围
# ==============================

start_page = last_page + 1

end_page = min(
    start_page + PAGES_PER_RUN - 1,
    total_pages
)


print(f"\n本次准备抓取：第 {start_page} 页 到 第 {end_page} 页")


# ==============================
# 抓取数据
# ==============================

new_count = 0
updated_count = 0


for page in range(start_page, end_page + 1):

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

        print("没有更多数据，停止抓取。")

        end_page = page - 1

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


        # 判断新增
        if movie_id not in movies_dict:

            new_count += 1


        # 判断更新
        elif movies_dict[movie_id] != item:

            updated_count += 1


        # 保存最新数据
        movies_dict[movie_id] = item


    # 避免请求太快
    time.sleep(0.5)


# ==============================
# 保存影视库
# ==============================

result = list(movies_dict.values())


# 按更新时间倒序
result.sort(
    key=lambda x: x.get("update_time") or "",
    reverse=True
)


with open(output_file, "w", encoding="utf-8") as f:

    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


# ==============================
# 更新进度
# ==============================

progress["last_page"] = end_page


if end_page >= total_pages:

    progress["completed"] = True


with open(progress_file, "w", encoding="utf-8") as f:

    json.dump(
        progress,
        f,
        ensure_ascii=False,
        indent=2
    )


# ==============================
# 输出结果
# ==============================

print("\n==============================")
print(f"本次新增影视：{new_count}")
print(f"本次更新影视：{updated_count}")
print(f"影视库总数：{len(result)}")
print(f"当前已抓到第：{end_page} 页")
print(f"是否完成：{progress['completed']}")
print("==============================")
