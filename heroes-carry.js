// data/heroes-carry.js — Данные для Pos 1 (Керри)

const CARRY_HEROES = [
  { name: "Abaddon", tags: { damage_single_sustained: 0.8, durability_tanky: 1.0, farm_based: 0.8, fight_brawler: 0.8, fight_diver: 0.8, lane_passive: 1.0, mobility_low: 1.0, peak_midgame: 1.0, push_medium: 1.0, team_dependent: 1.0 } },
  { name: "Alchemist", tags: { damage_aoe: 1.0, durability_tanky: 1.0, farm_based: 0.8, farm_fast: 1.5, fight_diver: 0.8, lane_passive: 1.0, mobility_low: 1.0, peak_midgame: 1.0, push_medium: 1.0, team_dependent: 1.0 } },
  { name: "Anti-Mage", tags: { damage_single_burst: 1.0, damage_single_sustained: 0.8, durability_medium: 1.0, farm_based: 0.8, farm_fast: 1.5, fight_brawler: 0.8, fight_diver: 0.8, fight_invis_flanker: 1.5, flexible_team: 1.0, lane_passive: 1.0, mobility_high: 1.5, peak_late: 0.8, push_medium: 1.0 } },
  { name: "Bloodseeker", tags: { damage_single_sustained: 0.8, durability_medium: 1.0, farm_based: 0.8, fight_brawler: 0.8, fight_diver: 0.8, lane_passive: 1.0, mobility_medium: 1.0, peak_late: 0.8, push_bad: 1.5, snowball_based: 1.0, team_dependent: 1.0 } },
  { name: "Broodmother", tags: { damage_single_burst: 1.0, durability_medium: 1.0, farm_fast: 1.5, fight_invis_flanker: 1.5, flexible_team: 1.0, lane_aggressive: 1.0, mobility_high: 1.5, needs_micro: 1.5, peak_midgame: 1.0, push_good: 1.0, snowball_based: 1.0 } },
  { name: "Chaos Knight", tags: { damage_single_burst: 1.0, durability_tanky: 1.0, fight_diver: 0.8, lane_aggressive: 1.0, mobility_low: 1.0, peak_midgame: 1.0, push_bad: 1.5, snowball_based: 1.0, team_dependent: 1.0 } },
  { name: "Clinkz", tags: { damage_single_burst: 1.0, durability_fragile: 1.0, farm_based: 0.8, fight_backline: 1.0, fight_invis_flanker: 1.5, flexible_team: 1.0, lane_aggressive: 1.0, mobility_high: 1.5, peak_midgame: 1.0, push_good: 1.0, snowball_based: 1.0 } },
  { name: "Dragon Knight", tags: { damage_single_sustained: 0.8, durability_tanky: 1.0, farm_based: 0.8, fight_brawler: 0.8, fight_diver: 0.8, lane_passive: 1.0, mobility_low: 1.0, peak_late: 0.8, push_medium: 1.0, team_dependent: 1.0 } },
  { name: "Drow Ranger", tags: { damage_single_sustained: 0.8, durability_fragile: 1.0, farm_based: 0.8, fight_backline: 1.0, fight_brawler: 0.8, lane_aggressive: 1.0, mobility_low: 1.0, peak_late: 0.8, peak_super_lategame: 1.5, push_medium: 1.0, team_dependent: 1.0 } },
  { name: "Faceless Void", tags: { damage_aoe: 1.0, damage_single_sustained: 0.8, durability_fragile: 1.0, durability_medium: 1.0, farm_based: 0.8, fight_diver: 0.8, fight_invis_flanker: 1.5, lane_passive: 1.0, mobility_medium: 1.0, peak_late: 0.8, peak_super_lategame: 1.5, push_medium: 1.0, team_dependent: 1.0 } },
  { name: "Gyrocopter", tags: { damage_aoe: 1.0, damage_single_sustained: 0.8, durability_fragile: 1.0, farm_based: 0.8, farm_fast: 1.5, fight_backline: 1.0, fight_brawler: 0.8, lane_passive: 1.0, mobility_low: 1.0, peak_late: 0.8, peak_super_lategame: 1.5, push_medium: 1.0, team_dependent: 1.0 } },
  { name: "Juggernaut", tags: { damage_aoe: 1.0, damage_single_sustained: 0.8, durability_medium: 1.0, farm_based: 0.8, fight_brawler: 0.8, fight_diver: 0.8, flexible_team: 1.0, lane_passive: 1.0, mobility_medium: 1.0, peak_late: 0.8, push_good: 1.0 } },
  { name: "Kez", tags: { damage_aoe: 1.0, damage_single_burst: 1.0, durability_medium: 1.0, fight_diver: 0.8, fight_invis_flanker: 1.5, flexible_team: 1.0, lane_passive: 1.0, mobility_medium: 1.0, peak_midgame: 1.0, push_good: 1.0, snowball_based: 1.0 } },
  { name: "Lifestealer", tags: { damage_single_sustained: 0.8, durability_tanky: 1.0, farm_based: 0.8, fight_brawler: 0.8, lane_passive: 1.0, mobility_medium: 1.0, peak_late: 0.8, push_medium: 1.0, team_dependent: 1.0 } },
  { name: "Luna", tags: { damage_aoe: 1.0, damage_single_sustained: 0.8, durability_medium: 1.0, farm_based: 0.8, farm_fast: 1.5, fight_backline: 1.0, fight_brawler: 0.8, lane_passive: 1.0, mobility_low: 1.0, peak_late: 0.8, peak_midgame: 1.0, push_medium: 1.0, team_dependent: 1.0 } },
  { name: "Marci", tags: { damage_single_burst: 1.0, durability_medium: 1.0, fight_diver: 0.8, lane_aggressive: 1.0, mobility_low: 1.0, peak_midgame: 1.0, push_medium: 1.0, snowball_based: 1.0, team_dependent: 1.0 } },
  { name: "Medusa", tags: { damage_aoe: 1.0, damage_single_sustained: 0.8, durability_tanky: 1.0, farm_based: 0.8, farm_fast: 1.5, fight_backline: 1.0, fight_brawler: 0.8, lane_passive: 1.0, mobility_low: 1.0, peak_late: 0.8, peak_super_lategame: 1.5, push_bad: 1.5, team_dependent: 1.0 } },
  { name: "Monkey King", tags: { damage_aoe: 1.0, damage_single_sustained: 0.8, durability_medium: 1.0, fight_brawler: 0.8, fight_invis_flanker: 1.5, flexible_team: 1.0, lane_aggressive: 1.0, mobility_high: 1.5, peak_midgame: 1.0, push_medium: 1.0, snowball_based: 1.0 } },
  { name: "Morphling", tags: { damage_single_burst: 1.0, damage_single_sustained: 0.8, durability_medium: 1.0, farm_based: 0.8, fight_brawler: 0.8, fight_diver: 0.8, flexible_team: 1.0, lane_passive: 1.0, mobility_medium: 1.0, peak_late: 0.8, push_good: 1.0, snowball_based: 1.0 } },
  { name: "Naga Siren", tags: { damage_single_sustained: 0.8, durability_medium: 1.0, farm_based: 0.8, farm_fast: 1.5, fight_brawler: 0.8, flexible_team: 1.0, lane_passive: 1.0, mobility_low: 1.0, needs_micro: 1.5, peak_late: 0.8, push_good: 1.0 } },
  { name: "Nature's Prophet", tags: { damage_aoe: 1.0, damage_single_sustained: 0.8, durability_fragile: 1.0, farm_based: 0.8, farm_fast: 1.5, fight_backline: 1.0, flexible_team: 1.0, lane_passive: 1.0, mobility_high: 1.5, peak_late: 0.8, peak_midgame: 1.0, push_good: 1.0 } },
  { name: "Omniknight", tags: { damage_single_burst: 1.0, damage_single_sustained: 0.8, durability_tanky: 1.0, fight_diver: 0.8, lane_aggressive: 1.0, mobility_low: 1.0, peak_midgame: 1.0, push_bad: 1.5, snowball_based: 1.0, team_dependent: 1.0 } },
  { name: "Phantom Assassin", tags: { damage_single_burst: 1.0, damage_single_sustained: 0.8, durability_fragile: 1.0, farm_based: 0.8, fight_brawler: 0.8, fight_diver: 0.8, flexible_team: 1.0, lane_passive: 1.0, mobility_medium: 1.0, peak_late: 0.8, peak_super_lategame: 1.5, push_medium: 1.0, snowball_based: 1.0 } },
  { name: "Phantom Lancer", tags: { damage_single_sustained: 0.8, durability_medium: 1.0, farm_based: 0.8, fight_brawler: 0.8, flexible_team: 1.0, lane_passive: 1.0, mobility_medium: 1.0, needs_micro: 1.5, peak_late: 0.8, peak_super_lategame: 1.5, push_medium: 1.0 } },
  { name: "Razor", tags: { damage_aoe: 1.0, damage_single_sustained: 0.8, durability_medium: 1.0, durability_tanky: 1.0, fight_brawler: 0.8, fight_diver: 0.8, lane_aggressive: 1.0, mobility_low: 1.0, peak_midgame: 1.0, push_bad: 1.5, snowball_based: 1.0, team_dependent: 1.0 } },
  { name: "Riki", tags: { damage_aoe: 1.0, damage_single_sustained: 0.8, durability_fragile: 1.0, fight_diver: 0.8, fight_invis_flanker: 1.5, flexible_team: 1.0, lane_passive: 1.0, mobility_medium: 1.0, peak_late: 0.8, push_bad: 1.5, snowball_based: 1.0 } },
  { name: "Shadow Fiend", tags: { damage_aoe: 1.0, damage_single_burst: 1.0, damage_single_sustained: 0.8, durability_fragile: 1.0, farm_based: 0.8, fight_backline: 1.0, fight_brawler: 0.8, fight_diver: 0.8, lane_aggressive: 1.0, mobility_low: 1.0, peak_midgame: 1.0, peak_super_lategame: 1.5, push_good: 1.0, snowball_based: 1.0, team_dependent: 1.0 } },
  { name: "Slark", tags: { damage_single_sustained: 0.8, durability_medium: 1.0, fight_brawler: 0.8, flexible_team: 1.0, lane_aggressive: 1.0, mobility_high: 1.5, peak_midgame: 1.0, push_bad: 1.5, snowball_based: 1.0 } },
  { name: "Sniper", tags: { damage_single_sustained: 0.8, durability_fragile: 1.0, farm_based: 0.8, fight_backline: 1.0, fight_brawler: 0.8, lane_aggressive: 1.0, mobility_low: 1.0, peak_late: 0.8, push_medium: 1.0, team_dependent: 1.0 } },
  { name: "Spectre", tags: { damage_aoe: 1.0, damage_single_sustained: 0.8, durability_medium: 1.0, farm_based: 0.8, fight_diver: 0.8, flexible_team: 1.0, lane_passive: 1.0, mobility_medium: 1.0, peak_super_lategame: 1.5, push_bad: 1.5, snowball_based: 1.0 } },
  { name: "Sven", tags: { damage_aoe: 1.0, damage_single_burst: 1.0, durability_medium: 1.0, durability_tanky: 1.0, farm_based: 0.8, farm_fast: 1.5, fight_diver: 0.8, flexible_team: 1.0, lane_passive: 1.0, mobility_low: 1.0, peak_late: 0.8, peak_midgame: 1.0, push_medium: 1.0 } },
  { name: "Templar Assassin", tags: { damage_single_burst: 1.0, damage_single_sustained: 0.8, durability_medium: 1.0, farm_based: 0.8, farm_fast: 1.5, fight_diver: 0.8, flexible_team: 1.0, lane_passive: 1.0, mobility_low: 1.0, peak_late: 0.8, peak_midgame: 1.0, push_medium: 1.0, snowball_based: 1.0 } },
  { name: "Terrorblade", tags: { damage_single_sustained: 0.8, durability_medium: 1.0, farm_based: 0.8, farm_fast: 1.5, fight_backline: 1.0, fight_brawler: 0.8, lane_passive: 1.0, mobility_low: 1.0, needs_micro: 1.5, peak_late: 0.8, peak_super_lategame: 1.5, push_good: 1.0, team_dependent: 1.0 } },
  { name: "Troll Warlord", tags: { damage_single_sustained: 0.8, durability_medium: 1.0, farm_based: 0.8, fight_brawler: 0.8, fight_diver: 0.8, lane_passive: 1.0, mobility_low: 1.0, peak_late: 0.8, push_good: 1.0, team_dependent: 1.0 } },
  { name: "Ursa", tags: { damage_single_burst: 1.0, durability_medium: 1.0, durability_tanky: 1.0, farm_based: 0.8, fight_diver: 0.8, fight_invis_flanker: 1.5, flexible_team: 1.0, lane_aggressive: 1.0, mobility_low: 1.0, peak_late: 0.8, peak_midgame: 1.0, push_bad: 1.5, snowball_based: 1.0 } },
  { name: "Weaver", tags: { damage_aoe: 1.0, damage_single_burst: 1.0, damage_single_sustained: 0.8, durability_fragile: 1.0, farm_based: 0.8, fight_backline: 1.0, flexible_team: 1.0, lane_passive: 1.0, mobility_high: 1.5, peak_late: 0.8, peak_midgame: 1.0, push_good: 1.0, snowball_based: 1.0 } },
  { name: "Windranger", tags: { damage_single_burst: 1.0, damage_single_sustained: 0.8, durability_fragile: 1.0, farm_based: 0.8, fight_backline: 1.0, fight_invis_flanker: 1.5, flexible_team: 1.0, lane_aggressive: 1.0, mobility_high: 1.5, peak_late: 0.8, peak_midgame: 1.0, push_good: 1.0, snowball_based: 1.0 } },
  { name: "Wraith King", tags: { damage_single_sustained: 0.8, durability_tanky: 1.0, farm_based: 0.8, fight_brawler: 0.8, fight_diver: 0.8, lane_passive: 1.0, mobility_low: 1.0, peak_late: 0.8, peak_midgame: 1.0, push_medium: 1.0, team_dependent: 1.0 } },
];

