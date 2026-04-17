
        const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

        let TELEGRAM_USER_ID = null;

        function initTelegramUser() {
            if (!tg) {
                console.warn('Telegram WebApp object not found');
                return;
            }

            tg.ready();
            tg.expand();

            const unsafe = tg.initDataUnsafe || {};

            if (unsafe.user && unsafe.user.id) {
                TELEGRAM_USER_ID = unsafe.user.id;
                console.log('TELEGRAM_USER_ID from initDataUnsafe:', TELEGRAM_USER_ID);
            } else {
                console.warn('No Telegram user in initDataUnsafe');
            }
        }

        initTelegramUser();

        function getDota2ProTrackerUrl(heroName) {
            return `https://dota2protracker.com/hero/${encodeURIComponent(heroName)}`;
        }


        // ========== КВИЗ ПО ПОЗИЦИЯМ ==========
        const quizData = [
            {
                questionId: "q1",
                question: "От каких моментов в игре ты получаешь максимальное удовольствие?",
                answers: [
                {
                    id: "q1_pos1",
                    text: "💰 Когда я вижу, что прогрессирую по золоту быстрее, чем вражеские герои",
                    scores: { pos1: 3, pos2: 2, pos3: 1, pos4: 1, pos5: 1 }
                },
                {
                    id: "q1_pos2",
                    text: "🔪 Когда я один в правильный момент поймал и стёр врага за пару секунд",
                    scores: { pos1: 2, pos2: 3, pos3: 1, pos4: 1, pos5: 1 }
                },
                {
                    id: "q1_pos3",
                    text: "⚔️ Когда я первый прыгаю в драку и закрываю вражеских героев",
                    scores: { pos1: 1, pos2: 2, pos3: 3, pos4: 2, pos5: 1 }
                },
                {
                    id: "q1_pos4", // pos4 и pos5 по 3, беру младший номер
                    text: "🤝 Когда моя помощь спасает союзников в критический момент",
                    scores: { pos1: 1, pos2: 1, pos3: 1, pos4: 3, pos5: 3 }
                }
                ]
            },
            {
                questionId: "q2",
                question: "Первые 10 минут игры. Что ты чаще всего делаешь?",
                answers: [
                {
                    id: "q2_pos1",
                    text: "🌾 Сосредотачиваюсь на добивании крипов и стараюсь максимально эффективно фармить",
                    scores: { pos1: 3, pos2: 2, pos3: 2, pos4: 0, pos5: 0 }
                },
                {
                    id: "q2_pos2",
                    text: "⚖️ Хочу переиграть оппонента на линии и начать двигаться по карте",
                    scores: { pos1: 1, pos2: 3, pos3: 2, pos4: 1, pos5: 1 }
                },
                {
                    id: "q2_pos3",
                    text: "⚔️ Ищу возможности для агрессии на линии и стараюсь доминировать",
                    scores: { pos1: 1, pos2: 2, pos3: 3, pos4: 2, pos5: 2 }
                },
                {
                    id: "q2_pos5",
                    text: "🗺️ Помогаю на линиях — даю тп при необходимости, контролирую руны/вижн",
                    scores: { pos1: 0, pos2: 1, pos3: 0, pos4: 2, pos5: 3 }
                }
                ]
            },
            {
                questionId: "q3",
                question: "Видишь, что враги начали драку на карте. Как ты реагируешь?",
                answers: [
                {
                    id: "q3_pos1",
                    text: "📊 Оцениваю выгоду. Если не выгодно, продолжаю фармить или сплит-пушу",
                    scores: { pos1: 3, pos2: 1, pos3: 1, pos4: 0, pos5: 0 }
                },
                {
                    id: "q3_pos4",
                    text: "⚔️ Сразу даю ТП, чтобы помочь команде",
                    scores: { pos1: 1, pos2: 1, pos3: 1, pos4: 3, pos5: 3 }
                },
                {
                    id: "q3_pos3",
                    text: "🎯 Пытаюсь 'выключить' опасного вражеского героя",
                    scores: { pos1: 1, pos2: 2, pos3: 3, pos4: 2, pos5: 1 }
                },
                {
                    id: "q3_pos1b", // pos1 и pos5 по 3, помечаю вторую керри‑метку
                    text: "💚 Держу позицию, чтобы грамотно раскинуть кнопки",
                    scores: { pos1: 3, pos2: 1, pos3: 1, pos4: 1, pos5: 3 }
                }
                ]
            },
            {
                questionId: "q4",
                question: "Каких героев ты предпочитаешь?",
                answers: [
                {
                    id: "q4_pos1",
                    text: "💎 Героев, которые становятся сильными с дорогими предметами",
                    scores: { pos1: 3, pos2: 2, pos3: 1, pos4: 1, pos5: 1 }
                },
                {
                    id: "q4_pos2",
                    text: "🎯 Героев с бёрст уроном — убил и ушёл",
                    scores: { pos1: 1, pos2: 3, pos3: 1, pos4: 1, pos5: 0 }
                },
                {
                    id: "q4_pos3",
                    text: "🛡️ Героев, которые выдерживают много урона",
                    scores: { pos1: 1, pos2: 1, pos3: 3, pos4: 2, pos5: 1 }
                },
                {
                    id: "q4_pos5",
                    text: "🤝 Героев с полезными способностями для команды (станы, сейвы, хил)",
                    scores: { pos1: 0, pos2: 0, pos3: 1, pos4: 3, pos5: 3 }
                }
                ]
            },
            {
                questionId: "q5",
                question: "На что ты обращаешь внимание в конце игры (статистика)?",
                answers: [
                {
                    id: "q5_pos1",
                    text: "📊 Золото/Фраги/Добито крипов",
                    scores: { pos1: 3, pos2: 2, pos3: 2, pos4: 1, pos5: 1 }
                },
                {
                    id: "q5_pos2",
                    text: "⚔️ Фраги и нанесённый урон",
                    scores: { pos1: 3, pos2: 3, pos3: 1, pos4: 1, pos5: 1 }
                },
                {
                    id: "q5_pos3",
                    text: "🎯 Количество контроля и впитанного урона",
                    scores: { pos1: 1, pos2: 1, pos3: 3, pos4: 2, pos5: 2 }
                },
                {
                    id: "q5_pos5",
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

        const heroHeaderTexts = {
            0: "Герои для Керри",
            1: "Герои для Мидера",
            2: "Герои для Хардлейнера",
            3: "Герои для Роумера",
            4: "Герои для Фулл-саппорта"
        };

        const pureCarryPattern = [
            "q1_pos1",
            "q2_pos1",
            "q3_pos1",
            "q4_pos1",
            "q5_pos1"
        ];

        const pureMidPattern = [
            "q1_pos2",
            "q2_pos2",
            "q3_pos3",
            "q4_pos2",
            "q5_pos2"
        ];

        const pureOfflanePattern = [
            "q1_pos3",
            "q2_pos3",
            "q3_pos3",
            "q4_pos3",
            "q5_pos3"
        ];

        const pureFullSupportPattern = [
            "q1_pos4",
            "q2_pos5",
            "q3_pos4",
            "q4_pos5",
            "q5_pos5"
        ];

        function matchesPattern(answers, pattern) {
            const ids = answers.map(a => a.answerId);
            if (ids.length !== pattern.length) return false;
            return pattern.every(id => ids.includes(id));
        }

        function getPurePosition(answers) {
            if (matchesPattern(answers, pureCarryPattern)) return "pos1";
            if (matchesPattern(answers, pureMidPattern)) return "pos2";
            if (matchesPattern(answers, pureOfflanePattern)) return "pos3";
            if (matchesPattern(answers, pureFullSupportPattern)) return "pos5";
            return null;
        }

        function getPositionResult(positionScores, answers) {
            const purePos = getPurePosition(answers);
            if (purePos) {
                return { mainPos: purePos, extraPos: null };
            }
            const sorted = Object.entries(positionScores).sort((a, b) => b[1] - a[1]);
            return { mainPos: sorted[0][0], extraPos: sorted[1][0] };
        }

        const positionDescriptions = {
            "pos1_pure": "Ты — классический керри, который играет вокруг собственного фарма и силы героев в лейте. Тебе комфортно, когда игра идёт через стабильный прирост нетворса, контроль линии и аккуратный выбор моментов для драки.\n\nТы не спешишь ломать игру в мидгейме: твоя задача — выйти к сильным слотам и решить матч за счёт правильного позиционирования и урона в ключевых файтах. Если команда создаёт тебе пространство, ты уверенно забираешь игру в свои руки.",
            "pos2_pure": "Ты — классический мидер, который строит игру вокруг своей линии и активности по карте. Для тебя важно выиграть мид, зафиксировать преимущества по уровню и темпу, а затем подключаться к дракам в самые важные моменты.\n\nТы любишь героев с ярко выраженным пиком силы в ранней и средней стадии: быстро получаешь уровни, делаешь первые ключевые фраги и задаёшь ритм всей команде. От твоих решений зависит, кто будет контролировать карту и важные объекты.",
            "pos3_pure": "Ты — классический офлейнер, который создаёт пространство и ломает игру за счёт давления. Твоя задача — мешать вражескому керри, навязывать драки на неудобных для соперника таймингах и быть фронтлейнером в затяжных файтах.\n\nТы выбираешь героев, которые рано входят в игру и могут инициировать без большого количества слотов. Ты не боишься умирать ради удачной инициации, если это открывает твоей команде возможность выиграть драку или забрать объект.",
            "pos5_pure": "Ты — классический фулл-саппорт, который ставит команду выше личных статов. Тебе важно, чтобы коры чувствовали себя комфортно: ты даёшь вижен, сейв, контролируешь руны, приносишь расходники и прикрываешь ошибки союзников.\n\nТы выбираешь героев с сильной утилитой и контролем, часто жертвуешь собственным фармом ради важных предметов для команды. Твоя ценность — в понимании приоритетов и умении быть в нужной точке карты в критический момент.",
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
            "pos4_pos1": "Ты — саппорт, который умеет находить фарм даже в сложных условиях и превращать небольшое преимущество в значительную силу к поздней игре. Ты не просто ставишь варды — ты активно участвуешь в драках и можешь стать серьёзной угрозой.\n\nТвоя особенность — ты не забываешь о собственном развитии, сохраняя баланс между поддержкой команды и личным ростом.",
            "pos4_pos2": "Ты — агрессивный роумер, который постоянно создаёт давление на карте. Ты не сидишь пассивно на линии — ты активно ищешь возможности для ганков и помогаешь команде захватывать контроль над игрой в ранней и средней стадии.\n\nТвоя игра — это постоянное движение, чтение карты и способность быть там, где решается исход драки.",
            "pos4_pos3": "Ты — прочный саппорт, который не боится стоять на передовой. Ты готов первым входить в драку, танковать урон и создавать пространство для команды. В отличие от хрупких роумеров, ты выдерживаешь фокус и контролируешь зону боя.\n\nТвоя сила — в способности диктовать условия драки и брать на себя удар.",
            "pos4_pos5": "Ты — универсальный саппорт, который одинаково хорошо справляется с ролью роумера и классического саппорта. Ты умеешь ставить варды в критических точках, спасать союзников и создавать давление на карте.\n\nТвоя сила — в адаптивности: ты можешь подстроиться под любую ситуацию и всегда найдёшь способ помочь команде.",
            "pos5_pos1": "Ты — саппорт, который умеет находить фарм даже после покупки вардов. Ты понимаешь важность поддержки команды, но не забываешь о собственном развитии, что позволяет тебе оставаться полезным на всех стадиях игры.\n\nТвоя особенность — умение балансировать между жертвенностью ради команды и собственным прогрессом.",
            "pos5_pos2": "Ты — активный фулл-саппорт, который не просто стоит за керри на линии. Ты активно двигаешься по карте, помогаешь мидеру, контролируешь руны и создаёшь давление.\n\nТвоя сила — в способности влиять на темп игры через правильное позиционирование и тайминги.",
            "pos5_pos3": "Ты — саппорт, который не боится стоять на передовой. Ты готов первым входить в драку рядом с офлейнером, танковать урон и создавать хаос в рядах врага своими способностями.\n\nТвоя особенность — ты не прячешься за спинами керри, а активно участвуешь в создании пространства.",
            "pos5_pos4": "Ты — фулл-саппорт, который делает всё для команды. Ты обеспечиваешь идеальный вижн, спасаешь союзников в критические моменты и жертвуешь собой ради победы.\n\nТвоя сила — в понимании приоритетов и способности всегда быть в нужном месте в нужное время."
        };

        let currentQuestion = 0;
        let scores = { pos1: 0, pos2: 0, pos3: 0, pos4: 0, pos5: 0 };
        let lastPositionResult = null;
        let selectedAnswersHistory = [];

        // Получаем token из URL параметров
        function getTokenFromUrl() {
            const params = new URLSearchParams(window.location.search);
            return params.get('token');
        }

        const USER_TOKEN = getTokenFromUrl();

        // Фоновая загрузка профиля при старте — не блокирует интерфейс
        if (USER_TOKEN) {
            setTimeout(function() { initProfile(); }, 0);
        }

        // Сохранение результата на backend
        async function saveResultToBackend(result) {
            if (!USER_TOKEN) {
                console.warn('No token available, cannot save to backend');
                return;
            }

            try {
                const response = await fetch(`${window.API_BASE_URL}/save_result`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        token: USER_TOKEN,
                        result: result
                    })
                });

                if (!response.ok) {
                    console.error('Failed to save result to backend:', response.status);
                }
            } catch (error) {
                console.error('Error saving result to backend:', error);
            }
        }

        function saveResult(result) {
            saveResultToBackend(result);
        }

        function switchPage(pageName, event) {
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));


            document.getElementById(`page-${pageName}`).classList.add('active');
            if (event && event.currentTarget) {
                event.currentTarget.classList.add('active');
            }


            if (pageName === 'home') {
                if (typeof initHomeScreen === 'function') initHomeScreen();
                else loadMeta();
            }
            if (pageName === 'quiz') {
                document.getElementById('quiz-list').style.display = 'block';
                document.getElementById('quiz-content-container').style.display = 'none';
                document.getElementById('hero-quiz-container').style.display = 'none';
                updateQuizPageResult();
            }
            if (pageName === 'profile') {
                initProfile();
            }
        }

        function startPositionQuiz() {
            document.getElementById('quiz-list').style.display = 'none';
            document.getElementById('quiz-content-container').style.display = 'block';
            document.getElementById('hero-quiz-container').style.display = 'none';
            initQuiz();
        }
        
        function startHeroQuiz() {
            document.getElementById('quiz-list').style.display = 'none';
            document.getElementById('quiz-content-container').style.display = 'none';
            document.getElementById('hero-quiz-container').style.display = 'block';
            heroQuiz.init();
        }


        function backToQuizList() {
            document.getElementById('quiz-list').style.display = 'block';
            document.getElementById('quiz-content-container').style.display = 'none';
            document.getElementById('hero-quiz-container').style.display = 'none';
            updateQuizPageResult();
        }

        function updateQuizPageResult() {
            if (lastPositionResult) {
                document.getElementById('quizPageLastResult').style.display = 'block';
                document.getElementById('quizPagePosition').textContent = lastPositionResult.position;
                document.getElementById('quizPageDate').textContent = `Пройден: ${lastPositionResult.date}`;
            }
        }

        function goToPositionQuiz() {
            // переключаемся на вкладку "Квизы"
            switchPage('quiz');
            document.querySelectorAll('.nav-item')[1].classList.add('active');
            document.querySelectorAll('.nav-item')[0].classList.remove('active');

            // сразу открываем сам квиз по позициям
            startPositionQuiz();
        }

        function goToHeroQuiz() {
            switchPage('quiz');
            document.querySelectorAll('.nav-item')[1].classList.add('active');
            document.querySelectorAll('.nav-item')[0].classList.remove('active');
            startHeroQuiz();
        }

        function goToMatchups() {
            switchPage('database');
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            document.querySelectorAll('.nav-item')[3].classList.add('active');
        }

        function initQuiz() {
            currentQuestion = 0;
            scores = { pos1: 0, pos2: 0, pos3: 0, pos4: 0, pos5: 0 };
            selectedAnswersHistory = [];

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
            const selectedAnswer = questionData.answers[index];
            const selectedScores = selectedAnswer.scores;

            // сохраняем id ответа для проверки чистых паттернов
            selectedAnswersHistory.push({
                questionId: questionData.questionId,
                answerId: selectedAnswer.id,
                answerIndex: index
            });

            for (let pos in selectedScores) {
                scores[pos] += selectedScores[pos];
            }

            const buttons = document.querySelectorAll('.answer-btn');
            buttons.forEach((btn, i) => {
                if (i === index) btn.classList.add('selected');
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

        function goBackInPositionQuiz() {
            // если на первом вопросе — возвращаем к списку квизов
            if (currentQuestion <= 0) {
                backToQuizList();
                return;
            }

            // откатываемся на предыдущий вопрос
            currentQuestion--;

            const questionData = quizData[currentQuestion];
            const prevEntry = selectedAnswersHistory[currentQuestion];

            if (prevEntry !== undefined) {
                const prevScores = questionData.answers[prevEntry.answerIndex].scores;
                for (let pos in prevScores) {
                    scores[pos] -= prevScores[pos];
                }
                selectedAnswersHistory.pop();
            }

            showQuestion();
        }

        function showResult() {
            document.querySelector('.quiz-content').style.display = 'none';

            // определяем позиции через новую логику
            const { mainPos, extraPos } = getPositionResult(scores, selectedAnswersHistory);
            const isPure = (extraPos === null);

            // формируем ключ для статов и описания
            const statsKey = isPure ? `${mainPos}_pure` : `${mainPos}_${extraPos}`;

            // сохраняем результат
            lastPositionResult = {
                type: 'position_quiz',
                position: positionNames[mainPos],
                posShort: positionShortNames[mainPos],
                positionIndex: parseInt(mainPos.replace('pos', '')) - 1,
                date: new Date().toLocaleDateString('ru-RU'),
                isPure: isPure,
                extraPos: extraPos
            };
            saveResult(lastPositionResult);
            updateQuizPageResult();
            updateHeroQuizStart();

            // основная позиция
            document.getElementById('positionPrimary').textContent = positionNames[mainPos];
            document.getElementById('positionBadge').textContent = positionShortNames[mainPos];

            // доп. позиция: показываем или скрываем
            const secondaryLabel = document.querySelector('.position-secondary-label');
            const secondaryBadge = document.getElementById('positionSecondaryBadge');
            if (isPure) {
                // чистая роль — ничего лишнего не показываем
                secondaryLabel.style.display = 'none';
                secondaryBadge.style.display = 'none';
            } else {
                secondaryLabel.style.display = '';
                secondaryBadge.style.display = '';
                secondaryBadge.textContent = positionShortNames[extraPos];
            }

            // описание
            document.getElementById('positionDescription').textContent = positionDescriptions[statsKey] || '';
            document.getElementById('positionDescription').classList.add('hidden');

            document.getElementById('result').classList.add('active');
        }

        function togglePositionDetails(event) {
            const description = document.getElementById('positionDescription');
            const btn = event?.target;

            if (!btn) return;

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
                currentQuestionSet: [],
                currentShuffledAnswers: null
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
                document.getElementById('hero-loading').style.display = 'none';
            },


            useSavedPosition() {
                if (lastPositionResult && lastPositionResult.positionIndex !== undefined) {
                    this.state.selectedPosition = lastPositionResult.positionIndex;
                    this.state.usedSavedPosition = true;
                    this.startQuestions();
                } else {
                    // ✅ БАГ-ФИХ: Если позиция не сохранена, перенаправляем на квиз позиций
                    console.log('[HERO QUIZ] Нет сохранённой позиции, перенаправление на position quiz');
                    goToPositionQuiz();
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
                this.state.currentSelections = [];


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

                this.state.currentSelections = [];

                document.getElementById('heroProgressBar').style.width = progress + '%';
                document.getElementById('heroQuestion').textContent = question.question;

                const hint = document.getElementById('heroQuizHint');
                hint.textContent = 'выбери 1 или 2 варианта';

                const backBtn = document.getElementById('heroBackBtn');
                backBtn.disabled = false;

                const isLast = this.state.currentQuestionIndex === this.state.currentQuestionSet.length - 1;
                const nextBtn = document.getElementById('heroNextBtn');
                nextBtn.disabled = true;
                nextBtn.textContent = isLast ? 'Результат →' : 'Далее →';

                const answersContainer = document.getElementById('heroAnswers');
                answersContainer.innerHTML = '';

                // Для керри (position 0) перемешиваем варианты ответов (Fisher-Yates)
                let displayAnswers = question.answers;
                if (this.state.selectedPosition === 0) {
                    displayAnswers = [...question.answers];
                    for (let i = displayAnswers.length - 1; i > 0; i--) {
                        const j = Math.floor(Math.random() * (i + 1));
                        [displayAnswers[i], displayAnswers[j]] = [displayAnswers[j], displayAnswers[i]];
                    }
                }
                this.state.currentShuffledAnswers = displayAnswers;

                displayAnswers.forEach((answer, index) => {
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
                const sel = this.state.currentSelections;
                const alreadyIdx = sel.indexOf(index);

                if (alreadyIdx !== -1) {
                    // Deselect
                    sel.splice(alreadyIdx, 1);
                } else {
                    if (sel.length >= 2) return; // max 2
                    sel.push(index);
                }

                // Update button visuals
                const buttons = document.querySelectorAll('#heroAnswers .answer-btn');
                buttons.forEach((btn, i) => {
                    btn.classList.toggle('selected', sel.includes(i));
                });

                // Update hint and next button
                const hint = document.getElementById('heroQuizHint');
                const nextBtn = document.getElementById('heroNextBtn');

                if (sel.length === 0) {
                    hint.textContent = 'выбери 1 или 2 варианта';
                    nextBtn.disabled = true;
                } else if (sel.length === 2) {
                    hint.textContent = 'выбрано максимум';
                    nextBtn.disabled = false;
                } else {
                    hint.textContent = 'можно добавить ещё один вариант';
                    nextBtn.disabled = false;
                }
            },


            nextQuestion() {
                if (this.state.currentSelections.length === 0) return;

                const question = this.state.currentQuestionSet[this.state.currentQuestionIndex];
                const answers = this.state.currentShuffledAnswers || question.answers;
                const selectedAnswers = this.state.currentSelections.map(i => answers[i]);
                this.state.answers.push(selectedAnswers);

                this.state.currentQuestionIndex++;
                if (this.state.currentQuestionIndex < this.state.currentQuestionSet.length) {
                    this.showQuestion();
                } else {
                    this.showResult();
                }
            },


            calculateTopHeroes() {
                // 1. Собираем взвешенные теги из всех вопросов.
                //    melee/ranged НЕ участвуют в скоринге — только в фильтрации (см. ниже).
                const selectedTags = {}; // tag → суммарный вес
                let selectedDifficulty = null;
                let wantsMelee = false;
                let wantsRanged = false;

                this.state.answers.forEach(questionAnswers => {
                    const weight = questionAnswers.length === 1 ? 1.0 : 0.5;
                    const questionTagWeights = {};

                    questionAnswers.forEach(answer => {
                        answer.tags.forEach(tag => {
                            if (tag === 'easy' || tag === 'medium' || tag === 'hard') {
                                selectedDifficulty = tag;
                            } else if (tag === 'melee') {
                                wantsMelee = true;
                            } else if (tag === 'ranged') {
                                wantsRanged = true;
                            } else {
                                questionTagWeights[tag] = Math.min(1.0, (questionTagWeights[tag] || 0) + weight);
                            }
                        });
                    });

                    Object.entries(questionTagWeights).forEach(([tag, w]) => {
                        selectedTags[tag] = (selectedTags[tag] || 0) + w;
                    });
                });

                const heroes = this.heroDatabase[this.state.selectedPosition];

                const scoredHeroes = heroes.map(hero => {
                    let score = 0;
                    const heroTags = hero.tags;

                    Object.entries(selectedTags).forEach(([tag, weight]) => {
                        // Вариант 1: hero.tags — МАССИВ (керри, мид)
                        if (Array.isArray(heroTags)) {
                            if (heroTags.includes(tag)) {
                                score += weight;
                            }
                        }
                        // Вариант 2: hero.tags — ОБЪЕКТ с весами (оффлейн, pos4/5)
                        else if (heroTags && typeof heroTags === 'object') {
                            if (heroTags[tag] !== undefined) {
                                score += heroTags[tag] * weight;
                            }
                        }
                    });

                    // Бонус за совпадение сложности
                    if (selectedDifficulty && hero.difficulty === selectedDifficulty) {
                        score += 1.5;
                    }

                    // Тай-брейкер для керри (position 0): случайный шум ±0.01
                    if (this.state.selectedPosition === 0) {
                        score += Math.random() * 0.02 - 0.01;
                    }

                    return { ...hero, score };
                });

                scoredHeroes.sort((a, b) => b.score - a.score);

                // 2. Фильтр по типу атаки (только для керри, pos 0).
                //    Если выбраны оба варианта — фильтр не применяется.
                if (this.state.selectedPosition === 0 && (wantsMelee || wantsRanged) && !(wantsMelee && wantsRanged)) {
                    const preferred = scoredHeroes.filter(h => {
                        if (Array.isArray(h.tags)) {
                            if (wantsMelee) return h.tags.includes('melee') && !h.tags.includes('ranged');
                            return h.tags.includes('ranged') && !h.tags.includes('melee');
                        }
                        // новый формат (объект тегов): используем h.melee из мета-данных
                        // both: true — герой со смешанной атакой, попадает в preferred всегда
                        return wantsMelee ? (h.melee === true || h.both === true) : (h.melee === false || h.both === true);
                    });
                    const fallback = scoredHeroes.filter(h => !preferred.includes(h));
                    const result = [...preferred, ...fallback];
                    return result.slice(0, 5);
                }

                return scoredHeroes.slice(0, 5);
            },

            showResult() {
                document.getElementById('hero-questions').style.display = 'none';

                const topHeroes = this.calculateTopHeroes().slice(0, 6);

                // Brief loading indicator (1.2s) — just enough to feel intentional,
                // not so long that it wastes the user's time
                this._startHeroLoading();

                setTimeout(() => {
                    const loading = document.getElementById('hero-loading');
                    loading.style.transition = 'opacity 0.3s ease';
                    loading.style.opacity = '0';
                    setTimeout(() => {
                        loading.style.display = 'none';
                        loading.style.opacity = '';
                        loading.style.transition = '';
                        this._renderResult(topHeroes);
                    }, 300);
                }, 1200);
            },

            _startHeroLoading() {
                const loading = document.getElementById('hero-loading');
                loading.style.display = 'flex';
                loading.style.opacity = '1';

                // A few hero icons drift subtly in the background
                const heroNames = Object.keys(window.dotaHeroImages || {});
                const shuffled = [...heroNames].sort(() => Math.random() - 0.5).slice(0, 6);

                const container = loading.querySelector('.hlo-orbits-wrap');
                container.innerHTML = '';

                const rand = (min, max) => (min + Math.random() * (max - min)).toFixed(1);

                // Генерируем уникальные @keyframes для каждой иконки
                let keyframesCss = '';
                shuffled.forEach((_heroName, i) => {
                    const animName = `hlo-drift-${i}`;
                    const pts = [0, 25, 50, 75, 100]
                        .map(pct => `${pct}%{top:${rand(-5, 105)}%;left:${rand(-5, 105)}%}`)
                        .join('');
                    keyframesCss += `@keyframes ${animName}{${pts}}`;
                });

                let styleEl = document.getElementById('hlo-dynamic-styles');
                if (!styleEl) {
                    styleEl = document.createElement('style');
                    styleEl.id = 'hlo-dynamic-styles';
                    document.head.appendChild(styleEl);
                }
                styleEl.textContent = keyframesCss;

                shuffled.forEach((heroName, i) => {
                    const size = 32 + Math.floor(Math.random() * 16); // 32–47px
                    const dur  = (8 + Math.random() * 6).toFixed(1);  // 8–14s
                    const delay = (0.1 + i * 0.08).toFixed(2);        // appear quickly

                    const img = document.createElement('img');
                    img.className = 'hlo-icon';
                    img.src = window.getHeroIconUrlByName(heroName);
                    img.style.width  = `${size}px`;
                    img.style.height = `${size}px`;
                    img.style.animation = [
                        `hlo-icon-in 0.8s ease ${delay}s forwards`,
                        `hlo-drift-${i} ${dur}s ease-in-out ${delay}s infinite`,
                    ].join(', ');
                    container.appendChild(img);
                });

                // Clear star field (not needed for brief loading)
                const starsEl = document.getElementById('hloStars');
                starsEl.innerHTML = '';

                // Прогресс-бар 0 → 100% за 1.2с
                const fill = document.getElementById('hloProgressFill');
                fill.style.transition = 'none';
                fill.style.width = '0%';
                requestAnimationFrame(() => requestAnimationFrame(() => {
                    fill.style.transition = 'width 1.2s ease-out';
                    fill.style.width = '100%';
                }));
            },

            _renderResult(topHeroes) {
                const positionIndex = this.state.selectedPosition; // 0..4
                const headerText = heroHeaderTexts[positionIndex] || "";
                document.getElementById("heroResultPosition").textContent = headerText;

                // Считаем топ-теги по ответам
                const topTags = {};
                this.state.answers.forEach(questionAnswers => {
                    questionAnswers.forEach(answer => {
                        answer.tags.forEach(tag => {
                            if (tag !== 'easy' && tag !== 'medium' && tag !== 'hard') {
                                topTags[tag] = (topTags[tag] || 0) + 1;
                            }
                        });
                    });
                });

                const sortedTags = Object.entries(topTags).sort((a, b) => b[1] - a[1]);

                if (positionIndex === 0) {
                    // Керри — «Твой стиль: ...» с carry-специфичными лейблами
                    const tagLabels = {
                        peak_midgame:       'силён в мид-гейме',
                        peak_late:          'раскрывается в лейте',
                        peak_super_lategame:'для затяжных игр',
                        farm_fast:          'быстрый фарм',
                        farm_based:         'фарм через предметы',
                        snowball_based:     'сноубол',
                        fight_diver:        'может инициировать',
                        fight_backline:     'бьёт с задней линии',
                        fight_brawler:      'убивает райткликом',
                        fight_invis_flanker:'заходит с фланга',
                        mobility_low:       'низкая мобильность',
                        mobility_medium:    'средняя мобильность',
                        mobility_high:      'высокая мобильность',
                        push_bad:           'слабый пуш',
                        push_medium:        'средний пуш',
                        push_good:          'хороший пуш',
                    };
                    const tagList = sortedTags
                        .map(([tag]) => tagLabels[tag])
                        .filter(Boolean)
                        .slice(0, 3)
                        .join(', ');
                    document.getElementById('heroResultDescription').textContent =
                        tagList ? `Твой стиль: ${tagList}` : '';
                } else {
                    const top3Tags = sortedTags.slice(0, 3).map(t => t[0]);
                    const tagNames = {
                        aggressive: "агрессию",
                        balanced: "баланс",
                        versatile: "универсальность",
                        farming: "фарм",
                        lategame: "лейт",
                        superlate: "лейт+",
                        greedy: "затяжные игры",
                        midgame: "мидгейм",
                        tempo: "темп",
                        mobile: "мобильность",
                        pickoff: "пикоффы",
                        teamfight: "командные драки",
                        control: "контроль",
                        burst: "бёрст урон",
                        snowball: "сноубол",
                        durable: "живучесть",
                        splitpush: "сплит-пуш",
                        map_pressure: "давление на карту",
                        melee: "ближний бой",
                        ranged: "дальний бой",
                        sustained: "постоянный урон",
                        utility: "утилита",
                        gank_level_rune: "ганги от уровня и рун",
                        gank_item: "ганги от предметов",
                        lane_pressure: "прессинг на линии",
                        lane_mixed: "гибкую линию",
                        lane_farm: "спокойный фарм линии",
                        post_team_gank: "игру с командой",
                        post_mix: "баланс фарма и драк",
                        post_farm_push: "фарм и пуш",
                        role_initiator: "инициацию",
                        role_burst: "бёрст",
                        role_control: "контроль и позиционку",
                        difficulty_easy: "простых героев",
                        difficulty_medium: "среднюю сложность",
                        difficulty_hard: "сложных героев",
                        needs_blink: "предметы",
                        needs_tank_items: "стойкость",
                        level_dependent: "силу от уровней",
                        needs_farm_scaling: "фарм и скейл",
                        long_control: "длительный контроль",
                        burst_control: "быстрый контроль",
                        zone_control: "зональный контроль",
                        high_damage: "высокий урон",
                        lane_aggressive: "агрессию на линии",
                        lane_passive: "пассивную линию",
                        lane_push_jungle: "быстрый фарм",
                        lane_roam: "роум после линии",
                        teamfight_5v5: "5v5 драки",
                        hunt_pickoff: "поиск пикоффов",
                        flexible: "гибкий стиль",
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
                }

                const heroListContainer = document.getElementById('heroResultList');
                heroListContainer.innerHTML = '';

                // Находим реальные max/min среди выбранных героев
                const scores = topHeroes.map(h => h.score);
                const maxScore = Math.max(...scores);
                const minScore = Math.min(...scores);
                const range = maxScore - minScore || 1; // защита от 0

                topHeroes.forEach((hero, index) => {
                    const card = document.createElement('div');

                    // Если у всех score одинаковый, не будем врать 100% — дадим всем 75%
                    let matchPercent;
                    if (maxScore === minScore) {
                        matchPercent = 75;
                    } else {
                        const normalized = (hero.score - minScore) / range; // от 0 до 1
                        matchPercent = Math.round(60 + normalized * 40);    // 60–100%
                    }

                    // рамка по совпадению
                    if (matchPercent >= 90) {
                        card.className = 'hero-card hero-card--gold';
                    } else if (matchPercent >= 75) {
                        card.className = 'hero-card hero-card--silver';
                    } else {
                        card.className = 'hero-card hero-card--bronze';
                    }

                    const heroIconUrl = window.getHeroIconUrlByName(hero.name);

                    card.innerHTML = `
                        <div class="hero-top">
                        <div class="hero-main">
                            <img src="${heroIconUrl}" alt="${hero.name}" class="hero-icon" onerror="this.style.display='none'">
                            <div class="hero-text">
                            <div class="hero-name">${hero.name}</div>
                            </div>
                        </div>
                        <div class="hero-rank">${index + 1}</div>
                        </div>

                        <div class="match-block">
                        <div class="match-line">
                            <span>Совпадение:</span>
                            <span class="match-value">${matchPercent}%</span>
                        </div>
                        <div class="match-bar">
                            <div class="match-fill" style="width: ${matchPercent}%;"></div>
                        </div>
                        </div>

                        <div class="guide-row" style="display:flex;justify-content:flex-end;">
                        <button
                            class="guide-chip hero-card__guide-btn"
                            data-hero-name="${hero.name}"
                        >
                            Открыть гайд
                        </button>
                        </div>
                    `;

                    heroListContainer.appendChild(card);
                });


                document.getElementById('hero-result').style.display = 'block';

                // Сохраняем результат hero-квиза
                const heroQuizResult = {
                    type: 'hero_quiz',
                    heroPositionIndex: positionIndex, // 0..4
                    topHeroes: topHeroes.map(hero => {
                        let matchPercent;
                        if (maxScore === minScore) {
                            matchPercent = 75;
                        } else {
                            const normalized = (hero.score - minScore) / range; // 0..1
                            matchPercent = Math.round(60 + normalized * 40);    // 60–100%
                        }
                        return {
                            name: hero.name,
                            score: hero.score,
                            matchPercent: matchPercent
                        };
                    })
                };

                console.log('[HERO QUIZ] Finish, saving result:', heroQuizResult);
                saveResult(heroQuizResult);
            },



            restart() {
                this.init();
            }
        };

        function goBackInHeroQuiz() {
            // если на первом вопросе — возвращаемся туда, откуда пришли
            if (heroQuiz.state.currentQuestionIndex <= 0) {
                heroQuiz.state.currentQuestionIndex = 0;
                heroQuiz.state.answers = [];

                document.getElementById('hero-questions').style.display = 'none';
                if (heroQuiz.state.usedSavedPosition) {
                    // пришли через «Использовать сохранённую позицию» — стартовый экран
                    heroQuiz.showStartScreen();
                } else {
                    // пришли через «Выбрать вручную» — экран выбора позиции
                    document.getElementById('hero-position-select').style.display = 'block';
                }
                return;
            }

            // иначе шаг назад по вопросам
            heroQuiz.state.currentQuestionIndex--;
            heroQuiz.state.answers.pop();
            heroQuiz.showQuestion();
        }

        function updateHeroQuizStart() {
            const btn = document.getElementById('useSavedPositionBtn');
            const textSpan = document.getElementById('savedPositionText');

            if (lastPositionResult && lastPositionResult.positionIndex !== undefined) {
                btn.disabled = false;
                btn.style.opacity = '1';
                textSpan.textContent = `Твоя последняя позиция: ${lastPositionResult.posShort}`;
            } else {
                btn.disabled = true;
                btn.style.opacity = '0.5';
                textSpan.textContent = 'Сначала пройди тест по позициям';
            }
        }

        document.addEventListener('click', (event) => {
            const btn = event.target.closest('.hero-card__guide-btn');
            if (!btn) return;

            const heroName = btn.getAttribute('data-hero-name');
            if (!heroName) return;

            _metaHeroClick(heroName);
        });
// ========== ПРОФИЛЬ ==========

async function initProfile() {
    console.log('[PROFILE] Загрузка профиля...');

    if (!USER_TOKEN) {
        console.error('[PROFILE] Токен отсутствует');
        updateProfileHeader(null);
        showEmptyProfile();
        return;
    }

    try {
        const response = await fetch(`${window.API_BASE_URL}/profile_full?token=${USER_TOKEN}`);
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }

        const profile = await response.json();
        console.log('[PROFILE] Данные получены:', profile);

        // ✅ БАГ-ФИХ: Fallback - сохраняем данные Telegram если их нет в профиле
        if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
            const user = tg.initDataUnsafe.user;
            // Проверяем, есть ли хоть какие-то данные в профиле
            if (!profile.first_name && user.first_name) {
                console.log('[PROFILE] Отправляем данные Telegram на backend (fallback)');
                try {
                    await fetch(`${window.API_BASE_URL}/save_telegram_data`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            token: USER_TOKEN,
                            first_name: user.first_name,
                            last_name: user.last_name || null,
                            username: user.username || null,
                            photo_url: user.photo_url || null
                        })
                    });
                    console.log('[PROFILE] Данные Telegram отправлены');
                } catch (e) {
                    console.error('[PROFILE] Ошибка отправки данных Telegram:', e);
                }
            }
        }

        updateProfileHeader(profile);
        displayPositionResult(profile);
        displayHeroesResult(profile);

    } catch (error) {
        console.error('[PROFILE] Ошибка загрузки:', error);
        updateProfileHeader(null);
        showEmptyProfile();
    }
}

function updateProfileHeader(profile) {
    const avatar = document.getElementById('profile-avatar');
    const nameEl = document.getElementById('profile-name');
    const usernameEl = document.getElementById('profile-username');

    let userData = null;

    if (profile && profile.first_name) {
        userData = {
            first_name: profile.first_name,
            last_name: profile.last_name,
            username: profile.username,
            photo_url: profile.photo_url
        };
    } else if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
        userData = tg.initDataUnsafe.user;
    }

    if (userData) {
        const fullName = `${userData.first_name || ''} ${userData.last_name || ''}`.trim();
        nameEl.textContent = fullName || 'Пользователь';
        if (userData.username) {
            usernameEl.textContent = `@${userData.username}`;
        } else {
            usernameEl.textContent = '';
        }
        if (userData.photo_url) {
            avatar.src = userData.photo_url;
        } else {
            avatar.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(userData.first_name || 'U')}&background=3a7bd5&color=fff&size=200&bold=true`;
        }
    } else {
        nameEl.textContent = 'Пользователь';
        usernameEl.textContent = '';
        avatar.src = `https://ui-avatars.com/api/?name=U&background=3a7bd5&color=fff&size=200&bold=true`;
    }

    avatar.onerror = function () {
        this.src = `https://ui-avatars.com/api/?name=U&background=3a7bd5&color=fff&size=200&bold=true`;
    };
}

