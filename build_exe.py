import PyInstaller.__main__
import os
import sys

def build():
    # 确定路径分隔符 (Windows用';', Linux/Mac用':')
    sep = os.pathsep

    # 定义要包含的资源文件夹
    # 格式: "源路径;目标路径"
    # 注意：在 Windows 上，路径分隔符是 ';', 在 Unix 上是 ':'
    add_data_assets = f"assets{sep}assets"
    add_data_data = f"data{sep}data"

    print("开始打包游戏...")
    
    PyInstaller.__main__.run([
        'main.py',                       # 主程序文件
        '--name=SlayTheStarlight',       # 生成的 EXE 名称
        '--onefile',                     # 打包成单个文件
        '--noconsole',                   # 不显示控制台窗口 (游戏运行时)
        f'--add-data={add_data_assets}', # 添加 assets 文件夹
        f'--add-data={add_data_data}',   # 添加 data 文件夹
        '--clean',                       # 清理临时文件
        # '--icon=assets/images/icons/user.png', # 如果有图标可以取消注释
    ])
    
    print("打包完成！请查看 dist 文件夹。")

if __name__ == "__main__":
    # 检查是否安装了 PyInstaller
    try:
        import PyInstaller
        build()
    except ImportError:
        print("错误: 未找到 PyInstaller。")
        print("请先运行以下命令安装:")
        print("pip install pyinstaller")
        input("按回车键退出...")
