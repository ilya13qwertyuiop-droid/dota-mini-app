
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
            document.querySelectorAll('.nav-item')[2].classList.add('active');
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

                // Считаем немедленно, параллельно с экраном загрузки
                const topHeroes = this.calculateTopHeroes().slice(0, 6);

                this._startHeroLoading();

                setTimeout(() => {
                    const loading = document.getElementById('hero-loading');
                    loading.style.transition = 'opacity 0.4s ease';
                    loading.style.opacity = '0';
                    setTimeout(() => {
                        loading.style.display = 'none';
                        loading.style.opacity = '';
                        loading.style.transition = '';
                        this._renderResult(topHeroes);
                    }, 400);
                }, 5500);
            },

            _startHeroLoading() {
                const loading = document.getElementById('hero-loading');
                loading.style.display = 'flex';
                loading.style.opacity = '1';

                // Иконки — хаотичный дрейф по всему экрану
                const heroNames = Object.keys(window.dotaHeroImages || {});
                const shuffled = [...heroNames].sort(() => Math.random() - 0.5).slice(0, 14);

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
                    const dur  = (12 + Math.random() * 8).toFixed(1); // 12–20s
                    const delay = (2 + i * 0.18).toFixed(2); // первые 2с — только фон и панель

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

                // Звёздное поле
                const starsEl = document.getElementById('hloStars');
                starsEl.innerHTML = '';
                for (let i = 0; i < 25; i++) {
                    const s = document.createElement('div');
                    s.className = 'hlo-star';
                    const sz = [2, 3, 4][Math.floor(Math.random() * 3)];
                    s.style.cssText = `
                        width:${sz}px; height:${sz}px;
                        top:${Math.random() * 100}%;
                        left:${Math.random() * 100}%;
                        --dur:${(1.5 + Math.random() * 2).toFixed(2)}s;
                        --delay:-${(Math.random() * 3).toFixed(2)}s;
                    `;
                    starsEl.appendChild(s);
                }

                // Прогресс-бар 0 → 100% за 5.5с
                const fill = document.getElementById('hloProgressFill');
                fill.style.transition = 'none';
                fill.style.width = '0%';
                requestAnimationFrame(() => requestAnimationFrame(() => {
                    fill.style.transition = 'width 5.5s linear';
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

                        <div class="guide-row">
                        <span>Гайд на D2PT</span>
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

            const url = getDota2ProTrackerUrl(heroName);

            if (tg && typeof tg.openLink === 'function') {
                tg.openLink(url);          // откроет во встроенном браузере Telegram
            } else {
                window.open(url, '_blank'); // запасной вариант
            }
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
    const posLabel = parts[0] || ''; // "Pos 1"
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
        console.log('[matchups] selected heroName =', heroName, 'heroId =', heroId);
        if (!heroId) {
            console.warn('[matchups] no heroId for heroName =', heroName);
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
var _activeFacetIdx = 0;
var _buildPosition  = null;   // 'POSITION_1' … 'POSITION_5'
var _buildRank      = 'ALL';  // 'ALL' | 'DIVINE_IMMORTAL'
var _buildSubTab    = 'facets'; // 'facets' | 'talents' | 'items' | 'skillbuild'

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

function _showBuildLoading() {
    _buildData      = null;
    _activeFacetIdx = 0;
    _buildPosition  = null;
    _buildRank      = 'ALL';
    _buildSubTab    = 'facets';
    var el = document.getElementById('build-content');
    if (el) el.innerHTML = '<p class="matchup-placeholder-text">Загрузка...</p>';
}

function _getTopPositions(data) {
    var positions = (data.stratz && data.stratz.ALL && data.stratz.ALL.positions) || [];
    return positions.slice()
        .sort(function (a, b) { return (b.matchCount || 0) - (a.matchCount || 0); })
        .slice(0, 3)
        .map(function (p) { return p.position; });
}

// ── Фасеты ────────────────────────────────────────────────────────────────

function selectFacet(idx) {
    _activeFacetIdx = idx;
    document.querySelectorAll('.build-facet-btn').forEach(function (btn, i) {
        btn.classList.toggle('active', i === idx);
    });
    var descEl = document.getElementById('build-facet-desc');
    if (descEl && _buildData) {
        var f = (_buildData.facets || [])[idx];
        descEl.textContent = f ? (f.description || '') : '';
    }
}

// ── Фильтры позиции / ранга ───────────────────────────────────────────────

function selectBuildPosition(pos) {
    _buildPosition = pos;
    document.querySelectorAll('.build-pos-btn').forEach(function (b) {
        b.classList.toggle('active', b.getAttribute('data-pos') === pos);
    });
    _renderBuildSubContent();
}

function selectBuildRank(rank) {
    _buildRank = rank;
    document.querySelectorAll('.build-rank-btn').forEach(function (b) {
        b.classList.toggle('active', b.getAttribute('data-rank') === rank);
    });
    _renderBuildSubContent();
}

// ── Горизонтальные подвкладки ─────────────────────────────────────────────

function selectBuildSubTab(tab) {
    _buildSubTab = tab;
    document.querySelectorAll('.build-subtab').forEach(function (b) {
        b.classList.toggle('active', b.getAttribute('data-tab') === tab);
    });
    _renderBuildSubContent();
}

// ── Итемные вкладки (стартовые / основные) ────────────────────────────────

function switchItemsTab(tab, btn) {
    ['start', 'core'].forEach(function (t) {
        var panel = document.getElementById('items-panel-' + t);
        if (panel) panel.style.display = t === tab ? '' : 'none';
    });
    document.querySelectorAll('.build-items-tab').forEach(function (b) {
        b.classList.toggle('active', b === btn);
    });
}

// ── Контент каждой подвкладки ─────────────────────────────────────────────

function _renderFacetsContent(data) {
    var facets = data.facets || [];
    if (facets.length <= 1) {
        return '<p class="build-placeholder">Аспекты для этого героя недоступны</p>';
    }
    var colorMap = {
        0: 'rgba(146,64,14,0.22)',  1: 'rgba(200,60,60,0.22)',
        2: 'rgba(34,197,94,0.22)',  3: 'rgba(6,182,212,0.22)',
        4: 'rgba(168,85,247,0.22)',
    };
    var btns = facets.map(function (f, i) {
        var iconUrl = '/images/facet_icons/' + (f.icon || '') + '.png';
        var bg = colorMap[f.color] !== undefined ? colorMap[f.color] : 'rgba(255,255,255,0.08)';
        var activeCls = i === _activeFacetIdx ? ' active' : '';
        return '<button class="build-facet-btn' + activeCls + '" data-idx="' + i + '" onclick="selectFacet(' + i + ')" style="background:' + bg + '">' +
            '<img src="' + iconUrl + '" class="build-facet-icon" onerror="this.style.display=\'none\'">' +
            '<span class="build-facet-name">' + (f.title || f.name || '') + '</span>' +
            '</button>';
    }).join('');
    var activeDesc = facets[_activeFacetIdx] ? (facets[_activeFacetIdx].description || '') : '';
    return '<div class="build-facets">' + btns + '</div>' +
        '<div class="build-facet-desc" id="build-facet-desc">' + activeDesc + '</div>';
}

function _renderTalentsContent(data) {
    var talents = data.talents || [];
    if (talents.length === 0) {
        return '<p class="build-placeholder">Данные о талантах недоступны</p>';
    }

    // Stratz talent popularity for current position/rank
    // score = winCount (= matchCount * winrate) — combined popularity+winrate formula
    var stratzTalents = [];
    var rankData = data.stratz && data.stratz[_buildRank];
    var posData  = rankData && rankData.by_position && rankData.by_position[_buildPosition];
    if (posData && posData.talents) {
        stratzTalents = posData.talents;
    }
    var abilityScore = {}; // abilityId -> winCount as score
    stratzTalents.forEach(function (t) { abilityScore[t.abilityId] = t.winCount || 0; });

    // Reverse map: abilityName -> abilityId
    var nameToId = {};
    Object.keys(data.ability_id_to_name || {}).forEach(function (id) {
        nameToId[data.ability_id_to_name[id]] = parseInt(id, 10);
    });

    var hasStratz = stratzTalents.length > 0;
    var sorted = talents.slice().sort(function (a, b) { return (b.level || 0) - (a.level || 0); });
    var rows = sorted.map(function (t) {
        var leftId  = nameToId[t.left_ability]  || 0;
        var rightId = nameToId[t.right_ability] || 0;
        var leftScore  = leftId  ? (abilityScore[leftId]  || 0) : 0;
        var rightScore = rightId ? (abilityScore[rightId] || 0) : 0;
        var leftPopular  = hasStratz && leftScore  > rightScore;
        var rightPopular = hasStratz && rightScore > leftScore;

        var leftCls  = 'build-talent-card build-talent-left'  + (leftPopular  ? ' build-talent-popular' : '');
        var rightCls = 'build-talent-card build-talent-right' + (rightPopular ? ' build-talent-popular' : '');
        return '<div class="build-talent-row">' +
            '<div class="' + leftCls  + '">' + (t.left  || '') + '</div>' +
            '<div class="build-talent-level-badge">' + (t.level || '') + '</div>' +
            '<div class="' + rightCls + '">' + (t.right || '') + '</div>' +
            '</div>';
    }).join('');
    return '<div class="build-talent-tree">' + rows + '</div>';
}

function _findBy(arr, key, val) {
    for (var i = 0; i < arr.length; i++) {
        if (arr[i][key] === val) return arr[i];
    }
    return null;
}

function _renderItemsContent(data) {
    var rankData = data.stratz && data.stratz[_buildRank];
    var posData  = rankData && rankData.by_position && rankData.by_position[_buildPosition];
    var itemsDb  = data.items_db || {};

    function resolveStratz(entry) {
        var info = itemsDb[String(entry.itemId)] || {};
        return {
            dname:      info.dname || ('Item ' + entry.itemId),
            img:        info.img   || null,
            matchCount: entry.matchCount || 0,
            winrate:    entry.matchCount ? (entry.winCount / entry.matchCount) : null,
        };
    }

    var startItems, coreItems;
    if (posData && posData.start_items && posData.start_items.length) {
        startItems = posData.start_items
            .slice().sort(function (a, b) { return (b.matchCount || 0) - (a.matchCount || 0); })
            .slice(0, 6).map(resolveStratz);
    } else {
        startItems = (data.items && data.items.start_game_items) || [];
    }
    if (posData && posData.core_items && posData.core_items.length) {
        coreItems = posData.core_items
            .slice().sort(function (a, b) { return (b.matchCount || 0) - (a.matchCount || 0); })
            .slice(0, 6).map(resolveStratz);
    } else {
        coreItems = (data.items && data.items.core_items) || [];
    }

    function itemSlot(item, showStats) {
        var wr    = (showStats && item.winrate != null) ? Math.round(item.winrate * 100) + '%' : '';
        var games = (showStats && item.matchCount)      ? item.matchCount + '\u00a0игр' : '';
        return '<div class="build-item-slot">' +
            (item.img
                ? '<img src="' + item.img + '" class="build-item-icon" onerror="this.style.opacity=\'0.3\'">'
                : '<div class="build-item-icon"></div>') +
            '<span class="build-item-name">' + (item.dname || '') + '</span>' +
            (wr    ? '<span class="build-item-stat">'  + wr    + '</span>' : '') +
            (games ? '<span class="build-item-games">' + games + '</span>' : '') +
            '</div>';
    }

    var startSlots = startItems.map(function (item) { return itemSlot(item, false); }).join('');
    var coreSlots  = coreItems.map(function  (item) { return itemSlot(item, true);  }).join('');

    return '<div class="build-items-tabs">' +
        '<button class="build-items-tab active" onclick="switchItemsTab(\'start\', this)">Стартовые</button>' +
        '<button class="build-items-tab" onclick="switchItemsTab(\'core\', this)">Основные</button>' +
        '</div>' +
        '<div class="build-items-panel" id="items-panel-start">' +
        '<div class="build-items-row">' + startSlots + '</div>' +
        '</div>' +
        '<div class="build-items-panel" id="items-panel-core" style="display:none">' +
        '<div class="build-items-row">' + coreSlots + '</div>' +
        '</div>';
}

function _renderSkillbuildContent(data) {
    var abilities = (data.ability_build || []).filter(function (aname) {
        return aname.indexOf('special_bonus_') !== 0;
    });
    if (abilities.length === 0) {
        return '<p class="build-placeholder">Данные собираются, скоро появится</p>';
    }
    var slots = abilities.map(function (aname, i) {
        var iconUrl = 'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/abilities/' + aname + '.png';
        return '<div class="build-ability-slot">' +
            '<div class="build-ability-level">' + (i + 1) + '</div>' +
            '<img src="' + iconUrl + '" class="build-ability-icon" title="' + aname + '" onerror="this.style.opacity=\'0.3\'">' +
            '</div>';
    }).join('');
    return '<div class="build-abilities">' + slots + '</div>';
}

// ── Переключение подконтента ──────────────────────────────────────────────

function _renderBuildSubContent() {
    var el = document.getElementById('build-subcontent');
    if (!el || !_buildData) return;
    var html = '';
    if      (_buildSubTab === 'facets')     html = _renderFacetsContent(_buildData);
    else if (_buildSubTab === 'talents')    html = _renderTalentsContent(_buildData);
    else if (_buildSubTab === 'items')      html = _renderItemsContent(_buildData);
    else if (_buildSubTab === 'skillbuild') html = _renderSkillbuildContent(_buildData);
    el.innerHTML = html;
}

// ── Основной рендер вкладки Сборка ───────────────────────────────────────

function renderBuildTab(data) {
    var el = document.getElementById('build-content');
    if (!el) return;

    // Set default position to most popular
    var topPositions = _getTopPositions(data);
    if (topPositions.length > 0) {
        var hasPos = false;
        for (var pi = 0; pi < topPositions.length; pi++) {
            if (topPositions[pi] === _buildPosition) { hasPos = true; break; }
        }
        if (!hasPos) _buildPosition = topPositions[0];
    }

    // ── Позиции: иконка сверху, название снизу ───────────────────────────
    var posButtons = topPositions.map(function (pos) {
        var activeCls = pos === _buildPosition ? ' active' : '';
        var imgSrc = _POSITION_IMG[pos] || '';
        return '<button class="build-pos-btn' + activeCls + '" data-pos="' + pos + '" onclick="selectBuildPosition(\'' + pos + '\')">' +
            '<img src="' + imgSrc + '" style="width:24px;height:24px;object-fit:contain;" onerror="this.style.display=\'none\'">' +
            '<span class="build-filter-name">' + (_POSITION_LABELS[pos] || pos) + '</span>' +
            '</button>';
    }).join('');

    // ── Ранг: иконки — иконка — название ─────────────────────────────────
    var rankDefs = [
        { rank: 'ALL',             label: 'Все ранги',    slugs: ['1-herald', '8-immortal'] },
        { rank: 'DIVINE_IMMORTAL', label: 'Высокий ранг', slugs: ['7-divine',  '8-immortal'] },
    ];
    var rankButtons = rankDefs.map(function (r) {
        var activeCls = r.rank === _buildRank ? ' active' : '';
        var rankImgs =
            '<div class="build-rank-icons">' +
                '<img src="https://www.dotabuff.com/assets/rank_tiers/' + r.slugs[0] + '.png" class="build-rank-icon" onerror="this.style.display=\'none\'">' +
                '<span class="build-rank-sep">—</span>' +
                '<img src="https://www.dotabuff.com/assets/rank_tiers/' + r.slugs[1] + '.png" class="build-rank-icon" onerror="this.style.display=\'none\'">' +
            '</div>';
        return '<button class="build-rank-btn' + activeCls + '" data-rank="' + r.rank + '" onclick="selectBuildRank(\'' + r.rank + '\')">' +
            rankImgs +
            '<span class="build-filter-name">' + r.label + '</span>' +
            '</button>';
    }).join('');

    // ── Подвкладки ────────────────────────────────────────────────────────
    var subTabDefs = [
        { tab: 'facets',     icon: '✨', label: 'Аспекты'   },
        { tab: 'talents',    icon: '🎯', label: 'Таланты'   },
        { tab: 'items',      icon: '🎒', label: 'Предметы'  },
        { tab: 'skillbuild', icon: '📈', label: 'Скиллбилд' },
    ];
    var subTabBtns = subTabDefs.map(function (t) {
        var activeCls = t.tab === _buildSubTab ? ' active' : '';
        return '<button class="build-subtab' + activeCls + '" data-tab="' + t.tab + '" onclick="selectBuildSubTab(\'' + t.tab + '\')">' +
            '<span class="build-filter-icon">' + t.icon + '</span>' +
            '<span class="build-filter-name">' + t.label + '</span>' +
            '</button>';
    }).join('');

    el.innerHTML =
        '<div class="build-filters">' +
            '<div class="build-filter-section">' +
                '<div class="build-filter-label">ПОПУЛЯРНЫЕ ПОЗИЦИИ</div>' +
                '<div class="build-filter-segmented">' + posButtons + '</div>' +
            '</div>' +
            '<div class="build-filter-divider"></div>' +
            '<div class="build-filter-section">' +
                '<div class="build-filter-label">РАНГ</div>' +
                '<div class="build-filter-segmented">' + rankButtons + '</div>' +
            '</div>' +
        '</div>' +
        '<div class="build-subtabs-wrap">' +
            '<div class="build-filter-label">ГАЙД</div>' +
            '<div class="build-filter-segmented">' + subTabBtns + '</div>' +
        '</div>' +
        '<div id="build-subcontent"></div>';

    _renderBuildSubContent();
}

async function loadHeroBuild(heroId) {
    _buildHeroId = heroId;
    _showBuildLoading();
    try {
        var response = await fetch(window.API_BASE_URL + '/hero/' + heroId + '/build');
        if (!response.ok) throw new Error('HTTP ' + response.status);
        var data = await response.json();
        if (_buildHeroId !== heroId) return;  // hero changed while loading
        _buildData = data;
        renderBuildTab(data);
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

function renderMatchupList(containerId, items, type, baseWr) {
    var container = document.getElementById(containerId);
    if (!container) return;

    if (!items || items.length === 0) {
        container.innerHTML = '<p class="matchup-placeholder-text">Недостаточно данных (мало игр)</p>';
        return;
    }

    // Обогащаем каждую запись дельтой относительно базового винрейта
    var enriched = [];
    for (var i = 0; i < items.length; i++) {
        var entry = items[i];
        var heroName = window.dotaHeroIdToName && window.dotaHeroIdToName[entry.hero_id];
        if (!heroName) {
            console.warn('[matchups] skip opponent: no name mapping for id =', entry.hero_id);
            continue;
        }
        var base = (baseWr != null) ? baseWr : 0.5;
        var delta = entry.wr_vs - base; // дробное значение, например 0.12
        enriched.push({ entry: entry, heroName: heroName, delta: delta });
    }

    if (enriched.length === 0) {
        container.innerHTML = '<p class="matchup-placeholder-text">Недостаточно данных (мало игр)</p>';
        return;
    }

    // Сортировка: «кого контрит» — по убыванию delta; «кто контрит» — по возрастанию
    if (type === 'strong') {
        enriched.sort(function (a, b) { return b.delta - a.delta; });
    } else {
        enriched.sort(function (a, b) { return a.delta - b.delta; });
    }

    // Масштаб прогресс-бара: по максимальному |delta| в списке (минимум 0.10)
    var maxAbsDelta = 0.10;
    for (var j = 0; j < enriched.length; j++) {
        if (Math.abs(enriched[j].delta) > maxAbsDelta) {
            maxAbsDelta = Math.abs(enriched[j].delta);
        }
    }

    var rendered = [];
    for (var k = 0; k < enriched.length; k++) {
        var item = enriched[k];
        var iconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(item.heroName) : '';
        var deltaPct = item.delta * 100;
        var absDeltaPct = Math.abs(deltaPct);
        var barWidth = Math.min(Math.round((absDeltaPct / (maxAbsDelta * 100)) * 100), 100);

        var sign = '';
        var cssClass = 'neutral';
        if (deltaPct > 2) {
            sign = '+';
            cssClass = 'positive';
        } else if (deltaPct < -2) {
            cssClass = 'negative';
        }

        var deltaStr = sign + Math.round(deltaPct) + '%';
        var gamesStr = item.entry.games + '\u00a0игр';

        rendered.push(
            '<div class="matchup-item ' + cssClass + '">' +
                '<div class="matchup-item-left">' +
                    '<img src="' + iconUrl + '" alt="" class="matchup-item-icon" onerror="this.style.display=\'none\'">' +
                    '<span class="matchup-item-name">' + item.heroName + '</span>' +
                '</div>' +
                '<div class="matchup-item-right">' +
                    '<div class="matchup-item-stat">' +
                        '<span class="matchup-item-delta">' + deltaStr + '</span>' +
                        '<span class="matchup-item-games">\u00b7\u00a0' + gamesStr + '</span>' +
                    '</div>' +
                    '<div class="matchup-item-bar-wrap">' +
                        '<div class="matchup-item-bar-fill" style="width:' + barWidth + '%"></div>' +
                    '</div>' +
                '</div>' +
            '</div>'
        );
    }

    container.innerHTML = rendered.join('');
}

async function loadHeroMatchups(heroId) {
    var LIMIT = 5;

    async function fetchCounters(minGames) {
        console.log('Loading counters from ' + window.API_BASE_URL + '/hero/' + heroId + '/counters?min_games=' + minGames);
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

        console.log('[matchups] API response victims.length =', data.victims && data.victims.length,
                    'counters.length =', data.counters && data.counters.length);
        console.log('[matchups] API sample victims[0] =', data.victims && data.victims[0]);
        console.log('[matchups] API sample counters[0] =', data.counters && data.counters[0]);

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
        var items = _activeCountersTab === 'strong' ? data.victims : data.counters;
        var type  = _activeCountersTab === 'strong' ? 'strong' : 'weak';
        renderMatchupList('counters-list', items, type, data.base_winrate);
    } catch (err) {
        console.error('[matchups] loadHeroMatchups error:', err);
        showMatchupsError();
    }
}

async function loadHeroSynergy(heroId) {
    var LIMIT = 5;

    async function fetchSynergy(minGames) {
        console.log('[synergy] fetching ' + window.API_BASE_URL + '/hero/' + heroId + '/synergy?min_games=' + minGames);
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

        console.log('[synergy] best_allies=', (data.best_allies || []).length,
                    'worst_allies=', (data.worst_allies || []).length);

        _synergyData = data;
        var items = _activeSynergyTab === 'best' ? data.best_allies : data.worst_allies;
        var type  = _activeSynergyTab === 'best' ? 'strong' : 'weak';
        renderMatchupList('synergy-list', items, type, data.base_winrate);
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

    window.addRecentHero = function (heroId) {
        if (!heroId) return;
        try {
            var list = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]');
            list = list.filter(function (id) { return id !== heroId; });
            list.unshift(heroId);
            if (list.length > MAX_RECENT) list = list.slice(0, MAX_RECENT);
            localStorage.setItem(RECENT_KEY, JSON.stringify(list));
        } catch (e) {}
    };

    window.renderRecentHeroes = function () {
        var block = document.getElementById('recent-heroes-block');
        var listEl = document.getElementById('recent-heroes-list');
        if (!block || !listEl) return;

        var list = [];
        try { list = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); } catch (e) {}

        if (!list.length) {
            block.style.display = 'none';
            return;
        }

        var idToName = getHeroIdToName();
        var items = list.map(function (id) {
            return idToName[id] ? { id: id, name: idToName[id] } : null;
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
    var navMap = { home: 0, quiz: 1, database: 2, profile: 3 };
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

