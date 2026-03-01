class Relic:
    def __init__(self, relic_id, name, desc):
        self.id = relic_id
        self.name = name
        self.desc = desc

    def on_equip(self, player):
        pass

    def on_combat_start(self, game_state):
        pass

    def on_turn_start(self, game_state):
        pass

# 示例遗物
class BurningBlood(Relic):
    def __init__(self):
        super().__init__("burning_blood", "燃烧之血", "在战斗结束时，回复 6 点生命。")

    def on_combat_end(self, game_state):
        game_state.player.hp = min(game_state.player.max_hp, game_state.player.hp + 6)
        if game_state.on_heal:
            game_state.on_heal(game_state.player, 6)


class Shop:
    def __init__(self):
        self.cards_for_sale = []
        self.relics_for_sale = []
        self.card_removal_price = 75

    def generate_inventory(self, stage):
        # 下陋逻辑，基于进程填充⢺店\u4e3b摩购
        pass
