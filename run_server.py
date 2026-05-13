#!/usr/bin/env python3
"""
商品数据清理系统 V4 - 启动脚本

使用方法:
    python run_server.py

然后访问:
    http://localhost:5001
"""

import sys
import os

from flask_cors import CORS  # <--- 新增这行

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from product_cleaner.web.app import app

CORS(app, resources={r"/*": {"origins": "*"}})


@app.route('/global/health', methods=['GET', 'OPTIONS'])
def health_check():
    return {"status": "ok"}, 200

@app.route('/global/event', methods=['GET', 'POST', 'OPTIONS'])
def event_check():
    return {"status": "success"}, 200


if __name__ == '__main__':
    print("\n" + "="*70)
    print("商品数据清理系统 V4")
    print("="*70)
    print("\n核心改进:")
    print("  ✓ 品牌聚类（去规格，包含关系不聚类）")
    print("  ✓ 品牌一致性检测（商品名不含品牌 → 错误）")
    print("  ✓ 标准化规则一次性确认，批量应用")
    print("  ✓ 三级联动分类下拉 + 搜索 + 营销标记")
    print("  ✓ 全量数据预览（含无需处理数据）")
    print("  ✓ AI结果置信度分级确认")
    print("="*70)
    print("\n主页: http://localhost:5001")
    print("复核: http://localhost:5001/review")
    print("="*70 + "\n")

    app.run(host='127.0.0.1', port=5001, debug=True, threaded=True, use_reloader=False)
