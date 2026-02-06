import os
import glob
import re
from datetime import datetime, timedelta
from .utils_1c import get_log_location_from_cfg


def get_latest_log_files(base_path, hours=1):
    """Получает все лог-файлы за последние N часов"""
    all_files = []
    
    # Ищем файлы во всех подкаталогах
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if file.endswith('.log'):
                file_path = os.path.join(root, file)
                # Проверяем, что файл изменялся за последние N часов
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if datetime.now() - file_time <= timedelta(hours=hours):
                    all_files.append(file_path)
    
    # Сортируем по времени модификации (новые первыми)
    all_files.sort(key=os.path.getmtime, reverse=True)
    return all_files


def get_metric(config):
    # 1. Пытаемся получить путь АВТОМАТИЧЕСКИ из logcfg.xml
    # Ищем секцию, где в пути есть 'excps' (как в вашем конфиге)
    auto_path = get_log_location_from_cfg(target_subfolder="excps")

    # 2. Если автомат не сработал, берем из config.yaml
    log_base_path = auto_path or config.get("logs", {}).get("zabbix_excps", {}).get("path")

    if not log_base_path or not os.path.exists(log_base_path):
        return {"error": "Log path not found (check logcfg.xml location or config.yaml)"}

    # Получаем последние лог-файлы за последние 2 часа
    log_files = get_latest_log_files(log_base_path, hours=2)
    
    if not log_files:
        return {"count": 0, "last_error": None}

    errors_found = []
    recent_errors_count = 0
    
    # Читаем последние файлы (ограничимся 10 файлами для производительности)
    for log_file in log_files[:10]:
        try:
            with open(log_file, "r", encoding="utf-8-sig", errors="ignore") as f:
                lines = f.readlines()
                
                # Ищем строки с ошибками (обычно содержат EXCP, ERROR, FATAL и т.д.)
                for line in lines:
                    if re.search(r'(EXCP|ERROR|FATAL|EXCPCNTX)', line, re.IGNORECASE):
                        recent_errors_count += 1
                        # Удаляем потенциальные проблемные символы из строки
                        clean_line = line.strip().encode('utf-8', errors='ignore').decode('utf-8')
                        errors_found.append({
                            "file": os.path.basename(log_file),
                            "line": clean_line,
                            "timestamp": os.path.getmtime(log_file)
                        })
                        
        except Exception as e:
            continue  # Пропускаем файлы, которые не удается прочитать

    # Возвращаем структурированную информацию об ошибках
    result = {
        "count": recent_errors_count,
        "errors_last_2_hours": recent_errors_count
    }
    
    if errors_found:
        # Сортируем ошибки по времени (новые первыми)
        errors_found.sort(key=lambda x: x["timestamp"], reverse=True)
        last_error = errors_found[0]
        result["last_error"] = {
            "file": last_error["file"],
            "message": last_error["line"]
        }
        # Возвращаем также последние 5 ошибок для детального анализа
        result["recent_errors"] = [
            {"file": err["file"], "message": err["line"]} 
            for err in errors_found[:5]
        ]
    
    return result
