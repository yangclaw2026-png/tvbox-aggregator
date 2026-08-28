import json
import os
import time
import requests


# ==============================
# 配置
# ==============================

# 每个播放源首次最多抓多少页
INITIAL_PAGES = 20

# 主影视库
movies_file = "data/movies.json"

# 播放源抓取进度
progress_file = "data/play_sources_progress.json"

# 每次请求间隔
REQUEST_DELAY = 0.5


# ==============================
# 读取源配置
# ==============================

with open("sources.json", "r", encoding="utf-8") as f:
    config = json.load(f)


# 排除豆瓣资源
sources = [
    source
    for source in config["cms_sources"]
    if source.get("name") != "豆瓣资源"
]


print(f"需要处理 {len(sources)} 个播放源")


# ==============================
# 读取主影视库
# ==============================

if not os.path.exists(movies_file):

    print("找不到 movies.json")

    exit()


with open(
    movies_file,
    "r",
    encoding="utf-8"
) as f:

    movies = json.load(f)


print(f"读取到主影视库：{len(movies)} 部影视")


# ==============================
# 建立匹配索引
# ==============================

# 豆瓣 ID 索引
douban_index = {}

# 名称 + 年份索引
name_year_index = {}

# 纯名称索引
name_index = {}

# 重名影片
duplicate_names = set()


for movie in movies:


    # --------------------------
    # 豆瓣 ID
    # --------------------------

    douban_id = movie.get(
        "douban_id"
    )

    if douban_id:

        douban_index[
            str(douban_id)
        ] = movie


    # --------------------------
    # 名称
    # --------------------------

    name = (
        movie.get("name")
        or ""
    ).strip()


    # --------------------------
    # 年份
    # --------------------------

    year = str(
        movie.get("year")
        or ""
    ).strip()


    if not name:

        continue


    # --------------------------
    # 名称 + 年份索引
    # --------------------------

    key = f"{name}|{year}"

    name_year_index[key] = movie


    # --------------------------
    # 纯名称索引
    #
    # 如果存在重名，
    # 后面删除该名称，
    # 避免错误匹配
    # --------------------------

    if name in name_index:

        duplicate_names.add(
            name
        )

    else:

        name_index[name] = movie


# ==============================
# 删除重名影片
# ==============================

for name in duplicate_names:

    name_index.pop(
        name,
        None
    )


print(
    f"建立豆瓣 ID 索引："
    f"{len(douban_index)} 条"
)

print(
    f"建立名称年份索引："
    f"{len(name_year_index)} 条"
)

print(
    f"建立纯名称索引："
    f"{len(name_index)} 条"
)

print(
    f"发现重名影片："
    f"{len(duplicate_names)} 个"
)


# ==============================
# 读取进度
# ==============================

if os.path.exists(progress_file):

    with open(
        progress_file,
        "r",
        encoding="utf-8"
    ) as f:

        progress = json.load(f)

else:

    progress = {
        "sources": {}
    }


if "sources" not in progress:

    progress = {
        "sources": {}
    }


# ==============================
# 保存进度
# ==============================

def save_progress():

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
# 保存影视库
# ==============================

def save_movies():

    with open(
        movies_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            movies,
            f,
            ensure_ascii=False,
            indent=2
        )


# ==============================
# 获取页面
# ==============================

