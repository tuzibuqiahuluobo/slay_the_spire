import random
import copy
import pickle
import os
from core.entity import Player, Enemy
from core.cards import Card
from core.data_library import CARD_LIBRARY, MONSTER_LIBRARY
from core.map_generator_new import MapGeneratorNew as MapGenerator
from core.config_loader import ConfigLoader
from core.audio_manager import audio_manager

class GameState:
    def __init__(self):
        self.player = Player()
        self.enemies = []
        self.stage = 1
        
        # 初始化状态标志，必须在访问节点前完成
        self.in_battle = False
        self.nodes_explored_this_stage = 0
        self.turn = 'player'
        self.turn_count = 1
        self.game_over = False
        self.battle_won = False
        self.reward_cards = []
        self.enemy_action_queue = []
        self.action_timer = 0
        self.restore_snapshot = None
        
        # 事件回调
        self.on_damage = None
        self.on_heal = None
        self.on_block = None
        self.on_message = None
        
        # 商店系统状态
        self.store_refreshes_used = 0
        self.current_store_items = []
        
        self.init_deck()
        
        # 地图系统
        map_config = ConfigLoader.get_map_nodes_config()
        map_gen_config = map_config.get('map_generation', {})
        self.total_chapters = map_gen_config.get('total_chapters', 6)
        self.chapter = 1
        
        self.map_generator = MapGenerator()
        self.map_generator.generate(self.stage)
        
        # 默认直接进入起点 (需要在所有属性初始化后调用)
        self.map_node_current = self.map_generator.start_node
        if self.map_node_current:
             self.visit_map_node(self.map_node_current)

    def create_restore_point(self):
        """创建当前状态的快照，用于重新开始本局"""
        # 暂时移除 snapshot 引用
        temp_snapshot = self.restore_snapshot
        self.restore_snapshot = None
        
        # 暂时移除回调，避免 pickle/deepcopy 错误
        callbacks = {
            'on_damage': self.on_damage,
            'on_heal': self.on_heal,
            'on_block': self.on_block,
            'on_message': self.on_message
        }
        self.on_damage = None
        self.on_heal = None
        self.on_block = None
        self.on_message = None
        
        try:
            self.restore_snapshot = copy.deepcopy(self)
        except Exception as e:
            print(f"创建快照失败: {e}")
            self.restore_snapshot = None
        finally:
            self.on_damage = callbacks['on_damage']
            self.on_heal = callbacks['on_heal']
            self.on_block = callbacks['on_block']
            self.on_message = callbacks['on_message']
    
    def restore_state(self):
        """恢复到最近的快照状态"""
        if self.restore_snapshot:
            snapshot = self.restore_snapshot
            restored_data = copy.deepcopy(snapshot)
            self.__dict__.update(restored_data.__dict__)
            self.process_current_node()
            return True
        return False

    def save_game(self, filename="savegame.pkl"):
        """保存游戏到文件"""
        try:
            callbacks = {
                'on_damage': self.on_damage,
                'on_heal': self.on_heal,
                'on_block': self.on_block,
                'on_message': self.on_message
            }
            self.on_damage = None
            self.on_heal = None
            self.on_block = None
            self.on_message = None
            
            with open(filename, 'wb') as f:
                pickle.dump(self, f)
            print(f"游戏已保存到 {filename}")
            
            self.on_damage = callbacks['on_damage']
            self.on_heal = callbacks['on_heal']
            self.on_block = callbacks['on_block']
            self.on_message = callbacks['on_message']
            return True
        except Exception as e:
            print(f"保存失败: {e}")
            return False

    @staticmethod
    def load_game(filename="savegame.pkl"):
        """从文件加载游戏"""
        if not os.path.exists(filename):
            return None
        try:
            with open(filename, 'rb') as f:
                state = pickle.load(f)
            print(f"游戏已从 {filename} 加载")
            return state
        except Exception as e:
            print(f"加载失败: {e}")
            return None

    def visit_map_node(self, node):
        if self.in_battle: return
        
        if self.map_node_current:
            if node not in self.map_node_current.children: 
                if node != self.map_generator.start_node or self.map_node_current != self.map_generator.start_node:
                    return
        
        self.map_node_current = node
        self.map_generator.visit(node)
        
        if node.type != 'start':
            self.nodes_explored_this_stage += 1
            
        self.create_restore_point()
        self.process_current_node()

    def process_current_node(self):
        node = self.map_node_current
        if not node: return

        if node.type in ['enemy', 'elite', 'boss']:
            self.start_battle(node.type)
        elif node.type == 'reward':
            r = random.random()
            if r < 0.33:
                self.player.gold += 10
                audio_manager.play_gold_sound()
                if self.on_message: self.on_message("获得了 10 枚金币！")
            elif r < 0.66:
                self.player.level += 1
                self.player.exp = 0
                if self.on_message: self.on_message(f"等级提升！当前等级：{self.player.level}")
            else:
                special_cards = []
                for cid, data in CARD_LIBRARY.items():
                    if data.get('innate', False) or data.get('retain', False):
                        special_cards.append(cid)
                if special_cards:
                    chosen = random.choice(special_cards)
                    self.player.deck.append(Card(CARD_LIBRARY[chosen]))
                    c_name = CARD_LIBRARY[chosen]['name']
                    if self.on_message: self.on_message(f"获得特殊卡牌：{c_name}")
                else:
                    self.player.gold += 10
                    audio_manager.play_gold_sound()
                    if self.on_message: self.on_message("获得了 10 枚金币！")
        elif node.type == 'merchant':
            # 进入商店时初始化商店状态
            self.store_refreshes_used = 0
            self.generate_store_items()
            # 移除 "进入商店" 提示
        elif node.type == 'camp':
             heal = int(self.player.max_hp * 0.2)
             self.player.hp = min(self.player.max_hp, self.player.hp + heal)
             if self.on_message: self.on_message(f"在营地休息，恢复了 {heal} 点生命")
        elif node.type == 'event':
             outcome = random.choice(['gold', 'heal', 'damage'])
             if outcome == 'gold':
                 self.player.gold += 20
                 audio_manager.play_gold_sound()
                 if self.on_message: self.on_message("事件：发现小宝箱，获得20金币")
             elif outcome == 'heal':
                 self.player.hp = min(self.player.max_hp, self.player.hp + 5)
                 if self.on_message: self.on_message("事件：喝下泉水，恢复5点生命")
             else:
                 self.player.hp = max(1, self.player.hp - 3)
                 if self.on_message: self.on_message("事件：踩到陷阱，损失3点生命")
        elif node.type == 'start':
            if self.on_message: self.on_message("旅途开始...")

    def init_deck(self):
        base_deck_ids = [
            'strike', 'strike', 'strike', 'strike', 
            'defend', 'defend', 'defend', 'defend',
            'bash', 'call_star'
        ]
        self.player.deck = [Card(CARD_LIBRARY[cid]) for cid in base_deck_ids]
        random.shuffle(self.player.deck)

    def start_battle(self, node_type='enemy'):
        self.in_battle = True
        
        num_enemies = 1
        if node_type == 'boss':
            num_enemies = 1
            stage_mod = self.stage + 5
        elif node_type == 'elite':
            num_enemies = 2
            stage_mod = self.stage + 2
        else:
            num_enemies = random.randint(1, 3)
            stage_mod = self.stage
            
        self.enemies = []
        for i in range(num_enemies):
            template = random.choice(MONSTER_LIBRARY)
            enemy = Enemy(template, stage_mod)
            if node_type == 'boss':
                balance = ConfigLoader.get_game_balance()
                boss_config = balance.get('boss', {})
                max_exploration = self.map_generator.height
                explored_ratio = min(1.0, self.nodes_explored_this_stage / max_exploration)
                hp_mult = boss_config.get('hp_multiplier', 3.0)
                dmg_bonus = boss_config.get('dmg_bonus', 5)
                weakness_max = boss_config.get('exploration_weakness_max', 0.8)
                min_hp = boss_config.get('min_hp', 10)
                min_dmg = boss_config.get('min_dmg', 2)
                weakness_factor = 1.0 - (explored_ratio * weakness_max) 
                final_hp = int(enemy.max_hp * hp_mult * weakness_factor)
                enemy.max_hp = max(min_hp, final_hp)
                enemy.hp = enemy.max_hp
                final_dmg = int((enemy.base_damage + dmg_bonus) * weakness_factor)
                enemy.base_damage = max(min_dmg, final_dmg)
                if self.on_message:
                    self.on_message(f"探索度 {int(explored_ratio*100)}%，Boss 实力削弱 {int(explored_ratio*weakness_max*100)}%！")
            elif node_type == 'elite':
                balance = ConfigLoader.get_game_balance()
                elite_config = balance.get('elite', {})
                elite_hp_mult = elite_config.get('hp_multiplier', 1.5)
                enemy.max_hp = int(enemy.max_hp * elite_hp_mult)
                enemy.hp = enemy.max_hp
            enemy.generate_intent(stage_mod, self.player.summon.active)
            self.enemies.append(enemy)
            
        self.turn = 'player'
        self.turn_count = 1
        self.game_over = False
        self.battle_won = False
        self.player.hand.clear()
        self.player.discard.clear()
        self.start_player_turn()
        
    def start_player_turn(self):
        self.turn = 'player'
        bonus_energy = (self.turn_count - 1) // 3
        balance = ConfigLoader.get_game_balance()
        max_energy_cap = balance.get('player_progression', {}).get('max_energy', 10)
        current_max = min(max_energy_cap, 3 + bonus_energy)
        self.player.max_energy = current_max
        self.player.reset_turn()
        hand_size = balance.get('player_progression', {}).get('base_hand_size', 5)
        if self.turn_count == 1:
            innate_cards = [c for c in self.player.deck if c.innate]
            self.player.deck = [c for c in self.player.deck if not c.innate]
            self.player.hand.extend(innate_cards)
            self.draw_cards(hand_size - len(innate_cards))
        else:
            self.draw_cards(hand_size - len(self.player.hand))
        rage_turn = balance.get('player_progression', {}).get('rage_mode_turn', 10)
        rage_msg = ""
        if self.turn_count >= rage_turn:
            rage_msg = " (狂暴！)"
        if self.on_message:
            self.on_message(f"第 {self.turn_count} 回合{rage_msg}")

    def draw_cards(self, count):
        for _ in range(count):
            if len(self.player.deck) == 0:
                if len(self.player.discard) == 0:
                    break
                self.player.deck = self.player.discard[:]
                self.player.discard.clear()
                random.shuffle(self.player.deck)
                if self.on_message:
                    self.on_message("重新洗牌")
            if len(self.player.deck) > 0:
                self.player.hand.append(self.player.deck.pop())

    def play_card(self, card_idx, target_idx=None, friendly_target=None):
        if self.turn != 'player': return False
        card = self.player.hand[card_idx]
        if self.player.energy < card.cost:
            if self.on_message: self.on_message("能量不足！")
            return False
        self.player.energy -= card.cost
        self.player.hand.pop(card_idx)
        self.player.discard.append(card)
        target_enemy = None
        if target_idx is not None and 0 <= target_idx < len(self.enemies):
            target_enemy = self.enemies[target_idx]
        self.execute_card(card, target_enemy, friendly_target)
        self.check_death()
        return True

    def execute_card(self, card, target, friendly_target):
        from core.effects import EffectHandler
        from core.audio_manager import audio_manager
        if card.type == 'attack':
            audio_manager.play_attack_sound()
        EffectHandler.execute(self, card, target, friendly_target)

    def end_turn(self):
        if self.turn != 'player': return
        self.turn = 'enemy'
        retained = []
        for c in self.player.hand:
            if c.retain: retained.append(c)
            else: self.player.discard.append(c)
        self.player.hand = retained
        if self.on_message: self.on_message("敌人回合")
        self.enemy_action_queue = [e for e in self.enemies if e.hp > 0]
        self.action_timer = 60 

    def update(self):
        if not self.in_battle: return
        if self.turn == 'enemy' and not self.game_over and not self.battle_won:
            if self.action_timer > 0:
                self.action_timer -= 1
            else:
                if len(self.enemy_action_queue) > 0:
                    enemy = self.enemy_action_queue.pop(0)
                    if enemy.hp > 0:
                        self.execute_enemy_action(enemy)
                    self.action_timer = 60 
                else:
                    self.turn_count += 1
                    for e in self.enemies:
                        if e.hp > 0:
                            if e.buffs['intangible'] > 0: e.buffs['intangible'] -= 1
                            e.generate_intent(self.stage, self.player.summon.active)
                    self.start_player_turn()

    def execute_enemy_action(self, enemy):
        intent = enemy.intent
        t = intent['type']
        val = intent['value']
        if t == 'attack':
            target = self.player.summon if (intent.get('target') == 'summon' and self.player.summon.active) else self.player
            from core.audio_manager import audio_manager
            audio_manager.play_hit_sound()
            final_dmg = val * 2 if self.turn_count >= 10 else val
            blocked, actual = target.take_damage(final_dmg)
            if self.on_damage and actual > 0: self.on_damage(target, actual, 'damage')
            if self.on_block and blocked > 0: self.on_block(target, blocked)
            if target == self.player.summon and target.hp <= 0:
                target.active = False
                if self.on_message: self.on_message("小星星 消失了...")
        elif t == 'block':
            enemy.block += val
            if self.on_block: self.on_block(enemy, val)
        elif t == 'heal':
            allies = [e for e in self.enemies if e.hp > 0]
            if allies:
                target = min(allies, key=lambda e: e.hp/e.max_hp)
                target.hp = min(target.max_hp, target.hp + val)
                if self.on_heal: self.on_heal(target, val)
        elif t == 'buff':
            for e in self.enemies:
                if e.hp > 0: e.base_damage += val
            if self.on_message: self.on_message("敌人力量提升！")
        elif t == 'debuff':
            self.player.buffs['weak'] += val
            if self.on_message: self.on_message(f"玩家虚弱 {val} 回合")
        elif t == 'intangible':
            enemy.buffs['intangible'] += val
        self.check_death()

    def check_death(self):
        alive_enemies = [e for e in self.enemies if e.hp > 0]
        if len(alive_enemies) == 0 and not self.battle_won:
            self.battle_won = True
            self.process_battle_rewards()
            self.generate_rewards()
            if self.map_node_current and self.map_node_current.type == 'boss':
                self.handle_boss_defeat()
        if self.player.hp <= 0 and not self.game_over:
            self.game_over = True
            if self.on_message: self.on_message("战斗失败...")
            self.in_battle = False
    
    def handle_boss_defeat(self):
        if self.chapter >= self.total_chapters:
            if self.on_message: self.on_message(f"恭喜通关！第{self.chapter}章完成")
        else:
            self.chapter += 1
            self.stage += 1
            self.advance_to_next_chapter()
    
    def advance_to_next_chapter(self):
        self.map_generator.clear()
        self.map_generator.generate(self.stage)
        self.map_node_current = self.map_generator.start_node
        if self.map_node_current:
             self.map_generator.visit(self.map_node_current)
        self.nodes_explored_this_stage = 0
        self.in_battle = False
        self.battle_won = False
        self.game_over = False
        self.turn_count = 1
        self.enemies = []
        if self.on_message: 
            self.on_message(f"进入第{self.chapter}章...")

    def process_battle_rewards(self):
        total_gold = 0
        total_exp = 0
        node_type = self.map_node_current.type if self.map_node_current else 'enemy'
        for e in self.enemies:
            if node_type == 'boss':
                total_gold += 5
                total_exp += (self.stage + 3) * 2
            else:
                total_gold += 2
                total_exp += self.stage + 3
        self.player.gold += total_gold
        if total_gold > 0:
            audio_manager.play_gold_sound()
        levels_gained = self.player.gain_exp(total_exp)
        msg = f"战斗胜利！获得 {total_exp} 经验, {total_gold} 金币"
        if levels_gained > 0:
            msg += f" (升级了!)"
        if self.on_message:
            self.on_message(msg)

    def generate_rewards(self):
        pool = [k for k in CARD_LIBRARY.keys() if k not in ['strike', 'defend', 'bash']]
        random.shuffle(pool)
        self.reward_cards = [Card(CARD_LIBRARY[cid]) for cid in pool[:3]]

    def claim_reward(self, card_idx):
        if 0 <= card_idx < len(self.reward_cards):
            self.player.deck.append(self.reward_cards[card_idx])
            self.finish_battle()

    def skip_reward(self):
        self.finish_battle()
        
    def generate_store_items(self):
        from core.data_library import STORE_LIBRARY
        pool = list(STORE_LIBRARY.values())
        if len(pool) >= 3:
            self.current_store_items = random.sample(pool, 3)
        else:
            self.current_store_items = pool[:]
        
    def finish_battle(self):
        self.in_battle = False
        self.battle_won = False
        self.player.deck.extend(self.player.hand)
        self.player.deck.extend(self.player.discard)
        self.player.hand.clear()
        self.player.discard.clear()
        self.stage += 1
        if self.map_node_current and self.map_node_current.type == 'boss':
            if self.on_message: self.on_message("通关！生成新地图...")
            self.map_generator = MapGenerator()
            self.map_generator.generate(self.stage)
            self.map_node_current = None
            self.nodes_explored_this_stage = 0
