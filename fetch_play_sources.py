import json
import os
import time
import requests


# ==============================
# 配置
# ==============================

# 每次运行，每个源抓多少页
PAGES_PER_RUN = 500

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


with open(movies_file, "r", encoding="utf-8") as f:
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
        douban_index[str(douban_id)] = movie


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


    print("\n================================")
    print(f"开始处理：{source_name}")
    print("================================")


    # ==============================
    # 当前源进度
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


    if completed:

        print(
            f"{source_name} 已完成，跳过"
        )

        continue


    # ==============================
    # 获取第一页和总页数
    # ==============================

    if total_pages == 0:

        print("正在获取第一页和总页数...")


        separator = (
            "&"
            if "?" in base_url
            else "?"
        )


        first_url = (
            f"{base_url}"
            f"{separator}pg=1"
        )


        try:

            response = requests.get(
                first_url,
                timeout=30
            )

            response.raise_for_status()

            first_data = response.json()


            total_pages = int(
                first_data.get(
                    "pagecount",
                    0
                )
            )


            print(
                f"总页数：{total_pages}"
            )


            if total_pages <= 0:

                print(
                    "没有获取到有效总页数，跳过"
                )

                continue


            source_progress[
                "total_pages"
            ] = total_pages


        except Exception as e:

            print(
                f"获取第一页失败：{e}"
            )

            continue


    # ==============================
    # 本次抓取范围
    # ==============================

    start_page = last_page + 1


    end_page = min(
        start_page + PAGES_PER_RUN - 1,
        total_pages
    )


    print(
        f"本次抓取："
        f"{start_page} - {end_page}"
    )


    source_matched = 0
    source_unmatched = 0
    source_new_play_sources = 0


    # ==============================
    # 分页抓取
    # ==============================

    for page in range(
        start_page,
        end_page + 1
    ):

        separator = (
            "&"
            if "?" in base_url
            else "?"
        )


        url = (
            f"{base_url}"
            f"{separator}pg={page}"
        )


        print(
            f"\n[{source_name}] "
            f"正在获取第 {page} 页"
        )


        try:

            response = requests.get(
                url,
                timeout=30
            )

            response.raise_for_status()

            data = response.json()


        except Exception as e:

            print(
                f"第 {page} 页请求失败：{e}"
            )

            break


        movie_list = data.get(
            "list",
            []
        )


        print(
            f"获取到 "
            f"{len(movie_list)} 条数据"
        )


        if not movie_list:

            print(
                "没有更多数据，"
                "停止当前源"
            )

            end_page = page - 1

            break


        # ==============================
        # 处理当前页
        # ==============================

        for source_movie in movie_list:

            # --------------------------------
            # 尝试匹配豆瓣 ID
            # --------------------------------

            douban_id = source_movie.get(
                "vod_douban_id"
            )


            matched_movie = None


            if douban_id:

                matched_movie = douban_index.get(
                    str(douban_id)
                )


            # --------------------------------
            # 如果没有豆瓣 ID 匹配
            # 使用 名称 + 年份
            # --------------------------------

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


            # --------------------------------
            # 没有匹配到
            # --------------------------------

            if not matched_movie:

                source_unmatched += 1
                total_unmatched += 1

                continue


            # --------------------------------
            # 匹配成功
            # --------------------------------

            source_matched += 1
            total_matched += 1


            # 初始化 play_sources
            if "play_sources" not in matched_movie:

                matched_movie[
                    "play_sources"
                ] = []


            play_sources = matched_movie[
                "play_sources"
            ]


            # 当前播放源
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


            # ==============================
            # 防止重复添加
            # ==============================

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


            if not exists:

                play_sources.append(
                    play_source
                )


                source_new_play_sources += 1

                total_new_play_sources += 1


        # ==============================
        # 每页保存
        # ==============================

        source_progress[
            "last_page"
        ] = page


        source_progress[
            "total_pages"
        ] = total_pages


        source_progress[
            "completed"
        ] = (
            page >= total_pages
        )


        progress[
            "sources"
        ][
            source_name
        ] = source_progress


        # 保存影视库
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


        # 保存进度
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


        # 请求间隔
        time.sleep(
            REQUEST_DELAY
        )


    # ==============================
    # 当前源统计
    # ==============================

    print("\n--------------------------------")

    print(
        f"{source_name} 匹配成功："
        f"{source_matched}"
    )


    print(
        f"{source_name} 未匹配："
        f"{source_unmatched}"
    )


    print(
        f"{source_name} 新增播放源："
        f"{source_new_play_sources}"
    )


    print("--------------------------------")


# ==============================
# 最终保存
# ==============================

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
# 最终统计
# ==============================

print("\n================================")
print("全部播放源处理完成")
print("================================")

print(
    f"匹配成功总数：{total_matched}"
)

print(
    f"未匹配总数：{total_unmatched}"
)

print(
    f"新增播放源总数："
    f"{total_new_play_sources}"
)

print("================================")
