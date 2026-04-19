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
// data/heroes-mid.js — Данные для Pos 2 (Мидер)
window.heroMidData = {
  questions: [
    {
      id: 'gank_source',
      question: 'От чего в основном зависит твой ганг‑потенциал на миде?',
      answers: [
        {
          text: 'От уровня и рун (получил 6, взял руну и пошёл гангать).',
          icon: 'ph-lightning',
          tags: ['gank_level_rune']
        },
        {
          text: 'От ключевого предмета (блинк, аганим и т.п.).',
          icon: 'ph-package',
          tags: ['gank_item']
        }
      ]
    },
    {
      id: 'lane_style',
      question: 'Как ты хочешь стоять линию?',
      answers: [
        {
          text: 'Давить и пытаться убить оппонента.',
          icon: 'ph-sword',
          tags: ['lane_pressure']
        },
        {
          text: 'Играть гибко: и фарм, и давление.',
          icon: 'ph-arrows-left-right',
          tags: ['lane_mixed']
        },
        {
          text: 'Спокойно фармить, главное — не проиграть линию.',
          icon: 'ph-coins',
          tags: ['lane_farm']
        }
      ]
    },
    {
      id: 'post_lane',
      question: 'Что ты хочешь делать после выхода с линии?',
      answers: [
        {
          text: 'Постоянно бегать и играть с командой.',
          icon: 'ph-users-three',
          tags: ['post_team_gank']
        },
        {
          text: 'Чередовать фарм и подключение к дракам.',
          icon: 'ph-arrows-clockwise',
          tags: ['post_mix']
        },
        {
          text: 'Больше фармить и пушить, файты если выгодно.',
          icon: 'ph-tree',
          tags: ['post_farm_push']
        }
      ]
    },
    {
      id: 'difficulty',
      question: 'Насколько сложным может быть герой по механике?',
      answers: [
        {
          text: 'Простой, минимум кнопок.',
          icon: 'ph-leaf',
          tags: ['difficulty_easy']
        },
        {
          text: 'Средний, без особого микро.',
          icon: 'ph-scales',
          tags: ['difficulty_medium']
        },
        {
          text: 'Сложный, люблю ломать пальцы.',
          icon: 'ph-fire',
          tags: ['difficulty_hard']
        }
      ]
    },
    {
      id: 'fight_role',
      question: 'Какую роль ты хочешь выполнять в драках?',
      answers: [
        {
          text: 'Инициатор — врываться первым.',
          icon: 'ph-rocket-launch',
          tags: ['role_initiator']
        },
        {
          text: 'Бёрст — быстро убивать ключевую цель.',
          icon: 'ph-crosshair',
          tags: ['role_burst']
        },
        {
          text: 'Контроль/длительный урон из позиции.',
          icon: 'ph-anchor',
          tags: ['role_control']
        }
      ]
    }
  ],
  
  heroes: [
    { name: "Earth Spirit", tags: ["gank_level_rune","lane_pressure","post_team_gank","difficulty_hard","role_initiator"], difficulty: "hard" },
    { name: "Earthshaker", tags: ["gank_item","lane_mixed","post_team_gank","difficulty_easy","role_initiator","role_control"], difficulty: "easy" },
    { name: "Huskar", tags: ["gank_item","lane_pressure","post_mix","difficulty_medium","role_initiator"], difficulty: "medium" },
    { name: "Dragon Knight", tags: ["gank_item","lane_farm","post_farm_push","difficulty_easy","role_initiator","role_control"], difficulty: "easy" },
    { name: "Primal Beast", tags: ["gank_level_rune","lane_pressure","post_team_gank","difficulty_medium","role_initiator","role_burst"], difficulty: "medium" },
    { name: "Slardar", tags: ["gank_item","lane_mixed","post_team_gank","difficulty_easy","role_initiator"], difficulty: "easy" },
    { name: "Timbersaw", tags: ["gank_level_rune","lane_pressure","post_farm_push","difficulty_medium","role_burst","role_initiator"], difficulty: "medium" },
    { name: "Tiny", tags: ["gank_item","lane_mixed","post_team_gank","difficulty_easy","role_initiator","role_burst"], difficulty: "easy" },
    { name: "Broodmother", tags: ["gank_item","lane_farm","post_farm_push","difficulty_hard","role_burst"], difficulty: "hard" },
    { name: "Clinkz", tags: ["gank_item","lane_farm","post_farm_push","difficulty_easy","role_burst","role_control"], difficulty: "easy" },
    { name: "Kez", tags: ["gank_item","lane_mixed","post_mix","difficulty_hard","role_burst"], difficulty: "hard" },
    { name: "Lone Druid", tags: ["gank_item","lane_farm","post_farm_push","difficulty_hard"], difficulty: "hard" },
    { name: "Meepo", tags: ["gank_item","lane_mixed","post_farm_push","difficulty_hard"], difficulty: "hard" },
    { name: "Monkey King", tags: ["gank_level_rune","lane_pressure","post_mix","difficulty_medium","role_initiator"], difficulty: "medium" },
    { name: "Morphling", tags: ["gank_item","lane_farm","post_farm_push","difficulty_hard","role_burst"], difficulty: "hard" },
    { name: "Riki", tags: ["gank_item","lane_farm","post_team_gank","difficulty_easy","role_control"], difficulty: "easy" },
    { name: "Shadow Fiend", tags: ["gank_level_rune","lane_pressure","post_mix","difficulty_medium","role_burst"], difficulty: "medium" },
    { name: "Sniper", tags: ["gank_item","lane_farm","post_farm_push","difficulty_easy","role_control"], difficulty: "easy" },
    { name: "Templar Assassin", tags: ["gank_item","lane_mixed","post_mix","difficulty_medium","role_burst"], difficulty: "medium" },
    { name: "Viper", tags: ["gank_level_rune","lane_pressure","post_mix","difficulty_easy","role_control"], difficulty: "easy" },
    { name: "Invoker", tags: ["gank_item","lane_mixed","post_mix","difficulty_hard","role_control","role_burst"], difficulty: "hard" },
    { name: "Keeper of the Light", tags: ["gank_item","lane_mixed","post_team_gank","difficulty_medium","role_control"], difficulty: "medium" },
    { name: "Leshrac", tags: ["gank_item","lane_pressure","post_team_gank","difficulty_easy","role_burst"], difficulty: "easy" },
    { name: "Lina", tags: ["gank_level_rune","lane_pressure","post_mix","difficulty_easy","role_burst"], difficulty: "easy" },
    { name: "Necrophos", tags: ["gank_level_rune","lane_farm","post_mix","difficulty_easy","role_control"], difficulty: "easy" },
    { name: "Arc Warden", tags: ["gank_item","lane_farm","post_farm_push","difficulty_hard","role_control"], difficulty: "hard" },
    { name: "Beastmaster", tags: ["gank_item","lane_pressure","post_mix","difficulty_hard","role_initiator","role_control"], difficulty: "hard" },
    { name: "Death Prophet", tags: ["gank_level_rune","lane_pressure","post_team_gank","difficulty_easy","role_control"], difficulty: "easy" },
    { name: "Magnus", tags: ["gank_item","lane_mixed","post_team_gank","difficulty_medium","role_initiator","role_control"], difficulty: "medium" },
    { name: "Marci", tags: ["gank_level_rune","lane_mixed","post_team_gank","difficulty_medium","role_initiator","role_burst"], difficulty: "medium" },
    { name: "Nature's Prophet", tags: ["gank_level_rune","lane_farm","post_farm_push","difficulty_medium","role_control"], difficulty: "medium" },
    { name: "Nyx Assassin", tags: ["gank_level_rune","lane_mixed","post_team_gank","difficulty_easy","role_burst"], difficulty: "easy" },
    { name: "Sand King", tags: ["gank_item","lane_mixed","post_mix","difficulty_easy","role_initiator","role_burst"], difficulty: "easy" },
    { name: "Void Spirit", tags: ["gank_level_rune","lane_mixed","post_mix","difficulty_medium","role_initiator","role_burst"], difficulty: "medium" },
    { name: "Visage", tags: ["gank_item","lane_mixed","post_mix","difficulty_hard","role_control"], difficulty: "hard" },
    { name: "Puck", tags: ["gank_level_rune","lane_mixed","post_team_gank","difficulty_hard","role_initiator","role_control","role_burst"], difficulty: "hard" },
    { name: "Queen of Pain", tags: ["gank_level_rune","lane_pressure","post_team_gank","difficulty_easy","role_burst"], difficulty: "easy" },
    { name: "Rubick", tags: ["gank_level_rune","lane_mixed","post_mix","difficulty_hard","role_control"], difficulty: "hard" },
    { name: "Skywrath Mage", tags: ["gank_level_rune","lane_pressure","post_team_gank","difficulty_easy","role_burst"], difficulty: "easy" },
    { name: "Storm Spirit", tags: ["gank_item","lane_mixed","post_mix","difficulty_medium","role_initiator","role_burst"], difficulty: "medium" },
    { name: "Tinker", tags: ["gank_item","lane_farm","post_farm_push","difficulty_hard","role_control"], difficulty: "hard" },
    { name: "Zeus", tags: ["gank_level_rune","lane_farm","post_mix","difficulty_easy","role_control"], difficulty: "easy" }
  ]
};
// data/heroes-offlane.js — Данные для Pos 3 (Хардлейнер)
window.heroOfflaneData = {
  questions: [
    {
      id: 'hero_priority',
      question: 'Что важнее всего для твоего героя?',
      answers: [
        {
          text: 'Ключевой предмет для инициации',
          icon: 'ph-package',
          tags: ['needs_blink']
        },
        {
          text: 'Предметы на стойкость',
          icon: 'ph-shield',
          tags: ['needs_tank_items']
        },
        {
          text: 'Уровень и способности — сильный с 6-7 уровня, предметы вторичны',
          icon: 'ph-lightning',
          tags: ['level_dependent']
        },
        {
          text: 'Фарм для масштабирования — нужны дорогие предметы',
          icon: 'ph-coins',
          tags: ['needs_farm_scaling']
        }
      ]
    },
    {
      id: 'control_type',
      question: 'Какой тип контроля тебе нужен?',
      answers: [
        {
          text: 'Длительный контроль — долго держу врагов в стане',
          icon: 'ph-lock',
          tags: ['long_control']
        },
        {
          text: 'Быстрый контроль — короткие станы + урон',
          icon: 'ph-lightning',
          tags: ['burst_control']
        },
        {
          text: 'Зональный контроль — замедления/сайленсы, ограничиваю пространство',
          icon: 'ph-grid-four',
          tags: ['zone_control']
        },
        {
          text: 'Без сильного контроля — давлю уроном',
          icon: 'ph-sword',
          tags: ['high_damage']
        }
      ]
    },
    {
      id: 'lane_style',
      question: 'Как ты играешь первые 10 минут?',
      answers: [
        {
          text: 'Агрессивно давлю керри, хочу убивать на линии',
          icon: 'ph-fire',
          tags: ['lane_aggressive']
        },
        {
          text: 'Пассивно фармлю/выживаю до 6 уровня',
          icon: 'ph-shield',
          tags: ['lane_passive']
        },
        {
          text: 'Быстро пушу линию и иду в лес',
          icon: 'ph-tree',
          tags: ['lane_push_jungle']
        },
        {
          text: 'Активно роумлю после 6 уровня',
          icon: 'ph-path',
          tags: ['lane_roam']
        }
      ]
    },
    {
      id: 'post_lane',
      question: 'Твой стиль после 15 минуты?',
      answers: [
        {
          text: 'Играю с командой 5v5',
          icon: 'ph-users-three',
          tags: ['teamfight_5v5']
        },
        {
          text: 'Хожу по разным лайнам — сплит-пушу',
          icon: 'ph-arrows-split',
          tags: ['splitpush']
        },
        {
          text: 'Охочусь за одиночными героями на карте',
          icon: 'ph-crosshair',
          tags: ['hunt_pickoff']
        },
        {
          text: 'Гибкий стиль — комбинирую драки, фарм и давление',
          icon: 'ph-arrows-left-right',
          tags: ['flexible']
        }
      ]
    },
    {
      id: 'difficulty',
      question: 'Какая сложность героя тебе подходит?',
      answers: [
        {
          text: 'Простой — понятные способности, минимум микро',
          icon: 'ph-leaf',
          tags: ['easy']
        },
        {
          text: 'Средний — нужно понимать тайминги и позиционирование',
          icon: 'ph-scales',
          tags: ['medium']
        },
        {
          text: 'Сложный — люблю ломать пальцы',
          icon: 'ph-fire',
          tags: ['hard']
        }
      ]
    }
  ],

  heroes: [
    { 
      name: "Alchemist", 
      tags: {
        needs_farm_scaling: 1.0,
        high_damage: 1.0,
        lane_aggressive: 0.6,
        lane_passive: 0.4,
        flexible: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Axe", 
      tags: {
        needs_blink: 1.0,
        burst_control: 1.0,
        lane_passive: 0.6,
        lane_aggressive: 0.4,
        teamfight_5v5: 0.7,
        hunt_pickoff: 0.3
      },
      difficulty: "easy" 
    },
    { 
      name: "Bristleback", 
      tags: {
        needs_tank_items: 1.0,
        high_damage: 1.0,
        lane_aggressive: 1.0,
        flexible: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Centaur Warrunner", 
      tags: {
        needs_blink: 0.2,
        needs_tank_items: 0.8,
        long_control: 1.0,
        lane_passive: 0.7,
        lane_aggressive: 0.3,
        teamfight_5v5: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Chaos Knight", 
      tags: {
        needs_farm_scaling: 1.0,
        burst_control: 1.0,
        lane_aggressive: 0.6,
        lane_passive: 0.4,
        flexible: 0.8,
        hunt_pickoff: 0.2
      },
      difficulty: "easy" 
    },
    { 
      name: "Dawnbreaker", 
      tags: {
        level_dependent: 1.0,
        burst_control: 0.7,
        zone_control: 0.3,
        lane_aggressive: 0.8,
        lane_passive: 0.2,
        flexible: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Doom", 
      tags: {
        level_dependent: 0.6,
        needs_farm_scaling: 0.4,
        zone_control: 0.3,
        long_control: 0.7,
        lane_push_jungle: 0.7,
        lane_passive: 0.3,
        flexible: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Dragon Knight", 
      tags: {
        needs_farm_scaling: 1.0,
        burst_control: 0.5,
        high_damage: 0.5,
        lane_passive: 0.7,
        lane_aggressive: 0.3,
        flexible: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Earth Spirit", 
      tags: {
        level_dependent: 1.0,
        long_control: 0.6,
        burst_control: 0.4,
        lane_aggressive: 0.7,
        lane_roam: 0.3,
        hunt_pickoff: 0.7,
        flexible: 0.3
      },
      difficulty: "hard" 
    },
    { 
      name: "Earthshaker", 
      tags: {
        needs_blink: 1.0,
        long_control: 1.0,
        lane_passive: 1.0,
        teamfight_5v5: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Elder Titan", 
      tags: {
        needs_farm_scaling: 1.0,
        burst_control: 1.0,
        lane_passive: 0.7,
        lane_aggressive: 0.3,
        teamfight_5v5: 1.0
      },
      difficulty: "medium" 
    },
    { 
      name: "Huskar", 
      tags: {
        level_dependent: 0.3,
        needs_farm_scaling: 0.7,
        high_damage: 1.0,
        lane_aggressive: 1.0,
        hunt_pickoff: 0.8,
        flexible: 0.2
      },
      difficulty: "medium" 
    },
    { 
      name: "Kunkka", 
      tags: {
        level_dependent: 0.7,
        needs_farm_scaling: 0.3,
        long_control: 1.0,
        lane_passive: 0.6,
        lane_aggressive: 0.4,
        teamfight_5v5: 0.8,
        flexible: 0.2
      },
      difficulty: "medium" 
    },
    { 
      name: "Largo", 
      tags: {
        level_dependent: 0.6,
        needs_farm_scaling: 0.4,
        zone_control: 1.0,
        lane_passive: 0.4,
        lane_aggressive: 0.6,
        teamfight_5v5: 1.0
      },
      difficulty: "hard" 
    },
    { 
      name: "Legion Commander", 
      tags: {
        needs_blink: 1.0,
        burst_control: 0.5,
        long_control: 0.5,
        lane_aggressive: 0.7,
        lane_push_jungle: 0.3,
        hunt_pickoff: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Lycan", 
      tags: {
        needs_farm_scaling: 1.0,
        high_damage: 1.0,
        lane_push_jungle: 1.0,
        splitpush: 1.0
      },
      difficulty: "hard" 
    },
    { 
      name: "Mars", 
      tags: {
        level_dependent: 0.4,
        needs_blink: 0.6,
        long_control: 1.0,
        lane_aggressive: 0.7,
        lane_passive: 0.3,
        teamfight_5v5: 1.0
      },
      difficulty: "medium" 
    },
    { 
      name: "Night Stalker", 
      tags: {
        level_dependent: 0.6,
        needs_blink: 0.4,
        burst_control: 1.0,
        lane_roam: 1.0,
        hunt_pickoff: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Omniknight", 
      tags: {
        needs_farm_scaling: 1.0,
        high_damage: 1.0,
        lane_passive: 0.6,
        lane_aggressive: 0.4,
        teamfight_5v5: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Phoenix", 
      tags: {
        level_dependent: 1.0,
        zone_control: 1.0,
        lane_aggressive: 0.7,
        lane_passive: 0.3,
        teamfight_5v5: 1.0
      },
      difficulty: "medium" 
    },
    { 
      name: "Primal Beast", 
      tags: {
        level_dependent: 1.0,
        long_control: 0.4,
        burst_control: 0.6,
        lane_aggressive: 1.0,
        teamfight_5v5: 0.8,
        flexible: 0.2
      },
      difficulty: "medium" 
    },
    { 
      name: "Pudge", 
      tags: {
        needs_blink: 0.6,
        needs_farm_scaling: 0.4,
        burst_control: 1.0,
        lane_passive: 0.6,
        lane_aggressive: 0.4,
        hunt_pickoff: 1.0
      },
      difficulty: "medium" 
    },
    { 
      name: "Slardar", 
      tags: {
        needs_blink: 1.0,
        burst_control: 1.0,
        lane_passive: 0.6,
        lane_aggressive: 0.4,
        hunt_pickoff: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Spirit Breaker", 
      tags: {
        level_dependent: 1.0,
        burst_control: 1.0,
        lane_roam: 1.0,
        hunt_pickoff: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Tidehunter", 
      tags: {
        needs_blink: 1.0,
        long_control: 1.0,
        lane_passive: 0.6,
        lane_aggressive: 0.4,
        teamfight_5v5: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Timbersaw", 
      tags: {
        needs_tank_items: 0.3,
        level_dependent: 0.7,
        high_damage: 1.0,
        lane_aggressive: 1.0,
        flexible: 1.0
      },
      difficulty: "medium" 
    },
    { 
      name: "Tiny", 
      tags: {
        needs_blink: 1.0,
        burst_control: 1.0,
        lane_passive: 0.7,
        lane_aggressive: 0.3,
        teamfight_5v5: 0.8,
        flexible: 0.2
      },
      difficulty: "easy" 
    },
    { 
      name: "Underlord", 
      tags: {
        needs_tank_items: 1.0,
        zone_control: 1.0,
        lane_aggressive: 1.0,
        flexible: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Undying", 
      tags: {
        level_dependent: 1.0,
        zone_control: 1.0,
        lane_aggressive: 1.0,
        teamfight_5v5: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Wraith King", 
      tags: {
        needs_farm_scaling: 1.0,
        burst_control: 0.2,
        high_damage: 0.8,
        lane_passive: 0.6,
        lane_aggressive: 0.4,
        flexible: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Broodmother", 
      tags: {
        needs_farm_scaling: 1.0,
        high_damage: 1.0,
        lane_push_jungle: 1.0,
        splitpush: 1.0
      },
      difficulty: "hard" 
    },
    { 
      name: "Razor", 
      tags: {
        needs_tank_items: 0.6,
        needs_farm_scaling: 0.4,
        high_damage: 1.0,
        lane_aggressive: 0.8,
        lane_passive: 0.2,
        teamfight_5v5: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Viper", 
      tags: {
        level_dependent: 0.3,
        needs_farm_scaling: 0.7,
        zone_control: 1.0,
        lane_aggressive: 0.7,
        lane_push_jungle: 0.3,
        flexible: 0.8,
        teamfight_5v5: 0.2
      },
      difficulty: "easy" 
    },
    { 
      name: "Dark Seer", 
      tags: {
        level_dependent: 0.4,
        needs_tank_items: 0.6,
        zone_control: 1.0,
        lane_passive: 0.7,
        lane_push_jungle: 0.3,
        teamfight_5v5: 1.0
      },
      difficulty: "medium" 
    },
    { 
      name: "Necrophos", 
      tags: {
        needs_farm_scaling: 1.0,
        high_damage: 1.0,
        lane_passive: 0.6,
        lane_aggressive: 0.4,
        flexible: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Abaddon", 
      tags: {
        needs_farm_scaling: 1.0,
        high_damage: 1.0,
        lane_passive: 0.6,
        lane_aggressive: 0.4,
        flexible: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Beastmaster", 
      tags: {
        needs_blink: 0.7,
        needs_farm_scaling: 0.3,
        long_control: 1.0,
        lane_push_jungle: 1.0,
        splitpush: 0.7,
        flexible: 0.3
      },
      difficulty: "medium" 
    },
    { 
      name: "Batrider", 
      tags: {
        needs_blink: 1.0,
        burst_control: 1.0,
        lane_aggressive: 1.0,
        hunt_pickoff: 1.0
      },
      difficulty: "medium" 
    },
    { 
      name: "Brewmaster", 
      tags: {
        needs_farm_scaling: 1.0,
        long_control: 0.6,
        high_damage: 0.4,
        lane_passive: 0.7,
        lane_aggressive: 0.3,
        flexible: 1.0
      },
      difficulty: "hard" 
    },
    { 
      name: "Death Prophet", 
      tags: {
        level_dependent: 0.7,
        needs_farm_scaling: 0.3,
        zone_control: 0.3,
        high_damage: 0.7,
        lane_aggressive: 0.6,
        lane_roam: 0.4,
        flexible: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Enigma", 
      tags: {
        needs_blink: 1.0,
        long_control: 1.0,
        lane_passive: 0.7,
        lane_push_jungle: 0.3,
        teamfight_5v5: 1.0
      },
      difficulty: "medium" 
    },
    { 
      name: "Magnus", 
      tags: {
        needs_blink: 1.0,
        long_control: 1.0,
        lane_passive: 0.7,
        lane_aggressive: 0.3,
        teamfight_5v5: 1.0
      },
      difficulty: "medium" 
    },
    { 
      name: "Marci", 
      tags: {
        level_dependent: 0.7,
        needs_farm_scaling: 0.3,
        burst_control: 1.0,
        lane_aggressive: 0.8,
        lane_passive: 0.2,
        hunt_pickoff: 0.7,
        flexible: 0.3
      },
      difficulty: "medium" 
    },
    { 
      name: "Sand King", 
      tags: {
        needs_blink: 1.0,
        long_control: 0.7,
        burst_control: 0.3,
        lane_passive: 0.6,
        lane_push_jungle: 0.4,
        teamfight_5v5: 1.0
      },
      difficulty: "easy" 
    },
    { 
      name: "Pangolier", 
      tags: {
        level_dependent: 0.4,
        needs_farm_scaling: 0.6,
        burst_control: 0.4,
        zone_control: 0.6,
        lane_aggressive: 0.6,
        lane_passive: 0.4,
        flexible: 1.0
      },
      difficulty: "medium" 
    },
    { 
      name: "Visage", 
      tags: {
        level_dependent: 1.0,
        high_damage: 1.0,
        lane_aggressive: 0.8,
        lane_passive: 0.2,
        flexible: 1.0
      },
      difficulty: "hard" 
    },
    { 
      name: "Windranger", 
      tags: {
        needs_farm_scaling: 1.0,
        burst_control: 0.3,
        high_damage: 0.7,
        lane_aggressive: 0.4,
        lane_passive: 0.6,
        flexible: 1.0
      },
      difficulty: "medium" 
    }
  ]
};
//heroes-pos45.js — Данные для Pos 4 и Pos 5

window.heroPos4Data = {
  questions: [
    {
      id: 'dependence',
      question: 'От чего ты больше хочешь зависеть в игре?',
      answers: [
        { text: 'От уровня и КД кнопок.', icon: 'ph-lightning', tags: ['from_level'] },
        { text: 'От утилити-предметов.', icon: 'ph-package', tags: ['from_items'] }
      ]
    },
    {
      id: 'fight_style',
      question: 'Что ты больше всего хочешь делать в драках?',
      answers: [
        { text: 'Давать контроль (стан, сайленс, замедление).', icon: 'ph-lock', tags: ['from_control'] },
        { text: 'Наносить урон (нюки, магический прокаст).', icon: 'ph-lightning', tags: ['from_damage'] },
        { text: 'Сейвить и баффать союзников (хилл, щит, сейв).', icon: 'ph-hand-heart', tags: ['from_save'] }
      ]
    },
    {
      id: 'difficulty',
      question: 'Тебе нравятся сложные герои?',
      answers: [
        { text: 'Да, мне нравятся сложные герои.', icon: 'ph-fire', tags: ['hard'] },
        { text: 'Нет, мне не нравятся сложные герои.', icon: 'ph-leaf', tags: ['easy'] }
      ]
    },
    {
      id: 'role_in_fight',
      question: 'Какую роль тебе больше всего хочется выполнять в драках?',
      answers: [
        { text: 'Инициация — первым врываться и начинать файты.', icon: 'ph-rocket-launch', tags: ['from_initiation'] },
        { text: 'Контр-инициация — ждать врыва врага и переворачивать файт.', icon: 'ph-shield-check', tags: ['from_counterinitiation'] },
        { text: 'Позиционная игра — держать позицию и откидывать кнопки.', icon: 'ph-anchor', tags: ['from_position'] }
      ]
    }
  ],

  heroes: [
    // Pos 4 герои — значения из heroesData[4]
    { name: "Lion", tags: { from_level: 1, from_control: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Shadow Shaman", tags: { from_level: 1, from_control: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Lich", tags: { from_level: 1, from_control: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Hoodwink", tags: { from_level: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Vengeful Spirit", tags: { from_items: 1, from_control: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Jakiro", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Witch Doctor", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Ogre Magi", tags: { from_items: 1, from_control: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Tusk", tags: { from_items: 1, from_control: 1, hard: 1, from_initiation: 1 }, difficulty: "hard" },
    { name: "Pudge", tags: { from_level: 1, from_control: 1, hard: 1, from_initiation: 1 }, difficulty: "hard" },
    { name: "Warlock", tags: { from_level: 1, from_damage: 1, easy: 1, from_counterinitiation: 1 }, difficulty: "easy" },
    { name: "Crystal Maiden", tags: { from_level: 1, from_control: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Dazzle", tags: { from_items: 1, from_save: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Skywrath Mage", tags: { from_level: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Ancient Apparition", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Rubick", tags: { from_level: 1, from_control: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Techies", tags: { from_level: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Silencer", tags: { from_level: 1, from_damage: 1, easy: 1, from_counterinitiation: 1 }, difficulty: "easy" },
    { name: "Venomancer", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Io", tags: { from_items: 1, from_save: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" },
    { name: "Treant Protector", tags: { from_items: 1, from_control: 1, easy: 1, from_counterinitiation: 1 }, difficulty: "easy" },
    { name: "Snapfire", tags: { from_level: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Undying", tags: { from_level: 1, from_control: 1, easy: 1, from_counterinitiation: 1 }, difficulty: "easy" },
    { name: "Oracle", tags: { from_items: 1, from_save: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" },
    { name: "Winter Wyvern", tags: { from_items: 1, from_save: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Grimstroke", tags: { from_level: 1, from_control: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" },
    { name: "Zeus", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Ringmaster", tags: { from_items: 1, from_control: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" },
    { name: "Dark Willow", tags: { from_level: 1, from_control: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Windranger", tags: { from_level: 1, from_damage: 1, hard: 1, from_initiation: 1 }, difficulty: "hard" },
    { name: "Invoker", tags: { from_level: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Shadow Demon", tags: { from_level: 1, from_save: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" },
    { name: "Pugna", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Clockwerk", tags: { from_level: 1, from_control: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Weaver", tags: { from_items: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Sniper", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Magnus", tags: { from_items: 1, from_control: 1, hard: 1, from_initiation: 1 }, difficulty: "hard" },
    { name: "Bane", tags: { from_level: 1, from_control: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Mirana", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Omniknight", tags: { from_items: 1, from_save: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Nature's Prophet", tags: { from_items: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Spirit Breaker", tags: { from_level: 1, from_control: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Phoenix", tags: { from_level: 1, from_damage: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" },
    { name: "Abaddon", tags: { from_items: 1, from_save: 1, easy: 1, from_counterinitiation: 1 }, difficulty: "easy" },
    { name: "Marci", tags: { from_items: 1, from_save: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Bounty Hunter", tags: { from_items: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Nyx Assassin", tags: { from_level: 1, from_control: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Enchantress", tags: { from_items: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Chen", tags: { from_items: 1, from_save: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Earthshaker", tags: { from_items: 1, from_control: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Tiny", tags: { from_items: 1, from_control: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Earth Spirit", tags: { from_level: 1, from_control: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" },
    { name: "Keeper of the Light", tags: { from_items: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Batrider", tags: { from_items: 1, from_control: 1, hard: 1, from_initiation: 1 }, difficulty: "hard" },
    { name: "Elder Titan", tags: { from_items: 1, from_control: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" },
    { name: "Disruptor", tags: { from_level: 1, from_control: 1, easy: 1, from_counterinitiation: 1 }, difficulty: "easy" },
    { name: "Largo", tags: { from_level: 1, from_save: 1, hard: 1, from_position: 1 }, difficulty: "hard" }
  ]
};


// POS 5 — используем те же вопросы, но свой список героев
window.heroPos5Data = {
  questions: window.heroPos4Data.questions,

  heroes: [
    { name: "Lion", tags: { from_level: 1, from_control: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Witch Doctor", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Shadow Shaman", tags: { from_level: 1, from_control: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Jakiro", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Crystal Maiden", tags: { from_level: 1, from_control: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Lich", tags: { from_level: 1, from_control: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Ogre Magi", tags: { from_items: 1, from_control: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Warlock", tags: { from_level: 1, from_damage: 1, easy: 1, from_counterinitiation: 1 }, difficulty: "easy" },
    { name: "Venomancer", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Skywrath Mage", tags: { from_level: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Silencer", tags: { from_level: 1, from_damage: 1, easy: 1, from_counterinitiation: 1 }, difficulty: "easy" },
    { name: "Techies", tags: { from_level: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Ancient Apparition", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Zeus", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Dazzle", tags: { from_items: 1, from_save: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Windranger", tags: { from_level: 1, from_damage: 1, hard: 1, from_initiation: 1 }, difficulty: "hard" },
    { name: "Vengeful Spirit", tags: { from_items: 1, from_control: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Hoodwink", tags: { from_level: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Undying", tags: { from_level: 1, from_control: 1, easy: 1, from_counterinitiation: 1 }, difficulty: "easy" },
    { name: "Snapfire", tags: { from_level: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Winter Wyvern", tags: { from_items: 1, from_save: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Dark Willow", tags: { from_level: 1, from_control: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Treant Protector", tags: { from_items: 1, from_control: 1, easy: 1, from_counterinitiation: 1 }, difficulty: "easy" },
    { name: "Grimstroke", tags: { from_level: 1, from_control: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" },
    { name: "Tusk", tags: { from_items: 1, from_control: 1, hard: 1, from_initiation: 1 }, difficulty: "hard" },
    { name: "Io", tags: { from_items: 1, from_save: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" },
    { name: "Nature's Prophet", tags: { from_items: 1, from_damage: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Clockwerk", tags: { from_level: 1, from_control: 1, easy: 1, from_initiation: 1 }, difficulty: "easy" },
    { name: "Pugna", tags: { from_level: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Ringmaster", tags: { from_items: 1, from_control: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" },
    { name: "Shadow Demon", tags: { from_level: 1, from_save: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" },
    { name: "Bane", tags: { from_level: 1, from_control: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Abaddon", tags: { from_items: 1, from_save: 1, easy: 1, from_counterinitiation: 1 }, difficulty: "easy" },
    { name: "Omniknight", tags: { from_items: 1, from_save: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Enchantress", tags: { from_items: 1, from_damage: 1, easy: 1, from_position: 1 }, difficulty: "easy" },
    { name: "Disruptor", tags: { from_level: 1, from_control: 1, easy: 1, from_counterinitiation: 1 }, difficulty: "easy" },
    { name: "Largo", tags: { from_level: 1, from_save: 1, hard: 1, from_position: 1 }, difficulty: "hard" },
    { name: "Oracle", tags: { from_items: 1, from_save: 1, hard: 1, from_counterinitiation: 1 }, difficulty: "hard" }
  ]
};
