import json
import os
import time
import requests


# ==============================
# 配置
# ==============================

# 每次运行，每个播放源最多检查多少页
PAGES_PER_RUN = 20

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


for movie in movies:

    douban_id = movie.get("douban_id")

    if douban_id:

        douban_index[
            str(douban_id)
        ] = movie


    name = (
        movie.get("name")
        or ""
    ).strip()


    year = str(
        movie.get("year")
        or ""
    ).strip()


    if name:

        key = f"{name}|{year}"

        name_year_index[key] = movie


print(
    f"建立豆瓣 ID 索引："
    f"{len(douban_index)} 条"
)

print(
    f"建立名称年份索引："
    f"{len(name_year_index)} 条"
)


# ==============================
# 读取抓取进度
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
        # 先匹配豆瓣 ID
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
        # 豆瓣 ID 匹配不到
        # 再使用 名称 + 年份
        # --------------------------

        if not matched_movie:

            name = (
                source_movie.get(
                    "vod_name"
                )
                or ""
            ).strip()


            year = str(
                source_movie.get(
                    "vod_year"
                )
                or ""
            ).strip()


            key = f"{name}|{year}"

            matched_movie = (
                name_year_index.get(key)
            )


        # --------------------------
        # 仍然匹配不到
        # --------------------------

        if not matched_movie:

            unmatched_count += 1

            continue


        # --------------------------
        # 匹配成功
        # --------------------------

        matched_count += 1


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
        # 检查是否已经存在
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
        # 添加新播放源
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
# 统计
# ==============================

total_matched = 0
total_unmatched = 0
total_new_play_sources = 0


# ==============================
# 遍历所有播放源
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


    # ==============================
    # 获取当前源进度
    # ==============================

    source_progress = progress[
        "sources"
    ].get(
        source_name,
        {}
    )


    last_page = source_progress.get(
        "last_page",
        0
    )


    total_pages = source_progress.get(
        "total_pages",
        0
    )


    completed = source_progress.get(
        "completed",
        False
    )


    # ==============================
    # 获取第一页
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


    current_total_pages = int(
        first_data.get(
            "pagecount",
            0
        )
    )


    if not first_movies:

        print(
            f"{source_name} 没有数据"
        )

        continue


    print(
        f"当前总页数："
        f"{current_total_pages}"
    )


    # ==============================
    # 首次抓取
    # ==============================

    if total_pages == 0:


        total_pages = current_total_pages


        start_page = 1


        end_page = min(
            PAGES_PER_RUN,
            total_pages
        )


        print(
            f"首次抓取："
            f"{start_page} - {end_page}"
        )


        source_matched = 0
        source_unmatched = 0
        source_new_play_sources = 0


        for page in range(
            start_page,
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


            last_page = page


            time.sleep(
                REQUEST_DELAY
            )


        # ==============================
        # 保存最新 ID
        # ==============================

        latest_ids = [

            str(
                movie.get(
                    "vod_id"
                )
            )

            for movie in first_movies

        ]


        source_progress = {

            "last_page":
                last_page,

            "total_pages":
                total_pages,

            "completed":
                last_page >= total_pages,

            "latest_ids":
                latest_ids

        }


        progress[
            "sources"
        ][
            source_name
        ] = source_progress


        save_movies()
        save_progress()


    # ==============================
    # 历史抓取未完成
    # ==============================

    elif not completed:


        # 如果源总页数发生变化
        total_pages = max(
            total_pages,
            current_total_pages
        )


        start_page = last_page + 1


        end_page = min(
            start_page + PAGES_PER_RUN - 1,
            total_pages
        )


        print(
            f"继续历史抓取："
            f"{start_page} - {end_page}"
        )


        source_matched = 0
        source_unmatched = 0
        source_new_play_sources = 0


        for page in range(
            start_page,
            end_page + 1
        ):


            try:

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


            last_page = page


            time.sleep(
                REQUEST_DELAY
            )


        latest_ids = [

            str(
                movie.get(
                    "vod_id"
                )
            )

            for movie in first_movies

        ]


        source_progress.update({

            "last_page":
                last_page,

            "total_pages":
                total_pages,

            "completed":
                last_page >= total_pages,

            "latest_ids":
                latest_ids

        })


        progress[
            "sources"
        ][
            source_name
        ] = source_progress


        save_movies()
        save_progress()


    # ==============================
    # 历史数据已完成
    # 只检查新增
    # ==============================

    else:


        print(
            "历史数据已完成，"
            "开始检查是否有新增..."
        )


        old_latest_ids = (
            source_progress.get(
                "latest_ids",
                []
            )
        )


        new_movies = []


        for movie in first_movies:


            movie_id = str(
                movie.get(
                    "vod_id"
                )
            )


            # 已经遇到旧数据
            # 后面的全部忽略
            if movie_id in old_latest_ids:

                break


            new_movies.append(
                movie
            )


        # ==============================
        # 没有新增
        # ==============================

        if not new_movies:


            print(
                f"{source_name}："
                "没有新增数据，跳过"
            )


        # ==============================
        # 有新增
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


        # 更新第一页最新 ID
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
