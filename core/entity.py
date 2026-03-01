import random
from core.data_library import MONSTER_LIBRARY
from core.config_loader import ConfigLoader
from core.audio_manager import audio_manager

class Entity:
    def __init__(self, name, max_hp):
        self.name = name
        self.max_hp = max_hp
        self.hp = max_hp
        self.block = 0
        self.buffs = {"strength": 0, "weak": 0, "intangible": 0}
        
    def take_damage(self, amount, source_strength=0):
        damage_taken = max(0, amount - self.block)
        blocked = min(amount, self.block)
        
        # 扣除护盾
        self.block = max(0, self.block - amount)
        
        # 扣除生命
        if damage_taken > 0:
            if self.buffs['intangible'] > 0:
                damage_taken = 1
                
            self.hp -= damage_taken
            # 播放受击音效 (如果是真实伤害)
            audio_manager.play_hit_sound()
            
        return blocked, damage_taken

class Player(Entity):
    def __init__(self):
        # 从英雄配置加载数据
        hero_config = ConfigLoader.get_hero_config('player')
        stats = hero_config.get('stats', {})
        
        initial_hp = stats.get('initial_hp', 80)
        super().__init__("英雄", initial_hp)
        
        self.max_energy = stats.get('initial_energy', 3)
        self.energy = self.max_energy
        self.deck = []
        self.hand = []
        self.discard = []
        self.summon = Summon()
        
        # Meta progression attributes
        self.level = stats.get('initial_level', 1)
        self.exp = stats.get('initial_exp', 0)
        self.gold = stats.get('initial_gold', 0)
        
    def get_max_exp(self):
        # 升级经验公式: (n * 2) + 5
        return (self.level * 2) + 5
        
    def gain_exp(self, amount):
        self.exp += amount
        levels_gained = 0
        while self.exp >= self.get_max_exp() and self.level < 999:
            self.exp -= self.get_max_exp()
            self.level += 1
            levels_gained += 1
            # 每次升级可以给予一些额外奖励，比如回血、加最大血量等。
            # 暂时只做等级提升。
        return levels_gained
        
    def reset_turn(self):
        self.energy = self.max_energy
        self.block = 0
        if self.summon.active:
            self.summon.block = 0
        if self.buffs["weak"] > 0:
            self.buffs["weak"] -= 1

class Summon(Entity):
    def __init__(self):
        # 从召唤物配置加载数据
        summon_config = ConfigLoader.get_summon_config('BaiMo')
        stats = summon_config.get('stats', {})
        scaling = summon_config.get('scaling', {})
        
        initial_hp = stats.get('initial_hp', 4)
        super().__init__("白摸", initial_hp)
        
        self.hp = 0
        self.active = False
        self.atk = stats.get('initial_atk', 2)
        self.hp_scaling = scaling.get('hp_increase_per_summon', 2)
        self.atk_scaling = scaling.get('atk_increase_per_summon', 1)
        
    def activate(self):
        if not self.active:
            self.active = True
            self.max_hp = self.max_hp
            self.hp = self.max_hp
        else:
            self.max_hp += self.hp_scaling
            self.hp += self.hp_scaling
            self.atk += self.atk_scaling
            
class Enemy(Entity):
    def __init__(self, data, stage):
        # 获取难度配置
        balance = ConfigLoader.get_game_balance()
        enemy_scaling = balance.get('difficulty', {}).get('enemy_scaling', {})
        
        # 计算敌人等级
        level_mult = balance.get('enemy_level', {}).get('level_multiplier_per_stage', 1.2)
        self.level = max(1, int(stage * level_mult))

        # 使用配置文件中的缩放参数
        hp_scale_per = enemy_scaling.get('hp_scale_per_stage', 0.06)
        hp_linear = enemy_scaling.get('hp_linear_bonus_per_stage', 2)
        hp_scale = 1.0 + hp_scale_per * max(0, (stage - 1))
        scaled_hp = int(data['hp'] * hp_scale + max(0, (stage - 1) * hp_linear))
        
        super().__init__(data['name'], max(1, scaled_hp))
        self.sprite = data['sprite']
        
        # 从 assets.json 获取正确的图片路径，而不是依赖 monster.json 或猜测
        assets_config = ConfigLoader.get_assets_config()
        self.image_path = assets_config.get('entities', {}).get(self.name)
        
        self.type = data['type']
        
        # 计算攻击力
        base_damage = data.get('baseDamage', enemy_scaling.get('default_base_damage', 6))
        dmg_scale_per = enemy_scaling.get('dmg_scale_per_stage', 0.04)
        self.base_damage = max(1, int(base_damage * (1.0 + dmg_scale_per * max(0, (stage - 1)))))
        
        self.actions = data.get('actions', [])
        self.intent = None
        
    def generate_intent(self, stage, is_summon_active):
        if self.type == 'attacker':
            if random.random() < 0.7:
                val = self.base_damage + stage // 2
                target = 'summon' if is_summon_active and random.random() < 0.5 else 'player'
                self.intent = {'type': 'attack', 'value': val, 'target': target}
            else:
                val = 6 + stage
                self.intent = {'type': 'block', 'value': val}
        else:
            r = random.random()
            cumulative = 0
            for action in self.actions:
                cumulative += action['weight']
                if r < cumulative:
                    val = action['value'] + stage // 3
                    target = 'player'
                    if action['type'] == 'attack' and is_summon_active and random.random() < 0.5:
                        target = 'summon'
                    self.intent = {'type': action['type'], 'value': val, 'target': target}
                    break
