import random

class Card:
    def __init__(self, data):
        self.id = data['id']
        self.name = data['name']
        self.type = data['type']
        self.cost = data['cost']
        self.value = data.get('value', 0)
        self.desc_template = data['desc']
        self.targetType = data.get('targetType', 'enemy')
        self.innate = data.get('innate', False)
        self.retain = data.get('retain', False)
        self.block = data.get('block', 0)
        self.draw = data.get('draw', 0)
        self.energyGain = data.get('energyGain', 0)
        self.hpCost = data.get('hpCost', 0)
        self.grow = data.get('grow', 0)
        
        # Keep track of modified damage for Rampage, etc.
        self.current_value = self.value
        
    def get_desc(self, player_strength=0, player_weak=0):
        # 计算动态值
        display_val = self.current_value
        if self.type == 'attack':
            final_dmg = display_val + player_strength
            if player_weak > 0:
                final_dmg = int(final_dmg * 0.75)
            display_val = final_dmg
            
        return self.desc_template.replace('{val}', str(display_val))
