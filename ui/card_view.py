import pygame
from settings import *
from ui.display_manager import display_manager

class CardView:
    def __init__(self, card, index):
        self.card = card
        self.index = index
        self.width = CARD_WIDTH
        self.height = CARD_HEIGHT
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        
        # 位置状态
        self.base_y = BOTTOM_UI_Y - self.height // 2
        self.target_x = 0
        self.target_y = self.base_y
        self.current_x = 0
        self.current_y = self.base_y
        
        # 缩放状态（用于悬停放大）
        self.scale = 1.0
        self.target_scale = 1.0
        
        # 旋转状态（角度制）
        self.angle = 0.0
        self.target_angle = 0.0
        
        self.is_hovered = False
        self.is_dragging = False
        
    def update_target_position(self, x, y):
        self.target_x = x
        self.target_y = y
        
    def update(self):
        # 朝目标位置插值
        if not self.is_dragging:
            # 加快插值速度（从0.2改为0.25）使动画更响应
            self.current_x += (self.target_x - self.current_x) * 0.25
            self.current_y += (self.target_y - self.current_y) * 0.25
            # 缩放插值
            self.scale += (self.target_scale - self.scale) * 0.2
            # 角度插值
            self.angle += (self.target_angle - self.angle) * 0.2
            
        # 计算缩放后的矩形大小 (用于碰撞检测)
        # 注意：这里我们保持 rect 为非旋转状态，以便鼠标交互更稳定
        # 只有在绘制时才应用旋转
        scaled_w = int(self.width * self.scale)
        scaled_h = int(self.height * self.scale)
        self.rect.width = scaled_w
        self.rect.height = scaled_h
        self.rect.center = (self.current_x, self.current_y)
    
    def draw_card_content(self, surface, width, height, strength, weak):
        """绘制未旋转、未缩放的卡牌内容到指定 surface"""
        # 卡牌矩形（相对于 surface (0,0)）
        card_rect = pygame.Rect(0, 0, width, height)
        
        # 背景
        color = COLORS['card_bg']
        if self.is_hovered and not self.is_dragging:
            color = (55, 62, 64)
            
        pygame.draw.rect(surface, color, card_rect, border_radius=12)
        
        # 边框
        border_color = COLORS.get(self.card.type, COLORS['text_white'])
        if self.is_hovered:
            border_color = COLORS['energy']
        pygame.draw.rect(surface, border_color, card_rect, width=3, border_radius=12)
        
        # 顶部类型线
        top_line = pygame.Rect(0, 0, width, 10)
        pygame.draw.rect(surface, COLORS.get(self.card.type, COLORS['text_gray']), top_line, border_top_left_radius=12, border_top_right_radius=12)

        # 成本圆圈 - 移动到更靠内的位置以避免被圆角遮挡 (从 -10,-10 改为 5,5)
        cost_rect = pygame.Rect(5, 5, 36, 36) #稍微调小一点圆圈以便更精致
        pygame.draw.circle(surface, COLORS['energy'], cost_rect.center, 18)
        pygame.draw.circle(surface, COLORS['text_white'], cost_rect.center, 18, width=2)
        
        font_cost = display_manager.get_font('card_cost')
        cost_surf = font_cost.render(str(self.card.cost), True, COLORS['black'])
        surface.blit(cost_surf, cost_surf.get_rect(center=cost_rect.center))
        
        # 名称 - 稍微下移
        font_name = display_manager.get_font('card_title')
        name_surf = font_name.render(self.card.name, True, COLORS['text_white'])
        surface.blit(name_surf, name_surf.get_rect(center=(width // 2, 35)))
        
        # 名称下方的线
        pygame.draw.line(surface, COLORS['text_gray'], (25, 55), (width - 25, 55))
        
        # 描述
        font_desc = display_manager.get_font('card_desc')
        desc_text = self.card.get_desc(strength, weak)
        
        # 文本换行 - 减小最大宽度以增加边距
        lines = []
        current_line = ""
        max_width = width - 40 # 增加内边距
        
        for char in desc_text:
            test_line = current_line + char
            if font_desc.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
            
        y_offset = 80
        for line in lines:
            desc_surf = font_desc.render(line.strip(), True, COLORS['text_gray'])
            surface.blit(desc_surf, desc_surf.get_rect(center=(width // 2, y_offset)))
            y_offset += 25

    def draw(self, surface, strength=0, weak=0):
        # 1. 创建临时 Surface 绘制原始卡牌
        # 使用 SRCALPHA 确保透明背景
        temp_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.draw_card_content(temp_surf, self.width, self.height, strength, weak)
        
        # 2. 应用缩放和旋转
        # rotozoom(Surface, angle, scale) -> Surface
        # 注意：angle 是逆时针度数
        rotated_surf = pygame.transform.rotozoom(temp_surf, self.angle, self.scale)
        
        # 3. 计算绘制位置使其居中
        # 获取旋转后图像的矩形，并将其中心对齐到 current_x, current_y
        draw_rect = rotated_surf.get_rect(center=(self.current_x, self.current_y))
        
        # 4. 绘制到屏幕
        surface.blit(rotated_surf, draw_rect)
