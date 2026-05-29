"""清理测试时误写入品牌库的测试品牌"""
import sys, json, os

# 设置项目根目录
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from product_cleaner.brands.database import BRAND_DATABASE_V6, rebuild_indexes, DYNAMIC_BRANDS_FILE

test_brands = [
    '不亦乐乎', '丽姬娅', '密语仙白', '沙巴哇菠萝蜜干果',
    '温佩兹', '美丽雅晶彩保鲜盒', '蓝莓尊尼', '野生旺旺', '美丽雅'
]

# 从内存中删除
for name in test_brands:
    if name in BRAND_DATABASE_V6:
        del BRAND_DATABASE_V6[name]
        print(f'内存删除: {name}')

rebuild_indexes()
print('索引重建完成')

# 从持久化文件删除
if DYNAMIC_BRANDS_FILE.exists():
    data = json.load(open(DYNAMIC_BRANDS_FILE))
    for name in test_brands:
        if name in data:
            del data[name]
            print(f'文件删除: {name}')
    tmp = str(DYNAMIC_BRANDS_FILE) + '.tmp'
    json.dump(data, open(tmp, 'w'), ensure_ascii=False, indent=2)
    os.replace(tmp, str(DYNAMIC_BRANDS_FILE))

print(f'\n品牌库当前: {len(BRAND_DATABASE_V6)} 个品牌')
