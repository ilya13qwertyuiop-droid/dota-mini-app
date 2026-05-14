
        const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

        let TELEGRAM_USER_ID = null;

        // Fallback: если Telegram WebApp недоступен (браузерный dev), всё равно
        // публикуем --tg-viewport-height для bottom sheet'ов; обновляем по resize.
        function _publishViewportFallback() {
            document.documentElement.style.setProperty('--tg-viewport-height', window.innerHeight + 'px');
        }
        _publishViewportFallback();
        window.addEventListener('resize', _publishViewportFallback);

        function initTelegramUser() {
            if (!tg) {
                console.warn('Telegram WebApp object not found');
                return;
            }

            tg.ready();
            tg.expand();

            // Хук на Telegram Viewport API — публикуем актуальную visible-высоту
            // в CSS-переменную --tg-viewport-height. Используется bottom sheet'ами
            // (режим Анализ драфтера), для которых vh ненадёжен в WebView.
            const _publishViewportHeight = () => {
                const h = tg.viewportHeight || window.innerHeight;
                document.documentElement.style.setProperty('--tg-viewport-height', h + 'px');
            };
            _publishViewportHeight();
            try { tg.onEvent('viewportChanged', _publishViewportHeight); } catch (e) {}

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
                    text: "Когда я вижу, что прогрессирую по золоту быстрее, чем вражеские герои",
                    icon: "ph-coins",
                    scores: { pos1: 3, pos2: 2, pos3: 1, pos4: 1, pos5: 1 }
                },
                {
                    id: "q1_pos2",
                    text: "Когда я один в правильный момент поймал и стёр врага за пару секунд",
                    icon: "ph-crosshair",
                    scores: { pos1: 2, pos2: 3, pos3: 1, pos4: 1, pos5: 1 }
                },
                {
                    id: "q1_pos3",
                    text: "Когда я первый прыгаю в драку и закрываю вражеских героев",
                    icon: "ph-sword",
                    scores: { pos1: 1, pos2: 2, pos3: 3, pos4: 2, pos5: 1 }
                },
                {
                    id: "q1_pos4", // pos4 и pos5 по 3, беру младший номер
                    text: "Когда моя помощь спасает союзников в критический момент",
                    icon: "ph-hand-heart",
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
                    text: "Сосредотачиваюсь на добивании крипов и стараюсь максимально эффективно фармить",
                    icon: "ph-coins",
                    scores: { pos1: 3, pos2: 2, pos3: 2, pos4: 0, pos5: 0 }
                },
                {
                    id: "q2_pos2",
                    text: "Хочу переиграть оппонента на линии и начать двигаться по карте",
                    icon: "ph-strategy",
                    scores: { pos1: 1, pos2: 3, pos3: 2, pos4: 1, pos5: 1 }
                },
                {
                    id: "q2_pos3",
                    text: "Ищу возможности для агрессии на линии и стараюсь доминировать",
                    icon: "ph-fire",
                    scores: { pos1: 1, pos2: 2, pos3: 3, pos4: 2, pos5: 2 }
                },
                {
                    id: "q2_pos5",
                    text: "Помогаю на линиях — даю тп при необходимости, контролирую руны/вижн",
                    icon: "ph-users-three",
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
                    text: "Оцениваю выгоду. Если не выгодно, продолжаю фармить или сплит-пушу",
                    icon: "ph-scales",
                    scores: { pos1: 3, pos2: 1, pos3: 1, pos4: 0, pos5: 0 }
                },
                {
                    id: "q3_pos4",
                    text: "Сразу даю ТП, чтобы помочь команде",
                    icon: "ph-lightning",
                    scores: { pos1: 1, pos2: 1, pos3: 1, pos4: 3, pos5: 3 }
                },
                {
                    id: "q3_pos3",
                    text: "Пытаюсь 'выключить' опасного вражеского героя",
                    icon: "ph-crosshair",
                    scores: { pos1: 1, pos2: 2, pos3: 3, pos4: 2, pos5: 1 }
                },
                {
                    id: "q3_pos1b", // pos1 и pos5 по 3, помечаю вторую керри‑метку
                    text: "Держу позицию, чтобы грамотно раскинуть кнопки",
                    icon: "ph-anchor",
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
                    text: "Героев, которые становятся сильными с дорогими предметами",
                    icon: "ph-crown",
                    scores: { pos1: 3, pos2: 2, pos3: 1, pos4: 1, pos5: 1 }
                },
                {
                    id: "q4_pos2",
                    text: "Героев с бёрст уроном — убил и ушёл",
                    icon: "ph-lightning",
                    scores: { pos1: 1, pos2: 3, pos3: 1, pos4: 1, pos5: 0 }
                },
                {
                    id: "q4_pos3",
                    text: "Героев, которые выдерживают много урона",
                    icon: "ph-shield",
                    scores: { pos1: 1, pos2: 1, pos3: 3, pos4: 2, pos5: 1 }
                },
                {
                    id: "q4_pos5",
                    text: "Героев с полезными способностями для команды (станы, сейвы, хил)",
                    icon: "ph-hand-heart",
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
                    text: "Золото/Фраги/Добито крипов",
                    icon: "ph-coins",
                    scores: { pos1: 3, pos2: 2, pos3: 2, pos4: 1, pos5: 1 }
                },
                {
                    id: "q5_pos2",
                    text: "Фраги и нанесённый урон",
                    icon: "ph-crosshair",
                    scores: { pos1: 3, pos2: 3, pos3: 1, pos4: 1, pos5: 1 }
                },
                {
                    id: "q5_pos3",
                    text: "Количество контроля и впитанного урона",
                    icon: "ph-shield",
                    scores: { pos1: 1, pos2: 1, pos3: 3, pos4: 2, pos5: 2 }
                },
                {
                    id: "q5_pos5",
                    text: "Количество расходников (варды, дасты), ассистов, лечения",
                    icon: "ph-hand-heart",
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

        let USER_TOKEN = getTokenFromUrl();

        // ── Silent token refresh через Telegram initData ─────────────────
        // Токены живут 24ч. Если пользователь давно не нажимал /start,
        // API-запросы падают с 401 — ловим их и бесшумно обновляем токен
        // через /api/refresh_token, проверяющий подпись initData.
        const _rawFetch = window.fetch.bind(window);
        let _refreshInFlight = null;

        function _getInitData() {
            const tg = window.Telegram && window.Telegram.WebApp;
            return (tg && tg.initData) ? tg.initData : null;
        }

        function _showAuthError(message) {
            if (document.getElementById('auth-error-banner')) return;
            const div = document.createElement('div');
            div.id = 'auth-error-banner';
            div.textContent = message;
            div.style.cssText = [
                'position:fixed','top:0','left:0','right:0',
                'padding:12px 16px','background:#e5534b','color:#fff',
                'font-size:13px','text-align:center','z-index:9999',
                'font-family:inherit','line-height:1.4'
            ].join(';');
            (document.body || document.documentElement).appendChild(div);
        }

        async function refreshToken() {
            if (_refreshInFlight) return _refreshInFlight;
            const initData = _getInitData();
            if (!initData) {
                _showAuthError('Вернитесь в чат с ботом и нажмите кнопку /start');
                return null;
            }
            const API = window.API_BASE_URL || '/api';
            _refreshInFlight = (async () => {
                try {
                    const resp = await _rawFetch(API + '/refresh_token', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ init_data: initData })
                    });
                    if (!resp.ok) {
                        console.warn('[auth] refresh_token HTTP', resp.status);
                        return null;
                    }
                    const data = await resp.json();
                    if (data && data.token) {
                        USER_TOKEN = data.token;
                        return data.token;
                    }
                    return null;
                } catch (e) {
                    console.warn('[auth] refresh_token error:', e);
                    return null;
                } finally {
                    _refreshInFlight = null;
                }
            })();
            return _refreshInFlight;
        }

        async function apiFetch(url, options) {
            const oldToken = USER_TOKEN;
            const resp = await _rawFetch(url, options);
            if (resp.status !== 401 && resp.status !== 403) return resp;

            const newToken = await refreshToken();
            if (!newToken) {
                if (_getInitData()) _showAuthError('Сессия истекла. Обновите страницу.');
                return resp;
            }
            if (newToken === oldToken) return resp;

            // Подменяем старый токен на новый в URL и теле запроса.
            // Токен — URL-safe base64 (secrets.token_urlsafe), поэтому
            // простая строковая замена безопасна от коллизий.
            let retryUrl = url;
            let retryOptions = options;
            if (oldToken && typeof retryUrl === 'string') {
                retryUrl = retryUrl.split(oldToken).join(newToken);
            }
            if (options && typeof options.body === 'string') {
                let newBody = options.body;
                if (oldToken) {
                    newBody = newBody.split(oldToken).join(newToken);
                } else {
                    // oldToken пустой — строковая замена бесполезна.
                    // Пересобираем JSON-тело, проставляя token явно.
                    try {
                        const parsed = JSON.parse(newBody);
                        if (parsed && typeof parsed === 'object') {
                            parsed.token = newToken;
                            newBody = JSON.stringify(parsed);
                        }
                    } catch (e) { /* не-JSON тело — оставляем как есть */ }
                }
                retryOptions = Object.assign({}, options, { body: newBody });
            }
            return _rawFetch(retryUrl, retryOptions);
        }

        // Сохранение результата на backend
        async function saveResultToBackend(result) {
            if (!USER_TOKEN) {
                console.warn('No token available, cannot save to backend');
                return;
            }

            try {
                const response = await apiFetch(`${window.API_BASE_URL}/save_result`, {
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
            // Скрыть undo-toast Анализа — он position:fixed и иначе виден на новой странице
            if (typeof _hideAnalysisUndoToast === 'function') _hideAnalysisUndoToast();

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
            if (pageName === 'teammates') {
                // initTeammatesPage определён в отдельном IIFE и экспортирован
                // как window._tmInitPage. Без этого вызова заход через
                // bottom-nav оставлял страницу без подгруженного профиля.
                if (typeof window._tmInitPage === 'function') window._tmInitPage();
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
            // переключаемся на вкладку «Квизы». Квизы больше не в bottom-nav
            // (слот заняли «Тиммейты»), поэтому никакой nav-item не подсвечиваем —
            // switchPage уже снял active со всех элементов.
            switchPage('quiz');
            startPositionQuiz();
        }

        function goToHeroQuiz() {
            switchPage('quiz');
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
            document.getElementById('positionQuestionCounter').textContent = `Вопрос ${currentQuestion + 1} из ${quizData.length}`;
            document.getElementById('question').textContent = questionData.question;


            const answersContainer = document.getElementById('answers');
            answersContainer.innerHTML = '';


            questionData.answers.forEach((answer, index) => {
                const button = document.createElement('button');
                button.className = 'answer-btn';
                const iconHtml = answer.icon ? `<i class="answer-icon ph ${answer.icon}" aria-hidden="true"></i>` : '';
                button.innerHTML = `${iconHtml}<span class="text">${answer.text}</span>`;
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
                document.getElementById('heroQuestionCounter').textContent = `Вопрос ${this.state.currentQuestionIndex + 1} из ${this.state.currentQuestionSet.length}`;
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
                    const button = document.createElement('button');
                    button.className = 'answer-btn';
                    const iconHtml = answer.icon ? `<i class="answer-icon ph ${answer.icon}" aria-hidden="true"></i>` : '';
                    button.innerHTML = `${iconHtml}<span class="text">${answer.text}</span>`;
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

                let maxPossibleScore = 0;
                Object.values(selectedTags).forEach(w => { maxPossibleScore += w; });
                if (selectedDifficulty) maxPossibleScore += 1.5;

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

                    return { ...hero, score, maxPossibleScore };
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

                topHeroes.forEach((hero, index) => {
                    const card = document.createElement('div');

                    const maxPossible = hero.maxPossibleScore || 1;
                    const matchPercent = Math.max(0, Math.min(100, Math.round((hero.score / maxPossible) * 100)));

                    card.className = 'hero-card';

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
                        const maxPossible = hero.maxPossibleScore || 1;
                        const matchPercent = Math.max(0, Math.min(100, Math.round((hero.score / maxPossible) * 100)));
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

function _profileSetLoadingState() {
    // Показываем skeleton, прячем result/empty, прячем error
    const show = id => {
        const el = document.getElementById(id);
        if (el) el.hidden = false;
    };
    const hide = id => {
        const el = document.getElementById(id);
        if (el) el.hidden = true;
    };
    show('profile-position-skeleton');
    show('profile-heroes-skeleton');
    hide('profile-position-result');
    hide('profile-position-empty');
    hide('profile-heroes-result');
    hide('profile-heroes-empty');
    hide('profile-error');
    const statsEl = document.getElementById('profile-stats');
    if (statsEl) statsEl.hidden = false;
}

function _profileHideSkeletons() {
    const pos = document.getElementById('profile-position-skeleton');
    const heroes = document.getElementById('profile-heroes-skeleton');
    if (pos) pos.hidden = true;
    if (heroes) heroes.hidden = true;
}

function _profileShowError() {
    _profileHideSkeletons();
    const error = document.getElementById('profile-error');
    const stats = document.getElementById('profile-stats');
    const posCard = document.getElementById('profile-position-card');
    const heroesCard = document.getElementById('profile-heroes-card');
    if (error) error.hidden = false;
    if (stats) stats.hidden = true;
    if (posCard) posCard.hidden = true;
    if (heroesCard) heroesCard.hidden = true;
}

function _profileHideError() {
    const error = document.getElementById('profile-error');
    const posCard = document.getElementById('profile-position-card');
    const heroesCard = document.getElementById('profile-heroes-card');
    if (error) error.hidden = true;
    if (posCard) posCard.hidden = false;
    if (heroesCard) heroesCard.hidden = false;
}

async function initProfile() {
    console.log('[PROFILE] Загрузка профиля...');

    _profileHideError();
    _profileSetLoadingState();
    updateProfileHeader(null, /*loading*/ true);

    if (!USER_TOKEN) {
        console.error('[PROFILE] Токен отсутствует');
        _profileHideSkeletons();
        updateProfileHeader(null);
        updateProfileStats(null);
        showEmptyProfile();
        return;
    }

    try {
        const response = await apiFetch(`${window.API_BASE_URL}/profile_full?token=${USER_TOKEN}`);
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
                    await apiFetch(`${window.API_BASE_URL}/save_telegram_data`, {
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

        _profileHideSkeletons();
        updateProfileHeader(profile);
        updateProfileStats(profile);
        displayPositionResult(profile);
        displayHeroesResult(profile);

    } catch (error) {
        console.error('[PROFILE] Ошибка загрузки:', error);
        updateProfileHeader(null);
        _profileShowError();
    }
}

function _renderAvatar(avatarEl, userData) {
    // Полный reset: убираем любые старые image / инициалы
    avatarEl.innerHTML = '';

    const photoUrl = userData && userData.photo_url;
    if (photoUrl) {
        const img = document.createElement('img');
        img.src = photoUrl;
        img.alt = '';
        img.decoding = 'async';
        img.loading = 'lazy';
        img.onerror = () => {
            // Сетевая ошибка — падаем на локальный инициал, без внешних сервисов
            avatarEl.innerHTML = '';
            avatarEl.textContent = _avatarInitial(userData);
        };
        avatarEl.appendChild(img);
        return;
    }

    avatarEl.textContent = _avatarInitial(userData);
}

function _avatarInitial(userData) {
    const source = (userData && (userData.first_name || userData.username)) || '';
    const ch = source.trim().charAt(0);
    return ch || '·';
}

function updateProfileHeader(profile, loading = false) {
    const avatar = document.getElementById('profile-avatar');
    const nameEl = document.getElementById('profile-name');
    const usernameEl = document.getElementById('profile-username');

    if (loading) {
        nameEl.textContent = 'Загрузка…';
        usernameEl.textContent = '';
        avatar.innerHTML = '';
        return;
    }

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
        usernameEl.textContent = userData.username ? `@${userData.username}` : '';
    } else {
        nameEl.textContent = 'Пользователь';
        usernameEl.textContent = '';
    }

    _renderAvatar(avatar, userData);
}

function _classifyDrafterRank(score) {
    // Та же шкала, что в рендере результата драфтера (script.js ≈ 4998).
    if (score >= 85) return { letter: 'SSS', desc: 'Идеальный драфт', color: 'var(--warning)' };
    if (score >= 70) return { letter: 'S',   desc: 'Отличный драфт',  color: 'var(--warning)' };
    if (score >= 55) return { letter: 'A',   desc: 'Хороший драфт',   color: 'var(--accent)' };
    if (score >= 45) return { letter: 'B',   desc: 'Средний драфт',   color: 'var(--text-primary)' };
    return             { letter: 'C',        desc: 'Слабый драфт',    color: 'var(--text-secondary)' };
}

function _renderDrafterBest() {
    const scoreEl = document.getElementById('profile-stat-best-score');
    const rankEl  = document.getElementById('profile-stat-best-rank');
    const descEl  = document.getElementById('profile-stat-best-desc');

    let best = 0;
    try {
        best = parseInt(localStorage.getItem('drafter_best_score') || '0', 10) || 0;
    } catch (e) { best = 0; }

    if (!best) {
        if (scoreEl) scoreEl.textContent = '—';
        if (rankEl) { rankEl.textContent = ''; rankEl.style.color = ''; }
        if (descEl) descEl.textContent = 'нет результата';
        return;
    }

    const rank = _classifyDrafterRank(best);
    if (scoreEl) scoreEl.textContent = String(best);
    if (rankEl) {
        rankEl.textContent = rank.letter;
        rankEl.style.color = rank.color;
    }
    if (descEl) descEl.textContent = rank.desc;
}

async function _renderDrafterPlace() {
    const placeEl = document.getElementById('profile-stat-place');
    const subEl   = document.getElementById('profile-stat-place-sub');

    if (!USER_TOKEN) {
        if (placeEl) placeEl.textContent = '—';
        if (subEl) subEl.textContent = 'нет результата';
        return;
    }

    try {
        const resp = await apiFetch(`${window.API_BASE_URL}/draft/leaderboard/me?token=${encodeURIComponent(USER_TOKEN)}`);
        if (!resp.ok) throw new Error(`API error: ${resp.status}`);
        const me = await resp.json();

        if (me && me.banned === true) {
            if (placeEl) placeEl.textContent = '—';
            if (subEl) subEl.textContent = 'Ваш аккаунт отстранён от участия в лидерборде за нарушение правил';
            return;
        }

        if (!me || me.rank === null || me.rank === undefined) {
            if (placeEl) placeEl.textContent = '—';
            if (subEl) subEl.textContent = 'нет результата';
            return;
        }

        if (placeEl) placeEl.textContent = `#${me.rank}`;
        if (subEl) {
            const sum = me.top5_sum != null ? Math.round(me.top5_sum) : null;
            subEl.textContent = sum != null ? `Счёт ${sum}` : '';
        }
    } catch (e) {
        console.warn('[PROFILE] leaderboard/me failed:', e);
        if (placeEl) placeEl.textContent = '—';
        if (subEl) subEl.textContent = 'нет данных';
    }
}

function updateProfileStats(_profile) {
    // Драфтер-метрики не зависят от quiz-профиля: лучший счёт — в localStorage,
    // место в лидерборде — отдельный запрос по токену.
    _renderDrafterBest();
    _renderDrafterPlace();
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
        posResult.hidden = true;
        posEmpty.hidden = false;
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

    posResult.hidden = false;
    posEmpty.hidden = true;

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
        heroesResult.hidden = false;
        heroesEmpty.hidden = true;
        renderProfileHeroes(heroesList, heroData.topHeroes);
        return;
    }

    // Иначе показываем заглушку
    heroesResult.hidden = true;
    heroesEmpty.hidden = false;
}

function renderProfileHeroes(container, heroes) {
    container.innerHTML = '';
    heroes.slice(0, 5).forEach((hero, index) => {
        const heroName = hero.name || hero;
        const matchPercent = hero.matchPercent || 75;
        const heroIconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(heroName) : '';

        const row = document.createElement('div');
        row.className = 'hero-row';
        row.setAttribute('role', 'button');
        row.tabIndex = 0;
        row.addEventListener('click', () => {
            goToMatchups();
            matchupPage.selectHero(heroName);
        });

        const rank = document.createElement('div');
        rank.className = 'hero-row-rank';
        rank.textContent = String(index + 1);

        const imgWrap = document.createElement('div');
        imgWrap.className = 'hero-row-img';
        if (heroIconUrl) {
            const img = document.createElement('img');
            img.src = heroIconUrl;
            img.alt = heroName;
            img.decoding = 'async';
            img.loading = 'lazy';
            img.onerror = () => { img.style.display = 'none'; };
            imgWrap.appendChild(img);
        }

        const text = document.createElement('div');
        text.className = 'hero-row-main-text';

        const name = document.createElement('div');
        name.className = 'hero-row-name';
        name.textContent = heroName;

        const sub = document.createElement('div');
        sub.className = 'hero-row-sub';
        sub.textContent = `${index === 0 ? 'Лучший мэтч' : 'Совпадение'} · ${matchPercent}%`;

        text.appendChild(name);
        text.appendChild(sub);

        row.appendChild(rank);
        row.appendChild(imgWrap);
        row.appendChild(text);

        container.appendChild(row);
    });
}

function showEmptyProfile() {
    document.getElementById('profile-position-result').hidden = true;
    document.getElementById('profile-position-empty').hidden = false;
    document.getElementById('profile-heroes-result').hidden = true;
    document.getElementById('profile-heroes-empty').hidden = false;
}

// ─── Обработчики кнопок профиля ──────────────────────────────────────
function _profileConfirmRedo(message, action) {
    // Telegram WebApp showConfirm асинхронный через callback; fallback на window.confirm
    const tgApp = window.Telegram && window.Telegram.WebApp;
    if (tgApp && typeof tgApp.showConfirm === 'function') {
        try {
            tgApp.showConfirm(message, (ok) => { if (ok) action(); });
            return;
        } catch (e) {
            console.warn('[PROFILE] showConfirm failed, fallback:', e);
        }
    }
    if (window.confirm(message)) action();
}

function _profileBindActions() {
    const retryBtn = document.getElementById('profile-retry-btn');
    if (retryBtn && !retryBtn.dataset.bound) {
        retryBtn.addEventListener('click', () => initProfile());
        retryBtn.dataset.bound = '1';
    }

    const posRedo = document.getElementById('profile-position-redo-btn');
    if (posRedo && !posRedo.dataset.bound) {
        posRedo.addEventListener('click', () => {
            _profileConfirmRedo(
                'Пройти квиз по позиции заново? Текущий результат будет перезаписан.',
                () => goToPositionQuiz()
            );
        });
        posRedo.dataset.bound = '1';
    }

    const posStart = document.getElementById('profile-position-start-btn');
    if (posStart && !posStart.dataset.bound) {
        posStart.addEventListener('click', () => goToPositionQuiz());
        posStart.dataset.bound = '1';
    }

    const heroesRedo = document.getElementById('profile-heroes-redo-btn');
    if (heroesRedo && !heroesRedo.dataset.bound) {
        heroesRedo.addEventListener('click', () => {
            _profileConfirmRedo(
                'Пройти квиз по героям заново? Текущий топ-5 будет перезаписан.',
                () => goToHeroQuiz()
            );
        });
        heroesRedo.dataset.bound = '1';
    }

    const heroesStart = document.getElementById('profile-heroes-start-btn');
    if (heroesStart && !heroesStart.dataset.bound) {
        heroesStart.addEventListener('click', () => goToHeroQuiz());
        heroesStart.dataset.bound = '1';
    }
}

document.addEventListener('DOMContentLoaded', _profileBindActions);

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
        if (typeof loadHeroesSearchMeta === 'function') loadHeroesSearchMeta();
        if (typeof initHeroesCatalog === 'function') initHeroesCatalog();
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
            const id = window.dotaHeroIds && window.dotaHeroIds[name];
            return id ? _analysisHeroMatchesQuery(id, query) : false;
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
        var response = await apiFetch(window.API_BASE_URL + '/hero/' + heroId + '/build');
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
        var response = await apiFetch(window.API_BASE_URL + '/hero/' + heroId + '/counters?limit=' + LIMIT + '&min_games=' + minGames);
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
        var response = await apiFetch(window.API_BASE_URL + '/hero/' + heroId + '/synergy?limit=' + LIMIT + '&min_games=' + minGames);
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

    // Восстанавливаем нав-элемент. Квизы больше не в bottom-nav — после
    // возврата с feedback с quiz-страницы ни один nav-item не подсвечивается
    // (страница доступна через виджет главной).
    var navMap = { home: 0, teammates: 1, drafter: 2, database: 3, profile: 4 };
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
    el.innerHTML = text;
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
        _setFeedbackStatus('Выбери оценку <i class="ph ph-hand-pointing" aria-hidden="true"></i>', 'hint');
        return;
    }

    var message = (ta ? ta.value : '').trim();
    if (!message) {
        _setFeedbackStatus('Напиши хотя бы пару слов в комментарии <i class="ph ph-hands-praying" aria-hidden="true"></i>', 'hint');
        return;
    }

    if (!USER_TOKEN) {
        _setFeedbackStatus('Не удалось отправить — токен не найден. Открой мини‑апп через бота.', 'err');
        return;
    }

    if (btn) { btn.disabled = true; btn.textContent = 'Отправка…'; }
    _clearFeedbackStatus();

    try {
        var resp = await apiFetch(`${window.API_BASE_URL}/feedback`, {
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
            _setFeedbackStatus('Спасибо за отзыв <i class="ph ph-heart" aria-hidden="true"></i>', 'ok');
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
    apiFetch(API + '/meta')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            _metaCache = data;
            _renderHomeMeta(data);
        })
        .catch(function(e) {
            console.warn('[meta] failed to load:', e);
        });
}

// ── Heroes-tab meta: "Сильные сейчас" ─────────────────────────────
function loadHeroesSearchMeta() {
    var rowsEl = document.getElementById('heroes-meta-rows');
    var patchEl = document.getElementById('heroes-meta-patch');
    if (!rowsEl) return;

    function render(data) {
        var patch = _resolveMetaPatch(data);
        if (patchEl) patchEl.textContent = 'патч ' + (patch || '—');

        var positions = (data && data.positions) || {};
        var posOrder = ['POSITION_1', 'POSITION_2', 'POSITION_3', 'POSITION_4', 'POSITION_5'];
        var blocks = [];
        posOrder.forEach(function (posKey) {
            var heroes = (positions[posKey] || []).slice(0, 2);
            if (!heroes.length) return;
            var posLabel = _META_POS_LABELS[posKey] || '';
            var heroesHtml = heroes.map(function (h) {
                var heroName = (window.dotaHeroIdToName && window.dotaHeroIdToName[h.hero_id]) || ('Hero #' + h.hero_id);
                var iconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(heroName) : '';
                var wrPct = Math.round((h.win_rate || 0) * 100);
                return (
                    '<button type="button" class="heroes-meta-hero" data-hero-name="' + _escHtml(heroName) + '">' +
                        '<img class="heroes-meta-hero-icon" src="' + _escHtml(iconUrl) + '" alt="" onerror="this.style.display=\'none\'">' +
                        '<span class="heroes-meta-hero-name">' + _escHtml(heroName) + '</span>' +
                        '<span class="heroes-meta-hero-wr">' + wrPct + '%</span>' +
                    '</button>'
                );
            }).join('');
            blocks.push(
                '<div class="heroes-meta-pos">' +
                    '<div class="heroes-meta-pos-label">' + _escHtml(posLabel) + '</div>' +
                    '<div class="heroes-meta-pos-heroes">' + heroesHtml + '</div>' +
                '</div>'
            );
        });

        if (!blocks.length) {
            rowsEl.innerHTML = '<div class="heroes-meta-skeleton" aria-hidden="true"></div>';
            return;
        }

        rowsEl.innerHTML = blocks.join('');

        rowsEl.querySelectorAll('.heroes-meta-hero').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var name = btn.getAttribute('data-hero-name');
                if (name && matchupPage && typeof matchupPage.selectHero === 'function') {
                    matchupPage.selectHero(name);
                }
            });
        });
    }

    if (_metaCache) {
        render(_metaCache);
        return;
    }
    var API = window.API_BASE_URL || '/api';
    apiFetch(API + '/meta')
        .then(function (r) { return r.json(); })
        .then(function (data) {
            _metaCache = data;
            render(data);
        })
        .catch(function (e) { console.warn('[heroes-meta] failed:', e); });
}

// ── Полноэкранный каталог героев по атрибутам ────────────────────────
// Статический снапшот OpenDota /api/heroes (зафиксировано 2026-04-18).
// Никаких сетевых запросов — каталог открывается мгновенно.
var _HEROES_CATALOG_DATA = [
    { id: 1,   primary_attr: 'agi', localized_name: 'Anti-Mage' },
    { id: 2,   primary_attr: 'str', localized_name: 'Axe' },
    { id: 3,   primary_attr: 'all', localized_name: 'Bane' },
    { id: 4,   primary_attr: 'agi', localized_name: 'Bloodseeker' },
    { id: 5,   primary_attr: 'int', localized_name: 'Crystal Maiden' },
    { id: 6,   primary_attr: 'agi', localized_name: 'Drow Ranger' },
    { id: 7,   primary_attr: 'str', localized_name: 'Earthshaker' },
    { id: 8,   primary_attr: 'agi', localized_name: 'Juggernaut' },
    { id: 9,   primary_attr: 'agi', localized_name: 'Mirana' },
    { id: 10,  primary_attr: 'agi', localized_name: 'Morphling' },
    { id: 11,  primary_attr: 'agi', localized_name: 'Shadow Fiend' },
    { id: 12,  primary_attr: 'agi', localized_name: 'Phantom Lancer' },
    { id: 13,  primary_attr: 'int', localized_name: 'Puck' },
    { id: 14,  primary_attr: 'str', localized_name: 'Pudge' },
    { id: 15,  primary_attr: 'agi', localized_name: 'Razor' },
    { id: 16,  primary_attr: 'all', localized_name: 'Sand King' },
    { id: 17,  primary_attr: 'int', localized_name: 'Storm Spirit' },
    { id: 18,  primary_attr: 'str', localized_name: 'Sven' },
    { id: 19,  primary_attr: 'str', localized_name: 'Tiny' },
    { id: 20,  primary_attr: 'agi', localized_name: 'Vengeful Spirit' },
    { id: 21,  primary_attr: 'all', localized_name: 'Windranger' },
    { id: 22,  primary_attr: 'int', localized_name: 'Zeus' },
    { id: 23,  primary_attr: 'str', localized_name: 'Kunkka' },
    { id: 25,  primary_attr: 'int', localized_name: 'Lina' },
    { id: 26,  primary_attr: 'int', localized_name: 'Lion' },
    { id: 27,  primary_attr: 'int', localized_name: 'Shadow Shaman' },
    { id: 28,  primary_attr: 'str', localized_name: 'Slardar' },
    { id: 29,  primary_attr: 'str', localized_name: 'Tidehunter' },
    { id: 30,  primary_attr: 'int', localized_name: 'Witch Doctor' },
    { id: 31,  primary_attr: 'int', localized_name: 'Lich' },
    { id: 32,  primary_attr: 'agi', localized_name: 'Riki' },
    { id: 33,  primary_attr: 'all', localized_name: 'Enigma' },
    { id: 34,  primary_attr: 'int', localized_name: 'Tinker' },
    { id: 35,  primary_attr: 'agi', localized_name: 'Sniper' },
    { id: 36,  primary_attr: 'int', localized_name: 'Necrophos' },
    { id: 37,  primary_attr: 'int', localized_name: 'Warlock' },
    { id: 38,  primary_attr: 'all', localized_name: 'Beastmaster' },
    { id: 39,  primary_attr: 'int', localized_name: 'Queen of Pain' },
    { id: 40,  primary_attr: 'all', localized_name: 'Venomancer' },
    { id: 41,  primary_attr: 'agi', localized_name: 'Faceless Void' },
    { id: 42,  primary_attr: 'str', localized_name: 'Wraith King' },
    { id: 43,  primary_attr: 'all', localized_name: 'Death Prophet' },
    { id: 44,  primary_attr: 'agi', localized_name: 'Phantom Assassin' },
    { id: 45,  primary_attr: 'int', localized_name: 'Pugna' },
    { id: 46,  primary_attr: 'agi', localized_name: 'Templar Assassin' },
    { id: 47,  primary_attr: 'agi', localized_name: 'Viper' },
    { id: 48,  primary_attr: 'agi', localized_name: 'Luna' },
    { id: 49,  primary_attr: 'str', localized_name: 'Dragon Knight' },
    { id: 50,  primary_attr: 'all', localized_name: 'Dazzle' },
    { id: 51,  primary_attr: 'str', localized_name: 'Clockwerk' },
    { id: 52,  primary_attr: 'int', localized_name: 'Leshrac' },
    { id: 53,  primary_attr: 'all', localized_name: "Nature's Prophet" },
    { id: 54,  primary_attr: 'str', localized_name: 'Lifestealer' },
    { id: 55,  primary_attr: 'int', localized_name: 'Dark Seer' },
    { id: 56,  primary_attr: 'agi', localized_name: 'Clinkz' },
    { id: 57,  primary_attr: 'str', localized_name: 'Omniknight' },
    { id: 58,  primary_attr: 'int', localized_name: 'Enchantress' },
    { id: 59,  primary_attr: 'str', localized_name: 'Huskar' },
    { id: 60,  primary_attr: 'str', localized_name: 'Night Stalker' },
    { id: 61,  primary_attr: 'agi', localized_name: 'Broodmother' },
    { id: 62,  primary_attr: 'agi', localized_name: 'Bounty Hunter' },
    { id: 63,  primary_attr: 'agi', localized_name: 'Weaver' },
    { id: 64,  primary_attr: 'int', localized_name: 'Jakiro' },
    { id: 65,  primary_attr: 'all', localized_name: 'Batrider' },
    { id: 66,  primary_attr: 'int', localized_name: 'Chen' },
    { id: 67,  primary_attr: 'agi', localized_name: 'Spectre' },
    { id: 68,  primary_attr: 'int', localized_name: 'Ancient Apparition' },
    { id: 69,  primary_attr: 'str', localized_name: 'Doom' },
    { id: 70,  primary_attr: 'agi', localized_name: 'Ursa' },
    { id: 71,  primary_attr: 'str', localized_name: 'Spirit Breaker' },
    { id: 72,  primary_attr: 'agi', localized_name: 'Gyrocopter' },
    { id: 73,  primary_attr: 'str', localized_name: 'Alchemist' },
    { id: 74,  primary_attr: 'int', localized_name: 'Invoker' },
    { id: 75,  primary_attr: 'int', localized_name: 'Silencer' },
    { id: 76,  primary_attr: 'int', localized_name: 'Outworld Destroyer' },
    { id: 77,  primary_attr: 'str', localized_name: 'Lycan' },
    { id: 78,  primary_attr: 'all', localized_name: 'Brewmaster' },
    { id: 79,  primary_attr: 'int', localized_name: 'Shadow Demon' },
    { id: 80,  primary_attr: 'agi', localized_name: 'Lone Druid' },
    { id: 81,  primary_attr: 'str', localized_name: 'Chaos Knight' },
    { id: 82,  primary_attr: 'agi', localized_name: 'Meepo' },
    { id: 83,  primary_attr: 'str', localized_name: 'Treant Protector' },
    { id: 84,  primary_attr: 'str', localized_name: 'Ogre Magi' },
    { id: 85,  primary_attr: 'str', localized_name: 'Undying' },
    { id: 86,  primary_attr: 'int', localized_name: 'Rubick' },
    { id: 87,  primary_attr: 'int', localized_name: 'Disruptor' },
    { id: 88,  primary_attr: 'all', localized_name: 'Nyx Assassin' },
    { id: 89,  primary_attr: 'agi', localized_name: 'Naga Siren' },
    { id: 90,  primary_attr: 'int', localized_name: 'Keeper of the Light' },
    { id: 91,  primary_attr: 'all', localized_name: 'Io' },
    { id: 92,  primary_attr: 'all', localized_name: 'Visage' },
    { id: 93,  primary_attr: 'agi', localized_name: 'Slark' },
    { id: 94,  primary_attr: 'agi', localized_name: 'Medusa' },
    { id: 95,  primary_attr: 'agi', localized_name: 'Troll Warlord' },
    { id: 96,  primary_attr: 'str', localized_name: 'Centaur Warrunner' },
    { id: 97,  primary_attr: 'all', localized_name: 'Magnus' },
    { id: 98,  primary_attr: 'str', localized_name: 'Timbersaw' },
    { id: 99,  primary_attr: 'str', localized_name: 'Bristleback' },
    { id: 100, primary_attr: 'str', localized_name: 'Tusk' },
    { id: 101, primary_attr: 'int', localized_name: 'Skywrath Mage' },
    { id: 102, primary_attr: 'all', localized_name: 'Abaddon' },
    { id: 103, primary_attr: 'str', localized_name: 'Elder Titan' },
    { id: 104, primary_attr: 'str', localized_name: 'Legion Commander' },
    { id: 105, primary_attr: 'all', localized_name: 'Techies' },
    { id: 106, primary_attr: 'agi', localized_name: 'Ember Spirit' },
    { id: 107, primary_attr: 'str', localized_name: 'Earth Spirit' },
    { id: 108, primary_attr: 'str', localized_name: 'Underlord' },
    { id: 109, primary_attr: 'agi', localized_name: 'Terrorblade' },
    { id: 110, primary_attr: 'str', localized_name: 'Phoenix' },
    { id: 111, primary_attr: 'int', localized_name: 'Oracle' },
    { id: 112, primary_attr: 'int', localized_name: 'Winter Wyvern' },
    { id: 113, primary_attr: 'all', localized_name: 'Arc Warden' },
    { id: 114, primary_attr: 'agi', localized_name: 'Monkey King' },
    { id: 119, primary_attr: 'int', localized_name: 'Dark Willow' },
    { id: 120, primary_attr: 'all', localized_name: 'Pangolier' },
    { id: 121, primary_attr: 'int', localized_name: 'Grimstroke' },
    { id: 123, primary_attr: 'agi', localized_name: 'Hoodwink' },
    { id: 126, primary_attr: 'all', localized_name: 'Void Spirit' },
    { id: 128, primary_attr: 'all', localized_name: 'Snapfire' },
    { id: 129, primary_attr: 'str', localized_name: 'Mars' },
    { id: 131, primary_attr: 'int', localized_name: 'Ringmaster' },
    { id: 135, primary_attr: 'str', localized_name: 'Dawnbreaker' },
    { id: 136, primary_attr: 'all', localized_name: 'Marci' },
    { id: 137, primary_attr: 'str', localized_name: 'Primal Beast' },
    { id: 138, primary_attr: 'int', localized_name: 'Muerta' },
    { id: 145, primary_attr: 'agi', localized_name: 'Kez' },
    { id: 155, primary_attr: 'str', localized_name: 'Largo' },
];

var _heroesCatalogBound = false;
var _heroesCatalogRendered = false;
var _catalogLastFocus = null;
var _catalogContext = 'matchup';

var _CATALOG_ATTR_ORDER = ['str', 'agi', 'int', 'all'];
var _CATALOG_ATTR_LABELS = {
    'str': 'Сила',
    'agi': 'Ловкость',
    'int': 'Интеллект',
    'all': 'Универсал',
};
var _CATALOG_ATTR_ICONS = {
    'str': 'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/icons/hero_strength.png',
    'agi': 'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/icons/hero_agility.png',
    'int': 'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/icons/hero_intelligence.png',
    'all': 'https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/icons/hero_universal.png',
};

function initHeroesCatalog() {
    var input = document.getElementById('matchup-hero-input');
    if (input && window.dotaHeroImages) {
        var count = Object.keys(window.dotaHeroImages).length;
        input.setAttribute('placeholder', 'Найти среди ' + count + ' героев');
    }

    if (_heroesCatalogBound) return;
    _heroesCatalogBound = true;

    var openBtn = document.getElementById('matchup-search-catalog-btn');
    var drafterOpenBtn = document.getElementById('drafter-search-catalog-btn');
    var closeBtn = document.getElementById('heroes-catalog-close');
    var overlay = document.getElementById('heroes-catalog-overlay');

    function _bindCatalogOpener(btn, inputId, contextName) {
        if (!btn) return;
        var lastOpenAt = 0;
        var handler = function (e) {
            var now = Date.now();
            if (now - lastOpenAt < 500) return;
            lastOpenAt = now;
            if (e && typeof e.preventDefault === 'function') e.preventDefault();
            if (e && typeof e.stopPropagation === 'function') e.stopPropagation();
            var inputEl = inputId ? document.getElementById(inputId) : null;
            if (inputEl && typeof inputEl.blur === 'function') inputEl.blur();
            _catalogContext = contextName;
            openHeroesCatalog();
        };
        btn.addEventListener('touchend', handler);
        btn.addEventListener('click', handler);
    }

    // iOS-обход: когда инпут сфокусирован и клавиатура поднята,
    // первый touchend уходит на dismiss keyboard и click не фирится.
    // Ловим touchend напрямую и блёрим инпут заранее.
    _bindCatalogOpener(openBtn, 'matchup-hero-input', 'matchup');
    _bindCatalogOpener(drafterOpenBtn, 'drafter-search', 'drafter');
    if (closeBtn) {
        closeBtn.addEventListener('click', function (e) {
            e.preventDefault();
            closeHeroesCatalog();
        });
    }
    if (overlay) {
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) closeHeroesCatalog();
        });
    }
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' || e.key === 'Esc') {
            var ov = document.getElementById('heroes-catalog-overlay');
            if (ov && !ov.hasAttribute('hidden')) closeHeroesCatalog();
        }
    });
}

