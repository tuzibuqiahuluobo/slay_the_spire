import os
import sys

# --- 窗口与分辨率设置 ---
# 逻辑分辨率（基础锚点分辨率）
LOGICAL_WIDTH = 1920
LOGICAL_HEIGHT = 1080

# 默认实际启动分辨率
DEFAULT_WINDOW_WIDTH = 1920
DEFAULT_WINDOW_HEIGHT = 1080

# 最小/最大分辨率限制
MIN_WINDOW_WIDTH = 800
MIN_WINDOW_HEIGHT = 600
MAX_WINDOW_WIDTH = 2560
MAX_WINDOW_HEIGHT = 1440

FPS = 60

# --- 颜色常量 ---
COLORS = {
    "bg_dark": (26, 26, 46),       # 深色背景
    "card_bg": (45, 52, 54),       # 卡牌背景
    "attack": (255, 71, 87),       # 攻击红
    "skill": (30, 144, 255),       # 技能蓝
    "power": (255, 165, 2),        # 能力黄
    "energy": (0, 210, 211),       # 能量青
    "hp": (255, 77, 77),           # 鲜血红
    "block": (116, 185, 255),      # 护盾蓝
    "text_white": (255, 255, 255), # 白字
    "text_gray": (204, 204, 204),  # 灰字
    "black": (0, 0, 0),            # 黑色
    "heal": (46, 204, 113),        # 治疗绿
    "menu_bg": (45, 52, 54),       # 菜单背景
}

# --- 资源路径 ---
if getattr(sys, 'frozen', False):
    # 如果是打包后的 EXE，使用临时解压目录
    BASE_DIR = sys._MEIPASS
else:
    # 否则使用当前文件所在目录
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
IMAGES_DIR = os.path.join(ASSETS_DIR, "images")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")

# 默认字体
# 可以将 "simhei.ttf" 等中文字体放入 assets/fonts/ 中
# 如果找不到，系统会尝试回退到系统内置字体
DEFAULT_FONT_NAME = "simhei.ttf"

# --- 游戏逻辑常量 ---
PLAYER_MAX_HP = 80
PLAYER_MAX_ENERGY = 3
HAND_LIMIT = 10
DRAW_COUNT = 5

# --- 布局常量 (基于 1920x1080 逻辑分辨率) ---
# 战斗顶部区域（敌人）的 Y 轴中心
BATTLE_TOP_Y = 280
# 战斗中部区域（玩家）的 Y 轴中心
BATTLE_MIDDLE_Y = 650
# 底部 UI (能量、手牌) 高度
BOTTOM_UI_HEIGHT = 250
BOTTOM_UI_Y = LOGICAL_HEIGHT - BOTTOM_UI_HEIGHT

# 手牌的逻辑宽高
CARD_WIDTH = 200
CARD_HEIGHT = 280
CARD_HOVER_Y_OFFSET = -80

# 实体间距
ENEMY_GAP = 300
