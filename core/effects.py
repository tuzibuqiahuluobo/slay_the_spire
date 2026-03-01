class EffectHandler:
    @staticmethod
    def execute(game_state, card, target, friendly_target):
        """
        根据卡牌 ID 执行对应效果。
        在一个更高级的架构中，这里会使用函数注册表或脚本求值系统。
        """
        cid = card.id
        val = card.current_value
        player = game_state.player
        
        def deal_dmg(t, amount):
            if t and t.hp > 0:
                # 计算玩家力量增益
                dmg = amount + player.buffs['strength']
                # 计算玩家虚弱减益
                if player.buffs['weak'] > 0:
                    dmg = int(dmg * 0.75)
                
                # 狂暴机制：高回合伤害加倍
                if game_state.turn_count >= 10:
                    dmg *= 2
                
                blocked, actual = t.take_damage(dmg)
                if game_state.on_damage: game_state.on_damage(t, actual, 'damage')
                if blocked > 0 and game_state.on_block: game_state.on_block(t, blocked)
                
                # 召唤物协同攻击
                if player.summon.active and player.summon.hp > 0:
                    sb, sa = t.take_damage(player.summon.atk)
                    if sa > 0 and game_state.on_damage: game_state.on_damage(t, sa, 'damage')
                    if sb > 0 and game_state.on_block: game_state.on_block(t, sb)

        # 字典映射分发，保持架构清晰
        # 我们使用内部函数来封装具体动作
        effects = {
            'strike': lambda: deal_dmg(target, val),
            'defend': lambda: add_block(val),
            'bash': lambda: deal_dmg(target, val),
            'call_star': lambda: summon_star(),
            'iron_wave': lambda: [deal_dmg(target, val), add_block_direct(card.block)],
            'body_slam': lambda: deal_dmg(target, player.block),
            'shrug_it_off': lambda: [add_block_direct(val), game_state.draw_cards(card.draw)],
            'heavy_blade': lambda: deal_dmg(target, val),
            'pommel_strike': lambda: [deal_dmg(target, val), game_state.draw_cards(card.draw)],
            'blood_letting': lambda: blood_letting_action(),
            'offering': lambda: offering_action(),
            'rampage': lambda: rampage_action()
        }

        def add_block(amount):
            if friendly_target == 'summon' and player.summon.active:
                player.summon.block += amount
            else:
                player.block += amount

        def add_block_direct(amount):
            player.block += amount

        def summon_star():
            if not player.summon.active:
                player.summon.activate()
                if game_state.on_message: game_state.on_message("召唤：小星星")
            else:
                player.summon.activate()
                if game_state.on_message: game_state.on_message("小星星 升级了！")
                
        def blood_letting_action():
            player.hp = max(1, player.hp - card.hpCost)
            player.energy += card.energyGain
            
        def offering_action():
            player.hp = max(1, player.hp - card.hpCost)
            player.energy += card.energyGain
            game_state.draw_cards(card.draw)
            
        def rampage_action():
            deal_dmg(target, val)
            card.current_value += card.grow

        if cid in effects:
            action = effects[cid]
            action()
        else:
            print(f"警告：未实现卡牌 {cid} 的效果。")
