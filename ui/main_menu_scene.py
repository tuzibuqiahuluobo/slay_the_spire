import pygame
import os
from settings import LOGICAL_WIDTH, LOGICAL_HEIGHT, COLORS
from ui.display_manager import display_manager
from utils.resource_manager import resource_manager
from core.audio_manager import audio_manager
from core.localization import localization

import json

class MainMenuScene:
    def __init__(self, game_state):
        self.gs = game_state
        self.background = None
        
        # 加载游戏信息配置
        self.game_info = {}
        try:
            with open('data/game_info.json', 'r', encoding='utf-8') as f:
                self.game_info = json.load(f)
        except Exception as e:
            print(f"Failed to load game info: {e}")
            
        self.version_text = self.game_info.get("game_version", "1.0.0")
        
        # 弹窗相关状态
        self.show_info_window = False
        self.scroll_y = 0
        self.is_dragging = False
        self.last_mouse_y = 0
        self.max_scroll_y = 0
        self.info_content_surface = None
        
        # 信息按钮状态
        self.info_btn_hover = False
        self.info_btn_rect = pygame.Rect(LOGICAL_WIDTH - 60, LOGICAL_HEIGHT - 60, 48, 48)

        # 加载背景图
        raw_bg = resource_manager.get_image("fontground.png")
        if raw_bg:
            self.background = pygame.transform.smoothscale(raw_bg, (LOGICAL_WIDTH, LOGICAL_HEIGHT))
            
        self.buttons = []
        self.last_lang = None
        self.setup_buttons()
        
        # 播放 BGM
        audio_manager.play_bgm()

    def setup_buttons(self):
        self.last_lang = localization.current_language
        self.buttons = []
        center_x = LOGICAL_WIDTH // 2
        start_y = LOGICAL_HEIGHT // 2 + 50
        gap = 70
        
        # 按钮文本逻辑
        start_key = 'menu_start'
        
        # 检查存档是否存在
        has_save_file = os.path.exists('savegame.pkl')
        
        # 按钮列表：开始，保存，载入，设置，退出
        # 注意：用户要求 Load 在 Save 下面
        btn_config = [
            {'text': localization.get(start_key), 'action': 'start_game'},
            {'text': localization.get('menu_save'), 'action': 'save_game'},
            {'text': localization.get('menu_load'), 'action': 'load_game', 'disabled': not has_save_file},
            {'text': localization.get('menu_settings'), 'action': 'settings'},
            {'text': localization.get('menu_quit'), 'action': 'quit_game'}
        ]
        
        font = display_manager.get_font('xlarge')
        
        for idx, cfg in enumerate(btn_config):
            y = start_y + idx * gap
            
            color = COLORS['text_white']
            if cfg.get('disabled', False):
                color = COLORS['text_gray']
                
            self.buttons.append({
                'text': cfg['text'],
                'action': cfg['action'],
                'rect': pygame.Rect(0, 0, 300, 60), # 临时，draw时会更新
                'center': (center_x, y),
                'color': color,
                'hover': False,
                'disabled': cfg.get('disabled', False)
            })

    def get_info_content_surface(self):
        if self.info_content_surface:
            return self.info_content_surface
            
        font = display_manager.get_font('small') # 把文本稍微变小一些
        title_font = display_manager.get_font('normal')
        game_title_font = display_manager.get_font('large')
        
        width = 800
        padding = 40
        safe_width = width - padding * 2 - 40 # 加大安全边距防超框
        y = padding
        
        # 准备内容行
        surfaces = []
        
        # 游戏名称
        name = self.game_info.get("game_name", "Unknown Game")
        surf = game_title_font.render(name, True, COLORS['text_white'])
        surfaces.append((surf, y))
        y += surf.get_height() + 15
        
        # 制作组
        dev = "制作组: " + self.game_info.get("developer_team", "Unknown")
        surf = title_font.render(dev, True, COLORS['text_gray'])
        surfaces.append((surf, y))
        y += surf.get_height() + 25
        
        # 说明文字（需要换行）
        desc = self.game_info.get("game_description", "")
        lines = []
        for paragraph in desc.split('\n'):
            if not paragraph:
                lines.append("")
                continue
            current_line = ""
            for char in paragraph:
                test_line = current_line + char
                test_surf = font.render(test_line, True, COLORS['text_white'])
                if test_surf.get_width() > safe_width:
                    lines.append(current_line)
                    current_line = char
                else:
                    current_line = test_line
            if current_line:
                lines.append(current_line)
                
        for line in lines:
            if line:
                surf = font.render(line, True, COLORS['text_white'])
                surfaces.append((surf, y))
                y += surf.get_height() + 8
            else:
                y += font.get_linesize() // 2 # 空行高度
                
        # 结尾留白
        y += padding
        
        # 创建总Surface
        self.info_content_surface = pygame.Surface((width, y), pygame.SRCALPHA)
        for surf, sy in surfaces:
            self.info_content_surface.blit(surf, (padding, sy))
            
        # 计算最大滚动高度
        visible_height = 600 - 60 # 弹窗高度减去顶部栏
        self.max_scroll_y = max(0, y - visible_height)
        return self.info_content_surface

    def handle_event(self, event):
        if self.show_info_window:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    from utils.input_handler import input_handler
                    logical_pos = input_handler.get_logical_mouse_pos(event.pos)
                    if not logical_pos:
                        return None
                        
                    # 检查是否点击关闭按钮 (弹窗尺寸 800x600)
                    close_rect = pygame.Rect(LOGICAL_WIDTH//2 + 400 - 50, LOGICAL_HEIGHT//2 - 300 + 25, 30, 30)
                    if close_rect.collidepoint(logical_pos):
                        self.show_info_window = False
                        self.is_dragging = False
                        return None
                        
                    # 检查是否点击内容区域用于拖拽
                    content_rect = pygame.Rect(LOGICAL_WIDTH//2 - 400, LOGICAL_HEIGHT//2 - 300 + 80, 800, 520)
                    if content_rect.collidepoint(logical_pos):
                        self.is_dragging = True
                        self.last_mouse_y = logical_pos[1]
                        
                elif event.button == 4: # 滚轮上滑
                    self.scroll_y = max(0, self.scroll_y - 30)
                elif event.button == 5: # 滚轮下滑
                    self.scroll_y = min(self.max_scroll_y, self.scroll_y + 30)
                    
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.is_dragging = False
                    
            elif event.type == pygame.MOUSEMOTION:
                if self.is_dragging:
                    from utils.input_handler import input_handler
                    logical_pos = input_handler.get_logical_mouse_pos(event.pos)
                    if logical_pos:
                        dy = logical_pos[1] - self.last_mouse_y
                        self.scroll_y = max(0, min(self.max_scroll_y, self.scroll_y - dy))
                        self.last_mouse_y = logical_pos[1]
            return None

        if event.type == pygame.MOUSEMOTION:
            from utils.input_handler import input_handler
            logical_pos = input_handler.get_logical_mouse_pos(event.pos)
            
            if logical_pos:
                self.info_btn_hover = self.info_btn_rect.collidepoint(logical_pos)
                for btn in self.buttons:
                    # 如果禁用，跳过悬停效果
                    if btn['disabled']: 
                        continue
                        
                    if btn['rect'].collidepoint(logical_pos):
                        btn['hover'] = True
                        btn['color'] = COLORS['power'] # Gold color for hover
                    else:
                        btn['hover'] = False
                        btn['color'] = COLORS['text_white']
                        
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            from utils.input_handler import input_handler
            logical_pos = input_handler.get_logical_mouse_pos(event.pos)
            
            if logical_pos:
                if self.info_btn_rect.collidepoint(logical_pos):
                    self.show_info_window = True
                    self.scroll_y = 0
                    return None
                    
                for btn in self.buttons:
                    if btn['disabled']:
                        continue
                        
                    if btn['rect'].collidepoint(logical_pos):
                        return btn['action']
        return None

    def update(self):
        # 检查语言是否改变，如果改变则刷新按钮
        if self.last_lang != localization.current_language:
            self.setup_buttons()
        # 也可以在这里检查存档文件状态变化(例如刚刚保存了)，但一般不需要每帧检查

    def draw(self, surface):
        # 绘制背景
        if self.background:
            surface.blit(self.background, (0, 0))
        else:
            surface.fill((20, 20, 30))
            
        font = display_manager.get_font('large')
        
        for btn in self.buttons:
            text_surf = font.render(btn['text'], True, btn['color'])
            btn['rect'] = text_surf.get_rect(center=btn['center'])
            
            # 简单的阴影效果 (禁用状态不画阴影或画淡点)
            if not btn['disabled']:
                shadow_surf = font.render(btn['text'], True, (0, 0, 0))
                surface.blit(shadow_surf, (btn['rect'].x + 2, btn['rect'].y + 2))
            
            surface.blit(text_surf, btn['rect'])
            
            # 如果鼠标悬停，画个左侧的小图标装饰
            if btn['hover'] and not btn['disabled']:
                icon_surf = font.render(">", True, btn['color'])
                surface.blit(icon_surf, (btn['rect'].left - 30, btn['rect'].y))
                
        # 绘制左下角版本号
        v_font = display_manager.get_font('normal')
        v_surf = v_font.render(self.version_text, True, COLORS['text_gray'])
        surface.blit(v_surf, (10, LOGICAL_HEIGHT - v_surf.get_height() - 10))
        
        # 绘制右下角信息按钮
        # 如果资源管理器没有获取到图标，使用pygame原生加载来确保加载成功
        icon = resource_manager.get_image("game_read.png")
        if not icon:
            try:
                icon_path = os.path.join("assets", "images", "icons", "game_read.png")
                icon = pygame.image.load(icon_path).convert_alpha()
            except Exception as e:
                print(f"Failed to load game info icon directly: {e}")

        if icon:
            scaled_icon = pygame.transform.smoothscale(icon, (48, 48))
            if self.info_btn_hover:
                glow = pygame.Surface((56, 56), pygame.SRCALPHA)
                pygame.draw.circle(glow, (255, 215, 0, 100), (28, 28), 28)
                surface.blit(glow, (self.info_btn_rect.x - 4, self.info_btn_rect.y - 4))
            surface.blit(scaled_icon, self.info_btn_rect)
        else:
            pygame.draw.rect(surface, COLORS.get('power', (255,215,0)) if self.info_btn_hover else COLORS.get('ui_bg', (30,30,40)), self.info_btn_rect)
            
        # 绘制信息弹窗
        if self.show_info_window:
            # 半透明遮罩
            overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            surface.blit(overlay, (0, 0))
            
            # 弹窗背景 (800x600)
            win_rect = pygame.Rect(LOGICAL_WIDTH//2 - 400, LOGICAL_HEIGHT//2 - 300, 800, 600)
            pygame.draw.rect(surface, COLORS.get('ui_bg', (30,30,40)), win_rect)
            pygame.draw.rect(surface, COLORS.get('ui_border', (100,100,120)), win_rect, 2)
            
            # 弹窗顶部栏
            top_rect = pygame.Rect(win_rect.x, win_rect.y, win_rect.width, 50)
            pygame.draw.rect(surface, (50, 50, 60), top_rect)
            pygame.draw.line(surface, COLORS.get('ui_border', (100,100,120)), (win_rect.x, win_rect.y + 50), (win_rect.right, win_rect.y + 50), 2)
            
            # 标题
            title_surf = display_manager.get_font('large').render("关于游戏", True, COLORS['text_white'])
            surface.blit(title_surf, (win_rect.x, win_rect.y ))
            
            # 关闭按钮
            close_rect = pygame.Rect(win_rect.right - 40, win_rect.y + 10, 30, 30)
            mouse_pos = pygame.mouse.get_pos()
            try:
                from utils.input_handler import input_handler
                logical_pos = input_handler.get_logical_mouse_pos(mouse_pos)
                is_hover_close = close_rect.collidepoint(logical_pos) if logical_pos else False
            except:
                is_hover_close = False
                
            close_color = COLORS.get('danger', (255, 50, 50)) if is_hover_close else COLORS.get('text_gray', (150, 150, 150))
            pygame.draw.line(surface, close_color, (close_rect.x, close_rect.y), (close_rect.right, close_rect.bottom), 3)
            pygame.draw.line(surface, close_color, (close_rect.right, close_rect.y), (close_rect.x, close_rect.bottom), 3)
            
            # 内容区域
            content_surf = self.get_info_content_surface()
            view_rect = pygame.Rect(0, self.scroll_y, win_rect.width, win_rect.height - 60)
            
            # 确保 view_rect 在 content_surf 范围内
            if view_rect.bottom > content_surf.get_height():
                view_rect.height = max(0, content_surf.get_height() - view_rect.top)
                
            if view_rect.height > 0:
                sub_surf = content_surf.subsurface(view_rect)
                surface.blit(sub_surf, (win_rect.x, win_rect.y + 60))
