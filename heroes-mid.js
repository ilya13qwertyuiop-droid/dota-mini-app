// data/heroes-mid.js — Данные для Pos 2 (Мидер)
window.heroMidData = {
  questions: [
    {
      id: 'gank_source',
      question: 'От чего в основном зависит твой ганг‑потенциал на миде?',
      answers: [
        {
          text: '⚡ От уровня и рун (получил 6, взял руну и пошёл гангать).',
          tags: ['gank_level_rune']
        },
        {
          text: '🛠 От ключевого предмета (блинк, аганим и т.п.).',
          tags: ['gank_item']
        }
      ]
    },
    {
      id: 'lane_style',
      question: 'Как ты хочешь стоять линию?',
      answers: [
        {
          text: '⚔️ Давить и пытаться убить оппонента.',
          tags: ['lane_pressure']
        },
        {
          text: '⚖️ Играть гибко: и фарм, и давление.',
          tags: ['lane_mixed']
        },
        {
          text: '🌾 Спокойно фармить, главное — не проиграть линию.',
          tags: ['lane_farm']
        }
      ]
    },
    {
      id: 'post_lane',
      question: 'Что ты хочешь делать после выхода с линии?',
      answers: [
        {
          text: '👥 Постоянно бегать и играть с командой.',
          tags: ['post_team_gank']
        },
        {
          text: '⚖️ Чередовать фарм и подключение к дракам.',
          tags: ['post_mix']
        },
        {
          text: '🌾 Больше фармить и пушить, файты если выгодно.',
          tags: ['post_farm_push']
        }
      ]
    },
    {
      id: 'difficulty',
      question: 'Насколько сложным может быть герой по механике?',
      answers: [
        {
          text: '🙂 Простой, минимум кнопок.',
          tags: ['difficulty_easy']
        },
        {
          text: '⚖️ Средний, без особого микро.',
          tags: ['difficulty_medium']
        },
        {
          text: '🎓 Сложный, люблю ломать пальцы.',
          tags: ['difficulty_hard']
        }
      ]
    },
    {
      id: 'fight_role',
      question: 'Какую роль ты хочешь выполнять в драках?',
      answers: [
        {
          text: '🚀 Инициатор — врываться первым.',
          tags: ['role_initiator']
        },
        {
          text: '💥 Бёрст — быстро убивать ключевую цель.',
          tags: ['role_burst']
        },
        {
          text: '🧊 Контроль/длительный урон из позиции.',
          tags: ['role_control']
        }
      ]
    }
  ],
  
  heroes: [
    { name: "Earth Spirit", tags: ["gank_level_rune","lane_pressure","post_team_gank","difficulty_hard","role_initiator"], difficulty: "hard" },
    { name: "Earthshaker", tags: ["gank_item","lane_mixed","post_team_gank","difficulty_easy","role_initiator","role_control"], difficulty: "easy" },
    { name: "Huskar", tags: ["gank_item","lane_pressure","post_mix","difficulty_medium","role_burst","role_initiator"], difficulty: "medium" },
    { name: "Dragon Knight", tags: ["gank_item","lane_farm","post_farm_push","difficulty_easy","role_initiator","role_control","role_burst"], difficulty: "easy" },
    { name: "Primal Beast", tags: ["gank_level_rune","lane_pressure","post_team_gank","difficulty_medium","role_initiator","role_burst"], difficulty: "medium" },
    { name: "Slardar", tags: ["gank_item","lane_mixed","post_team_gank","difficulty_easy","role_initiator"], difficulty: "easy" },
    { name: "Timbersaw", tags: ["gank_level_rune","lane_pressure","post_farm_push","difficulty_medium","role_burst","role_initiator"], difficulty: "medium" },
    { name: "Tiny", tags: ["gank_item","lane_mixed","post_team_gank","difficulty_easy","role_initiator","role_burst"], difficulty: "easy" },
    { name: "Broodmother", tags: ["gank_item","lane_farm","post_farm_push","difficulty_hard","role_burst"], difficulty: "hard" },
    { name: "Clinkz", tags: ["gank_item","lane_farm","post_farm_push","difficulty_easy","role_burst","role_control"], difficulty: "easy" },
    { name: "Kez", tags: ["gank_item","lane_mixed","post_mix","difficulty_hard","role_burst"], difficulty: "hard" },
    { name: "Lone Druid", tags: ["gank_item","lane_farm","post_farm_push","difficulty_hard","role_burst"], difficulty: "hard" },
    { name: "Meepo", tags: ["gank_item","lane_mixed","post_farm_push","difficulty_hard","role_burst"], difficulty: "hard" },
    { name: "Monkey King", tags: ["gank_level_rune","lane_pressure","post_mix","difficulty_medium","role_initiator","role_burst"], difficulty: "medium" },
    { name: "Morphling", tags: ["gank_item","lane_farm","post_farm_push","difficulty_hard","role_burst"], difficulty: "hard" },
    { name: "Riki", tags: ["gank_item","lane_farm","post_team_gank","difficulty_easy","role_burst","role_control"], difficulty: "easy" },
    { name: "Shadow Fiend", tags: ["gank_level_rune","lane_pressure","post_mix","difficulty_medium","role_burst"], difficulty: "medium" },
    { name: "Sniper", tags: ["gank_item","lane_farm","post_farm_push","difficulty_easy","role_control"], difficulty: "easy" },
    { name: "Templar Assassin", tags: ["gank_item","lane_mixed","post_mix","difficulty_medium","role_burst"], difficulty: "medium" },
    { name: "Viper", tags: ["gank_level_rune","lane_pressure","post_mix","difficulty_easy","role_control"], difficulty: "easy" },
    { name: "Invoker", tags: ["gank_item","lane_mixed","post_mix","difficulty_hard","role_control","role_burst"], difficulty: "hard" },
    { name: "Keeper of the Light", tags: ["gank_item","lane_mixed","post_team_gank","difficulty_medium","role_control"], difficulty: "medium" },
    { name: "Leshrac", tags: ["gank_item","lane_pressure","post_team_gank","difficulty_easy","role_burst"], difficulty: "easy" },
    { name: "Lina", tags: ["gank_level_rune","lane_pressure","post_mix","difficulty_easy","role_burst"], difficulty: "easy" },
    { name: "Necrophos", tags: ["gank_level_rune","lane_farm","post_mix","difficulty_easy","role_control"], difficulty: "easy" },
    { name: "Arc Warden", tags: ["gank_item","lane_farm","post_farm_push","difficulty_hard","role_burst","role_control"], difficulty: "hard" },
    { name: "Beastmaster", tags: ["gank_item","lane_pressure","post_mix","difficulty_hard","role_initiator","role_control"], difficulty: "hard" },
    { name: "Death Prophet", tags: ["gank_level_rune","lane_pressure","post_team_gank","difficulty_easy","role_burst","role_control"], difficulty: "easy" },
    { name: "Magnus", tags: ["gank_item","lane_mixed","post_team_gank","difficulty_medium","role_initiator","role_control"], difficulty: "medium" },
    { name: "Marci", tags: ["gank_level_rune","lane_mixed","post_team_gank","difficulty_medium","role_initiator","role_burst"], difficulty: "medium" },
    { name: "Nature's Prophet", tags: ["gank_level_rune","lane_farm","post_farm_push","difficulty_medium","role_burst","role_control"], difficulty: "medium" },
    { name: "Nyx Assassin", tags: ["gank_level_rune","lane_mixed","post_team_gank","difficulty_easy","role_burst"], difficulty: "easy" },
    { name: "Sand King", tags: ["gank_item","lane_mixed","post_mix","difficulty_easy","role_initiator","role_burst"], difficulty: "easy" },
    { name: "Void Spirit", tags: ["gank_level_rune","lane_mixed","post_mix","difficulty_medium","role_initiator","role_burst"], difficulty: "medium" },
    { name: "Visage", tags: ["gank_item","lane_mixed","post_mix","difficulty_hard","role_burst","role_control"], difficulty: "hard" },
    { name: "Puck", tags: ["gank_level_rune","lane_mixed","post_team_gank","difficulty_hard","role_initiator","role_control","role_burst"], difficulty: "hard" },
    { name: "Queen of Pain", tags: ["gank_level_rune","lane_pressure","post_team_gank","difficulty_easy","role_burst"], difficulty: "easy" },
    { name: "Rubick", tags: ["gank_level_rune","lane_mixed","post_mix","difficulty_hard","role_control","role_burst"], difficulty: "hard" },
    { name: "Skywrath Mage", tags: ["gank_level_rune","lane_pressure","post_team_gank","difficulty_easy","role_burst"], difficulty: "easy" },
    { name: "Storm Spirit", tags: ["gank_item","lane_mixed","post_mix","difficulty_medium","role_initiator","role_burst"], difficulty: "medium" },
    { name: "Tinker", tags: ["gank_item","lane_farm","post_farm_push","difficulty_hard","role_burst","role_control"], difficulty: "hard" },
    { name: "Zeus", tags: ["gank_level_rune","lane_farm","post_mix","difficulty_easy","role_burst","role_control"], difficulty: "easy" }
  ]
};
