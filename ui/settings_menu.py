import pygame
import sys
from settings import LOGICAL_WIDTH, LOGICAL_HEIGHT, COLORS
from ui.display_manager import display_manager
from core.audio_manager import audio_manager
from core.localization import localization

class SettingsMenu:
    def __init__(self, game_state):
        self.gs = game_state
        self.active = False
        self.pending_action = None # 用于向主循环传递信号
        
        self.music_volume = 0.5
        self.sfx_volume = 0.7
        
        # 布局参数
        self.center_x = LOGICAL_WIDTH // 2
        self.center_y = LOGICAL_HEIGHT // 2
        self.width = 500
        self.height = 700 
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.rect.center = (self.center_x, self.center_y)
        
        # UI组件初始化
        # 增加按钮宽度以容纳长文本
        self.btn_w = 320
        self.btn_h = 50
        
        self.init_ui_elements()
        self.dragging_slider = None

    def init_ui_elements(self):
        """初始化或刷新UI元素的文本"""
        # 滑块
        self.sliders = {
            'music': {'rect': pygame.Rect(0,0,250,20), 'val': self.music_volume, 'label': localization.get('volume_music')},
            'sfx': {'rect': pygame.Rect(0,0,250,20), 'val': self.sfx_volume, 'label': localization.get('volume_sfx')}
        }
        
        # 按钮列表
        # 顺序: 语言 -> 返回 -> 重开 -> 退出桌面 -> 退出主菜单
        # 注意: 这里使用 localization.get 获取当前语言的文本
        current_lang_name = localization.get(f'lang_{localization.current_language}')
        lang_label = f"{localization.get('lang_prefix')}{current_lang_name}"
        
        self.buttons = [
            {'label': lang_label, 'action': 'toggle_lang', 'rect': pygame.Rect(0,0,self.btn_w,self.btn_h)},
            {'label': localization.get('btn_return_game'), 'action': 'close', 'rect': pygame.Rect(0,0,self.btn_w,self.btn_h)},
            {'label': localization.get('btn_restart_game'), 'action': 'restart_game', 'rect': pygame.Rect(0,0,self.btn_w,self.btn_h)},
            {'label': localization.get('btn_exit_desktop'), 'action': 'exit_desktop', 'rect': pygame.Rect(0,0,self.btn_w,self.btn_h)},
            {'label': localization.get('btn_exit_main_menu'), 'action': 'return_main', 'rect': pygame.Rect(0,0,self.btn_w,self.btn_h)}
        ]

    def open(self):
        self.active = True
        self.pending_action = None
        audio_manager.pause_bgm()
        
    def close(self):
        self.active = False
        self.pending_action = None
        audio_manager.unpause_bgm()

    def handle_event(self, event):
        if not self.active: return False
        
        from utils.input_handler import input_handler
        logical_pos = input_handler.get_logical_mouse_pos(event.pos) if hasattr(event, 'pos') else None
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            if not self.rect.collidepoint(logical_pos):
                self.close() # 点击外部关闭
                return True
                
            # Check sliders
            for key, slider in self.sliders.items():
                handle_rect = self.get_handle_rect(slider)
                bar_rect = slider['rect']
                touch_rect = bar_rect.inflate(0, 30) # 更大的触摸区域
                if touch_rect.collidepoint(logical_pos):
                    self.dragging_slider = key
                    self.update_slider(key, logical_pos[0])
                    return True
            
            # Check buttons
            for btn in self.buttons:
                if btn['rect'].collidepoint(logical_pos):
                    action = btn['action']
                    
                    if action == 'close':
                        self.close()
                    elif action == 'toggle_lang':
                        # 切换语言
                        next_lang = localization.get_next_language()
                        localization.set_language(next_lang)
                        # 刷新所有UI文本
                        self.init_ui_elements()
                    elif action in ['restart_game', 'return_main', 'exit_desktop']:
                        self.close() 
                        self.pending_action = action
                        
                    return True

        elif event.type == pygame.MOUSEBUTTONUP:
            self.dragging_slider = None
            
        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_slider and logical_pos:
                self.update_slider(self.dragging_slider, logical_pos[0])
                
        return True # 拦截所有事件

    def update_slider(self, key, mouse_x):
        slider = self.sliders[key]
        rect = slider['rect']
        
        val = (mouse_x - rect.x) / rect.width
        val = max(0.0, min(1.0, val))
        slider['val'] = val
        
        # 更新内部状态以保持同步
        if key == 'music':
            self.music_volume = val
            audio_manager.set_music_volume(val)
        elif key == 'sfx':
            self.sfx_volume = val
            audio_manager.set_sfx_volume(val)

    def get_handle_rect(self, slider):
        rect = slider['rect']
        handle_x = rect.x + int(rect.width * slider['val'])
        return pygame.Rect(handle_x - 12, rect.centery - 12, 24, 24)

    def draw(self, surface):
        if not self.active: return
        
        # 遮罩
        overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0,0))
        
        # 背景
        pygame.draw.rect(surface, (40, 44, 52), self.rect, border_radius=15)
        pygame.draw.rect(surface, COLORS['text_white'], self.rect, 2, border_radius=15)
        
        font = display_manager.get_font('large')
        small_font = display_manager.get_font('medium')
        
        # 标题
        title_text = localization.get('settings_title')
        title = font.render(title_text, True, COLORS['text_white'])
        surface.blit(title, title.get_rect(center=(self.center_x, self.rect.top + 50)))
        
        current_y = self.rect.top + 110
        
        # 滑块
        for key, slider in self.sliders.items():
            label_surf = small_font.render(slider['label'], True, COLORS['text_white'])
            surface.blit(label_surf, label_surf.get_rect(center=(self.center_x, current_y)))
            current_y += 35
            
            bar_rect = slider['rect']
            bar_rect.centerx = self.center_x
            bar_rect.top = current_y
            
            pygame.draw.rect(surface, (20, 20, 30), bar_rect, border_radius=5)
            
            fill_w = int(bar_rect.width * slider['val'])
            fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, fill_w, bar_rect.height)
            pygame.draw.rect(surface, COLORS['energy'], fill_rect, border_radius=5)
            
            handle_rect = self.get_handle_rect(slider)
            pygame.draw.circle(surface, COLORS['text_white'], handle_rect.center, 12)
            
            current_y += 40
            
        # 按钮
        current_y += 20
        for btn in self.buttons:
            btn_rect = btn['rect']
            btn_rect.center = (self.center_x, current_y + btn_rect.height // 2)
            
            pygame.draw.rect(surface, (60, 64, 72), btn_rect, border_radius=8)
            pygame.draw.rect(surface, (100, 100, 100), btn_rect, 2, border_radius=8)
            
            text_surf = small_font.render(btn['label'], True, COLORS['text_white'])
            surface.blit(text_surf, text_surf.get_rect(center=btn_rect.center))
            
            current_y += 70
