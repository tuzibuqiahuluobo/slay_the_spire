import pygame
import math
from settings import *
from ui.display_manager import display_manager
from ui.card_view import CardView
from ui.fx_manager import fx_manager
from utils.input_handler import input_handler
from utils.resource_manager import resource_manager
from core.config_loader import ConfigLoader
from core.audio_manager import audio_manager

class BattleScene:
    def __init__(self, game_state):
        self.gs = game_state
        self.card_views = []
        
        self.dragged_card_idx = -1
        self.drag_start_pos = None
        self.mouse_pos = (0, 0)
        
        self.selected_enemy_idx = 0
        self.selected_friendly_target = 'player'
        
        # 碰撞检测用的矩形
        self.enemy_rects = []
        self.player_rect = pygame.Rect(LOGICAL_WIDTH//2 - 100, BATTLE_MIDDLE_Y - 100, 100, 100)
        # 召唤物位置改为与玩家垂直对齐
        self.summon_rect = pygame.Rect(LOGICAL_WIDTH//2 + 200, BATTLE_MIDDLE_Y - 100, 100, 100)
        
        self.end_turn_btn = pygame.Rect(LOGICAL_WIDTH - 250, LOGICAL_HEIGHT - 150, 200, 60)
        
        # 绑定回调
        self.gs.on_damage = self.on_damage
        self.gs.on_heal = self.on_heal
        self.gs.on_block = self.on_block
        self.gs.on_message = self.on_message
        
        self.message_text = ""
        self.message_timer = 0
        
        self.hover_pile = None # '抽牌堆'或'手牌堆'
        self.hover_summon = False  # 提示文字悬停标签
        
        self.hovered_card_idx = -1  # 当前悬停的卡牌索引
        
        self.background = None
        bg_img = resource_manager.get_image("ttk_background.png")
        if not bg_img:
            try:
                import os
                path = os.path.join("assets", "images", "ttk_background.png")
                if os.path.exists(path):
                    bg_img = pygame.image.load(path).convert_alpha()
            except:
                pass
                
        if bg_img:
            self.background = pygame.transform.smoothscale(bg_img, (LOGICAL_WIDTH, LOGICAL_HEIGHT))
        else:
            # Fallback
            fallback_img = resource_manager.get_image("background.png")
            if fallback_img:
                self.background = pygame.transform.smoothscale(fallback_img, (LOGICAL_WIDTH, LOGICAL_HEIGHT))
        
        self.sync_hand()
        
    def on_damage(self, target, amount, type_):
        rect = self.get_rect_for_target(target)
        fx_manager.add_floating_text(rect.centerx, rect.top, f"-{amount}", 'hp')
        fx_manager.add_shake(target, 15)
        
    def on_heal(self, target, amount):
        rect = self.get_rect_for_target(target)
        fx_manager.add_floating_text(rect.centerx, rect.top, f"+{amount}", 'heal')
        
    def on_block(self, target, amount):
        rect = self.get_rect_for_target(target)
        fx_manager.add_floating_text(rect.centerx, rect.top, f"🛡️{amount}", 'block')

    def on_message(self, msg):
        self.message_text = msg
        self.message_timer = 90 # 1.5秒
        
    def get_rect_for_target(self, target):
        if target == self.gs.player: return self.player_rect
        if target == self.gs.player.summon: return self.summon_rect
        for i, e in enumerate(self.gs.enemies):
            if target == e: return self.enemy_rects[i]
        return self.player_rect
    
    def calculate_fan_layout(self, hovered_idx):
        """计算卡牌扇形展开的目标位置和缩放 - 像扑克牌/扇子一样打开"""
        num_cards = len(self.card_views)
        if num_cards == 0 or hovered_idx < 0 or hovered_idx >= num_cards:
            return
        
        # 扇形展开参数
        center_x = LOGICAL_WIDTH // 2
        # 增加半径使弧度更平缓 (像手中的扑克牌)
        radius = 1200  
        # 调整圆心位置以匹配大半径 (center_y - radius ≈ 卡牌显示位置)
        center_y = BOTTOM_UI_Y + radius + 100
        
        # 总展开角度（度数）
        if num_cards == 1:
            angle_span = 0
            angle_step = 0
        else:
            # 计算每张卡牌需要的角度步长
            # 假设卡牌宽度的一半 (100px) 是理想的间距 (重叠50%)
            # 弧长 = R * angle_rad => angle_rad = arc_len / R
            # 想要间距约 100px (重叠一半): angle_rad = 100 / 1200 ≈ 0.083 rad ≈ 4.7度
            # 想要间距约 60px (重叠更多): angle_rad = 60 / 1200 = 0.05 rad ≈ 2.8度
            # 让我们尝试每张卡大约 5-6 度
            angle_per_card = 6.0
            angle_span = angle_per_card * (num_cards - 1)
            # 限制最大展开角度，避免太多卡时散太开
            angle_span = min(60, angle_span)
            angle_step = angle_span / (num_cards - 1) if num_cards > 1 else 0
        
        for i, cv in enumerate(self.card_views):
            # 计算该卡牌在扇形中的角度
            if num_cards == 1:
                angle_deg = -90 # 单张卡牌直接置于正上方
            else:
                angle_offset = (i / (num_cards - 1)) * angle_span
                # 重新定义角度范围：以 -90 (正上方) 为中心
                start_angle = -90 - (angle_span / 2)
                angle_deg = start_angle + angle_offset
            angle_rad = math.radians(angle_deg)
            
            # 计算该卡牌的目标位置
            tx = center_x + radius * math.cos(angle_rad)
            ty = center_y + radius * math.sin(angle_rad)
            
            cv.update_target_position(tx, ty)
            
            # 计算目标旋转角度
            # 卡牌默认是垂直竖立的。
            # 当卡牌在正上方 (-90度) 时，旋转应为 0。
            # 当卡牌在左侧 (-135度) 时，应该向左倾斜 (逆时针旋转？)。
            # Pygame 旋转：正值逆时针。
            # -135度位置 -> 需要卡牌头部指向该方向。
            # 卡牌垂直时头部指向 -90度方向。
            # 所以旋转角度 = -90 - angle_deg
            # 例如 angle_deg = -90 -> rotation = 0.
            # angle_deg = -135 (左) -> rotation = 45 (逆时针倾斜45度).
            # angle_deg = -45 (右) -> rotation = -45 (顺时针倾斜45度).
            
            if i == hovered_idx:
                cv.target_scale = 1.2
                cv.target_angle = 0 # 悬停的卡牌摆正方便阅读
                # 也可以让它稍微浮起一点
                cv.target_y -= 40
            else:
                cv.target_scale = 0.95
                cv.target_angle = -90 - angle_deg
        
    def sync_hand(self):
        # 仅当手牌数量变化时重新构造
        if len(self.card_views) != len(self.gs.player.hand):
            self.card_views = []
            for i, c in enumerate(self.gs.player.hand):
                self.card_views.append(CardView(c, i))
                
        # 更新每张卡牌的数据
        for i, cv in enumerate(self.card_views):
            cv.index = i
            cv.card = self.gs.player.hand[i]
        
        # 根据是否有悬停卡牌选择布局
        if self.hovered_card_idx == -1:
            # 没有悬停，使用常规水平布局
            num_cards = len(self.card_views)
            if num_cards > 0:
                total_width = num_cards * (CARD_WIDTH - 40)
                start_x = LOGICAL_WIDTH // 2 - total_width // 2
                
                for i, cv in enumerate(self.card_views):
                    if not cv.is_dragging:
                        tx = start_x + i * (CARD_WIDTH - 40) + CARD_WIDTH // 2
                        ty = BOTTOM_UI_Y + 100
                        cv.update_target_position(tx, ty)
                        cv.target_scale = 1.0
                        cv.target_angle = 0.0 # 重置角度
        else:
            # 有悬停，使用扇形展开布局
            self.calculate_fan_layout(self.hovered_card_idx)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            logical_pos = input_handler.get_logical_mouse_pos(event.pos)
            if not logical_pos: return
            self.mouse_pos = logical_pos
            
            # 悬停逻辑
            self.hover_pile = None
            if pygame.Rect(30, BOTTOM_UI_Y + 30, 100, 50).collidepoint(logical_pos):
                self.hover_pile = 'draw'
            elif pygame.Rect(30, BOTTOM_UI_Y + 130, 100, 50).collidepoint(logical_pos):
                self.hover_pile = 'discard'
                
            if self.dragged_card_idx == -1 and self.gs.turn == 'player':
                new_hovered = -1
                
                # 优先检查当前悬停的卡牌，增加判定范围以防止抖动 (迟滞效应)
                if self.hovered_card_idx != -1 and self.hovered_card_idx < len(self.card_views):
                    current_cv = self.card_views[self.hovered_card_idx]
                    # 增加垂直方向的判定范围，特别是向下，防止卡牌上浮后鼠标脱离
                    sticky_rect = current_cv.rect.inflate(0, 120) 
                    if sticky_rect.collidepoint(logical_pos):
                        new_hovered = self.hovered_card_idx
                
                # 如果没有保持悬停，则寻找新的悬停目标
                if new_hovered == -1:
                    for i in range(len(self.card_views)-1, -1, -1):
                        cv = self.card_views[i]
                        if cv.rect.collidepoint(logical_pos):
                            new_hovered = i
                            break
                            
                # 更新状态
                for i, cv in enumerate(self.card_views):
                    cv.is_hovered = (i == new_hovered)
                
                # 如果悬停卡牌改变，更新扇形布局
                if new_hovered != self.hovered_card_idx:
                    self.hovered_card_idx = new_hovered
                    self.sync_hand()
                    
                    # 播放卡牌悬停音效 (当悬停到有效卡牌时)
                    if new_hovered != -1:
                        audio_manager.play_card_hover_sound()
            
            # summon tooltip hover
            self.hover_summon = self.summon_rect.collidepoint(logical_pos)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            logical_pos = input_handler.get_logical_mouse_pos(event.pos)
            if not logical_pos: return
            
            if self.gs.turn != 'player': return
            
            # 检查结束回合按钮
            if self.end_turn_btn.collidepoint(logical_pos):
                self.gs.end_turn()
                return

            # 检查卡牌抽取
            for i in range(len(self.card_views)-1, -1, -1):
                cv = self.card_views[i]
                if cv.rect.collidepoint(logical_pos):
                    if self.gs.player.energy >= cv.card.cost:
                        self.dragged_card_idx = i
                        cv.is_dragging = True
                        self.drag_start_pos = logical_pos
                    else:
                        self.on_message("能量不足！")
                    break
                    
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.dragged_card_idx != -1:
                cv = self.card_views[self.dragged_card_idx]
                cv.is_dragging = False
                
                # 检查是否可以使用
                played = False
                logical_pos = input_handler.get_logical_mouse_pos(event.pos)
                if logical_pos:
                    if cv.card.targetType == 'friendly':
                        target = None
                        if self.player_rect.collidepoint(logical_pos): target = 'player'
                        elif self.summon_rect.collidepoint(logical_pos): target = 'summon'
                        else:
                            # 默认选择玩家
                            if logical_pos[1] < BATTLE_MIDDLE_Y + 100: target = 'player'
                            
                        if target:
                            self.gs.play_card(self.dragged_card_idx, friendly_target=target)
                            played = True
                    elif cv.card.targetType == 'self':
                        # 自我卡只需要向上拖拽
                        if logical_pos[1] < BATTLE_MIDDLE_Y + 100:
                            self.gs.play_card(self.dragged_card_idx, friendly_target='player')
                            played = True
                    else:
                        # 敌方目标
                        for i, r in enumerate(self.enemy_rects):
                            if r.collidepoint(logical_pos) and self.gs.enemies[i].hp > 0:
                                self.gs.play_card(self.dragged_card_idx, target_idx=i)
                                played = True
                                break
                                
                self.dragged_card_idx = -1
                if played:
                    self.sync_hand()
                    
    def update(self):
        self.gs.update()
        self.sync_hand()
        for cv in self.card_views:
            if cv.is_dragging:
                # 直接更新 current_x/y 以确保绘制位置跟随鼠标
                cv.current_x, cv.current_y = self.mouse_pos
                cv.rect.center = self.mouse_pos
            cv.update()
            
        fx_manager.update()

    def draw(self, surface):
        if getattr(self, 'background', None):
            surface.blit(self.background, (0, 0))
        else:
            surface.fill(COLORS['bg_dark'])
        
        # 1. 绘制敌人区域
        self.enemy_rects = []
        num_enemies = len(self.gs.enemies)
        total_w = num_enemies * ENEMY_GAP
        start_x = LOGICAL_WIDTH//2 - total_w//2 + ENEMY_GAP//2
        
        font = display_manager.get_font('medium')
        small_font = display_manager.get_font('small')
        
        for i, enemy in enumerate(self.gs.enemies):
            ex = start_x + i * ENEMY_GAP
            ey = BATTLE_TOP_Y - 20
            # 扩大点击判定区域以适应大图像
            rect = pygame.Rect(ex - 125, ey - 125, 250, 250)
            self.enemy_rects.append(rect)
            
            if enemy.hp <= 0: continue
            
            # 受击震动偏移
            sx, sy = fx_manager.get_shake_offset(enemy)
            ex += sx; ey += sy
            # 绘制敌人竖向血条（放在头像左侧，间距5px），并显示攻击力
            self.draw_enemy_vertical_hp(surface, rect, enemy, width=14, height=120, atk_val=enemy.base_damage)

            # 绘制敌人贴图/Emoji (先画本体)
            alpha = 100 if enemy.buffs['intangible'] > 0 else 255
            # 使用在 Enemy 对象初始化时就已确定的正确 image_path
            resource_manager.draw_sprite_or_fallback(
                surface, enemy.image_path, (ex, ey), enemy.sprite, 
                display_manager.get_font('xlarge'), COLORS['text_white'], 
                alpha, max_size=(250, 250)
            )

            # 绘制意图 (Intent) —— 基于头像尺寸，距离头像顶部 11px
            if enemy.intent:
                avatar_half = rect.height // 2
                intent_y = ey - avatar_half - 11
                intent_type = enemy.intent['type']

                # 先画图标，数值改为在悬停时显示
                intent_emoji_map = {
                    'attack': '⚔️', 'block': '🛡️', 'heal': '💖', 'buff': '💪', 'debuff': '✨', 'intangible': '🌫️'
                }
                fallback_emoji = intent_emoji_map.get(intent_type, '❓')
                resource_manager.draw_sprite_or_fallback(
                    surface, f"icons/intent_{intent_type}.png", (ex, intent_y), 
                    fallback_emoji, small_font, COLORS['text_white'], max_size=(64, 64)
                )

                # 如果鼠标悬停在图标上，则显示具体数值/效果浮窗
                icon_rect = pygame.Rect(ex - 32, intent_y - 32, 64, 64)
                if icon_rect.collidepoint(self.mouse_pos):
                    intent_val = str(enemy.intent.get('value', ''))
                    intent_text_map = {
                        'attack': f"{intent_val}伤害", 
                        'block': f"{intent_val}防守", 
                        'heal': f"{intent_val}回复", 
                        'buff': f"+{intent_val}", 
                        'debuff': f"-{intent_val}", 
                        'intangible': "虚化"
                    }
                    display_text = intent_text_map.get(intent_type, intent_val)
                    # draw tooltip near mouse
                    tip_surf = font.render(display_text, True, COLORS['attack'])
                    tip_rect = tip_surf.get_rect()
                    tip_rect.topleft = (self.mouse_pos[0] + 10, self.mouse_pos[1] - tip_rect.height - 10)
                    bg = pygame.Rect(tip_rect.inflate(10, 6))
                    pygame.draw.rect(surface, (0,0,0,180), bg, border_radius=4)
                    pygame.draw.rect(surface, COLORS['text_white'], bg, 1, border_radius=4)
                    surface.blit(tip_surf, tip_rect)

            # 绘制名字在头像底部，距离头像 8px
            avatar_half = rect.height // 2
            name_y = ey + avatar_half + 8
            name_surf = font.render(enemy.name, True, COLORS['text_white'])
            surface.blit(name_surf, name_surf.get_rect(center=(ex, name_y)))

        # 2. 绘制玩家区域
        px, py = self.player_rect.center
        sx, sy = fx_manager.get_shake_offset(self.gs.player)
        px += sx; py += sy
        
        resource_manager.draw_sprite_or_fallback(
            surface, "entities/player.png", (px, py), "⭐", 
            display_manager.get_font('xlarge'), COLORS['text_white'],
            max_size=(250, 250)
        )
        # 玩家纵向血条（左侧放置，类似敌人），并显示攻击力
        player_rect_adjusted = pygame.Rect(px - 125, py - 125, 250, 250)
        atk_val = getattr(self.gs.player, 'base_damage', 6)
        self.draw_enemy_vertical_hp(surface, player_rect_adjusted, self.gs.player, width=14, height=120, atk_val=atk_val)
        
        # 主角名字显示在头像底部 8px
        player_name = getattr(self.gs.player, 'name', '玩家')
        name_surf = font.render(player_name, True, COLORS['text_white'])
        surface.blit(name_surf, name_surf.get_rect(center=(px, py + 125 + 8)))
        
        # 绘制玩家 Buff
        buff_y = py + 170
        if self.gs.player.buffs['strength'] > 0:
            resource_manager.draw_sprite_or_fallback(
                surface, "icons/buff_strength.png", (px - 40, buff_y), "💪", 
                small_font, COLORS['power'], max_size=(32, 32)
            )
            val_surf = small_font.render(str(self.gs.player.buffs['strength']), True, COLORS['power'])
            surface.blit(val_surf, val_surf.get_rect(center=(px - 20, buff_y)))
            
        if self.gs.player.buffs['weak'] > 0:
            resource_manager.draw_sprite_or_fallback(
                surface, "icons/buff_weak.png", (px + 20, buff_y), "✨", 
                small_font, COLORS['text_gray'], max_size=(32, 32)
            )
            val_surf = small_font.render(str(self.gs.player.buffs['weak']), True, COLORS['text_gray'])
            surface.blit(val_surf, val_surf.get_rect(center=(px + 40, buff_y)))

        # 3. 绘制召唤物 (小星星)
        if self.gs.player.summon.active and self.gs.player.summon.hp > 0:
            sx_pos, sy_pos = self.summon_rect.center
            sx, sy = fx_manager.get_shake_offset(self.gs.player.summon)
            sx_pos += sx; sy_pos += sy
            
            # 召唤物与玩家垂直居中
            s_y = sy_pos
            resource_manager.draw_sprite_or_fallback(
                surface, "entities/BaiMo.png", (sx_pos, s_y), "✨", 
                display_manager.get_font('large'), COLORS['text_white'],
                max_size=(150, 150)
            )
            
            # 召唤物纵向血条（左侧放置，类似敌人），并显示攻击力
            summon_rect_adjusted = pygame.Rect(sx_pos - 125, s_y - 125, 250, 250)
            self.draw_enemy_vertical_hp(surface, summon_rect_adjusted, self.gs.player.summon, width=12, height=100, atk_val=self.gs.player.summon.atk)
            
            # 召唤物名字显示在头像底部 8px，与玩家名字对齐
            summon_name = self.gs.player.summon.name
            name_surf = font.render(summon_name, True, COLORS['text_white'])
            surface.blit(name_surf, name_surf.get_rect(center=(sx_pos, py + 125 + 8)))

            
            # 召唤物名字提示框（鼠标悬停时显示）
            if self.hover_summon:
                tooltip_text = self.gs.player.summon.name
                tooltip_surf = small_font.render(tooltip_text, True, COLORS['text_white'])
                tooltip_rect = tooltip_surf.get_rect(center=(sx_pos, s_y - 50))
                bg_rect = tooltip_rect.inflate(20, 10)
                pygame.draw.rect(surface, (0, 0, 0, 180), bg_rect, border_radius=5)
                pygame.draw.rect(surface, COLORS['text_white'], bg_rect, 1, border_radius=5)
                surface.blit(tooltip_surf, tooltip_rect)

        # 4. Draw Bottom UI Background
        pygame.draw.rect(surface, (20, 20, 20), (0, BOTTOM_UI_Y, LOGICAL_WIDTH, BOTTOM_UI_HEIGHT))
        pygame.draw.line(surface, COLORS['text_gray'], (0, BOTTOM_UI_Y), (LOGICAL_WIDTH, BOTTOM_UI_Y), 2)
        
        # Draw Deck Info
        icons = ConfigLoader.get_assets_config().get('ui_icons', {})
        draw_icon = icons.get('draw_pile')
        resource_manager.draw_sprite_or_fallback(surface, draw_icon, (60, BOTTOM_UI_Y + 60), "🎴", font, COLORS['text_white'], max_size=(48, 48))
        
        deck_surf = font.render(str(len(self.gs.player.deck)), True, COLORS['text_white'])
        surface.blit(deck_surf, (90, BOTTOM_UI_Y + 50))
        
        discard_icon = icons.get('discard_pile')
        resource_manager.draw_sprite_or_fallback(surface, discard_icon, (60, BOTTOM_UI_Y + 160), "🗑️", font, COLORS['text_white'], max_size=(48, 48))
        
        discard_surf = font.render(str(len(self.gs.player.discard)), True, COLORS['text_white'])
        surface.blit(discard_surf, (90, BOTTOM_UI_Y + 150))
        
        # Draw Energy
        pygame.draw.circle(surface, COLORS['energy'], (200, BOTTOM_UI_Y + 120), 40)
        pygame.draw.circle(surface, COLORS['text_white'], (200, BOTTOM_UI_Y + 120), 40, 3)
        en_surf = font.render(f"{self.gs.player.energy}/{self.gs.player.max_energy}", True, COLORS['black'])
        surface.blit(en_surf, en_surf.get_rect(center=(200, BOTTOM_UI_Y + 120)))

        # Draw End Turn Btn
        color = (255, 127, 80) if self.gs.turn == 'player' else (100, 100, 100)
        pygame.draw.rect(surface, color, self.end_turn_btn, border_radius=5)
        btn_surf = font.render("结束回合", True, COLORS['text_white'])
        surface.blit(btn_surf, btn_surf.get_rect(center=self.end_turn_btn.center))

        # 5. Draw Cards
        # 绘制非拖拽、非悬停的卡牌
        for i, cv in enumerate(self.card_views):
            if not cv.is_dragging and i != self.hovered_card_idx:
                cv.draw(surface, self.gs.player.buffs['strength'], self.gs.player.buffs['weak'])
        
        # 绘制悬停的卡牌及其阴影（在其他卡牌之上）
        if self.hovered_card_idx != -1 and self.hovered_card_idx < len(self.card_views) and not self.card_views[self.hovered_card_idx].is_dragging:
            hovered_cv = self.card_views[self.hovered_card_idx]
            # 绘制阴影
            shadow_rect = hovered_cv.rect.copy()
            shadow_rect.y += 8
            shadow_rect.x += 4
            shadow_surf = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
            shadow_surf.fill((0, 0, 0, 80))
            surface.blit(shadow_surf, shadow_rect)
            # 绘制卡牌
            hovered_cv.draw(surface, self.gs.player.buffs['strength'], self.gs.player.buffs['weak'])
        
        # 绘制拖拽的卡牌在最上层
        if self.dragged_card_idx != -1:
            # 拖拽时稍微缩小一点卡牌以便看清目标
            dragged_card = self.card_views[self.dragged_card_idx]
            original_scale = dragged_card.scale
            dragged_card.scale = 0.8
            dragged_card.draw(surface, self.gs.player.buffs['strength'], self.gs.player.buffs['weak'])
            dragged_card.scale = original_scale


        # 6. FX & Overlays
        # 绘制怪物攻击意图连线 (红色箭头)
        if self.gs.turn == 'enemy' and self.gs.action_timer > 0 and len(self.gs.enemy_action_queue) > 0:
            actor = self.gs.enemy_action_queue[0]
            if actor.hp > 0 and actor.intent['type'] == 'attack':
                # 确定目标
                is_summon_target = actor.intent.get('target') == 'summon'
                target_rect = self.summon_rect if is_summon_target and self.gs.player.summon.active else self.player_rect
                
                # 确定攻击者位置
                actor_rect = None
                for i, e in enumerate(self.gs.enemies):
                    if e == actor and i < len(self.enemy_rects):
                        actor_rect = self.enemy_rects[i]
                        break
                
                if actor_rect:
                    start_pos = actor_rect.center
                    end_pos = target_rect.center
                    
                    # 绘制红色连线
                    line_color = COLORS['attack'] # 红色
                    pygame.draw.line(surface, line_color, start_pos, end_pos, 5)
                    
                    # 绘制箭头
                    dx, dy = end_pos[0] - start_pos[0], end_pos[1] - start_pos[1]
                    angle = math.atan2(dy, dx)
                    
                    arrow_len = 25
                    angle_offset = 0.5 # 弧度
                    
                    # 箭头顶点
                    p1 = end_pos
                    # 箭头尾部两点
                    p2 = (end_pos[0] - arrow_len * math.cos(angle - angle_offset), end_pos[1] - arrow_len * math.sin(angle - angle_offset))
                    p3 = (end_pos[0] - arrow_len * math.cos(angle + angle_offset), end_pos[1] - arrow_len * math.sin(angle + angle_offset))
                    
                    pygame.draw.polygon(surface, line_color, [p1, p2, p3])

        fx_manager.draw(surface)
        
        if self.hover_pile:
            pile = self.gs.player.deck if self.hover_pile == 'draw' else self.gs.player.discard
            title_text = "抽牌堆:" if self.hover_pile == 'draw' else "弃牌堆:"
            cards_text = [c.name for c in pile]
            if not cards_text: cards_text = ["(空)"]
            
            # Simple text wrap for pile preview
            lines = [title_text]
            cur_line = ""
            for name in cards_text:
                if len(cur_line) + len(name) > 15:
                    lines.append(cur_line)
                    cur_line = name + " "
                else:
                    cur_line += name + " "
            if cur_line: lines.append(cur_line)
            
            info_surf = pygame.Surface((300, 40 * len(lines) + 20), pygame.SRCALPHA)
            info_surf.fill((0, 0, 0, 200))
            pygame.draw.rect(info_surf, COLORS['energy'], info_surf.get_rect(), 2)
            
            for idx, ln in enumerate(lines):
                s = small_font.render(ln, True, COLORS['text_white'])
                info_surf.blit(s, (10, 10 + idx * 35))
                
            surface.blit(info_surf, (150, BOTTOM_UI_Y - info_surf.get_height()))
        
        if self.message_timer > 0:
            self.message_timer -= 1
            msg_surf = display_manager.get_font('xlarge').render(self.message_text, True, COLORS['text_white'])
            bg_rect = msg_surf.get_rect(center=(LOGICAL_WIDTH//2, LOGICAL_HEIGHT//2 - 100))
            bg_rect.inflate_ip(40, 20)
            pygame.draw.rect(surface, (0,0,0,180), bg_rect, border_radius=20)
            surface.blit(msg_surf, msg_surf.get_rect(center=bg_rect.center))
            
        if self.gs.battle_won:
            self.draw_reward_overlay(surface)
        elif self.gs.game_over:
            over_surf = display_manager.get_font('xlarge').render("Game Over", True, COLORS['hp'])
            surface.blit(over_surf, over_surf.get_rect(center=(LOGICAL_WIDTH//2, LOGICAL_HEIGHT//2)))

    def draw_health_bar(self, surface, cx, cy, hp, max_hp, block, width=120):
        font = display_manager.get_font('small')
        bar_h = 14
        bg_rect = pygame.Rect(cx - width//2, cy, width, bar_h)
        pygame.draw.rect(surface, (50, 50, 50), bg_rect, border_radius=7)
        
        # Calculate scaling to make sure shield overlays correctly, and HP fits well
        # We don't cap block width visually if it's over max_hp, but limit it to width for rendering
        hp_w = max(0, min(width, int(width * (hp / max_hp))))
        if hp_w > 0:
            hp_rect = pygame.Rect(cx - width//2, cy, hp_w, bar_h)
            pygame.draw.rect(surface, COLORS['hp'], hp_rect, border_radius=7)
            
        if block > 0:
            # Shield covers the bar from left to right, can cap at 100% of visual width
            bl_w = max(10, min(width, int(width * (block / max_hp))))
            bl_rect = pygame.Rect(cx - width//2, cy, bl_w, bar_h)
            pygame.draw.rect(surface, COLORS['block'], bl_rect, border_radius=7)
            
            b_surf = font.render(str(block), True, COLORS['block'])
            surface.blit(b_surf, b_surf.get_rect(midright=(cx - width//2 - 5, cy + bar_h//2)))
            
        t_surf = font.render(f"{hp}/{max_hp}", True, COLORS['text_white'])
        surface.blit(t_surf, t_surf.get_rect(center=(cx, cy + bar_h + 10)))

    def draw_enemy_vertical_hp(self, surface, avatar_rect, enemy, width=14, height=120, atk_val=None):
        # 绘制竖向血条
        font = display_manager.get_font('small')
        left_x = avatar_rect.left - 5 - width
        top_y = avatar_rect.top + max(0, (avatar_rect.height - height) // 2)

        # 背景
        bg_rect = pygame.Rect(left_x, top_y, width, height)
        pygame.draw.rect(surface, (50, 50, 50), bg_rect, border_radius=7)

        # 血量填充（从下往上）
        ratio = 0.0
        if enemy.max_hp > 0:
            ratio = max(0.0, min(1.0, enemy.hp / enemy.max_hp))
        fill_h = int(height * ratio)
        fill_rect = pygame.Rect(left_x, top_y + (height - fill_h), width, fill_h)
        if fill_h > 0:
            pygame.draw.rect(surface, COLORS['hp'], fill_rect, border_radius=7)

        # 护盾值从血条顶部从上往下增加（最后渲染，确保显示在血条之上）
        block = getattr(enemy, 'block', 0)
        if block > 0 and enemy.max_hp > 0:
            block_ratio = min(1.0, block / enemy.max_hp)
            block_h = int(height * block_ratio)
            block_rect = pygame.Rect(left_x, top_y, width, block_h)
            pygame.draw.rect(surface, COLORS['block'], block_rect, border_radius=7)

        # 等级文本在血条上方 5px
        lv_surf = font.render(f"Lv.{getattr(enemy, 'level', 1)}", True, COLORS['text_white'])
        lv_x = left_x + width // 2
        lv_y = top_y - 5 - lv_surf.get_height() // 2
        surface.blit(lv_surf, lv_surf.get_rect(center=(lv_x, lv_y)))
        
        # 攻击力显示已移除
        pass

    def draw_reward_overlay(self, surface):
        overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0,0))
        
        font = display_manager.get_font('xlarge')
        title = font.render("胜利！", True, COLORS['energy'])
        surface.blit(title, title.get_rect(center=(LOGICAL_WIDTH//2, 200)))
        
        # We handle clicks for this in another layer or directly in main loop, 
        # but for simplicity let's just draw them and check in handle_event
        # Actually, handling it directly in main event loop is cleaner.
        
        # Draw cards
        start_x = LOGICAL_WIDTH//2 - len(self.gs.reward_cards)*(CARD_WIDTH+20)//2 + CARD_WIDTH//2
        self.reward_rects = []
        for i, c in enumerate(self.gs.reward_cards):
            rx = start_x + i*(CARD_WIDTH+20)
            ry = LOGICAL_HEIGHT//2
            
            # Temporary cardview for rendering
            cv = CardView(c, i)
            cv.current_x, cv.current_y = rx, ry
            cv.rect.center = (rx, ry)
            cv.draw(surface)
            self.reward_rects.append(cv.rect)
            
        # Draw skip
        self.skip_rect = pygame.Rect(LOGICAL_WIDTH//2 - 100, LOGICAL_HEIGHT - 200, 200, 50)
        pygame.draw.rect(surface, (100, 100, 100), self.skip_rect, border_radius=5)
        skip_font = display_manager.get_font('medium')
        s_surf = skip_font.render("跳过", True, COLORS['text_white'])
        surface.blit(s_surf, s_surf.get_rect(center=self.skip_rect.center))
