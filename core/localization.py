class LocalizationManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LocalizationManager, cls).__new__(cls)
            cls._instance.init()
        return cls._instance
    
    def init(self):
        self.current_language = 'zh' # 'zh', 'en', 'ja'
        self.translations = {
            'zh': {
                'settings_title': '设置',
                'volume_music': '音乐音量',
                'volume_sfx': '音效音量',
                'lang_prefix': '语言: ',
                'lang_zh': '中文',
                'lang_en': 'English',
                'lang_ja': '日本語',
                'btn_return_game': '返回游戏',
                'btn_restart_game': '重新开始本局游戏',
                'btn_exit_desktop': '退出到桌面',
                'btn_exit_main_menu': '退出到主菜单',
                
                # Main Menu
                'menu_start': '开始游戏',
                'menu_load': '载入存档',
                'menu_save': '游戏存档',
                'menu_settings': '设置',
                'menu_quit': '退出游戏',
                'menu_title': '杀戮星光',
            },
            'en': {
                'settings_title': 'Settings',
                'volume_music': 'Music',
                'volume_sfx': 'SFX',
                'lang_prefix': 'Language: ',
                'lang_zh': 'Chinese',
                'lang_en': 'English',
                'lang_ja': 'Japanese',
                'btn_return_game': 'Resume Game',
                'btn_restart_game': 'Restart Battle',
                'btn_exit_desktop': 'Exit to Desktop',
                'btn_exit_main_menu': 'Main Menu',
                
                # Main Menu
                'menu_start': 'Start Game',
                'menu_load': 'Load Game',
                'menu_save': 'Save Game',
                'menu_settings': 'Settings',
                'menu_quit': 'Quit Game',
                'menu_title': 'Slay the Starlight',
            },
            'ja': { # Reserved
                'settings_title': '設定',
                'volume_music': '音楽',
                'volume_sfx': '効果音',
                'lang_prefix': '言語: ',
                'lang_zh': '中国語',
                'lang_en': '英語',
                'lang_ja': '日本語',
                'btn_return_game': 'ゲームに戻る',
                'btn_restart_game': 'リスタート',
                'btn_exit_desktop': 'デスクトップに戻る',
                'btn_exit_main_menu': 'メインメニュー',
                
                # Main Menu
                'menu_start': 'ゲーム開始',
                'menu_settings': '設定',
                'menu_quit': 'ゲーム終了',
                'menu_title': 'スレイ・ザ・スターライト',
            }
        }
        
    def set_language(self, lang_code):
        if lang_code in self.translations:
            self.current_language = lang_code
            
    def get(self, key):
        lang_dict = self.translations.get(self.current_language, self.translations['zh'])
        return lang_dict.get(key, key)
        
    def get_next_language(self):
        langs = ['zh', 'en', 'ja'] # Order of toggle
        try:
            idx = langs.index(self.current_language)
            next_idx = (idx + 1) % len(langs)
            return langs[next_idx]
        except ValueError:
            return 'zh'

# Global instance
localization = LocalizationManager()
