# 1C:Enterprise Monitoring Tool for Zabbix

Кроссплатформенное решение (Windows/Linux) для бережного мониторинга кластера 1С:Предприятие с использованием **Python**, **Zabbix** и менеджера пакетов **uv**.

## 🚀 Основная концепция

Минимизация нагрузки на кластер 1С. В отличие от стандартных методов, данный инструмент:

1. **Кэширует ответы RAC**: запросы к кластеру выполняются не чаще одного раза в минуту.
2. **Парсит логи «с хвоста»**: чтение только последних записей журналов без нагрузки на диск.
3. **Единый код**: работает одинаково на Windows и Linux.

---

## 🛠 Технологический стек

* **Language:** Python 3.12+
* **Package Manager:** [uv](https://github.com/astral-sh/uv) (fastest Python bundler)
* **Monitoring:** Zabbix 6.0+ (Agent/Agent2)
* **1C Tools:** RAC (Remote Administration Client)

---

## 📋 Возможности

* **RAC Monitoring:** статус кластера, количество сеансов, рабочие процессы (rphost).
* **Log Analysis:** мониторинг критических ошибок (ERROR, FATAL, EXCP), блокировок (TLOCK, TTIMEOUT, TDEADLOCK), вызовов (CALL), медленных SQL-запросов (SDBL, DBMSSQL) в технологическом журнале 1С и системных логах (EventLog/journald).
* **Health Check:** проверка доступности службы RAS.
* **Smart Cache:** предотвращение "шторма запросов" к менеджеру кластера.

---

## 📦 Быстрый старт (Deployment)

### 1. Подготовка окружения

Установите `uv`, если он еще не установлен:

#### Windows (PowerShell)
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### Linux/macOS
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Установка проекта

Склонируйте репозиторий и синхронизируйте зависимости:

```bash
git clone https://github.com/your-repo/1c-zabbix-monitor.git
cd 1c-zabbix-monitor
uv sync
```

### 3. Настройка

#### С использованием .env файла (рекомендуется)

1. Создайте файл `.env` в корне проекта на основе примера `.env.example`:

```bash
cp .env.example .env
```

2. Отредактируйте файл `.env`, указав свои значения:

```bash
# --- Параметры подключения к 1С ---
RAC_HOST=localhost
RAC_PORT=1545
RAC_USER=your_username
RAC_PASSWORD=your_password

# --- Кэширование (секунды) ---
CACHE_TTL=60

# --- Пути ---
# Пути к техлогам 1С (Windows формат)
LOG_PATH_SQL_WINDOWS="/path/to/1c/logs/Query1c"
LOG_PATH_LOCKS_WINDOWS="/path/to/1c/logs/locks"
LOG_PATH_CALLS_WINDOWS="/path/to/1c/logs/calls"
LOG_PATH_ERRORS_WINDOWS="/path/to/1c/logs/srv"

# Пути к техлогам 1С (Linux формат)
LOG_PATH_SQL_LINUX="/var/log/1c/Query1c"
LOG_PATH_LOCKS_LINUX="/var/log/1c/locks"
LOG_PATH_CALLS_LINUX="/var/log/1c/calls"
LOG_PATH_ERRORS_LINUX="/var/log/1c/srv"

# Путь к RAC (Windows)
RAC_PATH_WINDOWS="/path/to/1cv8/x.x.x.x/bin/rac.exe"
# Путь к RAC (Linux)
RAC_PATH_LINUX="/opt/1cv8/x86_64/rac"

# --- Параметры мониторинга ---
SESSION_THRESHOLD=100

# --- Zabbix Server (для push-модели через zabbix_sender) ---
ZABBIX_SERVER=zabbix.example.com
ZABBIX_PORT=10051

# --- Режим платформы ---
PLATFORM=auto # auto, windows, linux
```

3. Убедитесь, что в `config.yaml` используются переменные окружения:

```yaml
# 1c-zabbix-monitor Configuration
# Приоритет: Environment Variables > Default values

# Путь к RAC будет выбран автоматически в Python коде на основе текущей ОС
# Windows
rac_path: "${RAC_PATH_WINDOWS:/path/to/1cv8/common/rac.exe}"
# Linux
# rac_path: "${RAC_PATH_LINUX:/opt/1cv8/x86_64/rac}"

rac:
  host: "${RAC_HOST:localhost}"
  port: ${RAC_PORT:1545}
  user: "${RAC_USER:admin}"
  password: "${RAC_PASSWORD}"

cache:
  ttl: ${CACHE_TTL:60}

# Пути к технологическим журналам 1С (кроссплатформенные)
logs:
  # Основной лог сервера
  main:
    # Windows
    path: "${MAIN_LOG_PATH_WINDOWS:/path/to/1c/logs/srv}"
    # Linux
    # path: "${MAIN_LOG_PATH_LINUX:/var/log/1c/srv}"
    history: ${MAIN_LOG_HISTORY:24}                 # История хранения (в часах)

  # Лог вызовов
  calls:
    # Windows
    path: "${CALL_LOG_PATH_WINDOWS:/path/to/1c/logs/CALL}"
    # Linux
    # path: "${CALL_LOG_PATH_LINUX:/var/log/1c/CALL}"
    history: ${CALL_LOG_HISTORY:10}                  # История хранения (в часах)

  # Лог блокировок
  locks:
    # Windows
    path: "${LOCKS_LOG_PATH_WINDOWS:/path/to/1c/logs/LOCKS}"
    # Linux
    # path: "${LOCKS_LOG_PATH_LINUX:/var/log/1c/LOCKS}"
    history: ${LOCKS_LOG_HISTORY:24}                   # История хранения (в часах)

  # Лог блокировок > 0.5 секунды
  locks_05sec:
    # Windows
    path: "${LOCKS_05SEC_LOG_PATH_WINDOWS:/path/to/1c/logs/LOCKS_05sec}"
    # Linux
    # path: "${LOCKS_05SEC_LOG_PATH_LINUX:/var/log/1c/LOCKS_05sec}"
    history: ${LOCKS_05SEC_LOG_HISTORY:24}                         # История хранения (в часах)

  # Zabbix - вызовы
  zabbix_calls:
    # Windows
    path: "${ZABBIX_CALLS_LOG_PATH_WINDOWS:/path/to/1c/logs/zabbix/calls}"
    # Linux
    # path: "${ZABBIX_CALLS_LOG_PATH_LINUX:/var/log/1c/zabbix/calls}"
    history: ${ZABBIX_CALLS_LOG_HISTORY:1}                           # История хранения (в часах)

  # Zabbix - блокировки
  zabbix_locks:
    # Windows
    path: "${ZABBIX_LOCKS_LOG_PATH_WINDOWS:/path/to/1c/logs/zabbix/locks}"
    # Linux
    # path: "${ZABBIX_LOCKS_LOG_PATH_LINUX:/var/log/1c/zabbix/locks}"
    history: ${ZABBIX_LOCKS_LOG_HISTORY:1}                           # История хранения (в часах)

  # Zabbix - исключения
  zabbix_excps:
    # Windows
    path: "${ZABBIX_EXCPS_LOG_PATH_WINDOWS:/path/to/1c/logs/zabbix/excps}"
    # Linux
    # path: "${ZABBIX_EXCPS_LOG_PATH_LINUX:/var/log/1c/zabbix/excps}"
    history: ${ZABBIX_EXCPS_LOG_HISTORY:1}                           # История хранения (в часах)

  # SQL запросы > 80ms
  sql:
    # Windows
    path: "${SQL_LOG_PATH_WINDOWS:/path/to/1c/logs/Query1c}"
    # Linux
    # path: "${SQL_LOG_PATH_LINUX:/var/log/1c/Query1c}"
    history: ${SQL_LOG_HISTORY:1}                      # История хранения (в часах)

  # Полные исключения
  error_excp:
    # Windows
    path: "${ERROR_EXCP_LOG_PATH_WINDOWS:/path/to/1c/logs/ERROR_EXCP}"
    # Linux
    # path: "${ERROR_EXCP_LOG_PATH_LINUX:/var/log/1c/ERROR_EXCP}"
    history: ${ERROR_EXCP_LOG_HISTORY:1}                         # История хранения (в часах)

session:
  threshold: ${SESSION_THRESHOLD:50}

zabbix:
  server: "${ZABBIX_SERVER:localhost}"
  port: ${ZABBIX_PORT:10051}

platform: "${PLATFORM:auto}"
```

---

## 🔧 Использование

### Запуск вручную

```bash
# Проверка состояния RAS
python -m src.1c-zabbix-monitor_Windows_Linux.main --metric ras_health --format plain

# Получение количества сессий
python -m src.1c-zabbix-monitor_Windows_Linux.main --metric sessions --format plain

# Получение количества rphost процессов
python -m src.1c-zabbix-monitor_Windows_Linux.main --metric rphost --format plain

# Получение других метрик
python -m src.1c-zabbix-monitor_Windows_Linux.main --metric locks --format plain
python -m src.1c-zabbix-monitor_Windows_Linux.main --metric calls --format plain
python -m src.1c-zabbix-monitor_Windows_Linux.main --metric log_errors --format plain
python -m src.1c-zabbix-monitor_Windows_Linux.main --metric slow_sql --format plain

# Справка по всем доступным параметрам
python -m src.1c-zabbix-monitor_Windows_Linux.main --help
```

### Форматы вывода

* `plain` - простой числовой формат (по умолчанию)
* `json` - JSON формат
* `lld` - Low Level Discovery для Zabbix

---

## 🔌 Интеграция с Zabbix

### 1. Настройка UserParameter

Добавьте файл конфигурации в ваш Zabbix Agent:

**Windows:** `C:\Program Files\Zabbix Agent\zabbix_agentd.conf.d\1c_monitor.conf`
**Linux:** `/etc/zabbix/zabbix_agentd.d/1c_monitor.conf`

```ini
# Проверка доступности RAS
UserParameter=1c.ras.health[*], python -m src.1c-zabbix-monitor_Windows_Linux.main --metric ras_health --format plain

# Количество сессий
UserParameter=1c.sessions.count[*], python -m src.1c-zabbix-monitor_Windows_Linux.main --metric sessions --format plain

# Количество rphost процессов
UserParameter=1c.rphost.count[*], python -m src.1c-zabbix-monitor_Windows_Linux.main --metric rphost --format plain

# Количество блокировок
UserParameter=1c.locks.count[*], python -m src.1c-zabbix-monitor_Windows_Linux.main --metric locks --format plain

# Количество вызовов
UserParameter=1c.calls.count[*], python -m src.1c-zabbix-monitor_Windows_Linux.main --metric calls --format plain

# Количество ошибок в логах
UserParameter=1c.log.errors.count[*], python -m src.1c-zabbix-monitor_Windows_Linux.main --metric log_errors --format plain

# Количество медленных SQL запросов
UserParameter=1c.sql.slow.count[*], python -m src.1c-zabbix-monitor_Windows_Linux.main --metric slow_sql --format plain

# Low Level Discovery для rphost процессов
UserParameter=1c.rphost.discovery[*], python -m src.1c-zabbix-monitor_Windows_Linux.main --metric rphost --format lld
```

### 2. Шаблоны Zabbix

Создайте шаблон Zabbix с соответствующими элементами данных и триггерами:

* `1c.ras.health` - проверка доступности RAS (ожидаемое значение: 1)
* `1c.sessions.count` - количество активных сессий
* `1c.rphost.count` - количество rphost процессов
* `1c.locks.count` - количество блокировок
* `1c.calls.count` - количество вызовов
* `1c.log.errors.count` - количество ошибок в логах
* `1c.sql.slow.count` - количество медленных SQL запросов

### 3. Рекомендуемые интервалы опроса

* RAS Health: 1-5 минут
* Сессии: 1-5 минут
* Rphost: 1-5 минут
* Блокировки: 1-5 минут
* Ошибки в логах: 1-10 минут
* Медленные SQL запросы: 1-10 минут

---

## ⚙️ Настройка кэширования

Кэширование позволяет снизить нагрузку на кластер 1С, выполняя запросы не чаще заданного интервала:

```yaml
cache:
  ttl: 60  # Время жизни кэша в секундах (по умолчанию 60)
```

Для отключения кэширования используйте флаг `--no-cache` при запуске:

```bash
python -m src.1c-zabbix-monitor_Windows_Linux.main --metric sessions --no-cache
```

---

## 🐞 Отладка

Для включения режима отладки используйте флаг `--debug`:

```bash
python -m src.1c-zabbix-monitor_Windows_Linux.main --metric sessions --debug
```

---

## 📁 Структура проекта

```
1c-zabbix-monitor/
├── src/
│   └── 1c-zabbix-monitor_Windows_Linux/
│       ├── main.py          # Главный модуль приложения
│       ├── __init__.py
│       ├── __main__.py      # Точка входа для запуска как модуля
│       └── metrics/         # Модули сбора метрик
│           ├── sessions.py  # Сбор метрик сессий
│           ├── rphost.py    # Сбор метрик rphost процессов
│           ├── ras_health.py # Проверка здоровья RAS
│           ├── locks.py     # Сбор метрик блокировок
│           ├── calls.py     # Сбор метрик вызовов
│           ├── log_errors.py # Сбор метрик ошибок в логах
│           ├── slow_sql.py  # Сбор метрик медленных SQL запросов
│           ├── utils_1c.py  # Утилиты для работы с 1С
│           └── __init__.py
├── config.yaml             # Файл конфигурации
├── config.yaml.example     # Пример файла конфигурации
├── .env                   # Файл переменных окружения
├── .env.example           # Пример файла переменных окружения
├── pyproject.toml         # Конфигурация проекта
├── README.md              # Документация
└── LICENSE
```

---

## 🤝 Конфиденциальность и производительность

* Инструмент не передает данные пользователей 1С.
* Все запросы выполняются локально.
* Рекомендуемый интервал опроса в Zabbix: **1-5 минут**.
* Кэширование снижает нагрузку на кластер 1С.

---

## 📞 Поддержка и обратная связь

Если у вас возникли вопросы или проблемы с использованием инструмента, пожалуйста, создайте issue в репозитории проекта.

---

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. Подробности см. в файле LICENSE.