function displayPositionResult(profile) {
    const posResult = document.getElementById('profile-position-result');
    const posEmpty = document.getElementById('profile-position-empty');

    let positionData = null;
    if (profile.quiz_history && profile.quiz_history.length > 0) {
        for (const quiz of profile.quiz_history) {
            const res = quiz.result;
            if (!res) continue;

            // Приоритет: новый формат
            if (res.position_quiz) {
                positionData = res.position_quiz;
                break;
            }
            // Legacy fallback (старый формат с type в корне)
            else if (res.type === 'position_quiz') {
                positionData = res;
                console.log('[PROFILE] Legacy position_quiz format detected');
                break;
            }
        }
    }

    if (!positionData) {
        posResult.style.display = 'none';
        posEmpty.style.display = 'block';
        // ✅ БАГ-ФИХ: Сбрасываем lastPositionResult и обновляем кнопку hero-квиза
        lastPositionResult = null;
        updateHeroQuizStart();
        return;
    }

    // ✅ БАГ-ФИХ: Синхронизируем lastPositionResult с данными из профиля
    lastPositionResult = {
        type: 'position_quiz',
        position: positionData.position,
        posShort: positionData.posShort,
        positionIndex: positionData.positionIndex,
        date: positionData.date,
        isPure: positionData.isPure,
        extraPos: positionData.extraPos
    };

    // ✅ Обновляем кнопку "использовать сохранённую позицию" в hero-квизе
    updateHeroQuizStart();
    console.log('[PROFILE] lastPositionResult синхронизирован:', lastPositionResult);

    posResult.style.display = 'block';
    posEmpty.style.display = 'none';

    const mainNameEl = document.getElementById('profile-position-main-name');
    const extraNameEl = document.getElementById('profile-position-extra-name');

    // full = "Pos 1 — Керри"
    const full = positionData.position || '';
    const parts = full.split('—').map(s => s.trim());
    const roleLabel = parts[1] || positionData.posShort || full || 'Не указана';

    // Основная строка: "Основная позиция: Керри"
    mainNameEl.textContent = `Основная позиция: ${roleLabel}`;

    // Дополнительная строка, если есть
    if (positionData.extraPos && !positionData.isPure) {
        const extraShort = positionShortNames[positionData.extraPos] || '';
        extraNameEl.textContent = `Доп. позиция: ${extraShort || '—'}`;
    } else {
        extraNameEl.textContent = '';
    }

}


function displayHeroesResult(profile) {
    const heroesResult = document.getElementById('profile-heroes-result');
    const heroesEmpty = document.getElementById('profile-heroes-empty');
    const heroesList = document.getElementById('profile-heroes-list');

    // Находим последний результат позиционного квиза (НОВЫЙ формат)
    let positionData = null;
    if (profile.quiz_history && profile.quiz_history.length > 0) {
        for (const quiz of profile.quiz_history) {
            const res = quiz.result;
            if (!res) continue;

            // Приоритет: новый формат
            if (res.position_quiz) {
                positionData = res.position_quiz;
                break;
            }
            // Legacy fallback
            else if (res.type === 'position_quiz') {
                positionData = res;
                console.log('[PROFILE] Legacy position_quiz format detected in heroes');
                break;
            }
        }
    }

    // Находим hero-квиз для ТЕКУЩЕЙ позиции
    let heroData = null;
    let currentPosIndex = null;
    if (positionData && positionData.positionIndex !== undefined && profile.quiz_history && profile.quiz_history.length > 0) {
        currentPosIndex = positionData.positionIndex;

        for (const quiz of profile.quiz_history) {
            const res = quiz.result;
            if (!res) continue;

            // НОВЫЙ ФОРМАТ: hero_quiz_by_position[positionIndex]
            if (res.hero_quiz_by_position) {
                const heroByPos = res.hero_quiz_by_position[currentPosIndex.toString()];
                if (heroByPos && heroByPos.topHeroes && heroByPos.topHeroes.length > 0) {
                    heroData = heroByPos;
                    break; // Берём первый найденный (самый свежий)
                }
            }

            // Legacy fallback: СТАРЫЙ ФОРМАТ hero_quiz
            if (!heroData) {
                let candidate = null;
                if (res.hero_quiz) {
                    candidate = res.hero_quiz;
                } else if (res.type === 'hero_quiz' && res.topHeroes) {
                    candidate = res;
                }

                // Проверяем совпадение позиции
                if (candidate && candidate.heroPositionIndex === currentPosIndex && candidate.topHeroes && candidate.topHeroes.length > 0) {
                    heroData = candidate;
                    console.log('[PROFILE] Legacy hero_quiz format detected');
                    break;
                }
            }
        }
    }

    // Обновляем заголовок блока героев
    const heroesTitleEl = document.getElementById('profile-heroes-title');
    if (heroesTitleEl) {
        heroesTitleEl.textContent = (currentPosIndex !== null ? heroHeaderTexts[currentPosIndex] : null) || 'Твои герои';
    }

    // Показываем героев или заглушку
    if (heroData) {
        heroesResult.style.display = 'block';
        heroesEmpty.style.display = 'none';
        renderProfileHeroes(heroesList, heroData.topHeroes);
        return;
    }

    // Иначе показываем заглушку
    heroesResult.style.display = 'none';
    heroesEmpty.style.display = 'block';
}

function renderProfileHeroes(container, heroes) {
    container.innerHTML = '';
    heroes.slice(0, 5).forEach((hero, index) => {
        const heroName = hero.name || hero;
        const matchPercent = hero.matchPercent || 75;
        const heroIconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(heroName) : '';

        const row = document.createElement('a');
        row.className = 'hero-row' + (index === 0 ? ' hero-row-main' : '');
        row.href = getDota2ProTrackerUrl(heroName);
        row.target = '_blank';
        row.rel = 'noopener noreferrer';

        row.innerHTML = `
            <div class="hero-row-rank">${index + 1}</div>
            <div class="hero-row-img">
                <img src="${heroIconUrl}" alt="${heroName}" style="width:100%; height:100%; object-fit:cover; border-radius:6px;" onerror="this.style.display='none'">
            </div>
            <div class="hero-row-main-text">
                <div class="hero-row-name">${heroName}</div>
                <div class="hero-row-sub">
                    ${index === 0 ? 'Лучший мэтч' : 'Совпадение'} • ${matchPercent}%
                </div>
            </div>
        `;

        container.appendChild(row);
    });
}

function showEmptyProfile() {
    document.getElementById('profile-position-result').style.display = 'none';
    document.getElementById('profile-position-empty').style.display = 'block';
    document.getElementById('profile-heroes-result').style.display = 'none';
    document.getElementById('profile-heroes-empty').style.display = 'block';
}

