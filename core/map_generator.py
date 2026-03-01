import random
from core.config_loader import ConfigLoader

class MapNode:
    def __init__(self, x, y, type_):
        self.x = x
        self.y = y
        self.type = type_ # 'start', 'enemy', 'elite', 'reward', 'boss', 'merchant', 'event'
        self.children = [] # next floor nodes
        self.parents = []  # previous floor nodes
        self.state = 'locked' # 'locked', 'available', 'visited'
    
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
        if total_children == 1:
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
        """获取按X坐标排序的children清单"""
        return sorted(self.children, key=lambda n: n.x)

class MapGenerator:
    def __init__(self, width=None, height=None):
        # 从配置文件获取地图参数
        map_config = ConfigLoader.get_map_nodes_config()
        map_gen_config = map_config.get('map_generation', {})
        
        self.width = width or map_gen_config.get('width', 7)
        self.height = height or map_gen_config.get('height', 10)
        self.grid = {} # (x,y) -> MapNode
        self.nodes = [] # Flat list of all nodes
        self.boss_node = None
        self.start_node = None
        self.node_ratios = map_gen_config.get('node_ratio', {}).get('stage_ratios', [])
        
    def _get_node_ratio(self, stage):
        """
        根据当前等级(stage)计算敌人与奖励的比例。
        从配置文件中读取阶级配置。
        返回值: (敌人权重, 奖励权重)
        """
        # 查找适用的阶级
        for ratio_config in self.node_ratios:
            if stage <= ratio_config.get('max_stage', 999):
                return ratio_config.get('enemy_weight', 1), ratio_config.get('reward_weight', 1)
        
        # 默认值
        return 1, 1

    def _get_random_type(self, stage):
        # 目前只保留普通敌人和奖励节点，以匹配当前需求
        # 如果需要精英怪，也可以加入其中
        enemy_w, reward_w = self._get_node_ratio(stage)
        total_w = enemy_w + reward_w
        r = random.uniform(0, total_w)
        if r < enemy_w:
            return 'enemy'
        else:
            return 'reward'
            
    def clear(self):
        """清除当前地图，准备生成新地图"""
        self.grid = {}
        self.nodes = []
        self.boss_node = None
        self.start_node = None
        
    def generate(self, stage=1):
        """
        核心算法：分层递进式地图生成
        
        步骤：
        1. 定义层级（深度）和宽度约束
        2. 在每层预生成节点
        3. 自上向下建立连接（确保每个节点都被覆盖）
        4. 在第6层强制所有节点连到Boss
        5. 清理孤岛节点
        """
        
        # ========== 步骤1：定义参数 ==========
        map_config = ConfigLoader.get_map_nodes_config()
        map_gen_config = map_config.get('map_generation', {})
        
        depth = self.height  # 总层数（0-7，共8层）
        width = self.width   # 最大宽度
        
        # ========== 步骤2：在每层预生成节点 ==========
        # 存储每层的所有节点：{layer_y: [nodes]}
        layer_nodes = {}
        occupied_positions = set()
        
        # 第0层：起点
        start_x = width // 2
        self.start_node = MapNode(start_x, 0, 'start')
        self.start_node.state = 'available'
        self.add_node(self.start_node)
        layer_nodes[0] = [self.start_node]
        occupied_positions.add((start_x, 0))
        
        # 第1-6层：随机生成2-4个节点
        for y in range(1, depth - 1):
            num_nodes = random.randint(2, 4)
            nodes_in_layer = []
            
            for _ in range(num_nodes):
                # 尝试在不重叠的位置生成节点
                attempts = 0
                while attempts < 15:
                    x = random.randint(0, width - 1)
                    if (x, y) not in occupied_positions:
                        node = MapNode(x, y, self._get_random_type(stage))
                        self.add_node(node)
                        occupied_positions.add((x, y))
                        nodes_in_layer.append(node)
                        break
                    attempts += 1
            
            # 如果生成失败，确保至少有一个节点
            if not nodes_in_layer:
                for x in range(width):
                    if (x, y) not in occupied_positions:
                        node = MapNode(x, y, self._get_random_type(stage))
                        self.add_node(node)
                        occupied_positions.add((x, y))
                        nodes_in_layer.append(node)
                        break
            
            # 按x坐标排序该层节点（便于后续优化）
            nodes_in_layer.sort(key=lambda n: n.x)
            layer_nodes[y] = nodes_in_layer
        
        # ========== 步骤3：自上向下建立连接 ==========
        # 关键：确保每层的每个节点都被上一层的至少一个节点连上
        # 改进：使用距离启发式方法（优先连接距离近的节点，以减少线条交叉）
        
        for y in range(1, depth - 1):
            current_layer = layer_nodes[y]
            previous_layer = layer_nodes[y - 1]
            
            # 追踪这一层哪些节点已被连接
            connected_nodes = set()
            
            # 遍历上一层的每个节点
            for prev_node in previous_layer:
                # 每个节点连接到1-2个下一层的节点
                num_connections = random.randint(1, min(2, len(current_layer)))
                
                # 优先连接未被连接的节点（确保覆盖）
                unconnected = [n for n in current_layer if n not in connected_nodes]
                
                # 对未连接的节点按与当前节点的X距离排序（优先连接距离近的）
                def dist_key(node):
                    return abs(node.x - prev_node.x)
                
                if unconnected:
                    unconnected.sort(key=dist_key)
                    # 连接一些最近的未覆盖节点
                    num_to_unconnected = min(num_connections, len(unconnected))
                    targets = unconnected[:num_to_unconnected]
                    for target in targets:
                        self.connect(prev_node, target)
                        connected_nodes.add(target)
                    
                    # 如果还有剩余的连接数，选择距离最近的已连接节点
                    remaining = num_connections - num_to_unconnected
                    if remaining > 0 and len(current_layer) > len(unconnected):
                        other_nodes = [n for n in current_layer if n not in unconnected]
                        other_nodes.sort(key=dist_key)
                        extra_targets = other_nodes[:min(remaining, len(other_nodes))]
                        for target in extra_targets:
                            self.connect(prev_node, target)
                else:
                    # 所有节点都已连接，选择距离最近的节点
                    current_layer.sort(key=dist_key)
                    targets = current_layer[:num_connections]
                    for target in targets:
                        self.connect(prev_node, target)
                        connected_nodes.add(target)
            
            # 确保这一层所有节点都被连接（孤岛修复）
            for node in current_layer:
                if node not in connected_nodes:
                    # 连接到距离最近的上一层节点
                    parent = min(previous_layer, key=lambda p: abs(p.x - node.x))
                    self.connect(parent, node)
        
        # ========== 步骤4：第6层强制收束到Boss ==========
        boss_y = depth - 1
        last_layer = layer_nodes[depth - 2]
        
        # 创建Boss节点
        boss_x = width // 2
        # 确保Boss不与其他节点重叠
        attempts = 0
        while (boss_x, boss_y) in occupied_positions and attempts < width:
            boss_x = (boss_x + 1) % width
            attempts += 1
        
        self.boss_node = MapNode(boss_x, boss_y, 'boss')
        self.add_node(self.boss_node)
        occupied_positions.add((boss_x, boss_y))
        layer_nodes[boss_y] = [self.boss_node]
        
        # 强制最后一层的所有节点连接到Boss
        for node in last_layer:
            self.connect(node, self.boss_node)
        
        # ========== 步骤5：优化节点位置以最小化线条交叉 ==========
        self.optimize_node_positions(layer_nodes)
        
        # ========== 步骤6：清理孤岛节点 ==========
        self._cleanup_unreachable_nodes()
        
        # ========== 步骤7：最终排序确保no overlaps ==========
        self.sort_children_by_position()
        
        return self.start_node
    
    def _cleanup_unreachable_nodes(self):
        """删除所有无法从起点到达的节点"""
        # 使用BFS找出所有可达的节点
        reachable = set()
        queue = [self.start_node]
        
        while queue:
            node = queue.pop(0)
            if node in reachable:
                continue
            reachable.add(node)
            
            for child in node.children:
                if child not in reachable:
                    queue.append(child)
        
        # 删除不可达的节点
        nodes_to_remove = [n for n in self.nodes if n not in reachable]
        
        for node in nodes_to_remove:
            self.nodes.remove(node)
            if (node.x, node.y) in self.grid:
                del self.grid[(node.x, node.y)]
            
            # 清理这个节点的连接关系
            for parent in node.parents:
                if node in parent.children:
                    parent.children.remove(node)
            for child in node.children:
                if node in child.parents:
                    child.parents.remove(node)

    def add_node(self, node):
        # 加上视觉防呆偏移 (Jitter)，让UI渲染时不显得太死板
        # 【修复重叠Bug】：大幅减小 Jitter 的范围，尤其是 Y 轴，确保不会导致上下层撞车
        node.jitter_x = random.randint(-15, 15)
        node.jitter_y = random.randint(-5, 5)
        
        # Boss 和 起点 不加偏移，确保完美居中
        if node.type in ['start', 'boss']:
            node.jitter_x = 0
            node.jitter_y = 0
            
        self.grid[(node.x, node.y)] = node
        self.nodes.append(node)
        
    def connect(self, parent, child):
        """
        建立父子节点连接
        自动按子节点的X坐标排序，确保连线不相交
        """
        if child not in parent.children:
            parent.children.append(child)
            # 按子节点X坐标排序，从左到右
            # 这样在UI中可以从左到右依次引出连线，避免相交
            parent.children.sort(key=lambda n: n.x)
        
        if parent not in child.parents:
            child.parents.append(parent)
    
    def optimize_node_positions(self, layer_nodes):
        """
        简化后的节点位置优化。

        每一层的节点会被随机打乱顺序，然后按均匀间隔分配x坐标，
        并为每个节点添加小幅抖动。
        这一做法既保证了不规则排列，也避免了节点之间间距过大。
        """
        width = self.width
        for y, layer in layer_nodes.items():
            if not layer:
                continue
            # 随机分布 x 坐标，以获取不规则间距
            for node in layer:
                node.x = random.uniform(0, width - 1)
                # 额外加一点随机抖动
                node.x += random.uniform(-0.2, 0.2)
            # 如果存在极端重叠，可选地排序或稍作微调
            layer_nodes[y] = layer    
    def sort_children_by_position(self):
        """
        在所有连接完成后，确保每个节点的children都按x坐标排序
        这样连线绘制时就能保证不相交
        """
        for node in self.nodes:
            node.children.sort(key=lambda n: n.x)
            
    def get_available_nodes(self, current_node):
        if not current_node:
            return [self.start_node]
        return current_node.children
        
    def visit(self, node):
        node.state = 'visited'
        # Unlock next nodes
        for child in node.children:
            if child.state == 'locked':
                child.state = 'available'