function openHeroesCatalog() {
    var overlay = document.getElementById('heroes-catalog-overlay');
    var panel = document.getElementById('heroes-catalog-panel');
    if (!overlay) return;
    if (!_heroesCatalogRendered) {
        renderHeroesCatalog();
        _heroesCatalogRendered = true;
    }
    _catalogLastFocus = document.activeElement;

    overlay.hidden = false;
    overlay.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    if (panel) {
        panel.classList.remove('is-closing');
        panel.style.transform = '';
        panel.style.transition = '';
        // force reflow so transition runs from translateY(100%) → 0
        void panel.offsetWidth;
        requestAnimationFrame(function () {
            panel.classList.add('is-open');
        });
    }
}

function closeHeroesCatalog() {
    var overlay = document.getElementById('heroes-catalog-overlay');
    var panel = document.getElementById('heroes-catalog-panel');
    if (!overlay) return;

    function finalize() {
        overlay.hidden = true;
        overlay.setAttribute('aria-hidden', 'true');
        if (panel) {
            panel.classList.remove('is-open', 'is-closing');
            panel.style.transform = '';
            panel.style.transition = '';
        }
        document.body.style.overflow = '';
        if (_catalogLastFocus && typeof _catalogLastFocus.focus === 'function') {
            try { _catalogLastFocus.focus(); } catch (e) {}
        }
        _catalogLastFocus = null;
    }

    if (panel) {
        panel.style.transform = '';
        panel.classList.remove('is-open');
        panel.classList.add('is-closing');
        var done = false;
        var onEnd = function () {
            if (done) return;
            done = true;
            panel.removeEventListener('transitionend', onEnd);
            finalize();
        };
        panel.addEventListener('transitionend', onEnd);
        setTimeout(onEnd, 320);
    } else {
        finalize();
    }
}

function renderHeroesCatalog() {
    var bodyEl = document.getElementById('heroes-catalog-body');
    var countEl = document.getElementById('heroes-catalog-count');
    if (!bodyEl) return;

    var groups = { str: [], agi: [], int: [], all: [] };
    var total = 0;

    _HEROES_CATALOG_DATA.forEach(function (h) {
        var heroName = (window.dotaHeroIdToName && window.dotaHeroIdToName[h.id]) || h.localized_name;
        if (!heroName) return;
        if (!window.dotaHeroImages || !window.dotaHeroImages[heroName]) return;
        var attr = h.primary_attr;
        if (!groups[attr]) return;
        groups[attr].push(heroName);
        total += 1;
    });

    if (countEl) countEl.textContent = total ? total + ' героев' : '—';

    var sectionsHtml = _CATALOG_ATTR_ORDER.map(function (attr) {
        var names = groups[attr] || [];
        if (!names.length) return '';
        names.sort(function (a, b) { return a.localeCompare(b, 'ru'); });
        var label = _CATALOG_ATTR_LABELS[attr] || attr;
        var tilesHtml = names.map(function (name) {
            var iconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(name) : '';
            return (
                '<button type="button" class="heroes-catalog-tile" data-hero-name="' + _escHtml(name) + '">' +
                    '<span class="heroes-catalog-tile-icon">' +
                        '<img src="' + _escHtml(iconUrl) + '" alt="" loading="lazy" onerror="this.style.display=\'none\'">' +
                    '</span>' +
                    '<span class="heroes-catalog-tile-name">' + _escHtml(name) + '</span>' +
                '</button>'
            );
        }).join('');
        var iconUrl = _CATALOG_ATTR_ICONS[attr] || '';
        var iconHtml = iconUrl
            ? '<img class="heroes-catalog-section-icon" src="' + _escHtml(iconUrl) + '" alt="" aria-hidden="true" onerror="this.style.display=\'none\'">'
            : '';
        return (
            '<section class="heroes-catalog-section">' +
                '<header class="heroes-catalog-section-header">' +
                    '<div class="heroes-catalog-section-title">' + iconHtml + '<span>' + _escHtml(label) + '</span></div>' +
                    '<div class="heroes-catalog-section-count">' + names.length + '</div>' +
                '</header>' +
                '<div class="heroes-catalog-grid">' + tilesHtml + '</div>' +
            '</section>'
        );
    }).join('');

    if (!sectionsHtml) {
        bodyEl.innerHTML = '<div class="heroes-catalog-empty">Каталог пуст</div>';
        return;
    }

    bodyEl.innerHTML = sectionsHtml;

    bodyEl.querySelectorAll('.heroes-catalog-tile').forEach(function (tile) {
        tile.addEventListener('click', function () {
            var name = tile.getAttribute('data-hero-name');
            if (!name) return;
            if (_catalogContext === 'drafter') {
                var hid = window.dotaHeroIds && window.dotaHeroIds[name];
                if (!hid) { closeHeroesCatalog(); return; }
                // Та же проверка, что в обычном гриде драфтера: герой,
                // уже занятый вражеской командой, не может быть выбран.
                var isEnemy = _drafterEnemyPick.some(function (e) {
                    return e && e.hero_id === hid;
                });
                if (isEnemy) {
                    showToast('Этот герой уже у врагов');
                    return;
                }
                closeHeroesCatalog();
                if (typeof selectDrafterHero === 'function') {
                    selectDrafterHero(hid);
                }
                return;
            }
            closeHeroesCatalog();
            if (matchupPage && typeof matchupPage.selectHero === 'function') {
                matchupPage.selectHero(name);
            }
        });
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

    var cta = widget.querySelector('.home-widget-cta');
    var heroId = _getLastHeroId();
    if (!heroId) {
        widget.disabled = false;
        widget.dataset.heroId = '';
        body.innerHTML = '<div class="home-hero-placeholder">Открой любого героя во вкладке Герои</div>';
        if (cta) cta.innerHTML = 'Перейти к героям <i class="ph ph-arrow-right" aria-hidden="true"></i>';
        return;
    }

    widget.disabled = false;
    widget.dataset.heroId = heroId;
    if (cta) cta.innerHTML = 'Открыть гайд <i class="ph ph-arrow-right" aria-hidden="true"></i>';
    var API = window.API_BASE_URL || '/api';
    apiFetch(API + '/hero/' + heroId + '/build')
        .then(function(r) { return r.ok ? r.json() : null; })
        .then(function(data) {
            if (!data) {
                body.innerHTML = '<div class="home-hero-placeholder">Данные недоступны</div>';
                return;
            }
            _HOME_HERO_LAST = { heroId: heroId, build: data };
            // items_db нужен для иконок предметов в виджете — ждём его перед рендером,
            // чтобы не показывать пустые слоты с последующим re-render.
            var ready = _itemsDbLoaded ? Promise.resolve() : _loadItemsDb();
            return ready.then(function() { _renderHomeHeroWidget(heroId, data); });
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
        '<div class="home-hero-items">' + itemSlots.join('') + '</div>';
}

function homeHeroWidgetClick() {
    var widget = document.getElementById('home-hero-widget');
    if (!widget || widget.disabled) return;
    var heroId = parseInt(widget.dataset.heroId || '0', 10);
    if (!heroId) { switchPage('database'); return; }
    var name = window.dotaHeroIdToName && window.dotaHeroIdToName[heroId];
    if (name) _metaHeroClick(name);
}

// ── Виджет: последний драфт ──────────────────────────────────────────
var _HOME_DRAFT_CACHE_KEY = 'home_last_draft_eval';

function cacheLastDraftEval(data, allyIds, enemyIds) {
    try {
        localStorage.setItem(_HOME_DRAFT_CACHE_KEY, JSON.stringify({
            total_score: data.total_score,
            synergy_score: data.synergy_score,
            matchup_score: data.matchup_score,
            ally_heroes: Array.isArray(allyIds) ? allyIds : [],
            enemy_heroes: Array.isArray(enemyIds) ? enemyIds : [],
            saved_at: Date.now(),
        }));
    } catch (e) {}
}

function _scoreRank(score) {
    if (score >= 85) return 'SSS';
    if (score >= 70) return 'S';
    if (score >= 55) return 'A';
    if (score >= 45) return 'B';
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
    apiFetch(API + '/draft/history?token=' + encodeURIComponent(token))
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
    body.innerHTML = '<div class="home-draft-placeholder">Сделай свой первый драфт</div>';
    if (cta) cta.innerHTML = 'Перейти к драфтеру <i class="ph ph-arrow-right" aria-hidden="true"></i>';
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
    var syn = null, mu = null;
    if (cached && Math.abs((cached.total_score || 0) - total) < 0.5) {
        syn = cached.synergy_score || 0;
        mu = cached.matchup_score || 0;
    }

    var totalRounded = Math.round(total);
    // Каждая из 2 компонент — 0..50
    var synPct = syn != null ? Math.min(100, Math.round((syn / 50) * 100)) : null;
    var muPct  = mu  != null ? Math.min(100, Math.round((mu  / 50) * 100)) : null;

    var allyIds = (cached && Array.isArray(cached.ally_heroes)) ? cached.ally_heroes.slice(0, 5) : [];
    var enemyIds = (cached && Array.isArray(cached.enemy_heroes)) ? cached.enemy_heroes.slice(0, 5) : [];
    var heroesHtml = '';
    if (allyIds.length || enemyIds.length) {
        heroesHtml = '<div class="home-draft-heroes">' +
            _draftTeamRow(allyIds) +
            _draftTeamRow(enemyIds) +
        '</div>';
    }

    body.innerHTML =
        '<div class="home-draft-top">' +
            '<div class="home-draft-score">' + totalRounded + '<span class="home-draft-score-max">/100</span></div>' +
            '<div class="home-draft-rank" data-rank="' + _escHtml(rank) + '">' + _escHtml(rank) + '</div>' +
        '</div>' +
        heroesHtml +
        '<div class="home-draft-bars">' +
            _draftBarRow('Синергия', 'positive', synPct) +
            _draftBarRow('Матчапы', 'warning', muPct) +
        '</div>';

    if (cta) cta.innerHTML = 'Новый драфт <i class="ph ph-arrow-right" aria-hidden="true"></i>';
}

function _draftTeamRow(heroIds) {
    var cells = [];
    for (var i = 0; i < 5; i++) {
        var id = heroIds[i];
        var url = id ? _drafterHeroIcon(id) : '';
        cells.push('<div class="home-draft-hero">' + (url ? '<img src="' + _escHtml(url) + '" alt="" onerror="this.style.display=\'none\'">' : '') + '</div>');
    }
    return '<div class="home-draft-team">' + cells.join('') + '</div>';
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
    apiFetch(API + '/news')
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
        var resp = await apiFetch(window.API_BASE_URL + '/items_db');
        if (resp.ok) {
            _itemsDb = await resp.json();
            _itemsDbLoaded = true;
            if (_HOME_HERO_LAST) _renderHomeHeroWidget(_HOME_HERO_LAST.heroId, _HOME_HERO_LAST.build);
        }
    } catch (e) {
        console.warn('Failed to load items_db:', e);
    }
}

// Загружаем мету при старте (главная открыта по умолчанию).
// items_db грузим лениво — при открытии героя (loadHeroBuild) или драфтера (initDrafter).
(function() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() { initHomeScreen(); });
    } else {
        initHomeScreen();
    }
}());

// ========== ДРАФТЕР ==========

const HERO_PRIMARY_POSITIONS = {
  1:1, 2:3, 3:5, 4:1, 5:5, 6:1, 7:4, 8:1, 9:4, 10:1, 11:1, 12:1, 13:2, 14:4, 15:3, 16:3, 17:2, 18:1, 19:4, 20:5, 21:4, 22:4, 23:3, 25:2, 26:5, 27:5, 28:3, 29:3, 30:5, 31:5, 32:1, 33:3, 34:2, 35:2, 36:2, 37:5, 38:3, 39:2, 40:5, 41:1, 42:1, 43:3, 44:1, 45:5, 46:1, 47:2, 48:1, 49:1, 50:5, 51:4, 52:2, 53:4, 54:1, 55:3, 56:1, 57:3, 58:5, 59:2, 60:3, 61:2, 62:4, 63:1, 64:5, 65:3, 66:5, 67:1, 68:5, 69:3, 70:1, 71:4, 72:1, 73:1, 74:2, 75:5, 76:2, 77:3, 78:3, 79:5, 80:2, 81:3, 82:2, 83:5, 84:5, 85:5, 86:4, 87:5, 88:4, 89:1, 90:2, 91:5, 92:3, 93:1, 94:1, 95:1, 96:3, 97:3, 98:3, 99:3, 100:4, 101:4, 102:5, 103:5, 104:3, 105:4, 106:2, 107:4, 108:3, 109:1, 110:4, 111:5, 112:5, 113:2, 114:1, 119:4, 120:2, 121:5, 123:4, 126:2, 128:4, 129:3, 131:5, 135:3, 136:5, 137:3, 138:1, 145:1, 155:3
};

var HERO_PRIMARY_ATTRS = (function() {
    var m = {};
    if (typeof _HEROES_CATALOG_DATA !== 'undefined' && _HEROES_CATALOG_DATA) {
        _HEROES_CATALOG_DATA.forEach(function(h) { m[h.id] = h.primary_attr; });
    }
    return m;
})();

var _drafterEnemyPick = [];          // [{hero_id, position}]
var _drafterAllyPick = [null, null, null, null, null]; // null = пусто
var _drafterActiveSlot = 0;
var _drafterMatchLoaded = false;
var _drafterPosFilter = 1;           // 1..5 — основная позиция героя
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
    // Показать экран драфта, скрыть результат
    document.getElementById('drafter-main').style.display = 'block';
    document.getElementById('drafter-result').style.display = 'none';

    // items_db нужен для предметов в результатах оценки драфта
    if (!_itemsDbLoaded) _loadItemsDb();

    // Bind catalog button (idempotent — guarded by _heroesCatalogBound)
    if (typeof initHeroesCatalog === 'function') initHeroesCatalog();

    // Prefetch лидерборда в фоне
    if (!_drafterLeaderboardCache) {
        apiFetch(window.API_BASE_URL + '/draft/leaderboard')
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

    // Восстановить ранее выбранный режим (по умолчанию — Анализ).
    // Ключ bumped до v2, чтобы старые сохранённые 'training' не перебивали
    // новый дефолт у уже существующих пользователей.
    var savedMode = null;
    try { savedMode = localStorage.getItem('drafter_mode_v2'); } catch (e) {}
    setDrafterMode(savedMode === 'training' ? 'training' : 'analysis');
}

/* ════════════════════════════════════════════════════════════════
   Drafter — режим «Анализ»
   ──────────────────────────────────────────────────────────────── */

var _drafterMode = 'analysis';
var _analysisLight = [null, null, null, null, null];
var _analysisDark  = [null, null, null, null, null];
var _analysisBans  = new Set();    // global bans — hero IDs исключены из picker'а
var _analysisActiveSide = 'light';
var _analysisActiveSlot = -1;
var _analysisSheetMode = null; // null | 'picker' | 'detail'
var _analysisPickerIntent = 'pick'; // 'pick' | 'ban' — поведение picker'а
var _ANALYSIS_MAX_BANS = 10;
var _analysisMatchups   = null;     // { "1": { vs: {...}, with: {...} }, ... }
var _analysisPopularity = null;     // { "1": { total, positions: { "1": {matches, win_rate}, ... } }, ... }
var _analysisDataLoading = false;
var _ANALYSIS_MIN_MATCH_COUNT = 30; // ниже — слишком шумно, игнорируем

// Параметры meta_bonus от per-position win_rate.
// Применяется и в _computeAnalysisScore, и в empty-board бейдже picker'а.
var _ANALYSIS_META_MIN_MATCHES = 200; // меньше — выборка не доверительная, бейдж = "—"
var _ANALYSIS_META_CENTER = 0.5;       // нейтральный winrate (50%) — точка отсчёта
var _ANALYSIS_META_SCALE  = 10;        // множитель отклонения от центра в score-единицы

// Русские алиасы для поиска. Покрывают героев из HERO_PRIMARY_POSITIONS.
// Несколько имён через запятую → каждое участвует в поиске как отдельный токен.
var _ANALYSIS_HERO_NAMES_RU = {
    1: 'антимаг,ам,antimage', 2: 'акс,топор', 3: 'бэйн', 4: 'бс,бладсикер,кровосос',
    5: 'кристалка,цм,crystal maiden,кристал мейден', 6: 'дроу,лучница', 7: 'эс,шейкер,земля',
    8: 'джаг,джагер', 9: 'мира,мирана', 10: 'морф,морфлинг', 11: 'сф,невермор,нм',
    12: 'пл,фантом ленсер,клоны', 13: 'пак', 14: 'пудж,хук,падж', 15: 'разор,молния',
    16: 'санд кинг,ск,песочник', 17: 'шторм,сторм', 18: 'свен', 19: 'тини,каменный',
    20: 'венга,венж,венджфул', 21: 'вр,виндрейнджер,винда', 22: 'зевс,зеус', 23: 'кунка,адмирал',
    25: 'лина', 26: 'лион', 27: 'шаман,сс,шадоу шаман', 28: 'слардар,рыба,селедка',
    29: 'тайд,тайдхантер', 30: 'вд,вич доктор', 31: 'лич', 32: 'рики',
    33: 'энигма,чёрная дыра', 34: 'тинкер,сын шлюхи', 35: 'снайпер,снайп', 36: 'некр,некрофос',
    37: 'варлок,локи', 38: 'бм,бистмастер,бист', 39: 'кв,квин,квин оф пэйн,квопа', 40: 'вено,веномансер,веник',
    41: 'войд,фэйслесс', 42: 'врейс,врейс кинг,скелет,вк', 43: 'дп,дэт профет,профетка', 44: 'па,фантомка',
    45: 'пугна', 46: 'та,темплар', 47: 'випер,вайпер', 48: 'луна',
    49: 'дк,драгон найт', 50: 'даззл', 51: 'клок,клокверк', 52: 'лешрак,леший',
    53: 'нп,натурс,фурион,фура', 54: 'лайф,лайфстилер,нейкс,гуля', 55: 'дс,дарк сир', 56: 'клинкз,клинк',
    57: 'омник,омнинайт', 58: 'энча,энчантресс', 59: 'хускар', 60: 'нс,найт сталкер',
    61: 'брудмазер,брудуха', 62: 'бх,баунти', 63: 'ткач,виверь,вивер', 64: 'джакиро',
    65: 'батрайдер,бэтрайдер,бэтик', 66: 'чен', 67: 'спектра,спектре', 68: 'аа,апа,апарик,апарат,аппарат',
    69: 'дум', 70: 'урса,медведь', 71: 'сб,спирит брейкер,бара,пиво', 72: 'гиро,гирокоптер,вертолет',
    73: 'алхим,алчимик', 74: 'инвокер,инвок,карл', 75: 'силенсер,сай,сало', 76: 'од,оверворлд,outworld',
    77: 'ликан,волки,люкан', 78: 'брю,брюмастер,панда,пиво', 79: 'шд,шадоу демон', 80: 'друид,лоун друид',
    81: 'ск,чаос найт,цк', 82: 'мипо', 83: 'трент,тент', 84: 'огр,огра',
    85: 'андаин,скелет,undying,зомби', 86: 'рубик', 87: 'дизраптор,диса', 88: 'никс',
    89: 'нага,сирена', 90: 'кота,kota,keeper,котел', 91: 'ио,виспер,wisp,шарик', 92: 'визаж',
    93: 'сларк', 94: 'медуза', 95: 'тролль,тролл', 96: 'кентавр,центавр',
    97: 'магнус,мага,колапс', 98: 'таймбер,timber,тимбер', 99: 'бристл,бб,brist', 100: 'таск,туск',
    101: 'скай,скайвраф,петух', 102: 'абба,абадон', 103: 'элдер,титан', 104: 'лк,легион',
    105: 'тачис,techies,минер,течис', 106: 'эмбер,эс,ember', 107: 'ес,earth spirit,земля,земеля', 108: 'ундерлорд,анделорд,андерлорд',
    109: 'тб,террорблейд', 110: 'фен,феникс', 111: 'оракл', 112: 'вв,винтер виверн,виверна',
    113: 'арк,арк варден', 114: 'мк,манки кинг,обезьяна', 119: 'дарк виллоу,виллоу,вилка',
    120: 'панго,пангольер', 121: 'грим,гримстрок', 123: 'худвинк,белка',
    126: 'войд спирит,вс', 128: 'снап,снапфаер,лиса,снэпка,снэпфаер', 129: 'марс',
    131: 'рингмастер,ринг', 135: 'давн,давнбрейкер,дб', 136: 'марси', 137: 'примал,бист,праймал',
    138: 'муэрта,муерта', 145: 'кез', 155: 'ларго'
};

// Lazy-built lower-cased search index: { id: ['name1', 'name2', ...] }
var _analysisSearchIndex = null;

function _buildAnalysisSearchIndex() {
    var idx = {};
    if (window.dotaHeroIds) {
        Object.keys(window.dotaHeroIds).forEach(function(name) {
            var id = window.dotaHeroIds[name];
            if (!idx[id]) idx[id] = [];
            idx[id].push(name.toLowerCase());
        });
    }
    Object.keys(_ANALYSIS_HERO_NAMES_RU).forEach(function(idStr) {
        var id = parseInt(idStr, 10);
        if (!idx[id]) idx[id] = [];
        _ANALYSIS_HERO_NAMES_RU[idStr].split(',').forEach(function(ru) {
            var s = ru.trim().toLowerCase();
            if (s) idx[id].push(s);
        });
    });
    return idx;
}

function _analysisHeroMatchesQuery(heroId, query) {
    if (!query) return true;
    if (!_analysisSearchIndex) _analysisSearchIndex = _buildAnalysisSearchIndex();
    var names = _analysisSearchIndex[heroId];
    if (!names) return false;
    for (var i = 0; i < names.length; i++) {
        if (names[i].indexOf(query) !== -1) return true;
    }
    return false;
}

