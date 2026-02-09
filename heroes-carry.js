// data/heroes-carry.js — Данные для Pos 1 (Керри)
window.heroCarryData = {
questions: [
                {
                    question: "На каком этапе игры ты хочешь быть максимально полезен?",
                    answers: [
                        { text: "⚔️ Середина игры — хочу почувствовать силу уже к 20–30 минуте", tags: ["midgame", "tempo"] },
                        { text: "🐉 Поздняя игра — пик где-то к 35–45 минуте", tags: ["lategame"] },
                        { text: "⏳ Суперлейт — люблю затяжные игры 50+ минут", tags: ["lategame", "superlate", "greedy"] }
                    ]
                },
                {
                    question: "Какой тип атаки тебе нравится?",
                    answers: [
                        { text: "🗡️ Ближний бой — не против подойти к врагу вплотную", tags: ["melee"] },
                        { text: "🏹 Дальняя дистанция — хочу держаться подальше", tags: ["ranged"] }
                    ]
                },
                {
                    question: "Какой тип урона тебе больше нравится?",
                    answers: [
                        { text: "💥 Быстрый урон — врываюсь и за секунды стираю героя", tags: ["burst"] },
                        { text: "♾ Постоянный урон — хочу просто райткликать", tags: ["sustained"] }
                    ]
                },
                {
                    question: "Как ты предпочитаешь влиять на карту?",
                    answers: [
                        { text: "🗺️ Сплит-пушить, давить линии, выманивать врагов", tags: ["splitpush", "map_pressure"] },
                        { text: "⚔️ Чаще быть с командой в драках и вокруг объективов", tags: ["teamfight"] },
                        { text: "🎯 Иметь возможность делать соло пикоффы по карте", tags: ["pickoff", "map_pressure"] }
                    ]
                },
                {
                    question: "Насколько сложного героя готов освоить?",
                    answers: [
                        { text: "😊 Простой — минимум микро, хочу фокус на макро и позиционке", tags: ["easy"] },
                        { text: "⚖️ Средняя сложность — пару комбинаций/навыков, но без экстремального микро", tags: ["medium"] },
                        { text: "🎓 Сложный — сложные механики и много кнопок", tags: ["hard"] }
                    ]
                }
            ],
        heroes: [
                    { name: "Alchemist", tags: ["midgame","lategame","tempo","melee","sustained","farming","snowball","map_pressure","splitpush","teamfight"], difficulty: "easy" },
                    { name: "Chaos Knight", tags: ["midgame","lategame","melee","burst","sustained","map_pressure","teamfight","durable","snowball"], difficulty: "medium" },
                    { name: "Dragon Knight", tags: ["midgame","lategame","melee","ranged","sustained","teamfight","map_pressure","splitpush","durable","control","farming"], difficulty: "easy" },
                    { name: "Lifestealer", tags: ["midgame","lategame","melee","sustained","pickoff","teamfight","durable","snowball"], difficulty: "easy" },
                    { name: "Omniknight", tags: ["midgame","lategame","melee","sustained","teamfight","utility","durable"], difficulty: "easy" },
                    { name: "Sven", tags: ["midgame","lategame","melee","burst","sustained","teamfight","map_pressure","farming"], difficulty: "easy" },
                    { name: "Tiny", tags: ["midgame","lategame","melee","burst","sustained","pickoff","teamfight","map_pressure","snowball","durable","control"], difficulty: "medium" },
                    { name: "Wraith King", tags: ["midgame","lategame","melee","sustained","teamfight","map_pressure","durable","farming"], difficulty: "easy" },
                    { name: "Anti-Mage", tags: ["lategame","superlate","greedy","melee","sustained","burst","splitpush","map_pressure","mobile","farming","snowball"], difficulty: "hard" },
                    { name: "Bloodseeker", tags: ["midgame","lategame","tempo","melee","burst","sustained","pickoff","teamfight","map_pressure","aggressive","snowball"], difficulty: "easy" },
                    { name: "Broodmother", tags: ["midgame","lategame","melee","sustained","splitpush","map_pressure","farming","snowball"], difficulty: "hard" },
                    { name: "Clinkz", tags: ["midgame","lategame","tempo","ranged","burst","sustained","pickoff","splitpush","map_pressure","mobile","snowball"], difficulty: "easy" },
                    { name: "Drow Ranger", tags: ["lategame","superlate","greedy","ranged","sustained","teamfight","farming"], difficulty: "easy" },
                    { name: "Faceless Void", tags: ["lategame","superlate","melee","sustained","burst","teamfight","pickoff","control","farming","mobile"], difficulty: "easy" },
                    { name: "Gyrocopter", tags: ["lategame","superlate","greedy","lategame","tempo","ranged","sustained","teamfight","map_pressure","farming"], difficulty: "easy" },
                    { name: "Juggernaut", tags: ["lategame","superlate","greedy","melee","sustained","burst","teamfight","map_pressure","pickoff","farming"], difficulty: "easy" },
                    { name: "Kez", tags: ["midgame","lategame","tempo","melee","burst","sustained","teamfight","map_pressure","pickoff","farming"], difficulty: "hard" },
                    { name: "Lone Druid", tags: ["midgame","lategame","melee","ranged","sustained","splitpush","map_pressure","teamfight","farming"], difficulty: "hard" },
                    { name: "Luna", tags: ["midgame","lategame","ranged","sustained","burst","teamfight","map_pressure","farming"], difficulty: "easy" },
                    { name: "Medusa", tags: ["lategame","superlate","greedy","ranged","sustained","teamfight","durable","farming"], difficulty: "easy" },
                    { name: "Monkey King", tags: ["midgame","lategame","melee","sustained","burst","teamfight","pickoff","map_pressure","mobile","snowball"], difficulty: "medium" },
                    { name: "Morphling", tags: ["lategame","superlate","ranged","burst","sustained","teamfight","pickoff","map_pressure","mobile","snowball","farming"], difficulty: "hard" },
                    { name: "Naga Siren", tags: ["lategame","superlate","greedy","melee","sustained","splitpush","map_pressure","teamfight","farming"], difficulty: "hard" },
                    { name: "Phantom Assassin", tags: ["midgame","lategame","melee","burst","sustained","pickoff","teamfight","snowball","farming"], difficulty: "easy" },
                    { name: "Phantom Lancer", tags: ["lategame","superlate","greedy","melee","sustained","splitpush","map_pressure","teamfight","farming"], difficulty: "hard" },
                    { name: "Razor", tags: ["midgame","lategame","tempo","ranged","sustained","teamfight","map_pressure","durable"], difficulty: "easy" },
                    { name: "Riki", tags: ["midgame","lategame","tempo","melee","burst","sustained","pickoff","map_pressure","mobile","snowball"], difficulty: "easy" },
                    { name: "Shadow Fiend", tags: ["midgame","lategame","ranged","burst","sustained","teamfight","map_pressure","farming","snowball"], difficulty: "medium" },
                    { name: "Slark", tags: ["midgame","lategame","tempo","melee","sustained","burst","pickoff","map_pressure","teamfight","mobile","snowball"], difficulty: "medium" },
                    { name: "Sniper", tags: ["lategame","superlate","greedy","ranged","sustained","burst","teamfight","map_pressure","farming"], difficulty: "easy" },
                    { name: "Spectre", tags: ["lategame","superlate","greedy","melee","sustained","teamfight","map_pressure","durable","farming"], difficulty: "medium" },
                    { name: "Templar Assassin", tags: ["midgame","lategame","tempo","ranged","burst","sustained","pickoff","teamfight","map_pressure","snowball","farming"], difficulty: "medium" },
                    { name: "Terrorblade", tags: ["lategame","superlate","greedy","melee","ranged","sustained","splitpush","map_pressure","teamfight","farming"], difficulty: "hard" },
                    { name: "Troll Warlord", tags: ["lategame","superlate","melee","ranged","sustained","teamfight","map_pressure","farming"], difficulty: "medium" },
                    { name: "Ursa", tags: ["midgame","lategame","tempo","melee","burst","sustained","pickoff","teamfight","map_pressure","snowball"], difficulty: "easy" },
                    { name: "Weaver", tags: ["midgame","superlate","lategame","ranged","sustained","burst","pickoff","map_pressure","teamfight","mobile","snowball"], difficulty: "medium" },
                    { name: "Abaddon", tags: ["midgame","lategame","superlate","melee","sustained","teamfight","map_pressure","durable","utility","farming"], difficulty: "easy" },
                    { name: "Windranger", tags: ["midgame","lategame","ranged","sustained","burst","pickoff","teamfight","map_pressure","mobile","snowball"], difficulty: "medium" },
                    { name: "Marci", tags: ["midgame","lategame","tempo","melee","burst","sustained","pickoff","teamfight","map_pressure","mobile","snowball"], difficulty: "medium" },
                    { name: "Nature's Prophet", tags: ["midgame","lategame","ranged","sustained","splitpush","map_pressure","pickoff","teamfight","farming","mobile"], difficulty: "medium" }
                ],
};