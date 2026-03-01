import pygame
from settings import LOGICAL_WIDTH, LOGICAL_HEIGHT, COLORS
from ui.display_manager import display_manager
from utils.resource_manager import resource_manager
from core.audio_manager import audio_manager
from core.data_library import STORE_CONFIG

class StoreScene:
    def __init__(self, game_state):
        self.gs = game_state
        self.background = None
        
        # 弹窗提示相关
        self.flash_message = ""
        self.flash_timer = 0
        
        # 加载背景图
        raw_bg = resource_manager.get_image("background.png")
        if raw_bg:
            self.background = pygame.transform.smoothscale(raw_bg, (LOGICAL_WIDTH, LOGICAL_HEIGHT))
            
        self.setup_ui()
        
    def setup_ui(self):
        # UI 区域设置
        self.card_width = 240
        self.card_height = 340
        self.gap = 50
        
        total_width = 3 * self.card_width + 2 * self.gap
        self.start_x = (LOGICAL_WIDTH - total_width) // 2
        self.start_y = (LOGICAL_HEIGHT - self.card_height) // 2 - 40
        
        # 按钮
        self.buttons = {}
        
        # 刷新按钮
        self.refresh_rect = pygame.Rect(LOGICAL_WIDTH // 2 - 160, LOGICAL_HEIGHT - 120, 140, 50)
        self.buttons['refresh'] = {
            'rect': self.refresh_rect,
            'hover': False
        }
        
        # 离开按钮
        self.leave_rect = pygame.Rect(LOGICAL_WIDTH // 2 + 20, LOGICAL_HEIGHT - 120, 140, 50)
        self.buttons['leave'] = {
            'rect': self.leave_rect,
            'hover': False
        }
        
        self.hovered_item_idx = -1
        
    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            from utils.input_handler import input_handler
            logical_pos = input_handler.get_logical_mouse_pos(event.pos)
            if not logical_pos:
                return None
                
            self.hovered_item_idx = -1
            for i in range(len(self.gs.current_store_items)):
                item_rect = pygame.Rect(self.start_x + i * (self.card_width + self.gap), self.start_y, self.card_width, self.card_height)
                if item_rect.collidepoint(logical_pos):
                    self.hovered_item_idx = i
                    break
                    
            for key, btn in self.buttons.items():
                btn['hover'] = btn['rect'].collidepoint(logical_pos)
                
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            from utils.input_handler import input_handler
            logical_pos = input_handler.get_logical_mouse_pos(event.pos)
            if not logical_pos:
                return None
                
            # 点击商品购买
            for i, item in enumerate(self.gs.current_store_items):
                if item is None: # 已售空
                    continue
                item_rect = pygame.Rect(self.start_x + i * (self.card_width + self.gap), self.start_y, self.card_width, self.card_height)
                if item_rect.collidepoint(logical_pos):
                    self.buy_item(i)
                    return None
                    
            # 点击离开 (优先判断离开，防止事件穿透)
            if self.buttons['leave']['rect'].collidepoint(logical_pos):
                return 'return_to_map'

            # 点击刷新
            if self.buttons['refresh']['rect'].collidepoint(logical_pos):
                self.refresh_store()
                return None
                
        return None

    def buy_item(self, idx):
        item = self.gs.current_store_items[idx]
        price = item.get('base_price', 0)
        
        if self.gs.player.gold >= price:
            self.gs.player.gold -= price
            audio_manager.play_gold_sound()
            
            # 应用效果
            effect_type = item.get('effect_type')
            val = item.get('effect_value', 0)
            
            if effect_type == "level_up":
                self.gs.player.level += val
                if self.gs.on_message: self.gs.on_message(f"等级提升了！当前等级 {self.gs.player.level}")
            elif effect_type == "max_hp_up":
                self.gs.player.max_hp += val
                self.gs.player.hp += val
                if self.gs.on_message: self.gs.on_message(f"最大生命值增加了 {val}！")
            elif effect_type == "full_heal":
                heal_amount = self.gs.player.max_hp - self.gs.player.hp
                self.gs.player.hp = self.gs.player.max_hp
                if self.gs.on_message: self.gs.on_message(f"生命值已完全恢复！")
                
            # 标记为已售空
            self.gs.current_store_items[idx] = None
        else:
            self.flash_message = "金币不足！"
            self.flash_timer = 60
            if self.gs.on_message: self.gs.on_message("金币不足！")
            
    def refresh_store(self):
        max_refreshes = STORE_CONFIG.get('max_refreshes_per_node', 1)
        # 如果次数用尽，直接静默返回，不弹错误
        if self.gs.store_refreshes_used > max_refreshes: 
            # 为什么是 > max_refreshes？因为首次免费，实际上允许的刷新总次数 = max_refreshes + 1 (免费1次+付费max次)
            # 或者我们把 max_refreshes 视作“付费刷新次数上限”，那总共可以刷新 1(免费) + max 次。
            # 为了简便，我们把 0 次视为免费，1次到max次视为付费。
            pass
            
        # 如果当前是首次刷新(0)，则是免费的
        is_free = (self.gs.store_refreshes_used == 0)
        
        # 实际允许刷新的最大次数是 max_refreshes (这里不包括免费，即总共可刷 max_refreshes + 1 次，或者可以定义总次数就是 max_refreshes)
        # 按照约定，我们让总次数 = 1(免费) + 1(付费，默认配置是1) = 2次。
        # 如果已用次数达到了总上限，不能再刷：
        total_allowed = max_refreshes + 1 # 因为有一次额外的免费机会
        if self.gs.store_refreshes_used >= total_allowed:
            return # 静默不弹窗
            
        cost = 0 if is_free else STORE_CONFIG.get('refresh_cost', 10)
        
        if self.gs.player.gold >= cost:
            self.gs.player.gold -= cost
            if cost > 0:
                audio_manager.play_gold_sound()
            self.gs.store_refreshes_used += 1
            self.gs.generate_store_items()
            if self.gs.on_message: self.gs.on_message("商店已刷新！")
        else:
            self.flash_message = "金币不足！"
            self.flash_timer = 60
            if self.gs.on_message: self.gs.on_message("刷新金币不足！")

    def update(self):
        if self.flash_timer > 0:
            self.flash_timer -= 1
        
    def draw(self, surface):
        if self.background:
            surface.blit(self.background, (0, 0))
        else:
            surface.fill((20, 20, 30))
            
        # 遮罩让背景变暗一点点突出商店
        overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        surface.blit(overlay, (0, 0))
            
        font_large = display_manager.get_font('large')
        font_normal = display_manager.get_font('normal')
        font_small = display_manager.get_font('small')
        
        # 顶部标题
        title_surf = font_large.render("神秘商店", True, COLORS['text_white'])
        surface.blit(title_surf, (LOGICAL_WIDTH // 2 - title_surf.get_width() // 2, 80))
        
        # 绘制商品
        for i, item in enumerate(self.gs.current_store_items):
            x = self.start_x + i * (self.card_width + self.gap)
            y = self.start_y
            rect = pygame.Rect(x, y, self.card_width, self.card_height)
            
            if item is None:
                # 已售空
                pygame.draw.rect(surface, (50, 50, 50), rect, border_radius=10)
                pygame.draw.rect(surface, (30, 30, 30), rect, 3, border_radius=10)
                sold_surf = font_large.render("已售空", True, (100, 100, 100))
                surface.blit(sold_surf, (x + self.card_width//2 - sold_surf.get_width()//2, y + self.card_height//2 - 20))
                continue
                
            # 正常商品背景
            is_hover = self.hovered_item_idx == i
            bg_color = (60, 60, 80) if is_hover else (40, 40, 50)
            pygame.draw.rect(surface, bg_color, rect, border_radius=10)
            
            border_color = COLORS.get('power', (255, 215, 0)) if is_hover else COLORS.get('ui_border', (100, 100, 120))
            pygame.draw.rect(surface, border_color, rect, 3, border_radius=10)
            
            # 商品名字
            # 尽量使用中文或者按需语言
            name = item.get('name_zh', item.get('name_en', 'Item'))
            name_surf = font_normal.render(name, True, COLORS['text_white'])
            surface.blit(name_surf, (x + self.card_width//2 - name_surf.get_width()//2, y + 20))
            
            # 分割线
            pygame.draw.line(surface, COLORS.get('ui_border', (100, 100, 120)), (x + 20, y + 60), (x + self.card_width - 20, y + 60), 2)
            
            # 商品描述（简单换行）
            desc = item.get('description_zh', '')
            desc_y = y + 80
            current_line = ""
            for char in desc:
                test_line = current_line + char
                if font_small.size(test_line)[0] > self.card_width - 40:
                    l_surf = font_small.render(current_line, True, COLORS['text_gray'])
                    surface.blit(l_surf, (x + 20, desc_y))
                    desc_y += 25
                    current_line = char
                else:
                    current_line = test_line
            if current_line:
                l_surf = font_small.render(current_line, True, COLORS['text_gray'])
                surface.blit(l_surf, (x + 20, desc_y))
                
            # 价格
            price = item.get('base_price', 0)
            can_afford = self.gs.player.gold >= price
            price_color = COLORS.get('power', (255, 215, 0)) if can_afford else COLORS.get('danger', (255, 50, 50))
            price_surf = font_large.render(f"{price} G", True, price_color)
            surface.blit(price_surf, (x + self.card_width//2 - price_surf.get_width()//2, y + self.card_height - 50))
            
        # 绘制按钮
        # 刷新按钮
        max_refreshes = STORE_CONFIG.get('max_refreshes_per_node', 1)
        total_allowed = max_refreshes + 1 # 1免费 + max付费
        is_free = (self.gs.store_refreshes_used == 0)
        refresh_cost = 0 if is_free else STORE_CONFIG.get('refresh_cost', 10)
        
        has_attempts = self.gs.store_refreshes_used < total_allowed
        can_afford = self.gs.player.gold >= refresh_cost
        can_refresh = has_attempts and can_afford
        
        r_rect = self.buttons['refresh']['rect']
        r_color = (60, 60, 80) if self.buttons['refresh']['hover'] and can_refresh else (40, 40, 50)
        pygame.draw.rect(surface, r_color, r_rect, border_radius=5)
        r_border = COLORS.get('power', (255, 215, 0)) if can_refresh else (100, 100, 100)
        pygame.draw.rect(surface, r_border, r_rect, 2, border_radius=5)
        
        if not has_attempts:
            r_text = "无法刷新"
        elif is_free:
            r_text = "刷新 (免费)"
        else:
            r_text = f"刷新 ({refresh_cost}G)"
            
        r_surf = font_normal.render(r_text, True, COLORS['text_white'] if can_refresh else (150, 150, 150))
        surface.blit(r_surf, (r_rect.x + r_rect.width//2 - r_surf.get_width()//2, r_rect.y + 15))
        
        # 离开按钮
        l_rect = self.buttons['leave']['rect']
        l_color = (100, 50, 50) if self.buttons['leave']['hover'] else (80, 40, 40)
        pygame.draw.rect(surface, l_color, l_rect, border_radius=5)
        pygame.draw.rect(surface, COLORS.get('danger', (255, 50, 50)), l_rect, 2, border_radius=5)
        
        l_surf = font_normal.render("离开商店", True, COLORS['text_white'])
        surface.blit(l_surf, (l_rect.x + l_rect.width//2 - l_surf.get_width()//2, l_rect.y + 15))
        
        # 绘制临时弹窗消息（如金币不足）
        if self.flash_timer > 0:
            # 透明度渐变效果
            alpha = min(255, self.flash_timer * 8)
            msg_surf = font_large.render(self.flash_message, True, COLORS.get('danger', (255, 50, 50)))
            msg_surf.set_alpha(alpha)
            
            # 添加一点背景使其更醒目
            bg_rect = msg_surf.get_rect(center=(LOGICAL_WIDTH//2, LOGICAL_HEIGHT//2))
            bg_rect.inflate_ip(40, 20)
            bg_surf = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
            bg_surf.fill((0, 0, 0, min(180, alpha)))
            
            surface.blit(bg_surf, bg_rect)
            surface.blit(msg_surf, msg_surf.get_rect(center=(LOGICAL_WIDTH//2, LOGICAL_HEIGHT//2)))
