# 游戏配置文件说明

**本项目已将所有可调节的数值提取到JSON配置文件中，方便维护和平衡调整。**

## 📁 配置文件结构

### 1. **heroes.json** - 英雄（玩家）配置
存储主角的初始属性和进度相关参数。

```json
{
    "ironclad": {
        "id": "ironclad",
        "name": "Iron Clad",
        "name_zh": "玩家",
        "stats": {
            "initial_hp": 80,
            "initial_energy": 3,
            "max_energy_cap": 10,
            "initial_level": 1,
            "initial_gold": 0,
            "initial_exp": 0
        },
        "progression": {
            "exp_formula": "(level * 2) + 5"
        }
    }
}
```

**关键参数**：
- `initial_hp`: 玩家初始血量
- `initial_energy`: 每回合初始能量
- `max_energy_cap`: 能量上限

---

### 2. **summons.json** - 召唤物配置
存储召唤物（小星星）的初始数据和缩放参数。

```json
{
    "little_star": {
        "id": "little_star",
        "name": "Little Star",
        "stats": {
            "initial_hp": 4,
            "initial_atk": 2
        },
        "scaling": {
            "hp_increase_per_summon": 2,
            "atk_increase_per_summon": 1
        }
    }
}
```

**关键参数**：
- `initial_hp`: 首次召唤的血量
- `initial_atk`: 首次召唤的攻击力
- `hp_increase_per_summon`: 每次再次召唤时增加的血量
- `atk_increase_per_summon`: 每次再次召唤时增加的攻击力

---

### 3. **game_balance.json** - 游戏平衡参数
存储所有难度、缩放、进度等核心数值。

#### 敌人缩放 (difficulty.enemy_scaling)
```json
"difficulty": {
    "enemy_scaling": {
        "hp_scale_per_stage": 0.06,           // 每关增加6%血量
        "hp_linear_bonus_per_stage": 2,       // 每关额外+2血量
        "dmg_scale_per_stage": 0.04,          // 每关增加4%攻击
        "default_base_damage": 6              // 默认攻击力
    }
}
```

#### Boss 难度 (boss)
```json
"boss": {
    "hp_multiplier": 3.0,                     // Boss血量倍数
    "dmg_bonus": 5,                          // Boss额外伤害
    "exploration_weakness_max": 0.8,         // 最高削弱比例(探索100%时)
    "min_hp": 10,                            // 最低保底血量
    "min_dmg": 2,                            // 最低保底攻击
    "stage_modifier": 5                      // Boss的阶段修正值
}
```

#### 精英怪难度 (elite)
```json
"elite": {
    "hp_multiplier": 1.5,                    // 精英血量倍数
    "stage_modifier": 2                      // 精英阶段修正值
}
```

#### 玩家进度 (player_progression)
```json
"player_progression": {
    "energy_bonus_per_3_turns": 1,          // 每3回合+1能量
    "max_energy": 10,                       // 能量上限
    "rage_mode_turn": 10,                   // 第N回合触发狂暴
    "rage_damage_multiplier": 2.0,          // 狂暴伤害倍数
    "base_hand_size": 5                     // 手牌数量
}
```

---

### 4. **monsters.json** - 敌人数据库
存储所有敌人的基础属性。

**更新**：所有敌人名称已改为英文

```json
{
    "name": "brute",                         // 英文ID (主键)
    "name_zh": "帅帅",                       // 中文名称
    "hp": 30,                                // 基础血量
    "sprite": "👹",                         // Emoji表情(未找到图片时显示)
    "sprite_path": "entities/brute.png",   // 美术资源路径
    "baseDamage": 5,                        // 基础攻击力
    "type": "attacker"                      // 敌人类型(attacker/supporter)
}
```

---

### 5. **map_nodes.json** - 地图节点配置
存储地图节点类型和生成规则。

