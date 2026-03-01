import pygame
from settings import *

class DisplayManager:
    def __init__(self):
        pygame.init()
        self.logical_width = LOGICAL_WIDTH
        self.logical_height = LOGICAL_HEIGHT
        
        # 从默认窗口大小开始
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        
        # 设置可调整大小的显示窗口
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("杀戮星光")
        
        # 所有游戏绘制都在这个逻辑表面上进行
        self.surface = pygame.Surface((self.logical_width, self.logical_height))
        
        # 字体字典
        self.fonts = {}
        self.init_fonts()
        
    def init_fonts(self):
        pygame.font.init()
        # 如果找不到特定字体文件，则回退到系统中文字体
        system_fonts = pygame.font.get_fonts()
        chosen_sys_font = "simhei" if "simhei" in system_fonts else ("microsoftyahei" if "microsoftyahei" in system_fonts else None)
        
        font_path = os.path.join(FONTS_DIR, DEFAULT_FONT_NAME)
        
        def load_font(size):
            if os.path.exists(font_path):
                return pygame.font.Font(font_path, size)
            elif chosen_sys_font:
                return pygame.font.SysFont(chosen_sys_font, size)
            else:
                return pygame.font.Font(None, size)
                
        # 注册标准尺寸
        self.fonts['small'] = load_font(24)
        self.fonts['medium'] = load_font(36)
        self.fonts['large'] = load_font(48)
        self.fonts['xlarge'] = load_font(72)
        # 卡牌数字等的字体
        self.fonts['card_title'] = load_font(28)
        self.fonts['card_desc'] = load_font(20)
        self.fonts['card_cost'] = load_font(32)

    def handle_resize(self, new_width, new_height):
        # 强制执行最小尺寸
        self.window_width = max(MIN_WINDOW_WIDTH, new_width)
        self.window_height = max(MIN_WINDOW_HEIGHT, new_height)
        # 这里不严格限制最大尺寸，除非需要，操作系统通常会限制
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)

    def update(self):
        # 计算缩放以将逻辑表面适配到物理窗口中，保持纵横比
        scale_x = self.window_width / self.logical_width
        scale_y = self.window_height / self.logical_height
        scale = min(scale_x, scale_y)
        
        scaled_width = int(self.logical_width * scale)
        scaled_height = int(self.logical_height * scale)
        
        # 将缩放的表面居中
        x_offset = (self.window_width - scaled_width) // 2
        y_offset = (self.window_height - scaled_height) // 2
        
        # 缩放逻辑表面并将其绘制到屏幕
        scaled_surface = pygame.transform.smoothscale(self.surface, (scaled_width, scaled_height))
        
        # 用黑色填充信箱效果
        self.screen.fill((0, 0, 0))
        self.screen.blit(scaled_surface, (x_offset, y_offset))
        pygame.display.flip()
        
    def get_font(self, size_name):
        return self.fonts.get(size_name, self.fonts['medium'])
        
    def logical_to_physical(self, point):
        """不经常用于绘制，但用于输入映射"""
        pass # 在 InputHandler 中实现

display_manager = DisplayManager()
