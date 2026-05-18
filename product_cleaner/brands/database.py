#!/usr/bin/env python3
"""
品牌数据库 V6

此文件包含所有品牌信息，可按以下方式扩展：
1. 添加新品牌：在 BRAND_DATABASE_V6 字典中添加新条目
2. 添加别名：在对应品牌的 'aliases' 列表中添加
3. 添加子品牌：在 'sub_brands' 字典中定义

品牌数据结构：
{
    '品牌名': {
        'aliases': ['别名1', '别名2', ...],  # 品牌别名列表
        'type': '品牌类型',  # 如：零食、饮料、乳品等
        'country': '国家代码',  # 如：CN, US, JP, DE等
        'sub_brands': {  # 可选，子品牌定义
            '子品牌名': ['子品牌别名1', '子品牌别名2', ...]
        }
    }
}
"""

import json
import os
import re
import threading
from pathlib import Path

# 动态品牌持久化文件路径
DYNAMIC_BRANDS_FILE = Path(__file__).parent / 'dynamic_brands.json'
DISMISSED_BRANDS_FILE = Path(__file__).parent / 'dismissed_brands.json'
def _corrected_products_path(group_id: str) -> Path:
    import logging
    _logger = logging.getLogger(__name__)
    if not group_id:
        _logger.warning("_corrected_products_path called with empty group_id")
    d = Path(__file__).parent.parent / 'corrections' / group_id
    d.mkdir(parents=True, exist_ok=True)
    return d / 'corrected_products.json'
CORRECTED_BRANDS_FILE = Path(__file__).parent.parent / 'corrections' / 'corrected_brands.json'
CORRECTED_CATEGORIES_FILE = Path(__file__).parent.parent / 'corrections' / 'corrected_categories.json'
RELATIONSHIPS_FILE = Path(__file__).parent / 'relationships.json'

