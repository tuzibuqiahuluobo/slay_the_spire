import pygame
import math
from settings import *
from ui.display_manager import display_manager
from utils.input_handler import input_handler
from utils.resource_manager import resource_manager
from core.config_loader import ConfigLoader


def draw_bezier_curve(surface, start_pos, end_pos, color, width=2):
    """
    使用三次贝塞尔曲线绘制平滑连线。
    公式: $P(t) = (1-t)^3 P_0 + 3(1-t)^2 t P_1 + 3(1-t) t^2 P_2 + t^3 P_3$
    """
    x0, y0 = start_pos
    x3, y3 = end_pos
    
    # 控制点：强制Y轴垂直延伸，形成向上生长的水流感
    offset = abs(y3 - y0) * 0.5
    x1, y1 = x0, y0 - offset
    x2, y2 = x3, y3 + offset
    
    points = []
    steps = 30 # 曲线平滑度
    for i in range(steps + 1):
        t = i / steps
        # 贝塞尔公式计算
        px = (1-t)**3 * x0 + 3*(1-t)**2 * t * x1 + 3*(1-t)*t**2 * x2 + t**3 * x3
        py = (1-t)**3 * y0 + 3*(1-t)**2 * t * y1 + 3*(1-t)*t**2 * y2 + t**3 * y3
        points.append((px, py))
    
    # 绘制抗锯齿折线连接点
    if len(points) > 1:
        if width > 1:
             pygame.draw.lines(surface, color, False, points, width)
        else:
             pygame.draw.aalines(surface, color, False, points)



