import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional
import glob
import time


def _get_log_location_from_cfg(target_keyword: str = "calls") -> Optional[str]:
    """
    Автоматически находит logcfg.xml и извлекает путь к логам по ключевому слову в location.

    """
    # Стандартные пути для Windows (согласно предоставленной архитектуре)
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
        # Ищем тег <log>, где атрибут location содержит 'calls' (как в вашем logcfg.xml)
        #
        for log_tag in root.findall(".//{*}log"):
            location = log_tag.get("location")
            if location and target_keyword.lower() in location.lower():
                return location
    except Exception:
        return None
    return None


def get_metric(config: Dict[str, Any]) -> int:
    """
    Подсчитывает количество серверных вызовов, используя пути из logcfg.xml.
    """
    # 1. Автоматический поиск пути из ТЖ (секция ZABBIX — CALLS)
    #
    auto_path = _get_log_location_from_cfg("calls")

    # 2. Резервный вариант из config.yaml
    calls_path = auto_path or config.get("logs", {}).get("calls", {}).get("path")

    if not calls_path or not os.path.exists(calls_path):
        return 0

    call_count = 0
    try:
        # Ищем .log файлы в подпапках rphost_*
        search_pattern = os.path.join(calls_path, "rphost_*", "*.log")
        log_files = glob.glob(search_pattern)

        # Анализируем файлы, измененные за последние 5 минут для актуальности данных
        now = time.time()
        recent_files = [f for f in log_files if now - os.path.getmtime(f) < 300]

        for file_path in recent_files:
            call_count += _count_calls_in_file(Path(file_path))

        return call_count
    except Exception:
        return 0


def _count_calls_in_file(log_file: Path) -> int:
    """Подсчитывает количество событий CALL в последних строках файла."""
    count = 0
    try:
        with log_file.open("r", encoding="utf-8", errors="ignore") as f:
            # Читаем последние 200 строк для оперативной сводки
            lines = f.readlines()
            recent_lines = lines[-200:] if len(lines) > 200 else lines

            for line in recent_lines:
                # В ТЖ формат: время-длительность,ИмяСобытия,...
                # Мы ищем событие CALL (регистронезависимо, как в вашем XML)
                #
                parts = line.split(",")
                if len(parts) > 1:
                    event_info = parts[1].split("-")
                    if event_info and event_info[-1].upper() == "CALL":
                        count += 1
        return count
    except Exception:
        return 0