const _originalSwitchPage = switchPage;
switchPage = function (pageName, event) {
    _originalSwitchPage(pageName, event);
    if (pageName === 'profile') {
        initProfile();
    }
    if (pageName === 'database') {
        matchupPage.showSearch();
    }
    if (pageName === 'drafter') {
        var resultEl = document.getElementById('drafter-result');
        if (resultEl && resultEl.style.display !== 'none') {
            resultEl.style.display = 'none';
            document.getElementById('drafter-main').style.display = 'block';
            loadDrafterMatch();
        } else {
            initDrafter();
        }
    }
};

// ========== МАТЧАПЫ ==========

var _heroPageActiveTab = 'build';

function switchHeroPageTab(tab) {
    _heroPageActiveTab = tab;
    var btnMatchups = document.getElementById('hero-ptab-matchups');
    var btnBuild    = document.getElementById('hero-ptab-build');
    var panelMatchups = document.getElementById('hero-tab-matchups');
    var panelBuild    = document.getElementById('hero-tab-build');
    if (btnMatchups)    btnMatchups.classList.toggle('active',    tab === 'matchups');
    if (btnBuild)       btnBuild.classList.toggle('active',       tab === 'build');
    if (panelMatchups)  panelMatchups.style.display = tab === 'matchups' ? 'block' : 'none';
    if (panelBuild)     panelBuild.style.display    = tab === 'build'    ? 'block' : 'none';
}

// Собираем единый массив всех героев из window.dotaHeroIds —
// единственного авторитетного источника для матчапов.
// Дедупликация по hero_id исключает дубли вроде
// 'Outworld Destroyer' / 'Outworld Devourer' (оба id=76).
//
// Примеры поиска после фикса:
//   "ember"     → Ember Spirit        (id 106)
//   "spi"       → Ember Spirit, Earth Spirit, Storm Spirit, Void Spirit
//   "out"       → Outworld Destroyer  (id 76)
//   "destroyer" → Outworld Destroyer
const allMatchupHeroes = (function () {
    if (!window.dotaHeroIds) return [];
    const seenIds = new Set();
    const result = [];
    Object.keys(window.dotaHeroIds).forEach(function (name) {
        const id = window.dotaHeroIds[name];
        if (!seenIds.has(id)) {
            seenIds.add(id);
            result.push(name);
        }
    });
    result.sort();
    return result;
}());

const matchupPage = {
    showSearch: function () {
        const searchScreen = document.getElementById('matchup-search-screen');
        const heroScreen = document.getElementById('matchup-hero-screen');
        const input = document.getElementById('matchup-hero-input');
        const suggestions = document.getElementById('matchup-suggestions');
        if (searchScreen) searchScreen.style.display = 'block';
        if (heroScreen) heroScreen.style.display = 'none';
        if (input) input.value = '';
        if (suggestions) {
            suggestions.innerHTML = '';
            suggestions.style.display = 'none';
        }
        if (window.renderRecentHeroes) window.renderRecentHeroes();
    },

    showHero: function (heroName) {
        const searchScreen = document.getElementById('matchup-search-screen');
        const heroScreen = document.getElementById('matchup-hero-screen');
        const iconEl = document.getElementById('matchup-hero-icon');
        const nameEl = document.getElementById('matchup-hero-name');
        if (searchScreen) searchScreen.style.display = 'none';
        if (heroScreen) heroScreen.style.display = 'block';
        if (iconEl) {
            iconEl.src = window.getHeroIconUrlByName(heroName);
            iconEl.alt = heroName;
            iconEl.style.display = '';
        }
        if (nameEl) {
            nameEl.textContent = heroName;
        }
        switchHeroPageTab(_heroPageActiveTab);
    },

    onInput: function (value) {
        const suggestionsEl = document.getElementById('matchup-suggestions');
        if (!suggestionsEl) return;
        const query = value.trim().toLowerCase();
        if (!query) {
            suggestionsEl.innerHTML = '';
            suggestionsEl.style.display = 'none';
            return;
        }
        const matches = allMatchupHeroes.filter(function (name) {
            return name.toLowerCase().includes(query);
        }).slice(0, 8);
        if (matches.length === 0) {
            suggestionsEl.innerHTML = '';
            suggestionsEl.style.display = 'none';
            return;
        }
        suggestionsEl.innerHTML = matches.map(function (name) {
            const iconUrl = window.getHeroIconUrlByName(name);
            const escaped = name.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
            return '<div class="matchup-suggestion-item" data-hero-name="' + escaped + '">' +
                '<img src="' + iconUrl + '" alt="" class="matchup-suggestion-icon" onerror="this.style.display=\'none\'">' +
                '<span class="matchup-suggestion-name">' + name + '</span>' +
                '</div>';
        }).join('');
        suggestionsEl.style.display = 'block';
    },

    selectHero: function (heroName) {
        const input = document.getElementById('matchup-hero-input');
        const suggestionsEl = document.getElementById('matchup-suggestions');
        if (input) input.value = '';
        if (suggestionsEl) {
            suggestionsEl.innerHTML = '';
            suggestionsEl.style.display = 'none';
        }
        this.showHero(heroName);

        const heroId = window.dotaHeroIds && window.dotaHeroIds[heroName];
        if (!heroId) {
            showMatchupsError('Матчапы для этого героя пока недоступны');
            return;
        }
        if (window.addRecentHero) window.addRecentHero(heroId);
        loadHeroBuild(heroId);
        loadHeroMatchups(heroId);
        loadHeroSynergy(heroId);
    }
};

// ---------- Build: загрузка и рендер ----------

var _buildData      = null;
var _buildHeroId    = null;
var _buildPosition  = null;   // 'POSITION_1' … 'POSITION_5'
var _buildItemsTab  = 'core'; // 'start' | 'core' | 'situ'

var _STRATZ_POS_TO_DOTA = {
    'POSITION_1': 'pos%201',
    'POSITION_2': 'pos%202',
    'POSITION_3': 'pos%203',
    'POSITION_4': 'pos%204',
    'POSITION_5': 'pos%205',
};
var _DOTA_TO_STRATZ_POS = {
    'pos%201': 'POSITION_1',
    'pos%202': 'POSITION_2',
    'pos%203': 'POSITION_3',
    'pos%204': 'POSITION_4',
    'pos%205': 'POSITION_5',
};

var _POSITION_LABELS = {
    'POSITION_1': 'Керри',
    'POSITION_2': 'Мид',
    'POSITION_3': 'Оффлейн',
    'POSITION_4': 'Частичная поддержка',
    'POSITION_5': 'Поддержка',
};
var _POSITION_IMG = {
    'POSITION_1': '/images/positions/pos_1.png',
    'POSITION_2': '/images/positions/pos_2.png',
    'POSITION_3': '/images/positions/pos_3.png',
    'POSITION_4': '/images/positions/pos_4.png',
    'POSITION_5': '/images/positions/pos_5.png',
};
// Прямые маппинги для ключей dota_builds (pos%20N)
var _DOTA_POS_LABELS = {
    'pos%201': 'Керри',
    'pos%202': 'Мид',
    'pos%203': 'Оффлейн',
    'pos%204': 'Частичная поддержка',
    'pos%205': 'Поддержка',
};
var _DOTA_POS_IMG = {
    'pos%201': '/images/positions/pos_1.png',
    'pos%202': '/images/positions/pos_2.png',
    'pos%203': '/images/positions/pos_3.png',
    'pos%204': '/images/positions/pos_4.png',
    'pos%205': '/images/positions/pos_5.png',
};

function _showBuildLoading() {
    _buildData     = null;
    _buildPosition = null;
    _buildItemsTab = 'core';
    var el = document.getElementById('build-content');
    if (el) el.innerHTML = '<p class="matchup-placeholder-text">Загрузка...</p>';
}

function selectBuildPosition(pos) {
    _buildPosition = pos;
    if (_buildHeroId && typeof window.setRecentHeroPosition === 'function') {
        window.setRecentHeroPosition(_buildHeroId, pos);
    }
    if (_buildData) renderBuildTab(_buildData);
}

function switchBuildItemsTab(tab) {
    _buildItemsTab = tab;
    ['start', 'core', 'situ', 'neutral'].forEach(function (t) {
        var panel = document.getElementById('build-items-panel-' + t);
        if (panel) panel.style.display = t === tab ? '' : 'none';
    });
    document.querySelectorAll('.build-items-tab-btn').forEach(function (b) {
        b.classList.toggle('active', b.getAttribute('data-tab') === tab);
    });
}

// ── helpers ───────────────────────────────────────────────────────────────

function _getTopPositionsFromBuilds(data) {
    // Prefer explicit sorted positions list from API (dota-key format: 'pos%20N')
    if (data.positions && data.positions.length) {
        return data.positions.slice(0, 3);
    }
    // Fallback: derive from dota_builds keys
    if (data.dota_builds) {
        var arr = Object.keys(data.dota_builds).map(function (k) {
            var pd = data.dota_builds[k];
            var total = pd.num_matches != null
                ? pd.num_matches
                : (pd.sixslot || []).reduce(function (s, e) { return s + (e.num_matches || 0); }, 0);
            return { position: k, matchCount: total };
        });
        arr.sort(function (a, b) { return b.matchCount - a.matchCount; });
        return arr.slice(0, 3).map(function (p) { return p.position; });
    }
    // Fallback: stratz positions (POSITION_N format)
    var positions = (data.stratz && data.stratz.ALL && data.stratz.ALL.positions) || [];
    return positions.slice()
        .sort(function (a, b) { return (b.matchCount || 0) - (a.matchCount || 0); })
        .slice(0, 3)
        .map(function (p) { return p.position; });
}

function _buildSkillRowHtml(dotaPos, data) {
    var abilities;
    if (dotaPos && dotaPos.abilities && dotaPos.abilities.length) {
        abilities = dotaPos.abilities
            .filter(function (a) { return !a.isTalent; })
            .map(function (a) { return a.name; });
    } else {
        abilities = (data.ability_build || []).filter(function (n) {
            return n.indexOf('special_bonus_') !== 0;
        });
    }
    if (!abilities.length) {
        return '<p class="build-placeholder">Данные собираются, скоро появится</p>';
    }

    // Detect ult: unique ability name that appears fewest times
    var counts = {};
    abilities.forEach(function (n) { counts[n] = (counts[n] || 0) + 1; });
    var vals = Object.keys(counts).map(function (k) { return counts[k]; });
    var minC = Math.min.apply(null, vals);
    var maxC = Math.max.apply(null, vals);
    var ultNames = {};
    if (minC < maxC) {
        Object.keys(counts).forEach(function (n) { if (counts[n] === minC) ultNames[n] = true; });
    }

    var slots = abilities.map(function (aname, i) {
        var iconUrl = 'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/abilities/' + aname + '.png';
        var ultCls = ultNames[aname] ? ' build-ability-slot--ult' : '';
        return '<div class="build-ability-slot' + ultCls + '">' +
            '<div class="build-ability-level">' + (i + 1) + '</div>' +
            '<img src="' + iconUrl + '" class="build-ability-icon" title="' + aname + '" onerror="this.style.opacity=\'0.3\'">' +
            '</div>';
    }).join('');
    return '<div class="build-skillrow">' + slots + '</div>';
}

function _extractTalentNum(displayName) {
    var m = (displayName || '').match(/[+-]?[\d.]+/);
    return m ? m[0] : null;
}

function _applyTalentNum(ruName, num) {
    if (!num) return ruName;
    if (ruName.indexOf('?') !== -1) {
        var qIdx = ruName.indexOf('?');
        var charBefore = qIdx > 0 ? ruName[qIdx - 1] : '';
        var isMinus = charBefore === '-' || charBefore === '\u2013' || charBefore === '\u2014';
        var numToInsert = ((charBefore === '+' && num[0] === '+') || (isMinus && num[0] === '-'))
            ? num.slice(1) : num;
        return ruName.replace('?', numToInsert);
    }
    // Если в русском тексте уже есть цифры — не дублируем число
    if (/\d/.test(ruName)) return ruName;
    // Убираем дублирующийся знак: если num начинается с +/- и ruName тоже начинается с того же знака
    var numSign = (num[0] === '+' || num[0] === '-') ? num[0] : '';
    var ruTrimmed = (numSign && ruName[0] === numSign) ? ruName.slice(1).replace(/^\s+/, '') : ruName;
    return num + ' ' + ruTrimmed;
}

function _buildTalentsHtml(dotaPos, data) {
    var rows;
    if (dotaPos && dotaPos.talents && dotaPos.talents.length) {
        // Строим карту ability_name → русское название из Valve-данных
        var ruMap = {};
        (data.talents_valve || []).forEach(function (tv) {
            if (tv.left_ability  && tv.left)  ruMap[tv.left_ability]  = tv.left;
            if (tv.right_ability && tv.right) ruMap[tv.right_ability] = tv.right;
        });
        var sorted = dotaPos.talents.slice().sort(function (a, b) { return (a.lvl || 0) - (b.lvl || 0); });
        rows = sorted.map(function (t) {
            var leftPopular  = t.choice === 'lt';
            var rightPopular = t.choice === 'rt';
            var leftCls  = 'build-talent-cell build-talent-left'  + (leftPopular  ? ' build-talent-popular' : '');
            var rightCls = 'build-talent-cell build-talent-right' + (rightPopular ? ' build-talent-popular' : '');
            var leftNum   = _extractTalentNum((t.left  || {}).displayName);
            var rightNum  = _extractTalentNum((t.right || {}).displayName);
            var leftRu    = ruMap[(t.left  || {}).name] || (t.left  || {}).displayName || '';
            var rightRu   = ruMap[(t.right || {}).name] || (t.right || {}).displayName || '';
            var leftName  = _applyTalentNum(leftRu,  leftNum);
            var rightName = _applyTalentNum(rightRu, rightNum);
            return '<div class="build-talent-row">' +
                '<div class="' + leftCls  + '">' + leftName  + '</div>' +
                '<div class="build-talent-level-badge">' + (t.lvl || '') + '</div>' +
                '<div class="' + rightCls + '">' + rightName + '</div>' +
                '</div>';
        }).join('');
    } else {
        var talents = data.talents || [];
        if (!talents.length) return '';
        var sortedFb = talents.slice().sort(function (a, b) { return (a.level || 0) - (b.level || 0); });
        rows = sortedFb.map(function (t) {
            var leftCls  = 'build-talent-cell build-talent-left';
            var rightCls = 'build-talent-cell build-talent-right';
            return '<div class="build-talent-row">' +
                '<div class="' + leftCls  + '">' + (t.left_display || t.left  || '') + '</div>' +
                '<div class="build-talent-level-badge">' + (t.level || '') + '</div>' +
                '<div class="' + rightCls + '">' + (t.right_display || t.right || '') + '</div>' +
                '</div>';
        }).join('');
    }
    return '<div class="build-talent-tree">' + rows + '</div>';
}

function _buildItemsSectionHtml(dotaPos, data) {
    function resolveById(id) {
        var info = _itemsDb[String(id)] || {};
        return { dname: info.dname || ('Item ' + id), img: info.img || null };
    }

    // ── Стартовые ────────────────────────────────────────────────────────
    var startItems = [];
    if (dotaPos) {
        var starting = dotaPos.starting_items || [];
        if (starting.length && Array.isArray(starting[0][0])) {
            startItems = starting[0][0].map(resolveById);
        }
    } else {
        startItems = (data.items && data.items.start_game_items) || [];
    }

    function itemSlot(item) {
        return '<div class="build-item-slot">' +
            (item.img
                ? '<img src="' + item.img + '" class="build-item-icon" onerror="this.style.opacity=\'0.3\'">'
                : '<div class="build-item-icon"></div>') +
            '<span class="build-item-name">' + (item.dname || '') + '</span>' +
            '</div>';
    }

    function itemSlotPR(item, prPct) {
        return '<div class="build-item-slot">' +
            (item.img
                ? '<img src="' + item.img + '" class="build-item-icon" onerror="this.style.opacity=\'0.3\'">'
                : '<div class="build-item-icon"></div>') +
            '<span class="build-item-name">' + (item.dname || '') + '</span>' +
            '<span class="build-item-pick-rate">' + prPct + '</span>' +
            '</div>';
    }

    // ── Основные — из anchor_items ────────────────────────────────────────
    var coreHtml;
    if (dotaPos && dotaPos.anchor_items && dotaPos.anchor_items.length) {
        var anchorSorted = (dotaPos.anchor_items || []).slice()
            .sort(function (a, b) { return (a.avg_minute || 0) - (b.avg_minute || 0); });
        coreHtml = '<div class="build-items-grid">' +
            anchorSorted.map(function (e) {
                var info = resolveById(e.raw_item_id);
                var prPct = 'Берут ' + ((e.pr || 0) * 100).toFixed(0) + '%';
                var timeStr = e.avg_minute != null ? '~' + Math.round(e.avg_minute) + 'м' : '';
                return '<div class="build-item-slot">' +
                    (info.img
                        ? '<img src="' + info.img + '" class="build-item-icon" onerror="this.style.opacity=\'0.3\'">'
                        : '<div class="build-item-icon"></div>') +
                    '<span class="build-item-name">' + (info.dname || '') + '</span>' +
                    '<div class="build-item-anchor-stats">' +
                        '<span class="build-item-anchor-pr">' + prPct + '</span>' +
                        (timeStr ? '<span class="build-item-anchor-time">' + timeStr + '</span>' : '') +
                    '</div>' +
                    '</div>';
            }).join('') + '</div>';
    } else {
        // Fallback: sixslot pick_rate >= 0.4
        var sixslotCore = (dotaPos ? (dotaPos.sixslot || []) : [])
            .slice().sort(function (a, b) { return (b.pick_rate || 0) - (a.pick_rate || 0); })
            .filter(function (e) { return (e.pick_rate || 0) >= 0.4; })
            .slice(0, 6);
        if (sixslotCore.length) {
            coreHtml = '<div class="build-items-grid">' +
                sixslotCore.map(function (e) {
                    return itemSlotPR(resolveById(e.item_id), ((e.pick_rate || 0) * 100).toFixed(0) + '%');
                }).join('') + '</div>';
        } else {
            var fallbackCore = (data.items && data.items.core_items) || [];
            coreHtml = '<div class="build-items-grid">' + fallbackCore.map(itemSlot).join('') + '</div>';
        }
    }

    // ── Ситуативные — из sixslot ──────────────────────────────────────────
    var sixslot = dotaPos ? (dotaPos.sixslot || []) : [];
    var sixslotSorted = sixslot.slice().sort(function (a, b) { return (b.pick_rate || 0) - (a.pick_rate || 0); });
    var situSlots = sixslotSorted
        .filter(function (e) { var pr = e.pick_rate || 0; return pr >= 0.1 && pr < 0.4; });
    var situHtml = situSlots.length
        ? '<div class="build-items-grid">' +
            situSlots.map(function (e) {
                return itemSlotPR(resolveById(e.item_id), ((e.pick_rate || 0) * 100).toFixed(0) + '%');
            }).join('') + '</div>'
        : '<p class="build-placeholder">Нет данных</p>';

    // ── Нейтральные (neutral_stats = {"0": {itemId: {wins,count,win_rate,pick_rate}}, ...}) ────
    var neutralHtml = '';
    if (dotaPos && dotaPos.neutral_stats) {
        var tierBest = {};  // tier (str) → { itemId, pick_rate }
        Object.entries(dotaPos.neutral_stats || {}).forEach(function (tierEntry) {
            var tier  = tierEntry[0];  // "0".."4"
            var items = tierEntry[1];  // { itemId: {wins, count, win_rate, pick_rate} }
            var top = Object.entries(items || {})
                .sort(function (a, b) { return (b[1].pick_rate || 0) - (a[1].pick_rate || 0); })[0];
            if (top) tierBest[tier] = { itemId: top[0], pick_rate: top[1].pick_rate || 0 };
        });
        var tierLabels = ['Тир 1', 'Тир 2', 'Тир 3', 'Тир 4', 'Тир 5'];
        neutralHtml = '<div class="build-items-grid build-items-grid--neutral">' +
            [0, 1, 2, 3, 4].map(function (tier) {
                var best = tierBest[String(tier)];
                if (!best) {
                    return '<div class="build-item-slot build-item-slot--neutral">' +
                        '<div class="build-item-icon build-item-icon--neutral"></div>' +
                        '<span class="build-neutral-tier">' + tierLabels[tier] + '</span>' +
                        '<span class="build-item-pick-rate">—</span>' +
                        '</div>';
                }
                var info = resolveById(best.itemId);
                var prPct = ((best.pick_rate || 0) * 100).toFixed(0) + '%';
                return '<div class="build-item-slot build-item-slot--neutral">' +
                    (info.img
                        ? '<img src="' + info.img + '" class="build-item-icon build-item-icon--neutral" onerror="this.style.opacity=\'0.3\'" title="' + (info.dname || '') + '">'
                        : '<div class="build-item-icon build-item-icon--neutral"></div>') +
                    '<span class="build-neutral-tier">' + tierLabels[tier] + '</span>' +
                    '<span class="build-item-pick-rate">' + prPct + '</span>' +
                    '</div>';
            }).join('') +
            '</div>';
    }

    var tabDefs = [
        { tab: 'start',   label: 'Стартовые'   },
        { tab: 'core',    label: 'Основные'    },
        { tab: 'situ',    label: 'Ситуативные' },
        { tab: 'neutral', label: 'Нейтральные' },
    ];
    var tabBtns = tabDefs.map(function (td) {
        var activeCls = td.tab === _buildItemsTab ? ' active' : '';
        return '<button class="build-items-tab-btn' + activeCls + '" data-tab="' + td.tab + '" onclick="switchBuildItemsTab(\'' + td.tab + '\')">' + td.label + '</button>';
    }).join('');

    function makePanel(tab, innerHtml) {
        var display = tab === _buildItemsTab ? '' : 'none';
        return '<div class="build-items-panel" id="build-items-panel-' + tab + '" style="display:' + display + '">' + innerHtml + '</div>';
    }

    return '<div class="build-filter-segmented build-items-tabs-ctrl">' + tabBtns + '</div>' +
        makePanel('start',   '<div class="build-items-grid">' + startItems.map(itemSlot).join('') + '</div>') +
        makePanel('core',    coreHtml) +
        makePanel('situ',    situHtml) +
        makePanel('neutral', neutralHtml || '<p class="build-placeholder">Нет данных</p>');
}

// ── Основной рендер вкладки Сборка ───────────────────────────────────────

