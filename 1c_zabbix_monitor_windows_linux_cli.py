"""
Точка входа для CLI-скрипта 1c-zabbix-monitor
"""

import importlib.util
import sys
from pathlib import Path

def main():
    # Получаем путь к директории проекта
    project_root = Path(__file__).parent
    src_path = project_root / "src"
    sys.path.insert(0, str(src_path))
    
    # Путь к основному модулю
    main_module_path = src_path / "1c-zabbix-monitor_Windows_Linux" / "main.py"
    
    # Загружаем модуль динамически
    spec = importlib.util.spec_from_file_location("main_module", main_module_path)
    main_module = importlib.util.module_from_spec(spec)
    
    if spec.loader is not None:
        spec.loader.exec_module(main_module)
        # Вызываем main функцию из загруженного модуля
        return main_module.main()
    else:
        print("Ошибка: Не удалось загрузить модуль main")
        return 1

if __name__ == "__main__":
    sys.exit(main())