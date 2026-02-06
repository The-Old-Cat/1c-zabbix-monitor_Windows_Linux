import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional
import glob
import time


def _get_log_location_from_cfg(target_keyword: str = "Query1c") -> Optional[str]:
    """
    Автоматически находит logcfg.xml и извлекает путь к логам медленных запросов.
    """
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

        # В вашем XML используется пространство имен xmlns:query
        # Ищем любые теги log (с учетом namespace или без), где location содержит Query1c
        for log_tag in root.findall(".//{*}log"):
            location = log_tag.get("location")
            if location and target_keyword.lower() in location.lower():
                return location
    except Exception:
        return None
    return None


def get_metric(config: Dict[str, Any]) -> int:
    """
    Подсчитывает количество медленных SQL-запросов (SDBL/DBMSSQL).
    """
    # 1. Автоматический поиск пути (G:\1c_log\Query1c из вашего XML)
    auto_path = _get_log_location_from_cfg("Query1c")

    # 2. Резервный путь из конфига
    sql_path = auto_path or config.get("logs", {}).get("sql", {}).get("path")

    if not sql_path or not os.path.exists(sql_path):
        return 0

    total_slow_queries = 0
    try:
        # 1С пишет логи запросов в корень указанной папки или подпапки rphost_*
        # Проверяем оба варианта
        search_patterns = [
            os.path.join(sql_path, "*.log"),
            os.path.join(sql_path, "rphost_*", "*.log"),
        ]

        log_files = []
        for pattern in search_patterns:
            log_files.extend(glob.glob(pattern))

        # Берем только свежие файлы (за последние 5 минут)
        now = time.time()
        recent_files = [f for f in log_files if now - os.path.getmtime(f) < 300]

        for file_path in recent_files:
            total_slow_queries += _count_events_in_file(Path(file_path))

        return total_slow_queries
    except Exception:
        return 0


def _count_events_in_file(log_file: Path) -> int:
    """Считает количество событий SDBL и DBMSSQL в последних строках."""
    count = 0
    # События, которые вы фильтруете в logcfg.xml
    target_events = {"SDBL", "DBMSSQL"}

    try:
        with log_file.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            # Нас интересуют последние записи
            for line in lines[-200:]:
                parts = line.split(",")
                if len(parts) > 1:
                    # Извлекаем имя события из второй части строки (время-длительность,Событие)
                    event_info = parts[1].split("-")
                    event_name = event_info[-1].upper() if event_info else ""

                    if event_name in target_events:
                        count += 1
        return count
    except Exception:
        return 0