// Мета-данные: сложность и тип атаки (нужны для бонуса за сложность и melee/ranged фильтра)
const CARRY_HERO_META = {
  "Abaddon":          { difficulty: "easy",   melee: true  },
  "Alchemist":        { difficulty: "easy",   melee: true  },
  "Anti-Mage":        { difficulty: "hard",   melee: true  },
  "Bloodseeker":      { difficulty: "easy",   melee: true  },
  "Broodmother":      { difficulty: "hard",   melee: true  },
  "Chaos Knight":     { difficulty: "medium", melee: true  },
  "Clinkz":           { difficulty: "easy",   melee: false },
  "Dragon Knight":    { difficulty: "easy",   melee: true, both: true },
  "Drow Ranger":      { difficulty: "easy",   melee: false },
  "Faceless Void":    { difficulty: "easy",   melee: true  },
  "Gyrocopter":       { difficulty: "easy",   melee: false },
  "Juggernaut":       { difficulty: "easy",   melee: true  },
  "Kez":              { difficulty: "hard",   melee: true  },
  "Lifestealer":      { difficulty: "easy",   melee: true  },
  "Luna":             { difficulty: "easy",   melee: false },
  "Marci":            { difficulty: "medium", melee: true  },
  "Medusa":           { difficulty: "easy",   melee: false },
  "Monkey King":      { difficulty: "medium", melee: true  },
  "Morphling":        { difficulty: "hard",   melee: false },
  "Naga Siren":       { difficulty: "hard",   melee: true  },
  "Nature's Prophet": { difficulty: "medium", melee: false },
  "Omniknight":       { difficulty: "easy",   melee: true  },
  "Phantom Assassin": { difficulty: "easy",   melee: true  },
  "Phantom Lancer":   { difficulty: "hard",   melee: true  },
  "Razor":            { difficulty: "easy",   melee: false },
  "Riki":             { difficulty: "easy",   melee: true  },
  "Shadow Fiend":     { difficulty: "medium", melee: false },
  "Slark":            { difficulty: "medium", melee: true  },
  "Sniper":           { difficulty: "easy",   melee: false },
  "Spectre":          { difficulty: "medium", melee: true  },
  "Sven":             { difficulty: "easy",   melee: true  },
  "Templar Assassin": { difficulty: "medium", melee: false },
  "Terrorblade":      { difficulty: "hard",   melee: true, both: true },
  "Troll Warlord":    { difficulty: "medium", melee: true, both: true },
  "Ursa":             { difficulty: "easy",   melee: true  },
  "Weaver":           { difficulty: "medium", melee: false },
  "Windranger":       { difficulty: "medium", melee: false },
  "Wraith King":      { difficulty: "easy",   melee: true  },
};

