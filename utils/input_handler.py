from settings import LOGICAL_WIDTH, LOGICAL_HEIGHT
from ui.display_manager import display_manager

class InputHandler:
    def __init__(self):
        pass

    def get_logical_mouse_pos(self, physical_pos):
        """
        将物理窗口坐标转换为逻辑的1920x1080坐标
        通过反转在 DisplayManager 中应用的信箱效果和缩放来实现
        """
        px, py = physical_pos
        
        # 缩放因子
        scale_x = display_manager.window_width / LOGICAL_WIDTH
        scale_y = display_manager.window_height / LOGICAL_HEIGHT
        scale = min(scale_x, scale_y)
        
        # 缩放后的区域宽高
        scaled_width = int(LOGICAL_WIDTH * scale)
        scaled_height = int(LOGICAL_HEIGHT * scale)
        
        # 偏移量
        x_offset = (display_manager.window_width - scaled_width) // 2
        y_offset = (display_manager.window_height - scaled_height) // 2
        
        # 检查是否点击在信箱效果区域外
        if px < x_offset or px > x_offset + scaled_width or py < y_offset or py > y_offset + scaled_height:
            return None # 点击了黑色条
            
        # 反向映射
        lx = (px - x_offset) / scale
        ly = (py - y_offset) / scale
        
        return (lx, ly)

input_handler = InputHandler()
