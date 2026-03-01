"""
新的地图生成器实现，基于用户指定的核心算法。

核心设计：
1. 网格化：给每个节点固定分配X坐标 (0 到 max_width-1)
2. 就近连接：节点只连接X距离≤1的下层节点，防止交叉
3. 强制收束：第6层所有节点连向Boss
4. 房间类型权重：硬性规则 + 权重随机
"""

import random
from core.config_loader import ConfigLoader


class MapNode:
    def __init__(self, x, y, type_='empty'):
        self.x = x  # 横向网格坐标 (0 到 width-1)
        self.y = y  # 纵向层级 (0 到 height-1)
        self.type = type_  # 房间类型：start, enemy, elite, boss, reward, merchant, event
        self.children = []  # 下一层的连接节点
        self.parents = []   # 上一层的连接节点
        self.state = 'locked'  # locked, available, visited
    
    def get_exit_position(self, child_index, total_children):
        """计算连线出口位置（用于UI绘制）"""
        if total_children == 1:
            return (0, 'center')
        elif total_children == 2:
            return (-8, 'left') if child_index == 0 else (8, 'right')
        else:
            spread = 12
            center_x = (total_children - 1) / 2
            offset_x = (child_index - center_x) * (spread / (total_children - 1))
            return (int(offset_x), 'multi')
    
    def get_sorted_children(self):
        """获取按X坐标排序的children清单"""
        return sorted(self.children, key=lambda n: n.x)
    
    def __repr__(self):
        return f"Node({self.type} x={self.x} y={self.y})"


