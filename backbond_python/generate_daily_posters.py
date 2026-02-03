#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
旅行日程海报生成器
根据 result.json 中的 daily_plans 生成每日海报
"""

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle
import matplotlib.font_manager as fm
from datetime import datetime
import os
import sys
import base64
from io import BytesIO
from agent import clean_json_markdown

def get_chinese_font():
    """获取系统中可用的中文字体"""
    # 常见中文字体列表（按优先级排序）
    chinese_fonts = [
        'Microsoft YaHei',      # 微软雅黑
        'SimHei',               # 黑体
        'SimSun',               # 宋体
        'KaiTi',                # 楷体
        'FangSong',             # 仿宋
        'STSong',               # 华文宋体
        'STKaiti',              # 华文楷体
        'STHeiti',              # 华文黑体
        'STFangsong',           # 华文仿宋
        'WenQuanYi Micro Hei',  # 文泉驿微米黑（Linux）
        'WenQuanYi Zen Hei',    # 文泉驿正黑（Linux）
        'Noto Sans CJK SC',     # 思源黑体
        'Source Han Sans CN',   # 思源黑体
    ]
    
    # 获取系统所有可用字体
    available_fonts = [f.name for f in fm.fontManager.ttflist]
    
    # 查找第一个可用的中文字体
    for font in chinese_fonts:
        if font in available_fonts:
            print(f"✓ 使用字体: {font}")
            return font
    
    # 如果没有找到预设的中文字体，尝试查找任何包含 'CJK' 或 'Chinese' 的字体
    for font_name in available_fonts:
        if 'CJK' in font_name or 'Chinese' in font_name or 'CN' in font_name:
            print(f"✓ 使用字体: {font_name}")
            return font_name
    
    print("⚠️  警告: 未找到中文字体，可能无法正确显示中文")
    print("\n可用的字体列表:")
    for i, font in enumerate(available_fonts[:20], 1):
        print(f"  {i}. {font}")
    if len(available_fonts) > 20:
        print(f"  ... 还有 {len(available_fonts) - 20} 个字体")
    
    print("\n建议解决方法:")
    print("1. Windows: 系统应该自带微软雅黑或黑体")
    print("2. Mac: 系统应该自带 PingFang SC")
    print("3. Linux: 安装字体 sudo apt-get install fonts-wqy-microhei")
    print("4. 或者下载思源黑体: https://github.com/adobe-fonts/source-han-sans")
    
    return None


# 设置中文字体
chinese_font = get_chinese_font()
if chinese_font:
    plt.rcParams['font.sans-serif'] = [chinese_font, 'DejaVu Sans']
else:
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
    
plt.rcParams['axes.unicode_minus'] = False


class DailyPosterGenerator:
    """每日旅行海报生成器"""
    
    # 配色方案 - 渐变主题色
    COLOR_SCHEMES = [
        {  # Day 1 - 蓝紫渐变
            'primary': '#5B8DEE',
            'secondary': '#8B5FBF',
            'accent': '#F39C6B',
            'bg': '#F8F9FE',
            'text': '#2C3E50',
            'light': '#E8EEF7'
        },
        {  # Day 2 - 橙粉渐变
            'primary': '#FF6B9D',
            'secondary': '#C06C84',
            'accent': '#F67280',
            'bg': '#FFF5F7',
            'text': '#2C3E50',
            'light': '#FFE5EC'
        },
        {  # Day 3 - 绿松石渐变
            'primary': '#4ECDC4',
            'secondary': '#44A08D',
            'accent': '#F7CE68',
            'bg': '#F4FFFE',
            'text': '#2C3E50',
            'light': '#D5F4F1'
        }
    ]
    
    def __init__(self, data_source):
        """初始化生成器
        """
        if isinstance(data_source, str):
            # 文件路径
            self.data = json.loads(data_source)
        elif isinstance(data_source, dict):
            # 直接传入的数据字典
            self.data = data_source
        else:
            raise ValueError("data_source 必须是文件路径(str)或数据字典(dict)")
        
        self.daily_plans = self.data.get('daily_plans', [])
        
    def create_poster(self, day_data, day_index):
        """为单日创建海报"""
        # 获取配色方案
        colors = self.COLOR_SCHEMES[day_index % len(self.COLOR_SCHEMES)]
        
        # 动态计算画布高度
        num_activities = len(day_data['activities'])
        activity_height = 0.95
        spacing = 0.15
        
        # 计算所需总高度
        header_height = 3.5  # 头部区域高度
        footer_height = 2.5  # 底部汇总高度
        activities_section_height = (activity_height) * (num_activities) + 1.0  # 活动区域（包含标题）
        total_height = header_height + activities_section_height + footer_height + 1.0  # 额外留白
        
        # 最小高度14，根据活动数量动态增加
        canvas_height = max(14, total_height)
        
        # 创建画布 - 竖版海报
        fig = plt.figure(figsize=(10, canvas_height), facecolor=colors['bg'])
        ax = fig.add_subplot(111)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, canvas_height)
        ax.axis('off')
        
        # 绘制背景装饰
        self._draw_background_decorations(ax, colors, canvas_height)
        
        # 绘制头部区域
        header_y = canvas_height - 2.2
        self._draw_header(ax, day_data, colors, header_y)
        
        # 绘制活动列表
        activities_start_y = canvas_height - 3.0
        activities_end_y = self._draw_activities(ax, day_data, colors, activities_start_y)
        
        # 绘制底部摘要 - 动态位置
        footer_y = max(2.5, activities_end_y - 0.5)  # 确保不会太靠下
        self._draw_footer(ax, day_data, colors, footer_y)
        
        # 将图片保存到内存并转换为base64
        buffer = BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight', facecolor=colors['bg'])
        plt.close()
        
        # 获取图片数据并编码为base64
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        buffer.close()
        
        print(f"✅ 已生成: Day {day_data['day']} - {day_data['date']}")
        
        return {
            'day': day_data['day'],
            'date': day_data['date'],
            'image_base64': image_base64
        }
    
    def _draw_background_decorations(self, ax, colors, canvas_height):
        """绘制背景装饰元素"""
        # 顶部装饰圆
        circle1 = Circle((8.5, canvas_height - 1), 1.5, color=colors['primary'], alpha=0.15)
        circle2 = Circle((1.5, 1), 1.2, color=colors['secondary'], alpha=0.1)
        ax.add_patch(circle1)
        ax.add_patch(circle2)
        
        # 装饰线条
        # ax.plot([0.5, 9.5], [canvas_height - 1.5, canvas_height - 1.5], color=colors['primary'], 
        #         linewidth=2, alpha=0.3)
        # ax.plot([0.5, 9.5], [2.5, 2.5], color=colors['secondary'], 
        #         linewidth=2, alpha=0.3)
    
    def _draw_header(self, ax, day_data, colors, header_y):
        """绘制头部区域"""
        # 日期标签背景
        header_box = FancyBboxPatch(
            (0.5, header_y), 9, 1.6,
            boxstyle="round,pad=0.1",
            facecolor=colors['primary'],
            edgecolor=colors['secondary'],
            linewidth=2,
            alpha=0.9
        )
        ax.add_patch(header_box)
        
        # Day 标签
        ax.text(1.2, header_y + 1.1, f'DAY {day_data["day"]}',
                fontsize=32, fontweight='bold',
                color='white', va='center')
        
        # 日期
        date_str = datetime.strptime(day_data['date'], '%Y-%m-%d').strftime('%Y年%m月%d日')
        ax.text(1.2, header_y + 0.5, date_str,
                fontsize=18, color='white', va='center', alpha=0.95)
        
        # 装饰圆形图标
        icon_circle = Circle((8.5, header_y + 0.8), 0.35, 
                            color='white', alpha=0.3, linewidth=2, 
                            edgecolor='white', fill=True)
        ax.add_patch(icon_circle)
        ax.text(8.5, header_y + 0.8, '旅', 
                fontsize=24, fontweight='bold',
                color='white', va='center', ha='center', alpha=0.9)
    
    def _draw_activities(self, ax, day_data, colors, start_y):
        """绘制活动列表"""
        activities = day_data['activities']
        activity_height = 0.95
        spacing = 0.15
        
        # 标题
        ax.text(0.8, start_y, '今日行程',
                fontsize=20, fontweight='bold',
                color=colors['text'])
        
        current_y = start_y - 0.5
        
        for idx, activity in enumerate(activities):
            y_pos = current_y - (activity_height + spacing) * idx
            
            # 活动卡片背景
            card = FancyBboxPatch(
                (0.7, y_pos - activity_height), 8.6, activity_height,
                boxstyle="round,pad=0.05",
                facecolor=colors['light'],
                edgecolor=colors['primary'],
                linewidth=1.5,
                alpha=0.8
            )
            ax.add_patch(card)
            
            # 时间标记（使用圆形标记）
            time_marker = Circle((1.0, y_pos - 0.25), 0.08, 
                                color=colors['primary'], alpha=0.8)
            ax.add_patch(time_marker)
            ax.text(1.3, y_pos - 0.25, activity['time'],
                    fontsize=11, fontweight='bold',
                    color=colors['primary'], va='center')
            
            # 活动内容
            activity_text = activity['activity']
            if len(activity_text) > 22:
                activity_text = activity_text
            
            ax.text(0.95, y_pos - 0.5, activity_text,
                    fontsize=10, color=colors['text'], 
                    va='center', fontweight='500')
            
            # 地点（如果有）
            if activity.get('location'):
                location = activity['location']
                if len(location) > 24:
                    location = location[:24] + '...'
                # 地点图标
                loc_marker = Circle((1.0, y_pos - 0.73), 0.05, 
                                   color=colors['secondary'], alpha=0.6)
                ax.add_patch(loc_marker)
                ax.text(1.15, y_pos - 0.73, location,
                        fontsize=8, color=colors['text'], 
                        va='center', alpha=0.7, style='italic')
            
            # 费用标签
            if activity.get('cost', 0) > 0:
                cost_box = FancyBboxPatch(
                    (7.8, y_pos - 0.65), 1.25, 0.35,
                    boxstyle="round,pad=0.03",
                    facecolor=colors['accent'],
                    edgecolor='none',
                    alpha=0.9
                )
                ax.add_patch(cost_box)
                ax.text(8.42, y_pos - 0.48, f'¥{activity["cost"]}',
                        fontsize=10, fontweight='bold',
                        color='white', va='center', ha='center')
        
        # 返回最后一个活动的底部Y坐标
        end_y = current_y - (activity_height + spacing) * len(activities)
        return end_y
    
    def _draw_footer(self, ax, day_data, colors, footer_y):
        """绘制底部摘要信息"""
        # 底部汇总框
        footer_box = FancyBboxPatch(
            (0.7, footer_y - 1.7), 8.6, 1.7,
            boxstyle="round,pad=0.1",
            facecolor='white',
            edgecolor=colors['primary'],
            linewidth=2,
            alpha=0.95
        )
        ax.add_patch(footer_box)
        
        # 标题
        ax.text(1.0, footer_y - 0.2, '当日费用汇总',
                fontsize=16, fontweight='bold',
                color=colors['text'])
        
        # 费用详情
        total_cost = day_data.get('total_day_cost', 0)
        transport_cost = day_data.get('transport_cost', 0)
        accommodation_cost = day_data.get('accommodation_cost', 0)
        
        # 使用文字标签展示
        ax.text(1.2, footer_y - 0.7, '总费用',
                fontsize=12, fontweight='bold', color=colors['text'], va='center')
        ax.text(3.5, footer_y - 0.7, f'¥{total_cost}',
                fontsize=14, fontweight='bold',
                color=colors['accent'], va='center')
        
        ax.text(5.0, footer_y - 0.7, '交通',
                fontsize=12, fontweight='bold', color=colors['text'], va='center')
        ax.text(6.8, footer_y - 0.7, f'¥{transport_cost}',
                fontsize=12, fontweight='bold',
                color=colors['primary'], va='center')
        
        # 住宿信息
        accommodation = day_data.get('accommodation', '无')
        ax.text(1.2, footer_y - 1.3, f'住宿: {accommodation}',
                fontsize=11, fontweight='bold', color=colors['text'], va='center')
        
        if accommodation_cost > 0:
            ax.text(6.8, footer_y - 1.3, f'¥{accommodation_cost}',
                    fontsize=12, fontweight='bold',
                    color=colors['secondary'], va='center')
    
    def generate_all_posters(self):
        """生成所有日期的海报，返回base64编码的图片列表"""
        print("🎨 开始生成旅行日程海报...\n")
        
        generated_posters = []
        for idx, day_data in enumerate(self.daily_plans):
            poster_data = self.create_poster(day_data, idx)
            generated_posters.append(poster_data)
        
        print(f"\n✨ 完成！共生成 {len(generated_posters)} 张海报")
        print("� 返回格式: Base64 编码的图片数据")
        
        return generated_posters


def main():
    """主函数"""
    # JSON 文件路径
    json_path = './result.json'
    DATA = """
    ```json
{
    "daily_plans": [
        {
            "day": 1,
            "date": "2026-01-29",
            "activities": [
                {
                    "time": "14:44",
                    "activity": "乘坐高铁从重庆西站出发前往珠海",
                    "location": "重庆西站",
                    "duration": 7,
                    "cost": 572,
                    "notes": "乘坐G3749次高铁，二等座，建议提前30天预订以获得折扣"
                },
                {
                    "time": "22:05",
                    "activity": "抵达珠海站，前往酒店办理入住",
                    "location": "珠海站",
                    "duration": 1,
                    "cost": 30,
                    "notes": "建议乘坐出租车或网约车前往酒店，费用约30元"
                },
                {
                    "time": "23:00",
                    "activity": "夜宵体验",
                    "location": "酒店附近或夏湾夜市",
                    "duration": 1,
                    "cost": 50,
                    "notes": "可前往夏湾夜市品尝当地小吃，人均消费约50元"
                }
            ],
            "total_day_cost": 652,
            "transport_cost": 602
        },
        {
            "day": 2,
            "date": "2026-01-30",
            "activities": [
                {
                    "time": "09:00",
                    "activity": "早餐",
                    "location": "酒店或附近早餐店",
                    "duration": 1,
                    "cost": 25,
                    "notes": "品尝当地早茶或特色早餐"
                },
                {
                    "time": "10:00",
                    "activity": "游览情侣路，欣赏海滨风光",
                    "location": "珠海市香洲区情侣中路",
                    "duration": 2,
                    "cost": 0,
                    "notes": "沿海滨步道散步，欣赏海景和港珠澳大桥"
                },
                {
                    "time": "12:00",
                    "activity": "参观珠海渔女雕像",
                    "location": "珠海市香洲区情侣中路63号香炉湾畔",
                    "duration": 1,
                    "cost": 0,
                    "notes": "珠海地标性雕塑，拍照打卡胜地"
                },
                {
                    "time": "13:00",
                    "activity": "午餐",
                    "location": "海滨泳场附近餐厅",
                    "duration": 1.5,
                    "cost": 80,
                    "notes": "选择海滨泳场附近的餐厅，品尝海鲜简餐"
                },
                {
                    "time": "14:30",
                    "activity": "海滨泳场休闲",
                    "location": "珠海市香洲区吉大路与情侣中路交叉口东南100米",
                    "duration": 2.5,
                    "cost": 0,
                    "notes": "沙滩漫步，欣赏爱情灯塔，如需游泳或玩水上项目需额外付费"
                },
                {
                    "time": "17:00",
                    "activity": "前往湾仔海鲜街",
                    "location": "珠海市香洲区湾仔海鲜街",
                    "duration": 0.5,
                    "cost": 20,
                    "notes": "乘坐公交或出租车前往，费用约20元"
                },
                {
                    "time": "17:30",
                    "activity": "湾仔海鲜街晚餐",
                    "location": "湾仔海鲜街",
                    "duration": 2,
                    "cost": 120,
                    "notes": "体验现买现做模式，推荐品尝横琴蚝、斗门沙虾等，人均约120元"
                },
                {
                    "time": "19:30",
                    "activity": "返回酒店休息",
                    "location": "酒店",
                    "duration": 0.5,
                    "cost": 20,
                    "notes": "乘坐公交或出租车返回"
                }
            ],
            "total_day_cost": 265,
            "transport_cost": 40
        },
        {
            "day": 3,
            "date": "2026-01-31",
            "activities": [
                {
                    "time": "08:00",
                    "activity": "早餐",
                    "location": "酒店或附近早餐店",
                    "duration": 1,
                    "cost": 25,
                    "notes": "简单早餐，为海岛游做准备"
                },
                {
                    "time": "09:00",
                    "activity": "前往香洲港码头",
                    "location": "香洲港码头",
                    "duration": 0.5,
                    "cost": 25,
                    "notes": "乘坐出租车前往，费用约25元"
                },
                {
                    "time": "10:30",
                    "activity": "乘船前往外伶仃岛",
                    "location": "香洲港码头至外伶仃岛",
                    "duration": 1.5,
                    "cost": 140,
                    "notes": "船票约140元/人（往返），航程约1.5小时，建议提前预订"
                },
                {
                    "time": "12:00",
                    "activity": "抵达外伶仃岛，午餐",
                    "location": "外伶仃岛",
                    "duration": 1.5,
                    "cost": 80,
                    "notes": "在岛上餐厅品尝海鲜三宝：海胆、狗爪螺、将军帽"
                },
                {
                    "time": "13:30",
                    "activity": "环岛游览，参观伶仃峰、沙滩",
                    "location": "外伶仃岛",
                    "duration": 3,
                    "cost": 0,
                    "notes": "登山观景，沙滩漫步，海水清澈见底"
                },
                {
                    "time": "16:30",
                    "activity": "自由活动，休闲放松",
                    "location": "外伶仃岛",
                    "duration": 1.5,
                    "cost": 0,
                    "notes": "可选择垂钓、游泳或在海边咖啡馆休息"
                },
                {
                    "time": "18:00",
                    "activity": "晚餐",
                    "location": "外伶仃岛餐厅",
                    "duration": 1.5,
                    "cost": 100,
                    "notes": "继续品尝岛上海鲜，人均约100元"
                },
                {
                    "time": "19:30",
                    "activity": "乘船返回珠海市区",
                    "location": "外伶仃岛至香洲港",
                    "duration": 1.5,
                    "cost": 0,
                    "notes": "船票已包含在往返费用中"
                },
                {
                    "time": "21:00",
                    "activity": "返回酒店休息",
                    "location": "酒店",
                    "duration": 0.5,
                    "cost": 25,
                    "notes": "从码头乘坐出租车返回酒店"
                }
            ],
            "total_day_cost": 395,
            "transport_cost": 190
        }
    ],
    "total_cost": 4800,
    "accommodation_cost": 1500,
    "attractions": [
        {
            "name": "情侣路",
            "description": "珠海著名的海滨景观大道，沿珠海海岸线蜿蜒，连接多个海滨景点，是观赏海景、散步休闲的理想场所。",
            "price": 0
        },
        {
            "name": "珠海渔女",
            "description": "珠海的地标雕像，建于1982年，高8.7米，重10吨，由70块花岗岩组成，是中国首座大型海滨雕塑，形象源自当地爱情传说。",
            "price": 0
        },
        {
            "name": "海滨泳场",
            "description": "位于珠海市区东侧海岸的沙滩浴场，环境优美，有浴场和水上娱乐设施，附近有临海咖啡店，是市区内看海玩沙的好去处。",
            "price": 0
        },
        {
            "name": "外伶仃岛",
            "description": "位于伶仃洋外围的海岛，面积4.23平方公里，以水清石奇、沙质细腻著称，有伶仃湾、塔湾、大东湾等优质沙滩，海水清澈见底。",
            "price": 140
        }
    ],
    "transport": {
        "long_distance": "重庆西站至珠海站乘坐G3749次高铁，14:44发车，22:05到达，二等座票价572元。建议提前预订。",
        "local": "珠海市内建议使用公交系统（票价2-5元）结合出租车（起步价10元）。前往外伶仃岛需从香洲港乘船，船票约140元往返。"
    },
    "budget_breakdown": {
        "accommodation": 1500,
        "transport": 1200,
        "food": 1000,
        "attractions": 600,
        "shopping": 300,
        "miscellaneous": 200,
        "total": 4800
    },
    "travel_tips": [
        "1. 珠海属亚热带海洋性气候，1月底天气较凉，建议携带外套，注意防风保暖。",
        "2. 海岛游船程约1.5小时，易晕船者建议提前服用晕船药。",
        "3. 湾仔海鲜街用餐时，可先挑选海鲜再找餐厅加工，比直接点菜更经济。",
        "4. 外伶仃岛船票建议提前在线预订，特别是周末和节假日。",
        "5. 珠海日照较强，即使冬季也建议做好防晒措施。",
        "6. 使用公共交通可节省交通费用，珠海公交系统覆盖主要景点。",
        "7. 品尝海鲜时注意选择新鲜食材，避免肠胃不适。",
        "8. 行程安排较为宽松，可根据个人体力和兴趣适当调整。"
    ]
}
```"""
    # if not os.path.exists(json_path):
    #     print(f"❌ 错误: 未找到文件 {json_path}")
    #     return
    daily_plans = json.loads(clean_json_markdown(DATA))
    # 创建生成器并生成海报
    generator = DailyPosterGenerator(daily_plans)
    posters = generator.generate_all_posters()
    
    # 示例：打印每张海报的信息
    for poster in posters:
        print(f"\nDay {poster['day']} ({poster['date']})")
        print(f"Base64 长度: {len(poster['image_base64'])} 字符")
        with open(f'./posters/day_{poster["day"]}.png', 'wb') as f:
            f.write(base64.b64decode(poster['image_base64']))
    return posters


if __name__ == '__main__':
    main()
