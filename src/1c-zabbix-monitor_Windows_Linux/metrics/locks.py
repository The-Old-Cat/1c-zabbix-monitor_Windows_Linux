import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional
import glob


def _get_log_location_from_cfg(target_keyword: str = "locks") -> Optional[str]:
    """
    Автоматически находит logcfg.xml и извлекает путь к логам по ключевому слову в location.
    """
    # Стандартные пути расположения logcfg.xml для Windows
    search_paths = [
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "1cv8/conf/logcfg.xml",
        Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
        / "1cv8/conf/logcfg.xml",
        Path.cwd() / "logcfg.xml",
    ]

    cfg_path = next((p for p in search_paths if p.exists()), None)
    if not cfg_path:
        return None

    try:
        tree = ET.parse(cfg_path)
        root = tree.getroot()
        # Ищем тег <log> у которого атрибут location содержит искомое слово (например, 'locks')
        for log_tag in root.findall(".//{*}log"):
            location = log_tag.get("location")
            if location and target_keyword.lower() in location.lower():
                return location
    except Exception:
        return None
    return None


def get_metric(config: Dict[str, Any]) -> int:
    """
    Подсчитывает количество новых событий блокировок, используя пути из logcfg.xml.
    """
    # 1. Пытаемся найти путь автоматически из ТЖ
    auto_path = _get_log_location_from_cfg("locks")

    # 2. Если автомат не нашел, пробуем взять из конфига (для гибкости)
    locks_path = auto_path or config.get("logs", {}).get("locks", {}).get("path")

    if not locks_path or not os.path.exists(locks_path):
        return 0

    lock_count = 0
    try:
        # Ищем все .log файлы в подпапках rphost_* (стандарт 1С)
        # Пример: G:\1c_log\zabbix\locks\rphost_*\*.log
        search_pattern = os.path.join(locks_path, "rphost_*", "*.log")
        log_files = glob.glob(search_pattern)

        # Берем файлы, измененные за последние 5 минут (чтобы не парсить старье)
        import time

        now = time.time()
        recent_files = [f for f in log_files if now - os.path.getmtime(f) < 300]

        for file_path in recent_files:
            lock_count += _count_locks_in_file(Path(file_path))

        return lock_count
    except Exception:
        return 0


def _count_locks_in_file(log_file: Path) -> int:
    """Подсчитывает количество событий TLOCK/TTIMEOUT/TDEADLOCK в файле."""
    count = 0
    # Ключевые события из вашего logcfg.xml
    target_events = {"TLOCK", "TTIMEOUT", "TDEADLOCK"}

    try:
        with log_file.open("r", encoding="utf-8", errors="ignore") as f:
            # Читаем только последние 100 строк, так как нас интересует оперативная статистика
            content = f.readlines()
            for line in content[-100:]:
                # Формат ТЖ: MM:SS.uuuuuu-Duration,EventName,...
                parts = line.split(",")
                if len(parts) > 1:
                    event_part = parts[1].split("-")
                    event_name = event_part[-1] if event_part else ""
                    if event_name.upper() in target_events:
                        count += 1
        return count
    except Exception:
        return 0
