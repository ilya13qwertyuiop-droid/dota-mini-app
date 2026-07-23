# STRATZ Collector

Локальная CLI-утилита для обновления `hero_matchups.json`. Она запускается на
ПК с доступом к STRATZ, поэтому не зависит от заблокированного IP production
сервера. Утилита не подключается к базе, не перезапускает сервисы и не делает
`scp` сама.

## Что делает

1. Запрашивает указанное число **полностью завершённых UTC-недель** (по
   умолчанию три; текущая неполная неделя не берётся).
2. Повторяет временные сетевые ошибки, `429` и `5xx` до четырёх раз.
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

## Request template

Скрипт не хранит GraphQL-запрос в Python-коде. Скопируй точный запрос и
соответствие полей из действующего браузерного коллектора в локальный файл,
например `tools/stratz_collector/request-template.local.json`. Этот файл уже
защищён правилом `.gitignore` для `.local.json`.

За основу можно взять `request-template.example.json`. В значениях `variables`
разрешены подстановки:

- `{{week_start}}` и `{{week_end}}` — ISO-границы недели в UTC;
- `{{week_iso}}` — например `2026-W29`;
- `{{week_year}}` и `{{week_number}}` — ISO-год и номер недели.

`records_path` — путь к массиву героев в GraphQL-ответе; остальные поля
сопоставляют его с форматом приложения. Это делает утилиту устойчивой к
переименованию полей в API и не заставляет менять Python при корректировке
рабочего GraphQL-запроса.

## Запуск

```powershell
python -m tools.stratz_collector `
  --reference .\hero_matchups.json `
  --output .\hero_matchups.new.json `
  --request-template .\tools\stratz_collector\request-template.local.json
```

Если проверка не проходит, команда завершится с кодом `1`, а исходный и
выходной рабочий файлы не будут заменены. После ручной проверки можно загрузить
`hero_matchups.new.json` на staging прежним процессом.

## Тесты

```powershell
python -m unittest discover -s tools\stratz_collector\tests -v
```
