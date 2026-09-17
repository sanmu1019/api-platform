"""清理数据库测试污染：测试注册key、冒烟测试key、已删接口的孤儿统计。"""
import sqlite3

conn = sqlite3.connect("data/api_platform.sqlite3")

# 1. 删除测试注册用户和冒烟测试用户的 key
cur = conn.execute(
    "DELETE FROM api_keys WHERE name IN ('测试注册用户', '冒烟测试用户')"
)
print(f"删除 api_keys: {cur.rowcount} 条")

# 2. 删除已删接口 joke_random 的孤儿统计
cur = conn.execute("DELETE FROM api_stats WHERE api_name = 'joke_random'")
print(f"删除 joke_random api_stats: {cur.rowcount} 条")

# 3. 清理 api_stats 中已不存在的接口（apis 表里没有的）
cur = conn.execute("""
    DELETE FROM api_stats
    WHERE api_name NOT IN (SELECT name FROM apis)
""")
print(f"删除其他孤儿 api_stats: {cur.rowcount} 条")

conn.commit()

# 验证
print(f"\n清理后 api_keys: {conn.execute('SELECT COUNT(*) FROM api_keys').fetchone()[0]} 条")
print(f"清理后 api_stats: {conn.execute('SELECT COUNT(*) FROM api_stats').fetchone()[0]} 条")
print("剩余 api_keys 名称:")
for r in conn.execute("SELECT name, COUNT(*) as c FROM api_keys GROUP BY name ORDER BY name"):
    print(f"  {r['name']!r}: {r['c']}条")

conn.close()
print("\n完成")
