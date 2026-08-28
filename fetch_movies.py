import json
import os
import time
import requests


# ==============================
# 配置
# ==============================

# 历史数据阶段，每次抓多少页
PAGES_PER_RUN = 300

# 增量检测时，最多保存多少个最新 ID
LATEST_IDS_COUNT = 50

# 数据文件
output_file = "data/movies.json"

# 进度文件
progress_file = "data/progress.json"

# 请求间隔
REQUEST_DELAY = 0.5


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
    if movie.get("id") is not None
}


# ==============================
# 读取抓取进度
# ==============================

if os.path.exists(progress_file):

    with open(progress_file, "r", encoding="utf-8") as f:
        progress = json.load(f)

else:

    progress = {}


last_page = progress.get("last_page", 0)
total_pages = progress.get("total_pages", 0)
completed = progress.get("completed", False)

# 保存上一次检测到的最新影片 ID
latest_ids = progress.get("latest_ids", [])


print(f"当前已抓到第 {last_page} 页")
print(f"总页数：{total_pages}")
print(f"历史抓取完成：{completed}")


# ==============================
# 获取第一页
# ==============================

separator = "&" if "?" in base_url else "?"

first_page_url = f"{base_url}{separator}pg=1"


def get_page(page):

    separator = "&" if "?" in base_url else "?"

    url = f"{base_url}{separator}pg={page}"

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ==============================
# 将源数据转换成影片数据
# ==============================

def make_movie_item(movie):

    return {
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


# ==============================
# 第一次请求第一页
# ==============================

print("\n正在检查第 1 页最新数据...")

try:

    first_data = get_page(1)

except Exception as e:

    print(f"请求第 1 页失败：{e}")

    exit()


first_page_movies = first_data.get("list", [])

if not first_page_movies:

    print("第 1 页没有获取到影视数据。")

    exit()


# 获取总页数
if total_pages == 0:

    try:

        total_pages = int(
            first_data.get("pagecount", 0)
        )

    except:

        total_pages = 0


print(f"当前总页数：{total_pages}")


# 当前第一页最新影片 ID
current_latest_ids = [

    str(movie.get("vod_id"))

    for movie in first_page_movies[:LATEST_IDS_COUNT]

    if movie.get("vod_id") is not None
]


# ==================================================
# 第一阶段：历史数据还没有抓完
# ==================================================

if not completed:

    print("\n================================")
    print("当前模式：历史数据抓取")
    print("================================")


    start_page = last_page + 1


    end_page = min(
        start_page + PAGES_PER_RUN - 1,
        total_pages
    )


    print(
        f"本次准备抓取："
        f"第 {start_page} 页 到 第 {end_page} 页"
    )


    new_count = 0
    updated_count = 0


    for page in range(
        start_page,
        end_page + 1
    ):


        print(
            f"\n正在获取第 {page} 页"
        )


        try:

            # 第 1 页已经请求过，避免重复请求
            if page == 1:

                data = first_data

            else:

                data = get_page(page)


        except Exception as e:

            print(
                f"第 {page} 页请求失败：{e}"
            )

            break


        movies = data.get(
            "list",
            []
        )


        print(
            f"第 {page} 页获取到 "
            f"{len(movies)} 部影视"
        )


        if not movies:

            print(
                "没有更多数据，停止抓取。"
            )

            end_page = page - 1

            break


        for movie in movies:


            movie_id = str(
                movie.get("vod_id")
            )


            item = make_movie_item(
                movie
            )


            # 判断新增
            if movie_id not in movies_dict:

                new_count += 1


            # 判断更新
            elif movies_dict[movie_id] != item:

                updated_count += 1


            # 保存最新数据
            movies_dict[
                movie_id
            ] = item


        # 每页保存一次进度
        progress["last_page"] = page
        progress["total_pages"] = total_pages
        progress["completed"] = (
            page >= total_pages
        )


        with open(
            progress_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                progress,
                f,
                ensure_ascii=False,
                indent=2
            )


        time.sleep(
            REQUEST_DELAY
        )


    # 更新最新 ID
    progress["latest_ids"] = (
        current_latest_ids
    )


# ==================================================
# 第二阶段：历史抓取已经完成
# 增量检测
# ==================================================

else:

    print("\n================================")
    print("当前模式：增量检测")
    print("================================")


    # --------------------------------
    # 如果没有历史最新 ID
    # 先初始化
    # --------------------------------

    if not latest_ids:

        print(
            "没有找到历史最新 ID，"
            "正在初始化增量检测..."
        )


        progress["latest_ids"] = (
            current_latest_ids
        )


        with open(
            progress_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                progress,
                f,
                ensure_ascii=False,
                indent=2
            )


        print(
            "增量检测初始化完成。"
        )

        exit()


    # --------------------------------
    # 检查有没有新增
    # --------------------------------

    new_movies = []


    for movie in first_page_movies:


        movie_id = str(
            movie.get("vod_id")
        )


        # 找到旧数据
        # 后面的都已经处理过
        if movie_id in latest_ids:

            break


        new_movies.append(
            movie
        )


    # --------------------------------
    # 没有新增
    # --------------------------------

    if not new_movies:

        print(
            "\n没有检测到新增影视。"
        )


        # 更新最新 ID
        progress["latest_ids"] = (
            current_latest_ids
        )


        with open(
            progress_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                progress,
                f,
                ensure_ascii=False,
                indent=2
            )


        exit()


    # --------------------------------
    # 有新增
    # --------------------------------

    print(
        f"\n检测到新增影视："
        f"{len(new_movies)} 部"
    )


    new_count = 0
    updated_count = 0


    for movie in new_movies:


        movie_id = str(
            movie.get("vod_id")
        )


        item = make_movie_item(
            movie
        )


        if movie_id not in movies_dict:

            new_count += 1

        else:

            updated_count += 1


        movies_dict[
            movie_id
        ] = item


    # 更新最新 ID
    progress["latest_ids"] = (
        current_latest_ids
    )


# ==============================
# 保存影视库
# ==============================

result = list(
    movies_dict.values()
)


# 按更新时间倒序
result.sort(

    key=lambda x:
        x.get("update_time") or "",

    reverse=True
)


# ==================================================
# 增量模式下保持影视库大小
# ==================================================

if completed:

    old_count = len(old_movies)

    new_total = len(result)


    # 如果因为新增导致数量增加
    if new_total > old_count:


        remove_count = (
            new_total - old_count
        )


        print(
            f"\n本次新增导致影视库增加 "
            f"{remove_count} 部"
        )


        print(
            f"删除最旧的 "
            f"{remove_count} 部影视"
        )


        result = result[
            :old_count
        ]


# ==============================
# 保存 movies.json
# ==============================

with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        result,
        f,
        ensure_ascii=False,
        indent=2
    )


# ==============================
# 更新进度
# ==============================

progress["last_page"] = (
    min(
        last_page + PAGES_PER_RUN,
        total_pages
    )
    if not completed
    else last_page
)


progress["total_pages"] = (
    total_pages
)


# 如果历史抓取完成
if progress["last_page"] >= total_pages:

    progress["completed"] = True


with open(
    progress_file,
    "w",
    encoding="utf-8"
) as f:

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

print(
    f"本次新增影视："
    f"{new_count if 'new_count' in locals() else 0}"
)

print(
    f"本次更新影视："
    f"{updated_count if 'updated_count' in locals() else 0}"
)

print(
    f"影视库总数："
    f"{len(result)}"
)

print(
    f"当前已抓到第："
    f"{progress['last_page']} 页"
)

print(
    f"是否完成："
    f"{progress['completed']}"
)

print("==============================")