class MapScene:
    def __init__(self, game_state):
        self.gs = game_state
        self.node_radius = 25
        self.node_rects = {} # (node_obj) -> Rect
        self.click_start_pos = None
        self.anim_timer = 0
        
        # 消息提示相关
        self.message_text = ""
        self.message_timer = 0
        self.gs.on_message = self.on_message # 绑定回调
        
        # 地图参数
        self.grid_w = 7
        self.grid_h = 10
        # 大幅增加 Y 轴间距，实现长卷轴效果
        self.spacing_y = 180 
        
        # 动态X坐标映射：层级 -> (节点数, 最小X, 最大X)
        self.layer_x_info = {}  # y -> {'count': int, 'min_x': int, 'max_x': int}
        self.compute_layer_x_info()
        
        # 摄像机滚动相关
        # 初始时，将镜头对准底部起点 (让起点位于屏幕下方 1/4 处)
        self.scroll_y = 0 
        self.target_scroll_y = 0
        self.is_dragging = False
        self.drag_start_y = 0
        self.drag_start_scroll = 0
        
        # 章节追踪
        self.current_chapter = self.gs.chapter
        
        # 加载背景图
        self.bg_image = None
        raw_bg = resource_manager.get_image("background.png")
        if raw_bg:
            # 保持宽高比缩放宽度到 LOGICAL_WIDTH
            bg_w, bg_h = raw_bg.get_size()
            scale = LOGICAL_WIDTH / bg_w
            new_h = int(bg_h * scale)
            self.bg_image = pygame.transform.smoothscale(raw_bg, (LOGICAL_WIDTH, new_h))
            self.bg_image.set_alpha(255) # 不透明，靠遮罩层调整亮度
        
        # 初始化聚焦到起点
        self.focus_on_node(self.gs.map_node_current or self.gs.map_generator.start_node)
        
        # 呼吸动画计时器
        self.anim_timer = 0

    def compute_layer_x_info(self):
        """
        计算每一层的节点数量和X坐标范围。
        用于动态计算该层的像素间距。
        """
        # 按层级组织节点
        nodes_by_layer = {}
        for node in self.gs.map_generator.nodes:
            if node.y not in nodes_by_layer:
                nodes_by_layer[node.y] = []
            nodes_by_layer[node.y].append(node)
        
        # 计算每层的X范围和节点数
        for y, nodes in nodes_by_layer.items():
            x_values = [n.x for n in nodes]
            min_x = min(x_values)
            max_x = max(x_values)
            count = len(nodes)
            self.layer_x_info[y] = {
                'count': count,
                'min_x': min_x,
                'max_x': max_x,
                'nodes': nodes
            }

    def on_message(self, msg):
        self.message_text = msg
        self.message_timer = 120 # 2秒

    def focus_on_node(self, node):
        if not node: return
        # 计算目标 Scroll Y，使得该节点位于屏幕垂直中心偏下一点的位置 (比如 3/4 处)
        # 节点的世界坐标 Y 是 node.y * spacing_y
        # 我们希望：LOGICAL_HEIGHT - (world_y - scroll_y) - base_offset = TARGET_SCREEN_Y
        # 简化计算：
        # 目标是把 node.y 这一层抬升到合适的高度
        # base visual y (无 scroll) = LOGICAL_HEIGHT - 150 - node.y * spacing
        # 加上 scroll 后 = visual_y + scroll
        # 我们希望 visual_y + scroll = LOGICAL_HEIGHT * 0.75
        
        node_world_y_from_bottom = 150 + node.y * self.spacing_y
        # 目标屏幕位置（从底部算起）
        target_screen_bottom = 300 # 也就是屏幕上方 LOGICAL_HEIGHT - 300 处
        
        self.target_scroll_y = max(0, node_world_y_from_bottom - target_screen_bottom)
        # 限制滚动范围，不要滚出地图顶部太多
        max_scroll = (self.grid_h * self.spacing_y) - LOGICAL_HEIGHT + 400
        self.target_scroll_y = min(self.target_scroll_y, max(0, max_scroll))

    def handle_event(self, event):
        logical_pos = input_handler.get_logical_mouse_pos(event.pos) if hasattr(event, 'pos') else None
        
        # 处理拖拽
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if logical_pos:
                self.is_dragging = True
                self.drag_start_y = logical_pos[1]
                self.drag_start_scroll = self.target_scroll_y
                
                # 同时也检查点击节点（如果拖拽距离很小，视为点击）
                self.click_start_pos = logical_pos

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.is_dragging = False
            # 检查是否是点击
            if logical_pos and self.click_start_pos:
                dist = math.hypot(logical_pos[0] - self.click_start_pos[0], logical_pos[1] - self.click_start_pos[1])
                if dist < 10: # 认为是点击而不是拖拽
                    self.check_node_click(logical_pos)
                    
        elif event.type == pygame.MOUSEMOTION:
            if self.is_dragging and logical_pos:
                dy = logical_pos[1] - self.drag_start_y
                # 拖拽方向相反：鼠标往下拉，地图应该往上走(看到上面)，或者反之？
                # 通常：鼠标往下拉，内容往下移（看到上面的内容）-> scroll 变小？
                # 地图是从下往上长的。Scroll 越大，看到的层级越高（内容下移）。
                # 鼠标下拉(dy > 0) -> 内容下移 -> Scroll 变大
                self.target_scroll_y = self.drag_start_scroll + dy
                # 限制范围
                max_scroll = (self.grid_h * self.spacing_y) - LOGICAL_HEIGHT + 600
                self.target_scroll_y = max(-100, min(self.target_scroll_y, max_scroll))
                # 拖拽时直接更新，不使用平滑插值，响应更跟手
                self.scroll_y = self.target_scroll_y

        return False

    def check_node_click(self, pos):
        if self.gs.map_node_current:
            available = self.gs.map_generator.get_available_nodes(self.gs.map_node_current)
        else:
            available = [self.gs.map_generator.start_node]
            
        for node in available:
            rect = self.get_node_rect(node)
            if rect.collidepoint(pos):
                self.gs.visit_map_node(node)
                self.focus_on_node(node) # 点击移动后，自动聚焦
                return True
        return False

    def get_node_pos(self, node):
        """
        获取节点的屏幕坐标。
        """
        # Y 坐标（从下到上）
        base_y = LOGICAL_HEIGHT - 150 - node.y * self.spacing_y
        visual_y = base_y + self.scroll_y
        
        # X 坐标 - 优先使用预计算的 rect_x
        if hasattr(node, 'rect_x') and node.rect_x != 0:
             visual_x = node.rect_x
        elif node.y in self.layer_x_info:
            layer_info = self.layer_x_info[node.y]
            min_x = layer_info['min_x']
            max_x = layer_info['max_x']
            count = layer_info['count']
            
            # 计算该层在屏幕上的可用宽度（考虑安全边距）
            margin = 100
            available_width = LOGICAL_WIDTH - 2 * margin
            
            if count == 1:
                # 单个节点居中
                visual_x = LOGICAL_WIDTH / 2
            else:
                # 多个节点：从min_x到max_x均匀分布在可用宽度内
                x_range = max_x - min_x
                if x_range > 0:
                    # 相对位置：从0到1
                    rel_pos = (node.x - min_x) / x_range
                    visual_x = margin + rel_pos * available_width
                else:
                    visual_x = LOGICAL_WIDTH / 2
        else:
            visual_x = LOGICAL_WIDTH / 2
        
        # 应用抖动（如果有）
        visual_x += getattr(node, 'jitter_x', 0)
        visual_y += getattr(node, 'jitter_y', 0)
        
        return (visual_x, visual_y)

    def get_node_rect(self, node):
        cx, cy = self.get_node_pos(node)
        
        # Larger rect for Boss and Start for click detection
        radius = self.node_radius
        if node.type in ['boss', 'start']:
            radius = self.node_radius * 1.5
            
        return pygame.Rect(cx - radius, cy - radius, radius*2, radius*2)

    def update(self):
        # 检测章节切换
        if hasattr(self.gs, 'chapter') and self.gs.chapter != self.current_chapter:
            self.current_chapter = self.gs.chapter
            self.compute_layer_x_info()
            # 重新聚焦起点
            self.focus_on_node(self.gs.map_generator.start_node)
            
        # 呼吸动画计时器
        self.anim_timer += 0.1
            
        # 平滑滚动相机
        if not self.is_dragging:
            self.scroll_y += (self.target_scroll_y - self.scroll_y) * 0.1

    def draw(self, surface):
        self.update() # Update scroll frame by frame
        
        # 绘制背景
        if self.bg_image:
             # 计算背景平铺逻辑，使其随节点同步移动
             # 锚点：背景底部对应 Start 节点层级下方 (y=LOGICAL_HEIGHT)
             # 背景随 scroll_y 移动
             
             bg_h = self.bg_image.get_height()
             
             # 计算当前屏幕底部对应的逻辑坐标
             # 当 scroll_y = 0 时，屏幕底部对应逻辑 y = LOGICAL_HEIGHT
             # 当 scroll_y 增加时，内容下移，意味着屏幕底部对应更低的逻辑 y ? 
             # 不，scroll_y 是加在 visual_y 上的。
             # visual_y = base_y + scroll_y
             # 如果我们要让背景固定在逻辑空间里：
             # bg_visual_y = bg_base_y + scroll_y
             
             # 我们设定背景图的底部基准线为 LOGICAL_HEIGHT (屏幕底部)
             # 所以 bg_base_y = LOGICAL_HEIGHT - bg_h
             
             start_draw_y = (LOGICAL_HEIGHT - bg_h) + self.scroll_y
             
             # 向上平铺直到覆盖整个地图高度 (约 1800 像素)
             # Start Node base_y ~ 900. Boss Node base_y ~ -300.
             # 需要覆盖到 -500 左右
             
             # 从下往上画
             curr_y = start_draw_y
             # 只要 curr_y + bg_h > 0 (还能看见)，就画
             # 并且要覆盖到顶部，即 curr_y 可能需要很小
             
             # 向下平铺（填补底部空缺，如果有的话）
             while curr_y < LOGICAL_HEIGHT:
                 surface.blit(self.bg_image, (0, int(curr_y)))
                 curr_y += bg_h
             
             # 向上平铺
             curr_y = start_draw_y
             while curr_y > -bg_h: # 只要还没完全移出屏幕上方
                 surface.blit(self.bg_image, (0, int(curr_y)))
                 curr_y -= bg_h
                 
             # 添加暗色遮罩以突出节点
             overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
             overlay.fill((0, 0, 0, 100)) # 调整遮罩浓度
             surface.blit(overlay, (0,0))
        else:
             # Draw semi-transparent background (fallback)
             overlay = pygame.Surface((LOGICAL_WIDTH, LOGICAL_HEIGHT), pygame.SRCALPHA)
             overlay.fill((0, 0, 0, 230))
             surface.blit(overlay, (0,0))
        
        # 裁剪区域 (Clipping)：只在屏幕中间区域绘制地图，上下留出UI空间
        # map_clip_rect = pygame.Rect(0, 60, LOGICAL_WIDTH, LOGICAL_HEIGHT - 60)
        # surface.set_clip(map_clip_rect)
        
        # 绘制连线 (Connections)
        all_nodes = self.gs.map_generator.nodes
        # 根据层级收集所有边
        layer_edges = {}  # y -> list of (parent, child, start_pos, end_pos, line_color, width)
        for node in all_nodes:
            start_pos = self.get_node_pos(node)
            sorted_children = node.children
            for child in sorted_children:
                end_pos = self.get_node_pos(child)
                # 屏幕外优化
                if max(start_pos[1], end_pos[1]) < -50 or min(start_pos[1], end_pos[1]) > LOGICAL_HEIGHT + 50:
                    continue
                # 计算样式
                line_color = (80, 80, 80)
                width = 3
                if node.state == 'visited' and (child.state == 'visited' or child == self.gs.map_node_current):
                    line_color = COLORS['text_white']
                    width = 5
                elif node == self.gs.map_node_current and child.state == 'available':
                    line_color = (150, 150, 150)
                    width = 4
                layer_edges.setdefault(node.y, []).append(
                    (node, child, start_pos, end_pos, line_color, width)
                )
        # 对每一层的边进行排序并绘制，每条边使用不同的lane_offset
        lane_space = 15  # 垂直间距，减小以免移动太多
        for y, edges in layer_edges.items():
            # 按中点x排序
            edges.sort(key=lambda e: (e[2][0] + e[3][0]))
            for idx, (node, child, start_pos, end_pos, line_color, width) in enumerate(edges):
                # 连接出口和入口点
                # 重新计算带偏移的出口/入口，保持与节点视觉对齐
                exit_offset, _ = node.get_exit_position(node.children.index(child), len(node.children))
                exit_x = start_pos[0] + exit_offset
                exit_y = start_pos[1] + 15
                entry_x = end_pos[0] - exit_offset
                entry_y = end_pos[1] - 15
                # lane offset: 交错布置以避免重合
                mid = (len(edges) - 1) / 2
                lane_off = (idx - mid) * lane_space
                draw_bezier_curve(surface, (exit_x, exit_y), (entry_x, entry_y), line_color, width)

        # Draw nodes
        current_node = self.gs.map_node_current
        available_nodes = []
        if not self.gs.in_battle:
            if not current_node:
                available_nodes = [self.gs.map_generator.start_node]
            elif current_node.children:
                available_nodes = current_node.children

        for node in all_nodes:
            pos = self.get_node_pos(node)
            # 性能优化：屏幕外不绘制
            if pos[1] < -50 or pos[1] > LOGICAL_HEIGHT + 50:
                continue
                
            rect = self.get_node_rect(node)
            
            # Determine style based on room type
            # 根据room type选择基础颜色
            type_colors = {
                'start': (100, 150, 200),    # 蓝色
                'enemy': (180, 80, 80),       # 红色
                'elite': (150, 100, 200),     # 紫色
                'reward': (200, 180, 80),     # 黄色
                'merchant': (100, 180, 150),  # 青色
                'event': (180, 150, 100),     # 棕色
                'boss': (200, 100, 100),      # 深红色
                'camp': (70, 180, 100),       # 营地绿
            }
            color = type_colors.get(node.type, (80, 80, 80))
            border_color = (150, 150, 150)
            width = 2
            
            # 计算呼吸缩放因子
            pulse = math.sin(self.anim_timer) * 0.2 + 1.2 # 1.0 ~ 1.4
            
            if node.state == 'visited':
                # Visited状态：使用同色但提高亮度
                color = tuple(min(255, c + 40) for c in color)
                border_color = COLORS['text_white']
            
            if node in available_nodes:
                # Available状态：使用能量色边框和本身color
                border_color = COLORS['energy']
                width = 3
                
            if node == current_node:
                border_color = COLORS['text_white'] # 当前节点用白色
                width = 4
            
            # 节点形状与图标
            ui_icons = ConfigLoader.get_assets_config().get('ui_icons', {})
            visited_icon = ui_icons.get('node_visited')

            if node.type == 'boss':
                icon_path = "icons/node_boss.png"
                icon_char = "👿"
                if node.state == 'visited' and visited_icon:
                    icon_path = visited_icon
                    icon_char = "✓"
                
                # 如果当前节点可选，画个高亮边框提示
                if node in available_nodes:
                    # 呼吸边框
                    inflate_size = 10 * pulse
                    pygame.draw.rect(surface, border_color, rect.inflate(inflate_size, inflate_size), width=width, border_radius=18)

                resource_manager.draw_sprite_or_fallback(
                    surface, icon_path, pos, icon_char, display_manager.get_font('large'), COLORS['hp'], max_size=(80, 80)
                )
            elif node.type == 'start':
                icon_path = "icons/node_start.png"
                icon_char = "🏠"
                if node.state == 'visited' and visited_icon:
                    icon_path = visited_icon
                    icon_char = "✓"
                
                # 如果当前节点可选，画个高亮边框提示
                if node in available_nodes:
                    inflate_size = 10 * pulse
                    pygame.draw.rect(surface, border_color, rect.inflate(inflate_size, inflate_size), width=width, border_radius=15)

                resource_manager.draw_sprite_or_fallback(
                    surface, icon_path, pos, icon_char, display_manager.get_font('medium'), COLORS['text_white'], max_size=(64, 64)
                )
            else:
                icon_char = "?"
                icon_col = COLORS['text_white']
                img_path = f"icons/node_{node.type}.png"
                if node.type == 'enemy': icon_char, icon_col = "⚔️", COLORS['text_gray']
                elif node.type == 'elite': icon_char, icon_col = "💀", COLORS['attack']
                elif node.type == 'reward': icon_char, icon_col = "🎁", COLORS['power']
                elif node.type == 'merchant': icon_char, icon_col = "🛒", COLORS['skill']
                elif node.type == 'camp': icon_char, icon_col = "🔥", COLORS['heal']
                elif node.type == 'event': icon_char, icon_col = "?", COLORS['text_white']
                
                if node.state == 'visited' and visited_icon:
                    img_path = visited_icon
                    icon_char = "✓"
                
                # 如果当前节点可选，画个高亮边框提示
                if node in available_nodes:
                    # 统一使用圆角矩形边框以匹配图标形状
                    inflate_size = 10 * pulse
                    # rect 是 50x50, 图标是 48x48. 
                    # 使用稍微大一点的圆角矩形
                    border_rect = pygame.Rect(0, 0, 56 + inflate_size, 56 + inflate_size)
                    border_rect.center = pos
                    pygame.draw.rect(surface, border_color, border_rect, width=width, border_radius=12)
                
                resource_manager.draw_sprite_or_fallback(
                    surface, img_path, pos, icon_char, display_manager.get_font('small'), icon_col, max_size=(48, 48)
                )

            # 如果这是当前节点，在节点绘制完成后再绘制白点覆盖，以便高亮显示玩家当前所在节点
            if node == current_node:
                pygame.draw.circle(surface, COLORS['text_white'], pos, 10)

        # surface.set_clip(None) # Reset clip

        # UI Overlay (Title, Hint)
        title_font = display_manager.get_font('xlarge')
        title = title_font.render("地图", True, COLORS['text_white'])
        surface.blit(title, (50, 70))
        
        hint_font = display_manager.get_font('medium')
        if not self.gs.in_battle:
            hint = hint_font.render("长按拖拽查看，点击节点前进", True, COLORS['energy'])
        else:
            hint = hint_font.render("战斗进行中...", True, COLORS['text_gray'])
        surface.blit(hint, (50, 140))
        
        # 奖励消息提示 (Message Overlay)
        if self.message_timer > 0:
            self.message_timer -= 1
            msg_surf = display_manager.get_font('xlarge').render(self.message_text, True, COLORS['power'])
            bg_rect = msg_surf.get_rect(center=(LOGICAL_WIDTH//2, LOGICAL_HEIGHT//2))
            bg_rect.inflate_ip(60, 40)
            pygame.draw.rect(surface, (0,0,0,200), bg_rect, border_radius=20)
            pygame.draw.rect(surface, COLORS['power'], bg_rect, 3, border_radius=20)
            surface.blit(msg_surf, msg_surf.get_rect(center=bg_rect.center))
