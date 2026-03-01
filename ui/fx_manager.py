import pygame
import random
from settings import COLORS
from ui.display_manager import display_manager

class FxManager:
    def __init__(self):
        self.particles = []
        self.shakes = {} # 目标: 持斗楢月

    def add_floating_text(self, x, y, text, color_type='damage'):
        color = COLORS.get(color_type, (255, 255, 255))
        # 添加随机偏移和程度不同的延迟，以防止重叠
        x += random.randint(-40, 40)
        y += random.randint(-20, 20)
        delay = random.randint(0, 15) # 等待若干帧后才出现
        self.particles.append({
            'x': x,
            'y': y,
            'text': text,
            'color': color,
            'life': 60,
            'max_life': 60,
            'vy': -2,
            'delay': delay
        })

    def add_shake(self, target_id, duration=15):
        self.shakes[target_id] = duration

    def update(self):
        # 更新粒子
        for p in self.particles:
            if p.get('delay', 0) > 0:
                p['delay'] -= 1
            else:
                p['life'] -= 1
                p['y'] += p['vy']
        self.particles = [p for p in self.particles if p['life'] > 0]
        
        # 更新基位刚化
        keys = list(self.shakes.keys())
        for k in keys:
            self.shakes[k] -= 1
            if self.shakes[k] <= 0:
                del self.shakes[k]

    def draw(self, surface):
        font = display_manager.get_font('large')
        for p in self.particles:
            if p.get('delay', 0) > 0:
                continue
                
            alpha = int(255 * (p['life'] / p['max_life']))
            text_surf = font.render(str(p['text']), True, p['color'])
            text_surf.set_alpha(alpha)
            
            # Simple outline/shadow
            shadow_surf = font.render(str(p['text']), True, (0, 0, 0))
            shadow_surf.set_alpha(alpha)
            
            rect = text_surf.get_rect(center=(p['x'], p['y']))
            surface.blit(shadow_surf, (rect.x + 2, rect.y + 2))
            surface.blit(text_surf, rect)

    def get_shake_offset(self, target_id):
        if target_id in self.shakes:
            return random.randint(-5, 5), random.randint(-5, 5)
        return 0, 0

fx_manager = FxManager()
