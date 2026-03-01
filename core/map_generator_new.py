import random
from settings import LOGICAL_WIDTH, LOGICAL_HEIGHT

# ==========================================
# 游戏常量与配置
# ==========================================
# 调整画布大小以适应游戏视口
WIDTH = LOGICAL_WIDTH
# 高度设置为稍大于屏幕，或者适应滚动。这里我们使用固定高度用于计算相对位置
# MapScene 会根据 node.y * spacing_y 计算实际 Y，所以这里的 HEIGHT 主要用于相对比例计算
HEIGHT = 1600 

# 房间权重配置 (战斗总计40, 商店20, 营地20, 事件20，满足比例 2:1:1:1)
ROOM_WEIGHTS = {
    'Combat': 30,
    'Elite': 10,
    'Shop': 20,
    'Camp': 20,
    'Event': 20
}

# ==========================================
# 数据结构：地图节点
# ==========================================
class MapNode:
    def __init__(self, layer_idx, virtual_x):
        self.layer = layer_idx       # 层级 (0-7)
        self.vx = virtual_x          # 虚拟X坐标 (用于防交叉逻辑)
        self.room_type = None        # 房间类型
        self.children = []           # 指向下一层的节点
        self.parents = []            # 指向上一层的节点
        
        # 兼容性属性
        self.x = virtual_x
        self.y = layer_idx
        self.state = 'locked'        # locked, available, visited (for compatibility)
        
        # 渲染用像素坐标
        self.rect_x = 0
        self.rect_y = 0
        self.jitter_x = 0 # 随机抖动X
        self.jitter_y = 0 # 随机抖动Y

    @property
    def type(self):
        # 映射到游戏系统识别的类型
        mapping = {
            'Combat': 'enemy',
            'Event': 'event',  
            'Elite': 'elite',
            'Shop': 'merchant',
            'Camp': 'camp',
            'Start': 'start',
            'Boss': 'boss'
        }
        return mapping.get(self.room_type, 'unknown')

    def get_exit_position(self, child_index, total_children):
        """
        计算连线出口位置
        Args:
            child_index: 该连线在所有children中的索引（已排序）
            total_children: 所有children的总数
        
        Returns:
            (exit_x_offset, exit_side) - 出口相对位置和方向
            例如：(0, 'center')表示从中心出，(-10, 'left')表示从左侧出
        """
        if total_children <= 1:
            return (0, 'center')
        elif total_children == 2:
            if child_index == 0:
                return (-8, 'left')
            else:
                return (8, 'right')
        else:
            # 3+个children时，均匀分布
            spread = 12
            center_x = (total_children - 1) / 2
            offset_x = (child_index - center_x) * (spread / (total_children - 1))
            return (int(offset_x), 'multi')

    def get_sorted_children(self):
        """获取按X坐标排序的children清单 (compatible with old code)"""
        return sorted(self.children, key=lambda n: n.vx)