class MapGeneratorNew:
    def __init__(self, width=None, height=None):
        """初始化地图生成器"""
        map_config = ConfigLoader.get_map_nodes_config()
        map_gen_config = map_config.get('map_generation', {})
        
        self.width = width or map_gen_config.get('width', 7)
        self.height = height or map_gen_config.get('height', 8)
        
        self.nodes = []
        self.grid = {}  # (x, y) -> MapNode
        self.start_node = None
        self.boss_node = None
        
        # 房间类型权重（从配置或使用默认值）
        self.room_weights = {
            'enemy': 40,
            'elite': 15,
            'event': 25,
            'merchant': 10,
            'reward': 10,
        }
    
    def clear(self):
        """重置地图数据"""
        self.nodes = []
        self.grid = {}
        self.start_node = None
        self.boss_node = None
    
    def _add_node(self, x, y, type_):
        """添加节点到网格"""
        node = MapNode(x, y, type_)
        self.nodes.append(node)
        self.grid[(x, y)] = node
        return node
    
    def _can_connect(self, x_from, x_to):
        """
        检查是否能连接两个X坐标的节点。
        规则：只能连接X距离 ≤ 1 的节点（左上、正上方、右上）
        """
        return abs(x_from - x_to) <= 1
    
    def _has_crossing(self, x_a, target_a, x_b, target_b):
        """
        检测两条边是否会"X坐标逆序交叉"。
        如果两条从同层出发的边，起点顺序相反却指向逆序的终点，则会交叉。
        """
        return (x_a < x_b and target_a > target_b) or (x_a > x_b and target_a < target_b)
    
    def _check_new_edge_crossing(self, parent, target, current_layer, existing_edges):
        """
        检查新边 (parent -> target) 是否与现有边产生交叉。
        existing_edges: set of (x_parent, x_target) pairs
        """
        parent_x = parent.x
        target_x = target.x
        
        for ex_x, ex_target_x in existing_edges:
            if self._has_crossing(parent_x, target_x, ex_x, ex_target_x):
                return True  # 会交叉
        return False  # 不交叉
    
    def _connect(self, parent, child):
        """建立父子连接（检查不会产生交叉）"""
        if child not in parent.children:
            parent.children.append(child)
            # 按x坐标排序，便于后续交叉检测
            parent.children.sort(key=lambda n: n.x)
        if parent not in child.parents:
            child.parents.append(parent)
            child.parents.sort(key=lambda n: n.x)
    
    def _get_candidates_in_range(self, layer_nodes, x, max_diff=1):
        """获取与给定x坐标在范围内的节点列表"""
        return [n for n in layer_nodes if self._can_connect(x, n.x)]
    
    def generate(self, stage=1):
        """
        核心地图生成算法（按用户指定的步骤）
        
        步骤1: 定义层级和宽度
        步骤2: 生成初始节点（固定X坐标）
        步骤3: 自底向上连线（确保覆盖 + 防止交叉）
        步骤4: 强制收束到Boss
        步骤5: 清理孤岛
        步骤6: 分配房间类型
        """
        self.clear()
        
        # ===== 步骤1: 定义参数 =====
        depth = self.height  # 8层
        width = self.width   # 横向宽度
        
        # ===== 步骤2: 生成初始节点 =====
        layer_nodes = {}  # y -> [nodes]
        
        # 第0层：起点（固定中心）
        start_x = width // 2
        self.start_node = self._add_node(start_x, 0, 'empty')
        layer_nodes[0] = [self.start_node]
        
        # 第1-6层：每层2-4个节点
        for y in range(1, depth - 1):
            num_nodes = random.randint(2, 4)
            # 为这一层随机选择X坐标（不重复）
            available_x = list(range(width))
            random.shuffle(available_x)
            selected_x = sorted(available_x[:num_nodes])  # 保证这一层的节点从左到右排列
            
            nodes = []
            for x in selected_x:
                node = self._add_node(x, y, 'empty')
                nodes.append(node)
            layer_nodes[y] = nodes
        
        # 第7层（最后一层）：先预留Boss位置
        # Boss先作为临时节点，最后再转换类型
        boss_x = width // 2
        self.boss_node = self._add_node(boss_x, depth - 1, 'empty')
        layer_nodes[depth - 1] = [self.boss_node]
        
        # ===== 步骤3: 自底向上连线 =====
        for y in range(depth - 2):  # 从第0层到第5层开始连接
            current_layer = layer_nodes[y]
            next_layer = layer_nodes[y + 1]
            
            # 追踪已建立的连接和下一层的覆盖状态
            connected_targets = set()
            existing_edges = set()  # (x_parent, x_target) 用于交叉检测
            
            # ===== 阶段1：孤岛预防 =====
            # 确保下一层每个节点都至少被连接一次
            for target in next_layer:
                # 确保只连接X距离≤1的父节点
                valid_parents = [p for p in current_layer if self._can_connect(p.x, target.x)]
                
                if valid_parents:
                    # 在有效父节点中找最接近的
                    best_parent = min(valid_parents, key=lambda p: abs(p.x - target.x))
                else:
                    # 如果没有有效父节点，使用最接近的（虽然会违反约束，这是必要的"容错"）
                    best_parent = min(current_layer, key=lambda p: abs(p.x - target.x))
                
                self._connect(best_parent, target)
                connected_targets.add(target)
                existing_edges.add((best_parent.x, target.x))
            
            # ===== 阶段2：额外连接 + 防交叉 =====
            for parent in current_layer:
                # 随机生成1-2条额外连线
                num_extra = random.randint(1, 2)
                
                # 获取该节点能连接的候选节点（X距离≤1）
                candidates = self._get_candidates_in_range(next_layer, parent.x, max_diff=1)
                
                if not candidates:
                    continue
                
                # 尝试建立新连接，同时检查交叉
                attempts = 0
                added = 0
                while added < num_extra and attempts < len(candidates) * 2:
                    target = random.choice(candidates)
                    
                    # 检查是否已经连接
                    if target in parent.children:
                        attempts += 1
                        continue
                    
                    # 检查是否会产生交叉
                    if not self._check_new_edge_crossing(parent, target, current_layer, existing_edges):
                        # 安全，建立连接
                        self._connect(parent, target)
                        existing_edges.add((parent.x, target.x))
                        added += 1
                    
                    attempts += 1
        
        # ===== 步骤4: 强制收束到Boss =====
        # 第6层所有节点连向Boss（遵守X约束）
        if depth > 1:
            layer_6 = layer_nodes.get(depth - 2, [])
            for node in layer_6:
                # 即使需要强制连接，也应该只连一次
                if self.boss_node not in node.children:
                    self._connect(node, self.boss_node)
        
        # ===== 步骤5: 清理孤岛 =====
        self._cleanup_unreachable_nodes()
        
        # ===== 步骤6: 分配房间类型 =====
        self._assign_room_types(stage)
        
        # ===== 最终整理 =====
        # 按X坐标排序每个节点的children，便于UI绘制
        for node in self.nodes:
            node.children.sort(key=lambda n: n.x)
        
        self.start_node.state = 'available'
        return self.start_node
    
    def _cleanup_unreachable_nodes(self):
        """删除所有从起点无法到达的节点"""
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
        unreachable = [n for n in self.nodes if n not in reachable]
        for node in unreachable:
            self.nodes.remove(node)
            if (node.x, node.y) in self.grid:
                del self.grid[(node.x, node.y)]
            
            # 清理连接
            for parent in node.parents:
                if node in parent.children:
                    parent.children.remove(node)
            for child in node.children:
                if node in child.parents:
                    child.parents.remove(node)
    
    def _assign_room_types(self, stage=1):
        """
        第二步：为每个节点分配房间类型。
        
        硬性规则：
          - Layer 0: START（起点）
          - Layer 1: ENEMY（普通战斗）
          - Layer 6: REWARD（休息营地）
          - Layer 7: BOSS（首领）
          - Layer 2: 不能有ELITE
        
        权重随机：
          中间层 (3-5) 根据权重随机分配
          权重: ENEMY 45%, EVENT 25%, ELITE 10%, MERCHANT 10%, REWARD 10%
        
        局部限制：
          - 不能出现连续的MERCHANT节点
          - 不能出现连续的REWARD节点
        """
        # 定义权重（固定在这里，可后期配置化）
        room_weights = {
            'enemy': 45,
            'event': 25,
            'elite': 10,
            'merchant': 10,
            'reward': 10,
        }
        
        for node in self.nodes:
            # 硬性规则
            if node.y == 0:
                node.type = 'start'
            elif node.y == 1:
                node.type = 'enemy'  # Layer 1 必定是普通战斗
            elif node.y == self.height - 2:  # Layer 6
                node.type = 'reward'  # 休息营地
            elif node.y == self.height - 1:  # Layer 7
                node.type = 'boss'
            elif node.y == 2:
                # Layer 2 不能有精英
                available = {k: v for k, v in room_weights.items() if k != 'elite'}
                node.type = self._sample_weighted_type(available)
            else:
                # 中间层（Layer 3-5）根据权重随机
                node.type = self._sample_weighted_type(room_weights)
        
        # 应用局部限制
        self._apply_local_constraints()
    
    def _sample_weighted_type(self, weights):
        """根据权重字典随机抽取一个类型"""
        types = list(weights.keys())
        weight_values = [weights[t] for t in types]
        return random.choices(types, weights=weight_values, k=1)[0]
    
    def _apply_local_constraints(self):
        """
        应用局部限制：
          - 不能出现连续的MERCHANT
          - 不能出现连续的REWARD
        
        注意：不修改硬规则节点（start, enemy, boss, reward第6层）
        """
        hard_rule_indices = {0, 1, 6, 7}  # Layer 0, 1, 6, 7 有硬规则
        
        for node in self.nodes:
            # 不修改硬规则节点
            if node.y in hard_rule_indices:
                continue
            
            if node.type == 'merchant':
                # 检查父节点是否也是merchant
                for parent in node.parents:
                    if parent.type == 'merchant':
                        # 改变当前节点的类型
                        node.type = random.choice(['enemy', 'event'])
                        break
            
            elif node.type == 'reward':
                # 检查父节点是否也是reward（但第6层的reward不改变）
                if node.y != self.height - 2:  # 不改变第6层
                    for parent in node.parents:
                        if parent.type == 'reward':
                            # 改变当前节点的类型
                            node.type = random.choice(['enemy', 'event'])
                            break
    
    def get_available_nodes(self, current_node):
        """获取当前节点的所有可连接下一个节点"""
        if not current_node:
            return [self.start_node]
        return current_node.children
    
    def visit(self, node):
        """标记节点为已访问，解锁其子节点"""
        node.state = 'visited'
        for child in node.children:
            if child.state == 'locked':
                child.state = 'available'