function setDrafterMode(mode) {
    if (mode !== 'training' && mode !== 'analysis') mode = 'analysis';
    var prevMode = _drafterMode;
    _drafterMode = mode;
    try { localStorage.setItem('drafter_mode_v2', mode); } catch (e) {}

    // Гигиена long-press flag — иначе застрявший true после быстрого
    // переключения mode подавит первый нормальный tap при возврате в Анализ.
    _analysisLongPressFired = false;

    var trainingPanel = document.getElementById('drafter-mode-training');
    var analysisPanel = document.getElementById('drafter-mode-analysis');
    if (trainingPanel) trainingPanel.hidden = (mode !== 'training');
    if (analysisPanel) analysisPanel.hidden = (mode !== 'analysis');

    var tabs = document.querySelectorAll('.drafter-mode-tab');
    tabs.forEach(function(t) {
        var isActive = t.getAttribute('data-mode') === mode;
        t.classList.toggle('drafter-mode-tab--active', isActive);
        t.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    if (mode === 'analysis') {
        _ensureAnalysisData();
        renderAnalysisSlots();
    } else {
        // При выходе из Анализа закрыть любой открытый sheet и undo-toast
        closeAnalysisSheet();
        closeHeroDetailSheet();
        _hideAnalysisUndoToast();
        _analysisPickerIntent = 'pick';
        // При возврате из Анализа в Тренировку — обновить вражеский драфт.
        // Гард по _drafterMatchLoaded отсекает первый init-вызов: там матч ещё
        // грузится отдельным loadDrafterMatch() и второй параллельный запрос
        // не нужен.
        if (prevMode === 'analysis' && _drafterMatchLoaded) {
            loadDrafterMatch();
        }
    }
}

// Показывает баннер с ошибкой загрузки matchups_all прямо в панели анализа.
// Кнопка «Попробовать снова» сбрасывает баннер и заново дергает _ensureAnalysisData.
function _showAnalysisLoadError() {
    var panel = document.getElementById('drafter-mode-analysis');
    if (!panel) return;
    if (document.getElementById('analysis-load-error')) return;
    var box = document.createElement('div');
    box.id = 'analysis-load-error';
    box.className = 'analysis-load-error';
    var text = document.createElement('div');
    text.className = 'analysis-load-error-text';
    text.textContent = 'Не удалось загрузить данные для анализа. Проверьте соединение.';
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'analysis-load-error-retry';
    btn.textContent = 'Попробовать снова';
    btn.addEventListener('click', function() {
        _hideAnalysisLoadError();
        _ensureAnalysisData();
    });
    box.appendChild(text);
    box.appendChild(btn);
    panel.insertBefore(box, panel.firstChild);
}

function _hideAnalysisLoadError() {
    var box = document.getElementById('analysis-load-error');
    if (box && box.parentNode) box.parentNode.removeChild(box);
}

function _ensureAnalysisData() {
    if (_analysisMatchups && _analysisPopularity) return;
    if (_analysisDataLoading) return;
    _analysisDataLoading = true;
    _hideAnalysisLoadError();

    var base = window.API_BASE_URL;
    // Cache-Control: no-store — VPN-прокси и браузеры иначе могут отдать
    // устаревший снапшот матчапов и сломать драфтер между релизами.
    var noStore = { headers: { 'Cache-Control': 'no-store' } };
    var matchupsFailed = false;
    var p1 = _analysisMatchups
        ? Promise.resolve(null)
        : apiFetch(base + '/draft/matchups_all', noStore)
            .then(function(r) {
                if (!r.ok) throw new Error('HTTP ' + r.status);
                return r.json();
            })
            .then(function(d) { _analysisMatchups = d; })
            .catch(function(e) {
                matchupsFailed = true;
                console.warn('[analysis] matchups_all failed:', e);
            });
    var p2 = _analysisPopularity
        ? Promise.resolve(null)
        : apiFetch(base + '/draft/popularity', noStore)
            .then(function(r) { return r.ok ? r.json() : null; })
            .then(function(d) { if (d) _analysisPopularity = d; })
            .catch(function(e) { console.warn('[analysis] popularity failed:', e); });

    Promise.all([p1, p2]).then(function() {
        _analysisDataLoading = false;
        if (matchupsFailed && !_analysisMatchups) {
            _showAnalysisLoadError();
            return;
        }
        // Если открыт sheet — обновляем его содержимое с реальными данными
        if (_analysisSheetMode === 'picker') {
            renderAnalysisSheetGrid();
        } else if (_analysisSheetMode === 'detail') {
            var arr = (_analysisActiveSide === 'light') ? _analysisLight : _analysisDark;
            var hid = arr[_analysisActiveSlot];
            if (hid) _renderHeroDetailSheet(hid, _analysisActiveSide, _analysisActiveSlot);
        }
        // Слоты тоже зависят от matchups (net-contribution бейджи)
        if (_drafterMode === 'analysis') renderAnalysisSlots();
    });
}

function _analysisAllPicks() {
    return _analysisLight.concat(_analysisDark).filter(Boolean);
}

function _analysisHasAnyPick() {
    return _analysisAllPicks().length > 0;
}

// slotIndex 0..4 → русское название роли. Используется в заголовках picker'а
// и детального листа. Падает на «слот N» для невалидных индексов.
var _ANALYSIS_SLOT_ROLES = ['Керри', 'Мид', 'Оффлейн', 'Поддержка', 'Полная поддержка'];
function _analysisSlotRoleLabel(slotIndex) {
    if (slotIndex >= 0 && slotIndex <= 4) return _ANALYSIS_SLOT_ROLES[slotIndex];
    return 'слот ' + (slotIndex + 1);
}

/* Достаёт synergy-значение из matchups для пары (heroId → mapKey → otherId).
   Возвращает null если запись отсутствует или matchCount ниже порога. */
function _analysisGetPairValue(heroId, mapKey, otherId) {
    if (!_analysisMatchups) return null;
    var entry = _analysisMatchups[String(heroId)];
    if (!entry) return null;
    var map = entry[mapKey];
    if (!map) return null;
    var rec = map[String(otherId)];
    if (!rec) return null;
    if ((rec.matchCount || 0) < _ANALYSIS_MIN_MATCH_COUNT) return null;
    return rec.synergy || 0;
}

/* Симметричная синергия пары союзников: avg(with[a][b], with[b][a]),
   если хоть одно значение есть. Совместимо с формулой из /api/draft/evaluate. */
function _analysisPairSynergy(a, b) {
    var v1 = _analysisGetPairValue(a, 'with', b);
    var v2 = _analysisGetPairValue(b, 'with', a);
    if (v1 == null && v2 == null) return null;
    if (v1 == null) return v2;
    if (v2 == null) return v1;
    return (v1 + v2) / 2;
}

/* Возвращает все валидные пары синергии внутри стороны: [{a, b, value}]. */
function _analysisCollectSynergies(heroes) {
    var out = [];
    for (var i = 0; i < heroes.length; i++) {
        for (var j = i + 1; j < heroes.length; j++) {
            var v = _analysisPairSynergy(heroes[i], heroes[j]);
            if (v != null) out.push({ a: heroes[i], b: heroes[j], value: v });
        }
    }
    return out;
}

/* Возвращает все валидные пары матчапов между сторонами с точки зрения
   первой стороны (perspective): vs[perspective][other].synergy. */
function _analysisCollectMatchups(perspective, other) {
    var out = [];
    for (var i = 0; i < perspective.length; i++) {
        for (var j = 0; j < other.length; j++) {
            var v = _analysisGetPairValue(perspective[i], 'vs', other[j]);
            if (v != null) out.push({ self: perspective[i], opp: other[j], value: v });
        }
    }
    return out;
}

function _analysisSumValues(arr) {
    var s = 0;
    for (var i = 0; i < arr.length; i++) s += arr[i].value;
    return s;
}

function _renderAnalysisStats() {
    var box = document.getElementById('analysis-stats');
    if (!box) return;

    var light = _analysisLight.filter(Boolean);
    var dark  = _analysisDark.filter(Boolean);

    var lightSyn = _analysisCollectSynergies(light);
    var darkSyn  = _analysisCollectSynergies(dark);
    var lightVsDark = _analysisCollectMatchups(light, dark);
    var darkVsLight = _analysisCollectMatchups(dark, light);

    // Тоталы = сумма net-contribution бейджей всех героев стороны.
    // Итерируем 5-слотный массив с исходным индексом (нужен для meta_bonus
    // в _computeAnalysisScore — учитывает win_rate на позиции слота).
    var lightTotal = 0;
    for (var li = 0; li < _analysisLight.length; li++) {
        var lid = _analysisLight[li];
        if (lid) lightTotal += _computeAnalysisScore(lid, 'light', li);
    }
    var darkTotal = 0;
    for (var di = 0; di < _analysisDark.length; di++) {
        var did = _analysisDark[di];
        if (did) darkTotal += _computeAnalysisScore(did, 'dark', di);
    }
    _setAnalysisTotal('analysis-stats-total-light', lightTotal, light.length === 0);
    _setAnalysisTotal('analysis-stats-total-dark',  darkTotal,  dark.length  === 0);

    // Сильнейшая пара: max value среди всех внутрикомандных синергий обеих сторон.
    var allSyn = lightSyn.concat(darkSyn);
    var bestBody = document.getElementById('analysis-stats-best-body');
    if (allSyn.length === 0) {
        _setAnalysisRowEmpty(bestBody);
    } else {
        var best = allSyn[0];
        for (var i = 1; i < allSyn.length; i++) if (allSyn[i].value > best.value) best = allSyn[i];
        bestBody.className = 'analysis-stats-row-body';
        bestBody.innerHTML = _analysisRenderPair(best.a, best.b, '+', best.value, ' + ');
    }

    // Кросс-сторонние матчапы.
    var allMu = lightVsDark.concat(darkVsLight);

    // Лучший матчап: max положительное value.
    var bestMuBody = document.getElementById('analysis-stats-best-mu-body');
    var bestMu = null;
    for (var bi = 0; bi < allMu.length; bi++) {
        if (allMu[bi].value > 0 && (bestMu == null || allMu[bi].value > bestMu.value)) {
            bestMu = allMu[bi];
        }
    }
    if (bestMu == null) {
        _setAnalysisRowEmpty(bestMuBody);
    } else {
        bestMuBody.className = 'analysis-stats-row-body';
        bestMuBody.innerHTML = _analysisRenderPair(bestMu.self, bestMu.opp, '+', bestMu.value, ' vs ');
    }
}

function _setAnalysisRowEmpty(bodyEl) {
    if (!bodyEl) return;
    bodyEl.className = 'analysis-stats-row-body analysis-stats-row-body--empty';
    bodyEl.innerHTML = '—';
}

function _setAnalysisTotal(id, value, isEmpty) {
    var el = document.getElementById(id);
    if (!el) return;
    if (isEmpty) {
        el.className = 'analysis-stats-total analysis-stats-total--neutral';
        el.textContent = '—';
        return;
    }
    var tone = value > 0.05 ? 'positive' : (value < -0.05 ? 'negative' : 'neutral');
    var sign = value > 0 ? '+' : (value < 0 ? '−' : '');
    el.className = 'analysis-stats-total analysis-stats-total--' + tone;
    el.textContent = sign + Math.abs(value).toFixed(1);
}

function _analysisRenderPair(idA, idB, forcedSign, value, separator) {
    var nameA = (window.dotaHeroIdToName && window.dotaHeroIdToName[idA]) || ('#' + idA);
    var nameB = (window.dotaHeroIdToName && window.dotaHeroIdToName[idB]) || ('#' + idB);
    var iconA = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(nameA) : '';
    var iconB = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(nameB) : '';
    var safeA = String(nameA).replace(/"/g, '&quot;');
    var safeB = String(nameB).replace(/"/g, '&quot;');
    var tone, sign;
    if (forcedSign === '+') { tone = 'positive'; sign = '+'; }
    else if (forcedSign === '-') { tone = 'negative'; sign = '−'; }
    else {
        tone = value > 0.05 ? 'positive' : (value < -0.05 ? 'negative' : 'neutral');
        sign = value > 0 ? '+' : (value < 0 ? '−' : '');
    }
    var html = '<div class="analysis-stats-pair">';
    html += '<img class="analysis-stats-pair-icon" src="' + iconA + '" alt="' + safeA + '">';
    html += '<span class="analysis-stats-pair-sep">' + _escHtml(separator.trim()) + '</span>';
    html += '<img class="analysis-stats-pair-icon" src="' + iconB + '" alt="' + safeB + '">';
    html += '</div>';
    html += '<span class="analysis-stats-value analysis-stats-value--' + tone + '">' + sign + Math.abs(value).toFixed(1) + '</span>';
    return html;
}

function renderAnalysisSlots() {
    _renderAnalysisSide('light');
    _renderAnalysisSide('dark');
    renderAnalysisBans();
    _renderAnalysisStats();
    _renderAnalysisOnboarding();
    var clearBtn = document.getElementById('analysis-clear-btn');
    if (clearBtn) clearBtn.hidden = !_analysisHasAnyState();
}

function _analysisHasAnyState() {
    return _analysisHasAnyPick() || _analysisBans.size > 0;
}

/* ── Онбординг: одноразовый hint при первом заходе ────────────── */

var _ANALYSIS_ONBOARDING_KEY = 'analysis_onboarded';

function _isAnalysisOnboarded() {
    try { return localStorage.getItem(_ANALYSIS_ONBOARDING_KEY) === 'true'; }
    catch (e) { return true; } // если localStorage недоступен — не пытаемся показывать
}

function _renderAnalysisOnboarding() {
    var el = document.getElementById('analysis-onboarding');
    if (el) el.hidden = _isAnalysisOnboarded();
}

function _markAnalysisOnboarded() {
    if (_isAnalysisOnboarded()) return;
    try { localStorage.setItem(_ANALYSIS_ONBOARDING_KEY, 'true'); } catch (e) {}
    var el = document.getElementById('analysis-onboarding');
    if (el) el.hidden = true;
}

function clearAllAnalysisHeroes() {
    if (!_analysisHasAnyState()) return;
    _analysisLight = [null, null, null, null, null];
    _analysisDark  = [null, null, null, null, null];
    _analysisBans.clear();
    if (navigator.vibrate) navigator.vibrate(20);
    // Закрываем любые открытые sheet'ы и undo-toast — они ссылались на удалённых героев
    closeAnalysisSheet();
    closeHeroDetailSheet();
    _hideAnalysisUndoToast();
    renderAnalysisSlots();
}

/* ── Блок банов: рендер строки + обработчик слотов ───────────── */

function renderAnalysisBans() {
    var el = document.getElementById('analysis-bans-slots');
    if (!el) return;
    var bansArr = Array.from(_analysisBans);
    var html = '';
    for (var i = 0; i < _ANALYSIS_MAX_BANS; i++) {
        if (i < bansArr.length) {
            var heroId = bansArr[i];
            var heroName = (window.dotaHeroIdToName && window.dotaHeroIdToName[heroId]) || ('#' + heroId);
            var iconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(heroName) : '';
            var safeName = String(heroName).replace(/"/g, '&quot;');
            html += '<div class="analysis-ban-slot analysis-ban-slot--filled" onclick="analysisBanSlotClick(' + i + ')" title="' + safeName + ' — снять бан">';
            if (iconUrl) {
                html += '<img class="analysis-ban-slot-img" src="' + iconUrl + '" alt="">';
            }
            html += '</div>';
        } else {
            html += '<div class="analysis-ban-slot analysis-ban-slot--empty" onclick="analysisBanSlotClick(' + i + ')" title="Добавить бан">';
            html += '<svg class="analysis-ban-slot-empty-icon" viewBox="0 0 16 16" fill="none" aria-hidden="true">';
            html += '<circle cx="8" cy="8" r="6" stroke="currentColor" stroke-width="1.4"/>';
            html += '<line x1="3.7" y1="12.3" x2="12.3" y2="3.7" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>';
            html += '</svg>';
            html += '</div>';
        }
    }
    el.innerHTML = html;
}

function analysisBanSlotClick(idx) {
    _markAnalysisOnboarded();
    var bansArr = Array.from(_analysisBans);
    if (idx < bansArr.length) {
        // Заполненный слот — разбан
        _analysisBans.delete(bansArr[idx]);
        if (navigator.vibrate) navigator.vibrate(15);
        renderAnalysisSlots();
        // Если picker открыт — пересобрать (разбаненный герой снова доступен)
        if (_analysisSheetMode === 'picker') renderAnalysisSheetGrid();
    } else {
        // Пустой слот — открыть picker в режиме бана
        openAnalysisBanPicker();
    }
}

function openAnalysisBanPicker() {
    if (_analysisBans.size >= _ANALYSIS_MAX_BANS) return;
    if (_analysisSheetMode === 'detail') closeHeroDetailSheet();

    _analysisActiveSide = 'light';   // не релевантно для ban-mode, но не ломаем state
    _analysisActiveSlot = -1;        // нет slot-контекста
    _analysisSheetMode = 'picker';
    _analysisPickerIntent = 'ban';

    var sheet = document.getElementById('analysis-sheet');
    var title = document.getElementById('analysis-sheet-title');
    var search = document.getElementById('analysis-sheet-search');
    if (!sheet) return;

    if (title) title.textContent = 'Бан героя';
    if (search) search.value = '';

    sheet.hidden = false;
    sheet.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    renderAnalysisSheetGrid();
}

function _renderAnalysisSide(side) {
    var el = document.getElementById('analysis-' + side + '-slots');
    if (!el) return;
    if (!el._lpAttached) {
        _attachAnalysisLongPress(el, side);
        el._lpAttached = true;
    }
    var arr = (side === 'light') ? _analysisLight : _analysisDark;
    // Подсветка активного слота — только когда открыт picker (не detail sheet)
    var isActiveSide = (_analysisSheetMode === 'picker' && _analysisActiveSide === side);
    var html = '';
    for (var i = 0; i < 5; i++) {
        var hero = arr[i];
        var posSrc = '/images/positions/pos_' + (i + 1) + '.png';
        var cls = 'drafter-slot analysis-slot analysis-slot--' + side;
        if (hero) cls += ' analysis-slot--filled drafter-slot--filled';
        if (isActiveSide && i === _analysisActiveSlot) cls += ' analysis-slot--active';
        html += '<div class="' + cls + '" onclick="analysisSlotClick(\'' + side + '\',' + i + ')">';
        if (hero) {
            var iconUrl = _drafterHeroIcon(hero);
            if (iconUrl) {
                html += '<img src="' + iconUrl + '" alt="" class="drafter-slot-img">';
            } else {
                html += '<span style="font-size:10px;color:#aaa;">#' + hero + '</span>';
            }
            // Net-contribution бейдж: synergy с союзниками + matchup против врагов.
            // Пока matchups ещё не подгрузились — рисуем «—» вместо «0.0» (это «нет данных»,
            // а не «нулевой вклад»).
            if (!_analysisMatchups) {
                html += '<span class="analysis-slot-net analysis-slot-net--loading">—</span>';
            } else {
                var net = _computeAnalysisScore(hero, side, i);
                var netTone = net > 0.05 ? 'positive' : (net < -0.05 ? 'negative' : 'neutral');
                var netSign = net > 0 ? '+' : (net < 0 ? '−' : '');
                html += '<span class="analysis-slot-net analysis-slot-net--' + netTone + '">' + netSign + Math.abs(net).toFixed(1) + '</span>';
            }
            html += '<img src="' + posSrc + '" class="drafter-slot-pos-icon drafter-slot-pos-icon--badge" alt="">';
        } else {
            html += '<img src="' + posSrc + '" class="drafter-slot-pos-icon" alt="">';
        }
        html += '</div>';
    }
    el.innerHTML = html;
}

function analysisSlotClick(side, slotIndex) {
    // Если только что отработал long-press на этом слоте — подавляем
    // последующий click чтобы не открывать picker для уже опустошённого слота.
    if (_analysisLongPressFired) {
        _analysisLongPressFired = false;
        return;
    }
    _markAnalysisOnboarded();
    var arr = (side === 'light') ? _analysisLight : _analysisDark;
    if (arr[slotIndex]) {
        // Тап на занятый слот — открыть детали героя
        openHeroDetailSheet(side, slotIndex);
        return;
    }
    openAnalysisSheet(side, slotIndex);
}

/* ── Long-press на занятый слот = мгновенное удаление + undo toast ──── */

var _ANALYSIS_LONG_PRESS_MS = 500;
var _ANALYSIS_LONG_PRESS_MOVE_THRESHOLD = 8; // px — толерантность к джиттеру пальца
var _analysisLongPressTimer = null;
var _analysisLongPressFired = false;
var _analysisLongPressStartX = 0;
var _analysisLongPressStartY = 0;

function _attachAnalysisLongPress(container, side) {
    container.addEventListener('pointerdown', function(e) {
        var slot = e.target.closest('.analysis-slot');
        if (!slot || !container.contains(slot)) return;
        if (!slot.classList.contains('analysis-slot--filled')) return;

        var idx = Array.prototype.indexOf.call(container.children, slot);
        if (idx < 0) return;

        _analysisLongPressFired = false;
        _analysisLongPressStartX = e.clientX;
        _analysisLongPressStartY = e.clientY;

        clearTimeout(_analysisLongPressTimer);
        _analysisLongPressTimer = setTimeout(function() {
            _analysisLongPressTimer = null;
            _analysisLongPressFired = true;
            _instantRemoveAnalysisHero(side, idx);
        }, _ANALYSIS_LONG_PRESS_MS);
    });

    container.addEventListener('pointermove', function(e) {
        if (!_analysisLongPressTimer) return;
        var dx = e.clientX - _analysisLongPressStartX;
        var dy = e.clientY - _analysisLongPressStartY;
        if (Math.abs(dx) > _ANALYSIS_LONG_PRESS_MOVE_THRESHOLD ||
            Math.abs(dy) > _ANALYSIS_LONG_PRESS_MOVE_THRESHOLD) {
            clearTimeout(_analysisLongPressTimer);
            _analysisLongPressTimer = null;
        }
    });

    var cancel = function() {
        clearTimeout(_analysisLongPressTimer);
        _analysisLongPressTimer = null;
    };
    container.addEventListener('pointerup', cancel);
    container.addEventListener('pointercancel', cancel);
    container.addEventListener('pointerleave', cancel);
}

function _instantRemoveAnalysisHero(side, slotIndex) {
    var arr = (side === 'light') ? _analysisLight : _analysisDark;
    var heroId = arr[slotIndex];
    if (!heroId) return;
    arr[slotIndex] = null;
    // Двойной короткий buzz — чтобы тактильно отличался от обычного tap-feedback
    if (navigator.vibrate) navigator.vibrate([15, 30, 15]);
    renderAnalysisSlots();
    _showAnalysisUndoToast(heroId, side, slotIndex);
}

function openAnalysisSheet(side, slotIndex) {
    if (_analysisSheetMode === 'detail') closeHeroDetailSheet();

    _analysisActiveSide = side;
    _analysisActiveSlot = slotIndex;
    _analysisSheetMode = 'picker';

    var sheet = document.getElementById('analysis-sheet');
    var title = document.getElementById('analysis-sheet-title');
    var search = document.getElementById('analysis-sheet-search');
    if (!sheet) return;

    if (title) {
        var sideLabel = (side === 'light') ? 'Силы Света' : 'Силы Тьмы';
        title.textContent = sideLabel + ' · ' + _analysisSlotRoleLabel(slotIndex);
    }
    if (search) search.value = '';

    sheet.hidden = false;
    sheet.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';

    renderAnalysisSlots();         // подсветить активный слот
    renderAnalysisSheetGrid();
}

function closeAnalysisSheet() {
    var sheet = document.getElementById('analysis-sheet');
    if (!sheet) return;
    sheet.hidden = true;
    sheet.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    _analysisActiveSlot = -1;
    _analysisPickerIntent = 'pick';     // сбрасываем intent на дефолтный
    if (_analysisSheetMode === 'picker') _analysisSheetMode = null;
    renderAnalysisSlots();              // снять подсветку
}

/* ── Bottom sheet с деталями уже выбранного героя ───────────────── */

function openHeroDetailSheet(side, slotIndex) {
    if (_analysisSheetMode === 'picker') closeAnalysisSheet();

    var arr = (side === 'light') ? _analysisLight : _analysisDark;
    var heroId = arr[slotIndex];
    if (!heroId) return;

    _analysisActiveSide = side;
    _analysisActiveSlot = slotIndex;
    _analysisSheetMode = 'detail';

    _renderHeroDetailSheet(heroId, side, slotIndex);

    var sheet = document.getElementById('analysis-hero-detail-sheet');
    if (!sheet) return;
    sheet.hidden = false;
    sheet.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
}

function closeHeroDetailSheet() {
    var sheet = document.getElementById('analysis-hero-detail-sheet');
    if (!sheet) return;
    sheet.hidden = true;
    sheet.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    _analysisActiveSlot = -1;
    if (_analysisSheetMode === 'detail') _analysisSheetMode = null;
}

function removeAnalysisHeroFromDetail() {
    if (_analysisActiveSlot < 0 || _analysisActiveSlot > 4) return;
    var arr = (_analysisActiveSide === 'light') ? _analysisLight : _analysisDark;
    var removedSide = _analysisActiveSide;
    var removedSlot = _analysisActiveSlot;
    var removedHeroId = arr[removedSlot];
    arr[removedSlot] = null;
    if (navigator.vibrate) navigator.vibrate(15);
    closeHeroDetailSheet();
    renderAnalysisSlots();
    _showAnalysisUndoToast(removedHeroId, removedSide, removedSlot);
}

/* ── Undo toast для удалённого героя ──────────────────────────────── */

var _analysisUndoTimer = null;

function _showAnalysisUndoToast(heroId, side, slotIndex) {
    if (!heroId) return;
    var heroName = (window.dotaHeroIdToName && window.dotaHeroIdToName[heroId]) || ('#' + heroId);

    var el = document.getElementById('analysis-undo-toast');
    if (!el) {
        el = document.createElement('div');
        el.id = 'analysis-undo-toast';
        el.className = 'analysis-undo-toast';
        document.body.appendChild(el);
    }
    el.innerHTML =
        '<span class="analysis-undo-toast-text">' + _escHtml(heroName) + ' удалён</span>' +
        '<button class="analysis-undo-toast-btn" type="button">Вернуть</button>';
    var btn = el.querySelector('.analysis-undo-toast-btn');
    if (btn) btn.onclick = function() { _undoAnalysisRemoval(heroId, side, slotIndex); };

    // requestAnimationFrame чтобы opacity-transition реально сработал, если toast только что создан
    requestAnimationFrame(function() { el.classList.add('analysis-undo-toast--visible'); });

    clearTimeout(_analysisUndoTimer);
    _analysisUndoTimer = setTimeout(function() { _hideAnalysisUndoToast(); }, 4000);
}

function _hideAnalysisUndoToast() {
    var el = document.getElementById('analysis-undo-toast');
    if (el) el.classList.remove('analysis-undo-toast--visible');
    clearTimeout(_analysisUndoTimer);
    _analysisUndoTimer = null;
}

function _undoAnalysisRemoval(heroId, side, slotIndex) {
    var arr = (side === 'light') ? _analysisLight : _analysisDark;
    // Слот успели заполнить чем-то другим — undo отменяется
    if (arr[slotIndex]) { _hideAnalysisUndoToast(); return; }
    // Этого героя уже добавили обратно где-то ещё — undo отменяется
    if (_analysisAllPicks().indexOf(heroId) !== -1) { _hideAnalysisUndoToast(); return; }

    arr[slotIndex] = heroId;
    if (navigator.vibrate) navigator.vibrate(10);
    _hideAnalysisUndoToast();
    renderAnalysisSlots();
}

function _renderHeroDetailSheet(heroId, side, slotIndex) {
    var heroName = (window.dotaHeroIdToName && window.dotaHeroIdToName[heroId]) || ('#' + heroId);
    var portraitUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(heroName) : '';

    var portraitEl = document.getElementById('analysis-detail-portrait');
    var nameEl = document.getElementById('analysis-detail-name');
    var posEl  = document.getElementById('analysis-detail-pos');
    var netEl  = document.getElementById('analysis-detail-net');

    if (portraitEl) {
        portraitEl.src = portraitUrl;
        portraitEl.alt = heroName;
    }
    if (nameEl) nameEl.textContent = heroName;
    if (posEl) {
        var sideLabel = (side === 'light') ? 'Силы Света' : 'Силы Тьмы';
        posEl.textContent = sideLabel + ' · ' + _analysisSlotRoleLabel(slotIndex);
    }
    if (netEl) {
        var netValue = _computeAnalysisScore(heroId, side, slotIndex);
        var tone = netValue > 0.05 ? 'positive' : (netValue < -0.05 ? 'negative' : 'neutral');
        var sign = netValue > 0 ? '+' : (netValue < 0 ? '−' : '');
        netEl.className = 'analysis-detail-net-value analysis-detail-net-value--' + tone;
        netEl.textContent = sign + Math.abs(netValue).toFixed(1);
    }

    var alliesArr  = ((side === 'light') ? _analysisLight : _analysisDark);
    var enemiesArr = ((side === 'light') ? _analysisDark  : _analysisLight);
    var allies  = alliesArr.filter(function(id) { return id && id !== heroId; });
    var enemies = enemiesArr.filter(Boolean);

    var alliesData = allies.map(function(id) {
        return { id: id, value: _analysisGetPairValue(heroId, 'with', id) };
    });
    var enemiesData = enemies.map(function(id) {
        return { id: id, value: _analysisGetPairValue(heroId, 'vs', id) };
    });

    // Сортировка: по убыванию |value|; пары без данных — в конец
    var sortByImpact = function(a, b) {
        if (a.value == null && b.value == null) return 0;
        if (a.value == null) return 1;
        if (b.value == null) return -1;
        return Math.abs(b.value) - Math.abs(a.value);
    };
    alliesData.sort(sortByImpact);
    enemiesData.sort(sortByImpact);

    var alliesEl  = document.getElementById('analysis-detail-allies');
    var enemiesEl = document.getElementById('analysis-detail-enemies');
    if (alliesEl) {
        alliesEl.innerHTML = alliesData.length === 0
            ? '<div class="analysis-detail-empty">Нет союзников</div>'
            : alliesData.map(_renderHeroDetailRow).join('');
    }
    if (enemiesEl) {
        enemiesEl.innerHTML = enemiesData.length === 0
            ? '<div class="analysis-detail-empty">Нет врагов</div>'
            : enemiesData.map(_renderHeroDetailRow).join('');
    }
}

function _renderHeroDetailRow(item) {
    var name = (window.dotaHeroIdToName && window.dotaHeroIdToName[item.id]) || ('#' + item.id);
    var iconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(name) : '';
    var safeName = String(name).replace(/"/g, '&quot;');

    var valueHtml;
    if (item.value == null) {
        valueHtml = '<span class="analysis-detail-row-value analysis-detail-row-value--neutral">—</span>';
    } else {
        var tone = item.value > 0.05 ? 'positive' : (item.value < -0.05 ? 'negative' : 'neutral');
        var sign = item.value > 0 ? '+' : (item.value < 0 ? '−' : '');
        valueHtml = '<span class="analysis-detail-row-value analysis-detail-row-value--' + tone + '">' + sign + Math.abs(item.value).toFixed(1) + '</span>';
    }

    return '<div class="analysis-detail-row">' +
        '<img class="analysis-detail-row-icon" src="' + iconUrl + '" alt="' + safeName + '">' +
        '<span class="analysis-detail-row-name">' + _escHtml(name) + '</span>' +
        valueHtml +
        '</div>';
}

function _computeAnalysisScore(heroId, sideOverride, slotIndexOverride) {
    if (!_analysisMatchups) return 0;
    var entry = _analysisMatchups[String(heroId)];
    if (!entry) return 0;

    var side = sideOverride || _analysisActiveSide;
    var slotIdx = (slotIndexOverride != null) ? slotIndexOverride : _analysisActiveSlot;
    var allies  = (side === 'light') ? _analysisLight : _analysisDark;
    var enemies = (side === 'light') ? _analysisDark  : _analysisLight;

    var score = 0;
    var withMap = entry['with'] || {};
    for (var i = 0; i < allies.length; i++) {
        var aid = allies[i];
        if (!aid || aid === heroId) continue;
        var w = withMap[String(aid)];
        if (w && (w.matchCount || 0) >= _ANALYSIS_MIN_MATCH_COUNT) {
            score += w.synergy || 0;
        }
    }
    var vsMap = entry['vs'] || {};
    for (var j = 0; j < enemies.length; j++) {
        var eid = enemies[j];
        if (!eid) continue;
        var v = vsMap[String(eid)];
        if (v && (v.matchCount || 0) >= _ANALYSIS_MIN_MATCH_COUNT) {
            score += v.synergy || 0;
        }
    }

    // Meta-bonus от per-position win_rate: герой, чей win_rate на этой позиции
    // выше 50%, получает положительную добавку; ниже — отрицательную.
    // Гейт по объёму выборки 200 матчей — иначе слишком шумно.
    if (slotIdx >= 0 && slotIdx <= 4 && _analysisPopularity) {
        var heroPop = _analysisPopularity[String(heroId)];
        var posData = (heroPop && heroPop.positions)
            ? heroPop.positions[String(slotIdx + 1)]
            : null;
        if (posData && (posData.matches || 0) >= _ANALYSIS_META_MIN_MATCHES && posData.win_rate != null) {
            score += (posData.win_rate - _ANALYSIS_META_CENTER) * _ANALYSIS_META_SCALE;
        }
    }

    return score;
}

function onAnalysisSheetSearch() {
    renderAnalysisSheetGrid();
}

function renderAnalysisSheetGrid() {
    var grid = document.getElementById('analysis-sheet-grid');
    if (!grid) return;

    if (!window.dotaHeroIds) {
        grid.innerHTML = '<div class="analysis-sheet-empty">Герои не загружены</div>';
        return;
    }

    var searchEl = document.getElementById('analysis-sheet-search');
    var query = searchEl ? searchEl.value.toLowerCase().trim() : '';
    var hasContext = _analysisHasAnyPick();
    var pop = _analysisPopularity || {};
    var pickedSet = new Set(_analysisAllPicks());

    // Позиция активного слота: slotIndex (0-4) → pos (1-5).
    // Для поиска позиция игнорируется (один общий список).
    var slotPos = (_analysisActiveSlot >= 0) ? (_analysisActiveSlot + 1) : null;

    // Собираем уникальных героев. dotaHeroIds может содержать алиасы на один id —
    // дедуп по id, при поиске учитываем все имена + русские алиасы.
    var seen = new Set();
    var heroes = [];
    var isBanModeForLoop = (_analysisPickerIntent === 'ban');
    Object.keys(window.dotaHeroIds).forEach(function(name) {
        var id = window.dotaHeroIds[name];
        if (seen.has(id)) return;
        seen.add(id);
        if (pickedSet.has(id)) return;
        if (query && !_analysisHeroMatchesQuery(id, query)) return;
        // Bans:
        // - в ban-picker'е забаненных не показываем (нечего разбанивать через picker)
        // - в обычном pick-picker'е без поиска тоже скрываем (не засоряют топ)
        // - при активном поиске — показываем как disabled (визуально отмечены)
        var isBanned = _analysisBans.has(id);
        if (isBanned) {
            if (isBanModeForLoop) return;
            if (!query) return;
        }

        var score = hasContext ? _computeAnalysisScore(id) : 0;
        // Popularity payload теперь объект {total, positions:{...}} — берём total
        var popData = pop[String(id)];
        var popularity = (popData && popData.total) || 0;
        var primaryPos = (typeof HERO_PRIMARY_POSITIONS !== 'undefined') ? HERO_PRIMARY_POSITIONS[id] : null;

        // Per-slot позиционные данные (для пустой доски — sort by win_rate
        // + рендер meta-score бейджа на карточке).
        var posData = (slotPos != null && popData && popData.positions)
            ? popData.positions[String(slotPos)]
            : null;
        var matchesAtSlot = (posData && typeof posData.matches === 'number') ? posData.matches : 0;
        var winRateAtSlot = (posData && posData.win_rate != null) ? posData.win_rate : null;

        heroes.push({
            id: id, name: name, score: score, pop: popularity, pos: primaryPos,
            winRateAtSlot: winRateAtSlot, matchesAtSlot: matchesAtSlot,
            banned: isBanned
        });
    });

    // Ban mode — сортировка по глобальной популярности (most-played first).
    // Empty board + slot-context — по per-position win_rate.
    // Иначе — по score (включает meta_bonus от win_rate с гейтом ≥200).
    // Во всех случаях: banned-герои выпадают в самый низ (только видны при поиске
    // в pick-режиме, не должны конкурировать за внимание с доступными пиками).
    var isBanMode = (_analysisPickerIntent === 'ban');
    var sortFn;
    if (isBanMode) {
        sortFn = function(a, b) {
            if (b.pop !== a.pop) return b.pop - a.pop;
            return a.name.localeCompare(b.name);
        };
    } else if (!hasContext && slotPos != null) {
        sortFn = function(a, b) {
            if (a.banned !== b.banned) return a.banned ? 1 : -1;
            var wA = (a.winRateAtSlot != null) ? a.winRateAtSlot : -Infinity;
            var wB = (b.winRateAtSlot != null) ? b.winRateAtSlot : -Infinity;
            if (wB !== wA) return wB - wA;
            if (b.pop !== a.pop) return b.pop - a.pop;
            return a.name.localeCompare(b.name);
        };
    } else {
        sortFn = function(a, b) {
            if (a.banned !== b.banned) return a.banned ? 1 : -1;
            if (b.score !== a.score) return b.score - a.score;
            if (b.pop !== a.pop) return b.pop - a.pop;
            return a.name.localeCompare(b.name);
        };
    }

    var html = '';

    if (isBanMode || query || slotPos == null) {
        // Ban mode / поиск / нет позиции — единый плоский список.
        // В ban-режиме показываем всех (≤125), для пика без поиска — топ-20.
        heroes.sort(sortFn);
        var flat;
        if (isBanMode) flat = heroes;
        else flat = heroes.slice(0, query ? heroes.length : 20);
        if (flat.length === 0) {
            grid.innerHTML = '<div class="analysis-sheet-empty">' + (query ? 'Не найдено' : 'Нет данных') + '</div>';
            return;
        }
        flat.forEach(function(h) { html += _renderAnalysisPickCard(h, hasContext); });
    } else {
        // Одна группа «Позиция N» через frequency-based фильтр: герой попадает
        // если на этой позиции играется ≥ порога от своих матчей. Порог
        // динамический: 0.07 пока на доске <4 героев (свободный exploration),
        // 0.10 когда героев ≥4 — сужаем до бесспорных мета-флексов.
        // Шум дополнительно фильтруется минимум-50-матчей floor'ом источника.
        // Fallback per-hero на статический map когда нет данных в popularity
        // payload'е (новый герой / старый формат / попадание до загрузки данных).
        // Героев, не проходящих порог, в picker'е не показываем — для них
        // остаётся поиск по имени.
        var pickedCount = _analysisLight.filter(Boolean).length + _analysisDark.filter(Boolean).length;
        var freqThreshold = pickedCount < 4 ? 0.07 : 0.10;
        var primary = [];
        heroes.forEach(function(h) {
            var hasFreqData = h.pop > 0 && typeof h.matchesAtSlot === 'number';
            var inPrimary;
            if (hasFreqData) {
                inPrimary = (h.matchesAtSlot / h.pop) >= freqThreshold;
            } else {
                inPrimary = (h.pos === slotPos);
            }
            if (inPrimary) primary.push(h);
        });
        primary.sort(sortFn);

        if (primary.length === 0) {
            grid.innerHTML = '<div class="analysis-sheet-empty">Нет данных</div>';
            return;
        }

        html += '<div class="analysis-sheet-divider">Позиция ' + slotPos + '</div>';
        primary.forEach(function(h) { html += _renderAnalysisPickCard(h, hasContext); });
    }

    grid.innerHTML = html;
    // При новом рендере прокручиваем наверх, чтобы лучшие герои были видны
    grid.scrollTop = 0;
}

function _renderAnalysisPickCard(h, hasContext) {
    var iconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(h.name) : '';
    var safeName = String(h.name).replace(/"/g, '&quot;');
    var clsBanned = h.banned ? ' analysis-pick-card--banned' : '';
    var titleAttr = safeName + (h.banned ? ' — забанен' : '');
    var onclick = h.banned ? '' : ' onclick="selectAnalysisHero(' + h.id + ')"';
    var html = '<div class="analysis-pick-card' + clsBanned + '"' + onclick + ' title="' + titleAttr + '">';
    if (iconUrl) {
        html += '<img class="analysis-pick-card-img" src="' + iconUrl + '" alt="' + safeName + '">';
    } else {
        html += '<div class="analysis-pick-card-img drafter-grid-img-empty"></div>';
    }
    html += '<div class="analysis-pick-card-name">' + _escHtml(h.name) + '</div>';
    // Score-бейджи не показываем для забаненных — они недоступны и любые числа вводят в заблуждение
    if (h.banned) {
        // no badge
    } else if (hasContext) {
        // С контекстом — обычный score (synergy + matchup + meta_bonus)
        var tone = h.score > 0.05 ? 'positive' : (h.score < -0.05 ? 'negative' : 'neutral');
        var sign = h.score > 0 ? '+' : (h.score < 0 ? '−' : '');
        var abs  = Math.abs(h.score).toFixed(1);
        html += '<div class="analysis-pick-card-score analysis-pick-card-score--' + tone + '">' + sign + abs + '</div>';
    } else {
        // Empty-board — meta-score из per-position win_rate в том же формате;
        // при matches < _ANALYSIS_META_MIN_MATCHES или отсутствии данных — «—» нейтральным.
        if (h.matchesAtSlot < _ANALYSIS_META_MIN_MATCHES || h.winRateAtSlot == null) {
            html += '<div class="analysis-pick-card-score analysis-pick-card-score--neutral">—</div>';
        } else {
            var metaScore = (h.winRateAtSlot - _ANALYSIS_META_CENTER) * _ANALYSIS_META_SCALE;
            var mTone = metaScore > 0.05 ? 'positive' : (metaScore < -0.05 ? 'negative' : 'neutral');
            var mSign = metaScore > 0 ? '+' : (metaScore < 0 ? '−' : '');
            var mAbs  = Math.abs(metaScore).toFixed(1);
            html += '<div class="analysis-pick-card-score analysis-pick-card-score--' + mTone + '">' + mSign + mAbs + '</div>';
        }
    }
    html += '</div>';
    return html;
}

function selectAnalysisHero(heroId) {
    if (_analysisPickerIntent === 'ban') {
        // Ban mode — добавить героя в баны, sheet оставляем открытым,
        // чтобы можно было быстро забанить серию героев подряд.
        if (_analysisBans.has(heroId)) return;
        if (_analysisBans.size >= _ANALYSIS_MAX_BANS) {
            closeAnalysisSheet();
            return;
        }
        _analysisBans.add(heroId);
        if (navigator.vibrate) navigator.vibrate(15);
        renderAnalysisBans();
        // Пересобрать grid — забаненный герой исчезает из списка
        if (_analysisBans.size >= _ANALYSIS_MAX_BANS) {
            closeAnalysisSheet();
        } else {
            renderAnalysisSheetGrid();
        }
        return;
    }
    if (_analysisActiveSlot < 0 || _analysisActiveSlot > 4) return;
    var arr = (_analysisActiveSide === 'light') ? _analysisLight : _analysisDark;
    arr[_analysisActiveSlot] = heroId;

    if (navigator.vibrate) navigator.vibrate(15);

    closeAnalysisSheet();
    renderAnalysisSlots();
}

async function loadDrafterMatch() {
    _drafterMatchLoaded = false;
    _drafterAllyPick = [null, null, null, null, null];
    _drafterActiveSlot = 0;
    _drafterEnemyPick = [];
    _drafterEnemyManualMode = false;
    _drafterActiveEnemySlot = -1;
    _updateManualBtn();

    document.getElementById('drafter-main').style.display = 'block';
    document.getElementById('drafter-result').style.display = 'none';
    document.getElementById('drafter-evaluate-wrap').style.display = 'none';

    var enemySlotsEl = document.getElementById('drafter-enemy-slots');
    if (enemySlotsEl) enemySlotsEl.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:8px 0;">Загрузка...</div>';

    try {
        var resp = await apiFetch(window.API_BASE_URL + '/draft/random');
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
        var cls = 'drafter-slot drafter-slot--ally';
        if (isActive) cls += ' drafter-slot--active';
        if (hero) cls += ' drafter-slot--filled';
        var posSrc = '/images/positions/pos_' + (i + 1) + '.png';
        html += '<div class="' + cls + '" id="drafter-ally-slot-' + i + '" onclick="drafterSlotClick(' + i + ')">';
        if (hero && hero.hero_id) {
            var iconUrl = _drafterHeroIcon(hero.hero_id);
            if (iconUrl) {
                html += '<img src="' + iconUrl + '" alt="" class="drafter-slot-img">';
            } else {
                html += '<span style="font-size:10px;color:#aaa;">#' + hero.hero_id + '</span>';
            }
            html += '<img src="' + posSrc + '" class="drafter-slot-pos-icon drafter-slot-pos-icon--badge" alt="">';
        } else {
            html += '<img src="' + posSrc + '" class="drafter-slot-pos-icon" alt="">';
        }
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
        html += '<div class="' + cls + '" id="drafter-enemy-slot-' + i + '"' + clickAttr + '>';
        if (hero.hero_id) {
            var iconUrl = _drafterHeroIcon(hero.hero_id);
            if (iconUrl) {
                html += '<img src="' + iconUrl + '" alt="" class="drafter-slot-img">';
            } else {
                html += '<span style="font-size:10px;color:#aaa;">#' + hero.hero_id + '</span>';
            }
            var posNum = parseInt(String(hero.position || '').replace('pos ', ''), 10);
            if (posNum >= 1 && posNum <= 5) {
                html += '<img src="/images/positions/pos_' + posNum + '.png" class="drafter-slot-pos-icon drafter-slot-pos-icon--badge" alt="">';
            }
        } else {
            html += '<img src="/images/positions/pos_' + (i + 1) + '.png" class="drafter-slot-pos-icon" alt="">';
        }
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
        var p = parseInt(btn.dataset.pos, 10);
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
        heroes = heroes.filter(function(h) { return _analysisHeroMatchesQuery(h.id, query); });
    } else {
        // Фильтр по основной позиции (1..5)
        heroes = heroes.filter(function(h) { return HERO_PRIMARY_POSITIONS[h.id] === _drafterPosFilter; });
    }

    // Уже выбранные
    var pickedIds = new Set(_drafterAllyPick.filter(Boolean).map(function(h) { return h.hero_id; }));

    var html = '';
    heroes.forEach(function(h) {
        var isPicked = pickedIds.has(h.id);
        var isEnemy  = _drafterEnemyPick.some(function(e) { return e && e.hero_id === h.id; });
        var iconUrl = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(h.name) : '';
        var cls = 'drafter-grid-hero' + (isPicked ? ' drafter-grid-hero--picked' : '') + (isEnemy ? ' drafter-grid-hero--enemy drafter-hero-disabled' : '');
        var onclick = (isPicked || isEnemy) ? '' : ' onclick="selectDrafterHero(' + h.id + ')"';
        var safeName = String(h.name).replace(/"/g, '&quot;');
        html += '<div class="' + cls + '"' + onclick + ' title="' + safeName + '">';
        if (iconUrl) {
            html += '<img src="' + iconUrl + '" alt="' + safeName + '" class="drafter-grid-img">';
        } else {
            html += '<div class="drafter-grid-img-empty"></div>';
        }
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
// kind: 'ok' — зелёный (положительные подтверждения); по умолчанию красный
// (ошибки и состояния-блокировки). Существующие call sites без второго
// аргумента остаются красными — это полностью backward-compatible.
function showToast(msg, kind) {
    var el = document.getElementById('app-toast');
    if (!el) {
        el = document.createElement('div');
        el.id = 'app-toast';
        el.className = 'app-toast';
        document.body.appendChild(el);
    }
    el.textContent = msg;
    // Чистим прошлый модификатор перед применением нового — иначе зелёный
    // toast после красного «прилипает» к зелёной палитре до перерендера.
    el.classList.remove('app-toast--ok');
    if (kind === 'ok') el.classList.add('app-toast--ok');
    el.classList.add('app-toast--visible');
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(function() {
        el.classList.remove('app-toast--visible');
    }, 3500);
}

var _lastSubmitDraftTs = 0;

async function submitDraft() {
    var now = Date.now();
    if (now - _lastSubmitDraftTs < 5000) return;
    _lastSubmitDraftTs = now;

    var ally = _drafterAllyPick.filter(Boolean);
    var enemy = _drafterEnemyPick.filter(function(h) { return h && h.hero_id; });

    var btn = document.getElementById('drafter-evaluate-btn');
    if (btn) btn.disabled = true;

    try {
        var resp = await apiFetch(window.API_BASE_URL + '/draft/evaluate', {
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
        var allyIds = ally.map(function(h) { return h && h.hero_id; }).filter(Boolean);
        var enemyIds = enemy.map(function(h) { return h && h.hero_id; }).filter(Boolean);
        if (typeof cacheLastDraftEval === 'function') cacheLastDraftEval(data, allyIds, enemyIds);
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

function _draftRankClass(rank) {
    if (rank === 'SSS' || rank === 'S') return 'drafter-hist-rank drafter-hist-rank--s';
    if (rank === 'A') return 'drafter-hist-rank drafter-hist-rank--a';
    if (rank === 'B') return 'drafter-hist-rank drafter-hist-rank--b';
    return 'drafter-hist-rank drafter-hist-rank--neutral';
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

function _histBuildHeader(PAGE_ID) {
    var header = document.createElement('div');
    header.className = 'drafter-fp-header';

    var back = document.createElement('button');
    back.type = 'button';
    back.className = 'drafter-fp-back';
    back.setAttribute('aria-label', 'Назад');
    back.textContent = '← Назад';
    back.addEventListener('click', function() { hideDrafterFullpage(PAGE_ID); });
    header.appendChild(back);

    var title = document.createElement('div');
    title.className = 'drafter-fp-title';
    title.textContent = 'Моя история';
    header.appendChild(title);

    var spacer = document.createElement('div');
    spacer.className = 'drafter-fp-spacer';
    header.appendChild(spacer);

    return header;
}

function _histBuildSkeleton(count) {
    var frag = document.createDocumentFragment();
    for (var i = 0; i < count; i++) {
        var card = document.createElement('div');
        card.className = 'drafter-hist-skel-card';
        card.setAttribute('aria-hidden', 'true');

        var top = document.createElement('div');
        top.className = 'drafter-hist-skel-top';

        var rank = document.createElement('div');
        rank.className = 'drafter-hist-skel-shape drafter-hist-skel-rank';
        top.appendChild(rank);

        var meta = document.createElement('div');
        meta.className = 'drafter-hist-skel-shape drafter-hist-skel-meta';
        top.appendChild(meta);

        var score = document.createElement('div');
        score.className = 'drafter-hist-skel-shape drafter-hist-skel-score';
        top.appendChild(score);

        card.appendChild(top);

        for (var t = 0; t < 2; t++) {
            var heroesRow = document.createElement('div');
            heroesRow.className = 'drafter-hist-skel-heroes';
            for (var h = 0; h < 5; h++) {
                var hero = document.createElement('div');
                hero.className = 'drafter-hist-skel-shape drafter-hist-skel-hero';
                heroesRow.appendChild(hero);
            }
            card.appendChild(heroesRow);
        }

        frag.appendChild(card);
    }
    return frag;
}

function _histBuildEmptyBlock(titleText, subText, onRetry) {
    var wrap = document.createElement('div');
    wrap.className = 'drafter-lb-empty';
    if (onRetry) wrap.setAttribute('role', 'alert');
    else wrap.setAttribute('role', 'status');

    var title = document.createElement('div');
    title.className = 'drafter-lb-empty-title';
    title.textContent = titleText;
    wrap.appendChild(title);

    if (subText) {
        var text = document.createElement('div');
        text.className = 'drafter-lb-empty-text';
        text.textContent = subText;
        wrap.appendChild(text);
    }

    if (onRetry) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'drafter-lb-retry';
        btn.textContent = 'Повторить';
        btn.addEventListener('click', onRetry);
        wrap.appendChild(btn);
    }

    return wrap;
}

function _histBuildTeam(labelText, heroIds, sideClass) {
    var team = document.createElement('div');
    team.className = 'drafter-hist-team';

    var label = document.createElement('div');
    label.className = 'drafter-hist-team-label';
    label.textContent = labelText;
    team.appendChild(label);

    var row = document.createElement('div');
    row.className = 'drafter-hist-heroes';
    heroIds.forEach(function(id) {
        var url = _drafterHeroIcon(id);
        if (!url) return;
        var img = document.createElement('img');
        img.className = 'drafter-hist-hero ' + sideClass;
        img.src = url;
        img.loading = 'lazy';
        img.decoding = 'async';
        var name = (typeof _drafterHeroName === 'function') ? _drafterHeroName(id) : '';
        img.alt = name || '';
        if (name) img.title = name;
        row.appendChild(img);
    });
    team.appendChild(row);

    return team;
}

function _histBuildCard(r) {
    var card = document.createElement('div');
    card.className = 'drafter-hist-card';

    var top = document.createElement('div');
    top.className = 'drafter-hist-top';

    var rank = document.createElement('div');
    rank.className = _draftRankClass(r.rank);
    rank.textContent = r.rank;
    top.appendChild(rank);

    var meta = document.createElement('div');
    meta.className = 'drafter-hist-meta';
    meta.textContent = _draftFormatDate(r.created_at);
    top.appendChild(meta);

    var scoreBlock = document.createElement('div');
    scoreBlock.className = 'drafter-hist-score-block';
    var scoreLabel = document.createElement('div');
    scoreLabel.className = 'drafter-hist-score-label';
    scoreLabel.textContent = 'Счёт';
    scoreBlock.appendChild(scoreLabel);
    var score = document.createElement('div');
    score.className = 'drafter-hist-score';
    score.textContent = r.total_score;
    scoreBlock.appendChild(score);
    top.appendChild(scoreBlock);

    card.appendChild(top);

    if (r.ally_heroes && r.enemy_heroes) {
        var teams = document.createElement('div');
        teams.className = 'drafter-hist-teams';
        teams.appendChild(_histBuildTeam('Враги', r.enemy_heroes, 'drafter-hist-hero--enemy'));
        teams.appendChild(_histBuildTeam('Союзники', r.ally_heroes, 'drafter-hist-hero--ally'));
        card.appendChild(teams);
    }

    return card;
}

function _histBuildScaffold(PAGE_ID) {
    var frag = document.createDocumentFragment();
    frag.appendChild(_histBuildHeader(PAGE_ID));
    var content = document.createElement('div');
    content.className = 'drafter-fp-content';
    frag.appendChild(content);
    return { frag: frag, content: content };
}

async function showDrafterHistory() {
    var PAGE_ID = 'drafter-history-page';
    var page = document.getElementById(PAGE_ID);
    page.style.display = 'block';
    page.textContent = '';

    var scaffold = _histBuildScaffold(PAGE_ID);
    page.appendChild(scaffold.frag);
    var content = scaffold.content;

    if (!USER_TOKEN) {
        content.appendChild(_histBuildEmptyBlock(
            'Войдите, чтобы посмотреть историю',
            'Драфты сохраняются для авторизованных игроков',
            null
        ));
        return;
    }

    content.appendChild(_histBuildSkeleton(4));

    try {
        var resp = await apiFetch(window.API_BASE_URL + '/draft/history?token=' + USER_TOKEN);
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var rows = await resp.json();

        content.textContent = '';

        if (!rows || rows.length === 0) {
            content.appendChild(_histBuildEmptyBlock(
                'Пока нет драфтов',
                'Сохранённые результаты появятся здесь',
                null
            ));
            return;
        }

        var frag = document.createDocumentFragment();
        rows.forEach(function(r) { frag.appendChild(_histBuildCard(r)); });
        content.appendChild(frag);
    } catch (e) {
        content.textContent = '';
        content.appendChild(_histBuildEmptyBlock(
            'Не удалось загрузить историю',
            'Проверь соединение и попробуй ещё раз',
            function() { showDrafterHistory(); }
        ));
    }
}

function _lbCurrentMonthLabel() {
    // "Май 2026" — текущий календарный месяц для подзаголовка лидерборда.
    var d = new Date();
    var month = d.toLocaleDateString('ru-RU', { month: 'long' });
    month = month.charAt(0).toUpperCase() + month.slice(1);
    return month + ' ' + d.getFullYear();
}

function _lbBuildHeader(PAGE_ID) {
    var header = document.createElement('div');
    header.className = 'drafter-fp-header';

    var back = document.createElement('button');
    back.type = 'button';
    back.className = 'drafter-fp-back';
    back.setAttribute('aria-label', 'Назад');
    back.textContent = '← Назад';
    back.addEventListener('click', function() { hideDrafterFullpage(PAGE_ID); });
    header.appendChild(back);

    var title = document.createElement('div');
    title.className = 'drafter-fp-title';
    var titleMain = document.createElement('div');
    titleMain.textContent = 'Топ драфтеров';
    title.appendChild(titleMain);
    var titleMonth = document.createElement('div');
    titleMonth.className = 'drafter-fp-title-month';
    titleMonth.textContent = _lbCurrentMonthLabel();
    title.appendChild(titleMonth);
    header.appendChild(title);

    var spacer = document.createElement('div');
    spacer.className = 'drafter-fp-spacer';
    header.appendChild(spacer);

    return header;
}

function _lbBuildNote() {
    var note = document.createElement('div');
    note.className = 'lb-note';
    var icon = document.createElement('span');
    icon.className = 'lb-note-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = 'ℹ';
    note.appendChild(icon);
    note.appendChild(document.createTextNode(' Счёт по сумме '));
    var b = document.createElement('b');
    b.textContent = 'лучших 5 результатов';
    note.appendChild(b);
    return note;
}

function _lbBuildSkeletonRows(count) {
    var frag = document.createDocumentFragment();
    for (var i = 0; i < count; i++) {
        var row = document.createElement('div');
        row.className = 'drafter-lb-skel-row';
        row.setAttribute('aria-hidden', 'true');

        var place = document.createElement('div');
        place.className = 'drafter-lb-skel-shape drafter-lb-skel-place';
        row.appendChild(place);

        var avatar = document.createElement('div');
        avatar.className = 'drafter-lb-skel-shape drafter-lb-skel-avatar';
        row.appendChild(avatar);

        var info = document.createElement('div');
        info.style.flex = '1';
        info.style.minWidth = '0';
        var name = document.createElement('div');
        name.className = 'drafter-lb-skel-shape drafter-lb-skel-name';
        var sub = document.createElement('div');
        sub.className = 'drafter-lb-skel-shape drafter-lb-skel-sub';
        info.appendChild(name);
        info.appendChild(sub);
        row.appendChild(info);

        var score = document.createElement('div');
        score.className = 'drafter-lb-skel-shape drafter-lb-skel-score';
        row.appendChild(score);

        frag.appendChild(row);
    }
    return frag;
}

function _lbBuildEmpty() {
    var wrap = document.createElement('div');
    wrap.className = 'drafter-lb-empty';
    var title = document.createElement('div');
    title.className = 'drafter-lb-empty-title';
    title.textContent = 'Пока нет участников';
    wrap.appendChild(title);
    var text = document.createElement('div');
    text.className = 'drafter-lb-empty-text';
    text.textContent = 'Сыграй драфт, чтобы попасть в топ';
    wrap.appendChild(text);
    return wrap;
}

function _lbBuildError(onRetry) {
    var wrap = document.createElement('div');
    wrap.className = 'drafter-lb-empty';
    wrap.setAttribute('role', 'alert');

    var title = document.createElement('div');
    title.className = 'drafter-lb-empty-title';
    title.textContent = 'Не удалось загрузить топ';
    wrap.appendChild(title);

    var text = document.createElement('div');
    text.className = 'drafter-lb-empty-text';
    text.textContent = 'Проверь соединение и попробуй ещё раз';
    wrap.appendChild(text);

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'drafter-lb-retry';
    btn.textContent = 'Повторить';
    btn.addEventListener('click', onRetry);
    wrap.appendChild(btn);
    return wrap;
}

function _lbBuildRow(r) {
    var row = document.createElement('div');
    var cls = 'drafter-lb-row';
    if (r.rank === 1) cls += ' drafter-lb-row--top1';
    else if (r.rank === 2) cls += ' drafter-lb-row--top2';
    else if (r.rank === 3) cls += ' drafter-lb-row--top3';
    row.className = cls;

    var place = document.createElement('div');
    place.className = 'drafter-lb-place';
    place.textContent = r.rank;
    row.appendChild(place);

    var displayName = r.username || r.first_name || ('Игрок ' + r.user_id);
    var firstChar = displayName.charAt(0).toUpperCase();

    if (r.photo_url) {
        var img = document.createElement('img');
        img.className = 'drafter-lb-avatar';
        img.src = r.photo_url;
        img.alt = '';
        img.loading = 'lazy';
        img.decoding = 'async';
        img.setAttribute('aria-hidden', 'true');

        var fallback = document.createElement('div');
        fallback.className = 'drafter-lb-avatar-letter';
        fallback.style.display = 'none';
        fallback.textContent = firstChar;

        img.addEventListener('error', function() {
            img.style.display = 'none';
            fallback.style.display = 'flex';
        });

        row.appendChild(img);
        row.appendChild(fallback);
    } else {
        var letter = document.createElement('div');
        letter.className = 'drafter-lb-avatar-letter';
        letter.textContent = firstChar;
        row.appendChild(letter);
    }

    var info = document.createElement('div');
    info.className = 'drafter-lb-info';

    var name = document.createElement('div');
    name.className = 'drafter-lb-name';
    name.textContent = displayName;
    info.appendChild(name);

    var count = document.createElement('div');
    count.className = 'drafter-lb-count';
    count.textContent = r.draft_count + ' драфтов';
    info.appendChild(count);

    row.appendChild(info);

    var score = document.createElement('div');
    score.className = 'drafter-lb-score';
    score.textContent = r.top5_sum;
    row.appendChild(score);

    return row;
}

function _lbRenderRowsInto(content, rows) {
    content.textContent = '';
    if (!rows || rows.length === 0) {
        content.appendChild(_lbBuildEmpty());
        return;
    }
    var frag = document.createDocumentFragment();
    rows.forEach(function(r) { frag.appendChild(_lbBuildRow(r)); });
    content.appendChild(frag);
}

function _lbBuildScaffold(PAGE_ID) {
    var frag = document.createDocumentFragment();
    frag.appendChild(_lbBuildHeader(PAGE_ID));
    frag.appendChild(_lbBuildNote());
    var content = document.createElement('div');
    content.className = 'drafter-fp-content';
    frag.appendChild(content);
    return { frag: frag, content: content };
}

async function _lbAttachMyrankBar(page) {
    var token = (typeof USER_TOKEN !== 'undefined' ? USER_TOKEN : '') || '';
    if (!token) return;

    var bar = document.createElement('div');
    bar.id = 'drafter-lb-myrank-bar';
    bar.className = 'drafter-lb-myrank';
    bar.setAttribute('role', 'status');
    bar.setAttribute('aria-label', 'Ваша позиция в лидерборде');
    bar.style.display = 'none';
    page.appendChild(bar);

    try {
        var meResp = await apiFetch(window.API_BASE_URL + '/draft/leaderboard/me?token=' + encodeURIComponent(token));
        if (!meResp.ok) return;
        var me = await meResp.json();
        if (!me || me.rank === null) return;
        if (me.rank <= 25) return;

        var left = document.createElement('div');
        left.className = 'drafter-lb-myrank-left';
        left.appendChild(document.createTextNode('Ваше место: '));
        var rank = document.createElement('span');
        rank.className = 'drafter-lb-myrank-rank';
        rank.textContent = '#' + me.rank;
        left.appendChild(rank);
        bar.appendChild(left);

        var right = document.createElement('div');
        right.className = 'drafter-lb-myrank-right';
        var label = document.createElement('div');
        label.className = 'drafter-lb-myrank-label';
        label.textContent = 'Счёт';
        right.appendChild(label);
        var score = document.createElement('div');
        score.className = 'drafter-lb-myrank-score';
        score.textContent = me.top5_sum;
        right.appendChild(score);
        bar.appendChild(right);

        bar.style.display = 'flex';
    } catch (e) { /* ignore */ }
}

async function showDrafterLeaderboard() {
    var PAGE_ID = 'drafter-leaderboard-page';
    var page = document.getElementById(PAGE_ID);
    page.style.display = 'block';
    page.textContent = '';

    var scaffold = _lbBuildScaffold(PAGE_ID);
    page.appendChild(scaffold.frag);
    var content = scaffold.content;

    if (_drafterLeaderboardCache) {
        _lbRenderRowsInto(content, _drafterLeaderboardCache);
        _lbAttachMyrankBar(page);
        return;
    }

    content.appendChild(_lbBuildSkeletonRows(6));

    try {
        var resp = await apiFetch(window.API_BASE_URL + '/draft/leaderboard');
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        var rows = await resp.json();
        _drafterLeaderboardCache = rows;
        _lbRenderRowsInto(content, rows);
        _lbAttachMyrankBar(page);
    } catch (e) {
        content.textContent = '';
        content.appendChild(_lbBuildError(function() { showDrafterLeaderboard(); }));
    }
}

function showDrafterResult(data) {
    document.getElementById('drafter-main').style.display = 'none';
    document.getElementById('drafter-result').style.display = 'block';

    var confrontScreen = document.getElementById('dr-confront-screen');
    var synergyScreen  = document.getElementById('dr-synergy-screen');
    var finalScreen    = document.getElementById('dr-final-screen');

    confrontScreen.style.display = 'none';
    synergyScreen.style.display  = 'none';
    finalScreen.style.display    = 'none';

    var allyIds      = data.ally_ids      || [];
    var enemyIds     = data.enemy_ids     || [];
    var matchupPairs = data.matchup_pairs || [];
    var synergyPairs = data.synergy_pairs || [];

    function _icon(id) { return _drafterHeroIcon(id) || ''; }
    function _name(id) { return _drafterHeroName(id) || ('Герой #' + id); }

    var _skip = false;
    function sleep(ms) {
        return new Promise(function(resolve) {
            if (_skip) { resolve(); return; }
            setTimeout(resolve, ms);
        });
    }

    function skipAnim() {
        if (_skip) return;
        _skip = true;
        try { gsap.globalTimeline.clear(); } catch(e) {}
        confrontScreen.style.display = 'none';
        synergyScreen.style.display  = 'none';
        gsap.set([confrontScreen, synergyScreen], {clearProps: 'opacity,scale'});
        var sb = document.getElementById('dr-skip-btn');
        if (sb) sb.remove();
        showFinal();
    }

    var _skipBtn = document.createElement('button');
    _skipBtn.id = 'dr-skip-btn';
    _skipBtn.className = 'dr-skip-btn';
    _skipBtn.textContent = 'Пропустить';
    _skipBtn.addEventListener('click', skipAnim);
    // Append to <html> so no body-level wrapper, transform, or overflow can
    // break position: fixed in mobile WebViews.
    document.documentElement.appendChild(_skipBtn);
    _skipBtn.style.opacity = '0';
    setTimeout(function() {
        _skipBtn.style.transition = 'opacity 0.35s ease-out';
        _skipBtn.style.opacity = '1';
    }, 400);

    // ─── STEP 1 · ПРОТИВОСТОЯНИЕ (1А сильнейший → 1Б слабейший) ─────
    async function playConfront() {
        if (!allyIds.length || !enemyIds.length || !matchupPairs.length) return;

        function pairValue(allyId, enemyId) {
            for (var k = 0; k < matchupPairs.length; k++) {
                var p = matchupPairs[k];
                if (p.ally_id === allyId && p.enemy_id === enemyId) return p.value;
            }
            return 0;
        }

        var allyTotals = allyIds.map(function(allyId) {
            var perEnemy = enemyIds.map(function(enemyId) {
                return { enemyId: enemyId, value: pairValue(allyId, enemyId) };
            });
            var sum = perEnemy.reduce(function(s, e) { return s + e.value; }, 0);
            return { allyId: allyId, sum: sum, perEnemy: perEnemy };
        });

        var sorted = allyTotals.slice().sort(function(a, b) { return b.sum - a.sum; });
        var strongest = sorted[0];
        var weakest   = sorted[sorted.length - 1];

        function cardHtml(side, t) {
            var labelText  = side === 'best' ? 'СИЛЬНЕЙШИЙ' : 'СЛАБЕЙШИЙ';
            var labelColor = side === 'best' ? 'var(--positive)' : 'var(--negative)';
            var sumColor   = t.sum > 0.5 ? 'var(--positive)' : t.sum < -0.5 ? 'var(--negative)' : 'var(--warning)';

            var rowsHtml = t.perEnemy.map(function(e) {
                var c = e.value > 0.1 ? 'var(--positive)'
                      : e.value < -0.1 ? 'var(--negative)'
                      : 'rgba(255,255,255,0.18)';
                var w = Math.min(100, Math.abs(e.value) * 14);
                var posClass = e.value >= 0 ? 'is-pos' : 'is-neg';
                return (
                    '<div class="dr-cf-row">' +
                        '<img class="dr-cf-row-icon" src="' + _icon(e.enemyId) + '" onerror="this.style.opacity=0">' +
                        '<div class="dr-cf-row-bar">' +
                            '<div class="dr-cf-row-mid"></div>' +
                            '<div class="dr-cf-row-fill ' + posClass + '" data-pct="' + w.toFixed(1) + '" style="background:' + c + ';width:0%;"></div>' +
                        '</div>' +
                        '<div class="dr-cf-row-val" style="color:' + c + ';">' + (e.value >= 0 ? '+' : '') + e.value.toFixed(1) + '</div>' +
                    '</div>'
                );
            }).join('');

            return (
                '<div class="dr-cf-card dr-cf-card--' + side + ' dr-cf-card--solo">' +
                    '<div class="dr-cf-card-label" style="color:' + labelColor + ';">' + labelText + '</div>' +
                    '<div class="dr-cf-card-portrait">' +
                        '<img src="' + _icon(t.allyId) + '" onerror="this.style.opacity=0">' +
                    '</div>' +
                    '<div class="dr-cf-card-name">' + _name(t.allyId) + '</div>' +
                    '<div class="dr-cf-card-total" style="color:' + sumColor + ';" data-target="' + t.sum.toFixed(2) + '">+0.0</div>' +
                    '<div class="dr-cf-card-rowlabel">vs враги</div>' +
                    '<div class="dr-cf-card-rows">' + rowsHtml + '</div>' +
                '</div>'
            );
        }

        confrontScreen.style.display = 'block';

        async function showBeat(side, t) {
            confrontScreen.innerHTML = (
                '<div class="dr-cf-grid dr-cf-grid--single">' +
                    cardHtml(side, t) +
                '</div>'
            );

            var card = confrontScreen.querySelector('.dr-cf-card');

            gsap.set(card, {opacity: 0, y: 20});
            gsap.to(card,  {opacity: 1, y: 0, duration: 0.55, ease: 'power3.out'});

            await sleep(720);
            if (_skip) return;

            var totalEl = card.querySelector('.dr-cf-card-total');
            var target  = parseFloat(totalEl.getAttribute('data-target'));
            var c = {v: 0};
            gsap.to(c, {
                v: target, duration: 0.8, ease: 'power2.out',
                onUpdate: function() {
                    totalEl.textContent = (c.v >= 0 ? '+' : '') + c.v.toFixed(1);
                }
            });

            var fills = card.querySelectorAll('.dr-cf-row-fill');
            fills.forEach(function(fill, fi) {
                var pct = parseFloat(fill.getAttribute('data-pct'));
                gsap.to(fill, {
                    width: pct + '%',
                    duration: 0.5,
                    delay: 0.18 + fi * 0.05,
                    ease: 'power2.out'
                });
            });

            await sleep(2200);
            if (_skip) return;

            gsap.to(confrontScreen, {opacity: 0, duration: 0.35, ease: 'power2.in'});
            await sleep(380);
            gsap.set(confrontScreen, {opacity: 1});
        }

        await showBeat('best',  strongest);
        if (_skip) return;
        await showBeat('worst', weakest);
        if (_skip) return;

        confrontScreen.style.display = 'none';
    }

    // ─── STEP 2 · СИНЕРГИЯ — pentagon redone ────────────────────────
    async function playSynergy() {
        if (allyIds.length < 2 || !synergyPairs.length) return;

        var W    = Math.min(340, document.documentElement.clientWidth - 40);
        var H    = W;
        var cx   = W / 2;
        var cy   = H / 2;
        var R    = W * 0.36;
        var SLOT = 54;

        var pts = allyIds.map(function(_, i) {
            var ang = i * 2 * Math.PI / 5 - Math.PI / 2;
            return { x: cx + R * Math.cos(ang), y: cy + R * Math.sin(ang) };
        });

        function pairValue(i, j) {
            var a = allyIds[i], b = allyIds[j];
            for (var k = 0; k < synergyPairs.length; k++) {
                var p = synergyPairs[k];
                if ((p.hero_id1 === a && p.hero_id2 === b) ||
                    (p.hero_id1 === b && p.hero_id2 === a)) return p.value;
            }
            return 0;
        }

        var allValues = [];
        var edges = [];
        for (var i = 0; i < allyIds.length; i++) {
            for (var j = i + 1; j < allyIds.length; j++) {
                var v = pairValue(i, j);
                allValues.push(v);
                edges.push({ i: i, j: j, v: v });
            }
        }
        var maxAbs = Math.max.apply(null, allValues.map(function(v) { return Math.abs(v); }).concat([1]));
        edges.forEach(function(e) { e.intensity = Math.abs(e.v) / maxAbs; });
        edges.sort(function(a, b) { return Math.abs(a.v) - Math.abs(b.v); });

        var sumSyn = allValues.reduce(function(s, v) { return s + v; }, 0);

        var bgPolyPts = pts.map(function(p) { return p.x.toFixed(1) + ',' + p.y.toFixed(1); }).join(' ');

        var svg =
            '<svg width="' + W + '" height="' + H + '" viewBox="0 0 ' + W + ' ' + H + '" style="overflow:visible;display:block;">' +
                '<polygon class="dr-syn-frame" points="' + bgPolyPts + '" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="1" stroke-dasharray="3 4"/>' +
                edges.map(function(e) {
                    var p1 = pts[e.i], p2 = pts[e.j];
                    var color = e.v > 0.1 ? '#3db87a' : e.v < -0.1 ? '#e5534b' : '#56565f';
                    var sw    = 1 + e.intensity * 3.6;
                    return '<line class="dr-syn-edge" data-i="' + e.i + '" data-j="' + e.j + '" data-v="' + e.v.toFixed(2) + '" ' +
                           'x1="' + p1.x.toFixed(1) + '" y1="' + p1.y.toFixed(1) + '" ' +
                           'x2="' + p2.x.toFixed(1) + '" y2="' + p2.y.toFixed(1) + '" ' +
                           'stroke="' + color + '" stroke-width="' + sw.toFixed(2) + '" ' +
                           'stroke-linecap="round" opacity="0" />';
                }).join('') +
            '</svg>';

        var verticesHtml = pts.map(function(p, i) {
            return '<div class="dr-syn-vertex" data-i="' + i + '" ' +
                   'style="left:' + (p.x - SLOT/2).toFixed(1) + 'px;top:' + (p.y - SLOT/2).toFixed(1) + 'px;width:' + SLOT + 'px;height:' + SLOT + 'px;">' +
                       '<img src="' + _icon(allyIds[i]) + '" onerror="this.style.opacity=0">' +
                   '</div>';
        }).join('');

        synergyScreen.innerHTML = (
            '<div class="dr-step-label">СОЮЗНАЯ СИНЕРГИЯ</div>' +
            '<div class="dr-syn-stage" style="width:' + W + 'px;height:' + H + 'px;">' +
                svg + verticesHtml +
            '</div>' +
            '<div class="dr-syn-summary">' +
                '<span class="dr-syn-summary-label">Сумма</span>' +
                '<span class="dr-syn-summary-val" id="dr-syn-cval">+0.0</span>' +
            '</div>'
        );

        synergyScreen.style.display = 'flex';

        var stepEl   = synergyScreen.querySelector('.dr-step-label');
        var stage    = synergyScreen.querySelector('.dr-syn-stage');
        var frame    = synergyScreen.querySelector('.dr-syn-frame');
        var vertices = synergyScreen.querySelectorAll('.dr-syn-vertex');
        var edgeEls  = synergyScreen.querySelectorAll('.dr-syn-edge');
        var summary  = synergyScreen.querySelector('.dr-syn-summary');
        var cValEl   = document.getElementById('dr-syn-cval');

        gsap.set(stepEl,   {opacity: 0, y: -8});
        gsap.set(stage,    {opacity: 0, scale: 0.92});
        gsap.set(vertices, {opacity: 0, scale: 0.4});
        gsap.set(summary,  {opacity: 0, y: 8});
        gsap.set(frame,    {opacity: 0});

        gsap.to(stepEl, {opacity: 1, y: 0, duration: 0.4, ease: 'power2.out'});
        gsap.to(stage,  {opacity: 1, scale: 1, duration: 0.55, delay: 0.1, ease: 'power3.out'});
        gsap.to(frame,  {opacity: 1, duration: 0.6, delay: 0.25, ease: 'power2.out'});

        await sleep(380);
        if (_skip) return;

        gsap.to(vertices, {
            opacity: 1, scale: 1, duration: 0.55,
            stagger: { each: 0.07, from: 'start' },
            ease: 'back.out(1.5)'
        });

        await sleep(700);
        if (_skip) return;

        for (var idx = 0; idx < edgeEls.length; idx++) {
            if (_skip) return;
            var edge = edgeEls[idx];
            var len  = edge.getTotalLength();
            edge.style.strokeDasharray  = len;
            edge.style.strokeDashoffset = len;
            edge.style.opacity = 1;

            var pair = edges[idx];
            var v1   = vertices[pair.i];
            var v2   = vertices[pair.j];

            gsap.to(edge, { strokeDashoffset: 0, duration: 0.30, ease: 'power2.inOut' });
            gsap.fromTo([v1, v2],
                { scale: 1 },
                { scale: 1.10, duration: 0.16, yoyo: true, repeat: 1, ease: 'power1.inOut' });

            await sleep(380);
        }
        if (_skip) return;

        gsap.to(summary, {opacity: 1, y: 0, duration: 0.45, ease: 'power2.out'});
        var cnt = {v: 0};
        gsap.to(cnt, {
            v: sumSyn, duration: 0.85, ease: 'power2.out',
            onUpdate: function() {
                cValEl.textContent = (cnt.v >= 0 ? '+' : '') + cnt.v.toFixed(1);
                cValEl.style.color = cnt.v > 3 ? 'var(--positive)'
                                  : cnt.v < -3 ? 'var(--negative)'
                                  : 'var(--warning)';
            }
        });

        await sleep(1500);
        if (_skip) return;

        gsap.to(synergyScreen, {opacity: 0, duration: 0.4, ease: 'power2.in'});
        await sleep(420);
        synergyScreen.style.display = 'none';
        gsap.set(synergyScreen, {opacity: 1});
    }

    // ─── STEP 3 · МАТРИЦА + RANK ────────────────────────────────────
    function showFinal() {
        var sb = document.getElementById('dr-skip-btn');
        if (sb) sb.remove();

        var total = Math.round(data.total_score || 0);
        var rank, rankColor, rankDesc;
        if (total >= 85)      { rank = 'SSS'; rankColor = 'var(--warning)';  rankDesc = 'Идеальный драфт'; }
        else if (total >= 70) { rank = 'S';   rankColor = 'var(--warning)';  rankDesc = 'Отличный драфт'; }
        else if (total >= 55) { rank = 'A';   rankColor = 'var(--accent)';   rankDesc = 'Хороший драфт'; }
        else if (total >= 45) { rank = 'B';   rankColor = 'var(--text-primary)'; rankDesc = 'Средний драфт'; }
        else                  { rank = 'C';   rankColor = 'var(--text-secondary)'; rankDesc = 'Слабый драфт'; }

        var best = parseInt(localStorage.getItem('drafter_best_score') || '0', 10);
        var isRecord = total > best;
        if (isRecord) localStorage.setItem('drafter_best_score', total);

        function matchupValue(allyId, enemyId) {
            for (var k = 0; k < matchupPairs.length; k++) {
                var p = matchupPairs[k];
                if (p.ally_id === allyId && p.enemy_id === enemyId) return p.value;
            }
            return 0;
        }
        function synergyValue(a, b) {
            if (a === b) return null;
            for (var k = 0; k < synergyPairs.length; k++) {
                var p = synergyPairs[k];
                if ((p.hero_id1 === a && p.hero_id2 === b) ||
                    (p.hero_id1 === b && p.hero_id2 === a)) return p.value;
            }
            return 0;
        }

        var maxAbsMu  = matchupPairs.reduce(function(m, p) { return Math.max(m, Math.abs(p.value)); }, 1);
        var maxAbsSyn = synergyPairs.reduce(function(m, p) { return Math.max(m, Math.abs(p.value)); }, 1);

        function cellBg(v, maxAbs) {
            if (v === null) return 'rgba(255,255,255,0.02)';
            if (Math.abs(v) < 0.1) return 'rgba(255,255,255,0.03)';
            var alpha = Math.min(0.45, 0.08 + Math.abs(v) / maxAbs * 0.40);
            return v > 0
                ? 'rgba(61, 184, 122, ' + alpha.toFixed(3) + ')'
                : 'rgba(229, 83, 75, ' + alpha.toFixed(3) + ')';
        }
        function cellTxt(v) {
            if (v === null)   return 'rgba(255,255,255,0.18)';
            if (v > 0.5)      return '#a8e7c4';
            if (v < -0.5)     return '#f3aaa6';
            return 'var(--text-secondary)';
        }
        function fmt(v) { return (v >= 0 ? '+' : '') + v.toFixed(1); }
        function sumColorCls(s) {
            return s > 0.5 ? 'var(--positive)' : s < -0.5 ? 'var(--negative)' : 'var(--warning)';
        }

        // ── Matrix 1: ally × enemy (advantage) ──────────────────────────
        var muHeader = '<div class="dr-mx-cell dr-mx-corner"></div>' +
            enemyIds.map(function(id) {
                return '<div class="dr-mx-cell dr-mx-head dr-mx-head-enemy"><img src="' + _icon(id) + '" onerror="this.style.opacity=0"></div>';
            }).join('') +
            '<div class="dr-mx-cell dr-mx-totals-head">Итог</div>';

        var muRows = allyIds.map(function(allyId) {
            var rowSum = 0;
            var cellsHtml = enemyIds.map(function(enemyId) {
                var v = matchupValue(allyId, enemyId);
                rowSum += v;
                return '<div class="dr-mx-cell dr-mx-data" style="background:' + cellBg(v, maxAbsMu) + ';color:' + cellTxt(v) + ';">' + fmt(v) + '</div>';
            }).join('');
            return '<div class="dr-mx-row">' +
                '<div class="dr-mx-cell dr-mx-head dr-mx-head-ally"><img src="' + _icon(allyId) + '" onerror="this.style.opacity=0"></div>' +
                cellsHtml +
                '<div class="dr-mx-cell dr-mx-rowsum" style="color:' + sumColorCls(rowSum) + ';">' + fmt(rowSum) + '</div>' +
            '</div>';
        }).join('');

        var muColSums = enemyIds.map(function(enemyId) {
            return allyIds.reduce(function(s, allyId) { return s + matchupValue(allyId, enemyId); }, 0);
        });
        var muGrand = muColSums.reduce(function(s, v) { return s + v; }, 0);
        var muColRow = '<div class="dr-mx-row dr-mx-row-tot">' +
            '<div class="dr-mx-cell dr-mx-totals-head">Итог</div>' +
            muColSums.map(function(s) {
                return '<div class="dr-mx-cell dr-mx-colsum" style="color:' + sumColorCls(s) + ';">' + fmt(s) + '</div>';
            }).join('') +
            '<div class="dr-mx-cell dr-mx-grand" style="color:' + (muGrand >= 0 ? 'var(--positive)' : 'var(--negative)') + ';">' + fmt(muGrand) + '</div>' +
        '</div>';

        // ── Matrix 2: ally × ally (synergy, symmetric) ──────────────────
        var synHeader = '<div class="dr-mx-cell dr-mx-corner"></div>' +
            allyIds.map(function(id) {
                return '<div class="dr-mx-cell dr-mx-head dr-mx-head-ally"><img src="' + _icon(id) + '" onerror="this.style.opacity=0"></div>';
            }).join('') +
            '<div class="dr-mx-cell dr-mx-totals-head">Итог</div>';

        var synRows = allyIds.map(function(rowId) {
            var rowSum = 0;
            var cellsHtml = allyIds.map(function(colId) {
                var v = synergyValue(rowId, colId);
                if (v === null) {
                    return '<div class="dr-mx-cell dr-mx-data dr-mx-diag" style="background:' + cellBg(null) + ';color:' + cellTxt(null) + ';">—</div>';
                }
                rowSum += v;
                return '<div class="dr-mx-cell dr-mx-data" style="background:' + cellBg(v, maxAbsSyn) + ';color:' + cellTxt(v) + ';">' + fmt(v) + '</div>';
            }).join('');
            return '<div class="dr-mx-row">' +
                '<div class="dr-mx-cell dr-mx-head dr-mx-head-ally"><img src="' + _icon(rowId) + '" onerror="this.style.opacity=0"></div>' +
                cellsHtml +
                '<div class="dr-mx-cell dr-mx-rowsum" style="color:' + sumColorCls(rowSum) + ';">' + fmt(rowSum) + '</div>' +
            '</div>';
        }).join('');

        var synColSums = allyIds.map(function(colId) {
            return allyIds.reduce(function(s, rowId) {
                var v = synergyValue(rowId, colId);
                return s + (v === null ? 0 : v);
            }, 0);
        });
        var synGrand = synColSums.reduce(function(s, v) { return s + v; }, 0) / 2;
        var synColRow = '<div class="dr-mx-row dr-mx-row-tot">' +
            '<div class="dr-mx-cell dr-mx-totals-head">Итог</div>' +
            synColSums.map(function(s) {
                return '<div class="dr-mx-cell dr-mx-colsum" style="color:' + sumColorCls(s) + ';">' + fmt(s) + '</div>';
            }).join('') +
            '<div class="dr-mx-cell dr-mx-grand" style="color:' + (synGrand >= 0 ? 'var(--positive)' : 'var(--negative)') + ';">' + fmt(synGrand) + '</div>' +
        '</div>';

        finalScreen.style.display = 'block';
        finalScreen.innerHTML = (
            '<div class="dr-fin-wrap">' +
                '<div class="dr-fin-rank-block">' +
                    '<div class="dr-fin-rank-label">ОЦЕНКА ДРАФТА</div>' +
                    '<div class="dr-fin-rank-letter" id="dr-fin-letter" style="color:' + rankColor + ';">' + rank + '</div>' +
                    '<div class="dr-fin-score" id="dr-fin-score" style="color:' + rankColor + ';">0</div>' +
                    '<div class="dr-fin-desc">' + rankDesc + '</div>' +
                    (isRecord ? '<div class="dr-fin-record">Новый рекорд</div>' : '') +
                '</div>' +
                '<div class="dr-fin-block">' +
                    '<div class="dr-fin-block-title">МАТРИЦА ПРЕИМУЩЕСТВА</div>' +
                    '<div class="dr-fin-block-sub">наши герои × вражеские</div>' +
                    '<div class="dr-mx-grid">' +
                        '<div class="dr-mx-row dr-mx-row-head">' + muHeader + '</div>' +
                        muRows +
                        muColRow +
                    '</div>' +
                '</div>' +
                '<div class="dr-fin-block">' +
                    '<div class="dr-fin-block-title">МАТРИЦА СИНЕРГИИ</div>' +
                    '<div class="dr-fin-block-sub">наши герои между собой</div>' +
                    '<div class="dr-mx-grid">' +
                        '<div class="dr-mx-row dr-mx-row-head">' + synHeader + '</div>' +
                        synRows +
                        synColRow +
                    '</div>' +
                '</div>' +
                '<button class="dr-fin-btn" onclick="loadDrafterMatch()">↻  НОВЫЙ МАТЧ</button>' +
            '</div>'
        );

        var letterEl = document.getElementById('dr-fin-letter');
        gsap.fromTo(letterEl,
            {scale: 0.2, opacity: 0},
            {scale: 1, opacity: 1, duration: 0.7, ease: 'back.out(1.6)', delay: 0.15});

        var scoreEl = document.getElementById('dr-fin-score');
        var sCount = {v: 0};
        gsap.to(sCount, {
            v: total, duration: 1.1, ease: 'power2.out', delay: 0.45,
            onUpdate: function() { scoreEl.textContent = Math.round(sCount.v); }
        });

        var dataCells = finalScreen.querySelectorAll('.dr-mx-data');
        gsap.fromTo(dataCells,
            {opacity: 0, scale: 0.85},
            {
                opacity: 1, scale: 1, duration: 0.32,
                stagger: { each: 0.022, from: 'start' },
                ease: 'power2.out', delay: 0.7
            });

        var staggerEls = Array.from(finalScreen.querySelectorAll(
            '.dr-fin-rank-label, .dr-fin-desc, .dr-fin-record, .dr-fin-block-title, .dr-fin-block-sub, ' +
            '.dr-mx-row-head .dr-mx-head, .dr-mx-row .dr-mx-head, .dr-mx-rowsum, ' +
            '.dr-mx-row-tot .dr-mx-cell, .dr-fin-btn'
        ));
        gsap.fromTo(staggerEls,
            {opacity: 0, y: 6},
            {opacity: 1, y: 0, duration: 0.32, stagger: 0.025, ease: 'power2.out', delay: 0.1});
    }

    (async function runFlow() {
        await playConfront();
        if (_skip) return;
        await playSynergy();
        if (_skip) return;
        var sb = document.getElementById('dr-skip-btn');
        if (sb) sb.remove();
        showFinal();
    })();
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


// ========== TEAMMATES ==========
//
// Логика страницы "Поиск тиммейтов": лента, профиль, заявки, отзывы.
// Использует существующие apiFetch / USER_TOKEN / showToast / switchPage и
// существующие хелперы window.dotaHeroIds / window.dotaHeroIdToName /
// window.getHeroIconUrlByName / window.openHeroesCatalog.
// Ничего из существующего кода не модифицирует.

(function () {
    var TM_API = (typeof window.API_BASE_URL === 'string' && window.API_BASE_URL) || '/api';

    var TM_RANKS = ['Рекрут','Страж','Рыцарь','Герой','Легенда','Властелин','Божество','Титан'];
    var TM_MODE_LABELS = { ranked: 'Рейтинговая', normal: 'Обычная', turbo: 'Турбо' };
    // Ключ `stomp` остался от прошлой версии («Бущу»). Семантика изменилась
    // на «Под пивом» (chill) — данные старых юзеров не теряем, мигрировать
    // ключ не нужно, меняем только display-label.
    var TM_MOOD_LABELS = { win: 'На победу', fun: 'Фанюсь', stomp: 'Под пивом' };
    var TM_POSITIVE_TAGS = ['Бустер','Душа компании','Командный','No tilted','1x9'];
    var TM_NEGATIVE_TAGS = ['Токсик','Фидер','AFK','Фотограф','Агент Габена'];

    var _tm = {
        myProfile: null,
        filters: {
            ranks: [],          // мультивыбор как positions
            positions: [],
            game_modes: [],
            microphone: false,
            discord: false,
        },
        filtersOpen: false,                   // collapsed by default
        feedCursor: null,
        feedLoading: false,
        favoriteHeroes: [],
        currentTab: 'feed',
        reviewRequestId: null,
        reviewTargetUserId: null,
        reviewSelectedTags: [],
        feedItems: [],
        previewMode: false,
        pollTimer: null,

        // ── Requests sub-tab state (внутри "Мой профиль") ────────────
        requestsTab: 'incoming',
        requestsData:    { incoming: [], outgoing: [], history: [] },
        requestsLoading: { incoming: false, outgoing: false, history: false },
        historyCursor: null,

        // ── Party-finder («Лобби») ───────────────────────────────────
        // lobbies — массив {lobby_id, host_id, party_size, mode, status,
        //                   rank_filter, needed_positions, host_position,
        //                   expires_at, slots: [{position, user, joined_at}]}
        lobbies: [],
        lobbiesLoading: false,
        // Состояние формы создания. Обнуляется при tmOpenLobbyForm.
        lobbyForm: null,
    };

    var _TM_POLL_INTERVAL_MS = 30000;  // 30 секунд между авто-обновлениями

    // Tier 1-8: Рекрут=1 … Титан=8.
    function _tmRankTier(rank) {
        var i = TM_RANKS.indexOf(rank);
        return i >= 0 ? i + 1 : 0;
    }

    // Реальные иконки рангов из проекта — /rank_icons/medal_N.png (N=1..8).
    // Размер задаётся CSS-классом (.tm-rank-icon / --sm / --xs).
    function _tmRankIconImg(rank, modifier) {
        var tier = _tmRankTier(rank);
        if (!tier) return '';
        var cls = 'tm-rank-icon' + (modifier ? ' ' + modifier : '');
        return '<img class="' + cls + '" src="/rank_icons/medal_' + tier + '.png" ' +
            'alt="' + _tmEsc(rank || ('Тир ' + tier)) + '" ' +
            'onerror="this.style.display=\'none\'">';
    }

    function _tmPosIcon(p) { return '/images/positions/pos_' + p + '.png'; }
    function _tmEsc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, function (ch) {
            return ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' })[ch];
        });
    }
    function _tmFormatHours(h) {
        if (h == null || isNaN(h)) return '';
        var n = Math.max(0, parseInt(h, 10) || 0);
        // 1500 → "1 500", 12345 → "12 345" — узкий пробел для группировки тысяч.
        return n.toLocaleString('ru-RU').replace(/ /g, ' ');
    }
    function _tmHeroIconById(id) {
        var name = (window.dotaHeroIdToName || {})[id];
        if (!name) return { name: '', url: '' };
        var url = window.getHeroIconUrlByName ? window.getHeroIconUrlByName(name) : '';
        return { name: name, url: url };
    }
    function _tmGetToken() { return (typeof USER_TOKEN === 'string' && USER_TOKEN) ? USER_TOKEN : ''; }

    // ── Telegram identity helpers ──────────────────────────────────────
    function _tmDisplayName(p) {
        if (!p) return '';
        var first = (p.first_name || '').trim();
        var last  = (p.last_name  || '').trim();
        var full  = (first + ' ' + last).trim();
        if (full) return full;
        if (p.username) return '@' + p.username;
        return 'Игрок ' + (p.user_id || '');
    }
    function _tmAvatarInitial(p) {
        var src = (p && (p.first_name || p.username || '')).trim();
        var ch = src.charAt(0);
        return ch ? ch.toUpperCase() : '·';
    }
    // Авотарка как в существующем _renderAvatar профиля: <img> при наличии
    // photo_url, иначе круг с инициалом на --bg-elevated.
    function _tmAvatarHtml(p, modifier) {
        var cls = 'tm-player-avatar' + (modifier ? ' ' + modifier : '');
        if (p && p.photo_url) {
            return '<div class="' + cls + '">' +
                '<img src="' + _tmEsc(p.photo_url) + '" alt="" ' +
                'onerror="var w=this.parentNode;w.classList.add(\'tm-player-avatar--fallback\');w.textContent=\'' +
                _tmEsc(_tmAvatarInitial(p)) + '\';">' +
            '</div>';
        }
        return '<div class="' + cls + ' tm-player-avatar--fallback">' +
            _tmEsc(_tmAvatarInitial(p)) +
        '</div>';
    }

    // ── Entry point from home widget ────────────────────────────────────
    // Используется deep-link обработчиком (?tm_incoming=1 из push'а бота)
    // и потенциально другими внешними entry-point'ами. Сам init теперь
    // вызывается из switchPage('teammates') — здесь только подсвечиваем
    // nav-item, потому что event у нас нет.
    window.goToTeammates = function () {
        switchPage('teammates');
        var navItems = document.querySelectorAll('.nav-item');
        if (navItems[1]) navItems[1].classList.add('active');
    };

    function initTeammatesPage() {
        // Очистка устаревшего currentTab='profile' из старых сессий (профиль
        // теперь sheet, не tab) — иначе setTeammatesTab сразу его перехватит
        // и откроет sheet при каждом заходе.
        if (_tm.currentTab === 'profile') _tm.currentTab = 'feed';
        setTeammatesTab(_tm.currentTab || 'feed');
        renderFilters();
        // Параллельно: профиль (для кнопки поиска и формы) + лента + входящие.
        loadMyProfile().then(function (p) {
            _tm.myProfile = p;
            _tm.favoriteHeroes = (p && Array.isArray(p.favorite_heroes)) ? p.favorite_heroes.slice() : [];
            renderSearchCta();
            renderProfileForm();
            // Avatar-btn в header'е: photo_url появляется только после
            // loadMyProfile, поэтому update делаем именно здесь.
            _tmUpdateProfileBtnAvatar();
            // Если профиль уже есть — показываем preview, иначе остаёмся на форме.
            if (p && p.rank) {
                tmShowProfilePreview();
            } else {
                tmShowProfileForm();
            }
        }).catch(function (e) { console.warn('[tm] loadMyProfile:', e); });
        loadFeed(true);
        loadLobbies();
        loadRequestsForTab(_tm.requestsTab);
        // Outgoing-список нужен ленте для cross-check «уже отправил ли я этому?».
        // Без этого после reload кнопка «Позвать» показывалась снова, юзер
        // тапал → 409 → toast «Запрос уже отправлен» → confusing UX. Грузим
        // в фоне даже если активная вкладка не outgoing — payload маленький.
        if (_tm.requestsTab !== 'outgoing') loadOutgoing();
        // Стартуем авто-обновление активной вкладки каждые 30 секунд.
        _tmStartPolling();
        // Включаем pulse на «?» если юзер первый раз в разделе.
        _tmInitHelpPulse();
    }

    // Экспортим init на window — switchPage снаружи IIFE вызывает его при
    // заходе на страницу через bottom-nav (см. switchPage case 'teammates').
    // Раньше init работал ТОЛЬКО при заходе через goToTeammates с виджета
    // главной, а tab-bar просто менял .active без подгрузки данных →
    // профиль/фильтры/CTA «Искать пати» оставались в пустом стейте.
    window._tmInitPage = initTeammatesPage;

    // ── Help-sheet «Как это работает» ─────────────────────────────────
    // localStorage-флаг ставится либо при первом тапе (юзер сам нашёл),
    // либо после полного цикла pulse-анимации (увидел и пропустил —
    // повторно не дёргаем).

    function _tmInitHelpPulse() {
        var btn = document.getElementById('tm-help-btn');
        if (!btn) return;
        var seen = false;
        try { seen = localStorage.getItem('tm_help_seen') === '1'; } catch (e) {}
        if (seen) return;
        btn.classList.add('tm-help-btn--pulse');
        // После 3-х циклов animation (CSS: animation: ... 3) последняя
        // итерация генерирует animationend. Тогда фиксируем «показано».
        var onEnd = function (ev) {
            // CSS на ::before-псевдо — animationend всплывёт от элемента
            // владельца псевдо (button). Игнорируем чужие анимации.
            if (ev && ev.animationName !== 'tmHelpPulse') return;
            btn.removeEventListener('animationend', onEnd);
            btn.classList.remove('tm-help-btn--pulse');
            try { localStorage.setItem('tm_help_seen', '1'); } catch (e) {}
        };
        btn.addEventListener('animationend', onEnd);
    }

    // System back-button handling: при открытии help-sheet делаем pushState,
    // на popstate (Android-system-back, iOS swipe-back, Telegram BackButton)
    // закрываем шторку, не выкидывая юзера из мини-аппа целиком. Флаг и
    // listener отдельные, чтобы избежать рекурсии: tmCloseHelp снимает
    // listener ПЕРЕД history.back(), на popstate listener тоже снимается
    // первым делом.
    var _tmHelpHistoryActive = false;

    function _tmDoCloseHelpVisual() {
        var sheet = document.getElementById('tm-help-sheet');
        if (!sheet) return;
        sheet.classList.remove('tm-help-sheet--open');
        sheet.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        var onEnd = function () {
            sheet.removeEventListener('transitionend', onEnd);
            if (!sheet.classList.contains('tm-help-sheet--open')) {
                sheet.hidden = true;
            }
        };
        sheet.addEventListener('transitionend', onEnd);
    }

    function _tmHandleHelpPopstate() {
        window.removeEventListener('popstate', _tmHandleHelpPopstate);
        _tmHelpHistoryActive = false;
        _tmDoCloseHelpVisual();
    }

    window.tmOpenHelp = function () {
        var sheet = document.getElementById('tm-help-sheet');
        if (!sheet) return;
        // Сначала снимаем hidden (display:none блокирует transition), затем
        // следующим кадром добавляем --open чтобы slide-in реально проиграл.
        sheet.hidden = false;
        sheet.setAttribute('aria-hidden', 'false');
        // Force reflow перед добавлением класса — иначе браузер
        // схлопнет «display:none → translateX(0)» в одно состояние.
        // eslint-disable-next-line no-unused-expressions
        sheet.offsetHeight;
        sheet.classList.add('tm-help-sheet--open');
        document.body.style.overflow = 'hidden';
        // Регистрируем «фейковую» history-точку для перехвата system-back.
        // Без неё system-back на Android закрывает весь мини-апп.
        if (!_tmHelpHistoryActive) {
            try {
                history.pushState({ tmHelp: true }, '');
                _tmHelpHistoryActive = true;
                window.addEventListener('popstate', _tmHandleHelpPopstate);
            } catch (e) {
                // history API может быть запрещён в некоторых embedded-кейсах —
                // просто игнорим, fallback на header back-button останется.
            }
        }
        // Юзер сам нашёл и тапнул → pulse больше не нужен никогда.
        var btn = document.getElementById('tm-help-btn');
        if (btn) btn.classList.remove('tm-help-btn--pulse');
        try { localStorage.setItem('tm_help_seen', '1'); } catch (e) {}
    };

    window.tmCloseHelp = function () {
        // Если зашли через pushState — корректно откатываем history-точку,
        // ИНАЧЕ при следующем system-back юзер увидит «пустой» popstate
        // и улетит из мини-аппа.
        if (_tmHelpHistoryActive) {
            window.removeEventListener('popstate', _tmHandleHelpPopstate);
            _tmHelpHistoryActive = false;
            try { history.back(); } catch (e) {}
        }
        _tmDoCloseHelpVisual();
    };

    // ── Profile-sheet ───────────────────────────────────────────────
    // Профиль (форма + запросы + история) переехал из tab'а в overlay-sheet.
    // Открывается по avatar-btn в header'е. Та же history-механика что
    // help-sheet — system-back закрывает шторку, не выкидывает из миниапа.
    var _tmProfileHistoryActive = false;

    function _tmDoCloseProfileSheetVisual() {
        var sheet = document.getElementById('tm-profile-sheet');
        if (!sheet) return;
        sheet.classList.remove('tm-help-sheet--open');
        sheet.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        var onEnd = function () {
            sheet.removeEventListener('transitionend', onEnd);
            if (!sheet.classList.contains('tm-help-sheet--open')) {
                sheet.hidden = true;
            }
        };
        sheet.addEventListener('transitionend', onEnd);
    }

    function _tmHandleProfilePopstate() {
        window.removeEventListener('popstate', _tmHandleProfilePopstate);
        _tmProfileHistoryActive = false;
        _tmDoCloseProfileSheetVisual();
    }

    window.tmOpenProfileSheet = function () {
        var sheet = document.getElementById('tm-profile-sheet');
        if (!sheet) return;
        sheet.hidden = false;
        sheet.setAttribute('aria-hidden', 'false');
        // eslint-disable-next-line no-unused-expressions
        sheet.offsetHeight;
        sheet.classList.add('tm-help-sheet--open');
        document.body.style.overflow = 'hidden';
        if (!_tmProfileHistoryActive) {
            try {
                history.pushState({ tmProfile: true }, '');
                _tmProfileHistoryActive = true;
                window.addEventListener('popstate', _tmHandleProfilePopstate);
            } catch (e) { /* history blocked in some embeds */ }
        }
    };

    window.tmCloseProfileSheet = function () {
        if (_tmProfileHistoryActive) {
            window.removeEventListener('popstate', _tmHandleProfilePopstate);
            _tmProfileHistoryActive = false;
            try { history.back(); } catch (e) {}
        }
        _tmDoCloseProfileSheetVisual();
    };

    // Avatar-кнопка в header'е: после loadMyProfile подставляем photo_url
    // если есть. Иначе остаётся ph-user fallback из HTML. Вызывается из
    // initTeammatesPage после loadMyProfile (см. ниже).
    function _tmUpdateProfileBtnAvatar() {
        var btn = document.getElementById('tm-profile-btn');
        if (!btn) return;
        var p = _tm.myProfile;
        var url = p && p.photo_url;
        if (!url) {
            btn.classList.remove('tm-profile-btn--has-photo');
            return;
        }
        // Если <img> уже стоит — обновим src. Иначе вставим.
        var img = btn.querySelector('img');
        if (img) {
            if (img.src !== url) img.src = url;
        } else {
            img = document.createElement('img');
            img.src = url;
            img.alt = '';
            img.onerror = function () {
                btn.classList.remove('tm-profile-btn--has-photo');
                if (img.parentNode) img.parentNode.removeChild(img);
            };
            btn.appendChild(img);
        }
        btn.classList.add('tm-profile-btn--has-photo');
    }

    // ── Auto-poll lifecycle ────────────────────────────────────────────
    // Останавливать polling при уходе со страницы тиммейтов мы НЕ через
    // wrap switchPage (хрупко) — а через self-check в каждом tick'е:
    // если page-teammates не active, тик сам себя глушит. Худший случай —
    // один лишний холостой тик после навигации, дальше тишина.

    function _tmIsPageActive() {
        var p = document.getElementById('page-teammates');
        return !!(p && p.classList.contains('active'));
    }

    function _tmPollTick() {
        if (!_tmIsPageActive()) {
            _tmStopPolling();
            return;
        }
        // Дуо: обновляем ленту игроков (без лобби — те живут на своей вкладке).
        if (_tm.currentTab === 'feed') {
            _tmTriggerRefresh('feed');
        }
        // Лобби: обновляем список лобби (без player-cards).
        else if (_tm.currentTab === 'lobby') {
            _tmTriggerRefresh('lobby');
        }
        // Профиль-sheet открыт: обновляем requests (если на incoming/outgoing —
        // history сама-обновляется только на manual refresh, иначе ломалась
        // бы пагинация прямо во время просмотра).
        if (_tmIsProfileSheetOpen() &&
            (_tm.requestsTab === 'incoming' || _tm.requestsTab === 'outgoing')) {
            _tmTriggerRefresh('requests');
        }
    }

    function _tmIsProfileSheetOpen() {
        var sheet = document.getElementById('tm-profile-sheet');
        return !!(sheet && sheet.classList.contains('tm-help-sheet--open'));
    }

    function _tmStartPolling() {
        _tmStopPolling();
        _tm.pollTimer = setInterval(_tmPollTick, _TM_POLL_INTERVAL_MS);
    }

    function _tmStopPolling() {
        if (_tm.pollTimer != null) {
            clearInterval(_tm.pollTimer);
            _tm.pollTimer = null;
        }
    }

    // При возврате приложения в foreground (юзер ушёл в Telegram-чат, увидел
    // push «X принял твой запрос», вернулся в миниап) — мгновенный refresh
    // не дожидаясь следующего 30s-полл-тика. Это закрывает лаг «accepted
    // запрос ещё висит как pending в исходящих». Также обновляем badge на
    // bottom-nav (входящие могли поменяться).
    function _tmHandleVisibilityChange() {
        if (document.visibilityState !== 'visible') return;
        _tmRefreshBadge();
        if (!_tmIsPageActive()) return;
        // Активная вкладка → refresh её основной поток.
        if (_tm.currentTab === 'feed')  _tmTriggerRefresh('feed');
        if (_tm.currentTab === 'lobby') _tmTriggerRefresh('lobby');
        // Если открыт sheet профиля — заодно обновим requests.
        if (_tmIsProfileSheetOpen())    _tmTriggerRefresh('requests');
    }
    document.addEventListener('visibilitychange', _tmHandleVisibilityChange);

    // Общий путь для авто-poll'а и manual-кнопок: крутим иконку, дёргаем
    // соответствующий loader, останавливаем спиннер в finally.
    async function _tmTriggerRefresh(kind) {
        // Сопоставление kind → spinner-button id (для feedback при рефреше).
        var btnId = (
            kind === 'feed'     ? 'tm-feed-refresh'     :
            kind === 'lobby'    ? 'tm-lobby-refresh'    :
            kind === 'requests' ? 'tm-requests-refresh' : null
        );
        var btn = btnId ? document.getElementById(btnId) : null;
        if (btn) btn.classList.add('tm-refresh-btn--spinning');
        try {
            if (kind === 'feed') {
                await loadFeed(true);
            } else if (kind === 'lobby') {
                await loadLobbies();
            } else if (kind === 'requests') {
                await loadRequestsForTab(_tm.requestsTab);
            }
        } finally {
            if (btn) btn.classList.remove('tm-refresh-btn--spinning');
        }
    }

    // Глобальные хендлеры для onclick'ов в HTML. Перезапускаем poll-таймер,
    // чтобы 30s отсчёт пошёл от момента ручного refresh'а — а не лупил
    // auto-call сразу после ручного.
    window.tmRefreshFeed = function () {
        _tmTriggerRefresh('feed');
        if (_tmIsPageActive()) _tmStartPolling();
    };
    window.tmRefreshRequests = function () {
        _tmTriggerRefresh('requests');
        if (_tmIsPageActive()) _tmStartPolling();
    };
    window.initTeammatesPage = initTeammatesPage;

    window.setTeammatesTab = function (tab) {
        // Old 'profile' tab → теперь профиль в overlay-sheet (avatar-btn в
        // header). Если что-то вызывает setTeammatesTab('profile') (deep-link
        // handler, persisted _tm.currentTab от старой сессии) — открываем
        // sheet и остаёмся на 'feed' для tab-bar UI.
        if (tab === 'profile') {
            if (typeof window.tmOpenProfileSheet === 'function') tmOpenProfileSheet();
            tab = 'feed';
        }
        if (tab !== 'feed' && tab !== 'lobby') tab = 'feed';
        _tm.currentTab = tab;

        var tabs = document.querySelectorAll('.tm-tab');
        for (var i = 0; i < tabs.length; i++) {
            tabs[i].classList.toggle('tm-tab--active', tabs[i].getAttribute('data-tm-tab') === tab);
        }
        var pf = document.getElementById('tm-pane-feed');
        var pl = document.getElementById('tm-pane-lobby');
        if (pf) pf.hidden = (tab !== 'feed');
        if (pl) pl.hidden = (tab !== 'lobby');

        // На вкладке Лобби сразу запрашиваем свежий список — юзер пришёл
        // целенаправленно посмотреть/создать лобби.
        if (tab === 'lobby') loadLobbies();
    };

    // ── My profile ──────────────────────────────────────────────────────
    async function loadMyProfile() {
        var token = _tmGetToken();
        if (!token) return null;
        var resp = await apiFetch(TM_API + '/teammates/profile/me?token=' + encodeURIComponent(token));
        if (!resp.ok) return null;
        try { return await resp.json(); } catch (e) { return null; }
    }

    // ── Feed ────────────────────────────────────────────────────────────
    async function loadFeed(reset) {
        if (_tm.feedLoading) return;
        _tm.feedLoading = true;
        if (reset) {
            _tm.feedCursor = null;
            _tm.feedItems = [];
        }
        var listEl = document.getElementById('tm-feed-list');
        if (reset && listEl) listEl.innerHTML = _tmSkeletonList(3);
        try {
            var params = new URLSearchParams();
            params.set('token', _tmGetToken());
            if (_tm.filters.ranks.length) params.set('ranks', _tm.filters.ranks.join(','));
            if (_tm.filters.positions.length) params.set('positions', _tm.filters.positions.join(','));
            if (_tm.filters.game_modes.length) params.set('game_modes', _tm.filters.game_modes.join(','));
            if (_tm.filters.microphone) params.set('microphone', '1');
            if (_tm.filters.discord)    params.set('discord', '1');
            if (_tm.feedCursor) params.set('cursor', String(_tm.feedCursor));
            var resp = await apiFetch(TM_API + '/teammates/feed?' + params.toString());
            if (!resp.ok) {
                if (listEl) listEl.innerHTML = '<div class="tm-feed-empty">Не удалось загрузить ленту</div>';
                return;
            }
            var data = await resp.json();
            var items = (data && data.items) || [];
            _tm.feedItems = reset ? items.slice() : _tm.feedItems.concat(items);
            _tm.feedCursor = data && data.next_cursor;
            renderFeed();
        } finally {
            _tm.feedLoading = false;
        }
    }
    window.tmLoadMore = function () { loadFeed(false); };

    function renderFeed() {
        var list = document.getElementById('tm-feed-list');
        var loadMore = document.getElementById('tm-load-more');
        if (!list) return;
        if (!_tm.feedItems.length) {
            list.innerHTML = _tmFeedEmptyState();
            if (loadMore) loadMore.hidden = true;
            return;
        }
        list.innerHTML = _tm.feedItems.map(_renderPlayerCard).join('');
        if (loadMore) loadMore.hidden = !_tm.feedCursor;
    }

    // Состояние пустой ленты — зависит от профиля и статуса поиска.
    // Один универсальный текст «попробуй сам включить поиск» был ложным
    // в двух из трёх ситуаций: для юзера БЕЗ профиля «включи поиск» бессмыслен,
    // а для юзера С активным поиском это вообще не релевантно.
    function _tmFeedEmptyState() {
        var profile = _tm.myProfile;
        var hasProfile  = !!(profile && profile.rank);
        var isSearching = _tmIsSearchingActive();

        var msg;
        if (!hasProfile) {
            msg = 'Заполни профиль, чтобы видеть других игроков.';
        } else if (!isSearching) {
            msg = 'Сейчас никого нет. Включи поиск — твоя карточка появится в чужих лентах, и ты увидишь, кто ещё ищет тиммейтов.';
        } else {
            msg = 'Никто не подходит под фильтры. Попробуй убрать ограничения — лента сама обновляется каждые 30 секунд.';
        }
        return '<div class="tm-feed-empty">' + _tmEsc(msg) + '</div>';
    }

    // Парсит ISO-строку безопасно: если в строке нет TZ-маркера (нет 'Z',
    // нет '+HH:MM' / '-HH:MM' хвоста), трактуем как UTC. Без этого браузер
    // парсит naive date-time как ЛОКАЛЬНОЕ время — для юзера в МСК сдвиг
    // на -3ч, и search_expires_at кажется уже истёкшим (см. /profile/me на
    // бэке — теперь оно отдаёт «+00:00», но defense-in-depth не повредит,
    // если кто-то добавит другую naive-сериализацию).
    function _tmParseUtcLike(s) {
        if (!s) return NaN;
        if (/Z$|[+\-]\d\d:?\d\d$/.test(s)) return new Date(s).getTime();
        return new Date(s + 'Z').getTime();
    }

    // Single source of truth для «активен ли поиск прямо сейчас». Не доверяем
    // только профильному флагу — бэк может его не успеть погасить, или мы
    // открыли страницу с уже устаревшими данными в кэше.
    function _tmIsSearchingActive() {
        var p = _tm.myProfile;
        if (!p || !p.is_searching || !p.search_expires_at) return false;
        var exp = _tmParseUtcLike(p.search_expires_at);
        return isFinite(exp) && exp > Date.now();
    }

    // Проверка: есть ли у меня pending-запрос к этому user_id?
    // Используется в _renderPlayerCard для cross-check'а после reload.
    function _tmHasOutgoingPending(to_user_id) {
        var list = _tm.requestsData && _tm.requestsData.outgoing;
        if (!Array.isArray(list)) return false;
        for (var i = 0; i < list.length; i++) {
            if (list[i] && list[i].to_user_id === to_user_id) return true;
        }
        return false;
    }

    // Set of user_id'ов, чьи карточки уже были отрисованы в текущей сессии.
    // Нужен чтобы reveal-анимация (.tm-player-card--enter) играла ТОЛЬКО при
    // первом появлении карточки в ленте — иначе каждый poll-тик (30s) будет
    // re-играть animation на всех видимых карточках. Set живёт в _tm, чтобы
    // переживал re-render'ы; чистится при leave-from-page если нужно.
    if (!_tm._seenCardIds) _tm._seenCardIds = Object.create(null);

    function _renderPlayerCard(p, opts) {
        opts = opts || {};

        var avatarHtml = _tmAvatarHtml(p, 'tm-player-avatar--lg');
        var displayName = _tmDisplayName(p);
        var rankIcon = _tmRankIconImg(p.rank, 'tm-rank-icon--xs');

        // Pos icons как inline-spans внутри spec-row (не отдельный блок).
        var posIcons = (p.positions || []).map(function (n) {
            return '<img class="tm-player-pos-icon" src="' + _tmEsc(_tmPosIcon(n)) + '" alt="Поз ' + n + '">';
        }).join('');

        var modesText = (p.game_modes || []).map(function (m) {
            return TM_MODE_LABELS[m] || m;
        }).join(', ');

        // Comms — inline иконки в мета-строке. Mood ОСОЗНАННО исключён:
        // в ленте все ищут «как-то играть», моуд не помогает выбору, а текстуру
        // мета-строки удлиняет. Mood будет на /profile/{id}-deep-link'е.
        var commsBits = [];
        if (p.microphone) commsBits.push('<i class="ph ph-microphone-stage" title="Микрофон" aria-hidden="true"></i>');
        if (p.discord)    commsBits.push('<i class="ph ph-chats-circle" title="Discord" aria-hidden="true"></i>');
        var commsInline = commsBits.length
            ? '<span class="tm-player-comms-inline">' + commsBits.join('') + '</span>'
            : '';

        // Hero-тайлы 32×32. Если избранных героев нет — НЕ показываем
        // пустой ряд (раньше код вставлял пустой div со срывом ритма).
        var heroes = (p.favorite_heroes || []).map(function (id) {
            var info = _tmHeroIconById(id);
            return '<div class="tm-hero-tile" title="' + _tmEsc(info.name) + '">' +
                '<img src="' + _tmEsc(info.url) + '" alt="' + _tmEsc(info.name) + '" onerror="this.style.display=\'none\'">' +
                '</div>';
        }).join('');

        // Tag — счётчик inline в моно-шрифте, без вложенного pill.
        var tags = (p.tags || []).map(function (t) {
            var cls = t.is_positive ? 'tm-tag--positive' : 'tm-tag--negative';
            var countHtml = t.count
                ? '<span class="tm-tag-count">' + t.count + '</span>'
                : '';
            return '<span class="tm-tag ' + cls + '">' + _tmEsc(t.tag) + countHtml + '</span>';
        }).join('');

        // Identity-meta строка: [medal]Divine · 3 500 ч [🎤 💬]
        var metaParts = [];
        if (p.rank) {
            metaParts.push(
                '<span class="tm-player-rank">' + rankIcon +
                '<span class="tm-player-rank-text">' + _tmEsc(p.rank) + '</span></span>'
            );
        }
        if (p.hours != null) {
            metaParts.push('<span class="tm-player-hours"><span class="tm-player-meta-num">' + _tmFormatHours(p.hours) + '</span> ч</span>');
        }
        var metaJoiner = ' <span class="tm-player-meta-dot">·</span> ';

        var metaRow = '';
        if (metaParts.length || commsInline) {
            metaRow = '<div class="tm-player-meta-row">' +
                metaParts.join(metaJoiner) +
                commsInline +
            '</div>';
        }

        // Spec-row: позиции + режимы слитно (одна группа «как играю»),
        // не split-attention left/right. Если оба пусты — секцию не рендерим.
        var specRow = '';
        if (posIcons || modesText) {
            var specParts = [];
            if (posIcons)   specParts.push('<span class="tm-player-positions">' + posIcons + '</span>');
            if (modesText)  specParts.push('<span class="tm-player-modes">' + _tmEsc(modesText) + '</span>');
            specRow = '<div class="tm-player-spec">' +
                specParts.join('<span class="tm-player-spec-sep">·</span>') +
            '</div>';
        }

        // CTA «Позвать» — теперь В identity-row рядом с именем (action proximate
        // to identity), а не в подвале после 5 строк инфо. В preview-режиме —
        // пусто (банер сверху уже объясняет «это превью»).
        //
        // Cross-check с outgoing-pending: если я этому юзеру уже отправил
        // запрос, рендерим кнопку в --sent-стейте сразу. Без этого после
        // reload приложения кнопка показывала «Позвать», тап → 409 → юзер
        // в замешательстве. _tm.requestsData.outgoing грузится в init.
        var ctaHtml;
        if (opts.self) {
            ctaHtml = '<span></span>';   // grid-slot заглушка, чтобы layout не схлопнулся
        } else if (p.user_id && _tmHasOutgoingPending(p.user_id)) {
            ctaHtml = '<button class="tm-player-cta tm-player-cta--sent" disabled>Уже отправлено</button>';
        } else {
            ctaHtml = '<button class="tm-player-cta" onclick="tmSendRequest(' + p.user_id + ', this)">Позвать</button>';
        }

        // Reveal-анимация только для НОВЫХ карточек (первое появление в этой
        // сессии). Иначе на каждом poll-тике лента бы дёргалась.
        var enterCls = '';
        if (p.user_id && !_tm._seenCardIds[p.user_id]) {
            enterCls = ' tm-player-card--enter';
            _tm._seenCardIds[p.user_id] = true;
        }

        return [
            '<article class="tm-player-card' + enterCls + '" data-user-id="' + (p.user_id || '') + '">',
              '<header class="tm-player-head">',
                avatarHtml,
                '<div class="tm-player-id">',
                  '<div class="tm-player-name">' + _tmEsc(displayName) + '</div>',
                  metaRow,
                '</div>',
                ctaHtml,
              '</header>',
              specRow,
              (heroes  ? '<div class="tm-player-heroes">' + heroes + '</div>' : ''),
              (p.about ? '<blockquote class="tm-player-about">' + _tmEsc(p.about) + '</blockquote>' : ''),
              (tags    ? '<div class="tm-tags">' + tags + '</div>' : ''),
            '</article>'
        ].join('');
    }

    window.tmSendRequest = async function (to_user_id, btn) {
        var token = _tmGetToken();
        if (!token) { showToast('Нужна авторизация'); return; }
        if (btn) btn.disabled = true;
        try {
            var resp = await apiFetch(TM_API + '/teammates/request', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token, to_user_id: to_user_id })
            });
            if (resp.status === 409) {
                showToast('Запрос уже отправлен');
                if (btn) _tmMarkCtaSent(btn, 'Уже отправлено');
                return;
            }
            if (resp.status === 429) {
                var errData;
                try { errData = await resp.json(); } catch (e) { errData = null; }
                showToast((errData && errData.detail) || 'Слишком много запросов в ожидании');
                if (btn) btn.disabled = false;
                return;
            }
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            showToast('Запрос отправлен', 'ok');
            if (btn) _tmMarkCtaSent(btn, 'Запрос отправлен');
            // Локально мирорим состояние: чтобы при re-render'е ленты (poll-tick
            // или refresh) кнопка осталась в --sent-state, а не вернулась к
            // «Позвать». Реальный outgoing-список подтянется фоном.
            if (!_tm.requestsData) _tm.requestsData = { incoming: [], outgoing: [], history: [] };
            if (!Array.isArray(_tm.requestsData.outgoing)) _tm.requestsData.outgoing = [];
            _tm.requestsData.outgoing.push({ to_user_id: to_user_id });
            loadOutgoing();
        } catch (e) {
            console.warn('[tm] sendRequest:', e);
            showToast('Не удалось отправить запрос');
            if (btn) btn.disabled = false;
        }
    };

    // Анимированный переход CTA «Позвать» → «Запрос отправлен». Раньше был
    // мгновенный textContent-swap — резкий jump. Теперь короткий fade+scale
    // через CSS-класс .tm-player-cta--just-sent (0.34s), параллельно ставим
    // постоянный --sent для серого цвета. Класс --just-sent снимаем по
    // animationend, чтобы не висел.
    function _tmMarkCtaSent(btn, text) {
        if (!btn) return;
        btn.textContent = text;
        btn.disabled = true;
        btn.classList.add('tm-player-cta--sent', 'tm-player-cta--just-sent');
        var onEnd = function () {
            btn.removeEventListener('animationend', onEnd);
            btn.classList.remove('tm-player-cta--just-sent');
        };
        btn.addEventListener('animationend', onEnd);
    }

    // ── Skeleton-карточка для первого монтирования ленты ──────────────
    // Заменяет «Загрузка…»-текст. Структура зеркалит реальную карточку
    // (avatar | name+meta | CTA сверху, spec ниже), чтобы при появлении
    // данных не было layout-shift'а.
    function _tmSkeletonCard() {
        return [
            '<div class="tm-skeleton-card">',
              '<div class="tm-skeleton-card-head">',
                '<div class="tm-skeleton-avatar"></div>',
                '<div>',
                  '<div class="tm-skeleton-line tm-skeleton-line--name"></div>',
                  '<div class="tm-skeleton-line tm-skeleton-line--meta"></div>',
                '</div>',
                '<div class="tm-skeleton-line tm-skeleton-line--cta"></div>',
              '</div>',
              '<div class="tm-skeleton-line tm-skeleton-line--spec"></div>',
            '</div>',
        ].join('');
    }
    function _tmSkeletonList(count) {
        var n = count || 3;
        var items = [];
        for (var i = 0; i < n; i++) items.push(_tmSkeletonCard());
        return '<div class="tm-skeleton-list">' + items.join('') + '</div>';
    }

    // ── Badge для bottom-nav «Тиммейты» + динамический сабтайтл главной ──
    // Лёгкий global-polling: входящие pending каждые 90s, плюс one-shot на
    // App-load. Юзер видит «есть N запросов» даже если он сейчас на странице
    // Героев / Главной / Драфтере. Реюзит /requests/incoming (нет отдельного
    // count-endpoint'а; пэйлоад мал — payload-overhead приемлем).
    var _TM_BADGE_POLL_MS = 90000;
    async function _tmRefreshBadge() {
        var token = _tmGetToken();
        if (!token) return;
        try {
            var resp = await apiFetch(
                TM_API + '/teammates/requests/incoming?token=' + encodeURIComponent(token)
            );
            if (!resp.ok) return;
            var data = await resp.json();
            var count = Array.isArray(data) ? data.length : 0;
            _tmApplyBadge(count);
            _tmApplyHomeSubtitle(count);
        } catch (e) {
            // Тихо: badge — second-class сигнал, не валим ради него UX.
        }
    }
    function _tmApplyBadge(count) {
        var badge = document.getElementById('nav-tm-badge');
        if (!badge) return;
        if (count > 0) {
            badge.textContent = count > 9 ? '9+' : String(count);
            badge.hidden = false;
        } else {
            badge.hidden = true;
        }
    }
    function _tmApplyHomeSubtitle(count) {
        var sub = document.querySelector('#home-teammates-widget .home-tm-subtitle');
        if (!sub) return;
        if (count > 0) {
            // Простая склонение-логика: 1 запрос / 2-4 запроса / 5+ запросов.
            // Узкий русско-специфичный кейс, не тянем целую i18n-либу.
            var label;
            var mod10  = count % 10;
            var mod100 = count % 100;
            if (mod100 >= 11 && mod100 <= 14)      label = 'запросов';
            else if (mod10 === 1)                  label = 'запрос';
            else if (mod10 >= 2 && mod10 <= 4)     label = 'запроса';
            else                                   label = 'запросов';
            sub.textContent = 'У тебя ' + count + ' входящих ' + label;
        } else {
            sub.textContent = 'Подбери напарника по рангу, позиции и настрою';
        }
    }
    // Глобальный polling. Запускаем один раз при загрузке DOM (с задержкой
    // ~1.5s — даём токену успеть подсосаться) и потом каждые 90s.
    function _tmStartBadgePolling() {
        if (window._tmBadgeTimer) return;
        setTimeout(_tmRefreshBadge, 1500);
        window._tmBadgeTimer = setInterval(_tmRefreshBadge, _TM_BADGE_POLL_MS);
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _tmStartBadgePolling);
    } else {
        _tmStartBadgePolling();
    }

    // ── Filters ─────────────────────────────────────────────────────────
    // Все 4 категории используют ОДИН класс .tm-fchip с тремя content-
    // модификаторами: --icon (квадрат с картинкой), --text (только текст),
    // --mixed (иконка + текст). Формула рамки/фона/active одинаковая.

    var TM_GAME_MODES_ORDER = ['ranked', 'normal', 'turbo'];

    function _tmFchip(opts) {
        // opts: { variant: 'icon'|'text'|'mixed', active, onclick, label, content, title }
        var cls = 'tm-fchip tm-fchip--' + opts.variant + (opts.active ? ' tm-fchip--active' : '');
        var titleAttr = opts.title ? ' title="' + _tmEsc(opts.title) + '"' : '';
        var labelAttr = opts.label ? ' aria-label="' + _tmEsc(opts.label) + '"' : '';
        var pressed   = ' aria-pressed="' + (opts.active ? 'true' : 'false') + '"';
        return '<button type="button" class="' + cls + '"' + titleAttr + labelAttr + pressed +
            ' onclick="' + opts.onclick + '">' +
            opts.content +
        '</button>';
    }

    function renderFilters() {
        // Ранги: мультивыбор — каждый выбранный отмечен independently.
        var rankWrap = document.getElementById('tm-filter-rank');
        if (rankWrap) {
            var rankSet = {};
            for (var rIdx = 0; rIdx < _tm.filters.ranks.length; rIdx++) rankSet[_tm.filters.ranks[rIdx]] = true;
            rankWrap.innerHTML = TM_RANKS.map(function (r, i) {
                var tier = i + 1;
                return _tmFchip({
                    variant: 'icon',
                    active: !!rankSet[r],
                    onclick: 'tmToggleFilterRank(\'' + _tmEsc(r) + '\')',
                    title: r,
                    label: r,
                    content: '<img src="/rank_icons/medal_' + tier + '.png" alt="" onerror="this.style.display=\'none\'">',
                });
            }).join('');
        }
        // Позиции: 5 чипов с иконкой позиции.
        var posWrap = document.getElementById('tm-filter-pos');
        if (posWrap) {
            var posSet = {};
            for (var i = 0; i < _tm.filters.positions.length; i++) posSet[_tm.filters.positions[i]] = true;
            posWrap.innerHTML = [1,2,3,4,5].map(function (n) {
                return _tmFchip({
                    variant: 'icon',
                    active: !!posSet[n],
                    onclick: 'tmToggleFilterPos(' + n + ')',
                    title: 'Позиция ' + n,
                    label: 'Позиция ' + n,
                    content: '<img src="' + _tmPosIcon(n) + '" alt="">',
                });
            }).join('');
        }
        // Режимы: текстовые чипы.
        var modesWrap = document.getElementById('tm-filter-modes');
        if (modesWrap) {
            var modeSet = {};
            for (var j = 0; j < _tm.filters.game_modes.length; j++) modeSet[_tm.filters.game_modes[j]] = true;
            modesWrap.innerHTML = TM_GAME_MODES_ORDER.map(function (m) {
                return _tmFchip({
                    variant: 'text',
                    active: !!modeSet[m],
                    onclick: 'tmToggleFilterMode(\'' + _tmEsc(m) + '\')',
                    content: _tmEsc(TM_MODE_LABELS[m] || m),
                });
            }).join('');
        }
        // Связь: микрофон/discord — иконка + текст.
        var commsWrap = document.getElementById('tm-filter-comms');
        if (commsWrap) {
            commsWrap.innerHTML =
                _tmFchip({
                    variant: 'mixed',
                    active: !!_tm.filters.microphone,
                    onclick: 'tmToggleFilterMic()',
                    content: '<i class="ph ph-microphone-stage" aria-hidden="true"></i>Микрофон',
                }) +
                _tmFchip({
                    variant: 'mixed',
                    active: !!_tm.filters.discord,
                    onclick: 'tmToggleFilterDiscord()',
                    content: '<i class="ph ph-chats-circle" aria-hidden="true"></i>Discord',
                });
        }

        _tmRenderFilterChips();
    }

    // Активные фильтры в свёрнутом баре. Две формы:
    //   kind='icon' — квадратный 24×24 тайл (medal/pos image или phosphor icon).
    //                 Один тайл на каждое выбранное значение (ranks/positions
    //                 показываются по-одному; тап убирает конкретное значение).
    //   kind='text' — длинный pill с текстом + ×. Используется для game_modes
    //                 (одна категория с агрегированным списком).
    function _tmActiveFilterChips() {
        var chips = [];

        // Ranks: один icon-тайл на каждый выбранный ранг — medal_N.png.
        _tm.filters.ranks.forEach(function (r) {
            var tier = TM_RANKS.indexOf(r) + 1;
            if (tier < 1) return;
            chips.push({
                kind: 'icon',
                label: r,
                content: '<img src="/rank_icons/medal_' + tier + '.png" alt="" onerror="this.style.display=\'none\'">',
                onclick: 'tmRemoveFilterValue(event, \'ranks\', \'' + _tmEsc(r) + '\')',
            });
        });

        // Positions: один icon-тайл на каждую выбранную позицию.
        _tm.filters.positions.slice().sort(function (a, b) { return a - b; }).forEach(function (p) {
            chips.push({
                kind: 'icon',
                label: 'Позиция ' + p,
                content: '<img src="' + _tmPosIcon(p) + '" alt="">',
                onclick: 'tmRemoveFilterValue(event, \'positions\', ' + p + ')',
            });
        });

        // Modes: один text-pill на всю категорию (агрегированный список).
        if (_tm.filters.game_modes.length) {
            var modeNames = _tm.filters.game_modes.map(function (m) { return TM_MODE_LABELS[m] || m; }).join(', ');
            chips.push({
                kind: 'text',
                label: modeNames,
                content: _tmEsc(modeNames),
                onclick: 'tmClearFilter(event, \'game_modes\')',
            });
        }

        // Microphone / Discord: icon-only (phosphor 14px).
        if (_tm.filters.microphone) {
            chips.push({
                kind: 'icon',
                label: 'Микрофон',
                content: '<i class="ph ph-microphone" aria-hidden="true"></i>',
                onclick: 'tmClearFilter(event, \'microphone\')',
            });
        }
        if (_tm.filters.discord) {
            chips.push({
                kind: 'icon',
                label: 'Discord',
                content: '<i class="ph ph-discord-logo" aria-hidden="true"></i>',
                onclick: 'tmClearFilter(event, \'discord\')',
            });
        }

        return chips;
    }

    function _tmRenderFilterChips() {
        var chips = _tmActiveFilterChips();
        var hasActive = chips.length > 0;

        var wrap = document.getElementById('tm-filters-active-chips');
        if (wrap) {
            wrap.innerHTML = chips.map(function (c) {
                var cls = 'tm-filter-chip-active tm-filter-chip-active--' + c.kind;
                if (c.kind === 'icon') {
                    return '<button type="button" class="' + cls + '" ' +
                        'onclick="' + c.onclick + '" ' +
                        'title="' + _tmEsc(c.label) + '" ' +
                        'aria-label="Убрать фильтр: ' + _tmEsc(c.label) + '">' +
                        c.content +
                    '</button>';
                }
                // text-вариант: pill с лейблом и × справа
                return '<button type="button" class="' + cls + '" ' +
                    'onclick="' + c.onclick + '" ' +
                    'aria-label="Убрать фильтр: ' + _tmEsc(c.label) + '">' +
                    '<span class="tm-filter-chip-active-label">' + c.content + '</span>' +
                    '<span class="tm-filter-chip-active-x" aria-hidden="true">×</span>' +
                '</button>';
            }).join('');
        }

        var countEl = document.getElementById('tm-filters-toggle-count');
        if (countEl) {
            if (hasActive) {
                countEl.textContent = chips.length;
                countEl.hidden = false;
            } else {
                countEl.hidden = true;
            }
        }

        var resetEl = document.getElementById('tm-filters-reset');
        if (resetEl) resetEl.hidden = !(_tm.filtersOpen && hasActive);

        var grp = document.getElementById('tm-filters-toggle-group');
        if (grp) grp.classList.toggle('tm-filters-toggle-group--active', hasActive);
    }

    window.tmToggleFilters = function (ev) {
        // Игнорируем клики, которые произошли по дочерним интерактивным
        // элементам (× на активных чипах, кнопка «Сбросить»). Они сами
        // обрабатывают свои события и stopPropagation'ят.
        if (ev && ev.target && ev.target.closest) {
            if (ev.target.closest('.tm-filter-chip-active')) return;
            if (ev.target.closest('.tm-filters-reset')) return;
        }
        _tm.filtersOpen = !_tm.filtersOpen;
        var root = document.getElementById('tm-filters');
        var bar  = document.getElementById('tm-filters-bar');
        if (root) root.classList.toggle('tm-filters--open', _tm.filtersOpen);
        if (bar)  bar.setAttribute('aria-expanded', String(_tm.filtersOpen));
        _tmRenderFilterChips();
    };

    // Клавиатурная активация bar'а — он role="button", но не настоящая кнопка.
    window.tmFiltersBarKeydown = function (ev) {
        if (ev.key === 'Enter' || ev.key === ' ') {
            if (ev.target && ev.target.closest && ev.target.closest('.tm-filter-chip-active, .tm-filters-reset')) return;
            ev.preventDefault();
            tmToggleFilters();
        }
    };

    window.tmClearFilter = function (ev, type) {
        if (ev && ev.stopPropagation) ev.stopPropagation();
        if (type === 'ranks')           _tm.filters.ranks = [];
        else if (type === 'positions')  _tm.filters.positions = [];
        else if (type === 'game_modes') _tm.filters.game_modes = [];
        else if (type === 'microphone') _tm.filters.microphone = false;
        else if (type === 'discord')    _tm.filters.discord = false;
        renderFilters();
        loadFeed(true);
    };

    // Точечное удаление ОДНОГО значения из мульти-фильтра (rank или position):
    // тап по конкретному chip-тайлу убирает именно его, остальные остаются.
    window.tmRemoveFilterValue = function (ev, type, value) {
        if (ev && ev.stopPropagation) ev.stopPropagation();
        var arr = _tm.filters[type];
        if (Array.isArray(arr)) {
            var i = arr.indexOf(value);
            if (i >= 0) arr.splice(i, 1);
        }
        renderFilters();
        loadFeed(true);
    };

    window.tmResetFilters = function (ev) {
        if (ev && ev.stopPropagation) ev.stopPropagation();
        _tm.filters.ranks = [];
        _tm.filters.positions = [];
        _tm.filters.game_modes = [];
        _tm.filters.microphone = false;
        _tm.filters.discord = false;
        renderFilters();
        loadFeed(true);
    };

    window.tmToggleFilterRank = function (rank) {
        var i = _tm.filters.ranks.indexOf(rank);
        if (i >= 0) _tm.filters.ranks.splice(i, 1);
        else _tm.filters.ranks.push(rank);
        renderFilters();
        loadFeed(true);
    };
    window.tmToggleFilterPos = function (p) {
        var i = _tm.filters.positions.indexOf(p);
        if (i >= 0) _tm.filters.positions.splice(i, 1);
        else _tm.filters.positions.push(p);
        renderFilters();
        loadFeed(true);
    };
    window.tmToggleFilterMode = function (m) {
        var i = _tm.filters.game_modes.indexOf(m);
        if (i >= 0) _tm.filters.game_modes.splice(i, 1);
        else _tm.filters.game_modes.push(m);
        renderFilters();
        loadFeed(true);
    };
    window.tmToggleFilterMic = function () {
        _tm.filters.microphone = !_tm.filters.microphone;
        renderFilters();
        loadFeed(true);
    };
    window.tmToggleFilterDiscord = function () {
        _tm.filters.discord = !_tm.filters.discord;
        renderFilters();
        loadFeed(true);
    };

    // ── Search toggle ───────────────────────────────────────────────────
    var _tmSearchCountdownTimer = null;

    function renderSearchCta() {
        var btn = document.getElementById('tm-search-cta');
        var label = document.getElementById('tm-search-cta-label');
        if (!btn || !label) return;

        // Stale-фильтр: если bool=true, но expiry прошёл — синхронизируемся
        // на фронте сразу (не ждём следующего fetch профиля).
        if (_tm.myProfile && _tm.myProfile.is_searching && !_tmIsSearchingActive()) {
            _tm.myProfile.is_searching = false;
        }
        var active = _tmIsSearchingActive();
        // Mutually exclusive с лобби: если юзер в активном лобби — поиск
        // дуо запрещён (бэк тоже это enforce'ит). UI делает кнопку disabled
        // и подсказывает почему.
        var inLobby = _tmGetMyLobbyId() != null;

        label.textContent = active ? 'Поиск активен — остановить' : 'Искать пати';
        btn.classList.toggle('tm-search-cta--active', active);
        btn.disabled = inLobby && !active;

        var hint = document.getElementById('tm-search-hint');
        if (hint) {
            if (inLobby && !active) {
                hint.textContent = 'Ты в лобби — выйди, чтобы искать дуо';
            } else if (active) {
                var minLeft = Math.max(0, Math.ceil(
                    (_tmParseUtcLike(_tm.myProfile.search_expires_at) - Date.now()) / 60000
                ));
                hint.textContent = 'Тебя видят другие · ещё ' + _tmFormatRemaining(minLeft);
            } else {
                hint.textContent = '1-на-1 · поиск длится 3 часа';
            }
        }

        // Тикер раз в минуту обновляет hint с убывающим временем. Когда
        // поиск выключен (или истёк) — таймер останавливается.
        _tmStopSearchCountdown();
        if (active) {
            _tmSearchCountdownTimer = setInterval(renderSearchCta, 60000);
        }
    }

    function _tmStopSearchCountdown() {
        if (_tmSearchCountdownTimer) {
            clearInterval(_tmSearchCountdownTimer);
            _tmSearchCountdownTimer = null;
        }
    }

    function _tmFormatRemaining(minutes) {
        if (minutes < 1)  return 'меньше минуты';
        if (minutes < 60) return minutes + ' мин';
        var h = Math.floor(minutes / 60);
        var m = minutes % 60;
        return m === 0 ? (h + ' ч') : (h + ' ч ' + m + ' мин');
    }
    window.tmToggleSearch = async function () {
        var token = _tmGetToken();
        if (!token) { showToast('Нужна авторизация'); return; }
        if (!_tm.myProfile) {
            showToast('Сначала заполни профиль');
            setTeammatesTab('profile');
            return;
        }
        // Используем normalized state (тот же, что и UI показывает) — иначе
        // при stale `is_searching=true` + истёкшем expires_at кликаем
        // search/stop вместо search/start и юзер видит «ничего не произошло».
        var isSearching = _tmIsSearchingActive();
        var url = TM_API + '/teammates/' + (isSearching ? 'search/stop' : 'search/start');
        var resp = await apiFetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token: token })
        });
        if (resp.status === 400) {
            showToast('Сначала заполни профиль');
            setTeammatesTab('profile');
            return;
        }
        if (!resp.ok) { showToast('Не удалось обновить статус'); return; }

        if (isSearching) {
            // Выключаем — гасим оба поля локально.
            _tm.myProfile.is_searching = false;
        } else {
            // Включаем — НУЖНО локально проставить и expires_at, иначе
            // renderSearchCta увидит is_searching=true + expiry=null и опять
            // сбросит флаг через нормализацию. Зеркалим backend-логику now+3h.
            _tm.myProfile.is_searching = true;
            _tm.myProfile.search_expires_at = new Date(
                Date.now() + 3 * 60 * 60 * 1000
            ).toISOString();
        }
        renderSearchCta();
        loadFeed(true);
    };

    // ── Profile preview / form switch ───────────────────────────────────
    window.tmShowProfilePreview = function () {
        _tm.previewMode = true;
        var preview = document.getElementById('tm-profile-preview');
        var form = document.getElementById('tm-profile-form');
        if (preview) preview.hidden = false;
        if (form) form.hidden = true;
        _tmRenderProfilePreview(_tm.myProfile);
    };
    window.tmShowProfileForm = function () {
        _tm.previewMode = false;
        var preview = document.getElementById('tm-profile-preview');
        var form = document.getElementById('tm-profile-form');
        if (preview) preview.hidden = true;
        if (form) form.hidden = false;
    };
    window.tmEditProfile = function () { tmShowProfileForm(); };

    function _tmRenderProfilePreview(profile) {
        var holder = document.getElementById('tm-preview-card');
        if (!holder) return;
        if (!profile || !profile.rank) {
            holder.innerHTML = '<div class="tm-feed-empty">Профиль ещё не заполнен</div>';
            return;
        }
        holder.innerHTML = _renderPlayerCard(profile, { self: true });
    }

    // ── Profile form ────────────────────────────────────────────────────
    function renderProfileForm() {
        var p = _tm.myProfile || {};

        var rankWrap = document.getElementById('tm-rank-scroll');
        if (rankWrap) {
            rankWrap.innerHTML = TM_RANKS.map(function (r) {
                var cls = (r === p.rank) ? 'tm-rank-card tm-rank-card--active' : 'tm-rank-card';
                return '<button type="button" class="' + cls + '" data-rank="' + _tmEsc(r) + '" onclick="tmSelectRank(\'' + _tmEsc(r) + '\')">' +
                    _tmRankIconImg(r, 'tm-rank-icon--md') +
                    '<span class="tm-rank-card-label">' + _tmEsc(r) + '</span>' +
                '</button>';
            }).join('');
        }

        var hoursInput = document.getElementById('tm-hours-input');
        if (hoursInput) hoursInput.value = (p.hours != null) ? p.hours : '';

        var posBtns = document.querySelectorAll('.tm-position-btn');
        var posSet = {};
        (p.positions || []).forEach(function (n) { posSet[n] = true; });
        for (var i = 0; i < posBtns.length; i++) {
            var n = parseInt(posBtns[i].getAttribute('data-pos'), 10);
            posBtns[i].classList.toggle('tm-position-btn--active', !!posSet[n]);
        }

        var modeBtns = document.querySelectorAll('.tm-mode-btn');
        var modeSet = {};
        (p.game_modes || []).forEach(function (m) { modeSet[m] = true; });
        for (var j = 0; j < modeBtns.length; j++) {
            var m = modeBtns[j].getAttribute('data-mode');
            modeBtns[j].classList.toggle('tm-mode-btn--active', !!modeSet[m]);
        }

        var micT = document.getElementById('tm-mic-toggle');
        var dcT = document.getElementById('tm-discord-toggle');
        if (micT) { micT.classList.toggle('tm-toggle--on', !!p.microphone); micT.setAttribute('aria-pressed', String(!!p.microphone)); }
        if (dcT)  { dcT.classList.toggle('tm-toggle--on', !!p.discord);     dcT.setAttribute('aria-pressed', String(!!p.discord)); }

        var moodBtns = document.querySelectorAll('.tm-mood-btn');
        for (var k = 0; k < moodBtns.length; k++) {
            moodBtns[k].classList.toggle('tm-mood-btn--active', moodBtns[k].getAttribute('data-mood') === p.mood);
        }

        renderHeroSlots();

        var ta = document.getElementById('tm-about-input');
        if (ta) { ta.value = p.about || ''; tmUpdateAboutCounter(); }
    }

    window.tmSelectRank = function (r) {
        if (!_tm.myProfile) _tm.myProfile = {};
        _tm.myProfile.rank = r;
        var cards = document.querySelectorAll('.tm-rank-card');
        for (var i = 0; i < cards.length; i++) {
            cards[i].classList.toggle('tm-rank-card--active', cards[i].getAttribute('data-rank') === r);
        }
    };

    window.tmTogglePos = function (_p, btn) { btn.classList.toggle('tm-position-btn--active'); };
    window.tmToggleMode = function (_m, btn) { btn.classList.toggle('tm-mode-btn--active'); };
    window.tmToggleMic = function () {
        var t = document.getElementById('tm-mic-toggle'); if (!t) return;
        t.classList.toggle('tm-toggle--on');
        t.setAttribute('aria-pressed', String(t.classList.contains('tm-toggle--on')));
    };
    window.tmToggleDiscord = function () {
        var t = document.getElementById('tm-discord-toggle'); if (!t) return;
        t.classList.toggle('tm-toggle--on');
        t.setAttribute('aria-pressed', String(t.classList.contains('tm-toggle--on')));
    };
    window.tmSetMood = function (m) {
        var btns = document.querySelectorAll('.tm-mood-btn');
        for (var i = 0; i < btns.length; i++) {
            btns[i].classList.toggle('tm-mood-btn--active', btns[i].getAttribute('data-mood') === m);
        }
    };

    window.tmUpdateAboutCounter = function () {
        var ta = document.getElementById('tm-about-input');
        var counter = document.getElementById('tm-about-counter');
        if (!ta || !counter) return;
        var len = (ta.value || '').length;
        counter.textContent = len + ' / 200';
    };

    function renderHeroSlots() {
        var wrap = document.getElementById('tm-hero-slots');
        if (!wrap) return;
        var html = '';
        for (var i = 0; i < 3; i++) {
            var id = _tm.favoriteHeroes[i];
            if (id) {
                var info = _tmHeroIconById(id);
                html += '<button type="button" class="tm-hero-slot tm-hero-slot--filled" onclick="tmRemoveHero(' + i + ')" title="' + _tmEsc(info.name) + '">' +
                    '<img class="tm-hero-slot-img" src="' + _tmEsc(info.url) + '" alt="' + _tmEsc(info.name) + '" onerror="this.style.display=\'none\'">' +
                    '<span class="tm-hero-slot-x">×</span>' +
                '</button>';
            } else {
                html += '<button type="button" class="tm-hero-slot tm-hero-slot--empty" onclick="tmOpenHeroPicker()" aria-label="Добавить героя">' +
                    '<i class="ph ph-plus" aria-hidden="true"></i>' +
                '</button>';
            }
        }
        wrap.innerHTML = html;
    }
    window.tmRemoveHero = function (idx) {
        _tm.favoriteHeroes.splice(idx, 1);
        renderHeroSlots();
    };
    // Reuse существующего каталога героев — никакого собственного picker'а.
    // Стратегия: вешаем capture-phase listener на оверлей, перехватываем клик
    // по тайлу до того, как сработает дефолтный обработчик (matchup/drafter),
    // и подбираем героя в фавориты. MutationObserver на attribute=hidden чистит
    // listener при закрытии каталога любым способом (X, backdrop, ESC).
    window.tmOpenHeroPicker = function () {
        if (_tm.favoriteHeroes.length >= 3) { showToast('Уже выбрано 3 героя'); return; }
        if (typeof window.openHeroesCatalog !== 'function') {
            console.warn('[tm] openHeroesCatalog недоступен');
            return;
        }
        var overlay = document.getElementById('heroes-catalog-overlay');
        if (!overlay) return;

        var mo;
        function cleanup() {
            overlay.removeEventListener('click', interceptor, true);
            if (mo) { mo.disconnect(); mo = null; }
        }
        function interceptor(e) {
            var t = e.target;
            var tile = t && t.closest ? t.closest('.heroes-catalog-tile') : null;
            if (!tile) return;
            var name = tile.getAttribute('data-hero-name');
            if (!name) return;
            var id = (window.dotaHeroIds || {})[name];
            if (!id) return;
            // Гасим bubble-phase handler оригинального каталога.
            e.stopPropagation();
            if (typeof e.preventDefault === 'function') e.preventDefault();
            if (_tm.favoriteHeroes.indexOf(id) === -1 && _tm.favoriteHeroes.length < 3) {
                _tm.favoriteHeroes.push(id);
                renderHeroSlots();
            }
            cleanup();
            if (typeof window.closeHeroesCatalog === 'function') {
                window.closeHeroesCatalog();
            }
        }

        overlay.addEventListener('click', interceptor, true);
        // Каталог скрывается через overlay.hidden=true — ловим этот переход.
        if (typeof MutationObserver === 'function') {
            mo = new MutationObserver(function () {
                if (overlay.hidden) cleanup();
            });
            mo.observe(overlay, { attributes: true, attributeFilter: ['hidden'] });
        }

        window.openHeroesCatalog();
    };

    window.tmSaveProfile = async function () {
        var token = _tmGetToken();
        if (!token) { showToast('Нужна авторизация'); return; }

        var rankActive = document.querySelector('.tm-rank-card--active');
        var rank = rankActive ? rankActive.getAttribute('data-rank') : '';
        if (!rank) { showToast('Выбери ранг'); return; }

        var hoursInput = document.getElementById('tm-hours-input');
        var hours = parseInt((hoursInput && hoursInput.value) || '0', 10);
        if (!(hours >= 0)) { showToast('Укажи часы корректно'); return; }

        var posBtns = document.querySelectorAll('.tm-position-btn--active');
        var positions = [];
        for (var i = 0; i < posBtns.length; i++) positions.push(parseInt(posBtns[i].getAttribute('data-pos'), 10));
        if (!positions.length) { showToast('Выбери хотя бы одну позицию'); return; }

        var modeBtns = document.querySelectorAll('.tm-mode-btn--active');
        var game_modes = [];
        for (var j = 0; j < modeBtns.length; j++) game_modes.push(modeBtns[j].getAttribute('data-mode'));
        if (!game_modes.length) { showToast('Выбери хотя бы один режим'); return; }

        var micT = document.getElementById('tm-mic-toggle');
        var dcT = document.getElementById('tm-discord-toggle');
        var microphone = !!(micT && micT.classList.contains('tm-toggle--on'));
        var discord    = !!(dcT && dcT.classList.contains('tm-toggle--on'));

        var moodActive = document.querySelector('.tm-mood-btn--active');
        var mood = moodActive ? moodActive.getAttribute('data-mood') : '';
        if (!mood) { showToast('Выбери настрой'); return; }

        var ta = document.getElementById('tm-about-input');
        var about = (ta && ta.value) || '';
        var favorite_heroes = _tm.favoriteHeroes.slice(0, 3);

        var btn = document.getElementById('tm-save-btn');
        if (btn) btn.disabled = true;
        try {
            var resp = await apiFetch(TM_API + '/teammates/profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: token,
                    rank: rank,
                    hours: hours,
                    positions: positions,
                    game_modes: game_modes,
                    microphone: microphone,
                    discord: discord,
                    mood: mood,
                    favorite_heroes: favorite_heroes,
                    about: about
                })
            });
            if (!resp.ok) { showToast('Не удалось сохранить'); return; }
            showToast('Профиль сохранён', 'ok');
            // Сохраняем в локальное состояние, чтобы кнопка поиска корректно обновилась.
            _tm.myProfile = Object.assign({}, _tm.myProfile || {}, {
                rank: rank, hours: hours, positions: positions, game_modes: game_modes,
                microphone: microphone, discord: discord, mood: mood,
                favorite_heroes: favorite_heroes, about: about
            });
            renderSearchCta();
            // После сохранения сразу показываем preview — это и фидбек об успехе,
            // и моментальное превью карточки в ленте.
            tmShowProfilePreview();
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } finally {
            if (btn) btn.disabled = false;
        }
    };

    // ── Requests: incoming / outgoing / history ─────────────────────────
    // Единая модель: три параллельных списка в _tm.requestsData, активная
    // вкладка в _tm.requestsTab. Лоадер пишет в свою ячейку, рендер выбирает
    // нужную по активной вкладке. Render'еры карточек разделены по типу.

    async function loadIncoming() {
        if (_tm.requestsLoading.incoming) return;
        _tm.requestsLoading.incoming = true;
        try {
            var token = _tmGetToken();
            if (!token) return;
            var resp = await apiFetch(TM_API + '/teammates/requests/incoming?token=' + encodeURIComponent(token));
            if (!resp.ok) return;
            var data;
            try { data = await resp.json(); } catch (e) { data = []; }
            _tm.requestsData.incoming = Array.isArray(data) ? data : [];
            _tmUpdateRequestsCounts();
            if (_tm.requestsTab === 'incoming') _tmRenderRequests();
        } finally {
            _tm.requestsLoading.incoming = false;
        }
    }

    async function loadOutgoing() {
        if (_tm.requestsLoading.outgoing) return;
        _tm.requestsLoading.outgoing = true;
        try {
            var token = _tmGetToken();
            if (!token) return;
            var resp = await apiFetch(TM_API + '/teammates/requests/outgoing?token=' + encodeURIComponent(token));
            if (!resp.ok) return;
            var data;
            try { data = await resp.json(); } catch (e) { data = []; }
            _tm.requestsData.outgoing = Array.isArray(data) ? data : [];
            _tmUpdateRequestsCounts();
            if (_tm.requestsTab === 'outgoing') _tmRenderRequests();
        } finally {
            _tm.requestsLoading.outgoing = false;
        }
    }

    async function loadHistory(reset) {
        if (_tm.requestsLoading.history) return;
        _tm.requestsLoading.history = true;
        try {
            var token = _tmGetToken();
            if (!token) return;
            if (reset) {
                _tm.historyCursor = null;
                _tm.requestsData.history = [];
            }
            var params = new URLSearchParams();
            params.set('token', token);
            params.set('limit', '20');
            if (_tm.historyCursor) params.set('cursor', _tm.historyCursor);

            // Load 1-на-1 history (paginated) + лобби history (no pagination,
            // только при reset) параллельно. Сортируем по timestamp DESC.
            var reqPromise = apiFetch(TM_API + '/teammates/requests/history?' + params.toString());
            var lobPromise = reset
                ? apiFetch(TM_API + '/teammates/lobbies/history?token=' + encodeURIComponent(token))
                : Promise.resolve(null);

            var responses = await Promise.all([reqPromise, lobPromise]);
            var reqResp = responses[0];
            var lobResp = responses[1];

            var reqItems = [];
            if (reqResp && reqResp.ok) {
                try {
                    var reqData = await reqResp.json();
                    reqItems = ((reqData && reqData.items) || []).map(function (r) {
                        r._type = 'request';
                        r._sortAt = r.accepted_at;
                        return r;
                    });
                    _tm.historyCursor = reqData && reqData.next_cursor;
                } catch (e) { /* tolerate parse */ }
            }

            var lobItems = [];
            if (lobResp && lobResp.ok) {
                try {
                    var lobData = await lobResp.json();
                    lobItems = ((lobData && lobData.items) || []).map(function (l) {
                        l._type = 'lobby';
                        l._sortAt = l.filled_at;
                        return l;
                    });
                } catch (e) { /* tolerate parse */ }
            }

            var combined;
            if (reset) {
                // Свежая загрузка: оба источника, merge + sort.
                combined = reqItems.concat(lobItems);
            } else {
                // Load-more: лобби-история уже загружена на первой странице,
                // догружаем только requests (с пагинацией). Сохраняем уже
                // показанные элементы.
                combined = _tm.requestsData.history.concat(reqItems);
            }
            // Сортируем по timestamp DESC (последние сверху).
            combined.sort(function (a, b) {
                var aT = a._sortAt ? new Date(a._sortAt).getTime() : 0;
                var bT = b._sortAt ? new Date(b._sortAt).getTime() : 0;
                return bT - aT;
            });
            _tm.requestsData.history = combined;
            if (_tm.requestsTab === 'history') _tmRenderRequests();
        } finally {
            _tm.requestsLoading.history = false;
        }
    }

    async function loadRequestsForTab(tab) {
        if (tab === 'incoming') return loadIncoming();
        if (tab === 'outgoing') return loadOutgoing();
        if (tab === 'history')  return loadHistory(true);
    }

    function _tmUpdateRequestsCounts() {
        var incEl = document.getElementById('tm-rt-count-incoming');
        var outEl = document.getElementById('tm-rt-count-outgoing');
        var inc = _tm.requestsData.incoming.length;
        var out = _tm.requestsData.outgoing.length;
        if (incEl) incEl.textContent = inc ? String(inc) : '';
        if (outEl) outEl.textContent = out ? String(out) : '';
    }

    function _tmRequestsEmptyState(tab) {
        var msg;
        if (tab === 'incoming') {
            msg = 'Никто пока не звал тебя играть. Включи поиск в Ленте, чтобы быть видимым.';
        } else if (tab === 'outgoing') {
            msg = 'Ты пока никому не написал. Найди тиммейта в Ленте.';
        } else {
            msg = 'Здесь появятся игроки, с которыми ты сыграешь через D2Helper.';
        }
        return '<div class="tm-feed-empty">' + msg + '</div>';
    }

    function _tmRenderRequests() {
        var list = document.getElementById('tm-requests-list');
        if (!list) return;
        var tab = _tm.requestsTab;
        var items = _tm.requestsData[tab] || [];
        if (!items.length) {
            list.innerHTML = _tmRequestsEmptyState(tab);
            return;
        }
        var html;
        if (tab === 'incoming')       html = items.map(_renderIncomingItem).join('');
        else if (tab === 'outgoing')  html = items.map(_renderOutgoingItem).join('');
        else /* history */            html = items.map(_renderHistoryItem).join('');
        // Load-more для history (если есть next_cursor).
        if (tab === 'history' && _tm.historyCursor) {
            html += '<button type="button" class="tm-load-more" onclick="tmLoadMoreHistory()">Показать ещё</button>';
        }
        list.innerHTML = html;
    }

    // Общий блок: avatar + name + meta-row. Используется во всех трёх вкладках.
    function _tmRenderRequestHead(p) {
        var avatarHtml = _tmAvatarHtml(p, 'tm-player-avatar--sm');
        var displayName = _tmDisplayName(p);
        var rankIcon = _tmRankIconImg(p.rank, 'tm-rank-icon--xs');
        var meta = [];
        if (p.rank) meta.push('<span class="tm-player-rank">' + rankIcon + '<span class="tm-player-rank-text">' + _tmEsc(p.rank) + '</span></span>');
        if (p.hours != null) meta.push('<span class="tm-player-hours"><span class="tm-player-meta-num">' + _tmFormatHours(p.hours) + '</span> ч</span>');
        if (p.mood) meta.push('<span class="tm-player-meta-mood">' + _tmEsc(TM_MOOD_LABELS[p.mood] || p.mood) + '</span>');
        return '<div class="tm-request-head">' +
            avatarHtml +
            '<div class="tm-player-id">' +
              '<div class="tm-player-name">' + _tmEsc(displayName) + '</div>' +
              (meta.length ? '<div class="tm-player-meta-row">' + meta.join(' <span class="tm-player-meta-dot">·</span> ') + '</div>' : '') +
            '</div>' +
        '</div>';
    }

    function _renderIncomingItem(r) {
        var p = r.profile || {};
        return [
            '<div class="tm-request-item" data-request-id="' + r.request_id + '">',
              _tmRenderRequestHead(p),
              (p.about ? '<div class="tm-player-about">' + _tmEsc(p.about) + '</div>' : ''),
              '<div class="tm-request-actions">',
                '<button type="button" class="tm-incoming-accept" onclick="tmRespondRequest(' + r.request_id + ', true, this)">Принять</button>',
                '<button type="button" class="tm-incoming-decline" onclick="tmRespondRequest(' + r.request_id + ', false, this)">Отклонить</button>',
              '</div>',
            '</div>'
        ].join('');
    }

    function _renderOutgoingItem(r) {
        var p = r.profile || {};
        return [
            '<div class="tm-request-item" data-request-id="' + r.request_id + '">',
              _tmRenderRequestHead(p),
              (p.about ? '<div class="tm-player-about">' + _tmEsc(p.about) + '</div>' : ''),
              '<div class="tm-request-status-row">',
                '<span class="tm-status-pending"><span class="tm-status-pending-dot" aria-hidden="true"></span>Ждём ответа</span>',
                '<button type="button" class="tm-outgoing-cancel" onclick="tmCancelRequest(' + r.request_id + ', this)">Отменить</button>',
              '</div>',
            '</div>'
        ].join('');
    }

    function _renderHistoryItem(item) {
        // Dispatcher: 1-на-1 request vs filled лобби. Тип проставляет loadHistory.
        if (item && item._type === 'lobby') return _renderHistoryLobbyItem(item);
        return _renderHistoryRequestItem(item);
    }

    function _renderHistoryRequestItem(r) {
        var p = r.profile || {};
        var when = _tmRelativeDate(r.accepted_at);
        var otherId = r.other_user_id != null ? r.other_user_id : 'null';
        var actionHtml;
        if (r.my_review_left) {
            actionHtml = '<span class="tm-history-done"><i class="ph ph-check-circle" aria-hidden="true"></i>Отзыв оставлен</span>';
        } else {
            actionHtml = '<button type="button" class="tm-history-review" onclick="tmOpenReview(' + r.request_id + ', ' + otherId + ')">Оценить игрока</button>';
        }
        return [
            '<div class="tm-request-item" data-request-id="' + r.request_id + '">',
              _tmRenderRequestHead(p),
              '<div class="tm-request-status-row">',
                (when ? '<span class="tm-history-when">' + _tmEsc(when) + '</span>' : '<span></span>'),
                actionHtml,
              '</div>',
            '</div>'
        ].join('');
    }

    // Лобби-запись в истории — список @ников как tg://-ссылки. Никаких action-
    // кнопок: бот уже отправил юзеру эти @ники в момент заполнения, юзер может
    // написать в личку напрямую без посредников (см. design brief).
    function _renderHistoryLobbyItem(lobby) {
        var myId = _tm.myProfile && _tm.myProfile.user_id;
        var slots = (lobby.slots || []).slice().sort(function (a, b) {
            return a.position - b.position;
        });
        // Members = все участники КРОМЕ меня (мне зачем мой собственный @ник).
        var otherMembersHtml = slots
            .filter(function (s) { return s.user && s.user.user_id !== myId; })
            .map(function (s) {
                var u = s.user;
                var name = _tmDisplayName(u);
                var uname = (u.username || '').toString().replace(/^@/, '');
                var label = uname ? ('@' + uname) : name;
                return '<a class="tm-history-lobby-member" href="tg://user?id=' + u.user_id + '">' +
                    _tmEsc(label) +
                '</a>';
            }).join(', ');

        var when = _tmRelativeDate(lobby.filled_at);
        var modeLabel = TM_LOBBY_MODE_LABELS[lobby.mode] || lobby.mode;

        return [
            '<div class="tm-request-item tm-request-item--lobby" data-lobby-id="' + lobby.lobby_id + '">',
              '<div class="tm-history-lobby-head">',
                '<i class="ph ph-users-three" aria-hidden="true"></i>',
                '<span class="tm-history-lobby-title">Лобби на ' + lobby.party_size + ' · ' + _tmEsc(modeLabel) + '</span>',
              '</div>',
              (otherMembersHtml
                ? '<div class="tm-history-lobby-members">' + otherMembersHtml + '</div>'
                : ''),
              '<div class="tm-request-status-row">',
                (when ? '<span class="tm-history-when">' + _tmEsc(when) + '</span>' : '<span></span>'),
                '<span></span>',
              '</div>',
            '</div>'
        ].join('');
    }

    // Относительная дата для истории: «3 ч назад», «2 дн. назад», fallback → «15 мая».
    function _tmRelativeDate(iso) {
        if (!iso) return '';
        var d = new Date(iso);
        if (isNaN(d.getTime())) return '';
        var diffMs = Date.now() - d.getTime();
        if (diffMs < 0) diffMs = 0;
        var min = Math.floor(diffMs / 60000);
        var hr  = Math.floor(diffMs / 3600000);
        var day = Math.floor(diffMs / 86400000);
        if (min < 1)  return 'только что';
        if (min < 60) return min + ' мин назад';
        if (hr  < 24) return hr  + ' ч назад';
        if (day < 30) return day + ' дн. назад';
        try {
            return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
        } catch (e) {
            return d.toISOString().slice(0, 10);
        }
    }

    // ── Tab switching + actions ─────────────────────────────────────────

    window.tmSetRequestsTab = function (tab) {
        if (tab !== 'incoming' && tab !== 'outgoing' && tab !== 'history') return;
        _tm.requestsTab = tab;
        var btns = document.querySelectorAll('.tm-requests-tab');
        for (var i = 0; i < btns.length; i++) {
            var isActive = btns[i].getAttribute('data-tm-rt') === tab;
            btns[i].classList.toggle('tm-requests-tab--active', isActive);
            btns[i].setAttribute('aria-selected', String(isActive));
        }
        // Сначала рендерим то, что уже есть (мгновенный UX), потом грузим свежее.
        _tmRenderRequests();
        loadRequestsForTab(tab);
        // Авто-poll-timer резетим, чтобы 30s отсчёт пошёл от свежей загрузки.
        if (_tmIsPageActive()) _tmStartPolling();
    };

    window.tmLoadMoreHistory = function () { loadHistory(false); };

    window.tmRespondRequest = async function (requestId, accept, btn) {
        var token = _tmGetToken();
        if (!token) { showToast('Нужна авторизация'); return; }
        if (btn) btn.disabled = true;
        try {
            var resp = await apiFetch(TM_API + '/teammates/request/respond', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token, request_id: requestId, accept: !!accept })
            });
            if (!resp.ok) { showToast('Не удалось ответить'); return; }
            // Accept — положительное действие (зелёный); decline — отрицательное (красный).
            if (accept) showToast('Запрос принят', 'ok');
            else        showToast('Запрос отклонён');
            // Optimistic: убираем из incoming сразу. Сервер-truth подтянем рефрешем.
            _tm.requestsData.incoming = _tm.requestsData.incoming.filter(function (x) {
                return x.request_id !== requestId;
            });
            _tmUpdateRequestsCounts();
            if (_tm.requestsTab === 'incoming') _tmRenderRequests();
            // Если приняли — history теперь устарела, заставим перезагрузить при следующем входе.
            if (accept) _tm.requestsData.history = [];
        } finally {
            if (btn) btn.disabled = false;
        }
    };

    window.tmCancelRequest = async function (requestId, btn) {
        var token = _tmGetToken();
        if (!token) { showToast('Нужна авторизация'); return; }
        if (btn) btn.disabled = true;
        try {
            var resp = await apiFetch(TM_API + '/teammates/request/cancel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token, request_id: requestId })
            });
            if (!resp.ok) {
                if (resp.status === 409) showToast('Запрос уже не активен');
                else showToast('Не удалось отменить');
                return;
            }
            showToast('Запрос отменён', 'ok');
            _tm.requestsData.outgoing = _tm.requestsData.outgoing.filter(function (x) {
                return x.request_id !== requestId;
            });
            _tmUpdateRequestsCounts();
            if (_tm.requestsTab === 'outgoing') _tmRenderRequests();
        } finally {
            if (btn) btn.disabled = false;
        }
    };

    // ── Review screen ───────────────────────────────────────────────────

    window.tmOpenReview = async function (requestId, targetUserId) {
        if (!requestId) return;
        _tm.reviewRequestId = parseInt(requestId, 10);
        _tm.reviewTargetUserId = targetUserId ? parseInt(targetUserId, 10) : null;
        _tm.reviewSelectedTags = [];
        switchPage('teammate-review');
        _tmRenderReviewTags();
        var head = document.getElementById('tm-review-target');
        if (head) head.innerHTML = '<div class="tm-feed-empty">Загрузка…</div>';
        if (_tm.reviewTargetUserId) {
            try {
                var resp = await apiFetch(TM_API + '/teammates/profile/' + _tm.reviewTargetUserId);
                if (resp.ok) {
                    var p = await resp.json();
                    _tmRenderReviewTarget(p);
                } else {
                    if (head) head.innerHTML = '<div class="tm-feed-empty">Не удалось загрузить профиль игрока</div>';
                }
            } catch (e) {
                console.warn('[tm] review target:', e);
            }
        } else if (head) {
            head.innerHTML = '<div class="tm-feed-empty">Игрок</div>';
        }
    };

    function _tmRenderReviewTarget(p) {
        var head = document.getElementById('tm-review-target');
        if (!head) return;
        var avatarHtml = _tmAvatarHtml(p);
        var displayName = _tmDisplayName(p);
        var rankIcon = _tmRankIconImg(p.rank, 'tm-rank-icon--xs');
        var meta = [];
        if (p.rank) meta.push('<span class="tm-player-rank">' + rankIcon + '<span class="tm-player-rank-text">' + _tmEsc(p.rank) + '</span></span>');
        if (p.hours != null) meta.push('<span class="tm-player-hours"><span class="tm-player-meta-num">' + _tmFormatHours(p.hours) + '</span> ч</span>');
        if (p.mood) meta.push('<span class="tm-player-meta-mood">' + _tmEsc(TM_MOOD_LABELS[p.mood] || p.mood) + '</span>');
        head.innerHTML =
            avatarHtml +
            '<div class="tm-player-id">' +
              '<div class="tm-player-name">' + _tmEsc(displayName) + '</div>' +
              (meta.length ? '<div class="tm-player-meta-row">' + meta.join(' <span class="tm-player-meta-dot">·</span> ') + '</div>' : '') +
            '</div>';
    }

    function _tmRenderReviewTags() {
        var posWrap = document.getElementById('tm-review-tags-positive');
        var negWrap = document.getElementById('tm-review-tags-negative');
        var render = function (tag, cls) {
            return '<button type="button" class="tm-review-tag ' + cls + '" data-tag="' + _tmEsc(tag) + '" onclick="tmToggleReviewTag(\'' + _tmEsc(tag) + '\', this)">' + _tmEsc(tag) + '</button>';
        };
        if (posWrap) posWrap.innerHTML = TM_POSITIVE_TAGS.map(function (t) { return render(t, 'tm-review-tag--positive'); }).join('');
        if (negWrap) negWrap.innerHTML = TM_NEGATIVE_TAGS.map(function (t) { return render(t, 'tm-review-tag--negative'); }).join('');
    }

    window.tmToggleReviewTag = function (tag, btn) {
        var i = _tm.reviewSelectedTags.indexOf(tag);
        if (i >= 0) _tm.reviewSelectedTags.splice(i, 1);
        else _tm.reviewSelectedTags.push(tag);
        btn.classList.toggle('tm-review-tag--selected');
    };

    window.tmSubmitReview = async function () {
        var token = _tmGetToken();
        if (!token) { showToast('Нужна авторизация'); return; }
        if (!_tm.reviewRequestId) { showToast('Нет запроса для оценки'); return; }
        if (!_tm.reviewSelectedTags.length) { showToast('Выбери хотя бы один тег'); return; }

        var btn = document.getElementById('tm-review-submit');
        if (btn) btn.disabled = true;
        try {
            var resp = await apiFetch(TM_API + '/teammates/review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    token: token,
                    request_id: _tm.reviewRequestId,
                    tags: _tm.reviewSelectedTags.slice()
                })
            });
            if (resp.status === 409) { showToast('Отзыв уже отправлен'); return; }
            if (!resp.ok) { showToast('Не удалось отправить отзыв'); return; }
            showToast('Спасибо за отзыв', 'ok');
            _tm.reviewRequestId = null;
            _tm.reviewTargetUserId = null;
            _tm.reviewSelectedTags = [];
            switchPage('home');
        } finally {
            if (btn) btn.disabled = false;
        }
    };

    // ── Deep links ───────────────────────────────────────────────────
    //   ?teammate_review=<request_id>&teammate_target=<user_id>
    //     → открыть экран оценки игрока.
    //   ?tm_incoming=1
    //     → открыть страницу тиммейтов на вкладке "Мой профиль"
    //       (там же показывается секция "Входящие запросы").
    //
    // Порядок инициализации критичен:
    //   1) Дожидаемся DOMContentLoaded. Скрипт грузится с defer, поэтому к
    //      моменту его выполнения readyState='interactive', но другие
    //      DOMContentLoaded-обработчики ещё не отстреляли. Синхронный запуск
    //      deep-link'а раньше них — и есть основной баг "попадаю на главную".
    //   2) Дожидаемся валидного токена. Уведомление приходит на URL без
    //      ?token=, поэтому USER_TOKEN изначально пуст. Первый API-вызов
    //      (например, GET /profile/<id>) ушёл бы с пустой строкой токена,
    //      получил 401 и НЕ был бы корректно пересобран в apiFetch
    //      (текущий ретрай URL не умеет вставлять токен в пустое место).
    //      Поэтому проактивно выпускаем свежий токен через refreshToken()
    //      ДО любых deep-link API-вызовов.

    async function _tmEnsureToken() {
        // Если токен пришёл в URL — используем как есть.
        if (_tmGetToken()) return true;
        // Иначе тянем через initData. refreshToken() сам дедуплицирует
        // параллельные вызовы через _refreshInFlight, поэтому безопасно
        // звать его проактивно — никакого двойного запроса не будет.
        try {
            var t = (typeof refreshToken === 'function') ? await refreshToken() : null;
            return !!t;
        } catch (e) {
            console.warn('[tm] deep-link: pre-refresh failed:', e);
            return false;
        }
    }

    async function _tmCheckDeepLink() {
        var params;
        try { params = new URLSearchParams(window.location.search); }
        catch (e) { return; }

        var reviewId = params.get('teammate_review');
        var tmIncoming = (params.get('tm_incoming') === '1');
        if (!reviewId && !tmIncoming) return;

        // (2) Гарантируем токен перед навигацией. Если не удалось — refreshToken
        //     уже показал auth-banner; всё равно пытаемся открыть экран, потому
        //     что иначе пользователь увидит главную и не поймёт, куда вёл клик.
        await _tmEnsureToken();

        try {
            if (reviewId) {
                var targetId = params.get('teammate_target');
                tmOpenReview(parseInt(reviewId, 10), targetId ? parseInt(targetId, 10) : null);
                return;
            }
            if (tmIncoming) {
                // Профиль теперь в overlay-sheet, не tab. Открываем страницу
                // тиммейтов, потом sheet поверх с requests-tab='incoming'.
                goToTeammates();
                if (typeof window.tmOpenProfileSheet === 'function') {
                    tmOpenProfileSheet();
                }
                tmSetRequestsTab('incoming');
            }
        } catch (e) {
            console.warn('[tm] deep-link handler error:', e);
        }
    }

    // ─────────────────────────────────────────────────────────────────
    //  Party-finder («Лобби»)
    // ─────────────────────────────────────────────────────────────────

    var _TM_LOBBY_TTL_MIN = 30;
    var _TM_LOBBY_VALID_SIZES = [3, 4, 5];
    var _TM_LOBBY_VALID_SIZES_RANKED = [3, 5];

    // Загрузка активных лобби. Кладём в _tm.lobbies, ререндерим.
    async function loadLobbies() {
        if (_tm.lobbiesLoading) return;
        _tm.lobbiesLoading = true;
        try {
            var token = _tmGetToken();
            if (!token) return;
            var resp = await apiFetch(
                TM_API + '/teammates/lobbies?token=' + encodeURIComponent(token)
            );
            if (!resp.ok) return;
            var data;
            try { data = await resp.json(); } catch (e) { data = { items: [] }; }
            _tm.lobbies = Array.isArray(data && data.items) ? data.items : [];
            renderLobbies();
        } catch (e) {
            console.warn('[tm] loadLobbies:', e);
        } finally {
            _tm.lobbiesLoading = false;
        }
    }
    window.tmRefreshLobbies = function () {
        _tmTriggerRefresh('lobby');
        if (_tmIsPageActive()) _tmStartPolling();
    };

    // Вычисляет lobby_id, в котором участвует текущий юзер (host или member).
    // null если ни в каком. Источник истины — клиентский кэш _tm.lobbies.
    function _tmGetMyLobbyId() {
        var myId = _tm.myProfile && _tm.myProfile.user_id;
        if (!myId) return null;
        for (var i = 0; i < _tm.lobbies.length; i++) {
            var l = _tm.lobbies[i];
            if (l.host_id === myId) return l.lobby_id;
            for (var j = 0; j < (l.slots || []).length; j++) {
                var s = l.slots[j];
                if (s.user && s.user.user_id === myId) return l.lobby_id;
            }
        }
        return null;
    }

    function renderLobbies() {
        var listEl = document.getElementById('tm-lobbies-list');
        if (!listEl) return;
        if (!_tm.lobbies.length) {
            // Empty-state с активным CTA — «be the first», не «no data».
            // CTA-кнопка дублирует primary вверху панели для удобства тапа
            // прямо из пустого экрана, без подъёма наверх.
            listEl.innerHTML = [
                '<div class="tm-lobby-empty">',
                  '<div class="tm-lobby-empty-icon"><i class="ph ph-users-three" aria-hidden="true"></i></div>',
                  '<div class="tm-lobby-empty-title">Никто не собирает стак</div>',
                  '<div class="tm-lobby-empty-body">Создай первое лобби — оно появится в ленте, и другие игроки смогут к тебе подключиться.</div>',
                '</div>',
            ].join('');
            return;
        }
        var myLobbyId = _tmGetMyLobbyId();
        listEl.innerHTML = _tm.lobbies.map(function (l) {
            return _renderLobbyCard(l, { myLobbyId: myLobbyId });
        }).join('');
    }

    var TM_LOBBY_MODE_LABELS = { ranked: 'Рейтинговый', normal: 'Обычный', turbo: 'Турбо' };

    function _renderLobbyCard(lobby, opts) {
        opts = opts || {};
        var slots = (lobby.slots || []).slice().sort(function (a, b) {
            return a.position - b.position;
        });

        // Host data — берём из его слота.
        var hostSlot = null;
        for (var i = 0; i < slots.length; i++) {
            if (slots[i].position === lobby.host_position) hostSlot = slots[i];
        }
        var hostUser = hostSlot && hostSlot.user;
        var hostName = hostUser ? _tmDisplayName(hostUser) : 'Хост';
        var hostAvatar = hostUser
            ? _tmAvatarHtml(hostUser, 'tm-player-avatar--lg')
            : '<div class="tm-player-avatar tm-player-avatar--lg tm-player-avatar--fallback">·</div>';

        // Filled count для footer'а.
        var filledCount = 0;
        for (var k = 0; k < slots.length; k++) if (slots[k].user) filledCount++;

        // Сколько минут осталось — простая локальная разница.
        var expMs = _tmParseUtcLike(lobby.expires_at);
        var minLeft = Math.max(0, Math.ceil((expMs - Date.now()) / 60000));
        var expiresLabel = (minLeft > 0 && isFinite(minLeft))
            ? ('истекает через ' + _tmFormatRemaining(minLeft))
            : 'истекает';

        // Member-state: я в этом лобби?
        var amInThisLobby = opts.myLobbyId === lobby.lobby_id;
        var amInOtherLobby = !amInThisLobby && opts.myLobbyId != null;
        var amHost = amInThisLobby && _tm.myProfile && _tm.myProfile.user_id === lobby.host_id;

        // Action-кнопка справа в head'е (показываем только если я участник).
        var actionBtn = '';
        if (amHost) {
            actionBtn = '<button class="tm-lobby-action" onclick="tmDisbandLobby(' + lobby.lobby_id + ', this)">Распустить</button>';
        } else if (amInThisLobby) {
            actionBtn = '<button class="tm-lobby-action" onclick="tmLeaveLobby(' + lobby.lobby_id + ', this)">Выйти</button>';
        }

        // Rank-filter защита: если у лобби rank_filter и мой ранг не в нём → join disabled.
        var myRank = _tm.myProfile && _tm.myProfile.rank;
        var rankBlocked = false;
        if (lobby.rank_filter && lobby.rank_filter.length) {
            if (!myRank || lobby.rank_filter.indexOf(myRank) === -1) rankBlocked = true;
        }
        var joinDisabled = amInOtherLobby || rankBlocked;

        // Slot-grid: для каждого slot — либо avatar (если занят), либо tappable
        // empty-circle с position-иконкой.
        var slotsHtml = slots.map(function (s) {
            if (s.user) {
                // Filled. Host slot — accent border.
                var isHost = (s.user.user_id === lobby.host_id);
                var cls = 'tm-lobby-slot tm-lobby-slot--filled' + (isHost ? ' tm-lobby-slot--host' : '');
                var ava = _tmAvatarHtmlInner(s.user);
                return '<div class="' + cls + '" title="Pos ' + s.position + '">' + ava + '</div>';
            }
            // Empty. Tap → join (если не disabled).
            var cls2 = 'tm-lobby-slot tm-lobby-slot--empty' + (joinDisabled ? ' tm-lobby-slot--disabled' : '');
            var onclick = joinDisabled
                ? ''
                : ' onclick="tmJoinLobbySlot(' + lobby.lobby_id + ', ' + s.position + ', this)"';
            return '<div class="' + cls2 + '"' + onclick + ' title="Pos ' + s.position + '">' +
                '<img src="' + _tmEsc(_tmPosIcon(s.position)) + '" alt="Pos ' + s.position + '">' +
            '</div>';
        }).join('');

        // Meta-line под именем: ранг хоста · режим · (если rank_filter — диапазон рангов).
        var metaParts = [];
        if (hostUser && hostUser.rank) {
            metaParts.push(
                '<span class="tm-player-rank">' + _tmRankIconImg(hostUser.rank, 'tm-rank-icon--xs') +
                '<span class="tm-player-rank-text">' + _tmEsc(hostUser.rank) + '</span></span>'
            );
        }
        metaParts.push(
            '<span class="tm-lobby-meta-mode">' + _tmEsc(TM_LOBBY_MODE_LABELS[lobby.mode] || lobby.mode) + '</span>'
        );
        if (lobby.rank_filter && lobby.rank_filter.length) {
            // Сжимаем 8 рангов в диапазон first–last.
            metaParts.push(
                '<span>' + _tmEsc(lobby.rank_filter[0]) +
                (lobby.rank_filter.length > 1 ? '–' + _tmEsc(lobby.rank_filter[lobby.rank_filter.length - 1]) : '') +
                '</span>'
            );
        }
        var metaJoiner = ' <span class="tm-lobby-meta-dot">·</span> ';
        var metaRow = '<div class="tm-lobby-meta">' + metaParts.join(metaJoiner) + '</div>';

        // Footer: «3 из 5 · истекает через 24 мин» + если rankBlocked, прибавляем reason
        var footerText = filledCount + ' из ' + lobby.party_size +
            ' <span class="tm-lobby-footer-dot">·</span> ' + expiresLabel;
        if (rankBlocked) {
            footerText += ' <span class="tm-lobby-footer-dot">·</span> твой ранг не подходит';
        } else if (amInOtherLobby) {
            footerText += ' <span class="tm-lobby-footer-dot">·</span> ты в другом лобби';
        }

        return [
            '<article class="tm-lobby-card" data-lobby-id="' + lobby.lobby_id + '">',
              '<header class="tm-lobby-head">',
                hostAvatar,
                '<div class="tm-lobby-host-info">',
                  '<div class="tm-lobby-host-name">Лобби ' + _tmEsc(hostName) + '</div>',
                  metaRow,
                '</div>',
                actionBtn,
              '</header>',
              '<div class="tm-lobby-slots">' + slotsHtml + '</div>',
              '<div class="tm-lobby-footer">' + footerText + '</div>',
            '</article>'
        ].join('');
    }

    // Хелпер: avatar — внутренности (без обёртки .tm-player-avatar div'а),
    // используется внутри slot-circle где обёртка уже есть.
    function _tmAvatarHtmlInner(user) {
        if (user && user.photo_url) {
            return '<img src="' + _tmEsc(user.photo_url) + '" alt="">';
        }
        var src = (user && (user.first_name || user.username || '')).trim();
        var ch = src ? src.charAt(0).toUpperCase() : '·';
        return '<span class="tm-lobby-slot-initial">' + _tmEsc(ch) + '</span>';
    }

    // ── Lobby actions ────────────────────────────────────────────────

    window.tmJoinLobbySlot = async function (lobbyId, position, slotEl) {
        var token = _tmGetToken();
        if (!token) { showToast('Нужна авторизация'); return; }
        // Optimistic UI: затемняем slot пока ждём ответ. Если 4xx — откатываем.
        if (slotEl) slotEl.classList.add('tm-lobby-slot--disabled');
        try {
            var resp = await apiFetch(TM_API + '/teammates/lobby/' + lobbyId + '/join', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token, position: position }),
            });
            if (!resp.ok) {
                // Подробный лог для диагностики (status + body) — без этого
                // юзер видит только generic «Не удалось», диагностировать
                // удалённо невозможно.
                var rawBody = '';
                var err;
                try { rawBody = await resp.text(); } catch (e) { /* пусто */ }
                try { err = rawBody ? JSON.parse(rawBody) : null; } catch (e) { err = null; }
                console.warn('[tm] joinLobby failed:', resp.status, rawBody);
                var detail = (err && (err.detail || err.message)) ||
                             ('Ошибка ' + resp.status);
                showToast(detail);
                if (slotEl) slotEl.classList.remove('tm-lobby-slot--disabled');
                return;
            }
            showToast('Ты в лобби', 'ok');
            // Refresh: лобби-карточка обновится со мной в слоте.
            await loadLobbies();
            // is_searching на бэке снимается; reflect locally.
            if (_tm.myProfile) _tm.myProfile.is_searching = false;
            renderSearchCta();
        } catch (e) {
            console.warn('[tm] joinLobby exception:', e);
            showToast('Сетевая ошибка — попробуй ещё раз');
            if (slotEl) slotEl.classList.remove('tm-lobby-slot--disabled');
        }
    };

    window.tmLeaveLobby = async function (lobbyId, btn) {
        var token = _tmGetToken();
        if (!token) { showToast('Нужна авторизация'); return; }
        if (btn) btn.disabled = true;
        try {
            var resp = await apiFetch(TM_API + '/teammates/lobby/' + lobbyId + '/leave', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token }),
            });
            if (!resp.ok) {
                var err;
                try { err = await resp.json(); } catch (e) { err = null; }
                showToast((err && err.detail) || 'Не удалось выйти');
                if (btn) btn.disabled = false;
                return;
            }
            showToast('Ты вышел из лобби', 'ok');
            await loadLobbies();
        } catch (e) {
            console.warn('[tm] leaveLobby:', e);
            showToast('Не удалось выйти');
            if (btn) btn.disabled = false;
        }
    };

    window.tmDisbandLobby = async function (lobbyId, btn) {
        if (!window.confirm('Распустить лобби? Все участники получат уведомление.')) return;
        var token = _tmGetToken();
        if (!token) { showToast('Нужна авторизация'); return; }
        if (btn) btn.disabled = true;
        try {
            var resp = await apiFetch(TM_API + '/teammates/lobby/' + lobbyId + '/disband', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: token }),
            });
            if (!resp.ok) {
                showToast('Не удалось распустить');
                if (btn) btn.disabled = false;
                return;
            }
            showToast('Лобби распущено', 'ok');
            await loadLobbies();
        } catch (e) {
            console.warn('[tm] disbandLobby:', e);
            showToast('Не удалось распустить');
            if (btn) btn.disabled = false;
        }
    };

    // ── Create-lobby form ────────────────────────────────────────────

    function _tmInitLobbyForm() {
        // Defaults: ranked, 5, host_position = первая позиция из профиля.
        var profile = _tm.myProfile;
        var positions = (profile && Array.isArray(profile.positions)) ? profile.positions : [];
        _tm.lobbyForm = {
            party_size: 5,
            mode: 'ranked',
            host_position: positions[0] || null,
            needed_positions: [],
            rank_filter: [],
            rank_filter_enabled: true,  // в ranked всегда включён
        };
        // Если в профиле есть ранг — заполняем default rank_filter (host'а ранг ±2).
        if (profile && profile.rank) {
            var idx = TM_RANKS.indexOf(profile.rank);
            if (idx >= 0) {
                var lo = Math.max(0, idx - 2);
                var hi = Math.min(TM_RANKS.length - 1, idx + 2);
                _tm.lobbyForm.rank_filter = TM_RANKS.slice(lo, hi + 1);
            }
        }
    }

    window.tmOpenLobbyForm = function () {
        if (!_tm.myProfile || !_tm.myProfile.rank) {
            showToast('Сначала заполни профиль');
            setTeammatesTab('profile');
            return;
        }
        if (_tmGetMyLobbyId() != null) {
            showToast('Ты уже в активном лобби');
            return;
        }
        _tmInitLobbyForm();
        _tmRenderLobbyForm();
        var sheet = document.getElementById('tm-lobby-form-sheet');
        if (!sheet) return;
        sheet.hidden = false;
        sheet.setAttribute('aria-hidden', 'false');
        // eslint-disable-next-line no-unused-expressions
        sheet.offsetHeight;
        sheet.classList.add('tm-help-sheet--open');
        document.body.style.overflow = 'hidden';
    };

    window.tmCloseLobbyForm = function () {
        var sheet = document.getElementById('tm-lobby-form-sheet');
        if (!sheet) return;
        sheet.classList.remove('tm-help-sheet--open');
        sheet.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        var onEnd = function () {
            sheet.removeEventListener('transitionend', onEnd);
            if (!sheet.classList.contains('tm-help-sheet--open')) {
                sheet.hidden = true;
            }
        };
        sheet.addEventListener('transitionend', onEnd);
    };

    function _tmRenderLobbyForm() {
        var f = _tm.lobbyForm;
        if (!f) return;

        var rankedLocked = (f.mode === 'ranked');

        // ── Section 1: Лобби ────────────────────────────────────────
        // Size — disable 4 при ranked.
        var sizeBtns = document.querySelectorAll('#tm-lobby-size .tm-mode-btn');
        sizeBtns.forEach(function (b) {
            var size = parseInt(b.getAttribute('data-size'), 10);
            var disabled = (rankedLocked && size === 4);
            b.disabled = disabled;
            b.classList.toggle('tm-mode-btn--active', size === f.party_size && !disabled);
        });
        var sizeHint = document.getElementById('tm-lobby-size-hint');
        if (sizeHint) {
            sizeHint.textContent = rankedLocked
                ? 'В рейтинге 4-стак запрещён правилами Доты — только 3 или 5.'
                : 'Включая тебя.';
        }

        var modeBtns = document.querySelectorAll('#tm-lobby-mode .tm-mode-btn');
        modeBtns.forEach(function (b) {
            b.classList.toggle('tm-mode-btn--active', b.getAttribute('data-mode') === f.mode);
        });

        // ── Section 2: Состав ───────────────────────────────────────
        // Host position — pill-buttons, single-select из профильных позиций.
        var hostPosWrap = document.getElementById('tm-lobby-host-pos');
        if (hostPosWrap) {
            var profilePositions = (_tm.myProfile && _tm.myProfile.positions) || [];
            hostPosWrap.innerHTML = [1, 2, 3, 4, 5].map(function (p) {
                var inProfile = profilePositions.indexOf(p) !== -1;
                var active = (p === f.host_position);
                var cls = 'tm-position-btn'
                    + (active ? ' tm-position-btn--active' : '')
                    + (inProfile ? '' : ' tm-position-btn--disabled');
                var onclick = inProfile ? ' onclick="tmLobbySetHostPos(' + p + ')"' : '';
                return '<button type="button" class="' + cls + '"' + onclick + ' data-pos="' + p + '">' +
                    '<img src="' + _tmEsc(_tmPosIcon(p)) + '" alt="' + p + '">' +
                '</button>';
            }).join('');
        }

        // Needed positions — slot-tiles (48×48 dashed circles), echo'ят реальные
        // лобби-слоты в ленте. Visually distinct от host-pill'ов выше.
        var neededWrap = document.getElementById('tm-lobby-needed-pos');
        if (neededWrap) {
            var needSet = {};
            for (var i = 0; i < f.needed_positions.length; i++) needSet[f.needed_positions[i]] = true;
            neededWrap.innerHTML = [1, 2, 3, 4, 5].map(function (p) {
                var isHostSlot = (p === f.host_position);
                var active = !!needSet[p];
                var cls = 'tm-lobby-form-slot'
                    + (active ? ' tm-lobby-form-slot--active' : '')
                    + (isHostSlot ? ' tm-lobby-form-slot--disabled' : '');
                var onclick = isHostSlot ? '' : ' onclick="tmLobbyToggleNeededPos(' + p + ')"';
                var title = isHostSlot ? 'Это твой слот' : 'Pos ' + p;
                return '<button type="button" class="' + cls + '"' + onclick +
                    ' data-pos="' + p + '" title="' + title + '" aria-label="' + title + '">' +
                    '<img src="' + _tmEsc(_tmPosIcon(p)) + '" alt="">' +
                '</button>';
            }).join('');
        }
        var neededHint = document.getElementById('tm-lobby-needed-hint');
        if (neededHint) {
            var needLimit = f.party_size - 1;
            var picked = f.needed_positions.length;
            var hintText;
            if (picked === 0) {
                hintText = 'Тап чтобы открыть слот · нужно ' + needLimit + '.';
            } else if (picked < needLimit) {
                hintText = 'Открыто ' + picked + ' из ' + needLimit + ' · ещё ' + (needLimit - picked) + '.';
            } else {
                hintText = 'Все ' + needLimit + ' слотов открыты.';
            }
            neededHint.textContent = hintText;
        }

        // ── Section 3: Кого пускать (rank segments) ────────────────
        var rankSegBtns = document.querySelectorAll('#tm-lobby-rank-segments .tm-segment');
        rankSegBtns.forEach(function (b) {
            var mode = b.getAttribute('data-rank-mode');
            var active = (mode === 'filter') === !!f.rank_filter_enabled;
            b.classList.toggle('tm-segment--active', active);
            // В ranked сегмент «Любой ранг» заблочен — нельзя выключить.
            var locked = (rankedLocked && mode === 'any');
            b.disabled = locked;
            b.classList.toggle('tm-segment--locked', locked);
        });
        var rankChips = document.getElementById('tm-lobby-rank-chips');
        var rankHint  = document.getElementById('tm-lobby-rank-hint');
        if (rankChips) {
            rankChips.hidden = !f.rank_filter_enabled;
            if (f.rank_filter_enabled) {
                var rfSet = {};
                for (var ri = 0; ri < f.rank_filter.length; ri++) rfSet[f.rank_filter[ri]] = true;
                rankChips.innerHTML = TM_RANKS.map(function (r, idx) {
                    var tier = idx + 1;
                    return _tmFchip({
                        variant: 'icon',
                        active: !!rfSet[r],
                        onclick: 'tmLobbyToggleRankChip(\'' + _tmEsc(r) + '\')',
                        title: r,
                        label: r,
                        content: '<img src="/rank_icons/medal_' + tier + '.png" alt="" onerror="this.style.display=\'none\'">',
                    });
                }).join('');
            }
        }
        if (rankHint) {
            if (rankedLocked) {
                rankHint.textContent = 'В рейтинге выбор обязателен — Dota не запустит matchmake с большим разбросом.';
            } else if (f.rank_filter_enabled) {
                rankHint.textContent = 'Тап на ранг — добавить/убрать.';
            } else {
                rankHint.textContent = 'Лобби увидят игроки любого ранга.';
            }
        }

        // ── Footer: summary + validation ────────────────────────────
        // Live-update summary даёт юзеру preview того что он создаёт ПЕРЕД
        // тапом submit. Validation error (если есть) — explicit reason почему
        // submit disabled, вместо «кнопка серая, почему?».
        var summaryEl = document.getElementById('tm-lobby-form-summary');
        var errorEl   = document.getElementById('tm-lobby-form-error');
        var submitBtn = document.getElementById('tm-lobby-submit');

        var canSubmit =
            f.host_position != null &&
            f.needed_positions.length === (f.party_size - 1) &&
            (!rankedLocked || f.rank_filter.length > 0);

        // Reason для validation hint.
        var errorText = '';
        if (!canSubmit) {
            if (f.host_position == null)                                 errorText = 'Выбери свою позицию.';
            else if (f.needed_positions.length < (f.party_size - 1))     errorText = 'Открой все ' + (f.party_size - 1) + ' слот' + ((f.party_size - 1) === 1 ? '' : 'а');
            else if (rankedLocked && f.rank_filter.length === 0)         errorText = 'Выбери допустимые ранги.';
        }

        if (summaryEl) {
            var modeLabel = TM_LOBBY_MODE_LABELS[f.mode] || f.mode;
            var parts = [
                '<strong>' + f.party_size + '-стак</strong>',
                _tmEsc(modeLabel),
            ];
            if (f.host_position != null) {
                parts.push('ты <strong>Pos ' + f.host_position + '</strong>');
            }
            if (f.needed_positions.length) {
                var sorted = f.needed_positions.slice().sort(function (a, b) { return a - b; });
                parts.push('нужны <strong>Pos ' + sorted.join(', ') + '</strong>');
            }
            if (f.rank_filter_enabled && f.rank_filter.length) {
                var sortedRanks = f.rank_filter.slice().sort(function (a, b) {
                    return TM_RANKS.indexOf(a) - TM_RANKS.indexOf(b);
                });
                var rangeText = sortedRanks.length === 1
                    ? sortedRanks[0]
                    : sortedRanks[0] + '–' + sortedRanks[sortedRanks.length - 1];
                parts.push(_tmEsc(rangeText));
            }
            summaryEl.innerHTML = parts.join(' · ');
        }
        if (errorEl) {
            errorEl.textContent = errorText;
            errorEl.hidden = !errorText;
        }
        if (submitBtn) submitBtn.disabled = !canSubmit;
    }

    window.tmLobbySetSize = function (size) {
        var f = _tm.lobbyForm; if (!f) return;
        // 4 запрещён при ranked.
        if (f.mode === 'ranked' && size === 4) return;
        if (_TM_LOBBY_VALID_SIZES.indexOf(size) === -1) return;
        f.party_size = size;
        // Если выбранных needed > нового лимита — обрезаем.
        if (f.needed_positions.length > size - 1) {
            f.needed_positions = f.needed_positions.slice(0, size - 1);
        }
        _tmRenderLobbyForm();
    };

    window.tmLobbySetMode = function (mode) {
        var f = _tm.lobbyForm; if (!f) return;
        f.mode = mode;
        // Переключение на ranked: если был size=4 — гоним в 5.
        if (mode === 'ranked' && f.party_size === 4) f.party_size = 5;
        // rank-filter включается принудительно для ranked.
        if (mode === 'ranked') f.rank_filter_enabled = true;
        _tmRenderLobbyForm();
    };

    window.tmLobbySetHostPos = function (p) {
        var f = _tm.lobbyForm; if (!f) return;
        f.host_position = p;
        // Если host_position попал в needed — убираем.
        var idx = f.needed_positions.indexOf(p);
        if (idx !== -1) f.needed_positions.splice(idx, 1);
        _tmRenderLobbyForm();
    };

    window.tmLobbyToggleNeededPos = function (p) {
        var f = _tm.lobbyForm; if (!f) return;
        if (p === f.host_position) return;
        var idx = f.needed_positions.indexOf(p);
        if (idx !== -1) {
            f.needed_positions.splice(idx, 1);
        } else {
            if (f.needed_positions.length >= f.party_size - 1) {
                showToast('Уже выбрано ' + (f.party_size - 1));
                return;
            }
            f.needed_positions.push(p);
        }
        _tmRenderLobbyForm();
    };

    // Segmented control: 'any' (любой ранг) ⇆ 'filter' (только эти).
    // В ranked-режиме 'any' заблокирован (UI-уровень + повторная защита тут).
    window.tmLobbySetRankMode = function (mode) {
        var f = _tm.lobbyForm; if (!f) return;
        if (f.mode === 'ranked' && mode === 'any') {
            showToast('В рейтинге выбор рангов обязателен');
            return;
        }
        var wantEnabled = (mode === 'filter');
        if (wantEnabled === !!f.rank_filter_enabled) return;
        f.rank_filter_enabled = wantEnabled;
        if (!wantEnabled) f.rank_filter = [];
        _tmRenderLobbyForm();
    };
    // Backward-compat alias на случай если где-то в коде остался старый вызов.
    window.tmLobbyToggleRankFilter = function () {
        var f = _tm.lobbyForm; if (!f) return;
        window.tmLobbySetRankMode(f.rank_filter_enabled ? 'any' : 'filter');
    };

    window.tmLobbyToggleRankChip = function (r) {
        var f = _tm.lobbyForm; if (!f) return;
        var idx = f.rank_filter.indexOf(r);
        if (idx !== -1) f.rank_filter.splice(idx, 1);
        else f.rank_filter.push(r);
        // Сохраняем sorted-by-tier для красивого отображения «Legend–Divine».
        f.rank_filter.sort(function (a, b) { return TM_RANKS.indexOf(a) - TM_RANKS.indexOf(b); });
        _tmRenderLobbyForm();
    };

    window.tmSubmitLobby = async function () {
        var f = _tm.lobbyForm; if (!f) return;
        var token = _tmGetToken();
        if (!token) { showToast('Нужна авторизация'); return; }

        var payload = {
            token: token,
            party_size: f.party_size,
            mode: f.mode,
            host_position: f.host_position,
            needed_positions: f.needed_positions.slice(),
        };
        // rank_filter включаем в payload только если active.
        if (f.rank_filter_enabled && f.rank_filter.length) {
            payload.rank_filter = f.rank_filter.slice();
        }

        var btn = document.getElementById('tm-lobby-submit');
        if (btn) btn.disabled = true;
        try {
            var resp = await apiFetch(TM_API + '/teammates/lobby', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });
            if (!resp.ok) {
                var err;
                try { err = await resp.json(); } catch (e) { err = null; }
                showToast((err && err.detail) || 'Не удалось создать лобби');
                if (btn) btn.disabled = false;
                return;
            }
            showToast('Лобби создано', 'ok');
            tmCloseLobbyForm();
            await loadLobbies();
            // is_searching на бэке снимается — reflect locally.
            if (_tm.myProfile) _tm.myProfile.is_searching = false;
            renderSearchCta();
        } catch (e) {
            console.warn('[tm] submitLobby:', e);
            showToast('Не удалось создать лобби');
            if (btn) btn.disabled = false;
        }
    };

    // (1) Откладываем запуск ВСЕГДА до DOMContentLoaded.
    //     Defer-скрипт выполняется при readyState='interactive' — раньше, чем
    //     ready-listener'ы остальных секций приложения. Старая ветка
    //     «иначе вызвать сразу» создавала ту самую гонку.
    if (document.readyState === 'complete') {
        // Страница уже полностью загружена (поздний reflow / тестовый запуск).
        _tmCheckDeepLink();
    } else {
        document.addEventListener('DOMContentLoaded', _tmCheckDeepLink, { once: true });
    }
})();

