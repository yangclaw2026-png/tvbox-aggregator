import json
import requests


# 读取源配置
with open("sources.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# 找到主源：豆瓣资源
primary_source = next(
    source
    for source in config["cms_sources"]
    if source.get("primary") is True
)

url = primary_source["detail_api"]

print(f"正在请求：{primary_source['name']}")
print(url)

# 请求 API
response = requests.get(
    url,
    timeout=30
)

response.raise_for_status()

data = response.json()

print("\n请求成功！")
print(f"返回 code: {data.get('code')}")
print(f"总数据量: {data.get('total')}")
print(f"当前页: {data.get('page')}")

movies = data.get("list", [])

print(f"\n本页影片数量: {len(movies)}")

# 打印第一部影片的所有字段
if movies:
    movie = movies[0]

    print("\n========== 第一部影片 ==========")

    for key, value in movie.items():
        print(f"{key}: {value}")

else:
    print("没有获取到影片数据。")
