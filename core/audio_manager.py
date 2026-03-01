import pygame
import os
import random
from settings import SOUNDS_DIR

class AudioManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AudioManager, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
            
        pygame.mixer.init()
        self.sounds = {}
        self.music_volume = 0.5
        self.sfx_volume = 0.5
        self.current_music = None
        self.paused = False
        
        # 预加载核心音效
        self.load_sound('attack', 'Impact_sound.wav')
        for i in range(1, 5):
            self.load_sound(f'hit0{i}', f'hit0{i}.flac')
        
        self.load_sound('gold', 'chain.ogg')
        self.load_sound('card_hover', 'item_misc.ogg')
            
        self.initialized = True

    def load_sound(self, name, filename):
        path = os.path.join(SOUNDS_DIR, filename)
        if os.path.exists(path):
            try:
                sound = pygame.mixer.Sound(path)
                sound.set_volume(self.sfx_volume)
                self.sounds[name] = sound
            except Exception as e:
                print(f"Failed to load sound {filename}: {e}")
        else:
            print(f"Sound file not found: {path}")

    def play_bgm(self, filename="The Bustling Port Market.flac"):
        path = os.path.join(SOUNDS_DIR, filename)
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(-1) # Loop indefinitely
                self.current_music = filename
            except Exception as e:
                print(f"Failed to play music {filename}: {e}")
        else:
            print(f"Music file not found: {path}")

    def pause_bgm(self):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.paused = True

    def unpause_bgm(self):
        if self.paused:
            pygame.mixer.music.unpause()
            self.paused = False

    def play_sound(self, name):
        if name in self.sounds:
            self.sounds[name].set_volume(self.sfx_volume)
            self.sounds[name].play()

    def play_hit_sound(self):
        """随机播放受击音效"""
        hit_id = random.randint(1, 4)
        self.play_sound(f'hit0{hit_id}')
        
    def play_attack_sound(self):
        """播放通用攻击音效"""
        self.play_sound('attack')

    def play_gold_sound(self):
        """播放获得金币音效"""
        self.play_sound('gold')

    def play_card_hover_sound(self):
        """播放卡牌悬停音效"""
        self.play_sound('card_hover')

    def set_music_volume(self, volume):
        self.music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.music_volume)

    def set_sfx_volume(self, volume):
        self.sfx_volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.sfx_volume)

audio_manager = AudioManager()