def get_page(base_url, page):

    separator = (
        "&"
        if "?" in base_url
        else "?"
    )

    url = (
        f"{base_url}"
        f"{separator}pg={page}"
    )

    response = requests.get(
        url,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ==============================
# 处理播放数据
# ==============================

def process_movies(
    source_name,
    movie_list
):

    matched_count = 0
    unmatched_count = 0
    new_play_sources = 0


    for source_movie in movie_list:


        # --------------------------
        # 优先匹配豆瓣 ID
        # --------------------------

        douban_id = source_movie.get(
            "vod_douban_id"
        )

        matched_movie = None


        if douban_id:

            matched_movie = douban_index.get(
                str(douban_id)
            )


        # --------------------------
        # 获取播放源影片名称
        # --------------------------

        name = (
            source_movie.get(
                "vod_name"
            )
            or ""
        ).strip()


        # --------------------------
        # 名称 + 年份匹配
        #
        # 如果播放源提供年份，
        # 优先精确匹配
        # --------------------------

        if not matched_movie:

            year = str(
                source_movie.get(
                    "vod_year"
                )
                or ""
            ).strip()


            if year:

                key = f"{name}|{year}"

                matched_movie = (
                    name_year_index.get(
                        key
                    )
                )


        # --------------------------
        # 纯名称匹配
        #
        # 播放源没有年份时使用
        # 只匹配唯一名称
        # --------------------------

        if not matched_movie and name:

            matched_movie = (
                name_index.get(
                    name
                )
            )


        # --------------------------
        # 匹配失败
        # --------------------------

        if not matched_movie:

            unmatched_count += 1

            continue


        # --------------------------
        # 匹配成功
        # --------------------------

        matched_count += 1


        # 初始化播放源
        if "play_sources" not in matched_movie:

            matched_movie[
                "play_sources"
            ] = []


        play_sources = matched_movie[
            "play_sources"
        ]


        play_source = {

            "source":
                source_name,

            "source_id":
                source_movie.get(
                    "vod_id"
                ),

            "play_from":
                source_movie.get(
                    "vod_play_from"
                ),

            "play_url":
                source_movie.get(
                    "vod_play_url"
                ),

            "remarks":
                source_movie.get(
                    "vod_remarks"
                )

        }


        # --------------------------
        # 防止重复
        # --------------------------

        exists = False


        for old_source in play_sources:

            if (

                old_source.get("source")
                == source_name

                and

                str(
                    old_source.get(
                        "source_id"
                    )
                )

                ==

                str(
                    source_movie.get(
                        "vod_id"
                    )
                )

            ):

                exists = True

                break


        # --------------------------
        # 添加播放源
        # --------------------------

        if not exists:

            play_sources.append(
                play_source
            )

            new_play_sources += 1


    return (
        matched_count,
        unmatched_count,
        new_play_sources
    )


# ==============================
# 总统计
# ==============================

total_matched = 0
total_unmatched = 0
total_new_play_sources = 0


# ==============================
# 遍历播放源
# ==============================

for source in sources:


    source_name = source.get("name")


    base_url = (
        source.get("detail_api")
        or source.get("api")
    )


    if not base_url:

        print(
            f"\n跳过 {source_name}："
            "没有 API 地址"
        )

        continue


    print()
    print("================================")
    print(f"开始处理：{source_name}")
    print("================================")


    # 当前源进度
    source_progress = progress[
        "sources"
    ].get(
        source_name,
        {}
    )


    initialized = source_progress.get(
        "initialized",
        False
    )


    # ==============================
    # 请求第一页
    # ==============================

    try:

        print("正在检查第 1 页...")

        first_data = get_page(
            base_url,
            1
        )

    except Exception as e:

        print(
            f"{source_name} 请求失败：{e}"
        )

        continue


    first_movies = first_data.get(
        "list",
        []
    )


    if not first_movies:

        print(
            f"{source_name} 没有数据"
        )

        continue


    current_total_pages = int(
        first_data.get(
            "pagecount",
            0
        )
    )


    print(
        f"当前总页数："
        f"{current_total_pages}"
    )


    # ==============================
    # 首次抓取
    # ==============================

    if not initialized:


        end_page = min(
            INITIAL_PAGES,
            current_total_pages
        )


        print(
            f"首次抓取最新 "
            f"1 - {end_page} 页"
        )


        source_matched = 0
        source_unmatched = 0
        source_new_play_sources = 0


        for page in range(
            1,
            end_page + 1
        ):


            try:

                if page == 1:

                    data = first_data

                else:

                    data = get_page(
                        base_url,
                        page
                    )


            except Exception as e:

                print(
                    f"第 {page} 页失败：{e}"
                )

                break


            movie_list = data.get(
                "list",
                []
            )


            print(
                f"[{source_name}] "
                f"第 {page} 页："
                f"{len(movie_list)} 条"
            )


            if not movie_list:

                break


            (
                matched_count,
                unmatched_count,
                new_play_sources
            ) = process_movies(
                source_name,
                movie_list
            )


            source_matched += matched_count
            source_unmatched += unmatched_count
            source_new_play_sources += new_play_sources


            total_matched += matched_count
            total_unmatched += unmatched_count
            total_new_play_sources += new_play_sources


            time.sleep(
                REQUEST_DELAY
            )


        # 保存第一页 ID
        latest_ids = [

            str(
                movie.get(
                    "vod_id"
                )
            )

            for movie in first_movies

        ]


        source_progress = {

            "initialized": True,

            "latest_ids":
                latest_ids,

            "total_pages":
                current_total_pages

        }


        progress[
            "sources"
        ][
            source_name
        ] = source_progress


        print(
            f"{source_name} 首次抓取完成"
        )

        print(
            f"匹配成功："
            f"{source_matched}"
        )

        print(
            f"未匹配："
            f"{source_unmatched}"
        )

        print(
            f"新增播放源："
            f"{source_new_play_sources}"
        )


        save_movies()
        save_progress()


    # ==============================
    # 后续增量更新
    # ==============================

    else:


        print(
            "开始检查新增数据..."
        )


        old_latest_ids = set(
            source_progress.get(
                "latest_ids",
                []
            )
        )


        new_movies = []

        found_old_movie = False

        page = 1


        # 最多检查当前总页数
        while (

            page <= current_total_pages

            and

            not found_old_movie

        ):


            try:

                if page == 1:

                    data = first_data

                else:

                    data = get_page(
                        base_url,
                        page
                    )


            except Exception as e:

                print(
                    f"第 {page} 页失败：{e}"
                )

                break


            movie_list = data.get(
                "list",
                []
            )


            if not movie_list:

                break


            print(
                f"检查第 {page} 页："
                f"{len(movie_list)} 条"
            )


            for movie in movie_list:


                movie_id = str(
                    movie.get(
                        "vod_id"
                    )
                )


                # ----------------------
                # 碰到旧数据
                # ----------------------

                if movie_id in old_latest_ids:

                    found_old_movie = True

                    print(
                        "发现旧数据，"
                        "停止检查"
                    )

                    break


                # 新数据
                new_movies.append(
                    movie
                )


            page += 1


            time.sleep(
                REQUEST_DELAY
            )


        # ==============================
        # 没有新增
        # ==============================

        if not new_movies:


            print(
                f"{source_name}："
                "没有新增数据"
            )


        # ==============================
        # 处理新增
        # ==============================

        else:


            print(
                f"{source_name}："
                f"发现 {len(new_movies)} 条新增"
            )


            (
                matched_count,
                unmatched_count,
                new_play_sources
            ) = process_movies(
                source_name,
                new_movies
            )


            total_matched += matched_count
            total_unmatched += unmatched_count
            total_new_play_sources += new_play_sources


            print(
                f"匹配成功："
                f"{matched_count}"
            )

            print(
                f"未匹配："
                f"{unmatched_count}"
            )

            print(
                f"新增播放源："
                f"{new_play_sources}"
            )


        # ==============================
        # 更新最新第一页 ID
        # ==============================

        source_progress[
            "latest_ids"
        ] = [

            str(
                movie.get(
                    "vod_id"
                )
            )

            for movie in first_movies

        ]


        source_progress[
            "total_pages"
        ] = current_total_pages


        progress[
            "sources"
        ][
            source_name
        ] = source_progress


        save_movies()
        save_progress()


# ==============================
# 最终保存
# ==============================

save_movies()

save_progress()


# ==============================
# 最终统计
# ==============================

print()
print("================================")
print("全部播放源处理完成")
print("================================")

print(
    f"匹配成功总数："
    f"{total_matched}"
)

print(
    f"未匹配总数："
    f"{total_unmatched}"
)

print(
    f"新增播放源总数："
    f"{total_new_play_sources}"
)

print("================================")
