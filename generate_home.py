import json
import os


# ==============================
# 文件路径
# ==============================

input_file = "data/movies.json"
output_file = "data/home.json"


# ==============================
# 读取影视库
# ==============================

with open(input_file, "r", encoding="utf-8") as f:
    movies = json.load(f)


print(f"影视库总数：{len(movies)}")


# ==============================
# 按更新时间倒序排列
# ==============================

movies.sort(
    key=lambda x: x.get("update_time") or "",
    reverse=True
)


# ==============================
# 取最新 50 部
# ==============================

latest_movies = movies[:50]


# ==============================
# 生成轻量首页数据
# ==============================

home_data = []

for movie in latest_movies:

    item = {
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

    home_data.append(item)


# ==============================
# 保存
# ==============================

os.makedirs("data", exist_ok=True)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(
        home_data,
        f,
        ensure_ascii=False,
        indent=2
    )


print("==============================")
print(f"首页影片数量：{len(home_data)}")
print(f"成功生成：{output_file}")
print("==============================")
