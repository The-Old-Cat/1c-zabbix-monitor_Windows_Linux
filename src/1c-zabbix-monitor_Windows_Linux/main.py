from __future__ import annotations

import argparse
import json
import os
import sys
import time
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Union, Callable

from loguru import logger

import importlib.util

# ============================================================================
# Исправление путей поиска (Решает проблему "Не удается разрешить импорт")
# ============================================================================
current_file_path = Path(__file__).resolve()
project_root = current_file_path.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Попытка загрузки расширений
try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Теперь импорт из локальной папки metrics будет работать корректно
try:
    # Используем importlib.util для явного указания пути к модулю
    utils_1c_spec = importlib.util.spec_from_file_location(
        "utils_1c", 
        project_root / "metrics" / "utils_1c.py"
    )
    if utils_1c_spec is not None and utils_1c_spec.loader is not None:
        utils_1c_module = importlib.util.module_from_spec(utils_1c_spec)
        utils_1c_spec.loader.exec_module(utils_1c_module)
        get_rac_path = utils_1c_module.get_rac_path
    else:
        # Резервный вариант, если спецификация модуля некорректна
        def get_rac_path(config: Dict[str, Any]) -> str:
            return config.get("ras", {}).get("path", "rac")
except (ImportError, AttributeError, FileNotFoundError, TypeError):
    # Резервный вариант, если модуль еще не готов или пути не настроены
    def get_rac_path(config: Dict[str, Any]) -> str:
        return config.get("ras", {}).get("path", "rac")

# ============================================================================
# Кэширование
# ============================================================================

class FileTTLCache:
    """Атомарный кэш в файловой системе для сохранения данных между вызовами Zabbix."""
    def __init__(self, ttl: int = 60):
        self.ttl = ttl
        # Исправлено: корректное получение TEMP без синтаксических ошибок
        if os.name == "nt":
            # Ищем системную папку TEMP или используем стандартный путь
            temp_base = os.environ.get("TEMP") or os.environ.get("TMP") or "C:/Windows/Temp"
        else:
            temp_base = "/tmp"
            
        self.cache_dir = Path(temp_base) / "1c_zabbix_monitor_cache"
        
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError) as e:
            logger.error(f"Ошибка создания директории кэша: {e}")

    def _get_cache_file(self, key: str) -> Path:
        safe_key = re.sub(r"[^\w\-_]", "_", key)
        return self.cache_dir / f"{safe_key}.json"

    def get(self, key: str) -> Optional[Any]:
        cache_file = self._get_cache_file(key)
        if not cache_file.exists():
            return None
        
        if (time.time() - cache_file.stat().st_mtime) > self.ttl:
            return None
            
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return None

    def set(self, key: str, value: Any) -> None:
        """Безопасная запись через временный файл (атомарно)."""
        cache_file = self._get_cache_file(key)
        try:
            with tempfile.NamedTemporaryFile('w', delete=False, dir=self.cache_dir, encoding='utf-8') as tf:
                json.dump(value, tf, ensure_ascii=False)
                temp_name = tf.name
            Path(temp_name).replace(cache_file)
        except (IOError, OSError, PermissionError) as e:
            logger.error(f"Ошибка записи в кэш {key}: {e}")

# ============================================================================
# Конфигурация
# ============================================================================

def _replace_env_vars(config: Any) -> Any:
    """Заменяет ${VAR:default} значениями из окружения."""
    if isinstance(config, dict):
        return {k: _replace_env_vars(v) for k, v in config.items()}
    elif isinstance(config, list):
        return [_replace_env_vars(i) for i in config]
    elif isinstance(config, str):
        pattern = r"\$\{([^}]+)\}"
        result = config
        for match in re.findall(pattern, config):
            parts = match.split(":", 1)
            var_name = parts[0].strip()
            default = parts[1].strip() if len(parts) > 1 else ""
            env_val = os.environ.get(var_name, default).strip('"').strip("'")
            result = result.replace(f"${{{match}}}", env_val)
        return result
    return config

def load_full_config(config_path: Optional[str]) -> Dict[str, Any]:
    if HAS_DOTENV:
        load_dotenv()

    candidates = []
    if config_path:
        candidates.append(Path(config_path))
    else:
        cwd = Path.cwd()
        candidates.extend([cwd / "config.yaml", cwd / "config.json"])
        if os.name == "nt":
            prog_data = os.environ.get("PROGRAMDATA", "C:/ProgramData")
            candidates.append(Path(prog_data) / "1c-monitor/config.yaml")

    final_config: Dict[str, Any] = {}
    for p in candidates:
        if p.is_file():
            try:
                content = p.read_text(encoding="utf-8")
                if p.suffix in (".yaml", ".yml") and HAS_YAML:
                    final_config = yaml.safe_load(content) or {}
                else:
                    final_config = json.loads(content)
                break
            except (IOError, OSError, yaml.YAMLError, json.JSONDecodeError) as e:
                logger.error(f"Ошибка чтения конфигурации {p}: {e}")

    return _replace_env_vars(final_config)

# ============================================================================
# Основная логика
# ============================================================================

def safe_import_metric(module_name: str) -> Optional[Callable]:
    """Динамический импорт функции get_metric из папки metrics."""
    try:
        import importlib
        # Загружаем модуль относительно корня проекта
        module = importlib.import_module(f"metrics.{module_name}")
        return getattr(module, "get_metric")
    except (ImportError, AttributeError) as e:
        logger.error(f"Модуль метрики '{module_name}' недоступен: {e}")
        return None

def main() -> int:
    parser = argparse.ArgumentParser(description="1C Zabbix Monitor CLI")
    parser.add_argument("--metric", required=True, 
                        choices=["sessions", "rphost", "ras_health", "log_errors", "locks", "calls", "slow_sql", "sql_queries"])
    parser.add_argument("--format", choices=["plain", "json", "lld"], default="plain")
    parser.add_argument("--config", help="Путь к config.yaml")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    # Логирование
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if args.debug else "ERROR")

    # 1. Загрузка настроек
    config = load_full_config(args.config)

    # 2. Определение пути к RAC (автопоиск через utils_1c)
    if "ras" not in config: config["ras"] = {}
    config["ras"]["path"] = get_rac_path(config)

    # 3. Кэширование
    ttl = int(config.get("cache", {}).get("ttl", 60))
    cache = FileTTLCache(ttl=ttl) if not args.no_cache else None
    cache_key = f"{args.metric}_{args.format}"

    if cache:
        cached_val = cache.get(cache_key)
        if cached_val is not None:
            output = cached_val if args.format == "plain" else json.dumps(cached_val, ensure_ascii=False)
            print(output)
            return 0

    # 4. Сбор данных
    get_metric_func = safe_import_metric(args.metric)
    if get_metric_func is None:
        print("0")
        return 1

    try:
        if args.metric == "rphost":
            result = get_metric_func(config, args.format)
        else:
            result = get_metric_func(config)

        if cache:
            cache.set(cache_key, result)

        print(json.dumps(result, ensure_ascii=False) if args.format in ["json", "lld"] else result)

    except (RuntimeError, ValueError, KeyError, TypeError) as e:
        logger.exception(f"Ошибка в метрике {args.metric}: {e}")
        print("0")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())