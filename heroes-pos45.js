//heroes-pos45.js — Данные для Pos 4 и Pos 5

window.heroPos4Data = {
  questions: [
    {
      id: 'dependence',
      question: 'От чего ты больше хочешь зависеть в игре?',
      answers: [
        { text: '⚡ От уровня и КД кнопок.', tags: ['from_level'] },
        { text: '🔧 От утилити-предметов.', tags: ['from_items'] }
      ]
    },
    {
      id: 'fight_style',
      question: 'Что ты больше всего хочешь делать в драках?',
      answers: [
        { text: '🧊 Давать контроль (стан, сайленс, замедление).', tags: ['from_control'] },
        { text: '💥 Наносить урон (нюки, магический прокаст).', tags: ['from_damage'] },
        { text: '💚 Сейвить и баффать союзников (хилл, щит, сейв).', tags: ['from_save'] }
      ]
    },
    {
      id: 'difficulty',
      question: 'Тебе нравятся сложные герои?',
      answers: [
        { text: '🎓 Да, мне нравятся сложные герои.', tags: ['hard'] },
        { text: '😊 Нет, мне не нравятся сложные герои.', tags: ['easy'] }
      ]
    },
    {
      id: 'role_in_fight',
      question: 'Какую роль тебе больше всего хочется выполнять в драках?',
      answers: [
        { text: '🚀 Инициация — первым врываться и начинать файты.', tags: ['from_initiation'] },
        { text: '🛡️ Контр-инициация — ждать врыва врага и переворачивать файт.', tags: ['from_counterinitiation'] },
        { text: '🎯 Позиционная игра — держать позицию и откидывать кнопки.', tags: ['from_position'] }
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
