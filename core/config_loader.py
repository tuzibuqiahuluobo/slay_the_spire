import json
import os
import sys

class ConfigLoader:
    """配置加载器 - 从JSON文件加载游戏配置"""
    
    _cache = {}
    
    @staticmethod
    def load_config(filename):
        """加载配置文件，支持缓存"""
        if filename in ConfigLoader._cache:
            return ConfigLoader._cache[filename]
        
        # 处理打包后的路径
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.join(os.path.dirname(__file__), '..')
            
        config_path = os.path.join(base_dir, 'data', filename)
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                ConfigLoader._cache[filename] = data
                return data
        except FileNotFoundError:
            print(f"配置文件未找到: {config_path}")
            return {}
        except json.JSONDecodeError:
            print(f"配置文件格式错误: {config_path}")
            return {}
    
    @staticmethod
    def get_hero_config(hero_id='ironclad'):
        """获取英雄配置"""
        heroes = ConfigLoader.load_config('heroes.json')
        return heroes.get(hero_id, {})
    
    @staticmethod
    def get_summon_config(summon_id='little_star'):
        """获取召唤物配置"""
        summons = ConfigLoader.load_config('summons.json')
        return summons.get(summon_id, {})
    
    @staticmethod
    def get_game_balance():
        """获取游戏平衡参数"""
        return ConfigLoader.load_config('game_balance.json')
    
    @staticmethod
    def get_map_nodes_config():
        """获取地图节点配置"""
        return ConfigLoader.load_config('map_nodes.json')
    
    @staticmethod
    def get_assets_config():
        """获取资源配置"""
        return ConfigLoader.load_config('assets.json')
    
    @staticmethod
    def get_asset_path(category, resource_id):
        """根据资源ID获取资源路径"""
        assets = ConfigLoader.get_assets_config()
        if category in assets and resource_id in assets[category]:
            return assets[category][resource_id]
        return resource_id  # 如果未找到，返回原ID
    
    @staticmethod
    def clear_cache():
        """清除缓存"""
        ConfigLoader._cache.clear()