function renderBuildTab(data) {
    var el = document.getElementById('build-content');
    if (!el) return;

    var topPositions = _getTopPositionsFromBuilds(data);
    if (topPositions.length && topPositions.indexOf(_buildPosition) === -1) {
        _buildPosition = topPositions[0];
    }
    if (_buildHeroId && _buildPosition && typeof window.setRecentHeroPosition === 'function') {
        window.setRecentHeroPosition(_buildHeroId, _buildPosition);
    }

    var dotaPos = data.dota_builds && _buildPosition && data.dota_builds[_buildPosition];

    var posButtons = topPositions.map(function (pos) {
        var activeCls = pos === _buildPosition ? ' active' : '';
        var imgSrc = _DOTA_POS_IMG[pos] || _POSITION_IMG[pos] || '';
        var label  = _DOTA_POS_LABELS[pos] || _POSITION_LABELS[pos] || pos;
        var posData = data.dota_builds && data.dota_builds[pos];
        var wrStr = (posData && posData.win_rate != null)
            ? '<span class="build-pos-winrate">' + (posData.win_rate * 100).toFixed(1) + '%</span>'
            : '';
        return '<button class="build-pos-btn' + activeCls + '" data-pos="' + pos + '" onclick="selectBuildPosition(\'' + pos + '\')">' +
            '<img src="' + imgSrc + '" class="build-pos-icon" onerror="this.style.display=\'none\'">' +
            '<span class="build-filter-name">' + label + '</span>' +
            wrStr +
            '</button>';
    }).join('');

    var talentsHtml = _buildTalentsHtml(dotaPos, data);
    var talentsSection = talentsHtml
        ? '<div class="build-section-divider"></div>' +
          '<div class="build-section">' +
              '<div class="build-section-label">ТАЛАНТЫ</div>' +
              talentsHtml +
          '</div>'
        : '';

    el.innerHTML =
        '<div class="build-filters">' +
            '<div class="build-filter-segmented">' + posButtons + '</div>' +
        '</div>' +
        '<div class="build-section">' +
            '<div class="build-section-label">ПРОКАЧКА</div>' +
            _buildSkillRowHtml(dotaPos, data) +
        '</div>' +
        talentsSection +
        '<div class="build-section-divider"></div>' +
        '<div class="build-section">' +
            '<div class="build-section-label">ПРЕДМЕТЫ</div>' +
            _buildItemsSectionHtml(dotaPos, data) +
        '</div>';
}

async function loadHeroBuild(heroId) {
    if (!_itemsDbLoaded) await _loadItemsDb();
    _buildHeroId = heroId;
    _showBuildLoading();
    try {
        var response = await fetch(window.API_BASE_URL + '/hero/' + heroId + '/build');
        if (!response.ok) throw new Error('HTTP ' + response.status);
        var data = await response.json();
        if (_buildHeroId !== heroId) return;  // hero changed while loading
        _buildData = data;
        renderBuildTab(data);
        // Обновляем винрейт в шапке из dota_builds если есть
        if (data.dota_builds) {
            var totalWins = 0, totalMatches = 0;
            Object.values(data.dota_builds).forEach(function (pos) {
                totalWins    += (pos.num_wins    || 0);
                totalMatches += (pos.num_matches || 0);
            });
            if (totalMatches > 0) {
                var wrPct = (totalWins / totalMatches * 100).toFixed(1);
                var wrEl = document.getElementById('matchup-hero-winrate');
                if (wrEl) {
                    wrEl.textContent = 'Винрейт: ' + wrPct + '% · ' + totalMatches.toLocaleString('ru-RU') + ' игр';
                }
            }
        }
    } catch (err) {
        console.error('[build] loadHeroBuild error:', err);
        var el = document.getElementById('build-content');
        if (el) el.innerHTML = '<p class="matchup-placeholder-text">Не удалось загрузить данные сборки</p>';
    }
}

// ---------- Matchups: загрузка и рендер ----------

// Кэш загруженных данных — нужен для рендера при переключении вкладок без повторных запросов
var _countersData = null;
var _synergyData  = null;
var _activeCountersTab = 'strong';
var _activeSynergyTab  = 'best';

function showMatchupsLoading() {
    _countersData = null;
    _synergyData  = null;
    _activeCountersTab = 'strong';
    _activeSynergyTab  = 'best';

    var cEl = document.getElementById('counters-list');
    var sEl = document.getElementById('synergy-list');
    if (cEl) cEl.innerHTML = '<p class="matchup-placeholder-text">Загрузка...</p>';
    if (sEl) sEl.innerHTML = '<p class="matchup-placeholder-text">Загрузка...</p>';

    var wrEl = document.getElementById('matchup-hero-winrate');
    if (wrEl) wrEl.textContent = '';

    // Сбрасываем активные кнопки в дефолт
    var cStrong = document.getElementById('counter-tab-btn-strong');
    var cWeak   = document.getElementById('counter-tab-btn-weak');
    if (cStrong) cStrong.classList.add('active');
    if (cWeak)   cWeak.classList.remove('active');

    var sBest  = document.getElementById('synergy-tab-btn-best');
    var sWorst = document.getElementById('synergy-tab-btn-worst');
    if (sBest)  sBest.classList.add('active');
    if (sWorst) sWorst.classList.remove('active');
}

function showMatchupsError(msg) {
    var el = document.getElementById('counters-list');
    if (el) el.innerHTML = '<p class="matchup-placeholder-text">' + (msg || 'Не удалось загрузить матчапы. Попробуй позже.') + '</p>';
}

function showSynergyError(msg) {
    var el = document.getElementById('synergy-list');
    if (el) el.innerHTML = '<p class="matchup-placeholder-text">' + (msg || 'Недостаточно матчей для оценки синергии.') + '</p>';
}

function renderMatchupList(containerId, positiveItems, negativeItems, baseWr, labels) {
    var container = document.getElementById(containerId);
    if (!container) return;

    var posLabel = (labels && labels.positive) || 'сильнее';
    var negLabel = (labels && labels.negative) || 'избегать';

    function enrichAndSort(list, desc) {
        var out = [];
        if (!list) return out;
        for (var i = 0; i < list.length; i++) {
            var entry = list[i];
            var heroName = window.dotaHeroIdToName && window.dotaHeroIdToName[entry.hero_id];
            if (!heroName) continue;
            var base = (baseWr != null) ? baseWr : 0.5;
            var delta = entry.wr_vs - base;
            out.push({ entry: entry, heroName: heroName, delta: delta });
        }
        out.sort(function (a, b) { return desc ? b.delta - a.delta : a.delta - b.delta; });
        return out;
    }

    var pos = enrichAndSort(positiveItems, true);
    var neg = enrichAndSort(negativeItems, false);

    if (pos.length === 0 && neg.length === 0) {
        container.classList.remove('expanded');
        container.innerHTML = '<p class="matchup-placeholder-text">Недостаточно данных (мало игр)</p>';
        return;
    }

    var TOP = 3;

    function formatGames(n) {
        if (n >= 10000) return Math.round(n / 1000) + 'k';
        if (n >= 1000)  return (n / 1000).toFixed(1).replace(/\.0$/, '') + 'k';
        return n.toLocaleString('ru-RU');
    }

    function renderRow(item, isTop, polarity, isExtra) {
        var iconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(item.heroName) : '';
        var deltaPct = item.delta * 100;
        var sign = deltaPct > 0 ? '+' : '';
        var cssClass = polarity;
        if (Math.abs(deltaPct) <= 2) cssClass = 'neutral';
        var deltaStr = sign + Math.round(deltaPct) + '%';
        var gamesStr = formatGames(item.entry.games) + ' игр';
        var topCls = isTop ? ' matchup-item--top' : '';
        var extraCls = isExtra ? ' matchup-item--extra' : '';
        return '<div class="matchup-item ' + cssClass + topCls + extraCls + '">' +
                '<div class="matchup-item-left">' +
                    '<img src="' + iconUrl + '" alt="" class="matchup-item-icon" onerror="this.style.display=\'none\'">' +
                    '<span class="matchup-item-name">' + item.heroName + '</span>' +
                '</div>' +
                '<div class="matchup-item-right">' +
                    '<span class="matchup-item-delta">' + deltaStr + '</span>' +
                    '<span class="matchup-item-games">' + gamesStr + '</span>' +
                '</div>' +
            '</div>';
    }

    var html = '';
    if (pos.length > 0) {
        html += '<div class="matchup-signed-divider"><span>' + posLabel + '</span></div>';
        for (var i = 0; i < pos.length; i++) {
            html += renderRow(pos[i], i === 0, 'positive', i >= TOP);
        }
    }
    if (neg.length > 0) {
        html += '<div class="matchup-signed-divider"><span>' + negLabel + '</span></div>';
        for (var j = 0; j < neg.length; j++) {
            html += renderRow(neg[j], j === 0, 'negative', j >= TOP);
        }
    }

    var extra = Math.max(0, pos.length - TOP) + Math.max(0, neg.length - TOP);
    var collapsedLabel = 'показать ещё ' + extra + ' \u2192';
    var expandedLabel  = 'свернуть \u2191';
    if (extra > 0) {
        html += '<button class="matchup-expand-btn" type="button">' + collapsedLabel + '</button>';
    }

    container.classList.remove('expanded');
    container.innerHTML = html;

    var btn = container.querySelector('.matchup-expand-btn');
    if (btn) {
        btn.addEventListener('click', function () {
            var isExpanded = container.classList.toggle('expanded');
            btn.textContent = isExpanded ? expandedLabel : collapsedLabel;
        });
    }
}

async function loadHeroMatchups(heroId) {
    var LIMIT = 5;

    async function fetchCounters(minGames) {
        var response = await fetch(window.API_BASE_URL + '/hero/' + heroId + '/counters?limit=' + LIMIT + '&min_games=' + minGames);
        if (!response.ok) {
            var text = await response.text().catch(function () { return ''; });
            var error = new Error('HTTP ' + response.status);
            error.status = response.status;
            error.body = text;
            throw error;
        }
        return response.json();
    }

    showMatchupsLoading();
    try {
        var data;
        try {
            data = await fetchCounters(50);
        } catch (err) {
            if (err.status === 503) {
                console.warn('[matchups] No data for min_games=50, trying 20');
                data = await fetchCounters(20);
            } else {
                throw err;
            }
        }

        // Fallback for sparse results: if fewer than 4 rows total survived the
        // min_games filter (can happen when a hero has very few matches in the DB),
        // retry with a lower threshold so we show something meaningful.
        var totalRows = ((data.counters || []).length) + ((data.victims || []).length);
        if (totalRows < 4) {
            console.warn('[matchups] Sparse result (' + totalRows + ' rows at min_games=50), retrying with min_games=20');
            try {
                data = await fetchCounters(20);
            } catch (retryErr) {
                console.warn('[matchups] Sparse-retry failed, keeping previous data:', retryErr);
            }
        }

        var wrEl = document.getElementById('matchup-hero-winrate');
        if (wrEl) {
            if (data.base_winrate != null) {
                var wrPct = Math.round(data.base_winrate * 100);
                var gamesStr = data.data_games != null ? ' по ' + data.data_games.toLocaleString('ru-RU') + ' играм' : '';
                wrEl.textContent = 'Базовый винрейт: ' + wrPct + '%' + gamesStr;
            } else {
                wrEl.textContent = '';
            }
        }

        _countersData = data;
        renderMatchupList('counters-list', data.victims, data.counters, data.base_winrate,
            { positive: 'силён против', negative: 'слаб против' });
    } catch (err) {
        console.error('[matchups] loadHeroMatchups error:', err);
        showMatchupsError();
    }
}

async function loadHeroSynergy(heroId) {
    var LIMIT = 5;

    async function fetchSynergy(minGames) {
        var response = await fetch(window.API_BASE_URL + '/hero/' + heroId + '/synergy?limit=' + LIMIT + '&min_games=' + minGames);
        if (!response.ok) {
            var error = new Error('HTTP ' + response.status);
            error.status = response.status;
            throw error;
        }
        return response.json();
    }

    try {
        var data;
        try {
            data = await fetchSynergy(50);
        } catch (err) {
            if (err.status === 503) {
                console.warn('[synergy] No data for min_games=50, trying 20');
                data = await fetchSynergy(20);
            } else {
                throw err;
            }
        }

        // Fallback for sparse results
        var totalRows = ((data.best_allies || []).length) + ((data.worst_allies || []).length);
        if (totalRows < 4) {
            console.warn('[synergy] Sparse result (' + totalRows + ' rows), retrying with min_games=20');
            try {
                data = await fetchSynergy(20);
            } catch (retryErr) {
                console.warn('[synergy] Sparse-retry failed, keeping previous data:', retryErr);
            }
        }

        _synergyData = data;
        renderMatchupList('synergy-list', data.best_allies, data.worst_allies, data.base_winrate,
            { positive: 'силён с', negative: 'слаб с' });
    } catch (err) {
        console.error('[synergy] loadHeroSynergy error:', err);
        showSynergyError();
    }
}

// Привязка событий для поиска и подсказок
(function () {
    // Событие ввода текста — через addEventListener, чтобы работало и на desktop
    var inputEl = document.getElementById('matchup-hero-input');
    if (inputEl) {
        inputEl.addEventListener('input', function () {
            matchupPage.onInput(this.value);
        });
    }

    // Делегирование кликов по подсказкам
    var suggestionsEl = document.getElementById('matchup-suggestions');
    if (suggestionsEl) {
        suggestionsEl.addEventListener('click', function (e) {
            var item = e.target.closest('.matchup-suggestion-item');
            if (!item) return;
            var heroName = item.dataset.heroName;
            if (heroName) matchupPage.selectHero(heroName);
        });
    }
}());

// Закрытие подсказок при клике вне поля поиска
document.addEventListener('click', function (e) {
    if (!e.target.closest('.matchup-search-wrap')) {
        var suggestionsEl = document.getElementById('matchup-suggestions');
        if (suggestionsEl) {
            suggestionsEl.innerHTML = '';
            suggestionsEl.style.display = 'none';
        }
    }
});

// ---------- Переключатель вкладок: Контрпики ----------
function switchCountersTab(tab) {
    _activeCountersTab = tab;

    var btnStrong = document.getElementById('counter-tab-btn-strong');
    var btnWeak   = document.getElementById('counter-tab-btn-weak');
    if (btnStrong) btnStrong.classList.toggle('active', tab === 'strong');
    if (btnWeak)   btnWeak.classList.toggle('active',   tab === 'weak');

    if (_countersData) {
        var items = tab === 'strong' ? _countersData.victims : _countersData.counters;
        var type  = tab === 'strong' ? 'strong' : 'weak';
        renderMatchupList('counters-list', items, type, _countersData.base_winrate);
    }
}

// ---------- Переключатель вкладок: Синергия ----------
function switchSynergyTab(tab) {
    _activeSynergyTab = tab;

    var btnBest  = document.getElementById('synergy-tab-btn-best');
    var btnWorst = document.getElementById('synergy-tab-btn-worst');
    if (btnBest)  btnBest.classList.toggle('active',  tab === 'best');
    if (btnWorst) btnWorst.classList.toggle('active', tab === 'worst');

    if (_synergyData) {
        var items = tab === 'best' ? _synergyData.best_allies : _synergyData.worst_allies;
        var type  = tab === 'best' ? 'strong' : 'weak';
        renderMatchupList('synergy-list', items, type, _synergyData.base_winrate);
    }
}


// ========== НЕДАВНИЕ ГЕРОИ ==========

(function () {
    var RECENT_KEY = 'recent_heroes';
    var MAX_RECENT = 7;

    var _heroIdToName = null;
    function getHeroIdToName() {
        if (_heroIdToName) return _heroIdToName;
        _heroIdToName = {};
        if (window.dotaHeroIds) {
            Object.keys(window.dotaHeroIds).forEach(function (name) {
                var id = window.dotaHeroIds[name];
                if (!_heroIdToName[id]) _heroIdToName[id] = name;
            });
        }
        return _heroIdToName;
    }

    // Read list — entries are {id, pos?}. Accepts legacy plain-id arrays too.
    function readList() {
        try {
            var raw = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
            if (!Array.isArray(raw)) return [];
            return raw.map(function (e) {
                if (typeof e === 'number') return { id: e, pos: null };
                if (e && typeof e === 'object' && e.id) return { id: e.id, pos: e.pos || null };
                return null;
            }).filter(Boolean);
        } catch (e) { return []; }
    }

    function writeList(list) {
        try { localStorage.setItem(RECENT_KEY, JSON.stringify(list)); } catch (e) {}
    }

    window.getRecentHeroes = readList;

    window.addRecentHero = function (heroId, position) {
        if (!heroId) return;
        var list = readList();
        var existing = list.find(function (e) { return e.id === heroId; });
        var pos = position || (existing && existing.pos) || null;
        list = list.filter(function (e) { return e.id !== heroId; });
        list.unshift({ id: heroId, pos: pos });
        if (list.length > MAX_RECENT) list = list.slice(0, MAX_RECENT);
        writeList(list);
    };

    window.setRecentHeroPosition = function (heroId, position) {
        if (!heroId || !position) return;
        var list = readList();
        var idx = list.findIndex(function (e) { return e.id === heroId; });
        if (idx === -1) return;
        list[idx] = { id: heroId, pos: position };
        writeList(list);
    };

    window.renderRecentHeroes = function () {
        var block = document.getElementById('recent-heroes-block');
        var listEl = document.getElementById('recent-heroes-list');
        if (!block || !listEl) return;

        var list = readList();

        if (!list.length) {
            block.style.display = 'none';
            return;
        }

        var idToName = getHeroIdToName();
        var items = list.map(function (e) {
            return idToName[e.id] ? { id: e.id, name: idToName[e.id] } : null;
        }).filter(Boolean).slice(0, 5);

        if (!items.length) {
            block.style.display = 'none';
            return;
        }

        // Center-outward delays: index 2 first, then 1&3, then 0&4
        var centerOutwardDelays = [0.24, 0.12, 0, 0.12, 0.24];

        block.style.display = 'block';
        listEl.innerHTML = items.map(function (hero, idx) {
            var iconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(hero.name) : '';
            var escaped = hero.name.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
            var delay = centerOutwardDelays[idx] !== undefined ? centerOutwardDelays[idx] : 0;
            return '<div class="recent-hero-item" data-hero-name="' + escaped + '" style="--rh-delay:' + delay + 's">' +
                '<div class="recent-hero-icon-wrap">' +
                  '<img src="' + iconUrl + '" alt="' + escaped + '" class="recent-hero-icon" onerror="this.style.display=\'none\'">' +
                '</div>' +
                '<div class="recent-hero-name">' + hero.name + '</div>' +
            '</div>';
        }).join('');

        listEl.querySelectorAll('.recent-hero-item').forEach(function (el) {
            el.addEventListener('click', function () {
                var name = el.dataset.heroName;
                if (name) matchupPage.selectHero(name);
            });
        });
    };
}());

// ========== ФИДБЕК ==========

// Состояние страницы фидбека
var _feedbackRating = null;
var _feedbackTags   = new Set();
var _prevPageBeforeFeedback = 'home';

function goToFeedback() {
    // Запоминаем, откуда пришли, чтобы вернуться
    var activePage = document.querySelector('.page.active');
    _prevPageBeforeFeedback = activePage ? activePage.id.replace('page-', '') : 'home';

    document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
    document.getElementById('page-feedback').classList.add('active');

    // Убираем активную метку с нав-элементов
    document.querySelectorAll('.nav-item').forEach(function(n) { n.classList.remove('active'); });

    // Сбрасываем форму
    _resetFeedbackForm();
}

function goBackFromFeedback() {
    document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
    var target = document.getElementById('page-' + _prevPageBeforeFeedback) ||
                 document.getElementById('page-home');
    target.classList.add('active');

    // Восстанавливаем нав-элемент
    var navMap = { home: 0, quiz: 1, drafter: 2, database: 3, profile: 4 };
    var navIdx = navMap[_prevPageBeforeFeedback];
    if (navIdx !== undefined) {
        var navItems = document.querySelectorAll('.nav-item');
        if (navItems[navIdx]) navItems[navIdx].classList.add('active');
    } else {
        document.querySelectorAll('.nav-item')[0].classList.add('active');
    }
}

function selectRating(value) {
    _feedbackRating = value;
    document.querySelectorAll('.feedback-rating-btn').forEach(function(btn) {
        btn.classList.toggle('selected', parseInt(btn.dataset.rating) === value);
    });
    _clearFeedbackStatus();
}

function toggleTag(tag) {
    var btn = document.querySelector('.feedback-tag-chip[data-tag="' + tag + '"]');
    if (_feedbackTags.has(tag)) {
        _feedbackTags.delete(tag);
        if (btn) btn.classList.remove('selected');
    } else {
        _feedbackTags.add(tag);
        if (btn) btn.classList.add('selected');
    }
}

function _clearFeedbackStatus() {
    var el = document.getElementById('feedback-status');
    if (el) { el.textContent = ''; el.className = 'feedback-status'; }
}

function _setFeedbackStatus(text, type) {
    var el = document.getElementById('feedback-status');
    if (!el) return;
    el.textContent = text;
    el.className = 'feedback-status ' + (type || '');
}

function _resetFeedbackForm() {
    _feedbackRating = null;
    _feedbackTags.clear();

    document.querySelectorAll('.feedback-rating-btn').forEach(function(b) { b.classList.remove('selected'); });
    document.querySelectorAll('.feedback-tag-chip').forEach(function(b) { b.classList.remove('selected'); });

    var ta = document.getElementById('feedback-message');
    if (ta) ta.value = '';

    var cc = document.getElementById('feedback-char-count');
    if (cc) cc.textContent = '0 / 500';

    _clearFeedbackStatus();

    var btn = document.getElementById('feedback-submit-btn');
    if (btn) { btn.disabled = false; btn.textContent = 'Отправить'; }
}

// Счётчик символов в textarea
(function() {
    document.addEventListener('DOMContentLoaded', function() {
        var ta = document.getElementById('feedback-message');
        var cc = document.getElementById('feedback-char-count');
        if (ta && cc) {
            ta.addEventListener('input', function() {
                cc.textContent = ta.value.length + ' / 500';
            });
        }
    });
})();