BRAND_DATABASE_V6 = {
    '盒马': {'aliases': ['盒马', '盒马/盒马', 'HM', '盒马有机'], 'type': '自有品牌', 'country': 'CN'},
    '小象': {'aliases': ['小象'], 'type': '自有品牌', 'country': 'CN'},
    '农夫山泉': {'aliases': ['农夫山泉', 'NONGFU SPRING', '农夫'], 'type': '饮水', 'country': 'CN'},
    '乐事': {'aliases': ['乐事', "Lay's", "Lay's/乐事"], 'type': '零食', 'country': 'US'},
    '三得利': {'aliases': ['三得利', 'SUNTORY', 'Suntory', 'SUNTORY/三得利'], 'type': '饮料', 'country': 'JP'},
    '海底捞': {'aliases': ['海底捞'], 'type': '火锅', 'country': 'CN'},
    '花王': {'aliases': ['花王', 'KAO', '花王/KAO'], 'type': '日化', 'country': 'JP'},
    '可口可乐': {'aliases': ['可口可乐', 'Coca-Cola', 'Coca Cola', 'cocacola', '可乐'], 'type': '饮料', 'country': 'US'},
    '李锦记': {'aliases': ['李锦记'], 'type': '调味', 'country': 'CN'},
    '雀巢': {'aliases': ['雀巢', 'Nestle', 'Nestlé'], 'type': '食品', 'country': 'CH'},
    '金龙鱼': {'aliases': ['金龙鱼'], 'type': '粮油', 'country': 'CN'},
    '湾仔码头': {'aliases': ['湾仔码头'], 'type': '速冻', 'country': 'CN'},
    '卡士': {'aliases': ['卡士', 'CLASSYKISS'], 'type': '乳品', 'country': 'CN'},
    '明治': {'aliases': ['明治', 'Meiji', '明治/Meiji'], 'type': '食品', 'country': 'JP'},
    '伊利': {'aliases': ['伊利', 'Yili', '伊利集团', '伊利乳业'], 'type': '乳品', 'country': 'CN'},
    '光明': {'aliases': ['光明', 'Bright', '光明乳业', '光明集团'], 'type': '乳品', 'country': 'CN'},
    '蒙牛': {'aliases': ['蒙牛', 'Mengniu', '蒙牛集团', '蒙牛乳业'], 'type': '乳品', 'country': 'CN'},
    '帝皇鲜': {'aliases': ['帝皇鲜'], 'type': '生鲜', 'country': 'CN'},
    '禄稣': {'aliases': ['禄稣'], 'type': '食品', 'country': 'CN'},
    '煎司令': {'aliases': ['煎司令'], 'type': '食品', 'country': 'CN'},
    '奔富': {'aliases': ['奔富', 'Penfolds'], 'type': '酒类', 'country': 'AU'},
    '洽洽': {'aliases': ['洽洽'], 'type': '零食', 'country': 'CN'},
    '瑞士莲': {'aliases': ['瑞士莲', 'Lindt'], 'type': '巧克力', 'country': 'CH'},
    '安佳': {'aliases': ['安佳', 'Anchor', 'Anchor/安佳'], 'type': '乳品', 'country': 'NZ'},
    '百事': {'aliases': ['百事', 'Pepsi', '百事可乐'], 'type': '饮料', 'country': 'US'},
    '家乐': {'aliases': ['家乐', 'Knorr'], 'type': '调味', 'country': 'NL'},
    '哈根达斯': {'aliases': ['哈根达斯', 'Häagen-Dazs'], 'type': '冰淇淋', 'country': 'US'},
    '得宝': {'aliases': ['得宝', 'Tempo', 'Tempo/得宝'], 'type': '纸品', 'country': 'DE'},
    '麒麟': {'aliases': ['麒麟', 'Kirin','麒麟一番榨'], 'type': '饮料', 'country': 'JP'},
    '狮王': {'aliases': ['狮王', 'LION', 'LION/狮王'], 'type': '日化', 'country': 'JP'},
    '德亚': {'aliases': ['德亚', 'Weidendorf'], 'type': '乳品', 'country': 'DE'},
    '歌帝梵': {'aliases': ['歌帝梵', 'Godiva'], 'type': '巧克力', 'country': 'BE'},
    '维达': {'aliases': ['维达', 'Vinda'], 'type': '纸品', 'country': 'CN'},
    '八喜': {'aliases': ['八喜', 'Baxi'], 'type': '冰淇淋', 'country': 'CN'},
    '海天': {'aliases': ['海天'], 'type': '调味', 'country': 'CN'},
    '简爱': {'aliases': ['简爱'], 'type': '乳品', 'country': 'CN'},
    '加点滋味': {'aliases': ['加点滋味'], 'type': '调味', 'country': 'CN'},
    '乐天': {'aliases': ['乐天', 'Lotte'], 'type': '零食', 'country': 'KR'},
    '爷爷的农场': {'aliases': ['爷爷的农场'], 'type': '食品', 'country': 'FR'},
    '施华蔻': {'aliases': ['施华蔻', 'Schwarzkopf'], 'type': '美发', 'country': 'DE'},
    '欣和': {'aliases': ['欣和'], 'type': '调味', 'country': 'CN'},
    '新新精艺': {'aliases': ['新新精艺'], 'type': '食品', 'country': 'CN'},
    '丘比': {'aliases': ['丘比', 'Kewpie'], 'type': '调味', 'country': 'JP'},
    '西鲜记': {'aliases': ['西鲜记'], 'type': '生鲜', 'country': 'CN'},
    '思念': {'aliases': ['思念'], 'type': '速冻', 'country': 'CN'},
    '味全': {'aliases': ['味全'], 'type': '乳品', 'country': 'TW'},
    '大公鸡管家': {'aliases': ['大公鸡管家'], 'type': '日化', 'country': 'IT'},
    '安速': {'aliases': ['安速', 'ARS', 'ARS/安速'], 'type': '日化', 'country': 'JP'},
    '干露': {'aliases': ['干露', 'Concha y Toro'], 'type': '酒类', 'country': 'CL'},
    '奥利奥': {'aliases': ['奥利奥', 'Oreo'], 'type': '零食', 'country': 'US'},
    '费列罗': {'aliases': ['费列罗', 'Ferrero'], 'type': '巧克力', 'country': 'IT'},
    '匠酱好': {'aliases': ['匠酱好'], 'type': '调味', 'country': 'CN'},
    '锐澳': {'aliases': ['锐澳', 'RIO'], 'type': '酒类', 'country': 'CN'},
    '李良济': {'aliases': ['李良济'], 'type': '食品', 'country': 'CN'},
    '小林制药': {'aliases': ['小林制药'], 'type': '日化', 'country': 'JP'},
    '梦龙': {'aliases': ['梦龙', 'Magnum'], 'type': '冰淇淋', 'country': 'NL'},
    '好丽友': {'aliases': ['好丽友', 'Orion'], 'type': '零食', 'country': 'KR'},
    '茅台': {'aliases': ['茅台'], 'type': '酒类', 'country': 'CN'},
    '维他': {'aliases': ['维他', 'Vita'], 'type': '饮料', 'country': 'HK'},
    '永璞': {'aliases': ['永璞'], 'type': '咖啡', 'country': 'CN'},
    '和乐怡': {'aliases': ['和乐怡', 'Horoyoi'], 'type': '酒类', 'country': 'JP'},
    '久年': {'aliases': ['久年'], 'type': '食品', 'country': 'CN'},
    '认养一头牛': {'aliases': ['认养一头牛'], 'type': '乳品', 'country': 'CN'},
    '官栈': {'aliases': ['官栈'], 'type': '食品', 'country': 'CN'},
    '元气森林': {'aliases': ['元气森林'], 'type': '饮料', 'country': 'CN'},
    '星巴克': {'aliases': ['星巴克', 'Starbucks'], 'type': '咖啡', 'country': 'US'},
    '北海牧场': {'aliases': ['北海牧场'], 'type': '乳品', 'country': 'CN'},
    '卡乐比': {'aliases': ['卡乐比', 'Calbee', 'Calbee/卡乐比'], 'type': '零食', 'country': 'JP'},
    '展艺': {'aliases': ['展艺'], 'type': '烘焙', 'country': 'CN'},
    '苏泊尔': {'aliases': ['苏泊尔', 'Supor'], 'type': '厨具', 'country': 'CN'},
    '卫龙': {'aliases': ['卫龙'], 'type': '零食', 'country': 'CN'},
    '健达': {'aliases': ['健达', 'Kinder'], 'type': '巧克力', 'country': 'IT'},
    '曼秀雷敦': {'aliases': ['曼秀雷敦', 'Mentholatum'], 'type': '日化', 'country': 'JP'},
    '和润': {'aliases': ['和润'], 'type': '乳品', 'country': 'CN'},
    '朝日': {'aliases': ['朝日', 'ASAHI', 'ASAHI/朝日'], 'type': '啤酒', 'country': 'JP'},
    '乐纯': {'aliases': ['乐纯'], 'type': '乳品', 'country': 'CN'},
    '三只松鼠': {'aliases': ['三只松鼠', 'Three Squirrels'], 'type': '零食', 'country': 'CN'},
    '良品铺子': {'aliases': ['良品铺子', 'Bestore'], 'type': '零食', 'country': 'CN'},
    '金字': {'aliases': ['金字', '金字火腿'], 'type': '火腿', 'country': 'CN'},
    '统一': {'aliases': ['统一', 'Uni-President', '统一企业'], 'type': '食品', 'country': 'TW'},
    '康师傅': {'aliases': ['康师傅', 'Master Kong'], 'type': '食品', 'country': 'TW'},
    '华为': {'aliases': ['华为', 'HUAWEI', 'Huawei'], 'type': '电子', 'country': 'CN'},
    '苹果': {'aliases': ['苹果', 'Apple', 'APPLE'], 'type': '电子', 'country': 'US'},
    '小米': {'aliases': ['小米', 'Xiaomi', 'MI'], 'type': '电子', 'country': 'CN'},
    '三星': {'aliases': ['三星', 'Samsung', 'SAMSUNG'], 'type': '电子', 'country': 'KR'},
    '养乐多': {'aliases': ['养乐多', 'YAKULT'], 'type': '乳酸菌', 'country': 'JP'},
    '百味来': {'aliases': ['百味来', 'Barilla', 'Barilla/百味来'], 'type': '意面', 'country': 'IT'},
    
    # === 斜杠品牌补充（从数据中分析得出，覆盖 1600+ 误判商品）===
    '卡诗': {'aliases': ['卡诗', 'Kerastase', 'KERASTASE', 'KERASTASE/卡诗', 'Kérastase/卡诗', 'Kerastase/卡诗', '卡诗/Kerastase'], 'type': '美发', 'country': 'FR'},
    '巴黎水': {'aliases': ['巴黎水', 'Perrier', 'Perrier/巴黎水'], 'type': '饮水', 'country': 'FR'},
    '好奇': {'aliases': ['好奇', 'HUGGIES', 'HUGGIES/好奇'], 'type': '母婴', 'country': 'US'},
    '乐而雅': {'aliases': ['乐而雅', 'Laurier', 'LAURIER', 'Laurier/乐而雅', 'LAURIER/乐而雅'], 'type': '日化', 'country': 'JP'},
    '亚光': {'aliases': ['亚光', 'LOFTEX', 'LOFTEX/亚光'], 'type': '纸品', 'country': 'CN'},
    '总统': {'aliases': ['总统', 'PRESIDENT', 'PRESIDENT/总统'], 'type': '乳品', 'country': 'FR'},
    '惠百施': {'aliases': ['惠百施', 'EBISU', 'EBISU/惠百施'], 'type': '日化', 'country': 'JP'},
    '小皮': {'aliases': ['小皮', 'Little Freddie', 'little freddie', 'little freddie/小皮', 'Little Freddie/小皮'], 'type': '食品', 'country': 'GB'},
    '皇家美素佳儿': {'aliases': ['皇家美素佳儿', 'Friso', 'Friso PRESTIGE', 'FRISO PRESTIGE', 'FrisoPrestige', 'Friso PRESTIGE/皇家美素佳儿', 'FRISO PRESTIGE/皇家美素佳儿', 'FrisoPrestige/皇家美素佳儿', 'Friso/皇家美素佳儿'], 'type': '乳品', 'country': 'NL'},
    '好来': {'aliases': ['好来', 'DARLIE', 'DARLIE/好来'], 'type': '日化', 'country': 'CN'},
    '高洁丝': {'aliases': ['高洁丝', 'KOTEX', 'Kotex', 'Kotex/高洁丝', 'KOTEX/高洁丝'], 'type': '日化', 'country': 'US'},
    '爱他美': {'aliases': ['爱他美', 'Aptamil', 'aptamil', 'Aptamil/爱他美', 'aptamil/爱他美'], 'type': '乳品', 'country': 'DE'},
    '圣培露': {'aliases': ['圣培露', 'Sanpellegrino', 'S.Pellegrino', 'S.Pellegrino/圣培露', 'Sanpellegrino/圣培露'], 'type': '饮水', 'country': 'IT'},
    '高露洁': {'aliases': ['高露洁', 'Colgate', 'Colgate/高露洁'], 'type': '日化', 'country': 'US'},
    '啪啪通': {'aliases': ['啪啪通', 'Papatonk', 'Papatonk/啪啪通'], 'type': '零食', 'country': 'TH'},
    '雷达': {'aliases': ['雷达', 'Raid', 'Raid/雷达'], 'type': '日化', 'country': 'US'},
    '优衣库': {'aliases': ['优衣库', 'UNIQLO', 'UNIQLO/优衣库'], 'type': '服饰', 'country': 'JP'},
    '茄意欧': {'aliases': ['茄意欧', 'CIRIO', 'CIRIO/茄意欧'], 'type': '食品', 'country': 'IT'},
    '科颜氏': {'aliases': ['科颜氏', "Kiehl's", "Kiehl's/科颜氏"], 'type': '美妆', 'country': 'US'},
    '悠诗诗': {'aliases': ['悠诗诗', 'UCC', 'UCC/悠诗诗'], 'type': '咖啡', 'country': 'JP'},
    '乐博乐博': {'aliases': ['乐博乐博', 'ROBOROBO', 'ROBOROBO/乐博乐博'], 'type': '母婴', 'country': 'KR'},
    '大逸昌': {'aliases': ['大逸昌', 'Daisho', 'Daisho/大逸昌'], 'type': '食品', 'country': 'JP'},
    '蒂安': {'aliases': ['蒂安', 'D&A', 'D&A/蒂安'], 'type': '日化', 'country': 'CN'},
    '摩飞电器': {'aliases': ['摩飞电器', 'Morphy Richards', 'Morphy richards', 'Morphy Richards/摩飞电器', 'Morphy richards/摩飞电器'], 'type': '电器', 'country': 'GB'},
    '阿尔乐': {'aliases': ['阿尔乐', 'Arla', 'Arla/阿尔乐'], 'type': '乳品', 'country': 'DK'},
    '莱家': {'aliases': ['莱家', 'Loacker', 'Loacker/莱家'], 'type': '零食', 'country': 'IT'},
    '蝶翠诗': {'aliases': ['蝶翠诗', 'DHC', 'DHC/蝶翠诗'], 'type': '美妆', 'country': 'JP'},
    '皓乐齿': {'aliases': ['皓乐齿', 'Ora2', 'Ora2/皓乐齿'], 'type': '日化', 'country': 'JP'},
    '苏菲': {'aliases': ['苏菲', 'SOFY', 'SOFY/苏菲'], 'type': '日化', 'country': 'JP'},
    '芬达': {'aliases': ['芬达', 'Fanta', 'Fanta/芬达'], 'type': '饮料', 'country': 'US'},
    '兰蔻': {'aliases': ['兰蔻', 'Lancome', 'LANCOME', 'LANCOME/兰蔻', 'Lancome/兰蔻'], 'type': '美妆', 'country': 'FR'},
    '玛尔仕': {'aliases': ['玛尔仕', 'MARVIS', 'MARVIS/玛尔仕'], 'type': '日化', 'country': 'IT'},
    '福纳丝': {'aliases': ['福纳丝', 'Frosch', 'Frosch/福纳丝'], 'type': '日化', 'country': 'DE'},
    '咖世家': {'aliases': ['咖世家', 'COSTA', 'COSTA/咖世家'], 'type': '咖啡', 'country': 'GB'},
    '康维他': {'aliases': ['康维他', 'Comvita', 'comvita', 'comvita/康维他', '康维他/Comvita'], 'type': '食品', 'country': 'NZ'},
    '万益蓝': {'aliases': ['万益蓝', 'WonderLab', 'WonderLab/万益蓝'], 'type': '食品', 'country': 'CN'},
    '皮卡思': {'aliases': ['皮卡思', "Pic's", "Pic's/皮卡思"], 'type': '食品', 'country': 'NZ'},
    '力士': {'aliases': ['力士', 'LUX', 'LUX/力士'], 'type': '日化', 'country': 'NL'},
    '露莎士': {'aliases': ['露莎士', 'ROZA', 'ROZA/露莎士'], 'type': '食品', 'country': 'TH'},
    '安热沙': {'aliases': ['安热沙', 'ANESSA', 'ANESSA/安热沙'], 'type': '美妆', 'country': 'JP'},
    '飞利浦': {'aliases': ['飞利浦', 'PHILIPS', 'PHILIPS/飞利浦'], 'type': '电器', 'country': 'NL'},
    '瑞哺哺': {'aliases': ['瑞哺哺', 'RIVSEA', 'RIVSEA/瑞哺哺'], 'type': '母婴', 'country': 'CN'},
    '护舒宝': {'aliases': ['护舒宝', 'Whisper', 'whisper', 'whisper/护舒宝', 'Whisper/护舒宝', '护舒宝/Whisper'], 'type': '日化', 'country': 'US'},
    '小王子': {'aliases': ['小王子', 'KODOMO', 'KODOMO/小王子'], 'type': '母婴', 'country': 'KR'},
    '粒刻': {'aliases': ['粒刻', 'ELECTRO X', 'ELECTRO', 'ELECTRO/粒刻', 'ELECTRO X/粒刻'], 'type': '零食', 'country': 'CN'},
    '百乐顺': {'aliases': ['百乐顺', 'Bahlsen', 'Bahlsen/百乐顺'], 'type': '零食', 'country': 'DE'},
    '滴露': {'aliases': ['滴露', 'Dettol', 'Dettol/滴露'], 'type': '日化', 'country': 'GB'},
    '皮爷': {'aliases': ['皮爷', "Peet's Coffee", "Peet's Coffee/皮爷"], 'type': '咖啡', 'country': 'US'},
    '碧然德': {'aliases': ['碧然德', 'BRITA', 'BRITA/碧然德'], 'type': '电器', 'country': 'DE'},
    '好时': {'aliases': ['好时', "HERSHEY'S", "HERSHEY'S/好时"], 'type': '巧克力', 'country': 'US'},
    '全棉时代': {'aliases': ['全棉时代', 'Purcotton', 'Purcotton/全棉时代'], 'type': '母婴', 'country': 'CN'},
    '善存': {'aliases': ['善存', 'Centrum', 'Centrum/善存'], 'type': '保健', 'country': 'US'},
    '芙丝': {'aliases': ['芙丝', 'Voss', 'Voss/芙丝'], 'type': '饮水', 'country': 'NO'},
    '芬浓': {'aliases': ['芬浓', 'Fino', 'Fino/芬浓'], 'type': '美妆', 'country': 'JP'},
    '诗裴丝': {'aliases': ['诗裴丝', 'Spes', 'Spes/诗裴丝'], 'type': '美发', 'country': 'CN'},
    '可酷优': {'aliases': ['可酷优', 'COCIO', 'COCIO/可酷优'], 'type': '饮料', 'country': 'DK'},
    '四洛克': {'aliases': ['四洛克', 'FOURLOKO', 'FOURLOKO/四洛克'], 'type': '酒类', 'country': 'US'},
    '自由点': {'aliases': ['自由点', 'FREEMORE', 'FREEMORE/自由点'], 'type': '日化', 'country': 'CN'},
    '西部约翰': {'aliases': ['西部约翰', 'JohnWest', 'JohnWest/西部约翰'], 'type': '食品', 'country': 'AU'},
    '圣安娜': {'aliases': ['圣安娜', "Sant'Anna", "Sant'Anna/圣安娜"], 'type': '饮水', 'country': 'IT'},
    '美的': {'aliases': ['美的', 'Midea', 'Midea/美的'], 'type': '电器', 'country': 'CN'},
    '银宝': {'aliases': ['银宝', 'LURPAK', 'LURPAK/银宝'], 'type': '乳品', 'country': 'DK'},
    '奇巧': {'aliases': ['奇巧', 'KitKat', 'Kitkat', 'Kitkat/奇巧', 'KitKat/奇巧'], 'type': '巧克力', 'country': 'GB'},
    '吕': {'aliases': ['吕', 'RYO', 'RYO/吕'], 'type': '美发', 'country': 'KR'},
    '博格瑞': {'aliases': ['博格瑞', 'BONGRAIN', 'BONGRAIN/博格瑞'], 'type': '乳品', 'country': 'FR'},
    '界界乐': {'aliases': ['界界乐', 'Jelley Brown', 'Jelley Brown/界界乐'], 'type': '乳品', 'country': 'CN'},
    '多力多滋': {'aliases': ['多力多滋', 'Doritos', 'Doritos/多力多滋'], 'type': '零食', 'country': 'US'},
    '格力高': {'aliases': ['格力高', 'glico', 'glico/格力高'], 'type': '零食', 'country': 'JP'},
    '肌肤之钥': {'aliases': ['肌肤之钥', 'CPB', 'CPB/肌肤之钥'], 'type': '美妆', 'country': 'JP'},
    '松下': {'aliases': ['松下', 'Panasonic', 'Panasonic/松下'], 'type': '电器', 'country': 'JP'},
    '雅培': {'aliases': ['雅培', 'Abbott', 'Abbott/雅培'], 'type': '乳品', 'country': 'US'},
    '凡士林': {'aliases': ['凡士林', 'Vaseline', 'Vaseline/凡士林', '凡士林/Vaseline'], 'type': '日化', 'country': 'US'},
    '潘婷': {'aliases': ['潘婷', 'Pantene', 'Pantene/潘婷'], 'type': '美发', 'country': 'US'},
    '意榛滋': {'aliases': ['意榛滋', 'Nutella', 'Nutella/意榛滋'], 'type': '零食', 'country': 'IT'},
    '辣椒仔': {'aliases': ['辣椒仔', 'Tabasco', 'TABASCO', 'TABASCO/辣椒仔', 'Tabasco/辣椒仔'], 'type': '调味', 'country': 'US'},
    '可悠然': {'aliases': ['可悠然', 'KUYURA', 'KUYURA/可悠然'], 'type': '日化', 'country': 'JP'},
    '雀巢奇巧': {'aliases': ['雀巢奇巧', 'Kitkat', 'Kitkat/雀巢奇巧'], 'type': '巧克力', 'country': 'CN'},
    '柏克': {'aliases': ['柏克', 'BOURKES', 'BOURKES/柏克'], 'type': '食品', 'country': 'AU'},
    '诺倍得': {'aliases': ['诺倍得', 'No Brand', 'No Brand/诺倍得'], 'type': '零食', 'country': 'KR'},
    '惠氏': {'aliases': ['惠氏', 'Wyeth', 'Wyeth/惠氏'], 'type': '乳品', 'country': 'US'},
    '米膳葆': {'aliases': ['米膳葆', 'MISANBROO', 'MISANBROO/米膳葆'], 'type': '食品', 'country': 'CN'},
    '海蓝之谜': {'aliases': ['海蓝之谜', 'LA MER', 'LA MER/海蓝之谜'], 'type': '美妆', 'country': 'US'},
    '奶酪博士': {'aliases': ['奶酪博士', 'Dr.Cheese', 'Dr.Cheese/奶酪博士'], 'type': '乳品', 'country': 'CN'},
    '她研社': {'aliases': ['她研社', 'Herlab', 'Herlab/她研社'], 'type': '日化', 'country': 'CN'},
    '可达怡': {'aliases': ['可达怡', 'KOTANYI', 'KOTANYI/可达怡'], 'type': '调味', 'country': 'AT'},
    '喜力': {'aliases': ['喜力', 'Heineken', 'Heineken/喜力'], 'type': '啤酒', 'country': 'NL'},
    '泰娘': {'aliases': ['泰娘', 'MAE PLOY', 'MAE PLOY/泰娘'], 'type': '调味', 'country': 'TH'},
    '亨氏': {'aliases': ['亨氏', 'Heinz', 'HEINZ', 'HEINZ/亨氏', 'Heinz/亨氏', '亨氏/Heinz'], 'type': '食品', 'country': 'US'},
    '莱芙士': {'aliases': ['莱芙士', 'Ruffles', 'Ruffles/莱芙士'], 'type': '零食', 'country': 'US'},
    '珊珂': {'aliases': ['珊珂', 'SENKA', 'SENKA/珊珂'], 'type': '美妆', 'country': 'JP'},
    '莱纳': {'aliases': ['莱纳', 'LERNA', 'LERNA/莱纳'], 'type': '食品', 'country': 'IT'},
    '三麟': {'aliases': ['三麟', 'SANLIN', 'SANLIN/三麟'], 'type': '啤酒', 'country': 'CN'},
    '西苔': {'aliases': ['西苔', 'CITTA', 'CITTA/西苔'], 'type': '母婴', 'country': 'CN'},
    '大宇': {'aliases': ['大宇', 'DAEWOO', 'DAEWOO/大宇'], 'type': '电器', 'country': 'KR'},
    '德佑': {'aliases': ['德佑', 'Deeyeo', 'Deeyeo/德佑'], 'type': '母婴', 'country': 'CN'},
    '瑞贝诗': {'aliases': ['瑞贝诗', 'RIVSEA', 'RIVSEA/瑞贝诗'], 'type': '母婴', 'country': 'CN'},
    '科普菲': {'aliases': ['科普菲', 'KEEPFIT', 'KEEPFIT/科普菲'], 'type': '电器', 'country': 'CN'},
    '贵为': {'aliases': ['贵为', 'Gigwi', 'GiGwi', 'GiGwi/贵为', 'Gigwi/贵为'], 'type': '宠物', 'country': 'CN'},
    '宝蓝吉': {'aliases': ['宝蓝吉', 'Polenghi', 'Polenghi/宝蓝吉'], 'type': '乳品', 'country': 'IT'},
    '佳洁士': {'aliases': ['佳洁士', 'Crest', 'Crest/佳洁士'], 'type': '日化', 'country': 'US'},
    '格露芙': {'aliases': ['格露芙', 'Grove', 'Grove/格露芙'], 'type': '日化', 'country': 'CA'},
    '郁金香': {'aliases': ['郁金香', 'Tulip', 'Tulip/郁金香'], 'type': '食品', 'country': 'DK'},
    '哲品': {'aliases': ['哲品', 'ZENS', 'ZENS/哲品'], 'type': '电器', 'country': 'CN'},
    '妃美堂': {'aliases': ['妃美堂', 'SIMEITOL', 'SIMEITOL/妃美堂'], 'type': '食品', 'country': 'CN'},
    '瑞沛': {'aliases': ['瑞沛', 'RIVSEA', 'RIVSEA/瑞沛'], 'type': '母婴', 'country': 'CN'},
    '舒适': {'aliases': ['舒适', 'Schick', 'Schick/舒适'], 'type': '日化', 'country': 'US'},
    '玛尔维斯': {'aliases': ['玛尔维斯', 'MARVIS', 'MARVIS/玛尔维斯'], 'type': '日化', 'country': 'IT'},
    '米杉博': {'aliases': ['米杉博', 'MISANBROO', 'MISANBROO/米杉博'], 'type': '食品', 'country': 'CN'},
    '艾美适': {'aliases': ['艾美适', 'ELMEX', 'Elmex', 'Elmex/艾美适', 'ELMEX/艾美适'], 'type': '日化', 'country': 'CH'},
    '吉列': {'aliases': ['吉列', 'Gillette', 'Gillette/吉列'], 'type': '日化', 'country': 'US'},
    '冈本': {'aliases': ['冈本', 'Okamoto', 'okamoto', 'okamoto/冈本', 'Okamoto/冈本'], 'type': '日化', 'country': 'JP'},
    '帮宝适': {'aliases': ['帮宝适', 'Pampers', 'Pampers/帮宝适'], 'type': '母婴', 'country': 'US'},
    '杰士派': {'aliases': ['杰士派', 'Gatsby', 'GATSBY', 'GATSBY/杰士派', 'Gatsby/杰士派'], 'type': '美发', 'country': 'JP'},
    '凯芮': {'aliases': ['凯芮', 'Kiri', 'Kiri/凯芮'], 'type': '乳品', 'country': 'FR'},
    '川宁': {'aliases': ['川宁', 'Twinings', 'Twinings/川宁'], 'type': '茶饮', 'country': 'GB'},
    '飞瑞尔': {'aliases': ['飞瑞尔', 'Frey', 'Frey/飞瑞尔'], 'type': '巧克力', 'country': 'CH'},
    '确美同': {'aliases': ['确美同', 'Coppertone', 'Coppertone/确美同'], 'type': '美妆', 'country': 'US'},
    '宾得宝': {'aliases': ['宾得宝', 'Bundaberg', 'Bundaberg/宾得宝'], 'type': '饮料', 'country': 'AU'},
    '一和': {'aliases': ['一和', 'IL HWA', 'IL HWA/一和'], 'type': '食品', 'country': 'KR'},
    '贺本清': {'aliases': ['贺本清', 'Herbacin', 'Herbacin/贺本清'], 'type': '日化', 'country': 'DE'},
    '茱蒂丝': {'aliases': ['茱蒂丝', "Julie's", "Julie's/茱蒂丝"], 'type': '零食', 'country': 'MY'},
    '安怡': {'aliases': ['安怡', 'Anlene', 'Anlene/安怡'], 'type': '乳品', 'country': 'NZ'},
    '三禾': {'aliases': ['三禾', 'SANHO', 'SANHO/三禾'], 'type': '厨具', 'country': 'CN'},
    '卡拉美拉': {'aliases': ['卡拉美拉', 'Caramella', 'caramella', 'caramella/卡拉美拉', 'Caramella/卡拉美拉'], 'type': '服饰', 'country': 'CN'},
    '珏士高': {'aliases': ['珏士高', 'Jaxcoco', 'Jaxcoco/珏士高'], 'type': '饮料', 'country': 'CN'},
    '北欧瓦特拉姆': {'aliases': ['北欧瓦特拉姆', 'wattram', 'wattram/北欧瓦特拉姆'], 'type': '乳品', 'country': 'SE'},
    '麦斯卡': {'aliases': ['麦斯卡', 'Mesuca', 'Mesuca/麦斯卡'], 'type': '美妆', 'country': 'CN'},
    '米珊博': {'aliases': ['米珊博', 'MISANBROO', 'MISANBROO/米珊博'], 'type': '食品', 'country': 'CN'},
    '安克': {'aliases': ['安克', 'Anker', 'Anker/安克'], 'type': '电子', 'country': 'CN'},
    '希望树': {'aliases': ['希望树', 'Full of Hope', 'Full of Hope/希望树'], 'type': '日化', 'country': 'CN'},
    '贝德玛': {'aliases': ['贝德玛', 'BIODERMA', 'BIODERMA/贝德玛'], 'type': '美妆', 'country': 'FR'},
    '益倍适': {'aliases': ['益倍适', 'life space', 'life space/益倍适'], 'type': '保健', 'country': 'AU'},
    '莉派': {'aliases': ['莉派', 'claynal', 'claynal/莉派'], 'type': '美发', 'country': 'JP'},
    '钙尔奇': {'aliases': ['钙尔奇', 'Caltrate', 'Caltrate/钙尔奇'], 'type': '保健', 'country': 'US'},
    '雅诗兰黛': {'aliases': ['雅诗兰黛', 'ESTEE LAUDER', 'Estee Lauder', 'Estee Lauder/雅诗兰黛', 'ESTEE LAUDER/雅诗兰黛'], 'type': '美妆', 'country': 'US'},
    '妮维雅': {'aliases': ['妮维雅', 'NIVEA', 'Nivea', 'Nivea/妮维雅', 'NIVEA/妮维雅'], 'type': '日化', 'country': 'DE'},
    '柏瑞美': {'aliases': ['柏瑞美', 'PRAMY', 'PRAMY/柏瑞美'], 'type': '美妆', 'country': 'CN'},
    '可伦诗': {'aliases': ['可伦诗', 'CLORIS', 'CLORIS/可伦诗'], 'type': '日化', 'country': 'CN'},
    '欧舒丹': {'aliases': ['欧舒丹', "L'occitane", "L'occitane/欧舒丹"], 'type': '美妆', 'country': 'FR'},
    '清扬': {'aliases': ['清扬', 'CLEAR', 'CLEAR/清扬'], 'type': '美发', 'country': 'NL'},
    '桃瑞': {'aliases': ['桃瑞', 'Torriden', 'Torriden/桃瑞'], 'type': '美妆', 'country': 'KR'},
    '圣罗兰': {'aliases': ['圣罗兰', 'YSL', 'YSL/圣罗兰'], 'type': '美妆', 'country': 'FR'},
    '阿玛尼': {'aliases': ['阿玛尼', 'GIORGIO ARMANI', 'GIORGIO ARMANI/阿玛尼'], 'type': '美妆', 'country': 'IT'},
    '爱和纯': {'aliases': ['爱和纯', 'AHC', 'AHC/爱和纯'], 'type': '美妆', 'country': 'KR'},
    '杰士邦': {'aliases': ['杰士邦', 'jissbon', 'JISSBON', 'JISSBON/杰士邦', 'jissbon/杰士邦'], 'type': '日化', 'country': 'CN'},
    '马洛先生': {'aliases': ['马洛先生', 'Mr Mallo', 'Mr Mallo/马洛先生'], 'type': '食品', 'country': 'CN'},
    '一口阳光': {'aliases': ['一口阳光', 'Sunbites', 'Sunbites/一口阳光'], 'type': '零食', 'country': 'US'},
    '荷美尔': {'aliases': ['荷美尔', 'Hormel', 'Hormel/荷美尔'], 'type': '食品', 'country': 'US'},
    '小熊': {'aliases': ['小熊', 'Bear', 'Bear/小熊'], 'type': '电器', 'country': 'CN'},
    '闲趣': {'aliases': ['闲趣', 'TUC', 'TUC/闲趣'], 'type': '零食', 'country': 'FR'},
    '金鸟': {'aliases': ['金鸟', 'KINCHO', 'KINCHO/金鸟'], 'type': '日化', 'country': 'JP'},
    '依云': {'aliases': ['依云', 'Evian', 'Evian/依云'], 'type': '饮水', 'country': 'FR'},
    '意立诗': {'aliases': ['意立诗', 'ellips', 'ellips/意立诗'], 'type': '美发', 'country': 'ID'},
    '矿派': {'aliases': ['矿派', 'claynal', 'claynal/矿派'], 'type': '美发', 'country': 'JP'},
    '保宁': {'aliases': ['保宁', 'B&B', 'B&B/保宁'], 'type': '母婴', 'country': 'KR'},
    '奇多': {'aliases': ['奇多', 'Cheetos', 'Cheetos/奇多'], 'type': '零食', 'country': 'US'},
    '斐泉': {'aliases': ['斐泉', 'FIJI', 'FIJI/斐泉'], 'type': '饮水', 'country': 'FJ'},
    '贝比': {'aliases': ['贝比', 'RIVSEA', 'RIVSEA/贝比'], 'type': '母婴', 'country': 'CN'},
    '薇姿': {'aliases': ['薇姿', 'Vichy', 'Vichy/薇姿'], 'type': '美妆', 'country': 'FR'},
    '东菱': {'aliases': ['东菱', 'Donlim', 'Donlim/东菱'], 'type': '电器', 'country': 'CN'},
    '三养': {'aliases': ['三养', 'SANLIN', 'SANLIN/三养'], 'type': '食品', 'country': 'KR'},
    '佳乐滋': {'aliases': ['佳乐滋', 'GAINES', 'GAINES/佳乐滋'], 'type': '宠物', 'country': 'JP'},
    '北欧沃特拉姆': {'aliases': ['北欧沃特拉姆', 'wattram', 'wattram/北欧沃特拉姆'], 'type': '乳品', 'country': 'SE'},
    '奇士美': {'aliases': ['奇士美', 'KISS ME', 'KISS ME/奇士美'], 'type': '美妆', 'country': 'JP'},
    '炫迈': {'aliases': ['炫迈', 'Stride', 'Stride/炫迈'], 'type': '零食', 'country': 'US'},
    '吉普': {'aliases': ['吉普', 'Jeep', 'Jeep/吉普'], 'type': '服饰', 'country': 'US'},
    '吉芝生活': {'aliases': ['吉芝生活', 'Oralife', 'Oralife/吉芝生活'], 'type': '日化', 'country': 'CN'},
    '康巴赫': {'aliases': ['康巴赫', 'KBH', 'KBH/康巴赫'], 'type': '厨具', 'country': 'CN'},
    '欧莱雅': {'aliases': ['欧莱雅', "L'OREAL", "L'OREAL/欧莱雅"], 'type': '美妆', 'country': 'FR'},
    '美赞臣': {'aliases': ['美赞臣', 'Mead Johnson', 'Mead Johnson/美赞臣'], 'type': '乳品', 'country': 'US'},
    '瑞碧': {'aliases': ['瑞碧', 'RIVSEA', 'RIVSEA/瑞碧'], 'type': '母婴', 'country': 'CN'},
    '桃瑞丝': {'aliases': ['桃瑞丝', 'Torriden', 'Torriden/桃瑞丝'], 'type': '美妆', 'country': 'KR'},
    '拉瓦萨': {'aliases': ['拉瓦萨', 'LAVAZZA', 'LAVAZZA/拉瓦萨'], 'type': '咖啡', 'country': 'IT'},
    '麦维他': {'aliases': ['麦维他', 'Mcvities', 'Mcvities/麦维他'], 'type': '零食', 'country': 'GB'},
    '芭绮': {'aliases': ['芭绮', 'Baci', 'Baci/芭绮'], 'type': '巧克力', 'country': 'IT'},
    '悠美芮': {'aliases': ['悠美芮', 'JUMINAIRE', 'JUMINAIRE/悠美芮'], 'type': '乳品', 'country': 'CN'},
    '杯具熊': {'aliases': ['杯具熊', 'BEDDYBEAR', 'BEDDYBEAR/杯具熊'], 'type': '母婴', 'country': 'CN'},
    '阿司倍鹭': {'aliases': ['阿司倍鹭', 'ASVEL', 'ASVEL/阿司倍鹭'], 'type': '厨具', 'country': 'JP'},
    '世棒': {'aliases': ['世棒', 'SPAM', 'SPAM/世棒'], 'type': '食品', 'country': 'US'},
    '入一': {'aliases': ['入一', 'INTEONE', 'INTEONE/入一'], 'type': '食品', 'country': 'CN'},
    '维爵士': {'aliases': ['维爵士', 'VEJECY', 'VEJECY/维爵士'], 'type': '母婴', 'country': 'CN'},
    '巴菲高': {'aliases': ['巴菲高', 'Badigo', 'Badigo/巴菲高'], 'type': '食品', 'country': 'CN'},
    '宝洁': {'aliases': ['宝洁', 'P&G', 'P&G/宝洁'], 'type': '日化', 'country': 'US'},
    '福克斯': {'aliases': ['福克斯', "FOX'S", "FOX'S/福克斯"], 'type': '零食', 'country': 'GB'},
    '西屋': {'aliases': ['西屋', 'Westinghouse', 'Westinghouse/西屋'], 'type': '电器', 'country': 'US'},
    '植村秀': {'aliases': ['植村秀', 'shu uemura', 'shu uemura/植村秀'], 'type': '美妆', 'country': 'JP'},
    '喜屋': {'aliases': ['喜屋', 'Sherwood', 'Sherwood/喜屋'], 'type': '食品', 'country': 'CN'},
    '莎娜': {'aliases': ['莎娜', 'SANA', 'SANA/莎娜'], 'type': '美妆', 'country': 'JP'},
    '莫利萨娜': {'aliases': ['莫利萨娜', 'Molisana', 'Molisana/莫利萨娜'], 'type': '意面', 'country': 'IT'},
    '芋太郎': {'aliases': ['芋太郎', 'SAKURA TARO', 'SAKURA TARO/芋太郎'], 'type': '零食', 'country': 'JP'},
    '爱马仕': {'aliases': ['爱马仕', 'Hermes', 'Hermes/爱马仕'], 'type': '美妆', 'country': 'FR'},
    '妙思乐': {'aliases': ['妙思乐', 'Mustela', 'Mustela/妙思乐'], 'type': '母婴', 'country': 'FR'},
    '乐知': {'aliases': ['乐知', 'JOYU', 'JOYU/乐知'], 'type': '食品', 'country': 'CN'},
    '品客': {'aliases': ['品客', 'Pringles', 'Pringles/品客'], 'type': '零食', 'country': 'US'},
    '绿鼻子': {'aliases': ['绿鼻子', 'Greennose', 'Greennose/绿鼻子'], 'type': '母婴', 'country': 'KR'},
    '紫焰': {'aliases': ['紫焰', 'PURPLE FLAME', 'PURPLE FLAME/紫焰'], 'type': '食品', 'country': 'CN'},
    '纽仕兰': {'aliases': ['纽仕兰', 'Theland', 'The land', 'Theland/纽仕兰', 'The land/纽仕兰'], 'type': '乳品', 'country': 'NZ'},
    '露安适': {'aliases': ['露安适', 'Lelch', 'Lelch/露安适'], 'type': '母婴', 'country': 'DE'},
    '李施德林': {'aliases': ['李施德林', 'Listerine', 'Listerine/李施德林'], 'type': '日化', 'country': 'US'},
    '红印': {'aliases': ['红印', 'RED SEAL', 'RED SEAL/红印'], 'type': '食品', 'country': 'NZ'},
    '九阳': {'aliases': ['九阳', 'Joyoung', 'Joyoung/九阳'], 'type': '电器', 'country': 'CN'},
    '康齿家': {'aliases': ['康齿家', 'GUM', 'GUM/康齿家'], 'type': '日化', 'country': 'JP'},
    '皇家美素力': {'aliases': ['皇家美素力', 'Frisolac PRESTIGE', 'Frisolac PRESTIGE/皇家美素力'], 'type': '乳品', 'country': 'NL'},
    '麦西恩': {'aliases': ['麦西恩', 'mission', 'mission/麦西恩'], 'type': '食品', 'country': 'MX'},
    '桃瑞丹': {'aliases': ['桃瑞丹', 'Torriden', 'Torriden/桃瑞丹'], 'type': '美妆', 'country': 'KR'},
    '威猛先生': {'aliases': ['威猛先生', 'Mr Muscle', 'Mr Muscle/威猛先生'], 'type': '日化', 'country': 'US'},
    '阿彼芙': {'aliases': ['阿彼芙', 'Abib', 'Abib/阿彼芙'], 'type': '美妆', 'country': 'KR'},
    '多芬': {'aliases': ['多芬', 'Dove', 'Dove/多芬'], 'type': '日化', 'country': 'US'},
    '米斯布朗': {'aliases': ['米斯布朗', 'MISANBROO', 'MISANBROO/米斯布朗'], 'type': '食品', 'country': 'CN'},
    '惠润': {'aliases': ['恵润', 'SUPER MILD', 'SUPER MILD/惠润'], 'type': '美发', 'country': 'JP'},
    '小犬王': {'aliases': ['小犬王', 'KODOMO', 'KODOMO/小犬王'], 'type': '宠物', 'country': 'KR'},
    '淳萃': {'aliases': ['淳萃', 'SUPER MILD', 'SUPER MILD/淳萃'], 'type': '美发', 'country': 'JP'},
    '凌仕牌': {'aliases': ['凌仕牌', 'AXE', 'AXE/凌仕牌'], 'type': '日化', 'country': 'US'},
    '健安喜': {'aliases': ['健安喜', 'GNC', 'GNC/健安喜'], 'type': '保健', 'country': 'US'},
    '肉匠': {'aliases': ['肉匠', 'Meatyway', 'Meatyway/肉匠'], 'type': '宠物', 'country': 'CN'},
    '闻绮': {'aliases': ['闻绮', 'Venchi', 'Venchi/闻绮'], 'type': '巧克力', 'country': 'IT'},
    '丹麦蓝罐': {'aliases': ['丹麦蓝罐', 'Kjeldsens', 'Kjeldsens/丹麦蓝罐'], 'type': '零食', 'country': 'DK'},
    '好乐门': {'aliases': ['好乐门', "Hellmann's", "Hellmann's/好乐门"], 'type': '调味', 'country': 'US'},
    '格沵': {'aliases': ['格沵', 'GERM', 'GERM/格沵'], 'type': '母婴', 'country': 'CN'},
    '莱米可': {'aliases': ['莱米可', 'Lemmycree', 'Lemmycree/莱米可'], 'type': '母婴', 'country': 'CN'},
    '斐济': {'aliases': ['斐济', 'FIJI', 'FIJI/斐济'], 'type': '饮水', 'country': 'FJ'},
    '蕉趣': {'aliases': ['蕉趣', 'BANANA TRIP', 'BANANA TRIP/蕉趣'], 'type': '服饰', 'country': 'CN'},
    '可可优': {'aliases': ['可可优', 'COCIO', 'COCIO/可可优'], 'type': '饮料', 'country': 'DK'},
    '椰子高': {'aliases': ['椰子高', 'Jaxcoco', 'Jaxcoco/椰子高'], 'type': '饮料', 'country': 'CN'},
    '未零': {'aliases': ['未零', 'beazero', 'beazero/未零'], 'type': '母婴', 'country': 'CN'},
    '达斯米': {'aliases': ['达斯米', 'Dasty', 'Dasty/达斯米'], 'type': '食品', 'country': 'CN'},
    '艾维诺': {'aliases': ['艾维诺', 'Aveeno', 'Aveeno/艾维诺'], 'type': '日化', 'country': 'US'},
    '蓬派': {'aliases': ['蓬派', 'claynal', 'claynal/蓬派'], 'type': '美发', 'country': 'JP'},
    '克雷纳': {'aliases': ['克雷纳', 'claynal', 'claynal/克雷纳'], 'type': '美发', 'country': 'JP'},
    '瑞比': {'aliases': ['瑞比', 'RIVSEA', 'RIVSEA/瑞比'], 'type': '母婴', 'country': 'CN'},
    '瑞维斯': {'aliases': ['瑞维斯', 'RIVSEA', 'RIVSEA/瑞维斯'], 'type': '母婴', 'country': 'CN'},
    '每日盒子': {'aliases': ['每日盒子', 'RIVSEA', 'RIVSEA/每日盒子'], 'type': '母婴', 'country': 'CN'},
    '西西里': {'aliases': ['西西里', 'La Sicilia', 'La Sicilia/西西里'], 'type': '意面', 'country': 'IT'},
    '啵乐乐': {'aliases': ['啵乐乐', 'Pororo', 'Pororo/啵乐乐'], 'type': '母婴', 'country': 'KR'},
    '巨人': {'aliases': ['巨人', 'COLOSSUS', 'COLOSSUS/巨人'], 'type': '食品', 'country': 'CN'},
    '艾梵达': {'aliases': ['艾梵达', 'Aveda', 'Aveda/艾梵达'], 'type': '美发', 'country': 'US'},
    '芳润': {'aliases': ['芳润', 'Fino', 'Fino/芳润'], 'type': '美妆', 'country': 'JP'},
    '希宝': {'aliases': ['希宝', 'SHEBA', 'SHEBA/希宝'], 'type': '宠物', 'country': 'AU'},
    '芳浓': {'aliases': ['芳浓', 'Fino', 'Fino/芳浓'], 'type': '美妆', 'country': 'JP'},
    '资生堂': {'aliases': ['资生堂', 'SHISEIDO', 'SHISEIDO/资生堂'], 'type': '美妆', 'country': 'JP'},
    '红牛': {'aliases': ['红牛', 'RedBull', 'RedBull/红牛'], 'type': '饮料', 'country': 'AT'},
    '地狱厨房': {'aliases': ['地狱厨房', "Hell's Kitchen", "Hell's Kitchen/地狱厨房"], 'type': '宠物', 'country': 'CN'},
    '樫太郎': {'aliases': ['樫太郎', 'SAKURA TARO', 'SAKURA TARO/樫太郎'], 'type': '零食', 'country': 'JP'},
    '皇家': {'aliases': ['皇家', 'FrisoPrestige', 'FrisoPrestige/皇家'], 'type': '乳品', 'country': 'NL'},
    '艾莉儿': {'aliases': ['艾莉儿', 'Ariul', 'Ariul/艾莉儿'], 'type': '美妆', 'country': 'KR'},
    '黏派': {'aliases': ['黏派', 'claynal', 'claynal/黏派'], 'type': '美发', 'country': 'JP'},
    '立时': {'aliases': ['立时', 'olayks', 'olayks/立时'], 'type': '电器', 'country': 'CN'},
    '桃瑞朵': {'aliases': ['桃瑞朵', 'Torriden', 'Torriden/桃瑞朵'], 'type': '美妆', 'country': 'KR'},
    '桃瑞旦': {'aliases': ['桃瑞旦', 'Torriden', 'Torriden/桃瑞旦'], 'type': '美妆', 'country': 'KR'},
    '桃瑞甸': {'aliases': ['桃瑞甸', 'Torriden', 'Torriden/桃瑞甸'], 'type': '美妆', 'country': 'KR'},
    '好时 KISSES': {'aliases': ['好时 KISSES', "HERSHEY'S", "HERSHEY'S/好时 KISSES"], 'type': '巧克力', 'country': 'US'},
    '格兰': {'aliases': ['格兰', 'GERM', 'GERM/格兰'], 'type': '母婴', 'country': 'CN'},
    '吉士生活': {'aliases': ['吉士生活', 'Oralife', 'Oralife/吉士生活'], 'type': '日化', 'country': 'CN'},
    '立刻': {'aliases': ['立刻', 'olayks', 'olayks/立刻'], 'type': '电器', 'country': 'CN'},
    '桃瑞德': {'aliases': ['桃瑞德', 'Torriden', 'Torriden/桃瑞德'], 'type': '美妆', 'country': 'KR'},
    '艾杜纱': {'aliases': ['艾杜纱', 'Ariul', 'Ariul/艾杜纱'], 'type': '美妆', 'country': 'JP'},
    '卡蛙': {'aliases': ['卡蛙', 'smart frog', 'smart frog/卡蛙'], 'type': '电器', 'country': 'CN'},
    '菓娜贝拉': {'aliases': ['菓娜贝拉', 'Dorabella', 'Dorabella/菓娜贝拉'], 'type': '零食', 'country': 'CN'},
    '澳芝蔓': {'aliases': ['澳芝蔓', 'G&M', 'G&M/澳芝蔓'], 'type': '日化', 'country': 'AU'},
    '微沃姆': {'aliases': ['微沃姆', 'WeWarm', 'WeWarm/微沃姆'], 'type': '电器', 'country': 'CN'},
    '松尾': {'aliases': ['松尾', 'TIROL', 'TIROL/松尾'], 'type': '零食', 'country': 'JP'},
    '淳净': {'aliases': ['淳净', 'SUPER MILD', 'SUPER MILD/淳净'], 'type': '美发', 'country': 'JP'},
    '安斯丽': {'aliases': ['安斯丽', 'AYNSLEY', 'AYNSLEY/安斯丽'], 'type': '厨具', 'country': 'GB'},
    '米妍': {'aliases': ['米妍', 'meyarn', 'meyarn/米妍'], 'type': '美妆', 'country': 'CN'},
    '生和堂': {'aliases': ['生和堂', 'Sunity', 'Sunity/生和堂'], 'type': '食品', 'country': 'CN'},
    '津金果': {'aliases': ['津金果', 'Jingold', 'Jingold/津金果'], 'type': '食品', 'country': 'CN'},
    '海特曼': {'aliases': ['海特曼', 'HEITMANN', 'HEITMANN/海特曼'], 'type': '日化', 'country': 'DE'},
    '露怡': {'aliases': ['露怡', 'LU', 'LU/露怡'], 'type': '零食', 'country': 'FR'},
    '格米': {'aliases': ['格米', 'GERM', 'GERM/格米'], 'type': '母婴', 'country': 'CN'},
    '八道': {'aliases': ['八道', 'PALDO', 'PALDO/八道'], 'type': '食品', 'country': 'KR'},
    '公仔': {'aliases': ['公仔', 'Doll', 'Doll/公仔'], 'type': '食品', 'country': 'HK'},
    '杜蕾斯': {'aliases': ['杜蕾斯', 'Durex', 'Durex/杜蕾斯'], 'type': '日化', 'country': 'GB'},
    '桑塔丽': {'aliases': ['桑塔丽', 'SANITARIUM', 'SANITARIUM/桑塔丽'], 'type': '食品', 'country': 'AU'},
    '圃美多': {'aliases': ['圃美多', 'Pulmuone', 'Pulmuone/圃美多'], 'type': '食品', 'country': 'KR'},
    '亮碟': {'aliases': ['亮碟', 'Finish', 'Finish/亮碟'], 'type': '日化', 'country': 'US'},

    # === 动态品牌（自动合并）===
    '1664': {'aliases': ['1664'], 'type': '啤酒', 'country': 'CN'},
    'AGF': {'aliases': ['AGF'], 'type': '咖啡', 'country': 'JP'},
    'AJI': {'aliases': ['AJI'], 'type': '零食', 'country': 'CN'},
    'ALCE NERO': {'aliases': ['有机尼奥', 'ALCE NERO', '有机尼奥/ALCE NERO'], 'type': '意面', 'country': 'IT'},
    'VFOODS': {'aliases': ['VFOODS'], 'type': '零食', 'country': 'TH'},
    'ZEK': {'aliases': ['ZEK'], 'type': '饮料', 'country': 'KR'},
    'knoppers': {'aliases': ['knoppers'], 'type': '零食', 'country': 'DE'},
    '不倒翁': {'aliases': ['不倒翁'], 'type': '速食', 'country': 'KR'},
    '乐芝牛': {'aliases': ['乐芝牛'], 'type': '乳品', 'country': 'CN'},
    '习酒': {'aliases': ['习酒'], 'type': '酒类', 'country': 'CN'},
    '今世缘': {'aliases': ['今世缘'], 'type': '酒类', 'country': 'CN'},
    '保拉纳': {'aliases': ['保拉纳'], 'type': '啤酒', 'country': 'DE'},
    '健力士': {'aliases': ['健力士'], 'type': '酒类', 'country': 'CN'},
    '六婆': {'aliases': ['六婆'], 'type': '调味', 'country': 'CN'},
    '养养': {'aliases': ['养养'], 'type': '速食', 'country': 'TH'},
    '冠利': {'aliases': ['冠利', 'Kuhne/冠利', 'Kuhne'], 'type': '调味', 'country': 'DE'},
    '力保健': {'aliases': ['力保健'], 'type': '饮料', 'country': 'CN'},
    '劲牌': {'aliases': ['劲牌'], 'type': '酒类', 'country': 'CN'},
    '北大荒': {'aliases': ['北大荒'], 'type': '酱菜', 'country': 'CN'},
    '古井贡': {'aliases': ['古井贡'], 'type': '酒类', 'country': 'CN'},
    '古越龙山': {'aliases': ['古越龙山'], 'type': '酒类', 'country': 'CN'},
    '吉利火星': {'aliases': ['吉利火星'], 'type': '零食', 'country': 'CN'},
    '味好美': {'aliases': ['味好美'], 'type': '调味', 'country': 'CN'},
    '呷哺呷哺': {'aliases': ['呷哺呷哺'], 'type': '调味', 'country': 'CN'},
    '喜之郎': {'aliases': ['喜之郎'], 'type': '零食', 'country': 'CN'},
    '四季宝': {'aliases': ['SKIPPY/四季宝', 'SKIPPY', '四季宝'], 'type': '酱料', 'country': 'CN'},
    '四洲': {'aliases': ['四洲'], 'type': '零食', 'country': 'CN'},
    '国窖': {'aliases': ['国窖'], 'type': '酒类', 'country': 'CN'},
    '国缘': {'aliases': ['国缘'], 'type': '酒类', 'country': 'CN'},
    '大自然': {'aliases': ['大自然'], 'type': '生鲜', 'country': 'CN'},
    '天福号': {'aliases': ['天福号'], 'type': '熟食', 'country': 'CN'},
    '太湖黑': {'aliases': ['太湖黑'], 'type': '肉禽蛋', 'country': 'CN'},
    '奥兰': {'aliases': ['奥兰'], 'type': '酒类', 'country': 'ES (西班牙)'},
    '好天好饮': {'aliases': ['好天好饮'], 'type': '酒类', 'country': 'KR'},
    '妙可蓝多': {'aliases': ['妙可蓝多'], 'type': '乳品', 'country': 'CN'},
    '妙妙': {'aliases': ['妙妙'], 'type': '零食', 'country': 'CN'},
    '宝矿力水特': {'aliases': ['宝矿力水特'], 'type': '饮料', 'country': 'CN'},
    '崂山': {'aliases': ['崂山'], 'type': '饮料', 'country': 'CN'},
    '川南': {'aliases': ['川南'], 'type': '调味', 'country': 'CN'},
    '德芙': {'aliases': ['德芙'], 'type': '巧克力', 'country': 'CN'},
    '怡泉': {'aliases': ['怡泉'], 'type': '饮料', 'country': 'CN'},
    '怡颗莓': {'aliases': ["Driscoll's /怡颗莓", '怡颗莓', "Driscoll's"], 'type': '水果', 'country': 'CN'},
    '新良': {'aliases': ['新良'], 'type': '烘焙', 'country': 'CN'},
    '日清': {'aliases': ['日清'], 'type': '粮油', 'country': 'JP'},
    '旺旺': {'aliases': ['旺旺'], 'type': '乳品', 'country': 'CN'},
    '林德曼': {'aliases': ['林德曼'], 'type': '酒类', 'country': 'BE (比利时)'},
    '森永': {'aliases': ['森永'], 'type': '食品', 'country': 'JP'},
    '椰树': {'aliases': ['椰树牌'], 'type': '饮料', 'country': 'CN'},
    '欣善怡': {'aliases': ['欣善怡'], 'type': '粮油', 'country': 'CN'},
    '欧丽薇兰': {'aliases': ['欧丽薇兰'], 'type': '粮油', 'country': 'CN'},
    '正大': {'aliases': ['正大食品', '正大', 'CP', 'CP/正大'], 'type': '速冻', 'country': 'TH'},
    '正林': {'aliases': ['正林'], 'type': '零食', 'country': 'CN'},
    '水井坊': {'aliases': ['水井坊'], 'type': '酒类', 'country': 'CN'},
    '汾酒': {'aliases': ['汾酒'], 'type': '酒类', 'country': 'CN'},
    '泰森': {'aliases': ['泰森'], 'type': '速冻', 'country': 'CN'},
    '泸州老窖': {'aliases': ['泸州老窖'], 'type': '酒类', 'country': 'CN'},
    '洋河': {'aliases': ['洋河'], 'type': '酒类', 'country': 'CN'},
    '海霸王': {'aliases': ['海霸王'], 'type': '速冻', 'country': 'CN'},
    '澳芝曼': {'aliases': ['澳芝曼'], 'type': '美妆', 'country': 'AU'},
    '珍酒': {'aliases': ['珍酒'], 'type': '酒类', 'country': 'CN'},
    '瑞特滋': {'aliases': ['瑞特滋'], 'type': '巧克力', 'country': 'DE'},
    '甘露': {'aliases': ['甘露'], 'type': '酒类', 'country': 'US'},
    '百利': {'aliases': ['百利'], 'type': '酒类', 'country': 'CN'},
    '碧浪': {'aliases': ['碧浪'], 'type': '个人清洁', 'country': 'CN'},
    '稻香诚制': {'aliases': ['稻香诚制'], 'type': '面点', 'country': 'CN'},
    '筷手小厨': {'aliases': ['筷手小厨'], 'type': '调味', 'country': 'CN'},
    '红星': {'aliases': ['红星'], 'type': '酒类', 'country': 'CN'},
    '绫鹰': {'aliases': ['绫鹰'], 'type': '饮料', 'country': 'JP'},
    '维他奶': {'aliases': ['维他奶'], 'type': '饮料', 'country': 'CN'},
    '绿箭': {'aliases': ['绿箭'], 'type': '零食', 'country': 'CN'},
    '罗斯福': {'aliases': ['罗斯福'], 'type': '酒类', 'country': 'BE (比利时)'},
    '美可卓': {'aliases': ['美可卓'], 'type': '乳品', 'country': 'AU'},
    '老恒和': {'aliases': ['老恒和'], 'type': '酒类', 'country': 'CN'},
    '脉动': {'aliases': ['脉动'], 'type': '饮料', 'country': 'CN'},
    '舍得': {'aliases': ['舍得'], 'type': '酒类', 'country': 'CN'},
    '艾饰庭': {'aliases': ['艾饰庭'], 'type': '个人清洁', 'country': 'JP'},
    '芝华士': {'aliases': ['芝华士'], 'type': '酒类', 'country': 'GB'},
    '草原领头羊': {'aliases': ['草原领头羊'], 'type': '生鲜', 'country': 'CN'},
    '萨克拉': {'aliases': ['萨克拉'], 'type': '调味', 'country': 'IT'},
    '蒙特斯': {'aliases': ['蒙特斯'], 'type': '酒类', 'country': 'CN'},
    '蓓妮妈妈': {'aliases': ['蓓妮妈妈'], 'type': '乳品', 'country': 'FR'},
    '蓝月亮': {'aliases': ['蓝月亮'], 'type': '个人清洁', 'country': 'CN'},
    '蚝湾': {'aliases': ['蚝湾'], 'type': '酒类', 'country': 'NZ'},
    '蝶矢': {'aliases': ['蝶矢'], 'type': '酒类', 'country': 'JP'},
    '赖茅': {'aliases': ['赖茅'], 'type': '酒类', 'country': 'CN'},
    '越前': {'aliases': ['越前'], 'type': '粮油', 'country': 'JP'},
    '阳帆': {'aliases': ['阳帆'], 'type': '调味', 'country': 'CN'},
    '陈克明': {'aliases': ['陈克明'], 'type': '粮油', 'country': 'CN'},
    '雅漾': {'aliases': ['Avene', 'Avene/雅漾', '雅漾'], 'type': '美妆', 'country': 'FR'},
    '雪碧': {'aliases': ['雪碧', 'Sprite', 'Sprite/雪碧'], 'type': '饮料', 'country': 'CN'},
    '青岛啤酒': {'aliases': ['青岛啤酒'], 'type': '啤酒', 'country': 'CN'},
    '鲁花': {'aliases': ['鲁花'], 'type': '粮油', 'country': 'CN'},
    '鲜美来': {'aliases': ['鲜美来'], 'type': '水产', 'country': 'CN'},
    '麦提莎': {'aliases': ['麦提莎'], 'type': '零食', 'country': 'CN'},

    'Ecover': {'aliases': ['Ecover'], 'type': '日化', 'country': 'CN'},
    'GEMEZ': {'aliases': ['GEMEZ'], 'type': '零食', 'country': 'ID'},
    'Kanro': {'aliases': ['Kanro'], 'type': '糖果', 'country': 'JP'},
    'a2': {'aliases': ['a2'], 'type': '乳品', 'country': 'AU'},
    '万多福': {'aliases': ['万多福', 'Wonderful', 'Wonderful/万多福'], 'type': '零食', 'country': 'US'},
    '万威客': {'aliases': ['万威客'], 'type': '肉制品', 'country': 'CN'},
    '万有全': {'aliases': ['万有全'], 'type': '肉制品', 'country': 'CN'},
    '三佳利': {'aliases': ['三佳利'], 'type': '饮料', 'country': 'JP'},
    '三胖蛋': {'aliases': ['三胖蛋'], 'type': '零食', 'country': 'CN'},
    '不二家': {'aliases': ['不二家'], 'type': '糖果', 'country': 'CN'},
    '乌苏': {'aliases': ['乌苏'], 'type': '酒类', 'country': 'CN'},
    '云雾之湾': {'aliases': ['云雾之湾'], 'type': '酒类', 'country': 'NZ'},
    '优诺': {'aliases': ['优诺'], 'type': '乳品', 'country': 'CN'},
    '佳得乐': {'aliases': ['佳得乐'], 'type': '饮料', 'country': 'CN'},
    '六神': {'aliases': ['六神'], 'type': '驱蚊防虫', 'country': 'CN'},
    '剑南春': {'aliases': ['剑南春'], 'type': '酒类', 'country': 'CN'},
    '劳仑兹': {'aliases': ['劳仑兹'], 'type': '零食', 'country': 'DE'},
    '北冰洋': {'aliases': ['北冰洋'], 'type': '饮料', 'country': 'CN'},
    '华英': {'aliases': ['华英'], 'type': '肉禽蛋', 'country': 'CN'},
    '南翔': {'aliases': ['南翔'], 'type': '面点', 'country': 'CN'},
    '双汇': {'aliases': ['双汇'], 'type': '肉制品', 'country': 'CN'},
    '双鱼': {'aliases': ['双鱼'], 'type': '调味', 'country': 'CN'},
    '可尔必思': {'aliases': ['可尔必思'], 'type': '饮料', 'country': 'JP'},
    '可康': {'aliases': ['可康'], 'type': '糖果', 'country': 'CN'},
    '哈达': {'aliases': ['哈达'], 'type': '饮料', 'country': 'JP'},
    '唯新': {'aliases': ['唯新'], 'type': '肉制品', 'country': 'CN'},
    '嘉云': {'aliases': ['嘉云'], 'type': '糖果', 'country': 'DE'},
    '国台': {'aliases': ['国台'], 'type': '酒类', 'country': 'CN'},
    '塔牌': {'aliases': ['塔牌'], 'type': '酒类', 'country': 'CN'},
    '墨西哥少女': {'aliases': ['墨西哥少女'], 'type': '零食', 'country': 'US'},
    '大字': {'aliases': ['大字'], 'type': '调味', 'country': 'JP'},
    '大益': {'aliases': ['大益'], 'type': '茶饮', 'country': 'CN'},
    '奥美加': {'aliases': ['奥美加'], 'type': '酒类', 'country': 'CN'},
    '娃哈哈': {'aliases': ['娃哈哈'], 'type': '乳品', 'country': 'CN'},
    '孟买': {'aliases': ['孟买'], 'type': '酒类', 'country': 'GB'},
    '宗家府': {'aliases': ['宗家府'], 'type': '酱菜', 'country': 'CN'},
    '宣若': {'aliases': ['宣若'], 'type': '洗护', 'country': 'JP'},
    '尊乐': {'aliases': ['尊乐'], 'type': '肉制品', 'country': 'CN'},
    '尊尼获加': {'aliases': ['尊尼获加'], 'type': '酒类', 'country': 'GB'},
    '尊美醇': {'aliases': ['尊美醇'], 'type': '饮料', 'country': 'IE'},
    '小糊涂仙': {'aliases': ['小糊涂仙'], 'type': '酒类', 'country': 'CN'},
    '屈臣氏': {'aliases': ['屈臣氏'], 'type': '饮料', 'country': 'CN'},
    '布琅兄弟': {'aliases': ['布琅兄弟'], 'type': '酒类', 'country': 'AU'},
    '帝力': {'aliases': ['帝力'], 'type': '酒类', 'country': 'IT'},
    '延世牧场': {'aliases': ['延世牧场'], 'type': '乳品', 'country': 'KR'},
    '必品阁': {'aliases': ['必品阁'], 'type': '面点', 'country': 'CN'},
    '必富达': {'aliases': ['必富达'], 'type': '酒类', 'country': 'GB'},
    '怡宝': {'aliases': ['怡宝'], 'type': '饮用水', 'country': 'CN'},
    '悠哈': {'aliases': ['悠哈'], 'type': '糖果', 'country': 'CN'},
    '扎伊尼': {'aliases': ['扎伊尼'], 'type': '糖果', 'country': 'IT'},
    '月桂冠': {'aliases': ['月桂冠'], 'type': '酒类', 'country': 'JP'},
    '李子柒': {'aliases': ['李子柒'], 'type': '酱料', 'country': 'CN'},
    '杰克丹尼': {'aliases': ['杰克丹尼'], 'type': '酒类', 'country': 'US'},
    '松林': {'aliases': ['松林'], 'type': '粮油', 'country': 'CN'},
    '格兰威特': {'aliases': ['格兰威特'], 'type': '酒类', 'country': 'GB'},
    '格兰菲迪': {'aliases': ['格兰菲迪'], 'type': '酒类', 'country': 'GB'},
    '梅乃宿': {'aliases': ['梅乃宿'], 'type': '酒类', 'country': 'JP'},
    '楼外楼': {'aliases': ['楼外楼'], 'type': '预制菜', 'country': 'CN'},
    '毛铺': {'aliases': ['毛铺'], 'type': '酒类', 'country': 'CN'},
    '水妈妈': {'aliases': ['水妈妈'], 'type': '调味', 'country': 'TH'},
    '沈大成': {'aliases': ['沈大成'], 'type': '餐饮', 'country': 'CN'},
    '泰象': {'aliases': ['泰象'], 'type': '饮料', 'country': 'TH'},
    '海太': {'aliases': ['海太'], 'type': '零食', 'country': 'KR'},
    '海牌': {'aliases': ['海牌'], 'type': '零食', 'country': 'KR'},
    '添加利': {'aliases': ['添加利'], 'type': '酒类', 'country': 'GB'},
    '湖羊': {'aliases': ['湖羊'], 'type': '调味品', 'country': 'CN'},
    '爱士堡': {'aliases': ['爱士堡'], 'type': '酒类', 'country': 'DE'},
    '獭祭': {'aliases': ['獭祭'], 'type': '酒类', 'country': 'JP'},
    '王老吉': {'aliases': ['王老吉'], 'type': '饮料', 'country': 'CN'},
    '理本': {'aliases': ['理本'], 'type': '糖果', 'country': 'JP'},
    '瓦伦丁': {'aliases': ['瓦伦丁'], 'type': '酒类', 'country': 'DE'},
    '白熊': {'aliases': ['白熊'], 'type': '酒类', 'country': 'BE'},
    '白鹤': {'aliases': ['白鹤'], 'type': '酒类', 'country': 'JP'},
    '百加得': {'aliases': ['百加得'], 'type': '酒类', 'country': 'CN'},
    '百岁山': {'aliases': ['百岁山'], 'type': '饮用水', 'country': 'CN'},
    '百龄坛': {'aliases': ['百龄坛'], 'type': '酒类', 'country': 'GB'},
    '皇冠': {'aliases': ['皇冠'], 'type': '零食', 'country': 'CN'},
    '益达': {'aliases': ['益达'], 'type': '糖果', 'country': 'CN'},
    '相模原创': {'aliases': ['相模原创'], 'type': '计生用品', 'country': 'JP'},
    '真露': {'aliases': ['真露'], 'type': '酒类', 'country': 'KR'},
    '督威': {'aliases': ['督威'], 'type': '酒类', 'country': 'BE'},
    '秋山制果': {'aliases': ['秋山制果'], 'type': '糖果', 'country': 'JP'},
    '秋林里道斯': {'aliases': ['秋林里道斯'], 'type': '肉制品', 'country': 'CN'},
    '立丰': {'aliases': ['立丰'], 'type': '肉制品', 'country': 'CN'},
    '纽仕兰牧场': {'aliases': ['纽仕兰牧场'], 'type': '乳品', 'country': 'NZ'},
    '纽澜地': {'aliases': ['纽澜地'], 'type': '肉片肉卷', 'country': 'CN'},
    '绍山鉴水': {'aliases': ['绍山鉴水'], 'type': '酒类', 'country': 'CN'},
    '绝对': {'aliases': ['绝对'], 'type': '酒类', 'country': 'CN'},
    '缸鸭狗': {'aliases': ['缸鸭狗'], 'type': '面点', 'country': 'CN'},
    '美美的花园': {'aliases': ['美美的花园'], 'type': '酒类', 'country': 'IT'},
    '脆香米': {'aliases': ['脆香米'], 'type': '巧克力', 'country': 'CN'},
    '芙华': {'aliases': ['芙华'], 'type': '酒类', 'country': 'FR'},
    '苏格登': {'aliases': ['苏格登'], 'type': '酒类', 'country': 'GB'},
    '苹果西打': {'aliases': ['苹果西打牌'], 'type': '饮料', 'country': 'CN'},
    '莲花': {'aliases': ['莲花'], 'type': '调味', 'country': 'CN'},
    '菲斯奈特': {'aliases': ['菲斯奈特'], 'type': '酒类', 'country': 'CN'},
    '西凤': {'aliases': ['西凤'], 'type': '酒类', 'country': 'CN'},
    '路易雅都': {'aliases': ['路易雅都'], 'type': '酒类', 'country': 'FR'},
    '轩尼诗': {'aliases': ['轩尼诗'], 'type': '酒类', 'country': 'FR'},
    '迷失海岸': {'aliases': ['迷失海岸'], 'type': '酒类', 'country': 'US'},
    '邵万生': {'aliases': ['邵万生'], 'type': '肉制品', 'country': 'CN'},
    '都乐': {'aliases': ['都乐', 'Dole', 'Dole/都乐'], 'type': '水果', 'country': 'PH'},
    '酩悦': {'aliases': ['酩悦'], 'type': '酒类', 'country': 'FR'},
    '金宾': {'aliases': ['金宾'], 'type': '酒类', 'country': 'US'},
    '雪涛': {'aliases': ['雪涛'], 'type': '调味', 'country': 'AU'},
    '雷神': {'aliases': ['雷神'], 'type': '巧克力', 'country': 'JP'},
    '露森': {'aliases': ['露森'], 'type': '酒类', 'country': 'DE'},
    '霸蛮': {'aliases': ['霸蛮'], 'type': '速食', 'country': 'CN'},
    '食族人': {'aliases': ['食族人'], 'type': '速食', 'country': 'CN'},
    '马利宝': {'aliases': ['马利宝'], 'type': '酒类', 'country': 'ES'},
    '马天尼': {'aliases': ['马天尼'], 'type': '酒类', 'country': 'IT'},
    '马爹利': {'aliases': ['马爹利'], 'type': '酒类', 'country': 'FR'},
    '魔爪': {'aliases': ['魔爪'], 'type': '饮料', 'country': 'CN'},
    '鱼泉': {'aliases': ['鱼泉'], 'type': '酱菜', 'country': 'CN'},
    '鹃城牌': {'aliases': ['鹃城牌'], 'type': '调味', 'country': 'CN'},
    '鹅岛': {'aliases': ['鹅岛'], 'type': '酒类', 'country': 'CN'},
    '麴醇堂': {'aliases': ['麴醇堂'], 'type': '酒类', 'country': 'KR'},
    '黄尾袋鼠': {'aliases': ['黄尾袋鼠'], 'type': '酒类', 'country': 'AU'},
    '黄飞红': {'aliases': ['黄飞红'], 'type': '零食', 'country': 'CN'},
    '齐藤': {'aliases': ['齐藤'], 'type': '饮料', 'country': 'JP'},
    '嘉顿': {'aliases': ['嘉顿', 'GARDEN/嘉顿', 'GARDEN'], 'type': '零食', 'country': 'CN'},
    '宾格瑞': {'aliases': ['宾格瑞', 'Binggrae', 'Binggrae/宾格瑞'], 'type': '饮料', 'country': 'KR'},
    '拉菲': {'aliases': ['拉菲', 'Lafite/拉菲', 'Lafite'], 'type': '酒类', 'country': 'CN'},
    '摩可纳': {'aliases': ['摩可纳', 'Moccona/摩可纳', 'Moccona'], 'type': '咖啡', 'country': 'CN'},
    '斧头牌': {'aliases': ['斧头牌', 'AXE', '斧头', 'AXE/斧头牌'], 'type': '日化', 'country': 'CN'},
    'AKOKO': {'aliases': ['AKOKO'], 'type': '零食', 'country': 'CN'},
    'Beretta': {'aliases': ['Beretta'], 'type': '肉制品', 'country': 'CN'},
    'COSTA COFFEE': {'aliases': ['COSTA COFFEE'], 'type': '咖啡', 'country': 'CN'},
    "M&M'S": {'aliases': ["M&M'S"], 'type': '巧克力', 'country': 'US'},
    'Mootaa': {'aliases': ['Mootaa'], 'type': '厨房清洁', 'country': 'CN'},
    'Regenerate': {'aliases': ['Regenerate'], 'type': '口腔', 'country': 'FR'},
    '万字': {'aliases': ['万字'], 'type': '调味', 'country': 'CN'},
    '三岛': {'aliases': ['三岛'], 'type': '调味', 'country': 'CN'},
    '三立': {'aliases': ['三立'], 'type': '巧克力', 'country': 'JP'},
    '三角': {'aliases': ['Toblerone', '三角', 'Toblerone/三角'], 'type': '巧克力', 'country': 'CH'},
    '上好佳': {'aliases': ['上好佳'], 'type': '零食', 'country': 'CN'},
    '中盐': {'aliases': ['中盐'], 'type': '调味', 'country': 'CN'},
    '丸天': {'aliases': ['丸天'], 'type': '调味', 'country': 'JP'},
    '丽尔泰': {'aliases': ['丽尔泰'], 'type': '乳品', 'country': 'TH'},
    '乐家': {'aliases': ['乐家'], 'type': '巧克力', 'country': 'US'},
    '九鬼牌': {'aliases': ['九鬼牌'], 'type': '调味', 'country': 'CN'},
    '五粮液': {'aliases': ['五粮液', '五粮液股份公司'], 'type': '酒类', 'country': 'CN'},
    '京都念慈菴': {'aliases': ['京都念慈菴'], 'type': '糖果', 'country': 'TH'},
    '人头马': {'aliases': ['人头马'], 'type': '酒类', 'country': 'FR'},
    '仲景': {'aliases': ['仲景'], 'type': '酱料', 'country': 'CN'},
    '伯爵': {'aliases': ['Borges/伯爵', 'Borges', '伯爵'], 'type': '调味', 'country': 'ES'},
    '依泉': {'aliases': ['URIAGE', '依泉', 'URIAGE/依泉'], 'type': '美妆', 'country': 'FR'},
    '克特多金象': {'aliases': ['克特多金象', 'COTEDOR/克特多金象', 'COTEDOR'], 'type': '巧克力', 'country': 'BE'},
    '六必居': {'aliases': ['六必居'], 'type': '酱料', 'country': 'CN'},
    '六记雄': {'aliases': ['六记雄'], 'type': '肉禽蛋', 'country': 'CN'},
    '农心': {'aliases': ['农心'], 'type': '速食', 'country': 'CN'},
    '冠生园': {'aliases': ['冠生园'], 'type': '冲调', 'country': 'CN'},
    '利口乐': {'aliases': ['利口乐'], 'type': '糖果', 'country': 'CN'},
    '千禾': {'aliases': ['千禾'], 'type': '调味品', 'country': 'CN'},
    '升元': {'aliases': ['升元'], 'type': '速食', 'country': 'CN'},
    '卡夫': {'aliases': ['卡夫'], 'type': '调味', 'country': 'US'},
    '卡迪那': {'aliases': ['卡迪那'], 'type': '零食', 'country': 'CN'},
    '发之食谱': {'aliases': ['发之食谱'], 'type': '洗护', 'country': 'CN'},
    '可莱美': {'aliases': ['可莱美'], 'type': '海鲜制品', 'country': 'KR'},
    '周生记': {'aliases': ['周生记', '盒马工坊/周生记'], 'type': '熟食', 'country': 'CN'},
    '和華味霸': {'aliases': ['和華味霸'], 'type': '调味', 'country': 'CN'},
    '坛坛乡': {'aliases': ['坛坛乡'], 'type': '酱料', 'country': 'CN'},
    '大喜大': {'aliases': ['大喜大'], 'type': '酱料', 'country': 'CN'},
    '天甜': {'aliases': ['天甜'], 'type': '零食', 'country': 'AU'},
    '太古': {'aliases': ['太古'], 'type': '调味', 'country': 'CN'},
    '好侍': {'aliases': ['好侍'], 'type': '调味', 'country': 'CN'},
    '好欢螺': {'aliases': ['好欢螺'], 'type': '速食', 'country': 'CN'},
    '娜丽丝': {'aliases': ['娜丽丝'], 'type': '美妆', 'country': 'JP'},
    '宝鼎天鱼': {'aliases': ['宝鼎天鱼'], 'type': '调味', 'country': 'CN'},
    '宮武': {'aliases': ['宮武'], 'type': '速食', 'country': 'JP'},
    '家乐氏': {'aliases': ['家乐氏'], 'type': '谷物', 'country': 'TH'},
    '密保诺': {'aliases': ['密保诺'], 'type': '厨房用品', 'country': 'US'},
    '寿桃': {'aliases': ['寿桃'], 'type': '面点', 'country': 'CN'},
    '小白心里软': {'aliases': ['小白心里软'], 'type': '零食', 'country': 'CN'},
    '小胖子': {'aliases': ['小胖子'], 'type': '罐头', 'country': 'TH'},
    '小萨牛牛': {'aliases': ['小萨牛牛'], 'type': '方便食品', 'country': 'CN'},
    '恒顺': {'aliases': ['恒顺'], 'type': '调味', 'country': 'CN'},
    '悦鲜活': {'aliases': ['悦鲜活'], 'type': '乳品', 'country': 'CN'},
    '打嗝海狸': {'aliases': ['打嗝海狸'], 'type': '酒类', 'country': 'US'},
    '拉尼娜': {'aliases': ['拉尼娜'], 'type': '酒类', 'country': '格鲁吉亚'},
    '旺仔': {'aliases': ['旺仔'], 'type': '乳品', 'country': 'CN'},
    '望山楂': {'aliases': ['望山楂'], 'type': '饮料', 'country': 'CN'},
    '杨大爷': {'aliases': ['杨大爷'], 'type': '肉制品', 'country': 'CN'},
    '松永': {'aliases': ['松永'], 'type': '零食', 'country': 'JP'},
    '极美滋': {'aliases': ['极美滋'], 'type': '调味', 'country': 'CN'},
    '柴火大院': {'aliases': ['柴火大院'], 'type': '粮油', 'country': 'CN'},
    '格兰昆奇': {'aliases': ['格兰昆奇'], 'type': '酒类', 'country': 'GB'},
    '格兰特': {'aliases': ['格兰特'], 'type': '乳品', 'country': 'CN'},
    '梅林': {'aliases': ['梅林'], 'type': '罐头', 'country': 'CN'},
    '每日黑巧': {'aliases': ['每日黑巧'], 'type': '巧克力', 'country': 'CN'},
    '沃特堡': {'aliases': ['沃特堡'], 'type': '乳品', 'country': 'CN'},
    '海欣': {'aliases': ['海欣'], 'type': '肉禽蛋', 'country': 'CN'},
    '清净园': {'aliases': ['清净园'], 'type': '酱料', 'country': 'KR'},
    '牛头牌': {'aliases': ['牛头牌'], 'type': '调味', 'country': 'CN'},
    '牧森': {'aliases': ['牧森'], 'type': '乳品', 'country': 'CN'},
    '王守义': {'aliases': ['王守义'], 'type': '调味', 'country': 'CN'},
    '王致和': {'aliases': ['王致和'], 'type': '酱料', 'country': 'CN'},
    '玥之秘': {'aliases': ['玥之秘'], 'type': '美妆', 'country': 'CN'},
    '百威': {'aliases': ['百威'], 'type': '酒类', 'country': 'CN'},
    '百钻': {'aliases': ['百钻'], 'type': '烘焙', 'country': 'CN'},
    '皇上皇': {'aliases': ['皇上皇'], 'type': '肉制品', 'country': 'CN'},
    '碧欧奇': {'aliases': ['碧欧奇'], 'type': '粮油', 'country': 'IT'},
    '碧迪皙': {'aliases': ['碧迪皙', 'pdc', 'pdc/碧迪皙'], 'type': '美妆', 'country': 'JP'},
    '空刻': {'aliases': ['空刻'], 'type': '意面', 'country': 'IT'},
    '索菲亚': {'aliases': ['索菲亚'], 'type': '冰淇淋', 'country': 'CN'},
    '纪州誉': {'aliases': ['纪州誉'], 'type': '酒类', 'country': 'JP'},
    '纳宝帝': {'aliases': ['纳宝帝'], 'type': '零食', 'country': 'ID'},
    '纷乐旗': {'aliases': ['纷乐旗'], 'type': '调味', 'country': 'US'},
    '美好': {'aliases': ['美好'], 'type': '炸烤', 'country': 'CN'},
    '美心': {'aliases': ['美心'], 'type': '零食', 'country': 'HK'},
    '美汁源': {'aliases': ['美汁源'], 'type': '饮料', 'country': 'CN'},
    '老干妈': {'aliases': ['老干妈'], 'type': '调味', 'country': 'CN'},
    '老板仔': {'aliases': ['老板仔'], 'type': '零食', 'country': 'TH'},
    '胡姬花': {'aliases': ['胡姬花'], 'type': '粮油', 'country': 'CN'},
    '自嗨锅': {'aliases': ['自嗨锅'], 'type': '速食', 'country': 'CN'},
    '芙丽芳丝': {'aliases': ['芙丽芳丝', 'freeplus', 'freeplus/芙丽芳丝'], 'type': '美妆', 'country': 'JP'},
    '茉莉莎娜': {'aliases': ['茉莉莎娜'], 'type': '意面', 'country': 'IT'},
    '营多': {'aliases': ['营多'], 'type': '速食', 'country': 'ID'},
    '葱伴侣': {'aliases': ['葱伴侣'], 'type': '酱料', 'country': 'CN'},
    '蓬盛': {'aliases': ['蓬盛'], 'type': '酱菜', 'country': 'CN'},
    '达亦多': {'aliases': ['达亦多'], 'type': '饮料', 'country': 'CN'},
    '郎': {'aliases': ['郎牌/郎', '郎牌', '郎'], 'type': '酒类', 'country': 'CN'},
    '酷乐高': {'aliases': ['ColaCao', 'ColaCao/酷乐高', '酷乐高', ], 'type': '乳品', 'country': 'ES'},
    '酷滋': {'aliases': ['酷滋'], 'type': '糖果', 'country': 'CN'},
    '金葵': {'aliases': ['金葵'], 'type': '酱料', 'country': 'CN'},
    '霍斯湾': {'aliases': ['霍斯湾'], 'type': '饮用水', 'country': 'NZ'},
    '颐参严选': {'aliases': ['颐参严选'], 'type': '海鲜', 'country': 'CN'},
    '飞鹤': {'aliases': ['飞鹤'], 'type': '乳品', 'country': 'CN'},
    '香纳兰': {'aliases': ['香纳兰'], 'type': '粮油', 'country': 'CN'},
    '高庄': {'aliases': ['高庄'], 'type': '面点', 'country': 'CN'},
    '麻辣王子': {'aliases': ['麻辣王子'], 'type': '零食', 'country': 'CN'},
    '黄天鹅': {'aliases': ['黄天鹅'], 'type': '肉禽蛋', 'country': 'CN'},
    '黑白狗': {'aliases': ['黑白狗'], 'type': '酒类', 'country': 'GB'},
    '龙角散': {'aliases': ['龙角散'], 'type': '糖果', 'country': 'JP'},
    '云南白药': {'aliases': ['云南白药'], 'type': '日化', 'country': 'CN'},
    '伊丽莎白雅顿': {'aliases': ['伊丽莎白雅顿'], 'type': '美妆', 'country': 'CN'},
    '众望': {'aliases': ['众望'], 'type': '零食', 'country': 'CN'},
    '名扬': {'aliases': ['名扬'], 'type': '火锅', 'country': 'CN'},
    '奥普瑞': {'aliases': ['奥普瑞'], 'type': '酒类', 'country': 'CN'},
    '川娃子': {'aliases': ['川娃子'], 'type': '酱料', 'country': 'CN'},
    '打嗝海狸牌': {'aliases': ['打嗝海狸牌'], 'type': '酒类', 'country': 'US'},
    '有机一分甘': {'aliases': ['有机一分'], 'type': '蔬菜', 'country': 'CN'},
    '杞里香': {'aliases': ['杞里香'], 'type': '干货', 'country': 'CN'},
    '每日鲜语': {'aliases': ['每日鲜语'], 'type': '乳品', 'country': 'CN'},
    '海格': {'aliases': ['海格'], 'type': '酒类', 'country': 'DE'},
    '狮峰': {'aliases': ['狮峰'], 'type': '茶叶', 'country': 'CN'},
    '碧富': {'aliases': ['碧富'], 'type': '糖果', 'country': 'CN'},
    '祖名': {'aliases': ['祖名'], 'type': '豆制品', 'country': 'CN'},
    '莫罗': {'aliases': ['莫罗'], 'type': '酒类', 'country': 'FR'},
    '阿华田': {'aliases': ['阿华田'], 'type': '乳品', 'country': 'CN'},
    '无名小卒': {'aliases': ['无名小卒'], 'type': '零食', 'country': 'CN'},
    '温柔山丘': {'aliases': ['温柔山丘'], 'type': '酒类', 'country': 'DE'},
    '红飞鹰': {'aliases': ['红飞鹰'], 'type': '调味', 'country': 'TH'},
    '艾美尼亚': {'aliases': ['艾美尼亚'], 'type': '饮料', 'country': 'ES'},
    '蒂李秀喜': {'aliases': ['蒂李秀喜'], 'type': '净菜', 'country': 'CN'},
    'DONCKELS': {'aliases': ['DONCKELS'], 'type': '巧克力', 'country': 'CN'},
    '三宝乐': {'aliases': ['三宝乐'], 'type': '酒类', 'country': 'JP'},
    '丝塔芙': {'aliases': ['丝塔芙'], 'type': '美妆', 'country': 'CN'},
    '可复美': {'aliases': ['可复美'], 'type': '美妆', 'country': 'CN'},
    '哈尔滨': {'aliases': ['哈尔滨'], 'type': '酒类', 'country': 'CN'},
    '敷尔佳': {'aliases': ['敷尔佳'], 'type': '美妆', 'country': 'CN'},
    '桂格': {'aliases': ['桂格'], 'type': '乳品', 'country': 'CN'},

    '美极': {'aliases': ['美极'], 'type': '调味', 'country': 'CN'},
    '花之舞': {'aliases': ['花之舞'], 'type': '酒类', 'country': 'JP'},
    '趣多多': {'aliases': ['趣多多'], 'type': '零食', 'country': 'CN'},
    'DJ&A': {'aliases': ['DJ&A'], 'type': '零食', 'country': 'AU'},
    '客唻美': {'aliases': ['客唻美'], 'type': '海鲜制品', 'country': 'KR'},
    '斯米诺': {'aliases': ['斯米诺'], 'type': '酒类', 'country': 'GB'},
    '爱顿博格': {'aliases': ['Anthon Berg', 'Anthon Berg/爱顿博格', '爱顿博格'], 'type': '巧克力', 'country': 'PL'},
    '甘源': {'aliases': ['甘源'], 'type': '零食', 'country': 'CN'},
    '红帽子': {'aliases': ['红帽子'], 'type': '零食', 'country': 'JP'},
    '船歌': {'aliases': ['船歌'], 'type': '面点', 'country': 'CN'},
    '艾达的世界': {'aliases': ['艾达的世界'], 'type': '巧克力', 'country': 'IT'},
    '莫顿': {'aliases': ['莫顿'], 'type': '调味', 'country': 'CN'},
    '托斯纳': {'aliases': ['莱贝克', '莱贝克', '托斯纳', '红五星'], 'type': '酒类', 'country': 'AU'},
     '3M': {'aliases': ['3M思高'], 'type': '日化', 'country': 'CN'},
    'FINUTE': {'aliases': ['FINUTE'], 'type': '零食', 'country': 'KR'},
    '三只猴子': {'aliases': ['三只猴子'], 'type': '酒类', 'country': 'CN'},
    '元気森林': {'aliases': ['元気森林'], 'type': '饮料', 'country': 'CN'},
    '刺猬阿甘': {'aliases': ['刺猬阿甘'], 'type': '零食', 'country': 'CN'},
    '博为雅': {'aliases': ['博为雅'], 'type': '酒类', 'country': 'FR'},
    '卡内斯': {'aliases': ['卡内斯'], 'type': '粮油', 'country': 'JP'},
    '哈瑞宝': {'aliases': ['哈瑞宝'], 'type': '糖果', 'country': 'TR'},
    '喜茶': {'aliases': ['喜茶'], 'type': '饮料', 'country': 'CN'},
    '圣玛丽酒庄老藤': {'aliases': ['圣玛丽酒庄'], 'type': '酒类', 'country': 'FR'},
    '夜肆': {'aliases': ['夜肆'], 'type': '酒类', 'country': 'CN'},
    '好望水': {'aliases': ['好望水'], 'type': '饮料', 'country': 'CN'},
    '妮飘': {'aliases': ['nepia', 'nepia/妮飘', '妮飘'], 'type': '日化', 'country': 'CN'},
    '广州酒家': {'aliases': ['广州酒家'], 'type': '食品', 'country': 'CN'},
     '意味乐': {'aliases': ['意味乐'], 'type': '酱料', 'country': 'ES'},
    '拉芳罗榭': {'aliases': ['拉芳罗榭'], 'type': '酒类', 'country': 'FR'},
    '斐素': {'aliases': ['斐素'], 'type': '饮料', 'country': 'CN'},
    '朝日唯品': {'aliases': ['朝日唯品'], 'type': '乳品', 'country': 'CN'},
    '果子熟了': {'aliases': ['果子熟了'], 'type': '饮料', 'country': 'CN'},
    '桑戈利亚': {'aliases': ['桑戈利亚'], 'type': '饮料', 'country': 'JP'},
    '梅见': {'aliases': ['梅见'], 'type': '酒类', 'country': 'CN'},
    '正洋': {'aliases': ['正洋'], 'type': '预制菜', 'country': 'CN'},
    '泰氏妈妈': {'aliases': ['泰氏妈妈'], 'type': '速食', 'country': 'TH'},
    '洛神山庄': {'aliases': ['洛神山庄'], 'type': '酒类', 'country': 'CN'},
    '潭牛': {'aliases': ['潭牛'], 'type': '肉禽蛋', 'country': 'CN'},
    '潮汕集锦': {'aliases': ['潮汕集锦'], 'type': '调味品', 'country': 'CN'},
    '特仑苏': {'aliases': ['特仑苏'], 'type': '乳品', 'country': 'CN'},
    '王家渡': {'aliases': ['王家渡'], 'type': '肉制品', 'country': 'CN'},
    '王小卤': {'aliases': ['王小卤'], 'type': '零食', 'country': 'CN'},
    '珂润': {'aliases': ['珂润'], 'type': '美妆', 'country': 'JP'},
    '白象': {'aliases': ['白象'], 'type': '速食', 'country': 'CN'},
    '美珍香': {'aliases': ['美珍香'], 'type': '肉制品', 'country': 'CN'},
    '能多益': {'aliases': ['能多益'], 'type': '零食', 'country': 'DE'},
    '茄皇': {'aliases': ['茄皇'], 'type': '速食', 'country': 'CN'},
    '蝴蝶兰': {'aliases': ['喜悦兰'], 'type': '花卉', 'country': 'CN'},
    '趣莱福': {'aliases': ['趣莱福'], 'type': '零食', 'country': 'KR'},
    '阿麦斯': {'aliases': ['阿麦斯'], 'type': '糖果', 'country': 'CN'},
    '青佑': {'aliases': ['青佑'], 'type': '零食', 'country': 'KR'},
    '马尔堡': {'aliases': ['马尔堡'], 'type': '酒类', 'country': 'NZ'},
    '鲜得来': {'aliases': ['鲜得来'], 'type': '半成品', 'country': 'CN'},
    'MAXICORN': {'aliases': ['MAXICORN'], 'type': '零食', 'country': 'ID'},
    'ZUO一下': {'aliases': ['ZUO一下'], 'type': '糖果', 'country': 'CN'},
    '三人食品': {'aliases': ['三人食品'], 'type': '酱料', 'country': 'CN'},
    '东湖': {'aliases': ['东湖'], 'type': '调味', 'country': 'CN'},
    '丹碧丝': {'aliases': ['丹碧丝', 'TAMPAX', 'TAMPAX/丹碧丝'], 'type': '护理', 'country': 'HU'},
    '九生堂': {'aliases': ['九生堂'], 'type': '半成品', 'country': 'CN'},
    '亲民食品': {'aliases': ['亲民食品'], 'type': '粮油', 'country': 'CN'},
    '亲热': {'aliases': ['亲热'], 'type': '肉禽蛋', 'country': 'CN'},
    '佳农': {'aliases': ['佳农'], 'type': '水果', 'country': 'CN'},
    '兰格格': {'aliases': ['兰格格'], 'type': '乳品', 'country': 'CN'},
    '兰芳园': {'aliases': ['兰芳园'], 'type': '饮料', 'country': 'CN'},
    '冶春': {'aliases': ['冶春'], 'type': '面点', 'country': 'CN'},
    '出前一丁': {'aliases': ['出前一丁'], 'type': '速食', 'country': 'HK'},
    '千焙屋': {'aliases': ['千焙屋'], 'type': '烘焙', 'country': 'CN'},
    '卢正浩': {'aliases': ['卢正浩'], 'type': '茶叶', 'country': 'CN'},
    '吾岛': {'aliases': ['吾岛'], 'type': '乳品', 'country': 'CN'},
    '咸亨': {'aliases': ['咸亨'], 'type': '调味', 'country': 'CN'},
    '嘉士伯': {'aliases': ['嘉士伯'], 'type': '酒类', 'country': 'CN'},
    '夏桐': {'aliases': ['夏桐'], 'type': '酒类', 'country': 'CN'},
    '天润': {'aliases': ['天润'], 'type': '乳品', 'country': 'CN'},
    '太太乐': {'aliases': ['太太乐'], 'type': '调味', 'country': 'CN'},
    '奈雪の茶': {'aliases': ['奈雪の茶'], 'type': '饮料', 'country': 'CN'},
    '好人家': {'aliases': ['好人家'], 'type': '汤底', 'country': 'CN'},
    '如意三宝': {'aliases': ['如意三宝'], 'type': '半成品', 'country': 'CN'},
    '宛禾': {'aliases': ['宛禾'], 'type': '速食', 'country': 'CN'},
    '富维克': {'aliases': ['富维克'], 'type': '饮用水', 'country': 'FR'},
    '寰彼极': {'aliases': ['寰彼极'], 'type': '饮用水', 'country': 'NZ'},
    '帝门': {'aliases': ['帝门'], 'type': '饮料', 'country': 'US'},
    '度小月': {'aliases': ['度小月'], 'type': '面点', 'country': 'TW'},
    '廿一研食社': {'aliases': ['廿一研食社'], 'type': '零食', 'country': 'CN'},
    '张力生': {'aliases': ['张力生'], 'type': '半成品', 'country': 'CN'},
    '张宝记': {'aliases': ['张宝记'], 'type': '熟食', 'country': 'CN'},
    '德哈森长发公主': {'aliases': ['德哈森'], 'type': '酒类', 'country': 'DE'},
    '思高': {'aliases': ['Scotch-Brite', '思高', 'Scotch-Brite/思高', '3M 思高'], 'type': '日化', 'country': 'CN'},
    '惠和': {'aliases': ['惠和'], 'type': '蔬菜', 'country': 'CN'},
    '成就人': {'aliases': ['成就人'], 'type': '速食', 'country': 'CN'},
    '拉图嘉利': {'aliases': ['拉图嘉利酒庄'], 'type': '酒类', 'country': 'FR'},
    '拉图飞卓': {'aliases': ['拉图'], 'type': '酒类', 'country': 'FR'},
    '月盛斋': {'aliases': ['月盛斋'], 'type': '熟食', 'country': 'CN'},
    '李窖主': {'aliases': ['李窖主'], 'type': '酱菜', 'country': 'CN'},
    '松鲜鲜': {'aliases': ['松鲜鲜'], 'type': '调味品', 'country': 'CN'},
    '桃之硕硕玛尔维萨': {'aliases': ['桃之硕硕'], 'type': '酒类', 'country': 'IT'},
    '每食富': {'aliases': ['MasterFoods/每食富', '每食富', 'MasterFoods'], 'type': '酱料', 'country': 'AU'},
    '江中猴姑': {'aliases': ['江中'], 'type': '乳品', 'country': 'CN'},
    '泸溪河': {'aliases': ['泸溪河'], 'type': '糕点', 'country': 'CN'},
    '润心': {'aliases': ['润心'], 'type': '粮油', 'country': 'CN'},
    '添加力': {'aliases': ['添加力'], 'type': '酒类', 'country': 'GB'},
    '溜溜梅': {'aliases': ['溜溜梅'], 'type': '零食', 'country': 'CN'},
    '满小饱': {'aliases': ['满小饱'], 'type': '速食', 'country': 'CN'},
    '满汉大餐': {'aliases': ['满汉大餐'], 'type': '速食', 'country': 'CN'},
    '瀛泉': {'aliases': ['瀛泉'], 'type': '调味品', 'country': 'CN'},
    '牛栏山': {'aliases': ['牛栏山'], 'type': '酒类', 'country': 'CN'},
    '瑞士三角': {'aliases': ['瑞士三角'], 'type': '零食', 'country': 'CN'},
    '百山祖': {'aliases': ['百山祖'], 'type': '酱料', 'country': 'CN'},
    '盒咖啡': {'aliases': ['盒咖啡'], 'type': '咖啡', 'country': 'CN'},
    '知味观': {'aliases': ['知味观'], 'type': '面点', 'country': 'CN'},
    '禧美海产': {'aliases': ['禧美海产'], 'type': '水产', 'country': 'CN'},
     '纽康特': {'aliases': ['纽康特'], 'type': '乳品', 'country': 'GB'},
     '绿柳居': {'aliases': ['绿柳居'], 'type': '熟食', 'country': 'CN'},
    '臭宝': {'aliases': ['臭宝'], 'type': '速食', 'country': 'CN'},
    '舒肤佳': {'aliases': ['Safeguard', '舒肤佳', 'Safeguard/舒肤佳'], 'type': '日化', 'country': 'CN'},
    '芙力': {'aliases': ['芙力'], 'type': '酒类', 'country': 'BE'},
    '英贝健': {'aliases': ['英贝健'], 'type': '饮料', 'country': 'CN'},
    '葡刻': {'aliases': ['葡刻'], 'type': '酒类', 'country': 'CN'},
    '蒙大菲': {'aliases': ['蒙大菲'], 'type': '酒类', 'country': 'US'},
    '蔻多乐': {'aliases': ['蔻多乐'], 'type': '粮油', 'country': 'IT'},
    '藤桥': {'aliases': ['藤桥'], 'type': '零食', 'country': 'CN'},
    '虎邦': {'aliases': ['虎邦'], 'type': '酱料', 'country': 'CN'},
    '让茶': {'aliases': ['让茶'], 'type': '饮料', 'country': 'CN'},
    '谢裕大': {'aliases': ['谢裕大'], 'type': '茶叶', 'country': 'CN'},
    '轩妈': {'aliases': ['轩妈'], 'type': '糕点', 'country': 'CN'},
    '辉英喜达': {'aliases': ['辉英喜达'], 'type': '速食', 'country': 'ID'},
    '达芬奇': {'aliases': ['达芬奇'], 'type': '乳品', 'country': 'CN'},
    '远洋全清': {'aliases': ['远洋'], 'type': '海鲜', 'country': 'CN'},
    '野格': {'aliases': ['野格'], 'type': '酒类', 'country': 'DE'},
    '颜外': {'aliases': ['颜外'], 'type': '方便食品', 'country': 'CN'},
    '马尔堡起源': {'aliases': ['起源'], 'type': '酒类', 'country': 'NZ'},
    '麦卡伦': {'aliases': ['麦卡伦'], 'type': '酒类', 'country': 'GB'},
    '麦肯': {'aliases': ['麦肯'], 'type': '半成品', 'country': 'CN'},
    '云南玫瑰洛神': {'aliases': ['云南玫瑰洛神'], 'type': '花卉', 'country': 'CN'},
    '同仁堂': {'aliases': ['同仁堂'], 'type': '药食', 'country': 'CN'},
    '巧兮兮': {'aliases': ['巧兮兮'], 'type': '零食', 'country': 'CN'},
    '松鹤楼': {'aliases': ['松鹤楼'], 'type': '餐饮', 'country': 'CN'},
     '涞可': {'aliases': ['涞可'], 'type': '零食', 'country': 'KR'},
     '胡庆余堂': {'aliases': ['胡庆余堂'], 'type': '药食', 'country': 'CN'},
    '贝纳丝': {'aliases': ['贝纳丝'], 'type': '巧克力', 'country': 'MY'},
    '野村': {'aliases': ['野村'], 'type': '零食', 'country': 'JP'},
    '食光往事': {'aliases': ['食光往事'], 'type': '干货调料', 'country': 'CN'},
    'ARCTiQUE': {'aliases': ['ARCTiQUE'], 'type': '海鲜制品', 'country': 'CN'},
    'Hipapa': {'aliases': ['Hipapa', 'Hi!papa', 'Hi!papa/Hipapa/海龟爸爸'], 'type': '美妆', 'country': 'CN'},
    "Hunter's": {'aliases': ["Hunter's"], 'type': '零食', 'country': 'AE'},
    'KIYOMOTO': {'aliases': ['KIYOMOTO'], 'type': '洗护', 'country': 'JP'},
    'SAPPORO': {'aliases': ['SAPPORO'], 'type': '酒类', 'country': 'JP'},
    'So Acai': {'aliases': ['So Acai'], 'type': '乳品', 'country': 'CN'},
    'Surf': {'aliases': ['Surf'], 'type': '饮料', 'country': 'JP'},
    'better me': {'aliases': ['better me'], 'type': '半成品', 'country': 'CN'},
    '七喜': {'aliases': ['七喜'], 'type': '饮料', 'country': 'CN'},
    '久久丫': {'aliases': ['久久丫'], 'type': '熟食', 'country': 'CN'},
    '乐达学糖': {'aliases': ['乐达学糖'], 'type': '糖果', 'country': 'CN'},
    '五香居': {'aliases': ['五香居'], 'type': '熟食', 'country': 'CN'},
    '伊藤园': {'aliases': ['伊藤园'], 'type': '饮料', 'country': 'CN'},
    '冰水屋牌': {'aliases': ['冰水屋牌'], 'type': '冰淇淋', 'country': 'JP'},
    '冻颜密码': {'aliases': ['冻颜密码'], 'type': '饮料', 'country': 'CN'},
    '凯斯博士': {'aliases': ['凯斯博士'], 'type': '口腔', 'country': 'US'},
    '台源': {'aliases': ['台源'], 'type': '酒类', 'country': 'CN'},
    '品利': {'aliases': ['品利'], 'type': '粮油', 'country': 'CN'},
    '哈纳斯乳业': {'aliases': ['哈纳斯乳业'], 'type': '乳品', 'country': 'CN'},
    '哈纳斯牧场': {'aliases': ['哈纳斯牧场'], 'type': '冲饮', 'country': 'CN'},
    '壮元海': {'aliases': ['壮元海'], 'type': '海鲜', 'country': 'CN'},
    '多力': {'aliases': ['多力'], 'type': '粮油', 'country': 'CN'},
    '大森屋': {'aliases': ['大森屋'], 'type': '干货调料', 'country': 'CN'},
    '安吉丽娜': {'aliases': ['Andorinha', '安吉丽娜', 'Andorinha/安吉丽娜'], 'type': '粮油', 'country': 'CN'},
    '安达露西': {'aliases': ['安达露西', 'Andasaludsia', 'Andasaludsia/安达露西'], 'type': '粮油', 'country': 'CN'},
    '宝制果': {'aliases': ['宝制果'], 'type': '零食', 'country': 'JP'},
    '广合': {'aliases': ['广合'], 'type': '酱料', 'country': 'CN'},
    '康乃馨': {'aliases': ['康乃馨'], 'type': '花卉', 'country': 'CN'},
    '张宝记土鸡小馆': {'aliases': ['张宝记土鸡小馆'], 'type': '熟食', 'country': 'CN'},
    '张琪寿': {'aliases': ['张琪寿'], 'type': '零食', 'country': 'CN'},
    '斯味特拉': {'aliases': ['斯味特拉'], 'type': '冰淇淋', 'country': 'RU'},
    '日晷谷': {'aliases': ['日晷谷'], 'type': '酒类', 'country': 'DE'},
    '日香': {'aliases': ['日香'], 'type': '零食', 'country': 'TW'},
    '春日井': {'aliases': ['春日井'], 'type': '糖果', 'country': 'JP'},
    '有友': {'aliases': ['有友'], 'type': '零食', 'country': 'CN'},
    '札幌': {'aliases': ['札幌'], 'type': '酒类', 'country': 'JP'},
    '朵娜贝拉': {'aliases': ['Dorabella/朵娜贝拉', '朵娜贝拉', 'Dorabella'], 'type': '巧克力', 'country': 'BE'},
    '林一二': {'aliases': ['林一二'], 'type': '冰淇淋', 'country': 'JP'},
    '柠檬共和国': {'aliases': ['柠檬共和国'], 'type': '饮料', 'country': 'CN'},
    '横沙优品': {'aliases': ['横沙优品'], 'type': '粮油', 'country': 'CN'},
    '泰斯卡': {'aliases': ['泰斯卡'], 'type': '酒类', 'country': 'GB'},
    '海飞丝': {'aliases': ['海飞丝'], 'type': '洗护', 'country': 'CN'},
    '玫瑰洛神': {'aliases': ['玫瑰洛神'], 'type': '花卉', 'country': 'CN'},
     '理肤泉': {'aliases': ['理肤泉'], 'type': '美妆', 'country': 'CN'},
     '盒马X北京同仁堂': {'aliases': ['盒马X北京同仁堂'], 'type': '汤底', 'country': 'CN'},
    '福临门': {'aliases': ['福临门'], 'type': '粮油', 'country': 'CN'},
    '福佳': {'aliases': ['福佳'], 'type': '酒类', 'country': 'CN'},
    '第6感': {'aliases': ['第6感'], 'type': '计生用品', 'country': 'TH'},
    '绝世': {'aliases': ['绝世'], 'type': '肉禽蛋', 'country': 'CN'},
    '维果清': {'aliases': ['维果清'], 'type': '饮料', 'country': 'CN'},
    '美素佳儿': {'aliases': ['美素佳儿', 'Friso', 'Friso/美素佳儿'], 'type': '乳品', 'country': 'NL'},
    '老徽乡': {'aliases': ['老徽乡'], 'type': '半成品', 'country': 'CN'},
    '舒洁': {'aliases': ['舒洁'], 'type': '纸品', 'country': 'CN'},
    '舒适达': {'aliases': ['舒适达'], 'type': '口腔', 'country': 'CN'},
    '艺杏': {'aliases': ['艺杏'], 'type': '豆制品', 'country': 'CN'},
    '蜂解': {'aliases': ['蜂解'], 'type': '饮料', 'country': 'CN'},
    '轻食兽': {'aliases': ['轻食兽'], 'type': '零食', 'country': 'CN'},
    '逐本': {'aliases': ['逐本'], 'type': '美妆', 'country': 'CN'},
    '野人日记': {'aliases': ['野人日记'], 'type': '半成品', 'country': 'CN'},
    '饭乎': {'aliases': ['饭乎'], 'type': '方便食品', 'country': 'CN'},
    '馥绿德雅': {'aliases': ['馥绿德雅'], 'type': '洗护', 'country': 'FR'},
    '鳄鱼山先生': {'aliases': ['鳄鱼山先生'], 'type': '零食', 'country': 'CN'},
    '麻六记': {'aliases': ['麻六记'], 'type': '速食', 'country': 'CN'},
    '鼎味泰': {'aliases': ['鼎味泰'], 'type': '半成品', 'country': 'CN'},
    '龙垦人': {'aliases': ['龙垦人'], 'type': '冲饮', 'country': 'CN'},
    '龙帮': {'aliases': ['龙帮'], 'type': '零食', 'country': 'CN'},
    '晟麦': {'aliases': ['晟麦'], 'type': '粮油', 'country': 'CN'},
    "I'm bruno": {'aliases': ["I'm bruno"], 'type': '零食', 'country': 'TH'},
    '可果美': {'aliases': ['Kagome', '可果美', '野菜生活'], 'type': '饮料', 'country': 'JP'},
    'Totaste': {'aliases': ['Totaste'], 'type': '零食', 'country': 'CN'},
    '口力': {'aliases': ['口力'], 'type': '糖果', 'country': 'DE'},
    '汤达人': {'aliases': ['汤达人'], 'type': '速食', 'country': 'CN'},

    '水深深': {'aliases': ['水深深'], 'type': '美妆', 'country': 'CN'},
    '盒马·风': {'aliases': ['盒马·风'], 'type': '海鲜', 'country': 'CN'},
    '盒马工坊X一米八': {'aliases': ['一米八', '盒马工坊X一米八', '一米八/盒马工坊X一米八'], 'type': '海鲜', 'country': 'CN'},
    '盒马树上熟': {'aliases': ['盒马树上熟'], 'type': '水果', 'country': 'CN'},
    '菌菇星球': {'aliases': ['菌菇星球'], 'type': '蔬菜', 'country': 'CN'},
    'Coles': {'aliases': ['Coles'], 'type': '烘焙', 'country': 'CN'},
    'OH MyFood': {'aliases': ['OH MyFood'], 'type': '冲调', 'country': 'CN'},
    '三顿半': {'aliases': ['三顿半'], 'type': '咖啡', 'country': 'CN'},
    '元气满满': {'aliases': ['元气满满'], 'type': '饮料', 'country': 'CN'},
    '回味一梦': {'aliases': ['回味一梦'], 'type': '零食', 'country': 'CN'},
    '宝珠': {'aliases': ['宝珠'], 'type': '饮料', 'country': 'CN'},
    '小熊驾到': {'aliases': ['小熊驾到'], 'type': '调味', 'country': 'CN'},
    '春彧记': {'aliases': ['春彧记'], 'type': '酱料', 'country': 'CN'},
    '暴肌独角兽': {'aliases': ['暴肌独角兽'], 'type': '零食', 'country': 'CN'},
    '朕宅': {'aliases': ['朕宅'], 'type': '面点', 'country': 'CN'},
    '盒马X哔哩哔哩': {'aliases': ['盒马X哔哩哔哩'], 'type': '零食', 'country': 'CN'},
    '盒马X豆西子': {'aliases': ['豆西子/盒马X豆西子', '盒马X豆西子', '豆西子'], 'type': '蔬菜', 'country': 'CN'},
    '绽家': {'aliases': ['Lycocelle', '绽家', 'Lycocelle/绽家'], 'type': '个人清洁', 'country': 'CN'},
    '翡马': {'aliases': ['翡马'], 'type': '酒类', 'country': 'FR'},
    '莫其托': {'aliases': ['莫其托'], 'type': '酒类', 'country': 'CN'},
    '雪花': {'aliases': ['雪花'], 'type': '酒类', 'country': 'CN'},
    '露比黎登': {'aliases': ['露比黎登'], 'type': '美妆', 'country': 'KR'},
    '鱼极': {'aliases': ['鱼极'], 'type': '冷冻食品', 'country': 'CN'},
    'Bello Vitahouse': {'aliases': ['Bello Vitahouse'], 'type': '肉制品', 'country': 'CN'},
    'BelloVITAHOUSE': {'aliases': ['BelloVITAHOUSE'], 'type': '巧克力', 'country': 'FR'},
    'FFIT8': {'aliases': ['FFIT8'], 'type': '零食', 'country': 'CN'},
    'HELLO KITTY': {'aliases': ['HELLO KITTY'], 'type': '饮用水', 'country': 'TH'},
    'KUMO KUMO': {'aliases': ['KUMO KUMO'], 'type': '零食', 'country': 'CN'},
    'Natural One': {'aliases': ['Natural One'], 'type': '饮料', 'country': 'BR'},
    'Popcorners': {'aliases': ['Popcorners'], 'type': '零食', 'country': 'CN'},
    '东甲粮仓': {'aliases': ['东甲粮仓'], 'type': '茶叶', 'country': 'CN'},
    '乐淇': {'aliases': ['Rockit/乐淇', '乐淇', 'Rockit'], 'type': '水果', 'country': 'NZ'},
    '会稽山': {'aliases': ['会稽山'], 'type': '酒类', 'country': 'CN'},
    '兔头妈妈': {'aliases': ['兔头妈妈'], 'type': '美妆', 'country': 'CN'},
    '华山牧场': {'aliases': ['华山牧场'], 'type': '乳品', 'country': 'CN'},
    '和情': {'aliases': ['和情'], 'type': '零食', 'country': 'BE'},
    '坦普特': {'aliases': ['坦普特'], 'type': '酒类', 'country': 'CN'},
    '外星人': {'aliases': ['外星人'], 'type': '饮料', 'country': 'CN'},
    '天堂': {'aliases': ['天堂'], 'type': '百货', 'country': 'CN'},
    '太阳谷': {'aliases': ['太阳谷'], 'type': '半成品', 'country': 'CN'},
    '安琪': {'aliases': ['安琪'], 'type': '烘焙', 'country': 'CN'},
    '宏源': {'aliases': ['宏源'], 'type': '糖果', 'country': 'CN'},
    '小胡鸭': {'aliases': ['小胡鸭'], 'type': '零食', 'country': 'CN'},
    '水手老爸': {'aliases': ['水手老爸'], 'type': '零食', 'country': 'CN'},
    '泉利堂': {'aliases': ['泉利堂'], 'type': '零食', 'country': 'CN'},
    '法兰希': {'aliases': ['法兰希'], 'type': '乳品', 'country': 'FR'},
    '清香壹号': {'aliases': ['清香壹号'], 'type': '酒类', 'country': 'CN'},
    '渔参乐': {'aliases': ['渔参乐'], 'type': '海鲜', 'country': 'CN'},
    '港荣': {'aliases': ['港荣'], 'type': '零食', 'country': 'CN'},
    '珍宝珠': {'aliases': ['珍宝珠'], 'type': '糖果', 'country': 'CN'},
    '百吉福': {'aliases': ['百吉福'], 'type': '乳品', 'country': 'CN'},
    '盐中甜': {'aliases': ['盐中甜'], 'type': '酱菜', 'country': 'CN'},
    '盐津铺子': {'aliases': ['盐津铺子'], 'type': '零食', 'country': 'CN'},
    '盒漫漫': {'aliases': ['盒漫漫'], 'type': '肉片肉卷', 'country': 'AU'},
    '盒马酩品': {'aliases': ['盒马酩品'], 'type': '酒类', 'country': 'FR'},
    '缪可': {'aliases': ['缪可'], 'type': '酒类', 'country': 'CN'},
    '老盛昌': {'aliases': ['老盛昌'], 'type': '面点', 'country': 'CN'},
    '臻夫子': {'aliases': ['臻夫子'], 'type': '零食', 'country': 'CN'},
    '若渴': {'aliases': ['若渴'], 'type': '酒类', 'country': 'CN'},
    '蜜丝婷': {'aliases': ['蜜丝婷'], 'type': '美妆', 'country': 'CN'},
    '贝欧宝': {'aliases': ['贝欧宝'], 'type': '糖果', 'country': 'CN'},
    '金色琥珀': {'aliases': ['金色琥珀'], 'type': '乳品', 'country': 'CN'},
    '鹰金钱': {'aliases': ['鹰金钱'], 'type': '罐头', 'country': 'CN'},
    'Clearwater': {'aliases': ['Clearwater'], 'type': '海鲜', 'country': 'CN'},
    'Hamlet': {'aliases': ['Hamlet'], 'type': '巧克力', 'country': 'BE'},
    'JAKE': {'aliases': ['JAKE'], 'type': '糖果', 'country': 'CN'},
    'Onlytree': {'aliases': ['Onlytree'], 'type': '饮料', 'country': 'CN'},
    'PH': {'aliases': ['Positivehotel', 'Positivehotel/PH', 'PH'], 'type': '咖啡', 'country': 'CN'},
    'Sol Mujer': {'aliases': ['Sol Mujer'], 'type': '零食', 'country': 'US'},
    '五谷磨房': {'aliases': ['五谷磨房'], 'type': '乳品', 'country': 'CN'},
    '今麦郎': {'aliases': ['今麦郎'], 'type': '速食', 'country': 'CN'},
    '克恩兹': {'aliases': ['克恩兹'], 'type': '零食', 'country': 'ID'},
    '华文冰室': {'aliases': ['华文冰室'], 'type': '饮料', 'country': 'MY'},
    '南江桥': {'aliases': ['南江桥'], 'type': '零食', 'country': 'CN'},
    '和田宽': {'aliases': ['和田宽'], 'type': '调味', 'country': 'JP'},
    '士力架': {'aliases': ['士力架'], 'type': '巧克力', 'country': 'CN'},
    '大关': {'aliases': ['大关'], 'type': '酒类', 'country': 'JP'},
    '富翁': {'aliases': ['富翁'], 'type': '酒类', 'country': 'JP'},
    '小梅屋': {'aliases': ['小梅屋'], 'type': '零食', 'country': 'CN'},
    '拉博丝特': {'aliases': ['拉博丝特'], 'type': '酒类', 'country': 'CN'},
    '李海龙': {'aliases': ['李海龙'], 'type': '方便食品', 'country': 'CN'},
    '沃隆': {'aliases': ['沃隆'], 'type': '坚果', 'country': 'CN'},
    '炭纪': {'aliases': ['炭纪'], 'type': '饮料', 'country': 'CN'},
    '特酷': {'aliases': ['特酷'], 'type': '巧克力', 'country': 'CN'},
    '疆合玉妃': {'aliases': ['疆合玉妃'], 'type': '粮油', 'country': 'CN'},
    '盒马工坊XCP正大食品': {'aliases': ['盒马工坊XCP正大食品'], 'type': '熟食', 'country': 'CN'},
    '科罗娜': {'aliases': ['科罗娜'], 'type': '酒类', 'country': 'CN'},
    '米惦': {'aliases': ['米惦'], 'type': '零食', 'country': 'CN'},
    '自然派': {'aliases': ['自然派'], 'type': '零食', 'country': 'CN'},
    '芭蜂': {'aliases': ['芭蜂'], 'type': '零食', 'country': 'KR'},
    '茶小开': {'aliases': ['茶小开'], 'type': '饮料', 'country': 'CN'},
    '蔬果园': {'aliases': ['蔬果园'], 'type': '厨房清洁', 'country': 'CN'},
    '诺思乐': {'aliases': ['诺思乐'], 'type': '零食', 'country': 'ID'},
    '金门一条根': {'aliases': ['金门一条根'], 'type': '护理', 'country': 'CN'},
    '钱家香': {'aliases': ['钱家香'], 'type': '零食', 'country': 'CN'},
    '黑色经典': {'aliases': ['黑色经典'], 'type': '零食', 'country': 'CN'},
    '徐福记': {'aliases': ['徐福记'], 'type': '零食', 'country': 'CN'},
    '有意酥': {'aliases': ['有意酥'], 'type': '零食', 'country': 'CN'},
    '薯袋仔': {'aliases': ['薯袋仔'], 'type': '零食', 'country': 'MY'},
    'JEKO&JEKO': {'aliases': ['JEKO&JEKO'], 'type': '厨具', 'country': 'CN'},
    'JUWOW': {'aliases': ['JUWOW'], 'type': '美妆', 'country': 'CN'},
    'Piuaemi': {'aliases': ['Piuaemi'], 'type': '饮料', 'country': 'VN'},
    "TALA'S": {'aliases': ["TALA'S"], 'type': '零食', 'country': 'CN'},
    "tea'stone": {'aliases': ["tea'stone"], 'type': '茶饮', 'country': 'CN'},
    '一品玉': {'aliases': ['一品玉'], 'type': '零食', 'country': 'CN'},
    '一念草木中': {'aliases': ['一念草木中'], 'type': '饮料', 'country': 'CN'},
    '京A': {'aliases': ['京A'], 'type': '酒类', 'country': 'CN'},
    '厚木': {'aliases': ['厚木'], 'type': '家纺', 'country': 'CN'},
    '明谦': {'aliases': ['明谦'], 'type': '咖啡', 'country': 'CN'},
    '林源春': {'aliases': ['林源春'], 'type': '饮料', 'country': 'CN'},
    '欧扎克': {'aliases': ['欧扎克'], 'type': '乳品', 'country': 'CN'},
    '牧高笛': {'aliases': ['牧高笛'], 'type': '百货', 'country': 'CN'},
    '白珠': {'aliases': ['白珠'], 'type': '粮油', 'country': 'CN'},
    '贝贝星': {'aliases': ['BABY STAR', 'BABY STAR/贝贝星', '贝贝星'], 'type': '零食', 'country': 'CN'},
    '适乐肤': {'aliases': ['适乐肤'], 'type': '美妆', 'country': 'CN'},
    '锡林郭勒': {'aliases': ['锡林郭勒'], 'type': '肉片肉卷', 'country': 'CN'},
    '风花雪月': {'aliases': ['风花雪月'], 'type': '酒类', 'country': 'CN'},
    '八宝利': {'aliases': ['八宝利'], 'type': '零食', 'country': 'CN'},
    '张君雅': {'aliases': ['张君雅'], 'type': '零食', 'country': 'TW'},
    '望月酒庄': {'aliases': ['望月酒庄'], 'type': '酒类', 'country': 'US'},
    '盒补补': {'aliases': ['盒补补'], 'type': '保健', 'country': 'CN'},
    '福特莎': {'aliases': ['福特莎'], 'type': '酱菜', 'country': 'ES'},
    '金陵卤之坊': {'aliases': ['金陵卤之坊'], 'type': '熟食', 'country': 'CN'},
    'MAX': {'aliases': ['MAX'], 'type': '食品', 'country': 'CN'},
    '日日鲜': {'aliases': ['日日鲜'], 'type': '蔬菜', 'country': 'CN'},
    '盒马MAX': {'aliases': ['盒马MAX'], 'type': '食品', 'country': 'CN'},
    '盒马先生': {'aliases': ['盒马先生'], 'type': '百货', 'country': 'CN'},
    '盒马小镇': {'aliases': ['盒马小镇'], 'type': '百货', 'country': 'CN'},
    '盒马工坊': {'aliases': ['盒马工坊'], 'type': '蔬菜', 'country': 'CN'},
    '盒马日日鲜': {'aliases': ['盒马日日鲜'], 'type': '生鲜', 'country': 'CN'},
    '盒马烘焙': {'aliases': ['盒马烘焙'], 'type': '烘焙', 'country': 'CN'},
    '一米八': {'aliases': ['一米八'], 'type': '海鲜', 'country': 'CN'},
    '脆升升': {'aliases': ['脆升升'], 'type': '零食', 'country': 'CN'},
    '加藤制果': {'aliases': ['加藤制果'], 'type': '零食', 'country': 'JP'},
    '鲜尝厚买': {'aliases': ['鲜尝厚买'], 'type': '烘焙', 'country': 'CN'},
    'CHALI': {'aliases': ['CHALI'], 'type': '茶饮', 'country': 'CN'},
    'Hellema': {'aliases': ['Hellema'], 'type': '零食', 'country': 'CN'},
    'Magic Smile': {'aliases': ['Magic Smile'], 'type': '零食', 'country': 'CN'},
    '乌江': {'aliases': ['乌江'], 'type': '酱菜', 'country': 'CN'},
    '优鲜沛': {'aliases': ['优鲜沛'], 'type': '饮料', 'country': 'CN'},
    '佳贝艾特': {'aliases': ['佳贝艾特'], 'type': '乳品', 'country': 'CN'},
    '俏雅': {'aliases': ['俏雅'], 'type': '酒类', 'country': 'CN'},
    '加菲猫X吉饮': {'aliases': ['加菲猫X吉饮'], 'type': '咖啡', 'country': 'CN'},
    '卓宜': {'aliases': ['卓宜'], 'type': '饮料', 'country': 'TH'},
    '卡卡业': {'aliases': ['卡卡业'], 'type': '谷物', 'country': 'CN'},
    '卡卡业 X Kiri': {'aliases': ['卡卡业 X Kiri'], 'type': '谷物', 'country': 'CN'},
    '叮小马': {'aliases': ['叮小马'], 'type': '糖果', 'country': 'CN'},
    '咖啡公社': {'aliases': ['咖啡公社'], 'type': '咖啡', 'country': 'CN'},
    '大江': {'aliases': ['大江'], 'type': '半成品', 'country': 'CN'},
    '山花集': {'aliases': ['山花集'], 'type': '饮料', 'country': 'CN'},
    '巧力美': {'aliases': ['巧力美'], 'type': '巧克力', 'country': 'CN'},
    '思密琪': {'aliases': ['思密琪'], 'type': '酒类', 'country': 'AU'},
    '方回春堂': {'aliases': ['方回春堂'], 'type': '冲调', 'country': 'CN'},
    '晨曦': {'aliases': ['晨曦'], 'type': '熟食', 'country': 'CN'},
    '有得解': {'aliases': ['有得解'], 'type': '饮料', 'country': 'MY'},
    '植场达人': {'aliases': ['植场达人'], 'type': '方便食品', 'country': 'CN'},
    '植想润': {'aliases': ['植想润'], 'type': '饮料', 'country': 'CN'},
    '橙汁': {'aliases': ['橙汁'], 'type': '饮料', 'country': 'CN'},
    '欣欣': {'aliases': ['欣欣'], 'type': '烘焙', 'country': 'CN'},
    '源究所': {'aliases': ['源究所'], 'type': '饮料', 'country': 'CN'},
    '牧果人': {'aliases': ['牧果人'], 'type': '零食', 'country': 'CN'},
    '白元': {'aliases': ['白元'], 'type': '家居', 'country': 'JP'},
    '素派': {'aliases': ['素派'], 'type': '豆制品', 'country': 'CN'},
    '老鸭集': {'aliases': ['老鸭集'], 'type': '预制菜', 'country': 'CN'},
    '薄荷生活': {'aliases': ['薄荷生活'], 'type': '零食', 'country': 'CN'},
    '诺贝达': {'aliases': ['诺贝达'], 'type': '糕点', 'country': 'CN'},
    '轻上轻燃': {'aliases': ['轻上轻燃'], 'type': '饮料', 'country': 'CN'},
    '阿甘正馔': {'aliases': ['阿甘正馔'], 'type': '零食', 'country': 'CN'},
    '魔饮': {'aliases': ['魔饮'], 'type': '咖啡', 'country': 'CN'},
    'CHAO SUA': {'aliases': ['CHAO SUA'], 'type': '零食', 'country': 'TH'},
    'CHAOSUA': {'aliases': ['CHAOSUA'], 'type': '零食', 'country': 'TH'},
    'KARA': {'aliases': ['KARA'], 'type': '烘焙', 'country': 'ID'},
    'Nonna': {'aliases': ['Nonna'], 'type': '零食', 'country': 'CN'},
    'OATLY': {'aliases': ['OATLY'], 'type': '乳品', 'country': 'CN'},
    'bare': {'aliases': ['bare'], 'type': '零食', 'country': 'CN'},
    '一鸣': {'aliases': ['一鸣'], 'type': '零食', 'country': 'CN'},
    '乐爱牙': {'aliases': ['乐爱牙'], 'type': '口腔', 'country': 'CN'},
    '六养': {'aliases': ['六养'], 'type': '冲饮', 'country': 'CN'},
    '半糖时光': {'aliases': ['半糖时光'], 'type': '糕点', 'country': 'CN'},
    '原本记忆': {'aliases': ['原本记忆'], 'type': '零食', 'country': 'CN'},
    '想真': {'aliases': ['想真'], 'type': '冲饮', 'country': 'CN'},
    '新希望': {'aliases': ['新希望'], 'type': '乳品', 'country': 'CN'},
    '晴天大白': {'aliases': ['EVERSHINE/晴天大白', '晴天大白', 'EVERSHINE'], 'type': '日化', 'country': 'CN'},
    '有你一面': {'aliases': ['有你一面'], 'type': '方便食品', 'country': 'CN'},
    '木桐嘉棣': {'aliases': ['木桐嘉棣'], 'type': '酒类', 'country': 'FR'},
    '李陌茶': {'aliases': ['李陌茶'], 'type': '茶饮', 'country': 'CN'},
    '比斯奇果屋': {'aliases': ['比斯奇果屋'], 'type': '零食', 'country': 'TH'},
    '而初': {'aliases': ['而初'], 'type': '肉禽蛋', 'country': 'CN'},
    '舒汇慢谷': {'aliases': ['舒汇慢谷'], 'type': '面点', 'country': 'CN'},
    '莫小仙': {'aliases': ['莫小仙'], 'type': '方便食品', 'country': 'CN'},
    '莱福澳': {'aliases': ['莱福澳', 'LoveAu', 'LoveAu/莱福澳'], 'type': '饮料', 'country': 'GB'},
    '薇诺娜': {'aliases': ['薇诺娜'], 'type': '美妆', 'country': 'CN'},
    '轻上': {'aliases': ['轻上'], 'type': '茶饮', 'country': 'CN'},
    '馋嘴娃娃': {'aliases': ['馋嘴娃娃'], 'type': '零食', 'country': 'CN'},
    '龙潭': {'aliases': ['龙潭'], 'type': '茶叶', 'country': 'CN'},
    'Bulla': {'aliases': ['Bulla'], 'type': '冰淇淋', 'country': 'AU'},
    'CACAOCAT': {'aliases': ['CACAOCAT'], 'type': '零食', 'country': 'JP'},
    'FRUTCO': {'aliases': ['FRUTCO'], 'type': '饮料', 'country': 'CN'},
    'KAPITI': {'aliases': ['KAPITI'], 'type': '冰淇淋', 'country': 'NZ'},
    'MY PHUONG FOOD': {'aliases': ['MY PHUONG FOOD'], 'type': '零食', 'country': 'VN'},
    'Nobaton': {'aliases': ['Nobaton'], 'type': '口腔', 'country': 'KR'},
    'P&G宝洁': {'aliases': ['P&G宝洁'], 'type': '个人清洁', 'country': 'JP'},
    'Sense Asia': {'aliases': ['Sense Asia'], 'type': '零食', 'country': 'VN'},
    'TIPTOP': {'aliases': ['TIPTOP'], 'type': '冰淇淋', 'country': 'NZ'},
    'TSUKI': {'aliases': ['TSUKI'], 'type': '饮料', 'country': 'CN'},
    'UNNY悠宜': {'aliases': ['UNNY悠宜'], 'type': '美妆', 'country': 'CN'},
    'cote noire': {'aliases': ['cote noire'], 'type': '美妆', 'country': 'CN'},
    '一口香香香香香': {'aliases': ['一口香香香香香'], 'type': '零食', 'country': 'CN'},
    '东洋': {'aliases': ['东洋'], 'type': '冰淇淋', 'country': 'JP'},
    '亚洲妈妈': {'aliases': ['亚洲妈妈'], 'type': '速食', 'country': 'KR'},
    '亿智': {'aliases': ['亿智'], 'type': '零食', 'country': 'CN'},
    '倍轻松': {'aliases': ['breo/倍轻松', '倍轻松', 'breo'], 'type': '百货', 'country': 'CN'},
    '克拉格摩尔': {'aliases': ['克拉格摩尔'], 'type': '酒类', 'country': 'GB'},
    '冰力克': {'aliases': ['冰力克'], 'type': '糖果', 'country': 'CN'},
    '冰水屋': {'aliases': ['冰水屋'], 'type': '冰淇淋', 'country': 'JP'},
    '北田': {'aliases': ['北田'], 'type': '零食', 'country': 'TW'},
    '北见铃木': {'aliases': ['北见铃木'], 'type': '零食', 'country': 'JP'},
    '卫视': {'aliases': ['卫视'], 'type': '饮料', 'country': 'CN'},
    '君度': {'aliases': ['君度'], 'type': '酒类', 'country': 'FR'},
    '哆比': {'aliases': ['哆比'], 'type': '糖果', 'country': 'CN'},
    '哈瓦那俱乐部': {'aliases': ['哈瓦那俱乐部'], 'type': '酒类', 'country': '古巴'},
    '喜思乐': {'aliases': ['喜思乐'], 'type': '巧克力', 'country': 'MY'},
    '嘉桦': {'aliases': ['嘉桦'], 'type': '饮料', 'country': 'CN'},
    '富吃': {'aliases': ['富吃'], 'type': '零食', 'country': 'MY'},
    '寻香牧场': {'aliases': ['寻香牧场'], 'type': '零食', 'country': 'CN'},
    '巴蜀公社': {'aliases': ['巴蜀公社'], 'type': '半成品', 'country': 'CN'},
    '手道木川': {'aliases': ['手道木川'], 'type': '零食', 'country': 'CN'},
    '桑加1': {'aliases': ['桑加1'], 'type': '饮料', 'country': 'CN'},
    '椰放': {'aliases': ['椰放'], 'type': '家居', 'country': 'CN'},
    '浙粮臻选': {'aliases': ['浙粮臻选'], 'type': '肉禽蛋', 'country': 'CN'},
    '燕之屋': {'aliases': ['燕之屋'], 'type': '冲饮', 'country': 'CN'},
    '特华得': {'aliases': ['特华得'], 'type': '肉制品', 'country': 'CN'},
    '白惜': {'aliases': ['白惜'], 'type': '口腔', 'country': 'CN'},
    '益昌老街': {'aliases': ['益昌老街'], 'type': '饮料', 'country': 'MY'},
    '稻院士': {'aliases': ['稻院士'], 'type': '粮油', 'country': 'CN'},
    '约克': {'aliases': ['约克'], 'type': '糖果', 'country': 'CN'},
    '维汉': {'aliases': ['维汉'], 'type': '零食', 'country': 'CN'},
    '茶口乐': {'aliases': ['茶口乐'], 'type': '糖果', 'country': 'CN'},
    '西贝': {'aliases': ['西贝'], 'type': '半成品', 'country': 'CN'},
    '西麦': {'aliases': ['西麦'], 'type': '谷物', 'country': 'CN'},
    '豆丁日记': {'aliases': ['豆丁日记'], 'type': '饮料', 'country': 'CN'},
    '赞萌露比': {'aliases': ['赞萌露比'], 'type': '零食', 'country': 'KR'},
    '超激泡沫': {'aliases': ['超激泡沫'], 'type': '酒类', 'country': 'CN'},
    '阿奇侬': {'aliases': ['阿奇侬'], 'type': '冰淇淋', 'country': 'TW'},
    '隔壁刘奶奶': {'aliases': ['隔壁刘奶奶'], 'type': '乳品', 'country': 'CN'},
    'Glasslock': {'aliases': ['Glasslock'], 'type': '厨房用品', 'country': 'CN'},
    'Skinnie': {'aliases': ['Skinnie'], 'type': '零食', 'country': 'MY'},
    '七度空间': {'aliases': ['七度空间'], 'type': '护理', 'country': 'CN'},
    '东远': {'aliases': ['东远'], 'type': '罐头', 'country': 'KR'},
    '五味麦社': {'aliases': ['五味麦社'], 'type': '速食', 'country': 'CN'},
    '低卡博士': {'aliases': ['低卡博士'], 'type': '酱料', 'country': 'CN'},
    '口不离': {'aliases': ['口不离'], 'type': '零食', 'country': 'CN'},
    '吉饮&加菲猫': {'aliases': ['吉饮&加菲猫'], 'type': '乳品', 'country': 'CN'},
    '宝露兹': {'aliases': ['宝露兹', 'AQUAPROS/宝露兹', 'AQUAPROS'], 'type': '饮料', 'country': 'CN'},
    '恩美斯': {'aliases': ['恩美斯'], 'type': '零食', 'country': 'DK'},
    '探寻风味社': {'aliases': ['探寻风味社'], 'type': '速食', 'country': 'CN'},
    '清可新': {'aliases': ['清可新'], 'type': '洗护', 'country': 'CN'},
    '百菲酪': {'aliases': ['百菲酪'], 'type': '乳品', 'country': 'CN'},
    '益周适': {'aliases': ['益周适'], 'type': '口腔', 'country': 'CN'},
    '童涵春堂': {'aliases': ['童涵春堂'], 'type': '谷物', 'country': 'CN'},
    '雀斑美人': {'aliases': ['雀斑美人'], 'type': '饮料', 'country': 'CN'},
    'Rossana': {'aliases': ['Rossana'], 'type': '糖果', 'country': 'IT'},
    '伊藤': {'aliases': ['伊藤'], 'type': '肉制品', 'country': 'CN'},
    '悠宜': {'aliases': ['悠宜'], 'type': '美妆', 'country': 'CN'},
    '轻爷': {'aliases': ['轻爷'], 'type': '调味', 'country': 'CN'},
    '黛丝恩': {'aliases': ['黛丝恩'], 'type': '洗护', 'country': 'JP'},
    'CHILLGREEN': {'aliases': ['CHILLGREEN'], 'type': '酒类', 'country': 'JP'},
    '光之颂亿': {'aliases': ['光之颂亿'], 'type': '酒类', 'country': 'FR'},
    '和苑酒家': {'aliases': ['和苑酒家'], 'type': '餐饮', 'country': 'CN'},
    '富久锦': {'aliases': ['富久锦'], 'type': '酒类', 'country': 'JP'},
    '摩根船长': {'aliases': ['摩根船长'], 'type': '酒类', 'country': 'GB'},
    '朱光玉': {'aliases': ['朱光玉'], 'type': '火锅', 'country': 'CN'},
    '梅冻': {'aliases': ['梅冻'], 'type': '糖果', 'country': 'CN'},
    '爱柏': {'aliases': ['爱柏'], 'type': '酒类', 'country': 'CN'},
    '爱芙': {'aliases': ['爱芙'], 'type': '巧克力', 'country': 'MY'},
    '纺优美': {'aliases': ['纺优美'], 'type': '洗护', 'country': 'CN'},
    '金尘茶': {'aliases': ['金尘茶'], 'type': '茶饮', 'country': 'CN'},
    '龟田制果': {'aliases': ['龟田制果'], 'type': '零食', 'country': 'CN'},
    "FOX'S霍士": {'aliases': ["FOX'S霍士"], 'type': '糖果', 'country': 'ID'},
    'Herbaland禾宝蓝': {'aliases': ['Herbaland禾宝蓝'], 'type': '糖果', 'country': 'CN'},
    'IMPRESAN英普林氏': {'aliases': ['IMPRESAN英普林氏'], 'type': '洗护', 'country': 'DE'},
    'OCEAN BOMB': {'aliases': ['OCEAN BOMB'], 'type': '饮料', 'country': 'TW'},
    'Tutto': {'aliases': ['Tutto'], 'type': '糖果', 'country': 'KR'},
    '仙之宝': {'aliases': ['仙之宝'], 'type': '零食', 'country': 'CN'},
    '北纯': {'aliases': ['北纯'], 'type': '杂粮', 'country': 'CN'},
    '卤味觉醒': {'aliases': ['卤味觉醒'], 'type': '零食', 'country': 'CN'},
    '叮叮': {'aliases': ['叮叮'], 'type': '半成品', 'country': 'CN'},
    '可可满分': {'aliases': ['可可满分'], 'type': '茶饮', 'country': 'CN'},
    '可爱多': {'aliases': ['可爱多'], 'type': '冰淇淋', 'country': 'CN'},
    '吉饮': {'aliases': ['吉饮'], 'type': '咖啡', 'country': 'CN'},
    '外婆的小铺': {'aliases': ['外婆的小铺'], 'type': '零食', 'country': 'CN'},
    '好人家X马路边边': {'aliases': ['好人家X马路边边'], 'type': '火锅', 'country': 'CN'},
    '广川': {'aliases': ['广川'], 'type': '零食', 'country': 'KR'},
    '日加满': {'aliases': ['日加满'], 'type': '饮料', 'country': 'CN'},
    '日本盛': {'aliases': ['日本盛'], 'type': '酒类', 'country': 'JP'},
    '杏花楼': {'aliases': ['杏花楼'], 'type': '餐饮', 'country': 'CN'},
    '柏治廷': {'aliases': ['柏治廷'], 'type': '百货', 'country': 'CN'},
    '水卫士': {'aliases': ['水卫士'], 'type': '厨房清洁', 'country': 'CN'},
    '海天下': {'aliases': ['海天下'], 'type': '海鲜制品', 'country': 'CN'},
    '湖池屋': {'aliases': ['湖池屋'], 'type': '零食', 'country': 'CN'},
    '源制所': {'aliases': ['源制所'], 'type': '饮料', 'country': 'CN'},
    '爱之味': {'aliases': ['爱之味'], 'type': '茶饮', 'country': 'TW'},
    '爱果乐': {'aliases': ['爱果乐'], 'type': '糖果', 'country': 'ES'},
    '瑞幸': {'aliases': ['瑞幸'], 'type': '咖啡', 'country': 'CN'},
    '碧柔': {'aliases': ['碧柔', 'Biore', 'Biore/碧柔'], 'type': '美妆', 'country': 'CN'},
    '红岩臻选': {'aliases': ['红岩臻选'], 'type': '零食', 'country': 'AU'},
    '臻牧': {'aliases': ['臻牧'], 'type': '乳品', 'country': 'CN'},
    '觅菓': {'aliases': ['觅菓'], 'type': '坚果', 'country': 'CN'},
    '记住这一分钟': {'aliases': ['记住这一分钟'], 'type': '酒类', 'country': 'CN'},
    '谷本日记': {'aliases': ['谷本日记'], 'type': '乳品', 'country': 'CN'},
    '贝贝之星': {'aliases': ['贝贝之星'], 'type': '速冻', 'country': 'CN'},
    '轻元素': {'aliases': ['轻元素'], 'type': '饮料', 'country': 'CN'},
    '辛尼里奇': {'aliases': ['辛尼里奇'], 'type': '乳品', 'country': 'CN'},
    '香香嘴': {'aliases': ['香香嘴'], 'type': '零食', 'country': 'CN'},
    '鲁胖胖': {'aliases': ['鲁胖胖'], 'type': '零食', 'country': 'CN'},
    '鸥际': {'aliases': ['鸥际'], 'type': '咖啡', 'country': 'CN'},
    '龙老师': {'aliases': ['龙老师'], 'type': '酱菜', 'country': 'CN'},
    '龙霸': {'aliases': ['龙霸'], 'type': '海鲜', 'country': 'CN'},
    'Off&Relax': {'aliases': ['Off&Relax'], 'type': '洗护', 'country': 'CN'},
    'Prinze': {'aliases': ['Prinze'], 'type': '零食', 'country': 'TH'},
    '伊刻活泉': {'aliases': ['伊刻活泉'], 'type': '饮料', 'country': 'CN'},
    '佳沃': {'aliases': ['佳沃'], 'type': '水果', 'country': 'CN'},
    '宏明': {'aliases': ['宏明'], 'type': '零食', 'country': 'CN'},
    '张一元': {'aliases': ['张一元'], 'type': '饮料', 'country': 'CN'},
    '膳苡': {'aliases': ['膳苡'], 'type': '零食', 'country': 'CN'},
    '蔓谷女孩': {'aliases': ['蔓谷女孩'], 'type': '糖果', 'country': 'TH'},
    '蔻蔻椰': {'aliases': ['蔻蔻椰'], 'type': '饮料', 'country': 'CN'},
    '轻空': {'aliases': ['轻空'], 'type': '饮料', 'country': 'CN'},
    '阿迪达斯': {'aliases': ['Adidas/阿迪达斯', '阿迪达斯', 'Adidas'], 'type': '日化', 'country': 'CN'},
    '雀巢咖啡': {'aliases': ['雀巢咖啡'], 'type': '咖啡', 'country': 'CN'},
    '香奈': {'aliases': ['香奈'], 'type': '酒类', 'country': 'FR'},
    'Morning Fresh': {'aliases': ['Morning Fresh'], 'type': '洗洁精', 'country': 'ID'},
    '乐卡斯': {'aliases': ['乐卡斯'], 'type': '零食', 'country': 'CN'},
    '优形': {'aliases': ['优形'], 'type': '肉制品', 'country': 'CN'},
    '南孚': {'aliases': ['南孚'], 'type': '电子', 'country': 'CN'},
    '咔咔番': {'aliases': ['咔咔番'], 'type': '零食', 'country': 'CN'},
    '小罐茶园': {'aliases': ['小罐茶园'], 'type': '茶叶', 'country': 'CN'},
    '时益多': {'aliases': ['时益多'], 'type': '饮料', 'country': 'CN'},
    '田园猎手': {'aliases': ['田园猎手'], 'type': '肉制品', 'country': 'CN'},
    '缤若诗': {'aliases': ['Bifesta', '缤若诗', 'Bifesta/缤若诗'], 'type': '美妆', 'country': 'JP'},
    '贝亲': {'aliases': ['贝亲', 'Pigeon', 'Pigeon/贝亲'], 'type': '美妆', 'country': 'CN'},
    '金典': {'aliases': ['金典'], 'type': '乳品', 'country': 'CN'},
    '3D盒大侠': {'aliases': ['3D盒大侠'], 'type': '冰淇淋', 'country': 'CN'},
    '元气自在水': {'aliases': ['元气自在水'], 'type': '饮料', 'country': 'CN'},
    '希腊奥林匹斯': {'aliases': ['希腊奥林匹斯'], 'type': '乳品', 'country': 'CN'},
    '北昀': {'aliases': ['北昀'], 'type': '酱菜', 'country': 'JP'},
    '小野轻煮': {'aliases': ['小野轻煮'], 'type': '调味', 'country': 'CN'},
    '润本': {'aliases': ['润本'], 'type': '护理', 'country': 'CN'},
    '纽麦福': {'aliases': ['纽麦福'], 'type': '乳品', 'country': 'NZ'},
    '阿丽塔': {'aliases': ['阿丽塔'], 'type': '乳品', 'country': 'CN'},
    'ChaCha': {'aliases': ['ChaCha'], 'type': '坚果', 'country': 'CN'},
    'GAIN YUM': {'aliases': ['GAIN YUM'], 'type': '零食', 'country': 'CN'},
    'SWOOSH': {'aliases': ['SWOOSH'], 'type': '酒类', 'country': 'CN'},
    'SmooShake': {'aliases': ['SmooShake'], 'type': '饮料', 'country': 'VN'},
    'VVC': {'aliases': ['VVC'], 'type': '家纺', 'country': 'CN'},
    'iFoodToy': {'aliases': ['iFoodToy'], 'type': '糖果', 'country': 'CN'},
    '中街冰点': {'aliases': ['中街冰点'], 'type': '冰淇淋', 'country': 'CN'},
    '八马': {'aliases': ['八马'], 'type': '茶叶', 'country': 'CN'},
    '初时家': {'aliases': ['初时家'], 'type': '饮料', 'country': 'CN'},
    '北陆制果': {'aliases': ['北陆制果'], 'type': '零食', 'country': 'JP'},
    '卓牧': {'aliases': ['卓牧'], 'type': '乳品', 'country': 'CN'},
    '吨吨哈水王': {'aliases': ['吨吨哈水王'], 'type': '饮料', 'country': 'CN'},
    '和路雪': {'aliases': ['和路雪'], 'type': '冰淇淋', 'country': 'CN'},
    '好巴食': {'aliases': ['好巴食'], 'type': '零食', 'country': 'CN'},
    '威廉姆斯食阁': {'aliases': ['威廉姆斯食阁'], 'type': '谷物', 'country': 'AU'},
    '宁夏盐池滩羊': {'aliases': ['宁夏盐池滩羊'], 'type': '半成品', 'country': 'CN'},
    '宝珠酿造': {'aliases': ['宝珠酿造'], 'type': '饮料', 'country': 'CN'},
    '延世': {'aliases': ['延世'], 'type': '乳品', 'country': 'KR'},
    '欢赞': {'aliases': ['欢赞'], 'type': '零食', 'country': 'CN'},
    '润成': {'aliases': ['润成'], 'type': '零食', 'country': 'CN'},
    '澳牧': {'aliases': ['澳牧'], 'type': '乳品', 'country': 'CN'},
    '福宁港': {'aliases': ['福宁港'], 'type': '预制菜', 'country': 'CN'},
    '贵茶': {'aliases': ['贵茶'], 'type': '饮料', 'country': 'CN'},
    '锐思': {'aliases': ['锐思'], 'type': '3C数码', 'country': 'CN'},
    '桐伊味': {'aliases': ['桐伊味'], 'type': '糕点', 'country': 'CN'},
    '马迭尔': {'aliases': ['马迭尔'], 'type': '冰淇淋', 'country': 'CN'},
    'LALINDA': {'aliases': ['LALINDA'], 'type': '零食', 'country': 'CN'},
    '兰妃': {'aliases': ['兰妃'], 'type': '肉禽蛋', 'country': 'CN'},
    '兰皇': {'aliases': ['兰皇'], 'type': '肉禽蛋', 'country': 'CN'},
    '小西牛': {'aliases': ['小西牛'], 'type': '乳品', 'country': 'CN'},
    '新碧': {'aliases': ['新碧'], 'type': '日化', 'country': 'CN'},
    '泰康': {'aliases': ['泰康'], 'type': '调味', 'country': 'CN'},
    '王朝': {'aliases': ['王朝'], 'type': '酒类', 'country': 'CN'},
    '珍妮花': {'aliases': ['珍妮花'], 'type': '日化', 'country': 'CN'},
    '盒小满': {'aliases': ['盒小满'], 'type': '肉片肉卷', 'country': 'CN'},
    '神丹': {'aliases': ['神丹'], 'type': '肉禽蛋', 'country': 'CN'},
    '稻香黑土': {'aliases': ['稻香黑土'], 'type': '粮油', 'country': 'CN'},
    '达力摇': {'aliases': ['达力摇'], 'type': '饮料', 'country': 'CN'},
    '阿波罗': {'aliases': ['阿波罗'], 'type': '冰淇淋', 'country': 'CN'},
    '智美': {'aliases': ['智美'], 'type': '酒类', 'country': 'CN'},
    '双洋': {'aliases': ['双洋'], 'type': '酒类', 'country': 'CN'},
    '和酒': {'aliases': ['和酒'], 'type': '酒类', 'country': 'CN'},
    '佳沛': {'aliases': ['佳沛'], 'type': '水果', 'country': 'NZ'},
    '天福天心': {'aliases': ['天福天心'], 'type': '茶叶', 'country': 'CN'},
    '雪菲力': {'aliases': ['雪菲力'], 'type': '饮料', 'country': 'CN'},
    '中国劲酒': {'aliases': ['中国劲酒'], 'type': '酒类', 'country': 'CN'},
    '林师傅': {'aliases': ['林师傅'], 'type': '水果', 'country': 'CN'},
    'Pidan': {'aliases': ['Pidan'], 'type': '宠物', 'country': 'CN'},
    '心相印': {'aliases': ['心相印'], 'type': '纸品', 'country': 'CN'},
    '盒马火锅': {'aliases': ['盒马火锅'], 'type': '火锅食材', 'country': 'CN'},
    '家佳康': {'aliases': ['家佳康'], 'type': '肉禽蛋', 'country': 'CN'},
    '唐宗筷': {'aliases': ['唐宗筷'], 'type': '厨房用品', 'country': 'CN'},
    '清风': {'aliases': ['清风'], 'type': '未知', 'country': 'CN'},
    '象大厨': {'aliases': ['象大厨'], 'type': '熟食', 'country': 'CN'},
    '象小家': {'aliases': ['象小家'], 'type': '日化', 'country': 'CN'},
}


