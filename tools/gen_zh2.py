# 生成海外免 Key 接口清单（输出 FREE_APIS.md）。原清单已并入 docs/API_SOURCES.md 第 1 节，重新生成后需手动替换该节。
import json
from collections import defaultdict

with open(r"C:\Users\Administrator\AppData\Local\Temp\apis.json", encoding="utf-8") as f:
    data = json.load(f)

entries = data["entries"]
free = [e for e in entries if e.get("auth") in ("No", None, "") and e.get("https")]

CAT_ZH = {
    "Animals": "动物", "Anime": "动漫", "Anti-Malware": "安全",
    "Art & Design": "艺术设计", "Books": "书籍", "Business": "商业",
    "Calendar": "日历", "Cloud Storage & File Sharing": "云存储",
    "Continuous Integration": "持续集成", "Cryptocurrency": "加密货币",
    "Currency Exchange": "汇率", "Data Validation": "数据验证",
    "Development": "开发工具", "Dictionaries": "词典", "Disasters": "灾害",
    "Documents & Productivity": "文档办公", "Education": "教育",
    "Environment": "环境", "Events": "活动", "Finance": "金融",
    "Food & Drink": "美食", "Fraud Prevention": "风控",
    "Games & Comics": "游戏漫画", "Geocoding": "地理编码",
    "Government": "政府公开", "Health": "健康", "Jobs": "招聘",
    "Machine Learning": "机器学习", "Music": "音乐", "News": "新闻",
    "Open Data": "开放数据", "Open Source Projects": "开源项目",
    "Patent": "专利", "Personality": "性格测试", "Photography": "摄影",
    "Science & Math": "科学数学", "Security": "网络安全", "Shopping": "购物",
    "Social": "社交", "Sports & Fitness": "体育", "Test Data": "测试数据",
    "Text Analysis": "文本分析", "Tracking": "物流追踪",
    "Transportation": "交通", "URL Shorteners": "短链接", "Vehicle": "车辆",
    "Video": "视频", "Weather": "天气", "Other": "其他",
}

by_cat = defaultdict(list)
for e in free:
    by_cat[e.get("category", "Other")].append(e)

lines = ["# 可移植免费 API 列表（免Key + HTTPS）", ""]
lines.append(f"> 来源：public-api-lists（共837个，筛选后 **{len(free)}** 个）")
lines.append("")

for cat_en in sorted(by_cat.keys(), key=lambda x: CAT_ZH.get(x, x)):
    items = by_cat[cat_en]
    cat_zh = CAT_ZH.get(cat_en, cat_en)
    lines.append(f"## {cat_zh}（{len(items)}个）")
    lines.append("")
    lines.append("| API名称 | 功能说明 | 地址 |")
    lines.append("|---------|---------|------|")
    for e in items:
        name = e["name"].replace("|", "\\|")
        desc = e.get("description", "").replace("|", "\\|")[:80]
        url = e["url"]
        lines.append(f"| {name} | {desc} | {url} |")
    lines.append("")

with open("FREE_APIS.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Written {len(free)} APIs")
