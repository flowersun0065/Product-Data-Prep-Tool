#!/usr/bin/env python3
"""
斜杠品牌模式

处理中英文品牌组合的情况，如 "Tempo/得宝"
格式：(完整名称, 中文名, 英文名)
"""

SLASH_BRAND_PATTERNS = [
    ('Tempo/得宝', '得宝', 'Tempo'),
    ('ARS/安速', '安速', 'ARS'),
    ("Lay's/乐事", '乐事', "Lay's"),
    ('KERASTASE/卡诗', '卡诗', 'KERASTASE'),
    ('LION/狮王', '狮王', 'LION'),
    ('Perrier/巴黎水', '巴黎水', 'Perrier'),
    ('HUGGIES/好奇', '好奇', 'HUGGIES'),
    ('Calbee/卡乐比', '卡乐比', 'Calbee'),
    ('PRESIDENT/总统', '总统', 'PRESIDENT'),
    ('Anchor/安佳', '安佳', 'Anchor'),
    ('LOFTEX/亚光', '亚光', 'LOFTEX'),
    ('EBISU/惠百施', '惠百施', 'EBISU'),
    ('DARLIE/好来', '好来', 'DARLIE'),
    ('Laurier/乐而雅', '乐而雅', 'Laurier'),
    ('Raid/雷达', '雷达', 'Raid'),
    ('UNIQLO/优衣库', '优衣库', 'UNIQLO'),
    ('Colgate/高露洁', '高露洁', 'Colgate'),
    ('Papatonk/啪啪通', '啪啪通', 'Papatonk'),
    ('CIRIO/茄意欧', '茄意欧', 'CIRIO'),
    ("Kiehl's/科颜氏", '科颜氏', "Kiehl's"),
    ('盒马/盒马', '盒马', '盒马'),
    ('SUNTORY/三得利', '三得利', 'SUNTORY'),
    ('花王/KAO', '花王', 'KAO'),
    ('明治/Meiji', '明治', 'Meiji'),
    ('ASAHI/朝日', '朝日', 'ASAHI'),
    ('AXE/斧头牌', '斧头牌', 'AXE'),
    ('Barilla/百味来', '百味来', 'Barilla'),
    # === 补充斜杠品牌模式（覆盖 1600+ 误判商品）===
    ('UCC/悠诗诗', '悠诗诗', 'UCC'),
    ('ROBOROBO/乐博乐博', '乐博乐博', 'ROBOROBO'),
    ('little freddie/小皮', '小皮', 'little freddie'),
    ('Little Freddie/小皮', '小皮', 'Little Freddie'),
    ('D&A/蒂安', '蒂安', 'D&A'),
    ('Arla/阿尔乐', '阿尔乐', 'Arla'),
    ('Aptamil/爱他美', '爱他美', 'Aptamil'),
    ('Loacker/莱家', '莱家', 'Loacker'),
    ('DHC/蝶翠诗', '蝶翠诗', 'DHC'),
    ('Ora2/皓乐齿', '皓乐齿', 'Ora2'),
    ('FRISO PRESTIGE/皇家美素佳儿', '皇家美素佳儿', 'FRISO PRESTIGE'),
    ('Sanpellegrino/圣培露', '圣培露', 'Sanpellegrino'),
    ('SOFY/苏菲', '苏菲', 'SOFY'),
    ('Fanta/芬达', '芬达', 'Fanta'),
    ('MARVIS/玛尔仕', '玛尔仕', 'MARVIS'),
    ('Frosch/福纳丝', '福纳丝', 'Frosch'),
    ('COSTA/咖世家', '咖世家', 'COSTA'),
    ('WonderLab/万益蓝', '万益蓝', 'WonderLab'),
    ("Pic's/皮卡思", '皮卡思', "Pic's"),
    ('LUX/力士', '力士', 'LUX'),
    ('ROZA/露莎士', '露莎士', 'ROZA'),
    ('ANESSA/安热沙', '安热沙', 'ANESSA'),
    ('PHILIPS/飞利浦', '飞利浦', 'PHILIPS'),
    ('RIVSEA/瑞哺哺', '瑞哺哺', 'RIVSEA'),
    ('KODOMO/小王子', '小王子', 'KODOMO'),
    ('Bahlsen/百乐顺', '百乐顺', 'Bahlsen'),
    ('Dettol/滴露', '滴露', 'Dettol'),
    ("Peet's Coffee/皮爷", '皮爷', "Peet's Coffee"),
    ('BRITA/碧然德', '碧然德', 'BRITA'),
    ('Purcotton/全棉时代', '全棉时代', 'Purcotton'),
    ('Centrum/善存', '善存', 'Centrum'),
    ('Voss/芙丝', '芙丝', 'Voss'),
    ('Fino/芬浓', '芬浓', 'Fino'),
    ('Spes/诗裴丝', '诗裴丝', 'Spes'),
    ('COCIO/可酷优', '可酷优', 'COCIO'),
    ('FOURLOKO/四洛克', '四洛克', 'FOURLOKO'),
    ('FREEMORE/自由点', '自由点', 'FREEMORE'),
    ('JohnWest/西部约翰', '西部约翰', 'JohnWest'),
    ('Midea/美的', '美的', 'Midea'),
    ('LURPAK/银宝', '银宝', 'LURPAK'),
    ('Whisper/护舒宝', '护舒宝', 'Whisper'),
    ('RYO/吕', '吕', 'RYO'),
    ('BONGRAIN/博格瑞', '博格瑞', 'BONGRAIN'),
    ('Jelley Brown/界界乐', '界界乐', 'Jelley Brown'),
    ('Doritos/多力多滋', '多力多滋', 'Doritos'),
    ('CPB/肌肤之钥', '肌肤之钥', 'CPB'),
    ('Panasonic/松下', '松下', 'Panasonic'),
    ('Abbott/雅培', '雅培', 'Abbott'),
    ('Vaseline/凡士林', '凡士林', 'Vaseline'),
    ('Pantene/潘婷', '潘婷', 'Pantene'),
    ('Nutella/意榛滋', '意榛滋', 'Nutella'),
    ('TABASCO/辣椒仔', '辣椒仔', 'TABASCO'),
    ('KUYURA/可悠然', '可悠然', 'KUYURA'),
    ('BOURKES/柏克', '柏克', 'BOURKES'),
    ('No Brand/诺倍得', '诺倍得', 'No Brand'),
    ('Wyeth/惠氏', '惠氏', 'Wyeth'),
    ('MISANBROO/米膳葆', '米膳葆', 'MISANBROO'),
    ('LA MER/海蓝之谜', '海蓝之谜', 'LA MER'),
    ('Dr.Cheese/奶酪博士', '奶酪博士', 'Dr.Cheese'),
    ('Herlab/她研社', '她研社', 'Herlab'),
    ('KOTANYI/可达怡', '可达怡', 'KOTANYI'),
    ('Heineken/喜力', '喜力', 'Heineken'),
    ('MAE PLOY/泰娘', '泰娘', 'MAE PLOY'),
    ('S.Pellegrino/圣培露', '圣培露', 'S.Pellegrino'),
    ('Ruffles/莱芙士', '莱芙士', 'Ruffles'),
    ('SENKA/珊珂', '珊珂', 'SENKA'),
    ('LERNA/莱纳', '莱纳', 'LERNA'),
    ('CITTA/西苔', '西苔', 'CITTA'),
    ('DAEWOO/大宇', '大宇', 'DAEWOO'),
    ('Deeyeo/德佑', '德佑', 'Deeyeo'),
    ('KEEPFIT/科普菲', '科普菲', 'KEEPFIT'),
    ('GiGwi/贵为', '贵为', 'GiGwi'),
    ('Polenghi/宝蓝吉', '宝蓝吉', 'Polenghi'),
    ('Crest/佳洁士', '佳洁士', 'Crest'),
    ('Grove/格露芙', '格露芙', 'Grove'),
    ('Tulip/郁金香', '郁金香', 'Tulip'),
    ('ZENS/哲品', '哲品', 'ZENS'),
    ('SIMEITOL/妃美堂', '妃美堂', 'SIMEITOL'),
    ('Schick/舒适', '舒适', 'Schick'),
    ('Gillette/吉列', '吉列', 'Gillette'),
    ('Pampers/帮宝适', '帮宝适', 'Pampers'),
    ('GATSBY/杰士派', '杰士派', 'GATSBY'),
    ('Kiri/凯芮', '凯芮', 'Kiri'),
    ('Twinings/川宁', '川宁', 'Twinings'),
    ('Frey/飞瑞尔', '飞瑞尔', 'Frey'),
    ('Coppertone/确美同', '确美同', 'Coppertone'),
    ('Bundaberg/宾得宝', '宾得宝', 'Bundaberg'),
    ('IL HWA/一和', '一和', 'IL HWA'),
    ('Herbacin/贺本清', '贺本清', 'Herbacin'),
    ("Julie's/茱蒂丝", '茱蒂丝', "Julie's"),
    ('Anlene/安怡', '安怡', 'Anlene'),
    ('SANHO/三禾', '三禾', 'SANHO'),
    ('Jaxcoco/珏士高', '珏士高', 'Jaxcoco'),
    ('Mesuca/麦斯卡', '麦斯卡', 'Mesuca'),
    ('Anker/安克', '安克', 'Anker'),
    ('Full of Hope/希望树', '希望树', 'Full of Hope'),
    ('BIODERMA/贝德玛', '贝德玛', 'BIODERMA'),
    ('Caltrate/钙尔奇', '钙尔奇', 'Caltrate'),
    ('PRAMY/柏瑞美', '柏瑞美', 'PRAMY'),
    ('CLORIS/可伦诗', '可伦诗', 'CLORIS'),
    ("L'occitane/欧舒丹", '欧舒丹', "L'occitane"),
    ('CLEAR/清扬', '清扬', 'CLEAR'),
    ('Torriden/桃瑞', '桃瑞', 'Torriden'),
    ('YSL/圣罗兰', '圣罗兰', 'YSL'),
    ('GIORGIO ARMANI/阿玛尼', '阿玛尼', 'GIORGIO ARMANI'),
    ('AHC/爱和纯', '爱和纯', 'AHC'),
    ('JISSBON/杰士邦', '杰士邦', 'JISSBON'),
    ('Mr Mallo/马洛先生', '马洛先生', 'Mr Mallo'),
    ('Sunbites/一口阳光', '一口阳光', 'Sunbites'),
    ('Hormel/荷美尔', '荷美尔', 'Hormel'),
    ('Bear/小熊', '小熊', 'Bear'),
    ('TUC/闲趣', '闲趣', 'TUC'),
    ('KINCHO/金鸟', '金鸟', 'KINCHO'),
    ('Evian/依云', '依云', 'Evian'),
    ('B&B/保宁', '保宁', 'B&B'),
    ('Cheetos/奇多', '奇多', 'Cheetos'),
    ('FIJI/斐泉', '斐泉', 'FIJI'),
    ('Donlim/东菱', '东菱', 'Donlim'),
    ('GAINES/佳乐滋', '佳乐滋', 'GAINES'),
    ('KISS ME/奇士美', '奇士美', 'KISS ME'),
    ('Stride/炫迈', '炫迈', 'Stride'),
    ('Jeep/吉普', '吉普', 'Jeep'),
    ('KBH/康巴赫', '康巴赫', 'KBH'),
    ("L'OREAL/欧莱雅", '欧莱雅', "L'OREAL"),
    ('Mead Johnson/美赞臣', '美赞臣', 'Mead Johnson'),
    ('LAVAZZA/拉瓦萨', '拉瓦萨', 'LAVAZZA'),
    ('Mcvities/麦维他', '麦维他', 'Mcvities'),
    ('Baci/芭绮', '芭绮', 'Baci'),
    ('JUMINAIRE/悠美芮', '悠美芮', 'JUMINAIRE'),
    ('BEDDYBEAR/杯具熊', '杯具熊', 'BEDDYBEAR'),
    ('ASVEL/阿司倍鹭', '阿司倍鹭', 'ASVEL'),
    ('SPAM/世棒', '世棒', 'SPAM'),
    ('INTEONE/入一', '入一', 'INTEONE'),
    ('VEJECY/维爵士', '维爵士', 'VEJECY'),
    ('Badigo/巴菲高', '巴菲高', 'Badigo'),
    ('P&G/宝洁', '宝洁', 'P&G'),
    ("FOX'S/福克斯", '福克斯', "FOX'S"),
    ('Westinghouse/西屋', '西屋', 'Westinghouse'),
    ('shu uemura/植村秀', '植村秀', 'shu uemura'),
    ('Sherwood/喜屋', '喜屋', 'Sherwood'),
    ('SANA/莎娜', '莎娜', 'SANA'),
    ('Molisana/莫利萨娜', '莫利萨娜', 'Molisana'),
    ('SAKURA TARO/芋太郎', '芋太郎', 'SAKURA TARO'),
    ('Hermes/爱马仕', '爱马仕', 'Hermes'),
    ('Mustela/妙思乐', '妙思乐', 'Mustela'),
    ('JOYU/乐知', '乐知', 'JOYU'),
    ('Pringles/品客', '品客', 'Pringles'),
    ('Greennose/绿鼻子', '绿鼻子', 'Greennose'),
    ('PURPLE FLAME/紫焰', '紫焰', 'PURPLE FLAME'),
    ('Theland/纽仕兰', '纽仕兰', 'Theland'),
    ('Lelch/露安适', '露安适', 'Lelch'),
    ('Listerine/李施德林', '李施德林', 'Listerine'),
    ('RED SEAL/红印', '红印', 'RED SEAL'),
    ('Joyoung/九阳', '九阳', 'Joyoung'),
    ('GUM/康齿家', '康齿家', 'GUM'),
    ('Frisolac PRESTIGE/皇家美素力', '皇家美素力', 'Frisolac PRESTIGE'),
    ('Mr Muscle/威猛先生', '威猛先生', 'Mr Muscle'),
    ('Abib/阿彼芙', '阿彼芙', 'Abib'),
    ('Dove/多芬', '多芬', 'Dove'),
    ('SUPER MILD/恵润', '恵润', 'SUPER MILD'),
    ('KODOMO/小犬王', '小犬王', 'KODOMO'),
    ('GNC/健安喜', '健安喜', 'GNC'),
    ('Meatyway/肉匠', '肉匠', 'Meatyway'),
    ('Venchi/闻绮', '闻绮', 'Venchi'),
    ('Kjeldsens/丹麦蓝罐', '丹麦蓝罐', 'Kjeldsens'),
    ("Hellmann's/好乐门", '好乐门', "Hellmann's"),
    ('GERM/格沵', '格沵', 'GERM'),
    ('Lemmycree/莱米可', '莱米可', 'Lemmycree'),
    ('BANANA TRIP/蕉趣', '蕉趣', 'BANANA TRIP'),
    ('beazero/未零', '未零', 'beazero'),
    ('Dasty/达斯米', '达斯米', 'Dasty'),
    ('Aveeno/艾维诺', '艾维诺', 'Aveeno'),
    ('claynal/莉派', '莉派', 'claynal'),
    ('claynal/矿派', '矿派', 'claynal'),
    ('La Sicilia/西西里', '西西里', 'La Sicilia'),
    ('Pororo/啵乐乐', '啵乐乐', 'Pororo'),
    ('COLOSSUS/巨人', '巨人', 'COLOSSUS'),
    ('Aveda/艾梵达', '艾梵达', 'Aveda'),
    ('SHEBA/希宝', '希宝', 'SHEBA'),
    ('SHISEIDO/资生堂', '资生堂', 'SHISEIDO'),
    ('RedBull/红牛', '红牛', 'RedBull'),
    ("Hell's Kitchen/地狱厨房", '地狱厨房', "Hell's Kitchen"),
    ('SAKURA TARO/樫太郎', '樫太郎', 'SAKURA TARO'),
    ('FrisoPrestige/皇家', '皇家', 'FrisoPrestige'),
    ('Ariul/艾莉儿', '艾莉儿', 'Ariul'),
    ('claynal/黏派', '黏派', 'claynal'),
    ('olayks/立时', '立时', 'olayks'),
    ('Torriden/桃瑞丝', '桃瑞丝', 'Torriden'),
    ('Torriden/桃瑞丹', '桃瑞丹', 'Torriden'),
    ('Torriden/桃瑞朵', '桃瑞朵', 'Torriden'),
    ('Torriden/桃瑞旦', '桃瑞旦', 'Torriden'),
    ('Torriden/桃瑞甸', '桃瑞甸', 'Torriden'),
    ('Torriden/桃瑞德', '桃瑞德', 'Torriden'),
    ('AYNSLEY/安斯丽', '安斯丽', 'AYNSLEY'),
    ('meyarn/米妍', '米妍', 'meyarn'),
    ('Sunity/生和堂', '生和堂', 'Sunity'),
    ('Jingold/津金果', '津金果', 'Jingold'),
    ('HEITMANN/海特曼', '海特曼', 'HEITMANN'),
    ('LU/露怡', '露怡', 'LU'),
    ('PALDO/八道', '八道', 'PALDO'),
    ('Doll/公仔', '公仔', 'Doll'),
    ('Durex/杜蕾斯', '杜蕾斯', 'Durex'),
    ('SANITARIUM/桑塔丽', '桑塔丽', 'SANITARIUM'),
    ('Pulmuone/圃美多', '圃美多', 'Pulmuone'),
    ('Finish/亮碟', '亮碟', 'Finish'),
]


def add_slash_pattern(full_name: str, chinese_name: str, english_name: str):
    """
    添加新的斜杠品牌模式

    Args:
        full_name: 完整名称（如 "Tempo/得宝"）
        chinese_name: 中文名（如 "得宝"）
        english_name: 英文名（如 "Tempo"）
    """
    pattern = (full_name, chinese_name, english_name)
    if pattern not in SLASH_BRAND_PATTERNS:
        SLASH_BRAND_PATTERNS.append(pattern)


def get_slash_pattern_by_chinese(chinese_name: str) -> tuple:
    """
    根据中文名查找斜杠品牌模式

    Args:
        chinese_name: 中文品牌名

    Returns:
        匹配的模式元组，未找到返回 None
    """
    for pattern in SLASH_BRAND_PATTERNS:
        if pattern[1] == chinese_name:
            return pattern
    return None


def get_slash_pattern_by_english(english_name: str) -> tuple:
    """
    根据英文名查找斜杠品牌模式

    Args:
        english_name: 英文品牌名

    Returns:
        匹配的模式元组，未找到返回 None
    """
    for pattern in SLASH_BRAND_PATTERNS:
        if pattern[2] == english_name:
            return pattern
    return None
