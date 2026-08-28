import json
import os
import shutil


# ==============================
# 配置
# ==============================

MOVIES_FILE = "data/movies.json"
CATEGORIES_FILE = "categories.json"
OUTPUT_DIR = "data/categories"

PAGE_SIZE = 50

# 每次重新生成前清理旧分类数据
if os.path.exists(OUTPUT_DIR):
    shutil.rmtree(OUTPUT_DIR)

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==============================
# 读取影视库
# ==============================

with open(MOVIES_FILE, "r", encoding="utf-8") as f:
    movies = json.load(f)


# 按更新时间倒序
movies.sort(
    key=lambda x: x.get("update_time") or "",
    reverse=True
)


print(f"影视库总数：{len(movies)}")


# ==============================
# 读取分类配置
# ==============================

with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)


categories = config["categories"]


# ==============================
# 生成轻量影片数据
# ==============================

def make_light_item(movie):

    return {
        "id": movie.get("id"),
        "name": movie.get("name"),
        "type": movie.get("type"),
        "category": movie.get("category"),
        "year": movie.get("year"),
        "area": movie.get("area"),
        "poster": movie.get("poster"),
        "score": movie.get("score"),
        "remarks": movie.get("remarks"),
        "update_time": movie.get("update_time")
    }


# ==============================
# 保存分页
# ==============================

def save_pages(movie_list, folder):

    os.makedirs(folder, exist_ok=True)

    page_count = (
        len(movie_list) + PAGE_SIZE - 1
    ) // PAGE_SIZE

    for page in range(page_count):

        start = page * PAGE_SIZE
        end = start + PAGE_SIZE

        page_movies = movie_list[start:end]

        output_file = os.path.join(
            folder,
            f"{page + 1}.json"
        )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                [make_light_item(movie) for movie in page_movies],
                f,
                ensure_ascii=False,
                indent=2
            )

    return page_count


# ==============================
# 生成所有分类
# ==============================

for category in categories:

    category_id = category["id"]
    category_name = category["name"]
    types = category["types"]

    print()
    print("==============================")
    print(f"正在生成：{category_name}")
    print("==============================")


    # --------------------------
    # 大分类全部
    # --------------------------

    all_movies = [

        movie

        for movie in movies

        if movie.get("type") in types

    ]


    all_folder = os.path.join(
        OUTPUT_DIR,
        category_id,
        "all"
    )


    all_pages = save_pages(
        all_movies,
        all_folder
    )


    print(
        f"全部：{len(all_movies)} 部，"
        f"{all_pages} 页"
    )


    # --------------------------
    # 子分类
    # --------------------------

    for type_name in types:

        type_movies = [

            movie

            for movie in movies

            if movie.get("type") == type_name

        ]


        type_folder = os.path.join(
            OUTPUT_DIR,
            category_id,
            type_name
        )


        page_count = save_pages(
            type_movies,
            type_folder
        )


        print(
            f"{type_name}："
            f"{len(type_movies)} 部，"
            f"{page_count} 页"
        )


print()
print("==============================")
print("分类数据生成完成")
print("==============================")
