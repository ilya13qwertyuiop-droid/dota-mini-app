# STRATZ Collector

Локальная CLI-утилита для обновления `hero_matchups.json`. Она запускается на
ПК с доступом к STRATZ, поэтому не зависит от заблокированного IP production
сервера. Утилита не подключается к базе, не перезапускает сервисы и не делает
`scp` сама.

## Что делает

1. Через `heroStats.stats` определяет текущую неделю STRATZ и запрашивает три
   предыдущие завершённые недели. Запросы и интервалы совпадают с прежним
   браузерным скриптом.
2. Повторяет временные сетевые ошибки, `429` и `5xx` до пяти попыток.
3. Агрегирует `synergy` с весом `matchCount` и выдаёт прежний формат
   `hero_matchups.json`, который уже читает backend.
4. До записи сверяет героев, наборы пар и общий объём матчей с текущим
   проверенным файлом. Неполный ответ не заменит рабочий файл.
5. Печатает отчёт о маленьких выборках и асимметричных обратных парах.

## Подготовка

Нужен Python 3.12.3 и отдельное окружение:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r tools\stratz_collector\requirements.txt
$env:STRATZ_API_TOKEN = "..."
```

Токен не передаётся в аргументах и не должен попадать в шаблон, Git или логи.

### macOS

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r tools/stratz_collector/requirements.txt
export STRATZ_API_TOKEN="..."
```

Если STRATZ возвращает `403`, сначала отключи VPN или прокси и повтори запуск:
сервис может блокировать IP-адрес используемого VPN.

## Запуск

```powershell
python -m tools.stratz_collector `
  --reference .\hero_matchups.json `
  --output .\hero_matchups.new.json
```

Если проверка не проходит, команда завершится с кодом `1`, а исходный и
выходной рабочий файлы не будут заменены. После ручной проверки можно загрузить
`hero_matchups.new.json` на staging прежним процессом.

На macOS команда запуска выглядит так:

```bash
python -m tools.stratz_collector \
  --reference ./hero_matchups.json \
  --output ./hero_matchups.new.json
```

## Тесты

```powershell
python -m unittest discover -s tools\stratz_collector\tests -v
```
