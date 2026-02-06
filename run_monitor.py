#!/usr/bin/env python3
"""
Скрипт запуска для 1c-zabbix-monitor_Windows_Linux
"""

import sys
import importlib.util
from pathlib import Path

# Добавляем путь к src в sys.path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Получаем путь к main.py
main_path = src_path / "1c-zabbix-monitor_Windows_Linux" / "main.py"

# Загружаем модуль динамически
spec = importlib.util.spec_from_file_location("main_module", main_path)
main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_module)

if __name__ == "__main__":
    main_module.main()