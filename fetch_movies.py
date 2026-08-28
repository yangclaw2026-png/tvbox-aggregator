import json
import os
import time
import requests


# ==============================
# 配置
# ==============================

# 豆瓣源每页数量通常是 20
# 首次最多抓 300 页
INITIAL_PAGES = 300

# 本地影视库最大保留数量
# 300 页 × 20 部
MAX_MOVIES = 6000

# 请求间隔
REQUEST_DELAY = 0.5

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
# 请求页面
# ==============================

def get_page(page):

    separator = "&" if "?" in base_url else "?"

    url = f"{base_url}{separator}pg={page}"

    print(f"正在获取第 {page} 页")

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ==============================
# 转换影片数据
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

        # 豆瓣源自己的播放地址也保留
        "play_from": movie.get("vod_play_from"),
        "play_url": movie.get("vod_play_url"),

        "update_time": movie.get("vod_time")
    }


# ==============================
# 读取旧影视数据
# ==============================

if os.path.exists(output_file):

    with open(
        output_file,
        "r",
        encoding="utf-8"
    ) as f:

        old_movies = json.load(f)

    print(
        f"读取到旧数据："
        f"{len(old_movies)} 部影视"
    )

else:

    old_movies = []

    print(
        "没有旧数据，"
        "将进行首次全量抓取"
    )


# ==============================
# 建立旧数据索引
# ==============================

old_ids = set()

old_douban_ids = set()


for movie in old_movies:

    movie_id = movie.get("id")

    if movie_id:

        old_ids.add(
            str(movie_id)
        )


    douban_id = movie.get(
        "douban_id"
    )

    if douban_id:

        old_douban_ids.add(
            str(douban_id)
        )


# ==============================
# 判断首次抓取
# ==============================

first_run = len(old_movies) == 0


# ==============================
# 首次抓取
# ==============================

if first_run:

    print()
    print("==============================")
    print("首次抓取模式")
    print(
        f"最多抓取最新 "
        f"{INITIAL_PAGES} 页"
    )
    print("==============================")


    movies_dict = {}


    for page in range(
        1,
        INITIAL_PAGES + 1
    ):

        try:

            data = get_page(page)

        except Exception as e:

            print(
                f"第 {page} 页获取失败："
                f"{e}"
            )

            break


        movie_list = data.get(
            "list",
            []
        )


        print(
            f"第 {page} 页获取到 "
            f"{len(movie_list)} 部影视"
        )


        if not movie_list:

            print(
                "没有更多数据，"
                "停止抓取"
            )

            break


        for movie in movie_list:

            item = make_movie_item(
                movie
            )

            movie_id = str(
                item.get("id")
            )

            movies_dict[
                movie_id
            ] = item


        time.sleep(
            REQUEST_DELAY
        )


    # API 最新数据在前
    result = list(
        movies_dict.values()
    )


    # 按更新时间排序
    result.sort(
        key=lambda x:
        x.get("update_time") or "",
        reverse=True
    )


    # 限制最大数量
    result = result[
        :MAX_MOVIES
    ]


    # 保存
    os.makedirs(
        "data",
        exist_ok=True
    )


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


    # 保存进度
    progress = {

        "initialized": True,

        "max_movies":
            MAX_MOVIES,

        "initial_pages":
            INITIAL_PAGES

    }


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


    print()
    print("==============================")
    print("首次抓取完成")
    print(
        f"当前影视库："
        f"{len(result)} 部"
    )
    print("==============================")


    exit()


# ==============================
# 后续增量检测
# ==============================

print()
print("==============================")
print("增量更新模式")
print("==============================")


new_movies = []

found_old_data = False


# 先从第一页开始检查
page = 1


while not found_old_data:

    try:

        data = get_page(page)

    except Exception as e:

        print(
            f"第 {page} 页获取失败："
            f"{e}"
        )

        break


    movie_list = data.get(
        "list",
        []
    )


    print(
        f"第 {page} 页获取到 "
        f"{len(movie_list)} 部影视"
    )


    if not movie_list:

        print(
            "没有更多数据"
        )

        break


    for movie in movie_list:

        movie_id = str(
            movie.get("vod_id")
        )


        douban_id = movie.get(
            "vod_douban_id"
        )


        # --------------------------
        # 判断是否已经存在
        # 优先使用豆瓣 ID
        # --------------------------

        exists = False


        if douban_id:

            if (
                str(douban_id)
                in old_douban_ids
            ):

                exists = True


        # 如果没有豆瓣 ID
        # 再使用 vod_id
        if not exists:

            if (
                movie_id
                in old_ids
            ):

                exists = True


        # --------------------------
        # 找到旧数据
        # --------------------------

        if exists:

            found_old_data = True

            print(
                "发现已有影视数据，"
                "停止继续抓取"
            )

            break


        # --------------------------
        # 新影片
        # --------------------------

        item = make_movie_item(
            movie
        )

        new_movies.append(
            item
        )


    if found_old_data:

        break


    page += 1


    time.sleep(
        REQUEST_DELAY
    )


# ==============================
# 没有新增
# ==============================

if len(new_movies) == 0:

    print()
    print("==============================")
    print("没有发现新增影视")
    print("影视库无需更新")
    print("==============================")

    exit()


# ==============================
# 合并新增影片
# ==============================

print()
print(
    f"发现新增影视："
    f"{len(new_movies)} 部"
)


# 去重
new_dict = {}

for movie in new_movies:

    movie_id = str(
        movie.get("id")
    )

    new_dict[
        movie_id
    ] = movie


# 保留旧库
result = new_movies + old_movies


# ==============================
# 去重
# ==============================

unique_movies = []

seen_ids = set()

seen_douban_ids = set()


for movie in result:

    movie_id = movie.get(
        "id"
    )

    douban_id = movie.get(
        "douban_id"
    )


    # 豆瓣 ID 优先去重
    if douban_id:

        if (
            str(douban_id)
            in seen_douban_ids
        ):

            continue


        seen_douban_ids.add(
            str(douban_id)
        )


    # vod_id 去重
    if movie_id:

        if (
            str(movie_id)
            in seen_ids
        ):

            continue


        seen_ids.add(
            str(movie_id)
        )


    unique_movies.append(
        movie
    )


# ==============================
# 保持固定容量
# ==============================

before_count = len(
    unique_movies
)


result = unique_movies[
    :MAX_MOVIES
]


removed_count = (
    before_count
    - len(result)
)


# ==============================
# 保存
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


# 更新进度文件
progress = {

    "initialized": True,

    "max_movies":
        MAX_MOVIES,

    "initial_pages":
        INITIAL_PAGES,

    "last_update_new_movies":
        len(new_movies)

}


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

print()
print("==============================")
print("影视库更新完成")
print("==============================")

print(
    f"新增影视："
    f"{len(new_movies)} 部"
)

print(
    f"删除旧影视："
    f"{removed_count} 部"
)

print(
    f"当前影视库："
    f"{len(result)} 部"
)

print("==============================")