#### 地图节点类型配置
```json
"node_types": [
    {
        "type": "start",
        "name": "Start",
        "name_zh": "起点",
        "icon": "icons/node_start.png",
        "icon_emoji": "🏠",
        "is_battle": false
    },
    // ... 其他节点类型 (enemy, elite, boss, reward, merchant, event)
]
```

#### 地图生成参数
```json
"map_generation": {
    "width": 7,                             // 地图宽度
    "height": 10,                           // 地图高度
    "initial_paths": {
        "min": 1,
        "max": 3                            // 初始路径数量 1-3条
    },
    "node_ratio": {
        "stage_ratios": [
            {
                "max_stage": 9,
                "enemy_weight": 1,
                "reward_weight": 1          // 1级: 1:1
            },
            {
                "max_stage": 19,            // 10-19级: 2:1
                "enemy_weight": 2,
                "reward_weight": 1
            },
            // ... 更高阶级的比例
        ]
    }
}
```

---

### 6. **assets.json** - 美术资源映射
存储美术资源的路径和名称映射。

```json
{
    "entities": {
        "player": "entities/ironclad.png",
        "brute": "entities/brute.png",
        // ... 其他敌人和召唤物
    },
    "icons": {
        "intent_attack": "icons/intent_attack.png",
        // ... 其他图标
    },
    "name_mappings": {
        "entities": {
            "帅帅": "brute",              // 中文 -> 英文ID映射
            // ... 其他映射
        }
    }
}
```

---

## 🔄 配置加载流程

所有配置通过 `ConfigLoader` 类加载：

```python
from core.config_loader import ConfigLoader

# 获取英雄配置
hero_config = ConfigLoader.get_hero_config('ironclad')

# 获取游戏平衡参数
balance = ConfigLoader.get_game_balance()

# 获取地图节点配置
map_config = ConfigLoader.get_map_nodes_config()

# 获取资源路径
asset_path = ConfigLoader.get_asset_path('entities', 'brute')
```

---

## 📝 核心改动

### 已更改的文件：

1. **core/config_loader.py** (新增)
   - 配置加载和缓存功能

2. **core/entity.py**
   - `Player`: 现在从 `heroes.json` 加载初始数据
   - `Summon`: 现在从 `summons.json` 加载数据
   - `Enemy`: 使用 `game_balance.json` 中的缩放参数

3. **core/game_state.py**
   - Boss/Elite 难度使用 `game_balance.json` 配置
   - 玩家回合进度使用配置参数

4. **core/map_generator.py**
   - 从 `map_nodes.json` 加载地图参数
   - 节点比例使用配置的分级系统

5. **ui/battle_scene.py**
   - 敌人贴图路径使用 `sprite_path` 字段

6. **data/monsters.json**
   - 所有敌人名称改为英文

---

## 🎯 维护建议

### 调整怪物难度
编辑 `game_balance.json` 中的敌人缩放参数：
- 增加 `hp_scale_per_stage` 使怪物血量增长更快
- 增加 `dmg_scale_per_stage` 使怪物伤害增长更快

### 添加新敌人
1. 在 `monsters.json` 中添加新敌人
2. 在 `assets.json` 的 `name_mappings.entities` 中添加名称映射
3. 确保 `sprite_path` 指向正确的美术资源

### 调整玩家进度
编辑 `game_balance.json` 中的 `player_progression`：
- 改变 `base_hand_size` 调整手牌数量
- 改变 `max_energy` 调整能量上限

### 添加新英雄
1. 在 `heroes.json` 中添加新英雄配置
2. 在 `core/entity.py` 中使用新英雄ID初始化 `Player`

---

## ✅ 已优化

✓ 所有硬编码数值已提取到配置文件  
✓ 敌人名称改为英文（保留中文别名）  
✓ 美术资源路径统一管理  
✓ 配置支持缓存以优化性能  
✓ 地图生成规则参数化  
✓ 难度平衡参数集中管理
