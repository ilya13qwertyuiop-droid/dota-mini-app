// data/heroes-offlane.js — Данные для Pos 3 (Хардлейнер)
window.heroOfflaneData = {
  questions: [
    {
      id: 'hero_priority',
      question: 'Что важнее всего для твоего героя?',
      answers: [
        {
          text: '🚀 Ключевой предмет для инициации',
          tags: ['needs_blink']
        },
        {
          text: '🛡️ Предметы на стойкость',
          tags: ['needs_tank_items']
        },
        {
          text: '⚡ Уровень и способности — сильный с 6-7 уровня, предметы вторичны',
          tags: ['level_dependent']
        },
        {
          text: '🌾 Фарм для масштабирования — нужны дорогие предметы',
          tags: ['needs_farm_scaling']
        }
      ]
    },
    {
      id: 'control_type',
      question: 'Какой тип контроля тебе нужен?',
      answers: [
        {
          text: '🧊 Длительный контроль — долго держу врагов в стане',
          tags: ['long_control']
        },
        {
          text: '⚡ Быстрый контроль — короткие станы + урон',
          tags: ['burst_control']
        },
        {
          text: '🌀 Зональный контроль — замедления/сайленсы, ограничиваю пространство',
          tags: ['zone_control']
        },
        {
          text: '🎯 Без сильного контроля — давлю уроном',
          tags: ['high_damage']
        }
      ]
    },
    {
      id: 'lane_style',
      question: 'Как ты играешь первые 10 минут?',
      answers: [
        {
          text: '💪 Агрессивно давлю керри, хочу убивать на линии',
          tags: ['lane_aggressive']
        },
        {
          text: '🛡️ Пассивно фармлю/выживаю до 6 уровня',
          tags: ['lane_passive']
        },
        {
          text: '🌾 Быстро пушу линию и иду в лес',
          tags: ['lane_push_jungle']
        },
        {
          text: '🎯 Активно роумлю после 6 уровня',
          tags: ['lane_roam']
        }
      ]
    },
    {
      id: 'post_lane',
      question: 'Твой стиль после 15 минуты?',
      answers: [
        {
          text: '👥 Играю с командой 5v5',
          tags: ['teamfight_5v5']
        },
        {
          text: '🗺️ Хожу по разным лайнам — сплит-пушу',
          tags: ['splitpush']
        },
        {
          text: '🎯 Охочусь за одиночными героями на карте',
          tags: ['hunt_pickoff']
        },
        {
          text: '🔄 Гибкий стиль — комбинирую драки, фарм и давление',
          tags: ['flexible']
        }
      ]
    },
    {
      id: 'difficulty',
      question: 'Какая сложность героя тебе подходит?',
      answers: [
        {
          text: '😊 Простой — понятные способности, минимум микро',
          tags: ['easy']
        },
        {
          text: '⚖️ Средний — нужно понимать тайминги и позиционирование',
          tags: ['medium']
        },
        {
          text: '🎓 Сложный — люблю ломать пальцы',
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
