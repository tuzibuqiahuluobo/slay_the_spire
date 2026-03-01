import pygame
from settings import LOGICAL_WIDTH, COLORS
from ui.display_manager import display_manager
from utils.resource_manager import resource_manager
from core.config_loader import ConfigLoader

class TopBar:
    def __init__(self, game_state):
        self.gs = game_state
        self.height = 50
        self.rect = pygame.Rect(0, 0, LOGICAL_WIDTH, self.height)
        self.icons = ConfigLoader.get_assets_config().get('ui_icons', {})

    def draw(self, surface):
        # Draw background bar
        pygame.draw.rect(surface, (30, 30, 40, 200), self.rect)
        pygame.draw.line(surface, COLORS['text_gray'], (0, self.height), (LOGICAL_WIDTH, self.height), 2)
        
        font = display_manager.get_font('medium')
        small_font = display_manager.get_font('small')
        
        player = self.gs.player
        
        # 1. Gold
        gold_icon = self.icons.get('gold')
        resource_manager.draw_sprite_or_fallback(surface, gold_icon, (40, 25), "💰", font, COLORS['power'], max_size=(32, 32))
        
        gold_text = str(player.gold)
        gold_surf = font.render(gold_text, True, COLORS['power'])
        surface.blit(gold_surf, (60, 6))
        
        current_x = 60 + gold_surf.get_width() + 20
        
        # 2. Level and Exp
        user_icon = self.icons.get('user')
        current_x += 30 
        resource_manager.draw_sprite_or_fallback(surface, user_icon, (current_x + 16, 25), "👤", font, COLORS['text_white'], max_size=(32, 32))
        
        level_text = f"Lv.{min(999, player.level)}"
        level_surf = font.render(level_text, True, COLORS['text_white'])
        surface.blit(level_surf, (current_x + 40, 6))
        
        # Draw EXP Bar next to level
        exp_bar_x = current_x + 40 + level_surf.get_width() + 20
        exp_bar_w = 200
        exp_bar_h = 20
        exp_bar_y = 15
        
        bg_rect = pygame.Rect(exp_bar_x, exp_bar_y, exp_bar_w, exp_bar_h)
        pygame.draw.rect(surface, (50, 50, 50), bg_rect, border_radius=5)
        
        max_exp = player.get_max_exp()
        fill_w = int(exp_bar_w * (player.exp / max_exp)) if max_exp > 0 else 0
        fill_rect = pygame.Rect(exp_bar_x, exp_bar_y, fill_w, exp_bar_h)
        pygame.draw.rect(surface, COLORS['skill'], fill_rect, border_radius=5)
        
        exp_text = f"{player.exp} / {max_exp}"
        exp_surf = small_font.render(exp_text, True, COLORS['text_white'])
        surface.blit(exp_surf, exp_surf.get_rect(center=bg_rect.center))
        
        # 3. Stage/Floor
        stage_text = f"第 {self.gs.stage} 层"
        stage_surf = font.render(stage_text, True, COLORS['hp'])
        surface.blit(stage_surf, (LOGICAL_WIDTH - stage_surf.get_width() - 100, 6))
        
        # 4. Settings Button (Move to far right)
        setting_icon = self.icons.get('setting_button')
        setting_x = LOGICAL_WIDTH - 50 # 50px margin from right edge
        
        # Draw Setting Icon
        resource_manager.draw_sprite_or_fallback(surface, setting_icon, (setting_x + 16, 25), "⚙️", font, COLORS['text_gray'], max_size=(32, 32))
        
        # Store rect for click detection in main loop
        self.setting_btn_rect = pygame.Rect(setting_x, 0, 50, 50)