async function submitFeedback() {
    var btn = document.getElementById('feedback-submit-btn');
    var ta  = document.getElementById('feedback-message');

    if (!_feedbackRating) {
        _setFeedbackStatus('Выбери оценку 👆', 'hint');
        return;
    }

    var message = (ta ? ta.value : '').trim();
    if (!message) {
        _setFeedbackStatus('Напиши хотя бы пару слов в комментарии 🙏', 'hint');
        return;
    }

    if (!USER_TOKEN) {
        _setFeedbackStatus('Не удалось отправить — токен не найден. Открой мини‑апп через бота.', 'err');
        return;
    }

    if (btn) { btn.disabled = true; btn.textContent = 'Отправка…'; }
    _clearFeedbackStatus();

    try {
        var resp = await fetch(`${window.API_BASE_URL}/feedback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                token: USER_TOKEN,
                rating: _feedbackRating,
                tags: Array.from(_feedbackTags),
                message: message,
            }),
        });

        if (resp.ok) {
            _setFeedbackStatus('Спасибо за отзыв ❤️', 'ok');
            _feedbackRating = null;
            _feedbackTags.clear();
            document.querySelectorAll('.feedback-rating-btn').forEach(function(b) { b.classList.remove('selected'); });
            document.querySelectorAll('.feedback-tag-chip').forEach(function(b) { b.classList.remove('selected'); });
            if (ta) ta.value = '';
            var cc = document.getElementById('feedback-char-count');
            if (cc) cc.textContent = '0 / 500';
            if (btn) { btn.disabled = false; btn.textContent = 'Отправить'; }
        } else {
            try { await resp.json(); } catch (_) {}
            if (resp.status === 401) {
                _setFeedbackStatus('Сессия устарела — открой мини‑апп через бота заново.', 'err');
            } else {
                _setFeedbackStatus('Не удалось отправить, попробуй ещё раз позже.', 'err');
            }
            if (btn) { btn.disabled = false; btn.textContent = 'Отправить'; }
        }
    } catch (e) {
        console.error('Feedback submit error:', e);
        _setFeedbackStatus('Не удалось отправить, попробуй ещё раз позже.', 'err');
        if (btn) { btn.disabled = false; btn.textContent = 'Отправить'; }
    }
}

// ========== DONATE ==========

function goToDonate() {
    document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
    document.getElementById('page-donate').classList.add('active');
    document.querySelectorAll('.nav-item').forEach(function(n) { n.classList.remove('active'); });
}

function goBackFromDonate() {
    document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
    document.getElementById('page-home').classList.add('active');
    document.querySelectorAll('.nav-item')[0].classList.add('active');
}

function openDonationAlerts() {
    var tg = window.Telegram && window.Telegram.WebApp;
    var url = 'https://www.donationalerts.com/r/kasumi_dota';
    if (tg && typeof tg.openLink === 'function') {
        tg.openLink(url);
    } else {
        window.open(url, '_blank');
    }
}

// ========== HOME SCREEN — МЕТА / ВИДЖЕТЫ ==========

var _metaCache = null;

var _META_POS_LABELS = {
    'POSITION_1': 'Керри',
    'POSITION_2': 'Мид',
    'POSITION_3': 'Оффлейн',
    'POSITION_4': 'Четвёрка',
    'POSITION_5': 'Пятёрка',
};

var _META_POS_IMG = {
    'POSITION_1': '/images/positions/pos_1.png',
    'POSITION_2': '/images/positions/pos_2.png',
    'POSITION_3': '/images/positions/pos_3.png',
    'POSITION_4': '/images/positions/pos_4.png',
    'POSITION_5': '/images/positions/pos_5.png',
};

var _HOME_POS_ORDER = ['POSITION_1', 'POSITION_2', 'POSITION_3', 'POSITION_4', 'POSITION_5'];

function _metaHeroClick(heroName) {
    document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
    document.getElementById('page-database').classList.add('active');
    document.querySelectorAll('.nav-item').forEach(function(n) { n.classList.remove('active'); });
    var navItems = document.querySelectorAll('.nav-item');
    if (navItems[3]) navItems[3].classList.add('active');
    _heroPageActiveTab = 'build';
    matchupPage.selectHero(heroName);
}

function _escHtml(s) {
    if (s == null) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function loadMeta() {
    if (_metaCache) {
        _renderHomeMeta(_metaCache);
        return;
    }
    var API = window.API_BASE_URL || '/api';
    fetch(API + '/meta')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            _metaCache = data;
            _renderHomeMeta(data);
        })
        .catch(function(e) {
            console.warn('[meta] failed to load:', e);
        });
}

// ── META: carousel ───────────────────────────────────────────────────
var _metaSlides = [];
var _metaActiveIdx = 0;
var _metaAutoTimer = null;
var _metaInteracted = false;
var _metaReducedMotion = false;
var _metaDragStartX = 0;
var _metaDragActive = false;
var _metaDragDX = 0;

// PATCH VERSION — обновлять вручную при выходе нового патча
const CURRENT_PATCH = '7.41b';

function _resolveMetaPatch(data) {
    return CURRENT_PATCH;
}

function _renderHomeMeta(data) {
    var slidesEl = document.getElementById('home-meta-slides');
    var dots = document.getElementById('home-meta-dots');
    var patchEl = document.getElementById('home-meta-patch');
    if (!slidesEl || !dots) return;

    var patch = _resolveMetaPatch(data);
    if (patchEl) patchEl.textContent = patch || '—';

    var positions = (data && data.positions) || {};
    var slides = [];
    _HOME_POS_ORDER.forEach(function(posKey) {
        var arr = positions[posKey];
        if (!arr || !arr.length) return;
        slides.push({ posKey: posKey, heroes: arr.slice(0, 5) });
    });

    if (!slides.length) {
        slidesEl.innerHTML = '<div class="home-meta-skeleton"></div>';
        dots.innerHTML = '';
        return;
    }

    _metaSlides = slides;
    _metaActiveIdx = 0;

    var slidesHtml = slides.map(function(s, i) {
        var posImg = _META_POS_IMG[s.posKey] || '';
        var posLabel = _META_POS_LABELS[s.posKey] || '';
        var cls = 'home-meta-slide' + (i === 0 ? ' is-active' : '');
        var heroesHtml = s.heroes.map(function(h) {
            var heroName = (window.dotaHeroIdToName && window.dotaHeroIdToName[h.hero_id]) || ('Hero #' + h.hero_id);
            var iconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(heroName) : '';
            var wrPct = Math.round((h.win_rate || 0) * 100);
            return (
                '<button class="home-meta-hero" data-hero-name="' + _escHtml(heroName) + '" aria-label="' + _escHtml(heroName) + '">' +
                    '<div class="home-meta-hero-icon">' +
                        '<img src="' + _escHtml(iconUrl) + '" alt="" onerror="this.style.display=\'none\'">' +
                    '</div>' +
                    '<div class="home-meta-hero-wr">' + wrPct + '%</div>' +
                '</button>'
            );
        }).join('');
        return (
            '<div class="' + cls + '" data-idx="' + i + '" role="tabpanel">' +
                '<div class="home-meta-slide-pos">' +
                    '<img class="home-meta-pos-icon" src="' + _escHtml(posImg) + '" alt="" onerror="this.style.display=\'none\'">' +
                    _escHtml(posLabel) +
                '</div>' +
                '<div class="home-meta-grid">' + heroesHtml + '</div>' +
            '</div>'
        );
    }).join('');

    slidesEl.innerHTML = slidesHtml;

    var dotsHtml = slides.map(function(_, i) {
        return '<button class="home-meta-dot' + (i === 0 ? ' is-active' : '') +
               '" data-idx="' + i + '" role="tab" aria-label="Слайд ' + (i + 1) + '"></button>';
    }).join('');
    dots.innerHTML = dotsHtml;

    _bindHomeMetaInteractions(slidesEl, dots);
    _startHomeMetaAutoplay();
}

function _bindHomeMetaInteractions(slidesEl, dots) {
    _metaReducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    dots.querySelectorAll('.home-meta-dot').forEach(function(btn) {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            var idx = parseInt(btn.getAttribute('data-idx'), 10);
            _metaInteracted = true;
            _stopHomeMetaAutoplay();
            _setMetaSlide(idx);
        });
    });

    slidesEl.querySelectorAll('.home-meta-hero').forEach(function(heroBtn) {
        heroBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            if (Math.abs(_metaDragDX) > 6) return;
            var name = heroBtn.getAttribute('data-hero-name');
            if (name) _metaHeroClick(name);
        });
    });

    var onDown = function(e) {
        _metaDragActive = true;
        _metaDragDX = 0;
        _metaDragStartX = (e.touches ? e.touches[0].clientX : e.clientX);
        _metaInteracted = true;
        _stopHomeMetaAutoplay();
    };
    var onMove = function(e) {
        if (!_metaDragActive) return;
        var x = (e.touches ? e.touches[0].clientX : e.clientX);
        _metaDragDX = x - _metaDragStartX;
    };
    var onUp = function() {
        if (!_metaDragActive) return;
        _metaDragActive = false;
        var threshold = 32;
        if (_metaDragDX <= -threshold) _setMetaSlide(_metaActiveIdx + 1);
        else if (_metaDragDX >= threshold) _setMetaSlide(_metaActiveIdx - 1);
        setTimeout(function() { _metaDragDX = 0; }, 50);
    };

    slidesEl.addEventListener('touchstart', onDown, { passive: true });
    slidesEl.addEventListener('touchmove', onMove, { passive: true });
    slidesEl.addEventListener('touchend', onUp);
    slidesEl.addEventListener('mousedown', onDown);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
}

function _metaNavClick(dir) {
    if (!_metaSlides.length) return;
    _metaInteracted = true;
    _stopHomeMetaAutoplay();
    _setMetaSlide(_metaActiveIdx + (dir > 0 ? 1 : -1));
    _startHomeMetaAutoplay();
}

function _setMetaSlide(idx) {
    if (!_metaSlides.length) return;
    var n = _metaSlides.length;
    var next = ((idx % n) + n) % n;
    if (next === _metaActiveIdx) return;

    var slidesEl = document.getElementById('home-meta-slides');
    var dots = document.getElementById('home-meta-dots');
    if (!slidesEl || !dots) return;

    var slides = slidesEl.querySelectorAll('.home-meta-slide');
    slides.forEach(function(el, i) {
        el.classList.remove('is-active', 'is-prev');
        if (i === next) el.classList.add('is-active');
        else if (i === _metaActiveIdx) el.classList.add('is-prev');
    });
    dots.querySelectorAll('.home-meta-dot').forEach(function(b, i) {
        b.classList.toggle('is-active', i === next);
    });
    _metaActiveIdx = next;
}

function _startHomeMetaAutoplay() {
    _stopHomeMetaAutoplay();
    if (_metaReducedMotion) return;
    // Autoplay disabled — manual nav only (arrows + swipe).
    // _metaAutoTimer = setInterval(function() {
    //     if (_metaInteracted) return;
    //     if (document.hidden) return;
    //     var homePage = document.getElementById('page-home');
    //     if (!homePage || !homePage.classList.contains('active')) return;
    //     _setMetaSlide(_metaActiveIdx + 1);
    // }, 3800);
}

function _stopHomeMetaAutoplay() {
    if (_metaAutoTimer) { clearInterval(_metaAutoTimer); _metaAutoTimer = null; }
}

// ── Аватар пользователя ──────────────────────────────────────────────
function _renderHomeAvatar() {
    var el = document.getElementById('home-avatar');
    if (!el) return;
    try {
        var tg = window.Telegram && window.Telegram.WebApp;
        var user = tg && tg.initDataUnsafe && tg.initDataUnsafe.user;
        var url = user && user.photo_url;
        if (url) {
            el.innerHTML = '<img src="' + _escHtml(url) + '" alt="">';
        }
    } catch (e) {}
}

// ── Виджет: последний герой ──────────────────────────────────────────
var _JUNK_ITEM_IDS = { 0:1, 44:1, 45:1, 46:1, 42:1, 43:1, 185:1, 145:1, 244:1 };

function _getLastHeroEntry() {
    var list = (typeof window.getRecentHeroes === 'function') ? window.getRecentHeroes() : [];
    var head = (list && list.length) ? list[0] : null;
    console.log('[_getLastHeroEntry] recent_heroes =', list, 'head =', head);
    return head;
}

function _getLastHeroId() {
    var e = _getLastHeroEntry();
    return e ? e.id : null;
}

var _HOME_HERO_LAST = null; // { heroId, build } — kept so we can re-render when items_db arrives

function _loadHomeHeroWidget() {
    var body = document.getElementById('home-hero-body');
    var widget = document.getElementById('home-hero-widget');
    if (!body || !widget) return;

    var heroId = _getLastHeroId();
    if (!heroId) {
        widget.disabled = true;
        body.innerHTML = '<div class="home-hero-placeholder">Открой любого героя</div>';
        return;
    }

    widget.disabled = false;
    widget.dataset.heroId = heroId;
    var API = window.API_BASE_URL || '/api';
    fetch(API + '/hero/' + heroId + '/build')
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
            if (!data) {
                body.innerHTML = '<div class="home-hero-placeholder">Данные недоступны</div>';
                return;
            }
            _HOME_HERO_LAST = { heroId: heroId, build: data };
            _renderHomeHeroWidget(heroId, data);
        })
        .catch(function(e) {
            console.warn('[home hero] failed:', e);
            body.innerHTML = '<div class="home-hero-placeholder">Нет подключения</div>';
        });
}

// Pick dota_builds position key (pos%20N): saved recent pos first, else max num_matches.
// savedPos may be in dota format ("pos%201") or stratz format ("POSITION_1").
function _pickHomeHeroDotaPos(heroId, dotaBuilds, savedPos) {
    if (!dotaBuilds) return null;
    if (savedPos) {
        if (dotaBuilds[savedPos]) {
            console.log('[home hero]', heroId, 'position from recent_heroes:', savedPos);
            return savedPos;
        }
        var mapped = _STRATZ_POS_TO_DOTA[savedPos];
        if (mapped && dotaBuilds[mapped]) {
            console.log('[home hero]', heroId, 'position from recent_heroes (mapped):', savedPos, '->', mapped);
            return mapped;
        }
        console.log('[home hero]', heroId, 'saved pos', savedPos, 'not in dota_builds, falling back');
    }
    var best = null;
    Object.keys(dotaBuilds).forEach(function(k) {
        var entry = dotaBuilds[k] || {};
        var nm = entry.num_matches || 0;
        if (!best || nm > best.nm) best = { key: k, nm: nm };
    });
    if (best) {
        console.log('[home hero]', heroId, 'position from max num_matches:', best.key, '(' + best.nm + ' matches)');
        return best.key;
    }
    console.log('[home hero]', heroId, 'no position resolved — dota_builds empty');
    return null;
}

function _renderHomeHeroWidget(heroId, build) {
    var body = document.getElementById('home-hero-body');
    if (!body) return;

    var heroName = (window.dotaHeroIdToName && window.dotaHeroIdToName[heroId]) || ('Hero #' + heroId);
    var iconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(heroName) : '';

    var db = build && build.dota_builds;
    // Backend-sorted list of pos keys by num_matches desc (uses sixslot sum fallback
    // for entries without a top-level num_matches field). First element = top pos.
    var sortedPositions = (build && build.positions) || [];
    var dotaPosKey = null;
    if (sortedPositions.length && db && db[sortedPositions[0]]) {
        dotaPosKey = sortedPositions[0];
    } else if (db) {
        var bestNm = -1;
        Object.keys(db).forEach(function (k) {
            if (k.indexOf('pos') !== 0) return;
            var entry = db[k] || {};
            var nm = entry.num_matches || 0;
            if (!nm && Array.isArray(entry.sixslot)) {
                nm = entry.sixslot.reduce(function (s, e) { return s + (e.num_matches || 0); }, 0);
            }
            if (nm > bestNm) { bestNm = nm; dotaPosKey = k; }
        });
    }
    var posData = dotaPosKey && db ? db[dotaPosKey] : null;

    var posNum = 1;
    if (dotaPosKey) {
        // Keys look like "pos%201" — %20 is a URL-encoded space, so /(\d)/
        // matches the "2" in "%20" first. Match the trailing position digit.
        var m = dotaPosKey.match(/(\d)$/);
        if (m) posNum = parseInt(m[1], 10);
    }
    var posKey = 'POSITION_' + posNum;
    var posImg = _META_POS_IMG[posKey] || '';
    var posLabel = _META_POS_LABELS[posKey] || '';
    var wrPct = (posData && typeof posData.win_rate === 'number') ? Math.round(posData.win_rate * 100) : null;

    var sixslot = ((posData && posData.sixslot) || [])
        .slice()
        .sort(function (a, b) { return (b.pick_rate || 0) - (a.pick_rate || 0); });
    var itemSlots = [];
    for (var i = 0; i < 6; i++) {
        var slot = sixslot[i];
        var itemId = slot && slot.item_id;
        var info = (itemId != null && _itemsDb) ? _itemsDb[String(itemId)] : null;
        if (info && info.img) {
            itemSlots.push('<div class="home-hero-item"><img src="' + _escHtml(info.img) + '" alt="' + _escHtml(info.dname || '') + '" onerror="this.style.display=\'none\'"></div>');
        } else {
            itemSlots.push('<div class="home-hero-item"></div>');
        }
    }

    var wrHtml = wrPct != null ? '<div class="home-hero-wr">' + wrPct + '%</div>' : '';

    body.innerHTML =
        '<div class="home-hero-head">' +
            '<div class="home-hero-icon"><img src="' + _escHtml(iconUrl) + '" alt="" onerror="this.style.display=\'none\'"></div>' +
            '<div class="home-hero-text">' +
                '<div class="home-hero-name">' + _escHtml(heroName) + '</div>' +
                '<div class="home-hero-pos">' +
                    '<img class="home-hero-pos-icon" src="' + _escHtml(posImg) + '" alt="" onerror="this.style.display=\'none\'">' +
                    _escHtml(posLabel) +
                '</div>' +
            '</div>' +
        '</div>' +
        wrHtml +
        '<div class="home-hero-items">' + itemSlots.join('') + '</div>';
}

function homeHeroWidgetClick() {
    var widget = document.getElementById('home-hero-widget');
    if (!widget || widget.disabled) return;
    var heroId = parseInt(widget.dataset.heroId || '0', 10);
    if (!heroId) return;
    var name = window.dotaHeroIdToName && window.dotaHeroIdToName[heroId];
    if (name) _metaHeroClick(name);
}

// ── Виджет: последний драфт ──────────────────────────────────────────
var _HOME_DRAFT_CACHE_KEY = 'home_last_draft_eval';

function cacheLastDraftEval(data) {
    try {
        localStorage.setItem(_HOME_DRAFT_CACHE_KEY, JSON.stringify({
            total_score: data.total_score,
            lane_score: data.lane_score,
            synergy_score: data.synergy_score,
            matchup_score: data.matchup_score,
            saved_at: Date.now(),
        }));
    } catch (e) {}
}

function _scoreRank(score) {
    if (score >= 85) return 'SSS';
    if (score >= 80) return 'S';
    if (score >= 65) return 'A';
    if (score >= 50) return 'B';
    return 'C';
}

function _formatDraftDate(iso) {
    if (!iso) return '';
    try {
        var d = new Date(iso);
        var now = new Date();
        var sameDay = d.toDateString() === now.toDateString();
        if (sameDay) {
            return d.getHours().toString().padStart(2, '0') + ':' + d.getMinutes().toString().padStart(2, '0');
        }
        return d.getDate().toString().padStart(2, '0') + '.' + (d.getMonth() + 1).toString().padStart(2, '0');
    } catch (e) { return ''; }
}

function _loadHomeDraftWidget() {
    var body = document.getElementById('home-draft-body');
    if (!body) return;

    var cached = null;
    try { cached = JSON.parse(localStorage.getItem(_HOME_DRAFT_CACHE_KEY) || 'null'); } catch (e) {}

    var token = (typeof USER_TOKEN !== 'undefined' && USER_TOKEN) ? USER_TOKEN : null;
    if (!token) {
        if (cached) _renderHomeDraftWidget(cached, null);
        else _renderHomeDraftEmpty();
        return;
    }

    var API = window.API_BASE_URL || '/api';
    fetch(API + '/draft/history?token=' + encodeURIComponent(token))
        .then(function(r) { return r.ok ? r.json() : []; })
        .then(function(list) {
            var last = (list && list.length) ? list[0] : null;
            _renderHomeDraftWidget(cached, last);
        })
        .catch(function(e) {
            console.warn('[home draft] failed:', e);
            if (cached) _renderHomeDraftWidget(cached, null);
            else _renderHomeDraftEmpty();
        });
}

function _renderHomeDraftEmpty() {
    var body = document.getElementById('home-draft-body');
    var cta = document.getElementById('home-draft-cta');
    if (!body) return;
    body.innerHTML = '<div class="home-draft-placeholder">Оцени свой первый драфт</div>';
    if (cta) cta.innerHTML = 'Оценить драфт <i class="ph ph-arrow-right" aria-hidden="true"></i>';
}

function _renderHomeDraftWidget(cached, lastHistory) {
    var body = document.getElementById('home-draft-body');
    var cta = document.getElementById('home-draft-cta');
    if (!body) return;

    var total = lastHistory ? lastHistory.total_score : (cached ? cached.total_score : null);
    if (total == null) { _renderHomeDraftEmpty(); return; }

    var rank = lastHistory ? lastHistory.rank : _scoreRank(total);

    // Sub-scores: если локальный кэш относится к тому же (или близкому) total — используем его.
    // Иначе показываем только total и нулевые bar'ы (визуально указывает на отсутствие детализации).
    var lane = null, syn = null, mu = null;
    if (cached && Math.abs((cached.total_score || 0) - total) < 0.5) {
        lane = cached.lane_score || 0;
        syn = cached.synergy_score || 0;
        mu = cached.matchup_score || 0;
    }

    var totalRounded = Math.round(total);
    // Каждая из 3 компонент — 0..33.33
    var lanePct = lane != null ? Math.min(100, Math.round((lane / 33.33) * 100)) : null;
    var synPct = syn != null ? Math.min(100, Math.round((syn / 33.33) * 100)) : null;
    var muPct = mu != null ? Math.min(100, Math.round((mu / 33.33) * 100)) : null;

    body.innerHTML =
        '<div class="home-draft-top">' +
            '<div class="home-draft-score">' + totalRounded + '<span class="home-draft-score-max">/100</span></div>' +
            '<div class="home-draft-rank" data-rank="' + _escHtml(rank) + '">' + _escHtml(rank) + '</div>' +
        '</div>' +
        '<div class="home-draft-bars">' +
            _draftBarRow('Линии', 'accent', lanePct) +
            _draftBarRow('Синергия', 'positive', synPct) +
            _draftBarRow('Матчапы', 'warning', muPct) +
        '</div>';

    if (cta) cta.innerHTML = 'Новый драфт <i class="ph ph-arrow-right" aria-hidden="true"></i>';
}

function _draftBarRow(label, tone, pct) {
    var width = (pct == null ? 0 : pct) + '%';
    var valueText = pct == null ? '—' : (pct + '%');
    return (
        '<div class="home-draft-bar-row">' +
            '<div class="home-draft-bar-label">' + label + '</div>' +
            '<div class="home-draft-bar-track"><div class="home-draft-bar-fill home-draft-bar-fill--' + tone + '" style="width:' + width + '"></div></div>' +
            '<div class="home-draft-bar-value">' + valueText + '</div>' +
        '</div>'
    );
}

function homeDraftWidgetClick() {
    switchPage('drafter');
}

// ── Новость ──────────────────────────────────────────────────────────
var _HOME_NEWS_LINK = null;

function _formatNewsDate(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    var now = new Date();
    var startOfDay = function(date) {
        return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
    };
    var diffDays = Math.floor((startOfDay(now) - startOfDay(d)) / 86400000);
    if (diffDays <= 0) return 'сегодня';
    if (diffDays === 1) return 'вчера';
    return diffDays + ' дн. назад';
}

function _loadHomeNews() {
    var block = document.getElementById('home-news');
    if (!block) return;
    var API = window.API_BASE_URL || '/api';
    fetch(API + '/news')
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
            if (!data || !data.title) { block.hidden = true; return; }
            var textEl = document.getElementById('home-news-text');
            var dateEl = document.getElementById('home-news-date');
            if (textEl) textEl.textContent = data.title;
            if (dateEl) dateEl.textContent = _formatNewsDate(data.published_at);
            _HOME_NEWS_LINK = data.link || null;
            block.hidden = false;
        })
        .catch(function(e) {
            console.warn('[home news] failed:', e);
            block.hidden = true;
        });
}

function homeNewsClick() {
    if (_HOME_NEWS_LINK) {
        var tg = window.Telegram && window.Telegram.WebApp;
        if (tg && typeof tg.openLink === 'function') {
            tg.openLink(_HOME_NEWS_LINK);
        } else {
            window.open(_HOME_NEWS_LINK, '_blank', 'noopener');
        }
        return;
    }
    switchPage('database');
}

// ── Инициализация главной ────────────────────────────────────────────
function initHomeScreen() {
    _renderHomeAvatar();
    loadMeta();
    _loadHomeHeroWidget();
    _loadHomeDraftWidget();
    _loadHomeNews();
}

// ── items_db: загружаем один раз при старте, используем во всём приложении ──
var _itemsDb = {};
var _itemsDbLoaded = false;

async function _loadItemsDb() {
    try {
        var resp = await fetch(window.API_BASE_URL + '/items_db');
        if (resp.ok) {
            _itemsDb = await resp.json();
            _itemsDbLoaded = true;
            if (_HOME_HERO_LAST) _renderHomeHeroWidget(_HOME_HERO_LAST.heroId, _HOME_HERO_LAST.build);
        }
    } catch (e) {
        console.warn('Failed to load items_db:', e);
    }
}

// Загружаем мету и items_db при старте (главная открыта по умолчанию)
(function() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() { initHomeScreen(); _loadItemsDb(); });
    } else {
        initHomeScreen();
        _loadItemsDb();
    }
}());

// ========== ДРАФТЕР ==========

const HERO_PRIMARY_POSITIONS = {
  1:1, 2:3, 3:5, 4:1, 5:5, 6:1, 7:4, 8:1, 9:4, 10:1, 11:1, 12:1, 13:2, 14:4, 15:3, 16:3, 17:2, 18:1, 19:4, 20:5, 21:4, 22:4, 23:3, 25:2, 26:5, 27:5, 28:3, 29:3, 30:5, 31:5, 32:1, 33:3, 34:2, 35:2, 36:2, 37:5, 38:3, 39:2, 40:5, 41:1, 42:1, 43:3, 44:1, 45:5, 46:1, 47:2, 48:1, 49:1, 50:5, 51:4, 52:2, 53:4, 54:1, 55:3, 56:1, 57:3, 58:5, 59:2, 60:3, 61:2, 62:4, 63:1, 64:5, 65:3, 66:5, 67:1, 68:5, 69:3, 70:1, 71:4, 72:1, 73:1, 74:2, 75:5, 76:2, 77:3, 78:3, 79:5, 80:2, 81:3, 82:2, 83:5, 84:5, 85:5, 86:4, 87:5, 88:4, 89:1, 90:2, 91:5, 92:3, 93:1, 94:1, 95:1, 96:3, 97:3, 98:3, 99:3, 100:4, 101:4, 102:5, 103:5, 104:3, 105:4, 106:2, 107:4, 108:3, 109:1, 110:4, 111:5, 112:5, 113:2, 114:1, 119:4, 120:2, 121:5, 123:4, 126:2, 128:4, 129:3, 131:5, 135:3, 136:5, 137:3, 138:1, 145:1, 155:3
};

var _drafterEnemyPick = [];          // [{hero_id, position}]
var _drafterAllyPick = [null, null, null, null, null]; // null = пусто
var _drafterActiveSlot = 0;
var _drafterMatchLoaded = false;
var _drafterPosFilter = 0;           // 0 = все, 1-5 = позиция
var _drafterLeaderboardCache = null;
var _drafterEnemyManualMode = false; // true = пользователь сам выбирает врагов
var _drafterActiveEnemySlot = -1;    // -1 = клик по герою идёт в союзный слот

function _drafterHeroName(heroId) {
    if (window.dotaHeroIdToName && window.dotaHeroIdToName[heroId]) {
        return window.dotaHeroIdToName[heroId];
    }
    return null;
}

function _drafterHeroIcon(heroId) {
    var name = _drafterHeroName(heroId);
    if (name && window.getHeroIconUrlByName) {
        return window.getHeroIconUrlByName(name);
    }
    return '';
}

function initDrafter() {
    // Показать лучший результат
    var best = localStorage.getItem('drafter_best_score');
    document.getElementById('drafter-best-score').textContent = best !== null ? best : '—';

    // Показать экран драфта, скрыть результат
    document.getElementById('drafter-main').style.display = 'block';
    document.getElementById('drafter-result').style.display = 'none';
    var _drOverlay = document.getElementById('dr-bg-overlay');
    if (_drOverlay) gsap.to(_drOverlay, {opacity: 0, duration: 0.4, ease: 'power2.out'});

    // Prefetch лидерборда в фоне
    if (!_drafterLeaderboardCache) {
        fetch(window.API_BASE_URL + '/draft/leaderboard')
            .then(function(r) { return r.ok ? r.json() : null; })
            .then(function(data) { if (data) _drafterLeaderboardCache = data; })
            .catch(function() {});
    }

    // Загрузить матч если ещё не загружен
    if (!_drafterMatchLoaded) {
        loadDrafterMatch();
    } else {
        _renderPosFilterBtns();
        _updateManualBtn();
        renderDrafterSlots();
        renderDrafterGrid();
    }
}

async function loadDrafterMatch() {
    _drafterMatchLoaded = false;
    _drafterAllyPick = [null, null, null, null, null];
    _drafterActiveSlot = 0;
    _drafterEnemyPick = [];
    _drafterPosFilter = 1;
    _drafterEnemyManualMode = false;
    _drafterActiveEnemySlot = -1;
    _updateManualBtn();

    var _ldrOverlay = document.getElementById('dr-bg-overlay');
    if (_ldrOverlay) gsap.to(_ldrOverlay, {opacity: 0, duration: 0.5, ease: 'power2.out'});

    document.getElementById('drafter-main').style.display = 'block';
    document.getElementById('drafter-result').style.display = 'none';
    document.getElementById('drafter-evaluate-wrap').style.display = 'none';

    var enemySlotsEl = document.getElementById('drafter-enemy-slots');
    if (enemySlotsEl) enemySlotsEl.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:8px 0;">Загрузка...</div>';

    try {
        var resp = await fetch(window.API_BASE_URL + '/draft/random');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var data = await resp.json();

        _drafterEnemyPick = (data.enemy || []).slice(0, 5);
        // Sort by position number so slots match pos 1..5 order
        _drafterEnemyPick.sort(function(a, b) {
            var posA = parseInt((a.position || '').replace('pos ', ''));
            var posB = parseInt((b.position || '').replace('pos ', ''));
            return posA - posB;
        });
        while (_drafterEnemyPick.length < 5) {
            _drafterEnemyPick.push({ hero_id: 0, position: '' });
        }
        _drafterMatchLoaded = true;
    } catch (e) {
        console.error('[drafter] loadDrafterMatch error:', e);
        if (enemySlotsEl) enemySlotsEl.innerHTML = '<div style="color:#f44;font-size:12px;">Ошибка загрузки</div>';
        return;
    }

    if (document.getElementById('drafter-search')) {
        document.getElementById('drafter-search').value = '';
    }
    var filtersEl = document.getElementById('drafter-pos-filters');
    if (filtersEl) filtersEl.style.opacity = '1';
    _renderPosFilterBtns();
    renderDrafterSlots();
    renderDrafterGrid();
}

function renderDrafterSlots() {
    _renderAllySlots();
    _renderEnemySlots();
    _updateEvaluateBtn();
}

function _renderAllySlots() {
    var el = document.getElementById('drafter-ally-slots');
    if (!el) return;
    var html = '';
    for (var i = 0; i < 5; i++) {
        var hero = _drafterAllyPick[i];
        var isActive = (i === _drafterActiveSlot);
        var cls = 'drafter-slot';
        if (isActive) cls += ' drafter-slot--active';
        if (hero) cls += ' drafter-slot--filled';
        html += '<div class="drafter-slot-wrap">';
        html += '<div class="' + cls + '" id="drafter-ally-slot-' + i + '" onclick="drafterSlotClick(' + i + ')">';
        if (hero && hero.hero_id) {
            var iconUrl = _drafterHeroIcon(hero.hero_id);
            if (iconUrl) {
                html += '<img src="' + iconUrl + '" alt="" class="drafter-slot-img">';
            } else {
                html += '<span style="font-size:10px;color:#aaa;">#' + hero.hero_id + '</span>';
            }
        } else {
            html += '<span class="drafter-slot-plus">+</span>';
        }
        html += '</div>';
        html += '<div class="drafter-slot-pos"><img src="/images/positions/pos_' + (i + 1) + '.png" width="16" height="16"></div>';
        html += '</div>';
    }
    el.innerHTML = html;
}

function _renderEnemySlots() {
    var el = document.getElementById('drafter-enemy-slots');
    if (!el) return;
    var html = '';
    for (var i = 0; i < 5; i++) {
        var hero = _drafterEnemyPick[i] || { hero_id: 0 };
        var isActive = _drafterEnemyManualMode && (i === _drafterActiveEnemySlot);
        var cls = 'drafter-slot drafter-slot--enemy';
        if (hero.hero_id) cls += ' drafter-slot--filled';
        if (isActive) cls += ' drafter-slot--enemy-active';
        var clickAttr = _drafterEnemyManualMode ? ' onclick="drafterEnemySlotClick(' + i + ')"' : '';
        html += '<div class="drafter-slot-wrap">';
        html += '<div class="' + cls + '" id="drafter-enemy-slot-' + i + '"' + clickAttr + '>';
        if (hero.hero_id) {
            var iconUrl = _drafterHeroIcon(hero.hero_id);
            if (iconUrl) {
                html += '<img src="' + iconUrl + '" alt="" class="drafter-slot-img">';
            } else {
                html += '<span style="font-size:10px;color:#aaa;">#' + hero.hero_id + '</span>';
            }
        } else if (_drafterEnemyManualMode) {
            html += '<span class="drafter-slot-plus">+</span>';
        }
        html += '</div>';
        html += '<div class="drafter-slot-pos"><img src="/images/positions/pos_' + (i + 1) + '.png" width="16" height="16"></div>';
        html += '</div>';
    }
    el.innerHTML = html;
}

function _updateManualBtn() {
    var btn = document.getElementById('drafter-manual-btn');
    if (!btn) return;
    btn.classList.toggle('drafter-manual-btn--active', !!_drafterEnemyManualMode);
}

function enableEnemyManualMode() {
    _drafterEnemyManualMode = true;
    _drafterEnemyPick = [
        { hero_id: 0, position: '' },
        { hero_id: 0, position: '' },
        { hero_id: 0, position: '' },
        { hero_id: 0, position: '' },
        { hero_id: 0, position: '' }
    ];
    _drafterActiveEnemySlot = 0;
    _drafterPosFilter = 1;
    _drafterMatchLoaded = true;
    var searchEl = document.getElementById('drafter-search');
    if (searchEl) searchEl.value = '';
    var filtersEl = document.getElementById('drafter-pos-filters');
    if (filtersEl) filtersEl.style.opacity = '1';
    _renderPosFilterBtns();
    _updateManualBtn();
    renderDrafterSlots();
    renderDrafterGrid();
}

function drafterEnemySlotClick(slotIndex) {
    if (!_drafterEnemyManualMode) return;
    if (_drafterEnemyPick[slotIndex] && _drafterEnemyPick[slotIndex].hero_id) {
        _drafterEnemyPick[slotIndex] = { hero_id: 0, position: '' };
        _drafterActiveEnemySlot = slotIndex;
        renderDrafterSlots();
        renderDrafterGrid();
        return;
    }
    _drafterActiveEnemySlot = slotIndex;
    var searchVal = (document.getElementById('drafter-search') || {}).value || '';
    if (!searchVal.trim()) {
        _drafterPosFilter = slotIndex + 1;
        _renderPosFilterBtns();
    }
    _renderEnemySlots();
    renderDrafterGrid();
}

function _updateEvaluateBtn() {
    var allFilled = _drafterAllyPick.every(function(h) { return h !== null; });
    var wrap = document.getElementById('drafter-evaluate-wrap');
    if (!wrap) return;
    if (allFilled && wrap.style.display === 'none') {
        wrap.style.display = 'block';
        var btn = wrap.querySelector('.drafter-evaluate-btn');
        if (btn) {
            btn.style.animation = 'none';
            btn.classList.add('drafter-btn--ready');
            // trigger fadeInBtn
            btn.style.animation = '';
        }
    } else if (!allFilled) {
        wrap.style.display = 'none';
        var btn2 = wrap.querySelector('.drafter-evaluate-btn');
        if (btn2) btn2.classList.remove('drafter-btn--ready');
    }
}

function drafterSlotClick(slotIndex) {
    // Switch focus from enemy back to ally side
    _drafterActiveEnemySlot = -1;
    // If slot is filled — clear it and make it active
    if (_drafterAllyPick[slotIndex]) {
        _drafterAllyPick[slotIndex] = null;
        _drafterActiveSlot = slotIndex;
        renderDrafterSlots();
        renderDrafterGrid();
        return;
    }
    _drafterActiveSlot = slotIndex;
    // Auto-activate position filter matching the slot
    var searchVal = (document.getElementById('drafter-search') || {}).value || '';
    if (!searchVal.trim()) {
        _drafterPosFilter = slotIndex + 1;
        _renderPosFilterBtns();
    }
    renderDrafterSlots();
    renderDrafterGrid();
}

function setDrafterPosFilter(pos) {
    _drafterPosFilter = pos;
    _renderPosFilterBtns();
    renderDrafterGrid();
}

function _renderPosFilterBtns() {
    var btns = document.querySelectorAll('.drafter-pos-btn');
    btns.forEach(function(btn) {
        var p = parseInt(btn.dataset.pos);
        btn.classList.toggle('drafter-pos-btn--active', p === _drafterPosFilter);
    });
}

function onDrafterSearch() {
    var query = (document.getElementById('drafter-search') || {}).value || '';
    var filtersEl = document.getElementById('drafter-pos-filters');
    if (filtersEl) filtersEl.style.opacity = query.trim() ? '0.4' : '1';
    renderDrafterGrid();
}

function renderDrafterGrid() {
    var el = document.getElementById('drafter-hero-grid');
    if (!el) return;

    var searchEl = document.getElementById('drafter-search');
    var query = searchEl ? searchEl.value.toLowerCase().trim() : '';

    if (!window.dotaHeroIds) {
        el.innerHTML = '<div style="color:var(--text-muted);font-size:12px;">Герои не загружены</div>';
        return;
    }

    // Собираем уникальных героев
    var seen = new Set();
    var heroes = [];
    Object.keys(window.dotaHeroIds).forEach(function(name) {
        var id = window.dotaHeroIds[name];
        if (!seen.has(id)) {
            seen.add(id);
            heroes.push({ id: id, name: name });
        }
    });
    heroes.sort(function(a, b) { return a.name.localeCompare(b.name); });

    if (query) {
        // Поиск по тексту — все герои, фильтр позиции игнорируется
        heroes = heroes.filter(function(h) { return h.name.toLowerCase().indexOf(query) !== -1; });
    } else {
        // Фильтр по позиции (всегда 1-5)
        heroes = heroes.filter(function(h) { return HERO_PRIMARY_POSITIONS[h.id] === _drafterPosFilter; });
    }

    // Уже выбранные
    var pickedIds = new Set(_drafterAllyPick.filter(Boolean).map(function(h) { return h.hero_id; }));

    var html = '';
    heroes.forEach(function(h) {
        var isPicked = pickedIds.has(h.id);
        var isEnemy  = _drafterEnemyPick.some(function(e) { return e && e.hero_id === h.id; });
        var iconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(h.name) : '';
        var cls = 'drafter-grid-hero' + (isPicked ? ' drafter-grid-hero--picked' : '') + (isEnemy ? ' drafter-hero-disabled' : '');
        var onclick = (isPicked || isEnemy) ? '' : ' onclick="selectDrafterHero(' + h.id + ')"';
        html += '<div class="' + cls + '"' + onclick + '>';
        if (iconUrl) {
            html += '<img src="' + iconUrl + '" alt="' + h.name + '" class="drafter-grid-img">';
        } else {
            html += '<div class="drafter-grid-img-empty"></div>';
        }
        html += '<div class="drafter-grid-name">' + h.name + '</div>';
        html += '</div>';
    });

    el.innerHTML = html;
}

function selectDrafterHero(heroId) {
    // Manual enemy selection: a free enemy slot is focused
    if (_drafterEnemyManualMode && _drafterActiveEnemySlot >= 0 && _drafterActiveEnemySlot < 5) {
        var enemySlot = _drafterActiveEnemySlot;
        _drafterEnemyPick[enemySlot] = {
            hero_id: heroId,
            position: 'pos ' + (enemySlot + 1)
        };

        if (navigator.vibrate) navigator.vibrate(25);

        var nextE = -1;
        for (var ei = enemySlot + 1; ei < 5; ei++) {
            if (!_drafterEnemyPick[ei] || !_drafterEnemyPick[ei].hero_id) { nextE = ei; break; }
        }
        if (nextE === -1) {
            for (var ej = 0; ej < enemySlot; ej++) {
                if (!_drafterEnemyPick[ej] || !_drafterEnemyPick[ej].hero_id) { nextE = ej; break; }
            }
        }
        _drafterActiveEnemySlot = nextE;

        renderDrafterSlots();
        renderDrafterGrid();

        var enemyEl = document.getElementById('drafter-enemy-slot-' + enemySlot);
        if (enemyEl) {
            enemyEl.style.transition = 'transform 0.15s ease';
            enemyEl.style.transform = 'scale(0.85)';
            setTimeout(function() { enemyEl.style.transform = 'scale(1)'; }, 150);
        }
        return;
    }

    if (_drafterActiveSlot >= 5) return;

    var filledSlot = _drafterActiveSlot;

    _drafterAllyPick[filledSlot] = {
        hero_id: heroId,
        position: 'pos ' + (filledSlot + 1)
    };

    if (navigator.vibrate) navigator.vibrate(25);

    // Переходим к следующему пустому слоту
    var next = -1;
    for (var i = filledSlot + 1; i < 5; i++) {
        if (!_drafterAllyPick[i]) { next = i; break; }
    }
    if (next === -1) {
        for (var j = 0; j < filledSlot; j++) {
            if (!_drafterAllyPick[j]) { next = j; break; }
        }
    }
    if (next !== -1) _drafterActiveSlot = next;

    renderDrafterSlots();
    renderDrafterGrid();

    // Animate the filled slot
    var slotEl = document.getElementById('drafter-ally-slot-' + filledSlot);
    if (slotEl) {
        slotEl.style.transition = 'transform 0.15s ease';
        slotEl.style.transform = 'scale(0.85)';
        setTimeout(function() { slotEl.style.transform = 'scale(1)'; }, 150);
    }
}

var _toastTimer = null;
function showToast(msg) {
    var el = document.getElementById('app-toast');
    if (!el) {
        el = document.createElement('div');
        el.id = 'app-toast';
        el.className = 'app-toast';
        document.body.appendChild(el);
    }
    el.textContent = msg;
    el.classList.add('app-toast--visible');
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(function() {
        el.classList.remove('app-toast--visible');
    }, 3500);
}

async function submitDraft() {
    var ally = _drafterAllyPick.filter(Boolean);
    var enemy = _drafterEnemyPick.filter(function(h) { return h && h.hero_id; });

    var btn = document.getElementById('drafter-evaluate-btn');
    if (btn) btn.disabled = true;

    try {
        var resp = await fetch(window.API_BASE_URL + '/draft/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ally: ally, enemy: enemy, token: USER_TOKEN || null })
        });
        if (resp.status === 429) {
            showToast('Слишком много драфтов! Подождите немного и попробуйте снова.');
            return;
        }
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var data = await resp.json();
        if (typeof cacheLastDraftEval === 'function') cacheLastDraftEval(data);
        showDrafterResult(data);
    } catch (e) {
        console.error('[drafter] submitDraft error:', e);
        const msg = 'Не удалось оценить драфт. Проверь подключение и попробуй снова.';
        const tg = window.Telegram && window.Telegram.WebApp;
        if (tg && typeof tg.showAlert === 'function') {
            tg.showAlert(msg);
        } else if (typeof showToast === 'function') {
            showToast(msg);
        } else {
            console.warn(msg);
        }
    } finally {
        if (btn) btn.disabled = false;
    }
}

function hideDrafterFullpage(id) {
    var el = document.getElementById(id);
    if (el) { el.style.display = 'none'; el.innerHTML = ''; }
}

function _drafterFpSkeleton(title, backId) {
    return (
        '<div class="drafter-fp-header">' +
            '<button class="drafter-fp-back" onclick="hideDrafterFullpage(\'' + backId + '\')">← Назад</button>' +
            '<div class="drafter-fp-title">' + title + '</div>' +
            '<div class="drafter-fp-spacer"></div>' +
        '</div>' +
        '<div class="drafter-fp-content">' +
            '<div style="color:#6b7280;font-size:12px;padding:8px 0;">Загрузка...</div>' +
        '</div>'
    );
}

function _drafterFpError(title, backId) {
    return (
        '<div class="drafter-fp-header">' +
            '<button class="drafter-fp-back" onclick="hideDrafterFullpage(\'' + backId + '\')">← Назад</button>' +
            '<div class="drafter-fp-title">' + title + '</div>' +
            '<div class="drafter-fp-spacer"></div>' +
        '</div>' +
        '<div class="drafter-fp-content"><div style="color:#e5534b;font-size:13px;">Ошибка загрузки</div></div>'
    );
}

function _draftRankColor(rank) {
    return rank === 'SSS' || rank === 'S' ? '#d29922'
         : rank === 'A' ? '#7b8bb8'
         : rank === 'B' ? '#60a5fa'
         : '#9ca3af';
}

function _draftFormatDate(isoStr) {
    if (!isoStr) return '';
    var d = new Date(isoStr);
    var now = new Date();
    var todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var yesterdayStart = new Date(todayStart - 86400000);
    var hh = String(d.getHours()).padStart(2, '0');
    var mm = String(d.getMinutes()).padStart(2, '0');
    var months = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'];
    if (d >= todayStart) return 'сегодня ' + hh + ':' + mm;
    if (d >= yesterdayStart) return 'вчера ' + hh + ':' + mm;
    return d.getDate() + ' ' + months[d.getMonth()] + ' ' + hh + ':' + mm;
}

function _rankCardStyle(rank) {
    if (rank === 'SSS' || rank === 'S') return 'background:rgba(251,191,36,0.06);border:1px solid rgba(210,153,34,0.12);';
    if (rank === 'A') return 'background:rgba(139,92,246,0.08);border:1px solid rgba(139,92,246,0.2);';
    if (rank === 'B') return 'background:rgba(96,165,250,0.08);border:1px solid rgba(96,165,250,0.15);';
    return 'background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);';
}

async function showDrafterHistory() {
    var PAGE_ID = 'drafter-history-page';
    var page = document.getElementById(PAGE_ID);
    page.innerHTML = _drafterFpSkeleton('\u041c\u041e\u042f \u0418\u0421\u0422\u041e\u0420\u0418\u042f', PAGE_ID);
    page.style.display = 'block';

    if (!USER_TOKEN) {
        page.innerHTML = (
            '<div class="drafter-fp-header">' +
                '<button class="drafter-fp-back" onclick="hideDrafterFullpage(\'' + PAGE_ID + '\')">← Назад</button>' +
                '<div class="drafter-fp-title">\u041c\u041e\u042f \u0418\u0421\u0422\u041e\u0420\u0418\u042f</div>' +
                '<div class="drafter-fp-spacer"></div>' +
            '</div>' +
            '<div class="drafter-fp-content"><div style="color:#6b7280;font-size:13px;">Войдите, чтобы посмотреть историю</div></div>'
        );
        return;
    }
    try {
        var resp = await fetch(window.API_BASE_URL + '/draft/history?token=' + USER_TOKEN);
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var rows = await resp.json();
        var cardsHtml = rows.length === 0
            ? '<div style="color:#6b7280;font-size:13px;">Нет сохранённых драфтов</div>'
            : rows.map(function(r) {
                var color = _draftRankColor(r.rank);
                var cardStyle = _rankCardStyle(r.rank);
                var dt = _draftFormatDate(r.created_at);
                var heroIconStyle = 'width:36px;height:36px;border-radius:50%;object-fit:cover;flex-shrink:0;';
                var heroesHtml = '';
                if (r.ally_heroes && r.enemy_heroes) {
                    var enemyIcons = r.enemy_heroes.map(function(id) {
                        var url = _drafterHeroIcon(id);
                        return url ? '<img src="' + url + '" style="' + heroIconStyle + 'border:2px solid #e5534b;">' : '';
                    }).join('');
                    var allyIcons = r.ally_heroes.map(function(id) {
                        var url = _drafterHeroIcon(id);
                        return url ? '<img src="' + url + '" style="' + heroIconStyle + 'border:2px solid #3db87a;">' : '';
                    }).join('');
                    heroesHtml = (
                        '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;">' + enemyIcons + '</div>' +
                        '<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:6px;">' + allyIcons + '</div>'
                    );
                }
                return (
                    '<div class="drafter-hist-card" style="' + cardStyle + 'flex-direction:column;align-items:stretch;gap:0;">' +
                        '<div style="display:flex;align-items:center;">' +
                            '<div style="font-size:24px;font-weight:900;color:' + color + ';width:40px;text-align:center;flex-shrink:0;line-height:1;">' + r.rank + '</div>' +
                            '<div style="flex:1;font-size:12px;color:#6b7280;">' + dt + '</div>' +
                            '<div style="font-size:16px;font-weight:700;color:' + color + ';white-space:nowrap;">' + r.total_score + '</div>' +
                        '</div>' +
                        heroesHtml +
                    '</div>'
                );
            }).join('');
        page.innerHTML = (
            '<div class="drafter-fp-header">' +
                '<button class="drafter-fp-back" onclick="hideDrafterFullpage(\'' + PAGE_ID + '\')">← Назад</button>' +
                '<div class="drafter-fp-title">\u041c\u041e\u042f \u0418\u0421\u0422\u041e\u0420\u0418\u042f</div>' +
                '<div class="drafter-fp-spacer"></div>' +
            '</div>' +
            '<div class="drafter-fp-content">' +
                '<div style="font-size:8px;color:#4b5563;text-align:center;margin-bottom:8px;">Последние 10 драфтов</div>' +
                cardsHtml +
            '</div>'
        );
    } catch (e) {
        page.innerHTML = _drafterFpError('\u041c\u041e\u042f \u0418\u0421\u0422\u041e\u0420\u0418\u042f', PAGE_ID);
    }
}

var _LB_ICON_1 = '<span style="color:#d29922;font-size:14px;">&#9733;</span>';
var _LB_ICON_2 = '<span style="color:#94a3b8;font-size:12px;font-weight:700;">2</span>';
var _LB_ICON_3 = '<span style="color:#b45309;font-size:12px;font-weight:700;">3</span>';

function _lbAvatarColors(rank) {
    if (rank === 1) return { bg: 'rgba(210,153,34,0.12)',  text: '#d29922' };
    if (rank === 2) return { bg: 'rgba(148,163,184,0.2)', text: '#94a3b8' };
    if (rank === 3) return { bg: 'rgba(180,83,9,0.2)',    text: '#b45309' };
    return { bg: 'rgba(255,255,255,0.05)', text: '#6b7280' };
}

function _lbScoreColor(rank) {
    if (rank === 1) return '#d29922';
    if (rank === 2) return '#94a3b8';
    if (rank === 3) return '#b45309';
    return '#8d9bc6';
}

async function _renderLeaderboardRows(rows, page, PAGE_ID) {
    var rowsHtml = rows.length === 0
        ? '<div style="color:#6b7280;font-size:13px;padding:8px 0;">Пока нет участников</div>'
        : rows.map(function(r) {
            var placeIcon = r.rank === 1 ? _LB_ICON_1 : r.rank === 2 ? _LB_ICON_2 : r.rank === 3 ? _LB_ICON_3
                : '<span style="font-size:11px;font-weight:700;color:#6b7280;">' + r.rank + '</span>';
            var rowCls = 'drafter-lb-row' + (r.rank === 1 ? ' drafter-lb-row--top1' : r.rank === 2 ? ' drafter-lb-row--top2' : r.rank === 3 ? ' drafter-lb-row--top3' : '');
            var ac = _lbAvatarColors(r.rank);
            var displayName = r.username || r.first_name || ('Игрок ' + r.user_id);
            var firstChar = displayName.charAt(0).toUpperCase();
            var letterDiv = '<div class="drafter-lb-avatar-letter" style="background:' + ac.bg + ';color:' + ac.text + ';">' + firstChar + '</div>';
            var avatarHtml = r.photo_url
                ? '<img class="drafter-lb-avatar" src="' + r.photo_url + '" alt="" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'">' +
                  '<div class="drafter-lb-avatar-letter" style="display:none;background:' + ac.bg + ';color:' + ac.text + ';">' + firstChar + '</div>'
                : letterDiv;
            return (
                '<div class="' + rowCls + '" style="display:flex;align-items:center;gap:8px">' +
                    '<div class="drafter-lb-place">' + placeIcon + '</div>' +
                    avatarHtml +
                    '<div style="flex:1;min-width:0">' +
                        '<div class="drafter-lb-name" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + displayName + '</div>' +
                        '<div class="drafter-lb-count">' + r.draft_count + ' \u0434\u0440\u0430\u0444\u0442\u043e\u0432</div>' +
                    '</div>' +
                    '<div class="drafter-lb-score" style="color:' + _lbScoreColor(r.rank) + ';">' + r.top5_sum + '</div>' +
                '</div>'
            );
        }).join('');
    page.innerHTML = (
        '<div class="drafter-fp-header">' +
            '<button class="drafter-fp-back" onclick="hideDrafterFullpage(\'' + PAGE_ID + '\')">← \u041d\u0430\u0437\u0430\u0434</button>' +
            '<div class="drafter-fp-title">\u0422\u041e\u041f \u0414\u0420\u0410\u0424\u0422\u0415\u0420\u041e\u0412</div>' +
            '<div class="drafter-fp-spacer"></div>' +
        '</div>' +
        '<div class="lb-prize-banner">' +
            '<img src="/images/arcana.gif" class="lb-prize-gif" alt="arcana">' +
            '<div class="lb-prize-info">' +
                '<div class="lb-prize-title">\u0410\u0440\u043a\u0430\u043d\u044b \u043a\u0430\u0436\u0434\u044b\u0439 \u043c\u0435\u0441\u044f\u0446</div>' +
                '<div class="lb-prize-sub">\u0422\u043e\u043f-3 \u043f\u043e\u043b\u0443\u0447\u0430\u044e\u0442 \u0430\u0440\u043a\u0430\u043d\u0443 \u043d\u0430 \u0432\u044b\u0431\u043e\u0440 \u0432 \u043a\u043e\u043d\u0446\u0435 \u043c\u0435\u0441\u044f\u0446\u0430</div>' +
                '<div class="lb-prize-month">\u0430\u043f\u0440\u0435\u043b\u044c 2026</div>' +
            '</div>' +
        '</div>' +
        '<div class="lb-note">' +
            '<span class="lb-note-icon">\u2139</span> ' +
            '\u0421\u0447\u0451\u0442 \u043f\u043e \u0441\u0443\u043c\u043c\u0435 <b>\u043b\u0443\u0447\u0448\u0438\u0445 5 \u0440\u0435\u0437\u0443\u043b\u044c\u0442\u0430\u0442\u043e\u0432</b>' +
        '</div>' +
        '<div class="drafter-fp-content">' + rowsHtml + '</div>'
    );

    // ── Fixed плашка «Ваше место» — показываем сразу, данные подгружаем ──
    var token = (typeof USER_TOKEN !== 'undefined' ? USER_TOKEN : '') || '';
    if (!token) return;

    // Показываем плашку-заглушку сразу (чтобы не прыгал контент)
    var bar = document.createElement('div');
    bar.id = 'drafter-lb-myrank-bar';
    bar.className = 'drafter-lb-myrank';
    bar.style.display = 'none'; // скрыта до получения данных
    page.appendChild(bar);

    try {
        var meResp = await fetch(window.API_BASE_URL + '/draft/leaderboard/me?token=' + encodeURIComponent(token));
        if (!meResp.ok) return;
        var me = await meResp.json();
        if (!me || me.rank === null) return;
        if (me.rank <= 25) return; // виден в списке — плашка не нужна
        bar.innerHTML = (
            '<div class="drafter-lb-myrank-left">' +
                '\u0412\u0430\u0448\u0435 \u043c\u0435\u0441\u0442\u043e: <span class="drafter-lb-myrank-rank">#' + me.rank + '</span>' +
            '</div>' +
            '<div class="drafter-lb-myrank-right">' +
                '<div class="drafter-lb-myrank-label">\u0421\u0427\u0401\u0422</div>' +
                '<div class="drafter-lb-myrank-score">' + me.top5_sum + '</div>' +
            '</div>'
        );
        bar.style.display = 'flex';
    } catch (e) { /* ignore */ }
}

async function showDrafterLeaderboard() {
    var PAGE_ID = 'drafter-leaderboard-page';
    var page = document.getElementById(PAGE_ID);
    page.style.display = 'block';

    if (_drafterLeaderboardCache) {
        _renderLeaderboardRows(_drafterLeaderboardCache, page, PAGE_ID);
        return;
    }

    page.innerHTML = _drafterFpSkeleton('\u0422\u041e\u041f \u0414\u0420\u0410\u0424\u0422\u0415\u0420\u041e\u0412', PAGE_ID);

    try {
        var resp = await fetch(window.API_BASE_URL + '/draft/leaderboard');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var rows = await resp.json();
        _drafterLeaderboardCache = rows;
        _renderLeaderboardRows(rows, page, PAGE_ID);
    } catch (e) {
        page.innerHTML = _drafterFpError('\u0422\u041e\u041f \u0414\u0420\u0410\u0424\u0422\u0415\u0420\u041e\u0412', PAGE_ID);
    }
}

function showDrafterResult(data) {
    document.getElementById('drafter-main').style.display = 'none';
    document.getElementById('drafter-result').style.display = 'block';

    var battleScreen = document.getElementById('dr-battle-screen');
    var finalScreen  = document.getElementById('dr-final-screen');

    battleScreen.style.display = 'block';
    finalScreen.style.display  = 'none';

    var duels = data.duels || [];

    var _drafterSkip = false;

    function sleep(ms) {
        return new Promise(function(resolve) {
            if (_drafterSkip) { resolve(); return; }
            setTimeout(resolve, ms);
        });
    }

    function skipDrafterAnim() {
        if (_drafterSkip) return;
        _drafterSkip = true;
        gsap.set(battleScreen, {clearProps: 'x'});
        battleScreen.style.display = 'none';
        var synSc = document.getElementById('dr-synergy-screen');
        if (synSc) { synSc.style.display = 'none'; gsap.set(synSc, {clearProps: 'opacity'}); }
        var sb = document.getElementById('dr-skip-btn');
        if (sb) sb.remove();
        showFinal();
    }

    function _icon(id) { return _drafterHeroIcon(id) || ''; }
    function _name(id) { return _drafterHeroName(id) || ('Герой #' + id); }

    var WIN_SVG  = '<svg width="52" height="52" viewBox="0 0 52 52"><path d="M26 4L6 12V26C6 37 15 46 26 48C37 46 46 37 46 26V12L26 4Z" fill="rgba(16,185,129,0.2)" stroke="#3db87a" stroke-width="2"/><path d="M16 26L22 32L36 18" stroke="#3db87a" stroke-width="3" stroke-linecap="round" fill="none"/></svg>';
    var LOSS_SVG = '<svg width="52" height="52" viewBox="0 0 52 52"><path d="M26 4L6 12V26C6 37 15 46 26 48C37 46 46 37 46 26V12L26 4Z" fill="rgba(229,83,75,0.15)" stroke="#e5534b" stroke-width="2"/><path d="M19 19L33 33M33 19L19 33" stroke="#e5534b" stroke-width="3" stroke-linecap="round"/></svg>';

    function spawnParticles(win) {
        var canvas = document.getElementById('dr-particles-canvas');
        if (!canvas) return;
        canvas.width  = canvas.clientWidth;
        canvas.height = canvas.clientHeight;
        var ctx = canvas.getContext('2d');
        var cx  = canvas.width  / 2;
        var cy  = canvas.height / 2;
        var rgb = win ? '192,132,252' : '239,68,68';
        var particles = [];
        for (var i = 0; i < 30; i++) {
            var angle = Math.random() * Math.PI * 2;
            var speed = 1.5 + Math.random() * 2.5;
            particles.push({x: cx, y: cy, vx: Math.cos(angle) * speed, vy: Math.sin(angle) * speed, r: 2 + Math.random() * 3, life: 60});
        }
        function tick() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            var alive = false;
            particles.forEach(function(p) {
                if (p.life <= 0) return;
                alive = true;
                p.x += p.vx; p.y += p.vy; p.vy += 0.08; p.life--;
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                ctx.fillStyle = 'rgba(' + rgb + ',' + (p.life / 60) + ')';
                ctx.fill();
            });
            if (alive) requestAnimationFrame(tick);
        }
        tick();
    }

    // ── Фон страницы — overlay с градиентом ─────────────────────────────
    function setBattleBackground(win) {
        var pageDrafter = document.getElementById('page-drafter');
        var overlay = document.getElementById('dr-bg-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'dr-bg-overlay';
            pageDrafter.insertBefore(overlay, pageDrafter.firstChild);
        }
        var newBg = win
            ? 'radial-gradient(ellipse at 50% 20%, rgba(120,40,220,0.5) 0%, #0a0612 65%)'
            : 'radial-gradient(ellipse at 50% 20%, rgba(180,20,20,0.5) 0%, #0a0612 65%)';
        var currentOpacity = parseFloat(gsap.getProperty(overlay, 'opacity')) || 0;
        if (currentOpacity < 0.1) {
            overlay.style.background = newBg;
            gsap.to(overlay, {opacity: 1, duration: 0.8, ease: 'power2.out'});
        } else {
            gsap.to(overlay, {opacity: 0.05, duration: 0.25, ease: 'power2.out', onComplete: function() {
                overlay.style.background = newBg;
                gsap.to(overlay, {opacity: 1, duration: 0.55, ease: 'power2.out'});
            }});
        }
    }

    // ── Шаг 1: 3 битвы линий ─────────────────────────────────────────────
    async function playBattle(index, duel) {
        var win = duel.win;

        var dotsHtml = duels.map(function(_, d) {
            return '<div class="dr-dot' + (d === index ? ' dr-dot-active' : '') + '" id="dr-dot-' + d + '"></div>';
        }).join('');

        gsap.set(battleScreen, {clearProps: 'backgroundColor,x'});
        battleScreen.innerHTML = (
            '<canvas id="dr-particles-canvas" style="position:absolute;top:0;left:0;width:100%;height:100%;pointer-events:none;z-index:10;"></canvas>' +
            '<div class="dr-b-header">' +
                '<div class="dr-b-num">БИТВА ' + (index + 1) + ' ИЗ ' + duels.length + '</div>' +
                '<div class="dr-b-name">' + duel.name.toUpperCase() + '</div>' +
            '</div>' +
            '<div class="dr-b-arena">' +
                '<div class="dr-b-side dr-b-ally" id="dr-side-ally">' +
                    (duel.ally_heroes || []).map(function(h) {
                        return '<img src="' + _icon(h.hero_id) + '" class="dr-b-avatar dr-b-avatar-ally" onerror="this.style.display=\'none\'">';
                    }).join('') +
                '</div>' +
                '<div class="dr-b-center-icon" id="dr-result-icon" style="opacity:0;"></div>' +
                '<div class="dr-b-side dr-b-enemy" id="dr-side-enemy">' +
                    (duel.enemy_heroes || []).map(function(h) {
                        return '<img src="' + _icon(h.hero_id) + '" class="dr-b-avatar dr-b-avatar-enemy" onerror="this.style.display=\'none\'">';
                    }).join('') +
                '</div>' +
            '</div>' +
            '<div class="dr-hbar-wrap">' +
                '<div class="dr-hbar-ally"  id="dr-hbar-ally"  style="width:50%"></div>' +
                '<div class="dr-hbar-enemy" id="dr-hbar-enemy" style="width:50%"></div>' +
            '</div>' +
            '<div class="dr-b-result-text" id="dr-b-result-text"></div>' +
            '<div class="dr-dots">' + dotsHtml + '</div>'
        );

        var allyEls    = Array.from(document.querySelectorAll('#dr-side-ally .dr-b-avatar'));
        var enemyEls   = Array.from(document.querySelectorAll('#dr-side-enemy .dr-b-avatar'));
        var resultIcon = document.getElementById('dr-result-icon');
        var hbarAlly   = document.getElementById('dr-hbar-ally');
        var hbarEnemy  = document.getElementById('dr-hbar-enemy');
        var resultText = document.getElementById('dr-b-result-text');

        gsap.set(allyEls,  {x: -30, opacity: 0});
        gsap.set(enemyEls, {x:  30, opacity: 0});

        await sleep(400);

        // Герои появляются
        gsap.to(allyEls,  {x: 0, opacity: 1, duration: 0.4, stagger: 0.1, ease: 'power2.out'});
        gsap.to(enemyEls, {x: 0, opacity: 1, duration: 0.4, stagger: 0.1, ease: 'power2.out'});

        await sleep(300);

        // Сближение
        gsap.to(allyEls,  {x:  18, scale: 1.08, duration: 0.3, ease: 'power2.in'});
        gsap.to(enemyEls, {x: -18, scale: 1.08, duration: 0.3, ease: 'power2.in'});

        await sleep(400);

        // Удар: частицы + shake + отдача
        spawnParticles(win);
        gsap.to('#dr-battle-screen', {x: -7, duration: 0.05, yoyo: true, repeat: 7, ease: 'none',
            onComplete: function() { gsap.set('#dr-battle-screen', {x: 0}); }});
        gsap.to(allyEls,  {x: -3, scale: 0.96, duration: 0.15, ease: 'power2.out'});
        gsap.to(enemyEls, {x:  3, scale: 0.96, duration: 0.15, ease: 'power2.out'});

        await sleep(150);

        // Шкала + фон страницы + текст
        gsap.to(hbarAlly,  {width: win ? '66%' : '34%', duration: 0.9, ease: 'power2.out'});
        gsap.to(hbarEnemy, {width: win ? '34%' : '66%', duration: 0.9, ease: 'power2.out'});
        setBattleBackground(win);
        if (resultText) {
            resultText.textContent = win ? 'Доминирование на линии' : 'Сложная линия для нас';
            gsap.fromTo(resultText, {opacity: 0, y: 8}, {opacity: 1, y: 0, duration: 0.4, ease: 'power2.out'});
        }

        await sleep(900);

        // Герои возвращаются
        gsap.to(allyEls.concat(enemyEls), {x: 0, scale: 1, duration: 0.3, ease: 'back.out(1)'});

        // SVG иконка результата
        if (resultIcon) {
            resultIcon.innerHTML = win ? WIN_SVG : LOSS_SVG;
            if (win) {
                gsap.fromTo(resultIcon, {scale: 0, opacity: 0}, {scale: 1, opacity: 1, duration: 0.5, ease: 'back.out(2)'});
            } else {
                gsap.fromTo(resultIcon, {y: -30, opacity: 0}, {y: 0, opacity: 1, duration: 0.4, ease: 'power2.out'});
            }
        }

        var dot = document.getElementById('dr-dot-' + index);
        if (dot) dot.className = 'dr-dot ' + (win ? 'dr-dot-win' : 'dr-dot-loss');

        await sleep(600);
    }

    // ── Шаг 2: Синергия команды — pentagon layout ───────────────────
    async function playSynergy() {
        var synPairs = data.synergy_pairs || [];
        var allyIds  = (data.ally_ids    || []).slice();

        // Fallback: derive ally hero list from duels if backend didn't return ally_ids
        if (!allyIds.length && data.duels) {
            var _seen = {};
            data.duels.forEach(function(d) {
                (d.ally_heroes || []).forEach(function(h) {
                    if (!_seen[h.hero_id]) { _seen[h.hero_id] = true; allyIds.push(h.hero_id); }
                });
            });
        }

        if (!synPairs.length || allyIds.length < 2) {
            if (!synPairs.length) console.warn('[synergy] synergy_pairs missing — restart backend to apply API update');
            return;
        }

        var synScreen = document.getElementById('dr-synergy-screen');
        var NS = 'http://www.w3.org/2000/svg';

        // ── Build DOM ────────────────────────────────────────────────
        var dotsHtml = synPairs.map(function(_, pi) {
            return '<div class="dr-dot" id="dr-syn-dot-' + pi + '"></div>';
        }).join('');

        synScreen.innerHTML = (
            '<div class="dr-syn-title">Командная синергия</div>' +
            '<div class="dr-syn-penta" id="dr-syn-penta"></div>' +
            '<div class="dr-syn-score-wrap">' +
                '<div class="dr-syn-total" id="dr-syn-total">+0.0</div>' +
                '<div class="dr-syn-delta" id="dr-syn-delta"></div>' +
            '</div>' +
            '<div class="dr-dots" style="margin-top:8px;">' + dotsHtml + '</div>'
        );

        var penta   = document.getElementById('dr-syn-penta');
        var totalEl = document.getElementById('dr-syn-total');
        var deltaEl = document.getElementById('dr-syn-delta');

        // SVG canvas (positioned absolute over penta, pointer-events:none)
        var svgEl = document.createElementNS(NS, 'svg');
        svgEl.style.cssText = 'position:absolute;top:0;left:0;pointer-events:none;overflow:visible;';
        penta.appendChild(svgEl);

        // Hero slots — positioned by JS after layout
        var SLOT_HALF = 25; // half of 50px slot
        var slots = allyIds.map(function(heroId, i) {
            var slot = document.createElement('div');
            slot.id = 'dr-syn-slot-' + i;
            slot.className = 'dr-syn-slot';
            var img = document.createElement('img');
            img.src = _icon(heroId);
            img.className = 'dr-syn-av';
            img.onerror = function() { this.style.opacity = 0; };
            slot.appendChild(img);
            penta.appendChild(slot);
            return slot;
        });

        // ── Fade in screen ───────────────────────────────────────────
        var overlay = document.getElementById('dr-bg-overlay');
        if (overlay) gsap.to(overlay, {opacity: 0.2, duration: 0.5});
        synScreen.style.display = 'block';
        gsap.fromTo(synScreen, {opacity: 0}, {opacity: 1, duration: 0.4, ease: 'power2.out'});

        await sleep(200);
        if (_drafterSkip) return;

        // ── Pentagon geometry ────────────────────────────────────────
        var RADIUS   = 88;
        var pentaW   = penta.offsetWidth || 300;
        var cx       = pentaW / 2;
        var cy       = RADIUS + 30;                            // top vertex at y=30
        var bottomY  = cy + RADIUS * Math.sin(2 * Math.PI / 5); // ≈ cy+71
        var pentaH   = Math.ceil(bottomY + SLOT_HALF + 10);   // bottom slot edge + padding

        var pts = allyIds.map(function(_, i) {
            return {
                x: cx + RADIUS * Math.cos(i * 2 * Math.PI / 5 - Math.PI / 2),
                y: cy + RADIUS * Math.sin(i * 2 * Math.PI / 5 - Math.PI / 2)
            };
        });

        // Apply geometry
        penta.style.height = pentaH + 'px';
        svgEl.setAttribute('width',   pentaW);
        svgEl.setAttribute('height',  pentaH);
        svgEl.setAttribute('viewBox', '0 0 ' + pentaW + ' ' + pentaH);

        slots.forEach(function(slot, i) {
            slot.style.left = (pts[i].x - SLOT_HALF) + 'px';
            slot.style.top  = (pts[i].y - SLOT_HALF) + 'px';
        });

        // ── Hero entrance: simple fade-in with subtle scale ──────────
        gsap.set(slots, {scale: 0.85, opacity: 0});
        for (var hi = 0; hi < slots.length; hi++) {
            if (_drafterSkip) return;
            gsap.to(slots[hi], {scale: 1, opacity: 1, duration: 0.3, ease: 'power2.out'});
            await sleep(110);
        }

        await sleep(240);
        if (_drafterSkip) return;

        // ── SVG helpers ──────────────────────────────────────────────
        function mkSvg(tag, attrs) {
            var el = document.createElementNS(NS, tag);
            Object.keys(attrs).forEach(function(k) { el.setAttribute(k, attrs[k]); });
            return el;
        }

        // Perimeter = adjacent vertices (index diff 1 or wraps 0↔n-1)
        var N = allyIds.length;
        function isPerimeter(i1, i2) {
            var a = Math.min(i1, i2), b = Math.max(i1, i2);
            return (b - a === 1) || (a === 0 && b === N - 1);
        }

        // Build two-layer bezier (glow + main), returns {glow, main}
        function buildBezier(i1, i2, color, intensity) {
            var p1 = pts[i1], p2 = pts[i2];
            var mx = (p1.x + p2.x) / 2, my = (p1.y + p2.y) / 2;
            var dx = cx - mx, dy = cy - my;
            var dist = Math.sqrt(dx * dx + dy * dy) || 1;
            var ux = dx / dist, uy = dy / dist;
            // Perimeter bends outward (negative = away from center)
            // Diagonals bend inward (positive = toward center)
            var off = isPerimeter(i1, i2)
                ? -(28 + intensity * 14)
                :  (22 + intensity * 10);
            var cpx = mx + ux * off, cpy = my + uy * off;
            var d = 'M ' + p1.x.toFixed(1) + ' ' + p1.y.toFixed(1)
                  + ' Q ' + cpx.toFixed(1) + ' ' + cpy.toFixed(1)
                  + ' ' + p2.x.toFixed(1) + ' ' + p2.y.toFixed(1);

            var glow = mkSvg('path', {d: d, stroke: color, 'stroke-width': '7',
                                      fill: 'none', 'stroke-linecap': 'round'});
            glow.style.opacity = '0';
            var main = mkSvg('path', {d: d, stroke: color, 'stroke-width': '2',
                                      fill: 'none', 'stroke-linecap': 'round'});
            main.style.opacity = '0';
            svgEl.appendChild(glow);
            svgEl.appendChild(main);

            var len = main.getTotalLength();
            gsap.set(main, {attr: {'stroke-dasharray': len, 'stroke-dashoffset': len}});
            gsap.set(glow, {attr: {'stroke-dasharray': len, 'stroke-dashoffset': len}});
            return {glow: glow, main: main};
        }

        // ── 10 пар ──────────────────────────────────────────────────
        var running = 0;

        for (var pi = 0; pi < synPairs.length; pi++) {
            if (_drafterSkip) return;

            var pair  = synPairs[pi];
            var idx1  = allyIds.indexOf(pair.hero_id1);
            var idx2  = allyIds.indexOf(pair.hero_id2);
            if (idx1 < 0 || idx2 < 0) continue;

            var val       = pair.value;
            var intensity = Math.min(Math.abs(val) / 18, 1);
            var lineColor = val > 0 ? '#3db87a' : '#e5534b';

            // Progress dots
            if (pi > 0) {
                var pd = document.getElementById('dr-syn-dot-' + (pi - 1));
                if (pd) pd.className = 'dr-dot ' + (synPairs[pi-1].value >= 0 ? 'dr-dot-win' : 'dr-dot-loss');
            }
            var cd = document.getElementById('dr-syn-dot-' + pi);
            if (cd) cd.className = 'dr-dot dr-dot-active';

            // Highlight active pair, dim rest
            slots.forEach(function(sl, si) {
                var on = si === idx1 || si === idx2;
                gsap.to(sl, {opacity: on ? 1 : 0.2, scale: on ? 1.1 : 1,
                             duration: 0.18, ease: 'power2.out'});
            });

            await sleep(80);
            if (_drafterSkip) return;

            // Draw bezier
            svgEl.innerHTML = '';
            var bez = buildBezier(idx1, idx2, lineColor, intensity);

            // Endpoint dots
            [idx1, idx2].forEach(function(i) {
                svgEl.appendChild(mkSvg('circle', {
                    cx: pts[i].x.toFixed(1), cy: pts[i].y.toFixed(1),
                    r: '4', fill: lineColor
                }));
            });

            gsap.to(bez.main, {attr: {'stroke-dashoffset': 0}, opacity: 1,
                               duration: 0.35, ease: 'power2.inOut'});
            gsap.to(bez.glow, {attr: {'stroke-dashoffset': 0}, opacity: 0.22,
                               duration: 0.35, ease: 'power2.inOut'});

            // Score counter (total stays in place)
            var newRunning = running + val;
            (function(from, to) {
                var obj = {v: from};
                gsap.to(obj, {v: to, duration: 0.35, ease: 'power2.out',
                    onUpdate: function() {
                        var sign = obj.v > 0.05 ? '+' : (obj.v < -0.05 ? '' : '+');
                        totalEl.textContent = sign + obj.v.toFixed(1);
                        totalEl.style.color = obj.v > 0.5  ? '#3db87a'
                                            : obj.v < -0.5 ? '#e5534b' : '#d29922';
                    }
                });
            })(running, newRunning);
            running = newRunning;

            // Delta: slide up from below, then exit upward
            var dSign = val >= 0 ? '+' : '';
            deltaEl.textContent = dSign + val.toFixed(1);
            deltaEl.style.color = lineColor;
            gsap.fromTo(deltaEl, {opacity: 0, y: 12}, {opacity: 1, y: 0,
                                  duration: 0.25, ease: 'power2.out'});

            await sleep(480);
            if (_drafterSkip) return;

            gsap.to([bez.main, bez.glow], {opacity: 0, duration: 0.2});
            gsap.to(deltaEl, {opacity: 0, y: -10, duration: 0.22, ease: 'power2.in'});

            await sleep(160);
        }

        // Mark last dot
        var lastDot = document.getElementById('dr-syn-dot-' + (synPairs.length - 1));
        if (lastDot) {
            lastDot.className = 'dr-dot ' + (synPairs[synPairs.length - 1].value >= 0
                                             ? 'dr-dot-win' : 'dr-dot-loss');
        }

        if (_drafterSkip) return;

        // Reset all heroes, clear SVG
        slots.forEach(function(sl) { gsap.to(sl, {opacity: 1, scale: 1, duration: 0.3, ease: 'back.out(1)'}); });
        gsap.set(deltaEl, {opacity: 0, y: 0});
        svgEl.innerHTML = '';

        await sleep(280);
        if (_drafterSkip) return;

        // ── Final score card ─────────────────────────────────────────
        var finalScore = data.synergy_score || 0;
        var cardColor  = finalScore >= 24 ? '#3db87a' : finalScore >= 16 ? '#d29922' : '#e5534b';

        var card = document.createElement('div');
        card.className = 'dr-syn-card';
        card.innerHTML = (
            '<div class="dr-syn-card-label">СИНЕРГИЯ</div>' +
            '<div class="dr-syn-card-val" id="dr-syn-fval" style="color:' + cardColor + ';">0.0</div>' +
            '<div class="dr-syn-card-sub">из 33 очков</div>'
        );
        synScreen.appendChild(card);

        gsap.fromTo(card, {opacity: 0, scale: 0.88, y: 8},
                          {opacity: 1, scale: 1, y: 0, duration: 0.4, ease: 'back.out(1.5)'});

        var fvalEl = document.getElementById('dr-syn-fval');
        var cnt = {v: 0};
        gsap.to(cnt, {v: finalScore, duration: 0.7, ease: 'power2.out',
            onUpdate: function() { fvalEl.textContent = cnt.v.toFixed(1); }
        });

        await sleep(2200);
        if (_drafterSkip) return;

        // Fade out and hand off to showFinal
        gsap.to(synScreen, {opacity: 0, duration: 0.4, ease: 'power2.in', onComplete: function() {
            synScreen.style.display = 'none';
            gsap.set(synScreen, {opacity: 1});
        }});
        await sleep(420);
    }

    async function runBattles() {
        for (var i = 0; i < duels.length; i++) {
            if (_drafterSkip) return;
            await playBattle(i, duels[i]);
        }
        if (_drafterSkip) return;
        gsap.set(battleScreen, {clearProps: 'x'});
        battleScreen.style.display = 'none';
        await playSynergy();
        if (_drafterSkip) return;
        var sb = document.getElementById('dr-skip-btn');
        if (sb) sb.remove();
        showFinal();
    }

    // ── Шаг 2: финальный экран ───────────────────────────────────────────
    function showFinal() {
        var sb = document.getElementById('dr-skip-btn');
        if (sb) sb.remove();

        var _sfOverlay = document.getElementById('dr-bg-overlay');
        if (_sfOverlay) gsap.to(_sfOverlay, {opacity: 0, duration: 0.5, ease: 'power2.out'});

        var total = Math.round(data.total_score || 0);
        var rank, rankColor, rankDesc, rankGlow;
        if (total >= 85) {
            rank = 'SSS'; rankColor = '#d29922'; rankDesc = 'Абсолютный драфтер';             rankGlow = true;
        } else if (total >= 80) {
            rank = 'S';   rankColor = '#d29922'; rankDesc = 'Как ты это сделал?';           rankGlow = true;
        } else if (total >= 65) {
            rank = 'A';   rankColor = '#7b8bb8'; rankDesc = 'Хороший драфт!';               rankGlow = false;
        } else if (total >= 50) {
            rank = 'B';   rankColor = '#60a5fa'; rankDesc = 'Неплохо, но можно лучше';      rankGlow = false;
        } else {
            rank = 'C';   rankColor = '#9ca3af'; rankDesc = 'Надо тренироваться, братанчик'; rankGlow = false;
        }

        var best = parseInt(localStorage.getItem('drafter_best_score') || '0', 10);
        var isRecord = total > best;
        if (isRecord) {
            localStorage.setItem('drafter_best_score', total);
            var bestLabel = document.getElementById('drafter-best-score');
            if (bestLabel) bestLabel.textContent = total;
        }

        // ── Битвы линий ──────────────────────────────────────────────────
        var laneCardsHtml = duels.map(function(duel) {
            var synColor = duel.win ? '#3db87a' : '#e5534b';
            var absSyn   = Math.abs(duel.synergy || 0);
            var pct      = Math.min(95, Math.max(15, 50 + absSyn * 4));
            var pctRound = Math.round(pct);

            var allyAvatars = (duel.ally_heroes || []).map(function(h) {
                return '<div class="lane-avatar"><img src="' + _icon(h.hero_id) + '" width="24" height="24" style="object-fit:cover;border-radius:4px;" onerror="this.style.display=\'none\'"></div>';
            }).join('');
            var enemyAvatars = (duel.enemy_heroes || []).map(function(h) {
                return '<div class="lane-avatar"><img src="' + _icon(h.hero_id) + '" width="24" height="24" style="object-fit:cover;border-radius:4px;" onerror="this.style.display=\'none\'"></div>';
            }).join('');

            // Победившая половина: наша (левая) если win, вражеская (правая) если нет
            var allyFillHtml  = duel.win
                ? '<div class="lane-ally-fill" data-pct="' + pctRound + '" style="width:0%;height:100%;background:#3db87a;"></div>'
                : '';
            var enemyFillHtml = !duel.win
                ? '<div class="lane-enemy-fill" data-pct="' + pctRound + '" style="width:0%;height:100%;background:#e5534b;"></div>'
                : '';

            // Подпись: одно число, прижатое к победившей стороне
            var labelHtml = duel.win
                ? '<span class="lane-bar-val" style="color:#3db87a;">' + pctRound + '%</span><span></span>'
                : '<span></span><span class="lane-bar-val" style="color:#e5534b;text-align:right;">' + pctRound + '%</span>';

            return (
                '<div class="lane-card">' +
                    '<div class="lane-header">' +
                        '<span style="font-size:11px;font-weight:700;color:#e5e7eb;">' + duel.name + '</span>' +
                        '<span style="font-size:11px;font-weight:700;color:' + synColor + ';">' + (duel.synergy != null ? duel.synergy.toFixed(2) : '\u2014') + '</span>' +
                    '</div>' +
                    '<div class="lane-teams">' +
                        '<div class="lane-team">' +
                            '<div class="lane-team-label">\u041c\u042b</div>' +
                            '<div class="lane-heroes">' + allyAvatars + '</div>' +
                        '</div>' +
                        '<div class="lane-team right">' +
                            '<div class="lane-team-label" style="text-align:right;">\u0412\u0420\u0410\u0413\u0418</div>' +
                            '<div class="lane-heroes">' + enemyAvatars + '</div>' +
                        '</div>' +
                    '</div>' +
                    '<div class="lane-bar-center">' +
                        '<div class="lane-bar-ally-half">' + allyFillHtml + '</div>' +
                        '<div class="lane-bar-enemy-half">' + enemyFillHtml + '</div>' +
                    '</div>' +
                    '<div class="lane-bar-labels">' + labelHtml + '</div>' +
                '</div>'
            );
        }).join('');

        // ── Ключевые матчапы ─────────────────────────────────────────────
        var comments = data.comments || [];
        var matchupCardsHtml = comments.slice(0, 4).map(function(c) {
            if (c.kind === 'synergy') {
                var n1   = _name(c.hero_id1);
                var n2   = _name(c.hero_id2);
                var sign = c.value >= 0 ? '+' : '';
                return (
                    '<div class="matchup-card" style="border:1px solid rgba(123,139,184,0.15);background:rgba(123,139,184,0.04);">' +
                        '<div class="mc-heroes">' +
                            '<div class="mc-av"><img src="' + _icon(c.hero_id1) + '" width="22" height="22" style="object-fit:cover;border-radius:4px;" onerror="this.style.display=\'none\'"></div>' +
                            '<span class="mc-sep">+</span>' +
                            '<div class="mc-av"><img src="' + _icon(c.hero_id2) + '" width="22" height="22" style="object-fit:cover;border-radius:4px;" onerror="this.style.display=\'none\'"></div>' +
                        '</div>' +
                        '<div class="mc-info">' +
                            '<div class="mc-text">' + n1 + ' + ' + n2 + '</div>' +
                            '<div style="font-size:8px;color:#8b5cf6;">\u0421\u0438\u043d\u0435\u0440\u0433\u0438\u044f</div>' +
                        '</div>' +
                        '<div class="mc-val" style="color:#8b5cf6;">' + sign + c.value.toFixed(1) + '</div>' +
                    '</div>'
                );
            }
            if (c.kind === 'matchup') {
                var allyName  = _name(c.ally_hero_id);
                var enemyName = _name(c.enemy_hero_id);
                if (c.value > 0) {
                    return (
                        '<div class="matchup-card" style="border:1px solid rgba(61,184,122,0.20);background:rgba(61,184,122,0.04);">' +
                            '<div class="mc-heroes">' +
                                '<div class="mc-av"><img src="' + _icon(c.ally_hero_id) + '" width="22" height="22" style="object-fit:cover;border-radius:4px;" onerror="this.style.display=\'none\'"></div>' +
                                '<span class="mc-sep">vs</span>' +
                                '<div class="mc-av"><img src="' + _icon(c.enemy_hero_id) + '" width="22" height="22" style="object-fit:cover;border-radius:4px;" onerror="this.style.display=\'none\'"></div>' +
                            '</div>' +
                            '<div class="mc-info">' +
                                '<div class="mc-text">' + allyName + ' \u043a\u043e\u043d\u0442\u0440\u0438\u0442</div>' +
                                '<div style="font-size:8px;color:#3db87a;">' + enemyName + '</div>' +
                            '</div>' +
                            '<div class="mc-val" style="color:#3db87a;">+' + c.value.toFixed(1) + '</div>' +
                        '</div>'
                    );
                } else {
                    return (
                        '<div class="matchup-card" style="border:1px solid rgba(229,83,75,0.20);background:rgba(229,83,75,0.04);">' +
                            '<div class="mc-heroes">' +
                                '<div class="mc-av"><img src="' + _icon(c.ally_hero_id) + '" width="22" height="22" style="object-fit:cover;border-radius:4px;" onerror="this.style.display=\'none\'"></div>' +
                                '<span class="mc-sep">vs</span>' +
                                '<div class="mc-av"><img src="' + _icon(c.enemy_hero_id) + '" width="22" height="22" style="object-fit:cover;border-radius:4px;" onerror="this.style.display=\'none\'"></div>' +
                            '</div>' +
                            '<div class="mc-info">' +
                                '<div class="mc-text">' + allyName + ' \u043f\u0440\u043e\u0438\u0433\u0440\u044b\u0432\u0430\u0435\u0442</div>' +
                                '<div style="font-size:8px;color:#e5534b;">' + enemyName + '</div>' +
                            '</div>' +
                            '<div class="mc-val" style="color:#e5534b;">' + c.value.toFixed(1) + '</div>' +
                        '</div>'
                    );
                }
            }
            return '';
        }).join('');

        var warnComment = comments.find(function(c) { return c.type === 'warn' && c.kind === 'position'; });
        var warnCardHtml = '';
        if (warnComment && warnComment.hero_ids && warnComment.hero_ids.length > 0) {
            var avatarsHtml = warnComment.hero_ids.map(function(hid) {
                return '<div class="mc-av"><img src="' + _icon(hid) + '" width="22" height="22" style="object-fit:cover;border-radius:4px;" onerror="this.style.display=\'none\'"></div>';
            }).join('');
            warnCardHtml = (
                '<div class="matchup-card" style="border:1px solid rgba(210,153,34,0.20);background:rgba(210,153,34,0.04);">' +
                    '<div class="mc-heroes">' + avatarsHtml + '</div>' +
                    '<div class="mc-info">' +
                        '<div class="mc-text" style="color:#f59e0b;">\u043d\u0430 \u043d\u0435\u0442\u0438\u043f\u0438\u0447\u043d\u043e\u0439 \u043f\u043e\u0437\u0438\u0446\u0438\u0438</div>' +
                    '</div>' +
                    '<div class="mc-val" style="color:#f59e0b;">&#x26A0;</div>' +
                '</div>'
            );
        }

        finalScreen.style.display = 'block';
        finalScreen.innerHTML = (
            '<div class="dr-fin-wrap">' +
                '<div class="dr-fin-rank-wrap" style="display:flex;flex-direction:column;align-items:center;width:100%;">' +
                    '<div class="dr-fin-rank-label">\u0422\u0412\u041e\u042f \u041e\u0426\u0415\u041d\u041a\u0410</div>' +
                    '<div class="dr-fin-letter" id="dr-fin-letter" style="color:' + rankColor + ';opacity:0;">' + rank + '</div>' +
                    (isRecord ? '<div class="dr-fin-record">\ud83c\udfc6 \u041d\u043e\u0432\u044b\u0439 \u0440\u0435\u043a\u043e\u0440\u0434!</div>' : '') +
                    '<div class="dr-fin-desc">' + rankDesc + '</div>' +
                '</div>' +
                '<div style="width:100%;margin-bottom:6px;">' +
                    '<div class="dr-fin-block-title">\u0411\u0418\u0422\u0412\u042b \u041b\u0418\u041d\u0418\u0419</div>' +
                    '<div>' + laneCardsHtml + '</div>' +
                '</div>' +
                (matchupCardsHtml || warnCardHtml ? (
                    '<div style="width:100%;margin-bottom:6px;">' +
                        '<div class="dr-fin-block-title">\u041a\u041b\u042e\u0427\u0415\u0412\u042b\u0415 \u041c\u0410\u0422\u0427\u0410\u041f\u042b</div>' +
                        '<div>' + matchupCardsHtml + warnCardHtml + '</div>' +
                    '</div>'
                ) : '') +
                '<button class="dr-fin-btn" id="dr-fin-btn" onclick="loadDrafterMatch()">\u27f3 \u041d\u041e\u0412\u042b\u0419 \u041c\u0410\u0422\u0427</button>' +
            '</div>'
        );

        // Анимация прогресс-баров — только победившая половина
        Array.from(finalScreen.querySelectorAll('.lane-card')).forEach(function(card, i) {
            var fill = card.querySelector('.lane-ally-fill') || card.querySelector('.lane-enemy-fill');
            if (!fill) return;
            var pct      = parseFloat(fill.getAttribute('data-pct'));
            var barDelay = 0.3 + (2 + i) * 0.12 + 0.4;
            gsap.fromTo(fill, {width: '0%'}, {width: pct + '%', duration: 0.8, ease: 'power2.out', delay: barDelay});
        });

        // Буква — отдельная pop-анимация (rank-pop)
        var letterEl = document.getElementById('dr-fin-letter');
        gsap.fromTo(letterEl,
            {scale: 0.05, opacity: 0},
            {scale: 1, opacity: 1, duration: 0.7, ease: 'back.out(1.5)', delay: 0.5, onComplete: function() {
                if (rankGlow) {
                    gsap.to(letterEl, {textShadow: '0 0 30px rgba(251,191,36,0.9)', yoyo: true, repeat: -1, duration: 1.5, ease: 'sine.inOut'});
                }
            }}
        );

        // Stagger-анимация в DOM-порядке — охватывает все видимые элементы включая заголовки секций
        var animEls = Array.from(finalScreen.querySelectorAll(
            '.dr-fin-rank-wrap, .dr-fin-block-title, .lane-card, .matchup-card, #dr-fin-btn'
        ));
        gsap.fromTo(animEls,
            {opacity: 0, y: 16},
            {opacity: 1, y: 0, duration: 0.4, stagger: 0.12, ease: 'power2.out', delay: 0.3}
        );
    }

    // Skip button — top-right pill, appended to body so position:fixed is viewport-relative
    var _skipBtn = document.createElement('button');
    _skipBtn.id = 'dr-skip-btn';
    _skipBtn.className = 'dr-skip-btn';
    _skipBtn.textContent = 'Пропустить';
    _skipBtn.addEventListener('click', skipDrafterAnim);
    document.body.appendChild(_skipBtn);
    gsap.fromTo(_skipBtn, {opacity: 0, x: 12}, {opacity: 1, x: 0, duration: 0.35, delay: 0.5, ease: 'power2.out'});

    runBattles();
}

function _drafterCommentText(c) {
    var name1, name2;
    if (c.kind === 'synergy') {
        name1 = _drafterHeroName(c.hero_id1) || ('Герой #' + c.hero_id1);
        name2 = _drafterHeroName(c.hero_id2) || ('Герой #' + c.hero_id2);
        var sign = c.value >= 0 ? '+' : '';
        return 'Хорошая синергия: ' + name1 + ' + ' + name2 + ' (' + sign + c.value.toFixed(1) + ')';
    }
    if (c.kind === 'matchup') {
        name1 = _drafterHeroName(c.ally_hero_id) || ('Герой #' + c.ally_hero_id);
        name2 = _drafterHeroName(c.enemy_hero_id) || ('Герой #' + c.enemy_hero_id);
        return name1 + ' проигрывает вражескому ' + name2 + ' (' + c.value.toFixed(1) + ')';
    }
    if (c.kind === 'position') {
        name1 = _drafterHeroName(c.hero_id) || ('Герой #' + c.hero_id);
        return name1 + ' На нетипичной позиции';
    }
    return '';
}