# ==========================================
# 核心系统：地图生成器
# ==========================================
class MapGeneratorNew:
    def __init__(self):
        self.layers = []
        self.max_width = 7 # 虚拟X轴的宽度 (Increased to 7 to match game grid roughly)
        self.nodes = [] # Flat list for compatibility
        self.start_node = None
        self.boss_node = None
        self.height = 8 # Total layers

    def clear(self):
        """重置生成器状态"""
        self.layers = []
        self.nodes = []
        self.start_node = None
        self.boss_node = None

    def generate(self, stage=1):
        """主生成流程：不断尝试直到生成一个完全合法的无死角DAG"""
        # stage 参数目前未使用，保留以兼容接口
        
        while True:
            self.layers = []
            self.nodes = [] # Clear flat list
            self.start_node = None
            self.boss_node = None
            
            self._step1_generate_topology()
            
            # 校验：除了第7层(Boss)外，不能有任何节点没有出路 (死胡同)
            is_valid = True
            for layer in self.layers[:-1]:
                for node in layer:
                    if len(node.children) == 0:
                        is_valid = False
                        break
                if not is_valid: break
            
            if is_valid:
                break # 拓扑合法，跳出循环
        
        # 确保所有节点的 children 按 vx 排序，优化连线视觉效果
        for layer in self.layers:
            for node in layer:
                node.children.sort(key=lambda n: n.vx)

        self._step2_assign_room_types()
        self._calculate_pixel_coordinates()
        
        # 填充兼容性数据
        for layer in self.layers:
            for node in layer:
                self.nodes.append(node)
                if node.room_type == 'Start':
                    self.start_node = node
                if node.room_type == 'Boss':
                    self.boss_node = node
        
        # If start node missing (should not happen due to step 2), ensure it
        if not self.start_node and self.layers and self.layers[0]:
             self.start_node = self.layers[0][0]

    def visit(self, node):
        """标记节点已访问 (for compatibility)"""
        node.state = 'visited'
        for child in node.children:
            if child.state == 'locked':
                child.state = 'available'

    def get_available_nodes(self, node):
        """获取给定节点的可达后续节点"""
        if not node:
            return [self.start_node]
        return node.children

    def _step1_generate_topology(self):
        """第一步：生成拓扑结构并连线"""
        # 1. 网格化层级：创建节点并分配虚拟X
        for depth in range(8):
            if depth == 0 or depth == 7:
                num_nodes = 1
            else:
                num_nodes = random.randint(3, 5) # Slightly increased for wider map
            
            # 为当前层随机抽取不重复的虚拟X，并排序以保证左右关系
            # 使用 self.max_width 防止越界
            x_indices = sorted(random.sample(range(self.max_width), num_nodes))
            current_layer = [MapNode(depth, vx) for vx in x_indices]
            self.layers.append(current_layer)

        # 2. 自底向上连线
        for i in range(7):
            current_layer = self.layers[i]
            next_layer = self.layers[i+1]

            # A. 孤岛预防：确保下一层的每一个节点至少被当前层连一次 (寻找X差值最小的)
            for target_node in next_layer:
                closest_node = min(current_layer, key=lambda n: abs(n.vx - target_node.vx))
                self._add_edge(closest_node, target_node)

            # B. 保证当前层节点有 1-2 条连线
            for node in current_layer:
                target_count = random.randint(1, 3) # Allow up to 3 connections
                attempts = 0
                while len(node.children) < target_count and attempts < 10:
                    attempts += 1
                    # 寻找距离在 2 以内的候选节点
                    candidates = [n for n in next_layer if abs(n.vx - node.vx) <= 2 and n not in node.children]
                    if not candidates:
                        break
                    
                    target = random.choice(candidates)
                    
                    # C. 防交叉判定
                    if not self._check_crossing(node, target, current_layer):
                        self._add_edge(node, target)

    def _add_edge(self, parent, child):
        if child not in parent.children:
            parent.children.append(child)
        if parent not in child.parents:
            child.parents.append(parent)

    def _check_crossing(self, u, v, current_layer):
        """检查新增边 (u -> v) 是否与当前层已有的边发生X坐标逆序交叉"""
        for existing_u in current_layer:
            for existing_v in existing_u.children:
                # 交叉判定：U在已有节点左侧，但V在已有目标右侧 (或相反)
                if (u.vx < existing_u.vx and v.vx > existing_v.vx) or \
                   (u.vx > existing_u.vx and v.vx < existing_v.vx):
                    return True
        return False

    def _step2_assign_room_types(self):
        """第二步：房间类型规则染色"""
        for depth, layer in enumerate(self.layers):
            for node in layer:
                # 1. 硬性规则
                if depth == 0:
                    node.room_type = 'Start'
                elif depth == 7:
                    node.room_type = 'Boss'
                elif depth == 1:
                    node.room_type = 'Combat'
                elif depth == 6:
                    node.room_type = 'Camp'
                else:
                    # 2. & 3. 局部限制与权重随机
                    choices = []
                    weights = []
                    for r_type, weight in ROOM_WEIGHTS.items():
                        # Layer 2 不能有精英怪
                        if depth == 2 and r_type == 'Elite':
                            continue
                            
                        # 不能连续三个战斗节点（含精英怪）
                        if r_type in ['Combat', 'Elite']:
                            is_three_combats = False
                            for parent in node.parents:
                                if parent.room_type in ['Combat', 'Elite']:
                                    for grandparent in parent.parents:
                                        if grandparent.room_type in ['Combat', 'Elite']:
                                            is_three_combats = True
                                            break
                                if is_three_combats:
                                    break
                            if is_three_combats:
                                continue

                        # 不能连续商店
                        if r_type == 'Shop' and any(p.room_type == 'Shop' for p in node.parents):
                            continue
                        # 不能连续营地
                        if r_type == 'Camp' and any(p.room_type == 'Camp' for p in node.parents):
                            continue
                        # 不能连续事件 (Optional, added for variety)
                        if r_type == 'Event' and any(p.room_type == 'Event' for p in node.parents):
                            # 降低事件连续的权重，或者也可以直接 continue
                            pass

                        choices.append(r_type)
                        weights.append(weight)
                    
                    # 权重抽取
                    if not choices:
                        node.room_type = 'Combat' # Fallback
                    else:
                        node.room_type = random.choices(choices, weights=weights, k=1)[0]

    def _calculate_pixel_coordinates(self):
        """计算 Pygame 渲染用的屏幕像素坐标"""
        # 使用 LOGICAL_WIDTH 居中布局
        content_width = LOGICAL_WIDTH * 0.75
        start_x = (LOGICAL_WIDTH - content_width) / 2
        
        for depth, layer in enumerate(self.layers):
            num_nodes = len(layer)
            if num_nodes == 0: continue
            
            x_step = content_width / (num_nodes + 1)
            
            for idx, node in enumerate(layer):
                # 基础坐标 (均匀分布)
                base_x = start_x + x_step * (idx + 1)
                
                # Boss (depth 7) 和 Start (depth 0) 不抖动
                if depth == 0 or depth == 7:
                    node.jitter_x = 0
                    node.jitter_y = 0
                else:
                    # X轴抖动：范围加大，例如 +/- 20% 的步长
                    x_jitter_range = int(x_step * 0.2)
                    node.jitter_x = random.randint(-x_jitter_range, x_jitter_range)
                    
                    # Y轴抖动：让层级不再那么笔直，范围 +/- 25
                    node.jitter_y = random.randint(-25, 25)
                
                node.rect_x = base_x
                node.rect_y = 0
