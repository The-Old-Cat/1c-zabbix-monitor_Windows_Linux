import subprocess
import os
import re
from pathlib import Path
from typing import Dict, Any, List


def _find_rac_executable(config: Dict[str, Any]) -> str:
    """Находит актуальный rac.exe (логика идентична другим модулям)."""
    config_path = config.get("rac", {}).get("path")
    if config_path and os.path.exists(config_path):
        return config_path

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
    return "rac"


def _get_clusters(rac_path: str, ras_address: str, user: str = None, password: str = None) -> List[str]:
    """Получает список всех кластеров на сервере."""
    try:
        # Пробуем разные варианты синтаксиса аутентификации
        cmd = [rac_path, "cluster", "list"]
        
        # Если указаны учетные данные, добавляем их
        if user and password:
            # Пробуем разные возможные форматы аутентификации
            auth_options = [
                ["--cluster-user", user, "--cluster-pwd", password],  # Формат для некоторых версий 1С
                ["--user", user, "--password", password],              # Альтернативный формат
            ]
            
            # Пробуем каждый вариант аутентификации
            for auth_option in auth_options:
                cmd_with_auth = cmd + auth_option + [ras_address]
                try:
                    result = subprocess.run(cmd_with_auth, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        # Успешно подключились с этими параметрами
                        return re.findall(r"cluster\s+:\s+([a-f0-9-]+)", result.stdout)
                except:
                    continue
            
            # Если ни один из вариантов не сработал, пробуем без аутентификации
            cmd.append(ras_address)
        else:
            cmd.append(ras_address)
        
        # Если не указаны учетные данные или не удалось подключиться с ними
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return re.findall(r"cluster\s+:\s+([a-f0-9-]+)", result.stdout)
    except:
        return []


def get_metric(config: Dict[str, Any]) -> int:
    """
    Считает общее количество активных сессий во всех кластерах сервера.
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

    clusters = _get_clusters(rac_path, ras_address, user, password)
    if not clusters:
        return 0

    total_sessions = 0
    try:
        for cluster_id in clusters:
            # Вызываем список сессий для конкретного кластера
            # Команда: rac session list --cluster=<ID> <адрес>
            cmd = [rac_path, "session", "list"]
            
            # Пробуем разные варианты аутентификации для session list
            if user and password:
                auth_options = [
                    ["--cluster-user", user, "--cluster-pwd", password],
                    ["--user", user, "--password", password],
                ]
                
                success = False
                for auth_option in auth_options:
                    cmd_with_auth = cmd + auth_option + [f"--cluster={cluster_id}", ras_address]
                    try:
                        result = subprocess.run(
                            cmd_with_auth,
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        if result.returncode == 0:
                            # Успешно получили сессии с этими параметрами
                            sessions = re.findall(r"session\s+:\s+[a-f0-9-]+", result.stdout)
                            total_sessions += len(sessions)
                            success = True
                            break
                    except:
                        continue
                
                if not success:
                    # Если не удалось с аутентификацией, пробуем без
                    cmd.extend([f"--cluster={cluster_id}", ras_address])
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    sessions = re.findall(r"session\s+:\s+[a-f0-9-]+", result.stdout)
                    total_sessions += len(sessions)
            else:
                # Без аутентификации
                cmd.extend([f"--cluster={cluster_id}", ras_address])
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                sessions = re.findall(r"session\s+:\s+[a-f0-9-]+", result.stdout)
                total_sessions += len(sessions)

    except subprocess.TimeoutExpired:
        # Если RAC завис, возвращаем 0, чтобы не блокировать агент Zabbix
        return 0
    except Exception:
        return 0

    return total_sessions
