        
        // --- Telegram WebApp user info + init ---
        const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

        let TELEGRAM_USER_ID = null;

        if (tg) {
            tg.ready();
            tg.expand();

            if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
                TELEGRAM_USER_ID = tg.initDataUnsafe.user.id; // Telegram user_id [web:62][web:59]
            }
        }
        // --- Проверка подписки через backend ---
        async function checkSubscription() {
            if (!TELEGRAM_USER_ID) {
                console.warn('No Telegram user id, denying by default');
                return false;
            }

            try {
                const resp = await fetch('http://62.171.144.53:8000/api/check-subscription', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ user_id: TELEGRAM_USER_ID }),
                });

                if (!resp.ok) {
                    console.error('Subscription check failed', resp.status);
                    return false;
                }

                const data = await resp.json(); // { allowed: true/false } [web:189]
                return !!data.allowed;
            } catch (e) {
                console.error('Subscription check error', e);
                return false;
            }
        }

        async function initSubscriptionGuard() {
            const overlay = document.getElementById('subscription-overlay');
            const retryBtn = document.getElementById('subscription-retry');

            if (!overlay) {
                console.warn('subscription-overlay not found in DOM');
                return;
            }

            async function runCheck() {
                const allowed = await checkSubscription();
                if (allowed) {
                    overlay.style.display = 'none';
                } else {
                    overlay.style.display = 'flex';
                }
            }

            if (retryBtn) {
                retryBtn.addEventListener('click', () => {
                    runCheck();
                });
            }

            runCheck();
        }

        // ========== КВИЗ ПО ПОЗИЦИЯМ ==========
        const quizData = [
            {
                question: "От каких моментов в игре ты получаешь максимальное удовольствие?",
                answers: [
                    {
                        text: "💰 Когда я вижу, что прогрессирую по золоту быстрее, чем вражеские герои",
                        scores: { pos1: 3, pos2: 2, pos3: 1, pos4: 1, pos5: 1 }
                    },
                    {
                        text: "🔪 Когда я один в правильный момент поймал и стёр врага за пару секунд",
                        scores: { pos1: 2, pos2: 3, pos3: 1, pos4: 1, pos5: 1 }
                    },
                    {
                        text: "⚔️ Когда я первый прыгаю в драку и закрываю вражеских героев",
                        scores: { pos1: 1, pos2: 2, pos3: 3, pos4: 2, pos5: 1 }
                    },
                    {
                        text: "🤝 Когда моя помощь спасает союзников в критический момент",
                        scores: { pos1: 1, pos2: 1, pos3: 1, pos4: 3, pos5: 3 }
                    }
                ]
            },
            {
                question: "Первые 10 минут игры. Что ты чаще всего делаешь?",
                answers: [
                    {
                        text: "🌾 Сосредотачиваюсь на добивании крипов и стараюсь максимально эффективно фармить",
                        scores: { pos1: 3, pos2: 2, pos3: 2, pos4: 0, pos5: 0 }
                    },
                    {
                        text: "⚖️ Хочу переиграть оппонента на линии и начать двигаться по карте",
                        scores: { pos1: 1, pos2: 3, pos3: 2, pos4: 1, pos5: 1 }
                    },
                    {
                        text: "⚔️ Ищу возможности для агрессии на линии и стараюсь доминировать",
                        scores: { pos1: 1, pos2: 2, pos3: 3, pos4: 2, pos5: 2 }
                    },
                    {
                        text: "🗺️ Помогаю на линиях — даю тп при необходимости, контролирую руны/вижн",
                        scores: { pos1: 0, pos2: 1, pos3: 0, pos4: 2, pos5: 3 }
                    }
                ]
            },
            {
                question: "Видишь, что враги начали драку на карте. Как ты реагируешь?",
                answers: [
                    {
                        text: "📊 Оцениваю выгоду. Если не выгодно, продолжаю фармить или сплит-пушу",
                        scores: { pos1: 3, pos2: 1, pos3: 1, pos4: 0, pos5: 0 }
                    },
                    {
                        text: "⚔️ Сразу даю ТП, чтобы помочь команде",
                        scores: { pos1: 1, pos2: 1, pos3: 1, pos4: 3, pos5: 3 }
                    },
                    {
                        text: "🎯 Пытаюсь 'выключить' опасного вражеского героя",
                        scores: { pos1: 1, pos2: 2, pos3: 3, pos4: 2, pos5: 1 }
                    },
                    {
                        text: "💚 Держу позицию, чтобы грамотно раскинуть кнопки",
                        scores: { pos1: 3, pos2: 1, pos3: 1, pos4: 1, pos5: 3 }
                    }
                ]
            },
            {
                question: "Каких героев ты предпочитаешь?",
                answers: [
                    {
                        text: "💎 Героев, которые становятся сильными с дорогими предметами",
                        scores: { pos1: 3, pos2: 2, pos3: 1, pos4: 1, pos5: 1 }
                    },
                    {
                        text: "🎯 Героев с бёрст уроном — убил и ушёл",
                        scores: { pos1: 1, pos2: 3, pos3: 1, pos4: 1, pos5: 0 }
                    },
                    {
                        text: "🛡️ Героев, которые выдерживают много урона",
                        scores: { pos1: 1, pos2: 1, pos3: 3, pos4: 2, pos5: 1 }
                    },
                    {
                        text: "🤝 Героев с полезными способностями для команды (станы, сейвы, хил)",
                        scores: { pos1: 0, pos2: 0, pos3: 1, pos4: 3, pos5: 3 }
                    }
                ]
            },
            {
                question: "На что ты обращаешь внимание в конце игры (статистика)?",
                answers: [
                    {
                        text: "📊 Золото/Фраги/Добито крипов",
                        scores: { pos1: 3, pos2: 2, pos3: 2, pos4: 1, pos5: 1 }
                    },
                    {
                        text: "⚔️ Фраги и нанесённый урон",
                        scores: { pos1: 3, pos2: 3, pos3: 1, pos4: 1, pos5: 1 }
                    },
                    {
                        text: "🎯 Количество контроля и впитанного урона",
                        scores: { pos1: 1, pos2: 1, pos3: 3, pos4: 2, pos5: 2 }
                    },
                    {
                        text: "💚 Количество расходников (варды, дасты), ассистов, лечения",
                        scores: { pos1: 0, pos2: 0, pos3: 0, pos4: 3, pos5: 3 }
                    }
                ]
            }
        ];


        const positionNames = {
            pos1: "Pos 1 — Керри",
            pos2: "Pos 2 — Мидер",
            pos3: "Pos 3 — Хардлейнер",
            pos4: "Pos 4 — Роумер",
            pos5: "Pos 5 — Фулл-саппорт"
        };


        const positionShortNames = {
            pos1: "Керри",
            pos2: "Мидер",
            pos3: "Хардлейнер",
            pos4: "Роумер",
            pos5: "Фулл-саппорт"
        };


        const positionStats = {
            "pos1_pos2": [
                { label: "Фарм", value: 95 },
                { label: "Мидгейм", value: 85 },
                { label: "Темп", value: 75 }
            ],
            "pos1_pos3": [
                { label: "Фарм", value: 90 },
                { label: "Фронт", value: 80 },
                { label: "Живучесть", value: 85 }
            ],
            "pos1_pos4": [
                { label: "Фарм", value: 85 },
                { label: "Роум", value: 70 },
                { label: "Агрессия", value: 75 }
            ],
            "pos1_pos5": [
                { label: "Фарм", value: 90 },
                { label: "Командность", value: 80 },
                { label: "Утилита", value: 70 }
            ],
            "pos2_pos1": [
                { label: "Линия", value: 85 },
                { label: "Лейт", value: 80 },
                { label: "Скалирование", value: 90 }
            ],
            "pos2_pos3": [
                { label: "Инициация", value: 85 },
                { label: "Фронт", value: 80 },
                { label: "Контроль", value: 90 }
            ],
            "pos2_pos4": [
                { label: "Роум", value: 90 },
                { label: "Мидгейм", value: 95 },
                { label: "Активность", value: 85 }
            ],
            "pos2_pos5": [
                { label: "Темп", value: 85 },
                { label: "Командность", value: 90 },
                { label: "Контроль карты", value: 75 }
            ],
            "pos3_pos1": [
                { label: "Фронт", value: 85 },
                { label: "Лейт", value: 80 },
                { label: "Давление", value: 75 }
            ],
            "pos3_pos2": [
                { label: "Линия", value: 90 },
                { label: "Агрессия", value: 95 },
                { label: "Прессинг", value: 85 }
            ],
            "pos3_pos4": [
                { label: "Роум", value: 80 },
                { label: "Пространство", value: 85 },
                { label: "Инициация", value: 90 }
            ],
            "pos3_pos5": [
                { label: "Фронт", value: 90 },
                { label: "Командность", value: 85 },
                { label: "Контроль", value: 80 }
            ],
            "pos4_pos1": [
                { label: "Роум", value: 85 },
                { label: "Фарм", value: 70 },
                { label: "Скалирование", value: 75 }
            ],
            "pos4_pos2": [
                { label: "Роум", value: 95 },
                { label: "Агрессия", value: 90 },
                { label: "Ганки", value: 85 }
            ],
            "pos4_pos3": [
                { label: "Фронт", value: 85 },
                { label: "Контроль", value: 90 },
                { label: "Танк", value: 80 }
            ],
            "pos4_pos5": [
                { label: "Вижен", value: 95 },
                { label: "Сейв", value: 90 },
                { label: "Командность", value: 95 }
            ],
            "pos5_pos1": [
                { label: "Вижен", value: 90 },
                { label: "Фарм", value: 65 },
                { label: "Лейт", value: 70 }
            ],
            "pos5_pos2": [
                { label: "Вижен", value: 95 },
                { label: "Роум", value: 85 },
                { label: "Темп", value: 80 }
            ],
            "pos5_pos3": [
                { label: "Фронт", value: 85 },
                { label: "Танк", value: 90 },
                { label: "Сейв", value: 85 }
            ],
            "pos5_pos4": [
                { label: "Вижен", value: 95 },
                { label: "Роум", value: 90 },
                { label: "Контроль", value: 85 }
            ]
        };


        const positionDescriptions = {
            "pos1_pos2": "Ты — керри, который не просто фармит до поздней игры, а начинает оказывать давление уже после первых ключевых предметов. В отличие от классических кэрри, ты умеешь читать карту и контролировать темп, выбирая момент, когда нужно включиться в драку, а когда продолжить развитие.\n\nТы не ждёшь 40-й минуты — ты влияешь на игру в мидгейме, сочетая эффективный фарм со способностью наказывать врагов за ошибки. Твоя сила в балансе между терпением и агрессией.",
            "pos1_pos3": "Ты — керри, который не боится первым входить в драку. Тебе нравится стоять на передовой и выдерживать фокус врагов, оставаясь при этом главным источником урона. Ты предпочитаешь прочных героев и готов собрать 1-2 защитных предмета, чтобы диктовать условия боя.\n\nВ отличие от «стеклянных» героев, ты сам создаёшь пространство для команды и контролируешь зону драки. Твоя игра — это сочетание живучести и разрушительной силы.",
            "pos1_pos4": "Ты — керри, который не сидит на одной линии 30 минут. После ключевых предметов ты активно двигаешься по карте, помогая в драках и создавая давление. Ты легко находишь баланс между личным развитием и участием в ключевых моментах игры.\n\nТебе подходят мобильные герои с возможностями для инициации или контроля. Твоя особенность — гибкость: ты не ждёшь, пока команда создаст тебе пространство, ты сам участвуешь в его создании.",
            "pos1_pos5": "Ты — редкий тип керри, который думает не только о своём фарме, но и о команде. Ты готов пожертвовать чем-то личным ради критичного момента: купить вард, если саппорт разорён, или дать TP для спасения союзника.\n\nТебе нравятся герои, которые дают команде не только урон, но и утилиту (ауры, AoE, контроль). Твоя сила — в умении балансировать между личным развитием и помощью команде, что делает тебя надёжным игроком.",
            "pos2_pos1": "Ты — мидер, который умеет не только доминировать на линии, но и масштабироваться в позднюю игру. В отличие от классических мидеров с пиком силы в середине игры, ты не торопишься закончить игру в мидгейме — ты строишь долгосрочное преимущество.\n\nТы предпочитаешь героев, которые остаются релевантными в любой стадии игры, и умеешь балансировать между активными действиями на карте и эффективным фармом. Твоя сила — в способности переходить от роли инициатора к роли главной ударной силы.",
            "pos2_pos3": "Ты — мидер, который любит открывать драки и контролировать пространство. Тебе нравятся прочные герои с возможностями для инициации, которые не боятся стоять на передовой. Ты не ждёшь, пока команда создаст условия — ты сам диктуешь темп.\n\nВ отличие от хрупких мидеров, ты готов собрать защитные предметы и первым врываться в драку, создавая хаос в рядах врага. Твоя игра — это сочетание агрессии, живучести и контроля над картой.",
            "pos2_pos4": "Ты — классический мидер, который не сидит на линии после получения ключевого уровня или предмета. Ты постоянно двигаешься по карте, создавая давление и помогая союзникам. Твоя сила — в способности читать игру и быть там, где решается её исход.\n\nТебе нравятся мобильные герои с высоким импактом в мидгейме. Ты понимаешь, что контроль карты и помощь союзникам важнее личной статистики, и умеешь превращать свою мобильность в победу команды.",
            "pos2_pos5": "Ты — редкий тип мидера, который думает не только о своём фарме и убийствах, но и о команде. Ты готов купить дополнительные варды, дать важные предметы союзникам или пожертвовать личным преимуществом ради победы.\n\nТебе нравятся герои с утилитой для команды — контролем, спасающими способностями или аурами. Твоя сила в зрелом подходе к игре: ты понимаешь, что победа команды важнее личной статистики.",
            "pos3_pos1": "Ты — офлейнер, который не просто создаёт пространство, но и сам превращается в серьёзную угрозу в поздней игре. Ты умеешь балансировать между своей основной ролью танка/инициатора и способностью наносить значительный урон.\n\nТебе нравятся герои, которые остаются релевантными на всех стадиях игры и могут вытягивать сложные матчи. Твоя сила — в умении быть одновременно прочным и опасным, что делает тебя сложной целью для врага.",
            "pos3_pos2": "Ты — офлейнер, который не просто выживает на сложной линии, а доминирует на ней. Ты активно давишь вражеского керри и быстро начинаешь двигаться по карте, создавая проблемы на всех линиях.\n\nТебе нравятся герои с высоким сольным потенциалом, способные убивать врагов один-на-один. Твоя игра — это чистая агрессия: ты создаёшь пространство не пассивным выживанием, а активным давлением.",
            "pos3_pos4": "Ты — офлейнер, который после получения ключевых предметов становится чрезвычайно активным на карте. Ты не сидишь на линии — ты двигаешься, создаёшь давление, помогаешь в драках и контролируешь пространство.\n\nТебе подходят мобильные герои-инициаторы с хорошим импактом. Твоя особенность — гибкость: ты одинаково комфортно чувствуешь себя как на передовой в драке, так и в роуме по карте.",
            "pos3_pos5": "Ты — офлейнер, который думает не только о своём фарме, но и о команде. Ты готов жертвовать личным преимуществом ради критичных моментов: купить важный предмет для инициации раньше, чем BKB, или умереть первым, чтобы союзники выжили.\n\nТебе нравятся герои с контролем и утилитой для команды. Твоя сила — в надёжности: союзники знают, что ты всегда будешь там, где нужно, и возьмёшь на себя удар.",
            "pos4_pos1": "Ты — саппорт, который умеет находить фарм даже в сложных условиях и превращать небольшое преимущество в значительную силу к поздней игре. Ты не просто ставишь варды — ты активно участвуешь в драках и можешь стать серьёзной угрозой.\n\nТебе подходят саппорты, которые хорошо масштабируются (Shadow Shaman, Jakiro, Warlock). Твоя особенность — ты не забываешь о собственном развитии, сохраняя баланс между поддержкой команды и личным ростом.",
            "pos4_pos2": "Ты — агрессивный роумер, который постоянно создаёт давление на карте. Ты не сидишь пассивно на линии — ты активно ищешь возможности для ганков и помогаешь команде захватывать контроль над игрой в ранней и средней стадии.\n\nТебе нравятся мобильные герои с высоким импактом (Earthshaker, Tusk, Spirit Breaker). Твоя игра — это постоянное движение, чтение карты и способность быть там, где решается исход драки.",
            "pos4_pos3": "Ты — прочный саппорт, который не боится стоять на передовой. Ты готов первым входить в драку, танковать урон и создавать пространство для команды. В отличие от хрупких роумеров, ты выдерживаешь фокус и контролируешь зону боя.\n\nТебе подходят танковые саппорты-инициаторы (Axe 4-ка, Clockwerk, Mars 4-ка). Твоя сила — в способности диктовать условия драки и брать на себя удар.",
            "pos4_pos5": "Ты — универсальный саппорт, который одинаково хорошо справляется с ролью роумера и классического саппорта. Ты умеешь ставить варды в критических точках, спасать союзников и создавать давление на карте.\n\nТебе подходят герои с гибким набором способностей (Rubick, Snapfire, Phoenix). Твоя сила — в адаптивности: ты можешь подстроиться под любую ситуацию и всегда найдёшь способ помочь команде.",
            "pos5_pos1": "Ты — саппорт, который умеет находить фарм даже после покупки вардов. Ты понимаешь важность поддержки команды, но не забываешь о собственном развитии, что позволяет тебе оставаться полезным на всех стадиях игры.\n\nТебе подходят саппорты с потенциалом роста (Crystal Maiden с аганимом, Warlock, Witch Doctor). Твоя особенность — умение балансировать между жертвенностью ради команды и собственным прогрессом.",
            "pos5_pos2": "Ты — активный фулл-саппорт, который не просто стоит за керри на линии. Ты активно двигаешься по карте, помогаешь мидеру, контролируешь руны и создаёшь давление.\n\nТебе нравятся герои с высоким импактом в раннем и среднем гейме (Vengeful Spirit, Jakiro, Shadow Shaman). Твоя сила — в способности влиять на темп игры через правильное позиционирование и тайминги.",
            "pos5_pos3": "Ты — саппорт, который не боится стоять на передовой. Ты готов первым входить в драку рядом с офлейнером, танковать урон и создавать хаос в рядах врага своими способностями.\n\nТебе подходят прочные саппорты (Ogre Magi, Undying, Abaddon 5-ка). Твоя особенность — ты не прячешься за спинами керри, а активно участвуешь в создании пространства.",
            "pos5_pos4": "Ты — классический фулл-саппорт, который делает всё для команды. Ты обеспечиваешь идеальный вижн, спасаешь союзников в критические моменты и жертвуешь собой ради победы.\n\nТебе нравятся герои с сильными защитными и контрольными способностями (Dazzle, Oracle, Lion). Твоя сила — в понимании приоритетов и способности всегда быть в нужном месте в нужное время."
        };


        let currentQuestion = 0;
        let scores = { pos1: 0, pos2: 0, pos3: 0, pos4: 0, pos5: 0 };
        let lastResult = null;


        function loadSavedResult() {
            const saved = localStorage.getItem('dota2helper_lastResult');
            if (saved) {
                lastResult = JSON.parse(saved);
                updateQuizPageResult();
                updateHeroQuizStart();
            }
        }


        function saveResult(result) {
            localStorage.setItem('dota2helper_lastResult', JSON.stringify(result));
        }


        loadSavedResult();


        function switchPage(pageName) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));


            document.getElementById(`page-${pageName}`).classList.add('active');
            event.currentTarget.classList.add('active');


            if (pageName === 'quiz') {
                document.getElementById('quiz-list').style.display = 'block';
                document.getElementById('quiz-content-container').style.display = 'none';
                document.getElementById('hero-quiz-container').style.display = 'none';
                updateQuizPageResult();
            }
        }


        function startPositionQuiz() {
            document.getElementById('quiz-list').style.display = 'none';
            document.getElementById('quiz-content-container').style.display = 'block';
            document.getElementById('hero-quiz-container').style.display = 'none';
            initQuiz();
        }


        function backToQuizList() {
            document.getElementById('quiz-list').style.display = 'block';
            document.getElementById('quiz-content-container').style.display = 'none';
            document.getElementById('hero-quiz-container').style.display = 'none';
            updateQuizPageResult();
        }


        function updateQuizPageResult() {
            if (lastResult) {
                document.getElementById('quizPageLastResult').style.display = 'block';
                document.getElementById('quizPagePosition').textContent = lastResult.position;
                document.getElementById('quizPageDate').textContent = `Пройден: ${lastResult.date}`;
            }
        }


        function goToQuiz() {
            switchPage('quiz');
            document.querySelectorAll('.nav-item')[1].classList.add('active');
            document.querySelectorAll('.nav-item')[0].classList.remove('active');
            document.getElementById('quiz-list').style.display = 'block';
            document.getElementById('quiz-content-container').style.display = 'none';
            document.getElementById('hero-quiz-container').style.display = 'none';
            updateQuizPageResult();
        }


        function goToHeroQuiz() {
            switchPage('quiz');
            document.querySelectorAll('.nav-item')[1].classList.add('active');
            document.querySelectorAll('.nav-item')[0].classList.remove('active');
            startHeroQuiz();
        }


        function initQuiz() {
            currentQuestion = 0;
            scores = { pos1: 0, pos2: 0, pos3: 0, pos4: 0, pos5: 0 };


            document.querySelector('.quiz-content').style.display = 'block';
            document.getElementById('result').classList.remove('active');


            showQuestion();
        }


        function showQuestion() {
            const questionData = quizData[currentQuestion];
            const progress = ((currentQuestion + 1) / quizData.length) * 100;


            document.getElementById('progressBar').style.width = progress + '%';
            document.getElementById('question').textContent = questionData.question;


            const answersContainer = document.getElementById('answers');
            answersContainer.innerHTML = '';


            questionData.answers.forEach((answer, index) => {
                const parts = answer.text.split(' ');
                const emoji = parts[0];
                const text = parts.slice(1).join(' ');


                const button = document.createElement('button');
                button.className = 'answer-btn';
                button.innerHTML = `
                    <span class="emoji">${emoji}</span>
                    <span class="text">${text}</span>
                `;
                button.onclick = () => selectAnswer(index);
                answersContainer.appendChild(button);
            });
        }


        function selectAnswer(index) {
            const questionData = quizData[currentQuestion];
            const selectedScores = questionData.answers[index].scores;


            for (let pos in selectedScores) {
                scores[pos] += selectedScores[pos];
            }


            const buttons = document.querySelectorAll('.answer-btn');
            buttons.forEach((btn, i) => {
                if (i === index) {
                    btn.classList.add('selected');
                }
            });


            setTimeout(() => {
                currentQuestion++;
                if (currentQuestion < quizData.length) {
                    showQuestion();
                } else {
                    showResult();
                }
            }, 300);
        }


        function showResult() {
            document.querySelector('.quiz-content').style.display = 'none';


            const sortedPositions = Object.entries(scores).sort((a, b) => b[1] - a[1]);
            const firstPos = sortedPositions[0][0];
            const secondPos = sortedPositions[1][0];


            lastResult = {
                position: positionNames[firstPos],
                posShort: positionShortNames[firstPos],
                positionIndex: parseInt(firstPos.replace('pos', '')) - 1,
                date: new Date().toLocaleDateString('ru-RU')
            };


            saveResult(lastResult);
            updateQuizPageResult();
            updateHeroQuizStart();


            document.getElementById('positionPrimary').textContent = positionNames[firstPos];
            document.getElementById('positionBadge').textContent = positionShortNames[firstPos];
            document.getElementById('positionSecondaryBadge').textContent = positionShortNames[secondPos];


            const statsKey = `${firstPos}_${secondPos}`;
            const statsData = positionStats[statsKey];
            const statsContainer = document.getElementById('stats');
            statsContainer.innerHTML = '';


            statsData.forEach(stat => {
                const statItem = document.createElement('div');
                statItem.className = 'stat-item';
                statItem.innerHTML = `
                    <div class="stat-label">
                        <span>${stat.label}</span>
                        <span class="stat-value">${stat.value}%</span>
                    </div>
                    <div class="stat-bar">
                        <div class="stat-bar-fill" style="width: 0%"></div>
                    </div>
                `;
                statsContainer.appendChild(statItem);
            });


            setTimeout(() => {
                document.querySelectorAll('.stat-bar-fill').forEach((bar, index) => {
                    bar.style.width = statsData[index].value + '%';
                });
            }, 100);


            const descriptionKey = `${firstPos}_${secondPos}`;
            document.getElementById('positionDescription').textContent = positionDescriptions[descriptionKey];
            document.getElementById('positionDescription').classList.add('hidden');


            document.getElementById('result').classList.add('active');
        }


        function togglePositionDetails() {
            const description = document.getElementById('positionDescription');
            const btn = event.target;


            if (description.classList.contains('hidden')) {
                description.classList.remove('hidden');
                btn.textContent = 'Скрыть детали';
            } else {
                description.classList.add('hidden');
                btn.textContent = 'Показать детали';
            }
        }


        // ========== КВИЗ ПО ГЕРОЯМ ==========


        const heroQuiz = {
            state: {
                selectedPosition: null,
                currentQuestionIndex: 0,
                answers: [],
                usedSavedPosition: false,
                currentQuestionSet: []
            },


            questions: window.heroCarryData.questions,


            positionNames: ["Керри", "Мидер", "Хардлейнер", "Роумер", "Фулл-саппорт"],


            heroDatabase: {
                0: window.heroCarryData.heroes,
                1: window.heroMidData.heroes,
                2: window.heroOfflaneData.heroes,
                3: window.heroPos4Data.heroes,
                4: window.heroPos5Data.heroes
            },



            init() {
                this.state.selectedPosition = null;
                this.state.currentQuestionIndex = 0;
                this.state.answers = [];
                this.state.usedSavedPosition = false;
                this.state.currentQuestionSet = [];
                this.showStartScreen();
            },


            showStartScreen() {
                document.getElementById('hero-start').style.display = 'block';
                document.getElementById('hero-position-select').style.display = 'none';
                document.getElementById('hero-questions').style.display = 'none';
                document.getElementById('hero-result').style.display = 'none';
            },


            useSavedPosition() {
                if (lastResult && lastResult.positionIndex !== undefined) {
                    this.state.selectedPosition = lastResult.positionIndex;
                    this.state.usedSavedPosition = true;
                    this.startQuestions();
                }
            },


            showPositionSelect() {
                document.getElementById('hero-start').style.display = 'none';
                document.getElementById('hero-position-select').style.display = 'block';
            },


            selectPosition(index) {
                this.state.selectedPosition = index;
                this.state.usedSavedPosition = false;
                this.startQuestions();
            },


            backToStart() {
                this.showStartScreen();
            },


            startQuestions() {
                this.state.currentQuestionIndex = 0;
                this.state.answers = [];


            const questionSets = {
                0: window.heroCarryData.questions,
                1: window.heroMidData.questions,
                2: window.heroOfflaneData.questions,
                3: window.heroPos4Data.questions,
                4: window.heroPos5Data.questions,
            };


            this.state.currentQuestionSet =
                questionSets[this.state.selectedPosition] || this.questions;


                document.getElementById('hero-start').style.display = 'none';
                document.getElementById('hero-position-select').style.display = 'none';
                document.getElementById('hero-questions').style.display = 'block';


                this.showQuestion();
            },


            showQuestion() {
                const question = this.state.currentQuestionSet[this.state.currentQuestionIndex];
                const progress = ((this.state.currentQuestionIndex + 1) / this.state.currentQuestionSet.length) * 100;


                document.getElementById('heroProgressBar').style.width = progress + '%';
                document.getElementById('heroQuestion').textContent = question.question;


                const answersContainer = document.getElementById('heroAnswers');
                answersContainer.innerHTML = '';


                question.answers.forEach((answer, index) => {
                    const parts = answer.text.split(' ');
                    const emoji = parts[0];
                    const text = parts.slice(1).join(' ');


                    const button = document.createElement('button');
                    button.className = 'answer-btn';
                    button.innerHTML = `
                        <span class="emoji">${emoji}</span>
                        <span class="text">${text}</span>
                    `;
                    button.onclick = () => this.selectAnswer(index);
                    answersContainer.appendChild(button);
                });
            },


            selectAnswer(index) {
                const question = this.state.currentQuestionSet[this.state.currentQuestionIndex];
                this.state.answers.push(question.answers[index]);


                const buttons = document.querySelectorAll('#heroAnswers .answer-btn');
                buttons.forEach((btn, i) => {
                    if (i === index) {
                        btn.classList.add('selected');
                    }
                });


                setTimeout(() => {
                    this.state.currentQuestionIndex++;
                    if (this.state.currentQuestionIndex < this.state.currentQuestionSet.length) {
                        this.showQuestion();
                    } else {
                        this.showResult();
                    }
                }, 300);
            },


            calculateTopHeroes() {
                // Бонусы для редких тегов
                const rareTagBonus = {
                    lane_push_jungle: 0.2,
                    needs_tank_items: 0.2,
                    lane_roam: 0.6,
                    splitpush: 0.6
                };

                // Собираем все выбранные теги
                const selectedTags = [];
                this.state.answers.forEach(answer => {
                    answer.tags.forEach(tag => {
                        selectedTags.push(tag);
                    });
                });

                // Получаем героев выбранной позиции
                const heroes = this.heroDatabase[this.state.selectedPosition];
                
                // Считаем score для каждого героя с учётом весов и бонусов
                const scoredHeroes = heroes.map(hero => {
                    let score = 0;
                    
                    // Проходим по всем выбранным тегам
                    selectedTags.forEach(tag => {
                        // Если у героя есть этот тег, добавляем его вес
                        if (hero.tags[tag] !== undefined) {
                            let weight = hero.tags[tag];
                            
                            // Добавляем бонус для редких тегов
                            if (rareTagBonus[tag]) {
                                weight += rareTagBonus[tag];
                            }
                            
                            score += weight;
                        }
                    });
                    
                    // Фильтр по сложности (если выбрана)
                    let selectedDifficulty = null;
                    this.state.answers.forEach(answer => {
                        if (answer.tags.includes('easy')) selectedDifficulty = 'easy';
                        else if (answer.tags.includes('medium')) selectedDifficulty = 'medium';
                        else if (answer.tags.includes('hard')) selectedDifficulty = 'hard';
                    });
                    
                    // Бонус за совпадение сложности
                    if (selectedDifficulty && hero.difficulty === selectedDifficulty) {
                        score += 1.5;
                    }
                    
                    return { ...hero, score };
                });

                // Сортируем по убыванию score
                scoredHeroes.sort((a, b) => b.score - a.score);
                
                // Возвращаем топ-5
                return scoredHeroes.slice(0, 5);
            },


            showResult() {
                document.getElementById('hero-questions').style.display = 'none';

                const topHeroes = this.calculateTopHeroes().slice(0, 6); // максимум 6
                const positionName = this.positionNames[this.state.selectedPosition];

                document.getElementById('heroResultPosition').textContent = `Рекомендуем для ${positionName}`;

                // Считаем топ-теги по ответам
                const topTags = {};
                this.state.answers.forEach(answer => {
                    answer.tags.forEach(tag => {
                        if (tag !== 'easy' && tag !== 'medium' && tag !== 'hard') {
                            topTags[tag] = (topTags[tag] || 0) + 1;
                        }
                    });
                });

                const sortedTags = Object.entries(topTags).sort((a, b) => b[1] - a[1]);
                const top3Tags = sortedTags.slice(0, 3).map(t => t[0]);

                const tagNames = {
                    aggressive: "агрессию",
                    balanced: "баланс",
                    versatile: "универсальность",
                    farming: "фарм",
                    lategame: "лейтгейм",
                    superlate: "суперлейт",
                    greedy: "затяжные игры",
                    midgame: "мидгейм",
                    tempo: "темп",
                    mobile: "мобильность",
                    pickoff: "пикоффы",
                    teamfight: "командные драки",
                    control: "контроль",
                    burst: "бёрст урон",
                    snowball: "снежный ком",
                    durable: "живучесть",
                    splitpush: "сплит-пуш",
                    map_pressure: "давление на карту",
                    melee: "ближний бой",
                    ranged: "дальний бой",
                    sustained: "постоянный урон",
                    utility: "утилита",

                    // мид
                    gank_level_rune: "ганги от уровня и рун",
                    gank_item: "ганги от предметов",
                    lane_pressure: "прессинг на линии",
                    lane_mixed: "гибкую линию",
                    lane_farm: "спокойный фарм линии",
                    post_team_gank: "игру с командой после линии",
                    post_mix: "баланс фарма и драк",
                    post_farm_push: "фарм и пуш после линии",
                    role_initiator: "инициацию",
                    role_burst: "бёрст",
                    role_control: "контроль и позиционку",
                    difficulty_easy: "простых героев",
                    difficulty_medium: "среднюю сложность",
                    difficulty_hard: "сложных героев",

                    // оффлейн
                    needs_blink: "блинк/инициацию с предмета",
                    needs_tank_items: "танковые предметы",
                    level_dependent: "силу от уровней",
                    needs_farm_scaling: "фарм и скейл",
                    long_control: "длительный контроль",
                    burst_control: "быстрый контроль",
                    zone_control: "зональный контроль",
                    high_damage: "высокий урон",
                    lane_aggressive: "агрессию на линии",
                    lane_passive: "пассивную линию",
                    lane_push_jungle: "пуш и лес",
                    lane_roam: "роум после линии",
                    teamfight_5v5: "5v5 драки",
                    hunt_pickoff: "поиск пикоффов",
                    flexible: "гибкий стиль",

                    // pos4/5
                    from_level: "зависимость от уровня",
                    from_items: "утилити‑предметы",
                    from_control: "контроль",
                    from_damage: "урон",
                    from_save: "сейвы/баффы",
                    from_initiation: "инициацию",
                    from_counterinitiation: "контр‑инициацию",
                    from_position: "позиционную игру"
                };

                const tagList = top3Tags.map(tag => tagNames[tag] || tag).join(', ');
                document.getElementById('heroResultDescription').textContent =
                    `На основе твоих ответов мы подобрали героев с упором на: ${tagList}. Попробуй их в игре!`;

                const heroListContainer = document.getElementById('heroResultList');
                heroListContainer.innerHTML = '';

                const maxScore = topHeroes[0].score || 1;
                const minScore = topHeroes[topHeroes.length - 1].score || 0;
                const range = maxScore - minScore;

                topHeroes.forEach(hero => {
                    const card = document.createElement('div');

                    // Нормализация процентов: 1-е место = 100%, последнее = ~55-65%
                    const matchPercent = range > 0
                        ? Math.round(55 + ((hero.score - minScore) / range) * 45)
                        : 100;

                    // рамка по совпадению
                    if (matchPercent >= 90) {
                        card.className = 'hero-card hero-card--gold';
                    } else if (matchPercent >= 70) {
                        card.className = 'hero-card hero-card--silver';
                    } else {
                        card.className = 'hero-card hero-card--bronze';
                    }

                    const heroIconUrl = window.getHeroIconUrlByName(hero.name);

                    // пока API не подключен: заглушки для винрейта/игр
                    const winrate = hero.winrate ?? null;   // сюда потом подставишь данные из API
                    const games = hero.games ?? null;

                    const winrateText = winrate != null ? `${winrate.toFixed(1)}%` : '—';
                    const gamesText = games != null ? `${games}` : '—';

                    card.innerHTML = `
                        <div class="hero-card__top">
                            <img src="${heroIconUrl}" alt="${hero.name}" class="hero-card__icon" onerror="this.style.display='none'">
                            <div class="hero-card__info">
                                <div class="hero-card__name">${hero.name}</div>
                                <div class="hero-card__match">Совпадение: <span>${matchPercent}%</span></div>
                            </div>
                        </div>
                        <div class="hero-card__stats">
                            <div class="hero-card__stat-row">
                                <span>Винрейт:</span>
                                <span>${winrateText}</span>
                            </div>
                            <div class="hero-card__stat-row">
                                <span>Сыграно игр:</span>
                                <span>${gamesText}</span>
                            </div>
                        </div>
                    `;

                    heroListContainer.appendChild(card);
                });

                document.getElementById('hero-result').style.display = 'block';
            },



            restart() {
                this.init();
            }
        };


        function startHeroQuiz() {
            document.getElementById('quiz-list').style.display = 'none';
            document.getElementById('quiz-content-container').style.display = 'none';
            document.getElementById('hero-quiz-container').style.display = 'block';
            heroQuiz.init();
        }


        function updateHeroQuizStart() {
            const btn = document.getElementById('useSavedPositionBtn');
            const textSpan = document.getElementById('savedPositionText');
            
            if (lastResult && lastResult.positionIndex !== undefined) {
                btn.disabled = false;
                btn.style.opacity = '1';
                textSpan.textContent = `Твоя последняя позиция: ${lastResult.posShort}`;
            } else {
                btn.disabled = true;
                btn.style.opacity = '0.5';
                textSpan.textContent = 'Сначала пройди тест по позициям';
            }
        }
        document.addEventListener('DOMContentLoaded', () => {
        initSubscriptionGuard();
        // твой существующий стартовый код можно оставить как есть
});