# === 动态品牌持久化 ===

def load_dynamic_brands() -> dict:
    """从 JSON 文件加载动态品牌"""
    if DYNAMIC_BRANDS_FILE.exists():
        try:
            with open(DYNAMIC_BRANDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


_save_lock = threading.Lock()

def _atomic_json_save(filepath: Path, data):
    """原子写入 JSON：先写临时文件，再 os.replace 原子替换，防止写入中途崩溃导致文件损坏"""
    tmp = filepath.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(str(tmp), str(filepath))

def save_dynamic_brand(brand_name: str, brand_info: dict):
    """保存单个动态品牌到 JSON 文件"""
    with _save_lock:
        dynamic_brands = load_dynamic_brands()
        dynamic_brands[brand_name] = brand_info
        _atomic_json_save(DYNAMIC_BRANDS_FILE, dynamic_brands)


def get_all_dynamic_brands() -> dict:
    """获取所有动态品牌"""
    return load_dynamic_brands()


def load_dismissed_brands() -> list:
    """加载已忽略的品牌列表"""
    if DISMISSED_BRANDS_FILE.exists():
        try:
            with open(DISMISSED_BRANDS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []


def save_dismissed_brand(brand_name: str):
    """持久化已忽略的品牌"""
    with _save_lock:
        dismissed = load_dismissed_brands()
        if brand_name not in dismissed:
            dismissed.append(brand_name)
        _atomic_json_save(DISMISSED_BRANDS_FILE, dismissed)


def load_corrected_products(group_id: str) -> dict:
    """加载已修正的商品规则（code → {brand/category}，按分组隔离）"""
    path = _corrected_products_path(group_id)
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_corrected_product(group_id: str, code: str, rule: dict):
    """保存单条商品修正记录"""
    path = _corrected_products_path(group_id)
    with _save_lock:
        rules = load_corrected_products(group_id)
        if code in rules:
            rules[code].update(rule)
        else:
            rules[code] = rule
        _atomic_json_save(path, rules)


def batch_save_corrected_products(group_id: str, updates: dict):
    """批量更新：读一次，合并所有，写一次"""
    path = _corrected_products_path(group_id)
    with _save_lock:
        rules = load_corrected_products(group_id)
        for code, rule in updates.items():
            if code in rules:
                rules[code].update(rule)
            else:
                rules[code] = rule
        _atomic_json_save(path, rules)


def clear_corrected_products(group_id: str):
    """清空所有商品修正记录"""
    path = _corrected_products_path(group_id)
    with _save_lock:
        _atomic_json_save(path, {})


def load_corrected_brands() -> dict:
    """加载品牌建议修正记录（suggested_name → corrected_to）"""
    if CORRECTED_BRANDS_FILE.exists():
        try:
            with open(CORRECTED_BRANDS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_corrected_brand(suggested: str, corrected_to: str, sample: dict):
    """保存品牌建议修正记录"""
    with _save_lock:
        records = load_corrected_brands()
        if suggested in records:
            records[suggested]['count'] += 1
            records[suggested]['samples'].append(sample)
        else:
            records[suggested] = {
                'suggested': suggested,
                'corrected_to': corrected_to,
                'samples': [sample],
                'count': 1,
                'corrected_at': __import__('datetime').datetime.now().isoformat()
            }
        _atomic_json_save(CORRECTED_BRANDS_FILE, records)


def load_corrected_categories() -> dict:
    """加载分类建议修正记录（entity → corrected_path）"""
    if CORRECTED_CATEGORIES_FILE.exists():
        try:
            with open(CORRECTED_CATEGORIES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_corrected_category(entity: str, record: dict):
    """保存分类建议修正记录"""
    with _save_lock:
        records = load_corrected_categories()
        if entity in records:
            records[entity]['count'] += 1
            records[entity]['samples'].append(record.get('samples', [{}])[0])
        else:
            records[entity] = record
        _atomic_json_save(CORRECTED_CATEGORIES_FILE, records)


def load_relationships() -> dict:
    """加载子品牌关联关系"""
    if RELATIONSHIPS_FILE.exists():
        try:
            return json.loads(RELATIONSHIPS_FILE.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}


def save_relationships(data: dict):
    """保存子品牌关联关系"""
    with _save_lock:
        _atomic_json_save(RELATIONSHIPS_FILE, data)


def export_to_database_py() -> int:
    """
    将动态品牌追加到 database.py 文件
    
    Returns:
        int: 成功导出的品牌数量，失败返回 -1
    """
    dynamic_brands = load_dynamic_brands()
    if not dynamic_brands:
        return 0

    try:
        db_file = Path(__file__)
        content = db_file.read_text(encoding='utf-8')

        # 提取静态段品牌名
        end_marker = '\n}\n\n\n# === 动态品牌持久化 ==='
        insert_pos = content.find(end_marker)
        if insert_pos == -1:
            return -1
        static_part = content[:insert_pos]
        existing_names = set(re.findall(r"'([^']+)':\s*\{", static_part))
        existing_names.update(re.findall(r'"([^"]+)":\s*\{', static_part))

        # 生成新品牌代码（跳过已存在的），保留已有品牌的更新
        dynamic_code_lines = []
        export_count = 0
        remaining = {}
        for brand_name, info in sorted(dynamic_brands.items()):
            if brand_name in existing_names:
                remaining[brand_name] = info  # 已有品牌的别名/子品牌更新，保留
                continue
            export_count += 1
            aliases_str = ', '.join(repr(a) for a in info.get('aliases', []))
            bt = info.get('type', '未知')
            co = info.get('country', 'Unknown')
            line = f"    {repr(brand_name)}: {{'aliases': [{aliases_str}], 'type': {repr(bt)}, 'country': {repr(co)}}},"
            dynamic_code_lines.append(line)

        if dynamic_code_lines:
            dynamic_code = '\n'.join(dynamic_code_lines)
            has_section = '# === 动态品牌（自动合并）===' in content
            insert_code = '\n' + dynamic_code if has_section else '\n\n    # === 动态品牌（自动合并）===\n' + dynamic_code
            new_content = content[:insert_pos] + insert_code + content[insert_pos:]
            db_file.write_text(new_content, encoding='utf-8')

        # 保留已有品牌的更新（别名/子品牌等），不清空
        DYNAMIC_BRANDS_FILE.write_text(
            json.dumps(remaining, ensure_ascii=False, indent=2), encoding='utf-8'
        )
        return export_count
    except Exception as e:
        print(f"导出品牌库失败: {e}")
        return -1


def add_brand(brand_name: str, aliases: list, brand_type: str, country: str, sub_brands: dict = None, persist: bool = True, parent_brand: str = '', relation_type: str = ''):
    """
    动态添加新品牌到数据库（自动重建索引 + 持久化）
    如果品牌已存在，合并别名、类型、国家、子品牌（不覆盖）

    Args:
        brand_name: 品牌标准名称
        aliases: 品牌别名列表
        brand_type: 品牌类型（如：零食、饮料等）
        country: 国家代码（如：CN, US等）
        sub_brands: 子品牌字典（可选）
        persist: 是否持久化到 JSON 文件（默认 True）
        parent_brand: 关联的主品牌名（可选）
        relation_type: 关联类型，'sub_brand' 或 'alias'
    """
    # 别名关系：不创建新品牌，只更新父品牌的别名列表
    if relation_type == 'alias' and parent_brand and parent_brand in BRAND_DATABASE_V6:
        parent = BRAND_DATABASE_V6[parent_brand]
        for a in aliases:
            if a not in parent.get('aliases', []):
                parent['aliases'].append(a)
        if persist:
            save_dynamic_brand(parent_brand, parent)
        _build_brand_indexes()
        return

    # 普通品牌：创建或合并（子品牌也走此路径，创建独立条目）
    if brand_name in BRAND_DATABASE_V6:
        existing = BRAND_DATABASE_V6[brand_name]
        existing_aliases = existing.get('aliases', [])
        for a in aliases:
            if a not in existing_aliases:
                existing_aliases.append(a)
        existing['aliases'] = existing_aliases
        if brand_type and brand_type != '未知':
            existing['type'] = brand_type
        if country and country != 'CN':
            existing['country'] = country
        if sub_brands:
            existing_sub = existing.get('sub_brands', {})
            for sub_name, sub_aliases in sub_brands.items():
                if sub_name not in existing_sub:
                    existing_sub[sub_name] = sub_aliases
                else:
                    sub_list = existing_sub[sub_name]
                    for sa in sub_aliases:
                        if sa not in sub_list:
                            sub_list.append(sa)
            existing['sub_brands'] = existing_sub
    else:
        BRAND_DATABASE_V6[brand_name] = {
            'aliases': aliases,
            'type': brand_type,
            'country': country
        }
        if sub_brands:
            BRAND_DATABASE_V6[brand_name]['sub_brands'] = sub_brands

    # 子品牌关系：维护父品牌关联
    if relation_type == 'sub_brand' and parent_brand and parent_brand in BRAND_DATABASE_V6:
        parent = BRAND_DATABASE_V6[parent_brand]
        subs = parent.get('sub_brands', {})
        if brand_name not in subs:
            subs[brand_name] = list(aliases)
        else:
            for a in aliases:
                if a not in subs[brand_name]:
                    subs[brand_name].append(a)
        parent['sub_brands'] = subs
        rels = load_relationships()
        if parent_brand not in rels:
            rels[parent_brand] = {}
        rsubs = rels[parent_brand].setdefault('sub_brands', {})
        rsubs[brand_name] = list(aliases)
        save_relationships(rels)

    if persist:
        save_dynamic_brand(brand_name, BRAND_DATABASE_V6[brand_name])
    
    _build_brand_indexes()


def add_alias(brand_name: str, alias: str):
    """
    为现有品牌添加别名（自动重建索引）

    Args:
        brand_name: 品牌标准名称
        alias: 要添加的别名
    """
    if brand_name in BRAND_DATABASE_V6:
        if alias not in BRAND_DATABASE_V6[brand_name]['aliases']:
            BRAND_DATABASE_V6[brand_name]['aliases'].append(alias)
            # 自动重建哈希索引
            _build_brand_indexes()


def get_all_brands() -> list:
    """获取所有品牌名称列表"""
    return list(BRAND_DATABASE_V6.keys())


def get_brand_info(brand_name: str) -> dict:
    """获取品牌详细信息"""
    return BRAND_DATABASE_V6.get(brand_name, {})


# === 性能优化：预建哈希索引 ===
# 别名 → 标准品牌 的 O(1) 查找映射
ALIAS_TO_BRAND = {}
# 品牌名 → 标准品牌 的 O(1) 查找映射（包含所有别名）
BRAND_NAME_TO_STANDARD = {}
# 子品牌别名 → 标准子品牌 的 O(1) 查找映射
SUB_BRAND_ALIAS_TO_STANDARD = {}


def _build_brand_indexes():
    """
    构建品牌哈希索引，用于 O(1) 查找
    在模块加载时自动执行，添加/修改品牌后需调用 rebuild_indexes()
    """
    global ALIAS_TO_BRAND, BRAND_NAME_TO_STANDARD, SUB_BRAND_ALIAS_TO_STANDARD
    
    ALIAS_TO_BRAND = {}
    BRAND_NAME_TO_STANDARD = {}
    SUB_BRAND_ALIAS_TO_STANDARD = {}
    
    for std_brand, info in BRAND_DATABASE_V6.items():
        # 建立别名 → 标准品牌 映射（小写键）
        for alias in info.get('aliases', []):
            ALIAS_TO_BRAND[alias.lower()] = std_brand
            BRAND_NAME_TO_STANDARD[alias.lower()] = std_brand
        
        # 建立标准品牌名 → 自身 映射
        BRAND_NAME_TO_STANDARD[std_brand.lower()] = std_brand
        
        # 建立子品牌别名映射
        for sub_brand, sub_aliases in info.get('sub_brands', {}).items():
            for sub_alias in sub_aliases:
                SUB_BRAND_ALIAS_TO_STANDARD[sub_alias.lower()] = sub_brand


def rebuild_indexes():
    """
    重建品牌哈希索引
    在动态添加品牌或别名后调用
    """
    _build_brand_indexes()


def find_brand_by_alias_fast(alias: str) -> str:
    """
    O(1) 根据别名查找品牌（使用哈希索引）
    
    Args:
        alias: 品牌别名
    
    Returns:
        品牌标准名称，如果未找到返回 None
    """
    if not alias:
        return None
    return ALIAS_TO_BRAND.get(alias.lower())


def find_brand_by_name_fast(brand_name: str) -> str:
    """
    O(1) 根据品牌名查找标准品牌（使用哈希索引）
    
    Args:
        brand_name: 品牌名称或别名
    
    Returns:
        品牌标准名称，如果未找到返回 None
    """
    if not brand_name:
        return None
    return BRAND_NAME_TO_STANDARD.get(brand_name.lower())


def find_sub_brand_fast(alias: str) -> str:
    """
    O(1) 根据别名查找子品牌（使用哈希索引）
    
    Args:
        alias: 子品牌别名
    
    Returns:
        子品牌标准名称，如果未找到返回 None
    """
    if not alias:
        return None
    return SUB_BRAND_ALIAS_TO_STANDARD.get(alias.lower())


def _find_parent_brand(sub_brand_name: str) -> str:
    """
    根据子品牌名查找所属的主品牌

    Args:
        sub_brand_name: 子品牌标准名

    Returns:
        主品牌标准名，如果未找到返回 None
    """
    for std_brand, info in BRAND_DATABASE_V6.items():
        if sub_brand_name in info.get('sub_brands', {}):
            return std_brand
    return None


def find_any_brand(name: str) -> dict:
    """
    统一品牌查询：同时查主品牌/别名/子品牌

    Args:
        name: 品牌名称或别名

    Returns:
        dict: {
            'found': bool,              # 是否找到
            'standard_name': str|None,  # 主品牌标准名
            'match_type': str|None,     # 'main' | 'alias' | 'sub_brand' | None
            'sub_brand_name': str|None  # 如果是子品牌，子品牌名
        }
    """
    if not name:
        return {'found': False, 'standard_name': None, 'match_type': None, 'sub_brand_name': None}

    key = name.lower()

    # 1. 主品牌名精确匹配（BRAND_DATABASE_V6 的 key 是品牌标准名）
    for std_name in BRAND_DATABASE_V6:
        if std_name.lower() == key:
            return {'found': True, 'standard_name': std_name, 'match_type': 'main', 'sub_brand_name': None}

    # 2. 别名匹配（ALIAS_TO_BRAND 只包含别名，不包含标准名自身）
    std = ALIAS_TO_BRAND.get(key)
    if std:
        return {'found': True, 'standard_name': std, 'match_type': 'alias', 'sub_brand_name': None}

    # 3. 子品牌匹配
    sub = SUB_BRAND_ALIAS_TO_STANDARD.get(key)
    if sub:
        parent = _find_parent_brand(sub)
        return {'found': True, 'standard_name': parent, 'match_type': 'sub_brand', 'sub_brand_name': sub}

    return {'found': False, 'standard_name': None, 'match_type': None, 'sub_brand_name': None}


# 模块加载时自动构建索引
_build_brand_indexes()

# 启动时加载关联关系（子品牌/别名）— 合并到内存
_relations = load_relationships()
if _relations:
    for parent_name, rel in _relations.items():
        if parent_name in BRAND_DATABASE_V6:
            parent = BRAND_DATABASE_V6[parent_name]
            for sub_name, sub_aliases in rel.get('sub_brands', {}).items():
                subs = parent.get('sub_brands', {})
                if sub_name not in subs:
                    subs[sub_name] = list(sub_aliases)
                else:
                    for a in sub_aliases:
                        if a not in subs[sub_name]:
                            subs[sub_name].append(a)
                parent['sub_brands'] = subs
    _build_brand_indexes()

# 启动时加载动态品牌（持久化）— 合并而非覆盖
_dynamic_brands = load_dynamic_brands()
if _dynamic_brands:
    for brand_name, info in _dynamic_brands.items():
        if brand_name in BRAND_DATABASE_V6:
            existing = BRAND_DATABASE_V6[brand_name]
            existing_aliases = existing.get('aliases', [])
            for a in info.get('aliases', []):
                if a not in existing_aliases:
                    existing_aliases.append(a)
            existing['aliases'] = existing_aliases
            if info.get('type', '未知') != '未知':
                existing['type'] = info['type']
            if info.get('country', 'CN') != 'CN':
                existing['country'] = info['country']
            # 合并子品牌
            for sub_name, sub_aliases in info.get('sub_brands', {}).items():
                existing_subs = existing.get('sub_brands', {})
                if sub_name not in existing_subs:
                    existing_subs[sub_name] = sub_aliases
                else:
                    for sa in sub_aliases:
                        if sa not in existing_subs[sub_name]:
                            existing_subs[sub_name].append(sa)
                existing['sub_brands'] = existing_subs
        else:
            # 如果该品牌已是别人的子品牌，不重复添加为独立 key
            if brand_name.lower() in SUB_BRAND_ALIAS_TO_STANDARD:
                continue
            BRAND_DATABASE_V6[brand_name] = info
    _build_brand_indexes()


def find_brand_by_alias(alias: str) -> str:
    """
    根据别名查找品牌（兼容旧版，内部使用哈希索引）
    """
    return find_brand_by_alias_fast(alias)


# ===== 品牌配置管理（类型+国家） =====
import json

BRAND_CONFIG_FILE = Path(__file__).parent / 'brand_config.json'

def _load_brand_config() -> dict:
    """加载品牌配置"""
    if BRAND_CONFIG_FILE.exists():
        with open(BRAND_CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'brand_types': [], 'countries': []}

def _save_brand_config(config: dict):
    """保存品牌配置"""
    _atomic_json_save(BRAND_CONFIG_FILE, config)

def get_brand_config() -> dict:
    """获取完整配置"""
    return _load_brand_config()

def add_brand_type(type_name: str) -> bool:
    """新增品牌类型，返回是否成功"""
    with _save_lock:
        config = _load_brand_config()
        if type_name not in config['brand_types']:
            config['brand_types'].append(type_name)
            config['brand_types'].sort()
            _save_brand_config(config)
            return True
    return False

def delete_brand_type(type_name: str) -> bool:
    """删除品牌类型"""
    with _save_lock:
        config = _load_brand_config()
        if type_name in config['brand_types']:
            config['brand_types'].remove(type_name)
            _save_brand_config(config)
            return True
    return False

def add_country(code: str, name: str) -> bool:
    """新增国家"""
    with _save_lock:
        config = _load_brand_config()
        if not any(c['code'] == code for c in config['countries']):
            config['countries'].append({'code': code, 'name': name})
            config['countries'].sort(key=lambda x: x['code'])
            _save_brand_config(config)
            return True
    return False

def delete_country(code: str) -> bool:
    """删除国家"""
    with _save_lock:
        config = _load_brand_config()
        config['countries'] = [c for c in config['countries'] if c['code'] != code]
        _save_brand_config(config)
    return True
