import pygame
import os
from settings import IMAGES_DIR, SOUNDS_DIR

class ResourceManager:
    def __init__(self):
        self.images = {}
        self.sounds = {}
        # 避免与 display_manager 产生循环导入
        
    def get_image(self, path_relative_to_images):
        """
        加载图像并进行缓存，返回 pygame.Surface。
        如果找不到图片，则返回 None。
        示例用法: get_image("entities/player.png")
        """
        if path_relative_to_images in self.images:
            return self.images[path_relative_to_images]
            
        full_path = os.path.join(IMAGES_DIR, *path_relative_to_images.split('/'))
        if os.path.exists(full_path):
            img = pygame.image.load(full_path).convert_alpha()
            self.images[path_relative_to_images] = img
            return img
        else:
            # 找不到图片时返回 None，这样上层可以平滑降级为 Emoji
            self.images[path_relative_to_images] = None
            return None

    def draw_sprite_or_fallback(self, surface, image_path, center_pos, fallback_text, font_obj, fallback_color=(255, 255, 255), alpha=255, max_size=None):
        """
        尝试加载并绘制指定的图片素材。如果找不到图片，则使用提供的 fallback_text (如 Emoji) 进行渲染。
        
        :param surface: 目标绘制的 Surface
        :param image_path: 相对于 IMAGES_DIR 的图片路径，如 'entities/player.png'
        :param center_pos: 绘制中心点坐标 (x, y)
        :param fallback_text: 当图片不存在时退回使用的文本/Emoji
        :param font_obj: 用于渲染 Fallback 文本的字体对象
        :param fallback_color: Fallback 文本的颜色
        :param alpha: 透明度 (0-255)，目前主要用于虚化状态
        :param max_size: (width, height) 元组。如果提供且图片尺寸超过此值，则按比例缩小。
        """
        img = self.get_image(image_path)
        if img:
            # 缩放逻辑
            final_img = img
            if max_size:
                w, h = img.get_size()
                target_w, target_h = max_size
                
                # 如果图片比目标尺寸大，才进行缩放
                if w > target_w or h > target_h:
                    scale = min(target_w / w, target_h / h)
                    new_size = (int(w * scale), int(h * scale))
                    final_img = pygame.transform.smoothscale(img, new_size)
            
            # 透明度处理
            if alpha < 255:
                # 必须复制一份以免修改原缓存图
                if final_img == img:
                    final_img = img.copy()
                final_img.set_alpha(alpha)
            
            rect = final_img.get_rect(center=center_pos)
            surface.blit(final_img, rect)
        else:
            # 如果没有图片，渲染文本/Emoji
            text_surf = font_obj.render(fallback_text, True, fallback_color)
            if alpha < 255:
                text_surf.set_alpha(alpha)
            surface.blit(text_surf, text_surf.get_rect(center=center_pos))

    def play_sound(self, sound_name):
        """
        加载并播放音效。
        示例用法: play_sound("hit.wav")
        """
        if sound_name not in self.sounds:
            full_path = os.path.join(SOUNDS_DIR, sound_name)
            if os.path.exists(full_path):
                self.sounds[sound_name] = pygame.mixer.Sound(full_path)
            else:
                print(f"警告: 未找到音效文件 {full_path}。")
                return
                
        self.sounds[sound_name].play()

resource_manager = ResourceManager()
