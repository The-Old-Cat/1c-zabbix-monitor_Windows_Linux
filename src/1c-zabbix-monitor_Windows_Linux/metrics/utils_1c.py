import os
import platform
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


def get_rac_path(config: Dict[str, Any]) -> str:
    """
    Кроссплатформенный поиск пути к RAC.
    """
    # 1. Проверяем путь из конфига (подтянутый из .env)
    cfg_path = config.get("ras", {}).get("path")
    if cfg_path and Path(cfg_path).exists():
        return str(cfg_path)

    # 2. Проверяем системный PATH
    system_rac = shutil.which("rac.exe" if os.name == "nt" else "rac")
    if system_rac:
        return system_rac

    # 3. Автопоиск в стандартных путях Windows
    if os.name == "nt":
        base_path = Path("C:/Program Files/1cv8")
        if base_path.exists():
            # Находим все rac.exe и выбираем версию по самой свежей дате изменения
            rac_files = list(base_path.glob("**/bin/rac.exe"))
            if rac_files:
                latest_rac = max(rac_files, key=lambda p: p.stat().st_mtime)
                return str(latest_rac)

    # 4. Автопоиск в Linux
    else:
        opt_path = Path("/opt/1cv8")
        if opt_path.exists():
            rac_files = list(opt_path.glob("**/rac"))
            if rac_files:
                latest_rac = max(rac_files, key=lambda p: p.stat().st_mtime)
                return str(latest_rac)

    return "rac"


def get_log_location_from_cfg(target_subfolder: str = "zabbix") -> Optional[str]:
    """
    Автоматически находит logcfg.xml и извлекает путь к логам.
    """
    # Стандартные пути для Windows и Linux
    search_paths = [
        Path.cwd() / "logcfg.xml",
        Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "1cv8/conf/logcfg.xml",
        Path("/opt/1cv8/conf/logcfg.xml"),
    ]

    cfg_path = next((p for p in search_paths if p.exists()), None)

    if not cfg_path:
        logger.warning("Файл logcfg.xml не найден автоматически.")
        return None

    try:
        tree = ET.parse(cfg_path)
        root = tree.getroot()

        # Поиск через namespaces (используем {*} для игнорирования префиксов типа query:)
        for log_tag in root.findall(".//{*}log"):
            location = log_tag.get("location")
            if location and target_subfolder.lower() in location.lower():
                logger.debug(f"Найден путь в logcfg.xml: {location}")
                return location

    except Exception as e:
        logger.error(f"Ошибка парсинга logcfg.xml ({cfg_path}): {e}")

    return None
