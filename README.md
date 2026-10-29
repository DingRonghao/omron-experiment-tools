# omron-experiment-tools

用于在 Windows 上双击启动现有 Jupyter Notebook 环境的小工具。

## 环境要求

- Windows，已有 `%USERPROFILE%\Experiment` 目录。
- 已有虚拟环境，Python 位于 `%USERPROFILE%\Experiment\.venv\Scripts\python.exe`。
- 该虚拟环境已安装并能够运行 `notebook`。

## 使用方法

1. 下载 `Start_Jupyter.bat`（无需登录 GitHub），确认文件扩展名为 `.bat`，而不是 `.bat.txt`。
2. 将脚本保存在任意方便的位置，双击运行。
3. 脚本在 `%USERPROFILE%\Experiment` 中启动 Jupyter Notebook，通常会自动打开浏览器；若未打开，可使用终端显示的本地 URL。
4. 使用期间保留终端窗口，结束时按 `Ctrl+C` 并按提示关闭服务。

脚本检查目录、Python 解释器和 Notebook 模块；检查或启动失败会显示错误并暂停。脚本不会安装软件、激活环境或修改系统配置。Jupyter 正常运行可能生成自身的运行时文件。此仓库不包含实验数据或内部资料。
