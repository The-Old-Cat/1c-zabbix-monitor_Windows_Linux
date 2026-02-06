import subprocess
import os
from pathlib import Path
from typing import Dict, Any


def _find_rac_executable(config: Dict[str, Any]) -> str:
    """
    Пытается найти путь к исполняемому файлу rac.exe / rac.
    """
    # 1. Проверяем конфиг
    config_path = config.get("rac", {}).get("path")
    if config_path and os.path.exists(config_path):
        return config_path

    # 2. Ищем в Program Files на основе стандартных путей 1С
    # (можно доработать поиск на основе установленных версий)
    prog_files = os.environ.get("ProgramFiles", "C:/Program Files")
    common_1c_path = Path(prog_files) / "1cv8"

    if common_1c_path.exists():
        # Сначала ищем все доступные версии rac.exe
        rac_files = list(common_1c_path.glob("**/bin/rac.exe"))
        if rac_files:
            # Если в конфиге указаны предпочтительные версии, используем их
            preferred_version = config.get("ras", {}).get("preferred_version")
            if preferred_version:
                for rac_file in rac_files:
                    if preferred_version in str(rac_file):
                        return str(rac_file)
            
            # В противном случае, пробуем использовать последнюю версию
            return str(max(rac_files, key=lambda p: p.stat().st_mtime))

    return "rac"  # Надеемся, что rac в PATH


def get_metric(config: Dict[str, Any]) -> int:
    """
    Проверяет доступность RAS, запрашивая список кластеров.

    Returns:
        1 - RAS доступен и отвечает
        0 - RAS недоступен или ошибка подключения
    """
    rac_path = _find_rac_executable(config)
    
    # Формируем ras_address из host и port из конфигурации
    ras_config = config.get("ras", {})
    host = ras_config.get("host", "localhost")
    port = ras_config.get("port", 1545)
    ras_address = f"{host}:{port}"
    
    # Получаем учетные данные
    user = ras_config.get("user", "admin")
    password = ras_config.get("password")

    try:
        # Выполняем команду: rac cluster list localhost:1545
        # timeout ограничивает ожидание, если RAS "завис"
        cmd = [rac_path, "cluster", "list"]
        
        # Пробуем разные варианты аутентификации
        if user and password:
            auth_options = [
                ["--cluster-user", user, "--cluster-pwd", password],
                ["--user", user, "--password", password],
            ]
            
            # Пробуем каждый вариант аутентификации
            for auth_option in auth_options:
                cmd_with_auth = cmd + auth_option + [ras_address]
                try:
                    result = subprocess.run(
                        cmd_with_auth,
                        capture_output=True,
                        text=True,
                        timeout=5,
                        check=False,
                    )
                    
                    # Если код возврата 0 — RAS здоров
                    if result.returncode == 0:
                        return 1
                except:
                    continue
        
        # Если аутентификация не сработала или не указана, пробуем без нее
        cmd.append(ras_address)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

        # Если код возврата 0 — RAS здоров
        if result.returncode == 0:
            return 1

        return 0

    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        # Если rac.exe не найден или время вышло — RAS считаем мертвым
        return 0