window.heroCarryData = {
  questions: [
    {
      question: "На каком этапе игры ты хочешь быть максимально полезен?",
      answers: [
        { text: "Середина игры — хочу почувствовать силу уже к 20–30 минуте.", icon: "ph-clock", tags: ["peak_midgame"] },
        { text: "Поздняя игра — пик где-то к 35–45 минуте.", icon: "ph-clock-clockwise", tags: ["peak_late"] },
        { text: "Суперлейт — люблю затяжные игры 50+ минут.", icon: "ph-hourglass", tags: ["peak_super_lategame"] }
      ]
    },
    {
      question: "Как твой герой фармит?",
      answers: [
        { text: "Есть встроенная механика — фармлю быстрее обычного с самого начала.", icon: "ph-lightning", tags: ["farm_fast"] },
        { text: "Как обычный герой — разгоняюсь только после покупки фарм-предмета.", icon: "ph-package", tags: ["farm_based"] }
      ]
    },
    {
      question: "Какой тип атаки тебе нравится?",
      answers: [
        { text: "Ближний бой — не против подойти к врагу вплотную.", icon: "ph-sword", tags: ["melee"] },
        { text: "Дальняя дистанция — хочу держаться подальше.", icon: "ph-crosshair", tags: ["ranged"] }
      ]
    },
    {
      question: "Как тебе комфортнее действовать в файте?",
      answers: [
        { text: "Могу инициировать файт — стараюсь убивать ключевых вражеских героев.", icon: "ph-rocket-launch", tags: ["fight_diver"] },
        { text: "Держу позицию — убиваю издалека.", icon: "ph-crosshair", tags: ["fight_backline"] },
        { text: "Стою в центре файта и убиваю райткликом.", icon: "ph-sword", tags: ["fight_brawler"] },
        { text: "Захожу неожиданно — с фланга, из инвиза или через телепорт.", icon: "ph-eye-slash", tags: ["fight_invis_flanker"] }
      ]
    },
    {
      question: "Насколько для тебя важна мобильность героя?",
      answers: [
        { text: "Не важна — позиционируюсь заранее и просто бью.", icon: "ph-anchor", tags: ["mobility_low"] },
        { text: "Средняя — иногда догнать или убежать.", icon: "ph-arrows-left-right", tags: ["mobility_medium"] },
        { text: "Высокая — хочу постоянно быть в движении.", icon: "ph-lightning", tags: ["mobility_high"] }
      ]
    },
    {
      question: "Насколько твой герой хорош в пуше строений?",
      answers: [
        { text: "Герой должен хорошо пушить.", icon: "ph-tree", tags: ["push_good"] },
        { text: "Средне — когда команда рядом могу сносить строения.", icon: "ph-scales", tags: ["push_medium"] },
        { text: "Плохо — пусть другие пушат, я хочу фармить и убивать.", icon: "ph-coins", tags: ["push_bad"] }
      ]
    },
    {
      question: "Насколько сложного героя готов освоить?",
      answers: [
        { text: "Простой — минимум микро, хочу фокус на макро и позиционке.", icon: "ph-leaf", tags: ["easy"] },
        { text: "Средняя сложность — пару комбинаций/навыков, но без экстремального микро.", icon: "ph-scales", tags: ["medium"] },
        { text: "Сложный — сложные механики и много кнопок.", icon: "ph-fire", tags: ["hard"] }
      ]
    }
  ],

  heroes: CARRY_HEROES.map(h => ({
    ...h,
    ...(CARRY_HERO_META[h.name] || { difficulty: "medium", melee: true }),
  })),
};
