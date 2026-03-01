import pygame
import sys
from settings import FPS, LOGICAL_WIDTH, LOGICAL_HEIGHT, COLORS
from ui.display_manager import display_manager
from core.game_state import GameState
from ui.battle_scene import BattleScene
from ui.map_scene import MapScene
from ui.top_bar import TopBar
from utils.input_handler import input_handler
from core.config_loader import ConfigLoader
from utils.resource_manager import resource_manager
from ui.main_menu_scene import MainMenuScene
from ui.store_scene import StoreScene
from ui.settings_menu import SettingsMenu
from core.audio_manager import audio_manager

def main():
    clock = pygame.time.Clock()
    
    # 初始化核心状态与 UI 场景
    game_state = GameState()
    battle_scene = BattleScene(game_state)
    map_scene = MapScene(game_state)
    store_scene = StoreScene(game_state)
    top_bar = TopBar(game_state)
    main_menu_scene = MainMenuScene(game_state)
    settings_menu = SettingsMenu(game_state)
    
    running = True
    
    # 状态机：'main_menu', 'game'
    # 暂停由 settings_menu.active 决定
    current_state = 'main_menu'
    
    # 地图覆盖层状态
    show_map = False
    map_btn_rect = pygame.Rect(20, 80, 60, 60) # 左侧的地图图标按钮，稍微下移避开顶部栏
    
    def update_game_state_refs(new_state):
        nonlocal game_state, battle_scene, map_scene, store_scene, top_bar, main_menu_scene, settings_menu
        game_state = new_state
        battle_scene = BattleScene(game_state)
        map_scene = MapScene(game_state)
        store_scene = StoreScene(game_state)
        top_bar = TopBar(game_state)
        main_menu_scene.gs = game_state
        # 主菜单按钮可能需要刷新（比如存档存在了）
        main_menu_scene.setup_buttons()
        settings_menu.gs = game_state

    while running:
        # 获取输入状态
        mouse_pos = pygame.mouse.get_pos()
        logical_mouse = input_handler.get_logical_mouse_pos(mouse_pos)
        keys = pygame.key.get_pressed()
        is_tab_held = keys[pygame.K_TAB]
        
        is_map_icon_held = False
        if logical_mouse and pygame.mouse.get_pressed()[0] and not settings_menu.active:
            if map_btn_rect.collidepoint(logical_mouse):
                is_map_icon_held = True
        
        in_store = game_state.map_node_current and game_state.map_node_current.type == 'merchant' and not game_state.in_battle
        force_map_mode = not game_state.in_battle and not in_store
        show_map_overlay = is_tab_held or is_map_icon_held
        
        # --- 事件循环 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                display_manager.handle_resize(event.w, event.h)
                
            # 1. 优先处理全屏覆盖的设置菜单
            if settings_menu.active:
                if settings_menu.handle_event(event):
                    # 检查设置菜单的挂起操作
                    if settings_menu.pending_action:
                        action = settings_menu.pending_action
                        settings_menu.pending_action = None
                        
                        if action == 'exit_desktop':
                            running = False
                        elif action == 'return_main':
                            current_state = 'main_menu'
                            # 返回主菜单时重置游戏状态 (防止污染下一局)
                            update_game_state_refs(GameState())
                        elif action == 'restart_game':
                            current_state = 'game'
                            # 尝试恢复快照
                            if game_state.restore_state():
                                # 恢复成功，只需要刷新 battle_scene 的显示状态
                                # 因为 battle_scene 持有 game_state 引用，数据已经回滚
                                # 但为了保险，重建 battle_scene
                                battle_scene = BattleScene(game_state)
                                if game_state.on_message: game_state.on_message("重新开始本局...")
                            else:
                                # 恢复失败（无快照），重置整个游戏
                                update_game_state_refs(GameState())
                                if game_state.on_message: game_state.on_message("无法回溯，已重新开始游戏")
                            
                    continue # 事件被设置菜单消费
            
            # 2. 根据主状态分发事件
            if current_state == 'main_menu':
                action = main_menu_scene.handle_event(event)
                if action == 'start_game':
                    current_state = 'game'
                    # 每次新开始，确保是新状态（除非是继续）
                    # 这里如果是"开始游戏"，通常意味着新游戏
                    # 但 MainMenuScene 可能会改成 "继续游戏" 如果有内存状态
                    # 简单起见，如果 game_state.stage > 1 视为继续，否则重置
                    # 但 main_menu_scene 的按钮是根据 gs 状态生成的。
                    # 如果玩家刚进游戏，gs 是新的。
                    pass
                elif action == 'save_game':
                    game_state.save_game()
                    # 刷新主菜单按钮（因为现在有存档了）
                    main_menu_scene.setup_buttons()
                elif action == 'load_game':
                    loaded_state = GameState.load_game()
                    if loaded_state:
                        update_game_state_refs(loaded_state)
                        current_state = 'game'
                elif action == 'settings':
                    settings_menu.open()
                elif action == 'quit_game':
                    running = False
                    
            elif current_state == 'game':
                # 暂停/设置
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    settings_menu.open()
                    continue
                
                # 顶部栏点击检测 (设置按钮)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if logical_mouse and top_bar.setting_btn_rect.collidepoint(logical_mouse):
                        settings_menu.open()
                        continue
                
                # 游戏内逻辑分发
                if force_map_mode:
                    if map_scene.handle_event(event):
                        if game_state.in_battle:
                            battle_scene.sync_hand()
                elif in_store:
                    action = store_scene.handle_event(event)
                    if action == 'return_to_map':
                        if game_state.map_node_current:
                            # 通过将类型强制转为普通已访问节点类型（或者给它加个前缀），
                            # 它可以彻底退出 `in_store` 的判断条件 `type == 'merchant'`
                            # 我们把它变成 'visited_merchant'，这样既能保留信息，又不会被识别成可用商店
                            game_state.map_node_current.room_type = 'Visited_Shop'
                            
                            # 释放子节点，允许往下走
                            game_state.map_node_current.state = 'visited'
                            for child in game_state.map_node_current.children:
                                if child.state == 'locked':
                                    child.state = 'available'
                            # 统计节点以便 boss 的机制能正常运作
                            game_state.nodes_explored_this_stage += 1
                            
                        # 强制切换当前帧的状态标识，确保事件不会泄漏
                        in_store = False
                        force_map_mode = True
                        
                elif show_map_overlay:
                    pass
                else:
                    if not game_state.battle_won and not game_state.game_over:
                        # 过滤掉点击在地图图标上的事件
                        if event.type == pygame.MOUSEBUTTONDOWN and logical_mouse:
                            if map_btn_rect.collidepoint(logical_mouse):
                                continue
                        battle_scene.handle_event(event)
                    elif game_state.battle_won:
                        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and logical_mouse:
                            if hasattr(battle_scene, 'reward_rects'):
                                for i, rect in enumerate(battle_scene.reward_rects):
                                    if rect.collidepoint(logical_mouse):
                                        game_state.claim_reward(i)
                                        battle_scene.sync_hand()
                                        break
                            if hasattr(battle_scene, 'skip_rect') and battle_scene.skip_rect.collidepoint(logical_mouse):
                                game_state.skip_reward()
                                battle_scene.sync_hand()
                    elif game_state.game_over:
                         if event.type == pygame.MOUSEBUTTONDOWN:
                             # 游戏结束点击：重置并返回
                            update_game_state_refs(GameState())
                            current_state = 'main_menu' # 返回主菜单更合理

        # --- 逻辑更新 ---
        if current_state == 'main_menu':
            main_menu_scene.update()
        elif current_state == 'game':
            if not settings_menu.active:
                if not force_map_mode and not in_store:
                    battle_scene.update()
                elif in_store:
                    store_scene.update()
                
        # --- 渲染阶段 ---
        display_manager.surface.fill((20, 20, 30)) # Clear
        
        if current_state == 'main_menu':
            main_menu_scene.draw(display_manager.surface)
            if settings_menu.active:
                settings_menu.draw(display_manager.surface)
                
        elif current_state == 'game':
            if force_map_mode:
                display_manager.surface.fill((20, 20, 30))
                map_scene.draw(display_manager.surface)
            elif in_store:
                store_scene.draw(display_manager.surface)
            else:
                battle_scene.draw(display_manager.surface)
                # Map Icon
                pygame.draw.rect(display_manager.surface, (50, 50, 50), map_btn_rect, border_radius=10)
                
                map_icon = ConfigLoader.get_assets_config().get('ui_icons', {}).get('map_button')
                resource_manager.draw_sprite_or_fallback(display_manager.surface, map_icon, map_btn_rect.center, "🗺️", display_manager.get_font('large'), COLORS['text_white'], max_size=(48, 48))
                
                if show_map_overlay:
                    map_scene.draw(display_manager.surface)
            
            # UI Overlay
            top_bar.draw(display_manager.surface)
            
            # Settings Menu Overlay
            if settings_menu.active:
                settings_menu.draw(display_manager.surface)
        
        display_manager.update()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
