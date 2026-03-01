# 游戏打包指南

本文档介绍如何将《杀戮星光》打包成可执行的 `.exe` 文件，以便发送给其他玩家。

## 1. 准备工作

打包需要使用 `PyInstaller` 工具。请确保您已经安装了 Python。

打开终端（命令行），运行以下命令安装 PyInstaller：

```bash
pip install pyinstaller
```

## 2. 使用自动脚本打包 (推荐)

项目根目录下已经准备好了一个打包脚本 `build_exe.py`。

1.  在项目根目录下打开终端。
2.  运行脚本：
    ```bash
    python build_exe.py
    ```
3.  等待脚本执行完毕。

## 3. 获取打包结果

打包完成后，您会在项目根目录下看到一个 `dist` 文件夹。

*   打开 `dist` 文件夹。
*   您会看到一个名为 `SlayTheStarlight.exe` 的文件。
*   **这就是您可以发送给其他玩家的游戏文件。**

由于我们使用了单文件打包 (`--onefile`)，所有的资源文件（图片、音频、配置）都已经包含在这个 EXE 文件中，玩家不需要安装 Python 或其他依赖即可直接运行。

## 4. 常见问题

*   **打包后的游戏运行闪退**：
    *   请尝试在终端中运行生成的 exe 文件，查看是否有报错信息。
    *   确保 `assets` 和 `data` 文件夹存在且内容完整。
*   **被杀毒软件误报**：
    *   PyInstaller 打包的程序有时会被某些杀毒软件误报为病毒。这是正常现象（因为它是自解压程序）。您可以将其添加到信任列表。

## 5. 手动打包命令

如果您想手动运行 PyInstaller，可以使用以下命令：

```bash
pyinstaller main.py --name=SlayTheStarlight --onefile --noconsole --add-data "assets;assets" --add-data "data;data" --clean
```

(注意：在 macOS 或 Linux 上，请将分号 `;` 替换为冒号 `:`)
