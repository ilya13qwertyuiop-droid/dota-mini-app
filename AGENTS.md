## Design Context

### Users
Dota 2 players (primarily Russian-speaking) accessing the app inside Telegram on mobile. They're looking for a competitive edge — hero picks, counters, synergies, draft strategy. Context is fast decision-making: between games, during draft phase, or theorycrafting builds. They expect information density without clutter.

### Brand Personality
**Competitive, sharp, precise.** The app should feel like a tactical instrument — the kind of tool a serious player trusts before a ranked match. Not flashy for the sake of it, but confident and authoritative. Every element should communicate "this knows what it's talking about."

### Aesthetic Direction
- **Theme:** Dark — near-black (#09090b) with cool neutral tint, minimal contrast between surface layers
- **Visual tone:** Linear.app precision adapted for Dota analytics. Typography does hierarchy work. Color only for meaning (winrate, statuses, active states). Sterile, quiet luxury.
- **Palette:** Single muted slate-blue accent (#6b7db3 — фактический `--accent` в styles.css; ранее здесь значился #7b8bb8, документ синхронизирован с кодом 2026-07-09). Semantic only: green (#3db87a) for wins, red (#e5534b) for losses, amber (#d29922) for warnings/rank. All surfaces use 4-step token system (base → surface → elevated → hover).
- **References:** Linear.app (quiet luxury, sterile precision), Telegram native dark UI
- **Anti-references:** Gaming neon, red/gold "Dota UI", Discord blue (#5865F2), purple gradients, glassmorphism, colored glow effects

### Design Principles
1. **Tactical clarity** — Information hierarchy serves decision-making. The most important data (win rates, counters, synergies) is immediately scannable. No decoration that doesn't serve comprehension.
2. **Native feel** — Should feel like it belongs inside Telegram, not like a website crammed into a webview. Respect platform conventions, touch targets, and scrolling behavior.
3. **Earned confidence** — Use bold typography and sharp contrast to convey authority. The UI should feel like it was built by someone who plays the game, not by someone who read a brief about it.
4. **Dense but breathable** — Pack information tightly (gamers expect data density) but use spacing and grouping to prevent cognitive overload. Every pixel of whitespace is intentional.
5. **Restrained intensity** — Dark theme with controlled accent color. No neon explosions, no gratuitous gradients. Intensity comes from precision, not volume.

## Staging deployment instructions

После изменений проекта в финальном ответе всегда добавляй точную инструкцию деплоя на staging с учётом реально изменённых файлов.

Установленный порядок обновления staging:

1. Локально закоммитить изменения и выполнить `git push origin staging`.
2. На сервере:
   - `cd ~/dota-mini-app-staging`
   - `git pull`
3. Перезапустить только те systemd-сервисы, код которых действительно изменился.
4. Если `git pull` блокируется локальными изменениями, сначала показать `git status --short`. `git stash` указывать только для этого случая.
5. Не предлагать Alembic, nginx, сборку frontend или рестарт остальных сервисов, если они не нужны конкретному изменению.
6. Если изменён `script.js`, обязательно проверить и увеличить `script.js?v=N` в `index.html`.
7. Не выполнять push, деплой или рестарт без отдельной явной команды пользователя.