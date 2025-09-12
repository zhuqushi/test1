# __init__.py 代码（保持不变，但需确保 main.py 在同一目录）
if __name__ == '__main__':
    from .main import main  # 显式导入，避免路径问题
    main().main_loop()
