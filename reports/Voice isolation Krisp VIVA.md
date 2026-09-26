# Krisp VIVA варто пілотувати заради переривань, не ізоляції

Krisp VIVA варто оцінити як евалюаційний, а потім платний пілот за прямою ліцензією Krisp, і головна причина — **Interruption Prediction v1**, а не сама ізоляція. Voice Isolation від Krisp належить до того самого класу, що ai-coustics Voice Focus і NVIDIA Speaker Focus: мовця вона обирає без enrollment, за близькістю до мікрофона і рівнем сигналу, тож має ту саму сліпу пляму «абонент мовчить, говорить телевізор», а її задокументований ризик протилежний — надмірне придушення тихих абонентів. Інспекція wheel-пакетів показала, що «VIVA PRO v1», яку LiveKit постачає для Cloud, побайтово збігається зі старою headset-моделлю BVC, а «VIVA TEL v2» — це перенавчений BVCTelephony; новіші VI-tel v2.1, VI v3 і VI 2.5/lite (за заявою Krisp — 15 мс алгоритмічної затримки і −46% WER на 10 STT-рушіях, серед яких є NVIDIA) доступні лише з порталу Krisp. Легітимний self-hosted шлях лише один: `livekit-plugins-krisp` 0.4.3 у режимі `krisp_license` з wheel `krisp_audio` (поки підтверджено лише cp312 для macOS arm64 і Linux x86_64), файлом `.kef` і ключем від Krisp, тоді як моделі, вбудовані в пропрієтарний wheel LiveKit, поза LiveKit Cloud не ліцензовані й використовуватися не повинні. Аудіо абонента не залишає хост, але стандартна «UAR»-збірка SDK асинхронно перевіряє ліцензію і звітує про використання через мережу, поведінку після grace-періоду не задокументовано, а кожна відома відмова інтеграцій Krisp зводилася до мовчазного пропуску сирого звуку. Публічної ціни немає; треті сторони дають ~$0.001–0.0015/хв, тобто ~$100–750 на місяць за 100–500 тис. хв — на рівні ai-coustics і помітно дешевше за NVAIE. Унікальне для цього репозиторію — аудіокласифікатор «backchannel чи перебивання» (IP v1: ~6 M параметрів, лише англійська, за заявою вендора менше 6% хибних спрацювань), якого LiveKit не дає ні в Cloud, ні локально, тож його доведеться перенести з Pipecat у bargein-сервер і PolicyRunner поруч із лексиконом і MaAI. Рекомендація: надіслати Krisp письмові питання, отримати evaluation-доступ до VI-tel v2.1/2.5, IP v1.1 і TP v3, прогнати гілку K та IP на корпусі A/B/C (≈2–3 тижні інженера) і купувати лише після проходження воріт; найімовірніший результат — «IP як сигнал, а ізоляція лише тоді, коли вона перемагає Voice Focus».

> **Позначки достовірності.** **Перевірено** — факт прочитано безпосередньо з коду: репозиторіїв Krisp (`Krisp-SDK-Sample-Apps`, `gst-krisp-audio`, `pipecat-fork-sdk`), Pipecat і його документації, `livekit/agents`, wheel-пакетів із PyPI або цього репозиторію. **Вимір** — дослідники запустили код самі в scratch-середовищі. **Snippet / заява вендора** — текст пошукової видачі чи маркетинг: egress-проксі блокував krisp.ai, sdk-docs.krisp.ai, help.krisp.ai, docs.livekit.io, livekit.com, docs.pipecat.ai, ai-coustics.com і community.livekit.io, тож ці сторінки повністю прочитати не вдалося. **Третя сторона** — незалежний профіль `api-evangelist/krisp`, що цитує документацію Krisp. **Висновок** — наше міркування, яке треба перевірити вимірюванням. Справжнього `krisp_audio`, `.kef` чи ключа Krisp у дослідників не було: license-режим перевірено лише з фейковим SDK.

## Три релізи VIVA ховають дві родини моделей і перейменований BVC

«VIVA» розшифровується як **Voice Isolation for Voice AI**. Krisp описує ці моделі як такі, що стоять на сервері «in front of the VAD to improve turn-taking, false interrupts and sometimes WER» (snippet, [sdk-docs VI](https://sdk-docs.krisp.ai/docs/models-for-conversational-ai)). Лінійка пройшла три платформні релізи:

| Реліз | Дата | Що увійшло | Заяви вендора | Джерела |
|---|---|---|---|---|
| VIVA SDK | 16.07.2025 | SDK для server-side voice isolation | Понад 1 млрд хвилин обробки голосових агентів на місяць | [BusinessWire](https://www.businesswire.com/news/home/20250716580385/en/Krisp-Launches-VIVA-SDK-and-Surpasses-1B-Minutes-of-Voice-AI-Processing-per-Month-Milestone) |
| VIVA 2.0 | 06.05.2026 | Один CPU-пакет: Voice Isolation v3, Turn Prediction v3, Interruption Prediction v1, сигнальні детектори (TTS, стать, акцент) і VAD | «15 ms latency»; понад 12 млрд хвилин на рік у понад 130 продуктах, серед них Daily, Vapi, LiveKit, Ultravox і Telnyx | [BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents), [Krisp blog](https://krisp.ai/blog/viva-2-0-ai-infrastructure-for-voice-ai-agents/) |
| VIVA 2.5 | 12.08.2026 | VI 2.5 у двох розмірах: повний і lite «for CPU-constrained and edge deployments» | — | [Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/), [davitb](https://x.com/davitb/status/2087555112810250608) |

Моделі ізоляції діляться на дві родини: **`krisp-viva-tel-*`** для «Telephony, Cellular, Landline, Mobile, Desktop, Browser (up to 16kHz)» і **`krisp-viva-pro`** для «Mobile, Desktop, Browser (WebRTC, up to 32kHz)» (перевірено, [Pipecat docs](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx)). Керований Krisp у Pipecat Cloud теж дає вибрати лише `tel` або `pro` ([Pipecat Cloud](https://github.com/pipecat-ai/docs/blob/main/pipecat-cloud/guides/krisp-viva.mdx)).

| Модель / файл | Дата | Що заявлено або відомо | Доказ |
|---|---|---|---|
| `krisp-viva-tel-v1` | 2025 | «bi-directional» VI для голосових ботів | Snippet, [sdk-docs VI](https://sdk-docs.krisp.ai/docs/models-for-conversational-ai) |
| `krisp-viva-tel-lite-v1` | 2025–2026 | «3.5x smaller»; наступник `krisp-bvc-o-lite-v2`; додає inbound-телефонію «within the same CPU footprint» | Snippet, [Krisp blog](https://krisp.ai/blog/small-voice-isolation-model/) |
| `krisp-viva-tel-v2.kef` / `krisp-viva-vi-tel-v2.kef` | до 2026 | Обидва написання трапляються в гайді Pipecat | Перевірено, [Pipecat docs](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx) |
| `krisp-viva-pro` | — | WebRTC, до 32 кГц | Перевірено, там само |
| `krisp-viva-vi-tel-v2.1` | 08.07.2026 (Go SDK 1.4.0; C/C++ SDK 9.19.0) | 16 кГц, «optimized for 8-16KHz telephony»; порівняно з v2 «reduces voice suppression… improves WER» | Snippet і третя сторона, [changelog](https://sdk-docs.krisp.ai/changelog/viva-go-sdk-v140), [api-evangelist](https://github.com/api-evangelist/krisp/blob/main/changelog/krisp-changelog.yml) |
| Voice Isolation v3 | 06.05.2026 | «ground-up rebuild»; один snippet додає «3.5x smaller… 20-40% WER», але, схоже, змішує це з lite-моделлю | Snippet, [Krisp blog](https://krisp.ai/blog/viva-2-0-ai-infrastructure-for-voice-ai-agents/) |
| VI 2.5 і VI lite 2.5 | 12.08.2026 | 15 мс алгоритмічної затримки на CPU, підтримка narrowband; lite має ≈3.5× менше параметрів і обчислень | Snippet, [Krisp blog](https://krisp.ai/blog/voice-isolation-2-5/) |
| `krisp-viva-tt-v2` → `krisp-viva-tp-v3.kef` | 11.2025 → 04–05.2026 | Turn Prediction | Перевірено (назви), [Pipecat docs](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx) |
| `krisp-viva-ip-v1.kef` → `ip-v1.1` | 04–05.2026 → 07.2026 | Interruption Prediction; v1.1 має «updated model encryption», і попередній файл із новим SDK несумісний | Перевірено (назва) + третя сторона, [api-evangelist](https://github.com/api-evangelist/krisp/blob/main/changelog/krisp-changelog.yml) |
| `krisp-viva-vad-v2.kef` | 2026 | VAD, 8–48 кГц | Перевірено, [Pipecat docs](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx) |
| TTS Detector | 06.05.2026 | Детектор синтетичної мови; назву файлу не знайдено | Snippet, [BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents) |

### Що LiveKit насправді постачає під назвою VIVA

Відповідь дала інспекція публічних wheel-пакетів із PyPI: дослідники витягли рядки й порахували SHA-1 вбудованих блобів. Це доказ того, які саме моделі LiveKit постачає, а не спосіб їх отримати чи використовувати.

`livekit-plugins-krisp-internal` 0.2.0 (22.07.2026) містить дві моделі: `KRISP_VIVA_PRO_V1` і `KRISP_VIVA_TEL_V2`.

**PRO v1 — це стара headset-модель BVC.** Блоби PRO v1 (`pnc.thw` на 28 772 541 Б і `csd.thw` на 644 148 Б) мають ті самі UID, що й headset-модель BVC `hs.c6.f.m.75df8f.kef` із Cloud-пакета `livekit-plugins-noise-cancellation` 0.2.6. Байти `pnc.thw` збігаються побайтово.

**TEL v2 — це перенавчений BVCTelephony.** Модель зберігається у файлі `inb.bvc.blocked.laughter.hs.c6.w.s.5272a6.thw` (28 030 666 Б), а її `FrameProcessorCfg.json` має ті самі 36 ключів і значень, що й конфіг старого BVCTelephony `inb.bvc.hs.c6.w.s.23cdb3.kef`; різняться лише вектори нормалізації ознак, тобто це нове тренування тієї самої конструкції. Обидва факти перевірено ([internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.2.0/), [noise-cancellation 0.2.6](https://pypi.org/project/livekit-plugins-noise-cancellation/0.2.6/)). Попередня версія internal 0.1.0 (06.07.2026) замість TEL мала `KRISP_VIVA_SS_V1`. Це ONNX-модель DeepFilterNet `df.c8.f.m.528d1f.ort`, тобто звичайне шумозаглушення, яке голосів не прибирає ([internal 0.1.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.1.0/)).

Звідси **поправка до попередніх звітів:** «VIVA PRO v1» у LiveKit — це BVC для гарнітур 2025 року, «VIVA TEL v2» — перенавчений inbound BVCTelephony, а поколінь VI v2.1, v3 і 2.5 у пакетах LiveKit немає. Тож будь-який відгук чи вимір «VIVA через LiveKit Cloud» характеризує BVC, а не ті моделі, які Krisp продає зараз.

| Параметр із вбудованого конфігу | VIVA PRO v1 (= LiveKit BVC) | VIVA TEL v2 (≈ BVCTelephony) |
|---|---|---|
| `workingSampleRate` | 32 000 | 16 000 |
| Вікно / крок | 30 мс / 480 семплів (**15 мс**) | 30 мс / 240 семплів (**15 мс**) |
| FFT-біни / розмірність ознак / `compressRate` | 481 / 150 / 3 | 241 / 120 / 2 |
| `frameCount` | 4 | 4 |
| `backgroundSpeakerFix` | `cutStartDB` 10, `cutEndDB` 5, `runFrameCount` 40, `varWindMode` true | Ідентично |
| `pnc` | `freezeLowEnThr` 700, `freezeHighEnThr` 710, `halfLifeInSec` −1 | Ідентично |
| Додаткова підмодель | `csd` (0.64 МБ, 90-вимірні ознаки) | Немає |
| Ваги | GRU, float32, ≈7.2 M параметрів | GRU, float32, ≈7.0 M параметрів |

Джерело для таблиці: перевірено, [internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.2.0/).

### Як читати назви моделей

Імена файлів розшифровуються з високою впевненістю там, де це підтверджує конфіг:

| Фрагмент | Значення | Чим підтверджено |
|---|---|---|
| `inb` | inbound, тобто прийнятий потік дальнього кінця | Висновок |
| `bvc` | background voice cancellation | Висновок |
| `hs` | headset / ближнє поле | Висновок |
| `f` / `w` | 32 / 16 кГц | `workingSampleRate` |
| `c6` / `c8` | нативна GRU-родина / DeepFilterNet на ONNX | Скомпільовані в бінарник шляхи `krisp_gru_*_executable_network.cpp` і `krisp_nc_df_*processor.cpp` |
| `blocked.laughter` | Змінилася ціль тренування щодо сміху | Прибирає TEL v2 сміх чи навпаки зберігає, покаже лише прослуховування |

### Два відкриті питання щодо моделей

**Чи VI v3 і VI 2.5 — одна модель.** Травневий прес-реліз називає нову модель «Voice Isolation v3», а серпневий блог порівнює VI 2.5 з «v2.1», не з v3 ([Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/)). Можливі два прочитання: v3 — це пресова назва того, що потім вийшло як 2.5, або v3 — окремий, можливо дорожчий варіант. Публічні джерела питання не закривають, тому в Krisp треба запитати, який `.kef` відповідає кожній назві.

**Яку родину брати для цього стеку.** Висновок: **`tel`, причому і для SIP, і для WebRTC.** Це виправляє попередній огляд, який радив `-pro` для WebRTC. Nemotron працює на 16 кГц, а `tel` теж обробляє сигнал усередині на 16 кГц, і Krisp сам відносить до `tel` «Mobile, Desktop, Browser». Натомість `pro` — headset-модель із робочою частотою 32 кГц: для ASR на 16 кГц вона нічого не додає і ризиковіша для ноутбуків і гучного зв'язку.

**Як бути з SIP на 8 кГц.** Прямих narrowband-моделей Krisp не публікує. Доступні лише «v2.1 optimized for 8–16 kHz» і «VI 2.5 supports narrowband», а SDK сам ресемплить вхід до частоти моделі (snippet, [sdk-docs VI](https://sdk-docs.krisp.ai/docs/models-for-conversational-ai)).

## Мовця обирають близькість і рівень, тож телевізор лишається відкритим ризиком

### Механізм вибору мовця

Ізоляція Krisp працює **без enrollment**. Про BVC сказано, що він «detects the primary speaker using speaker-to-microphone proximity cues» і «does not require user voice enrollment» ([Krisp BVC blog](https://krisp.ai/blog/contact-center-background-voice-cancellation/)). Довідка Krisp пояснює, що мікрофон на штанзі тримає голос «loud and consistent», і прямо вимагає «that the user speak close to the microphone» (snippet, [help.krisp.ai](https://help.krisp.ai/hc/en-us/articles/7270378194972-Voice-Isolation-compatible-devices)). Селекційний гайд додає обмеження, яке для цієї задачі важить найбільше: «Krisp inbound tech is not designed for multiple simultaneous voices on the same microphone» (snippet, [Model Selection Guide](https://sdk-docs.krisp.ai/docs/rtc-model-guide-bvc-nc)).

Вбудовані конфіги підтверджують рівневу логіку. Постпроцесор `backgroundSpeakerFix` має пороги відсікання 10 → 5 дБ на серіях по 40 кроків, тобто ≈0.6 с, а блок `pnc` має безкінечний період напіврозпаду (`halfLifeInSec: -1`). Модель PRO додатково запускає підмережу `csd` — найімовірніше, competing-speaker detection (перевірено, [internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.2.0/)). Висновок: модель має станову, незгасну оцінку «основного» мовця, і раннє захоплення не того голосу може протриматися весь дзвінок.

### Задокументовані відмови: надмірне придушення

Відомі проблеми вказують в один бік — модель надто агресивна. У спільноті LiveKit пишуть, що BVCTelephony «can be overly aggressive and occasionally cancels out quiet callers», і пропонують підсилювати сигнал до фільтра ([LiveKit community](https://community.livekit.io/t/audio-gain-before-bvctelephony/300)). Тред про деградацію звуку після ввімкнення BVC називає причинами 50-мс кадри і подвійну обробку («don't also enable Krisp on the frontend or your SIP trunk») (snippet, [LiveKit community](https://community.livekit.io/t/unexpected-audio-degradation-after-enabling-bvc-noise-cancellation-in-livekit-voice-agent/745)). Нарешті, сам Krisp визнав проблему: `vi-tel-v2.1` «reduces voice suppression in certain scenarios» порівняно з v2 ([changelog](https://sdk-docs.krisp.ai/changelog/viva-go-sdk-v140)).

Для задачі важливий ще один польовий сигнал. Команда на Pipecat Cloud з **увімкненим фільтром Krisp VI `tel`** порахувала, що в 153 реальних дзвінках «34% contained a reply aborted by a false turn-start inside the caller's own sentence, 6.5%… degenerated into a loop». Виправити це вона хотіла моделлю IP, але отримати її на Pipecat Cloud не змогла ([pipecat#4994](https://github.com/pipecat-ai/pipecat/issues/4994)). Отже, ізоляція сама по собі хибних перехоплень ходу не усуває. Це головний аргумент на користь того, що цінність Krisp для агента лежить у моделях turn-taking.

### Поправка: TTS-гейт у Pipecat не захищає від еха

TTS-гейт у Pipecat — **одноразовий механізм на старті сесії, а не захист від еха.** Попередній огляд вивів, що ізоляція «може захопити ехо бота», але код каже інше. `start()` створює сесію `TtsDetectorFloat`, і доки гейт активний, аудіо йде **без фільтрації**; ізоляція вмикається через 0.5 с після останнього кадру з TTS або через 3 с, якщо TTS не з'явився взагалі, після чого гейт «for the remainder of the session» більше не спрацьовує (перевірено, [krisp_viva_filter.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/filters/krisp_viva_filter.py), [PR #4668](https://github.com/pipecat-ai/pipecat/pull/4668)). Докстрінг пояснює мотив: «iPhone screening feature is standalone model… preventing later real human speech suppression artifacts». Сам Krisp позиціонує TTS Detector для вихідних дзвінків, де відповідає IVR або інший бот ([BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)). Висновок: гейт існує тому, що ізоляція може зачепитися за першу синтетичну мову і потім гасити людину, яка заговорить після неї. Для вхідних дзвінків абонентів він не потрібен, ехо TTS посеред дзвінка не ловить, а в LiveKit аналога немає.

### Гіпотези режимів відмови для перевірки

Поведінку в ключових для агента випадках Krisp не публікує. Тому таблиця нижче — гіпотези, які корпус має підтвердити або спростувати.

| Режим відмови | Чому очікуємо (висновок) | Як виявити на корпусі |
|---|---|---|
| Абонент мовчить, говорить телевізор | Коли голос один, «найближчий і найгучніший» — це телевізор | Згасання B у дБ, старти VAD і слова витоку за хвилину на B |
| TV на ≥10 дБ гучніший за абонента | Пороги `backgroundSpeakerFix` 10/5 дБ | C при SIR −5/0/+5/+10 дБ |
| TV звучить уже з початку дзвінка | Незгасна оцінка `pnc` закріплює перший голос | Суміші, де TV випереджає абонента на 5–10 с |
| Тихий абонент, гучний зв'язок | Модель без ближнього поля — задокументований симптом «quiet callers» | A на −10…−30 dBFS; співвідношення енергії вихід/вхід |
| Backchannel і сміх | Короткі тихі серії; `blocked.laughter` у назві | Recall «угу» і енергія на кожному backchannel за рівнів 60/75/100 |
| Ехо TTS посеред дзвінка | Pipecat-гейт одноразовий | Сегменти з домішаним `C_agent.wav` на −20 і −10 дБ |
| Друга легітимна людина | Модель придушує її за задумом | Окремі записи, якщо є |

## SDK `krisp_audio`: синхронний `process()`, близько 10% ядра і прохідні відмови

### Три рівні API і один патерн сесії

Krisp постачає SDK на трьох рівнях.

**C++ «Krisp Audio SDK» v9.x** (`Krisp::AudioSdk`) існує у desktop- і server-збірках. Хронологія за історією прикладів Krisp (перевірено, [commit log](https://github.com/krispai/Krisp-SDK-Sample-Apps/commits/krisp-sdk-v9)):

| Дата | Подія |
|---|---|
| 2024-05 | Старий C API у v7/v8 |
| 30.08.2024 | v9.0 |
| 18.02.2025 | v9.2 з підтримкою 24 кГц |
| 18.09.2025 | Linux aarch64, v9.9 |
| 17.02.2026 | v9.14 |
| вересень 2026 | v9.20 (snippet, [changelog](https://sdk-docs.krisp.ai/changelog)) |

**Python-прив'язка `krisp_audio` 1.x** на PyPI відсутня і завантажується з порталу. До 1.10 вона була на pybind11, за кодом Pipecat із 1.11.0 перейшла на nanobind, а 1.12.0 вийшла як `cp312-abi3`. Існують також прив'язки для Go, Node і Rust.

Модель роботи в усіх однакова: один на процес виклик `globalInit(workingPath, licenseKey, licensingCallback, logCallback, logLevel)`, сесії на кожен потік, створені з `*SessionConfig` із `ModelInfo.path` на `.kef`, і синхронний `process(frame, level)` на моно-кадрах фіксованого розміру. Кадри бувають 10/15/20/30/32 мс, частота — 8–48 кГц (C++ приймає й 88.2/96 кГц), формат — int16 або float32. Сесія прив'язана до однієї частоти, а стереокадри інтеграції пропускають без обробки. Кінцевий `globalDestroy()` можна викликати лише після знищення всіх сесій (перевірено, [sample-nc](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/src/sample-nc/main.cpp), [gst-krisp-audio](https://github.com/krispai/gst-krisp-audio)). За заявою Krisp, «multiple audio streams using a single model loaded into memory», тож модель на ~28–29 МБ ділять усі сесії процесу (snippet, [sdk-docs VI](https://sdk-docs.krisp.ai/docs/models-for-conversational-ai)). У C++ є `getSessionStats` із часом розмови і рівнями шуму, у Python статистичний API з'явився в 1.11.0, а `RingtoneCfg` — окремий `.kef` «for inbound» для рингтонів і музики, доданий 26.11.2025 ([commit 95c0eca](https://github.com/krispai/Krisp-SDK-Sample-Apps/commit/95c0eca759dc8c2c97801f3410ab337afa904940)).

| Сесія | Виклик | Типовий кадр | Вихід |
|---|---|---|---|
| `NcInt16` / `NcFloat` (ізоляція) | `process(frame, suppression_level)` | 10 мс | Оброблений кадр тієї самої довжини |
| `VadFloat` | `process(float32)` | 10 мс | Ймовірність мови |
| `TtFloat` (Turn v3) | `process(frame, is_speech, False)` | 20 мс | Ймовірність кінця репліки |
| `IpFloat` | `process(frame, speech_active)` | 20 мс | Ймовірність справжнього перебивання |
| `TtsDetectorFloat` | `process(float32)` | — | Ймовірність синтетичної мови |

Джерела для таблиці: перевірено, [krisp_viva_filter.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/filters/krisp_viva_filter.py), [krisp_viva_turn.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/turn/krisp_viva_turn.py), [IP strategy](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/turns/user_start/krisp_viva_ip_user_turn_start_strategy.py), [krisp_viva_vad.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/vad/krisp_viva_vad.py).

Типовий рівень придушення в різних інтеграціях різний, тому в будь-якому A/B-тесті його треба фіксувати явно:

| Інтеграція | Рівень за замовчуванням |
|---|---|
| Приклади Krisp і GStreamer-елемент | 100 |
| Pipecat `KrispVivaFilter` | 100.0 |
| `livekit-plugins-krisp` | 75 |
| Внутрішній Cloud-бекенд LiveKit | 90 |

**Сигнатура ліцензійної ініціалізації.** Ключ обов'язковий із Python SDK 1.6.1, і виклик виглядає як `globalInit("", key, license_cb, log_cb, LogLevel.Off)`. Для старішої трьохаргументної форми Pipecat має fallback на `TypeError` ([krisp_instance.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/krisp_instance.py)).

**Наслідки переходу на nanobind.** Рівень придушення став float, а масиви на вході мають бути записуваними ([PR #5302](https://github.com/pipecat-ai/pipecat/pull/5302)). Задокументовано й наслідок: з `krisp_audio` 1.12.0 фільтр Pipecat отримував read-only масиви, ловив виняток і пропускав звук — «noise cancellation is silently disabled — no crash, no warning, just unfiltered audio» ([pipecat#5413](https://github.com/pipecat-ai/pipecat/issues/5413)).

### Затримка 15–30 мс і ~10% ядра — оцінки, які треба переміряти на ліцензованих `.kef`

**Затримка.** Krisp публікує «15 ms of algorithmic latency» лише для VI 2.5 і «15 ms latency» для пакета VIVA 2.0 ([Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/)). Конфіги PRO v1 і TEL v2 показують вікно 30 мс із кроком 15 мс і лише минулий контекст (`frameCount` 4); ознак look-ahead там немає (перевірено). Висновок: власна затримка моделі становить 15–30 мс залежно від вікна синтезу. До неї додається 0–10 мс буферизації SDK-кадру і час обчислень. Цей діапазон вкладається в бюджет front-end ≤40 мс, закладений попередніми звітами.

**Обчислення.** Єдині реальні виміри дослідники отримали в ізольованому scratch-середовищі, запустивши Cloud-бекенд `livekit-plugins-krisp-internal` 0.2.0 з вбудованими моделями PRO v1 і TEL v2 проти локальної заглушки замість LiveKit Cloud. Ці цифри наводимо **лише як технічне вимірювання класу моделі** — GRU на ~7 M параметрів. Запуск Cloud-моделей LiveKit проти заглушки чи будь-де поза LiveKit Cloud **не є ліцензованим шляхом**: це не варіант розгортання і не обхід, у репозиторії такого бути не повинно, а ліцензовані `.kef` від Krisp треба переміряти окремо.

Виміри на 4-vCPU Xeon 2.1 ГГц (вимір, [internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.2.0/)):

| Показник | Значення |
|---|---|
| Сталий CPU real-time factor | **0.087–0.101 на потік**, ≈9–10% одного ядра; час CPU ≈ wall time на потоці, що викликає |
| Перший `_process` у процесі | 290–470 мс (ініціалізація SDK, завантаження моделі, авторизація) |
| Наступні нові сесії | 15–30 мс |
| Нулі на початку першого вихідного кадру | 14–27 мс — грубий індикатор алгоритмічної затримки |
| `import livekit.plugins.krisp` | ≈1.25 с |
| maxrss процесу з обома моделями | ≈309 МБ |

Орієнтири вендора щодо CPU скупі: VI lite 2.5 має «3.5x less compute» ([Krisp blog](https://krisp.ai/blog/voice-isolation-2-5/)), а FP16 SIMD знизив CPU моделей VI на armv8a на 30–40% ([Go SDK 1.4.0](https://sdk-docs.krisp.ai/changelog/viva-go-sdk-v140)). Цифру «6-10% single-core CPU per stream» зі стороннього блогу використовувати не можна: джерело не прочитане, а назва «VIVA-VC» незрозуміла ([callsphere](https://callsphere.ai/blog/vw9h-build-voice-agent-krisp-audio-filter-viva-2026)). Висновок: ~10% ядра на asyncio-циклі для одного абонента на job-процес прийнятні, але IP, TP і VAD додадуть ще по сесії з невідомою ціною, і все це рахується до лагу event loop.

### Платформи: Mac arm64 і Linux x86_64 є, Python лише 3.12, aarch64 під питанням

**C++ server SDK** підтримує Linux x64 і armv8a (ARM — з v7.0.2), macOS arm64 і x64 та Windows. Приклади вимагають GCC 9.4+ і Clang 15+ (snippet і перевірено, [Supported Platforms](https://sdk-docs.krisp.ai/docs/supported-platforms-server), [native-cpp README](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/README.md)). Статично влінковані onnxruntime, OpenBLAS, abseil, cpuinfo і libresample, а для ліцензування — OpenSSL, libcurl і zlib ([cmake](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/cmake/krisp.third.party.linux.aarch64.cmake)).

**Python-wheel** звужувався з часом. Python SDK 1.0.0 заявляв Python 3.10–3.13 на Linux x64, Windows x64 і Mac arm64 (snippet, [changelog](https://sdk-docs.krisp.ai/changelog/python-sdk-v100)); документація наводить прикладом `krisp_audio-1.8.0-cp312-cp312-macosx_12_0_arm64.whl` (перевірено, [Pipecat docs](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx)); версія 1.12.0 вийшла як `cp312-abi3` ([pipecat#5413](https://github.com/pipecat-ai/pipecat/issues/5413)). Висновок: **потрібен venv на Python ≥3.12**, тоді як репозиторій декларує `>=3.10`, а локальний venv має 3.11. Linux aarch64 для Python-wheel не підтверджено; оптимізації під armv8 у Python 1.11.0 на це натякають, але питання треба поставити письмово.

**Помилки, що вже траплялися в інтеграціях:**

| Інтеграція | Проблема | Наслідок | Статус |
|---|---|---|---|
| Pipecat | `globalDestroy()` під час роботи нативного коду | SIGSEGV у `libkrisp-audio-sdk` «10–15×/day, always within ~0.5 s of call teardown» | Виправлено: Pipecat більше не викликає `globalDestroy` ([pipecat#5408](https://github.com/pipecat-ai/pipecat/issues/5408), [PR #5411](https://github.com/pipecat-ai/pipecat/pull/5411)) |
| Pipecat | `api_key` зчитує лише перший виклик ініціалізації | Процес із кількома ліцензіями працює під першою | Обмеження SDK |
| Pipecat | nanobind відкидає read-only масиви | Фільтр тихо вимкнено | [pipecat#5413](https://github.com/pipecat-ai/pipecat/issues/5413) |
| LiveKit Cloud NC | Збірка OpenBLAS | Падіння на деяких AMD, поки не задати `OPENBLAS_CORETYPE=Haswell` | [PyPI noise-cancellation](https://pypi.org/project/livekit-plugins-noise-cancellation/) |
| LiveKit | 50-мс кадри з NC | Стрибки затримки Silero | [agents#3894](https://github.com/livekit/agents/issues/3894) |
| LiveKit | Передчасний `_close()` процесора | Нуль оброблених кадрів | Виправлено до 1.8.3 ([agents#5448](https://github.com/livekit/agents/issues/5448)) |

### Ліцензія перевіряється через мережу, а збій не зупиняє аудіо

GStreamer-плагін самого Krisp (квітень 2026) описує механіку прямо: «The server SDK validates the license key on its own internal thread after `globalInit` returns. Any licensing error is stored and surfaced… The pipeline keeps running — the SDK passes audio through after its grace period». У коді те саме сказано інакше: «A licensing error is non-fatal — the SDK continues to pass audio through its grace period» (перевірено, [gst-krisp-audio](https://github.com/krispai/gst-krisp-audio), [gstkrisp_common.cpp](https://github.com/krispai/gst-krisp-audio/blob/243bbecfd98d78fb1b7e82895dd223e5f1fb0e2b/src/gstkrisp_common.cpp)). Приклади Krisp вмикають libcurl лише під `ENABLE_LICENSING`, а на macOS додають фреймворки `Security` і `SystemConfiguration` ([wav-cli](https://github.com/krispai/Krisp-SDK-Sample-Apps/blob/krisp-sdk-v9/native-cpp/src/wav-cli/main.cpp)).

Формулювання двозначне: після grace-періоду модель або продовжує обробляти аудіо як звичайно, або SDK віддає сирий звук. Тривалість grace-періоду, інтервал повторної перевірки, хости ліцензування і поведінку після grace публічно не описано. Збірки мають ще одну особливість: документований пакет Python SDK називається `krisp-viva-uar-python-sdk-*`, де **UAR означає usage auto reporting**, а для Go Krisp уже розділив збірки на UAR і non-UAR ([Go SDK 1.4.0](https://sdk-docs.krisp.ai/changelog/viva-go-sdk-v140), [Pipecat docs](https://github.com/pipecat-ai/docs/blob/main/pipecat/features/krisp-viva.mdx)).

Сторінка безпеки Krisp стверджує: «The SDK accesses the network only for license verification needs. Krisp does not access, collect, or store any audio data», і там само — що метадані «not stored or transmitted» (snippet, [sdk-docs Security](https://sdk-docs.krisp.ai/docs/privacy)). Із UAR це не зовсім узгоджується; найімовірніше, UAR-пакет містить лише лічильники хвилин і сесій, але вміст треба підтвердити письмово. Інтеграції сигнал про збій ліцензії лише логують: Pipecat пише «Krisp licensing error», а LiveKit — `[Krisp Licensing Error: …]` і в README радить на «Silent output» перевірити файл моделі ([PyPI livekit-plugins-krisp](https://pypi.org/project/livekit-plugins-krisp/)).

Для вимоги «аудіо абонента не йде в чужі хмари» це означає таке. Саму вимогу **виконано**: аудіо лишається на хості, назовні йдуть лише ліцензійні дані й дані про використання. Вимогу «жодної залежності від вендора в рантаймі» **не виконано**, доки Krisp не дасть non-UAR або offline-збірку. Відмова м'якша, ніж у ai-coustics, яка за стандартним ключем зупиняє очищення через 10 с без активації або через 5 хв без телеметрії ([ai-coustics changelog](https://docs.ai-coustics.com/sdk/changelog)), але гірша, ніж у NVIDIA AFX, де ліцензійних викликів в API немає. Головний ризик у тому, що збій не видно: ізоляція може тихо зникнути після grace-періоду, тому потрібні алерт на licensing-callback, тест із заблокованим egress на staging і лічильник «оброблено / пропущено сирим».

## Turn Prediction v3 та Interruption Prediction v1 — справжня відмінність Krisp

### Turn Prediction: три покоління аудіо-EOT

Turn Prediction визначає кінець репліки лише за аудіо, без транскрипту. **Turn v1 (2025)** описано як «Audio-only, 6M weights» ([Krisp blog](https://krisp.ai/blog/turn-taking-for-voice-ai/)), і запит на його підтримку в LiveKit закрили як «not planned» ([agents#3094](https://github.com/livekit/agents/issues/3094)). **Turn v2 (листопад 2025)** дає «up to a 6% improvement in F1 score under noisy conditions» ([Krisp blog v2](https://krisp.ai/blog/krisp-turn-taking-v2-voice-ai-viva-sdk/)). **Turn v3** (`krisp-viva-tp-v3.kef`) з'явився в Pipecat 17.04.2026 комітом інженера Krisp і публічно вийшов у VIVA 2.0. На вхід він бере лише аудіо користувача кадрами 10–32 мс плюс **зовнішній VAD-прапорець на кожен кадр**, а на виході дає ймовірність кінця репліки на кожен кадр; Pipecat фіксує COMPLETE при `prob ≥ 0.5` після того, як VAD побачив тишу (перевірено, [krisp_viva_turn.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/turn/krisp_viva_turn.py)). Модель має ~9 M параметрів, 30 МБ, «12+ languages» і рекомендований поріг 0.5 (snippet, [Krisp blog](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/)).

Вендорські цифри для v3 суперечать одна одній. Частка відповідей швидше за 200 мс зросла з 47% до 69% порівняно з v2 ([voicendata](https://www.voicendata.com/artificialintelligence/krisp-expands-voice-ai-infrastructure-with-viva-20-release-11808462)), а крива «FPR vs Mean Shift Time» лежить нижче за SmartTurn і «LiveKit». Проте блог визнає, що Deepgram Flux «marginally ahead on F1 Score (84.60 vs 84.44)» і має нижчий mean shift time за того самого FPR ([Krisp blog](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/)), тоді як BusinessWire пише, що крива Krisp «sat below… Deepgram Flux's».

### Interruption Prediction v1: backchannel чи перебивання

Interruption Prediction v1 (`krisp-viva-ip-v1.kef`, тепер v1.1) — **аудіокласифікатор, що працює лише з англійською**. Він «distinguishes intent-to-take-the-floor from backchannel speech like 'yes' or 'mhm'» ([BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)). За заявами вендора, модель має ~6 M параметрів і 24 МБ, рекомендований поріг **0.4** (Pipecat за замовчуванням бере 0.5), і там, де VAD-перебивання «fires on almost two-thirds of backchannels», IP відділяє їх «with under 6% false positives at the recommended threshold» і «sub-second mean interruption time» ([Krisp blog](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/)).

В інтеграції Pipecat, яку написали інженери Krisp, модель отримує «every frame… regardless of speech state so that the model maintains continuous internal state», другим аргументом `process()` іде VAD-прапорець, рішення «липке» — не більше одного на VAD-сегмент, а ймовірність може досягти піку «one frame *after* the raw VAD goes silent» (перевірено, [IP strategy](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/turns/user_start/krisp_viva_ip_user_turn_start_strategy.py), [Krisp demo](https://github.com/krispai/pipecat-fork-sdk/blob/krisp-viva-demo/scripts/krisp/demo_interrupt_prediction.py)). Символи в нативній бібліотеці LiveKit (`vadKefName`, `audio_volume_calculator.cpp`, `vocabulary_checker.cpp` у просторі `KRISP::InterruptionPrediction`) натякають, що IP-пакет несе власний VAD і гейт гучності ([internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.2.0/)); це висновок. Важливо й те, що IP **не залежить від мовця**: речення з телевізора, сказане поверх агента, цілком може отримати оцінку «справжнього перебивання», тож ізоляція чи Voice Focus має стояти перед ним (висновок).

### Krisp VAD v2 і TTS Detector

**Krisp VAD v2** дає ймовірність мови на кадр для 8–48 кГц і з'явився в Pipecat 0.0.108 від 27.03.2026 ([krisp_viva_vad.py](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/vad/krisp_viva_vad.py)). Для цього стеку його головна цінність — дешеве джерело покадрового VAD-прапорця для TP і IP. **TTS Detector** потрібен лише для вихідних дзвінків, тобто для гейта на старті сесії.

### Pipecat як еталонна інтеграція

Pipecat фактично є еталонною реалізацією, бо його Krisp-код комітять працівники Krisp (`gharutyunyan@krisp.ai`, `apoghosyan@krisp.ai`).

| Обгортка Pipecat | Сесія | Кадр | Роль | З'явилася |
|---|---|---|---|---|
| `KrispVivaFilter` | `NcInt16` | 10 мс | Фільтр на вході | 0.0.90 (10.10.2025); TTS-гейт — 1.5.0 (04.07.2026) |
| `KrispVivaTurn` | `TtFloat` | 20 мс | Стратегія зупинки ходу | 0.0.99 (13.01.2026); API v3 — 1.1.0 (27.04.2026) |
| `KrispVivaIPUserTurnStartStrategy` | `IpFloat` | 20 мс | Стратегія старту ходу, тобто barge-in | 1.1.0 (27.04.2026) |
| `KrispVivaVadAnalyzer` | `VadFloat` | 10 мс | VAD | 0.0.108 (27.03.2026) |

Джерело: перевірено, [CHANGELOG](https://github.com/pipecat-ai/pipecat/blob/main/CHANGELOG.md).

Референсний приклад ставить `start=[KrispVivaIPUserTurnStartStrategy(threshold=0.5), TranscriptionUserTurnStartStrategy()]` ([voice-krisp-viva.py](https://github.com/pipecat-ai/pipecat/blob/main/examples/voice/voice-krisp-viva.py)). Другий елемент — fallback, що спрацьовує на **будь-який** транскрипт, зокрема на «yeah». Тож у рецепті Pipecat IP переважно пришвидшує справжні перебивання, а придушення backchannel тримається лише на тому, що STT не встиг видати текст. Лексикон цього репозиторію сильніший за такий fallback, тому чесне перенесення має поєднувати IP з лексиконом, а не з голим тригером на транскрипт (висновок).

### LiveKit не пропонує жодної з цих моделей

Станом на 26.09.2026 `livekit-plugins-krisp` 0.4.3 експортує лише ізоляцію, без жодних символів turn, IP, VAD чи TTS (перевірено, [PyPI](https://pypi.org/pypi/livekit-plugins-krisp/json)). Нативна бібліотека `krisp-internal` при цьому лінкує `KRISP::InterruptionPrediction`, `KRISP::TurnTakingV3` і `vad_v2_processor.cpp`, проте її FFI відкриває лише NC-сесії (перевірено). Запит [agents#6033](https://github.com/livekit/agents/issues/6033) на self-hosted adaptive interruption або офіційну інтеграцію Krisp IP/Turn відкритий із 09.06.2026 і досі без відповіді, а форк `livekit-agents-fork-sdk` в організації Krisp — порожній знімок upstream. Власні аналоги LiveKit працюють лише в Cloud: це adaptive interruption із заявами «86% precision and 100% recall at 500 ms overlap» і «rejects 51% of VAD-based barge-ins» ([LiveKit blog](https://livekit.com/blog/adaptive-interruption-handling)) та ймовірність backchannel у `turn-detector v1`. Локальний `v1-mini` такої ймовірності не має (перевірено, [livekit-agents 1.8.3](https://pypi.org/project/livekit-agents/1.8.3/)). Для планування варто виходити з того, що **офіційного шляху від LiveKit у 2026 році не буде**, а будь-яке використання IP/TP тут — власне перенесення BSD-2-обгорток Pipecat на `krisp_audio`.

### Як вбудувати IP і TP v3 у цей репозиторій

Усе в цьому підрозділі — висновок, спертий на код, прочитаний вище, і на код репозиторію.

**Варіант (а): IP як класифікатор у `bargein_server`.** Сервер відповідає на кожне бінарне вікно, відновлює новий хвіст через `new_tail()` і починає нове перекриття, якщо між запитами проходить понад 0.35 с. Імовірність він повертає константним списком `[p] * max(2, n_samples // 400)`. Пороги класифікатора такі: `min_overlap_s=0.25`, `single_word_s=0.6`, `maai_threshold=0.45`, `no_asr_min_s=0.6`, `long_overlap_s=2.0` (перевірено, `voice_agent/local_voice_agent/bargein_server/server.py`, `classifier.py`). Клієнт LiveKit 1.8.3 шле аудіо 16 кГц лише тоді, коли агент говорить: перший запит із префіксом `AUDIO_PREFIX_DURATION=1.0` с, далі кожні 0.1 с увесь буфер до 3 с, з таймаутом 0.7 с. Довжину префікса сервер не отримує, бо `session.create` передає лише `sample_rate`, `num_channels`, `threshold`, `min_frames` і `encoding` (перевірено, [livekit-agents 1.8.3](https://pypi.org/project/livekit-agents/1.8.3/), `inference/interruption.py`).

Звідси дизайн. Одна `IpFloat`-сесія створюється на WebSocket-сесію після єдиного `globalInit` у процесі, і в неї подається **лише новий хвіст** кадрами по 20 мс (320 семплів float32, поділених на 32768). Префікс 1.0 с дзеркалиться в конфігурації сервера, а VAD-прапорець рахує серверний VAD (Krisp VAD v2 або Silero). 20-мс ймовірності переводяться на 25-мс сітку протоколу через максимум, а `bargein_detected` повертається, щойно будь-який кадр перекриття перетне θ = 0.4, причому рішення липке в межах перекриття. Між перекриттями сервер нічого не бачить, тож два варіанти — нова сесія, прогріта префіксом, або одна сесія з розривом — треба порівняти офлайн. Правило об'єднання з лексиконом (висновок) виглядає так:

| Умова | Рішення |
|---|---|
| У транскрипті є interrupt-токен | Перебити |
| Транскрипт — лише backchannel або continuer | Не перебивати, навіть якщо IP високий. Захист від хибних IP на емфатичне «yeah!» і на «do not stop» |
| IP ≥ θ | Перебити |
| IP < θ, але ≥2 змістові слова або перекриття ≥ `long_overlap_s` | Перебити. Страховка від пропусків IP |

**Варіант (б): IP як сигнал у PolicyRunner і фільтрах, поруч із `MaaiReading`.** Детектор `KrispIpDetector` підключається до `stt_node` у тому ж місці, де MaAI викликає `push_user`. Він годує сесію **безперервно** з VAD-прапорцем і повертає `KrispReading(status, p_int_max, p_int_last, evaluated_at, window_s, clock)`. У `decide_text` і `BargeinClassifier.decide` значення `p_int_max ≥ θ` пропускає коротке interim, не чекаючи фіналу, що знижує латентність справжніх перебивань. Значення `p_int_max < θ_low` при ≤2 змістових словах відкидає сегмент як backchannel — у тому самому слоті, що `maai_backchannel`. `awaiting_answer` лишається пріоритетним, бо IP нічого не знає про запитання. Варіант (б) найточніше відтворює використання в Pipecat і, на відміну від `/bargein`, дає **живий shadow-режим**: `signals.maai` і `signals.krisp_ip` логуються на тих самих подіях.

**Варіант (в): Turn v3 замість `turn-detector v1-mini`.** Підключити його можна лише через приватний протокол `_StreamingTurnDetector` 1.8.3, де `push_audio` годує `TtFloat`, `predict()` одразу повертає останню ймовірність, а `unlikely_threshold()` дорівнює 0.5.

| | LiveKit `v1-mini` (у репозиторії) | Krisp TP v3 |
|---|---|---|
| Де працює | Локально, ctypes | Локально, `krisp_audio` і ключ |
| Вхід | Вікно аудіо 1.2 с | Потік 20-мс кадрів + VAD-прапорець |
| Коли питають | Після тиші VAD ≥0.2 с (у репозиторії 0.55 с) | Безперервно |
| Поріг для англійської | 0.36 | 0.5 |
| Розмір | ~108 МБ ваг | ~9 M параметрів, 30 МБ |

Порівняння зроблено за кодом LiveKit ([livekit-agents 1.8.3](https://pypi.org/project/livekit-agents/1.8.3/)) і заявами Krisp. LiveKit питає детектор лише після кінця мови за VAD, тож заявлені «<200 ms» Krisp тут не реалізуються без зменшення `min_silence_duration` (межа 0.25 с) і `min_endpointing_delay`. Починати варто з shadow-логування обох ймовірностей на кожному кінці VAD, враховуючи власний endpointing у `riva_server`.

| | Лексикон (опції 1/2) | MaAI `bc_det` | Krisp IP v1 |
|---|---|---|---|
| Потрібен текст ASR | Так, однослівні interim утримуються | Ні | Ні |
| Семантика («stop», «do not stop», відповідь на «?») | Так, детерміновано | Ні | Ні |
| Латентність | Прив'язана до ASR | Кадри 80 мс | Кадри 20–40 мс |
| Бачить аудіо агента | — | Так (двоканальний) | Ні |
| Ліцензія | У репозиторії | MIT-код, ліцензія ваг під питанням | Пропрієтарна, ключ |
| Перевірено тут | Тести є | Реальна модель ще не запускалась | Ні |

MaAI прогнозує саме «backchannel-ність», а IP — намір перехопити хід. Жодна з двох аудіомоделей не розв'язує проблему фонових мовців. Найкраща комбінація, найімовірніше, така: IP або MaAI для ранніх рішень без ASR, а лексикон — як override (висновок).

## `livekit-plugins-krisp` 0.4.3 придатний для OSS лише з явним `krisp_license`

### Код плагіна по версіях

Дослідники розпакували всі 37 релізів з PyPI і виділили чотири покоління коду (перевірено, [PyPI JSON](https://pypi.org/pypi/livekit-plugins-krisp/json)).

| Версії (дати) | Що змінилося | Залежності |
|---|---|---|
| 0.1.1 (16.04.2026) … 0.2.5 (09.07.2026) | Лише license-режим ([PR #4370](https://github.com/livekit/agents/pull/4370)); **`ValueError` на будь-який невідповідний розмір кадру**; рівень 100 | `livekit-agents` від ≥1.5.3 до ≥1.6.5, `numpy` |
| 0.2.6 (18.07.2026) | Cloud-автентифікація і адаптивна буферизація ([PR #5914](https://github.com/livekit/agents/pull/5914)); видалено `KrispSDKManager` | + `krisp-internal>=0.1.0` |
| 0.2.7 (25.07.2026) | `voice_isolation_telephony()`, `VivaMode` ([PR #6510](https://github.com/livekit/agents/pull/6510)); **internal-wheel імпортується одразу при імпорті модуля** | `krisp-internal==0.2.0` |
| 0.2.8 (03.08.2026) | Рівень за замовчуванням 100 → **75** ([PR #6640](https://github.com/livekit/agents/pull/6640)) | Те саме |
| 0.2.9 … 0.4.3 (23.09.2026) | Код ідентичний 0.2.8; змінюється лише мінімальна версія; 0.4.3 вимагає `livekit-agents>=1.8.3` | Те саме |

**Публічний API 0.4.3** складається з `voice_isolation(*, auth_provider=None, noise_suppression_level=75)`, `voice_isolation_telephony(...)`, `KrispVivaFilterFrameProcessor` і `auth.livekit_cloud` / `auth.krisp_license`. **Бекенд обирається** в такому порядку: явний `auth_provider`, потім застарілий `model_path=`, потім license-режим, якщо задано **обидві** змінні `KRISP_VIVA_SDK_LICENSE_KEY` і `KRISP_VIVA_FILTER_MODEL_PATH`, і лише наостанок Cloud. Тому, якщо задано лише шлях до моделі, `voice_isolation()` **мовчки обирає Cloud-бекенд** (вимір). `KrispLicenseAuthProvider` перевіряє, що `.kef` існує, але **приймає порожній ключ** (вимір).

**Ініціалізація і teardown `krisp_audio`.** Модуль імпортується ліниво, без залежності в метаданих і без закріпленої версії, викликом `globalInit("", key, cb, cb, LogLevel.Off)`. Singleton має лічильник посилань, ключ береться від першого, хто його отримав, а `globalDestroy()` викликається, коли лічильник доходить до нуля, — лише в `__del__`, а не в `_close()`. Саме від такого патерну Pipecat відмовився через SIGSEGV.

**Модель і сесія.** У license-режимі `mode` бекенду не передається, тож `voice_isolation()` і `_telephony()` поводяться однаково, а модель визначає `.kef`. Використовується `NcInt16` з `Fd10ms`. Сесію на 16 кГц **створюють заздалегідь у конструкторі**, а для будь-якої іншої частоти її перестворюють усередині `_process`, тобто модель перевантажується просто на аудіошляху. Ресемплінгу немає; вхід накопичується до цілих 10-мс чанків, а на вихід віддається `min(вхід, готове)` без доповнення нулями.

Як поводиться буферизація на різних кадрах (вимір із фейковим SDK):

| Вхідні кадри | Вихід |
|---|---|
| 16 кГц / 20 мс | Та сама довжина, два виклики по 160 семплів, **нуль додаткової затримки** |
| 24 кГц / 50 мс | Сесію `NcInt16.create(24000)` створено посеред аудіо |
| 16 кГц / 25 мс | Постійне відставання на 5 мс |
| Перший кадр на 5 мс | Кадр на 0 семплів |

**Обробка помилок.** Стерео проходить сирим із разовим попередженням. Непідтримувана частота (наприклад, 22 050) дає `ValueError` із `_process`: `rtc.AudioStream` ловить його і на **кожному кадрі** логує «Frame processing failed, passing through original frame». Виняток у `session.process` чи неправильна довжина виходу — сирий чанк. Тобто **кожна відмова — це сирий звук, ніколи не тиша**, а вихідний кадр не несе `userdata`. Рівень придушення обрізається до `int` (55.7 → 55) і передається Python-int; чи приймає це nanobind-збірка `krisp_audio`, не перевірено, але масиви записувані, тож ризик #5413 тут нижчий (вимір). Власного потоку чи executor немає: `process` виконується синхронно в `AudioStream._run()` на asyncio-циклі. У 1.8.3 RoomIO створює потік з `auto_close_noise_cancellation=False`, тож переданий напряму процесор ніколи не закривається і живе між доріжками, а `Plugin.register_plugin` падає поза головним потоком (перевірено, `room_io/_input.py`, `agents/plugin.py`).

**Поправка до попереднього огляду.** Той писав, що плагін «працює з публічним wheel `krisp_audio`». Насправді **`krisp_audio` на PyPI немає** (`/pypi/krisp-audio/json` повертає 404), а починаючи з 0.2.7 **навіть license-режим вимагає встановити й імпортувати пропрієтарний `livekit-plugins-krisp-internal`** — ≈106 МБ розпакованого wheel під LiveKit ToS. Це питання і для юридичного рев'ю, і для розміру образу.

**Cloud-бекенд.** Нативний фільтр `krisp_internal` пропускає аудіо без змін, доки кімната не передасть токен, а потім робить `GET {room_url}/settings` з JWT кімнати і `POST {room_url}/report` з `featureUsage: KRISP_VIVA` для кожної доріжки. README прямо каже, що цей шлях «authenticates through LiveKit Cloud», а сам wheel поширюється під LiveKit ToS (перевірено, [internal 0.2.0](https://pypi.org/project/livekit-plugins-krisp-internal/0.2.0/), [README 0.4.3](https://pypi.org/project/livekit-plugins-krisp/0.4.3/)). На self-hosted сервері **це не ліцензований шлях, і використовувати його не можна**; репозиторій має зробити його недосяжним через явний `krisp_license`, перевірку ключа і тест на тип бекенда. Офіційний `krisp_minimal_example.py` сам пояснює, чому поза агентом береться саме `KrispLicenseAuthProvider` ([example](https://github.com/livekit/agents/blob/main/livekit-plugins/livekit-plugins-krisp/examples/krisp_minimal_example.py)).

### Дизайн інтеграції за зразком `aic.py`

Репозиторій уже має потрібний шаблон. `aic.build_enhancer` повертає FrameProcessor із не-Cloud автентифікацією, `aic.enhance()` викликає `_process`, `agent.py` передає процесор лише за `AUDIO_ENHANCEMENT=aic`, а `replay_stt` і `vad_scores` приймають `--enhance none|aic` (перевірено, `voice_agent/local_voice_agent/{aic.py,agent.py,settings.py,tools/}`). Нижче — дизайн, код не змінювався.

| Місце | Зміна | Навіщо |
|---|---|---|
| `voice_agent/pyproject.toml` | Extra `krisp = ["livekit-plugins-krisp==0.4.3"]` (тягне `krisp-internal==0.2.0`). `krisp_audio` ставиться вручну з порталу у venv на Python 3.12. `*.kef` і `krisp_audio-*.whl` — у `.gitignore` | Ліцензований wheel і моделі не вендоряться |
| `local_voice_agent/krisp.py` | `build_enhancer()` з явним `krisp.auth.krisp_license(license_key=…, model_path=…)`; `pin_sdk()` у prewarm; `enhance()` = `_process`; `enhancer_description()` з ім'ям і sha256 `.kef`, `krisp_audio.getVersion()` і версіями плагінів, але ніколи з ключем | Дзеркало `aic.py`; жодного авто-вибору бекенда |
| `settings.py` | `AUDIO_ENHANCEMENT=none\|aic\|krisp`; `KRISP_VIVA_SDK_LICENSE_KEY` (`field(repr=False)`), `KRISP_VIVA_FILTER_MODEL_PATH` (перевірка `.kef`), `KRISP_NOISE_SUPPRESSION_LEVEL` (75); `audio_input_sample_rate=16000`, `audio_input_frame_ms=20` (кратне 10); `enhancement_route=all\|vad` | Явні параметри з валідацією |
| `agent.py` | `AudioInputOptions(sample_rate=16000, frame_size_ms=20, noise_cancellation=krisp.build_enhancer(settings))`; процесор створюється в `entrypoint` на кожен job | 16-кГц сесію створено поза аудіошляхом, нуль буферизації |
| `tools/enhancement.py`, `replay_stt`, `vad_scores` | Диспетчер `--enhance none\|aic\|krisp`; fail-fast для WAV не на 8/16/24/32/44.1/48 кГц (підказка `ffmpeg -ar 16000`); версії й sha256 у `*.meta.json` | Той самий `_process`, що й у кімнаті |
| E2: `IsolatedVAD` | `noise_cancellation=None`; обгортка `agents.vad.VAD`, чий `stream()` створює внутрішній потік і Krisp-процесор на кожен потік та підміняє `push_frame` на `push(enhance(enh, frame))` | STT, turn і interruption отримують сирий звук, VAD — ізольований |
| `tests/test_krisp.py` | Фейковий `krisp_audio` у `sys.modules`; 7 кейсів + opt-in `KRISP_SMOKE=1` | CI без ліцензії |
| Моніторинг | Лічильник «оброблено / пропущено сирим» по чанках; лог licensing-callback | Прохідні відмови інакше невидимі |

**Пін SDK.** `pin_sdk()` будує процесор, одразу викликає `close()` і тримає об'єкт у `proc.userdata` до кінця життя процесу. `_close()` звільняє сесію, але посилання на SDK залишає, тож `globalDestroy` не спрацює, поки живуть інші сесії. Вимір із фейковим SDK підтвердив: коли пін живий, видалення процесора job не викликає `globalDestroy`. Пін також перевіряє ключ і модель на етапі prewarm і забирає одноразові 0.3–0.5 с ініціалізації з шляху дзвінка. Імпортувати `livekit.plugins.krisp` треба в головному потоці.

**Тести.** `tests/test_krisp.py` будується за патерном `test_aic.py` і гермети́чного тесту LiveKit ([test_krisp_frame_buffer.py](https://github.com/livekit/agents/blob/main/tests/test_krisp_frame_buffer.py)) і покриває сім кейсів: бекенд завжди license, навіть якщо задано лише змінну моделі; без ключа — помилка з назвою змінної, а ключа немає в `repr(Settings)`; 16 кГц / 20 мс на вході дають ту саму довжину на виході і два виклики по 160 семплів; `TypeError` сесії дає вихід, рівний входу (фіксує fail-open); пін блокує `globalDestroy`; `replay_stt` і `vad_scores` з `--enhance krisp` проходять через `fake_riva`; нарешті, для E2 фейковий енхансер, що обнуляє кадри, дає VAD без мови, тоді як STT отримує оригінал. Smoke-тест із реальним wheel перевіряє, що вихід відрізняється від входу і що Python-int рівень працює з nanobind.

**E2, Mac і альтернатива.** Обгортка `IsolatedVAD` зберігає вирівнювання часу, бо довжина виходу дорівнює довжині входу для кадрів, кратних 10 мс. Вона працює навіть у `console`, яка обходить `noise_cancellation`, але консоль додає WebRTC NS, тож із room-режимом результати не порівнювані; альтернатива — upstream [PR #7269](https://github.com/livekit/agents/pull/7269) з каналом `lk.audio.raw`, проте він відкритий і в 1.8.3 його немає. Для розробки на Mac потрібні venv на 3.12, wheel для macOS arm64 з порталу і режим `dev` проти локального `livekit-server --dev`; license-режиму Cloud не потрібен. Довгостроково варто розглянути **власний FrameProcessor на ~100 рядків** за зразком `KrispVivaFilter` Pipecat (BSD-2) зі спільним менеджером SDK для всіх сесій (висновок): IP, TP і VAD однаково вимагатимуть прямих сесій `krisp_audio` з одним `globalInit` на процес, двічі ініціалізувати чи знищувати SDK не можна, а менеджер плагіна приватний. Власна обгортка одночасно прибирає пропрієтарний `krisp-internal`, дає float-рівень для nanobind і правило «ніколи не викликати `globalDestroy`». Для першої оцінки VI простіше взяти плагін 0.4.3.

## Доступ — через продажі, ціна — з чужих прайсів, якість — зі слів вендора

### Доступ, ліцензія й умови

**Самообслуговування для VIVA немає.** Спершу подається заявка через developer-портал Krisp (`sdk.krisp.ai` / `developers.krisp.ai`), після чого заявника розподіляють на трек «Early Stage (Developers)» з «contact sales custom pricing» або на Enterprise із SSO, HIPAA/SOC 2/GDPR, BAA і виділеним менеджером (snippet, [UsagePricing](https://www.usagepricing.com/blueprint/krisp), [krisp.ai/developers](https://krisp.ai/developers/)). На порталі видно «licensed SDK version IDs» і генерується API-ключ, а для CI є REST API `GET /v2/sdk/versions/{id}/download-urls`, що повертає S3-посилання на 300 с для збірки і `.kef`; при цьому «A VIVA build without its model files will not run» (третя сторона, [api-evangelist](https://github.com/api-evangelist/krisp/blob/main/skills/krisp-sdk-download-pipeline.md)). Умови trial (тривалість, ліміт хвилин, чи можна тестувати в проді) не опубліковані. Конкурент ai-coustics стверджує, що Krisp «doesn't allow production testing during the trial period» ([ai-coustics](https://ai-coustics.com/blog/comparing-krisp-and-ai-coustics-real-time-audio-enhancement-which-is-best-for-you)), але це заява конкурента.

Права на моделі видаються окремо для кожної родини. Pipecat Cloud постачає лише модель ізоляції, а IP не дає, і в тому ж issue сказано, що моделі Krisp «can only be distributed on Pipecat Cloud» ([pipecat#4994](https://github.com/pipecat-ai/pipecat/issues/4994), [Pipecat Cloud](https://github.com/pipecat-ai/docs/blob/main/pipecat-cloud/guides/krisp-viva.mdx)). Отже, у замовленні VI, IP, TP, VAD і TTS треба перелічити явно, а версії SDK і `.kef` закріплювати разом, бо IP v1.1 зі старим SDK не працює.

**Юридичні умови** видно лише частково. Сам SDK — «a commercial product» під окремою ліцензією, текст якої не публічний (snippet, [sdk-docs Licensing](https://sdk-docs.krisp.ai/docs/licensing-information)). Публічні Terms of Use забороняють reverse engineering, а для конкурентів мають пункт про бенчмарки ([Terms](https://krisp.ai/terms-of-use/)). MSA автоматично припиняється, якщо ліцензії не куплено протягом шести місяців, і платежі не повертаються, крім суттєвого порушення з боку Krisp ([MSA](https://krisp.ai/master-subscription-agreement/)). Серед сертифікацій заявлено SOC 2, PCI DSS і HIPAA із застереженням «availability depends on plan», а trust-центр Krisp працює на Vanta ([api-evangelist](https://github.com/api-evangelist/krisp/blob/main/security/krisp-trust-center.yml)); ISO 27001 і тим більше FedRAMP пошукові резюме згадують, але документально це не підтверджено. Висновок: у контракті треба прямо назвати власні Linux-сервери, dev-Mac і CI, приватні образи, внутрішні бенчмарки проти ai-coustics і NVIDIA, а також офлайн-поведінку.

### Ціни

| Джерело | Ціна | Статус |
|---|---|---|
| Krisp напряму | Не опублікована; «application-gated» | Snippet, [UsagePricing](https://www.usagepricing.com/blueprint/krisp) |
| Оцінка третьої сторони | Поминутно «via SDK token», до **~$0.001/хв** на обсязі | Snippet, [UsagePricing](https://www.usagepricing.com/blueprint/krisp) |
| Pipecat Cloud (перепродаж) | 10 000 хв/міс безкоштовно, далі **$0.0015/хв** | Перевірено, [Pipecat Cloud](https://github.com/pipecat-ai/docs/blob/main/pipecat-cloud/guides/krisp-viva.mdx) |
| LiveKit Cloud (перепродаж) | 100 / 1 000 / 10 000 хв на Build / Ship / Scale, далі $0.0012/хв — або $0.002–0.004/хв за іншим джерелом; окремо тарифікується з 01.05.2026 | Суперечливі snippet-и, [livekit.com/pricing](https://livekit.com/pricing), [forasoft](https://www.forasoft.com/blog/article/voice-ai-agents-livekit-guide), [community](https://community.livekit.io/t/voice-isolation-system-payment/1657/3) |
| Retell denoising | $0.005/хв; що це Krisp, не підтверджено | Snippet, [cekura](https://www.cekura.ai/blogs/retell-ai-pricing-per-minute) |

За 100–500 тис. хв на місяць ставки $0.001–0.0015 дають **≈$100–750 на місяць**, тобто $1.2–9 тис. на рік; можливі мінімальні платежі треку не видно. Для порівняння, ai-coustics бере $149–599 на місяць за ті самі обсяги, а offline-ліцензію дає лише в Enterprise, «від ~$2 000/міс» за snippet-ом ([ai-coustics pricing](https://ai-coustics.com/pricing)), тоді як NVIDIA NVAIE коштує $4 500 за GPU на рік ([NVIDIA](https://docs.nvidia.com/ai-enterprise/planning-resource/licensing-guide/latest/pricing.html)). Якщо Krisp назве ціну в цьому діапазоні, за вартістю він буде на рівні ai-coustics. Але якщо Voice Focus лишиться основним ізолятором, а Krisp потрібен лише заради IP, ці витрати **додаються** до ai-coustics, а не замінюють їх (висновок).

### Компанія і підтримка

Ризик життєздатності вендора низький. Krisp має ≈343–370 працівників ([Owler](https://www.owler.com/company/krisptechnologies)), вбудований у понад 130 продуктів голосового AI і обробляє >12 млрд хвилин на рік (заява, [BusinessWire](https://www.businesswire.com/news/home/20260506612131/en/Krisp-Launches-VIVA-2.0-Introducing-Voice-Infrastructure-for-Voice-AI-Agents)). Операційні ризики вищі: публічного SLA для SDK немає, `status.krisp.ai` закрито за Cloudflare Access, «99.9%» обіцяно лише для Voice Translation API, а політики deprecation немає ([api-evangelist](https://github.com/api-evangelist/krisp/blob/main/lifecycle/krisp-lifecycle.yml)). Канали підтримки — help center, форма продажів і дашборд, а релізи часті й іноді ламають сумісність, як з IP v1.1 і переходом на nanobind. Позитивний сигнал зрілості — сам Krisp підтримує інтеграцію в Pipecat, включно з інструментами оцінки: `demo_interrupt_prediction.py` і release-eval із реальним шумним barge-in ([krispai/pipecat-fork-sdk](https://github.com/krispai/pipecat-fork-sdk)).

### Докази якості

**Незалежних кількісних оцінок VIVA не знайдено.** Уся доказова база ділиться на три групи.

**Цифри самого Krisp:**

| Модель | Заявлений результат | Джерело |
|---|---|---|
| VI 2.5, 10 STT-систем від 7 вендорів (Deepgram, NVIDIA, Soniox, ElevenLabs, AssemblyAI, Google, Cartesia) | Середній WER **15.35% → 8.22% (−46.4%)** | [Krisp blog VI 2.5](https://krisp.ai/blog/voice-isolation-2-5/) |
| VI 2.5, записи з конкурентними мовцями | **35.92% → 10.90% (−69.7%)** | Там само |
| VI 2.5, умови | «no harm on clean audio», найбільші виграші в реверберації | Там само |
| VI 2.5 проти v2.1 на складних записах | 15.42% → 11.61% | Там само |
| VI 2.5, інший агрегат | «43% (17.9% → 10.2%) across 11 speech-to-text engines» | Там само |
| BVC (2025), AMI + Silero + Whisper v3 base | У 3.5 раза менше хибних спрацювань VAD, precision більш ніж на чверть вища, WER покращено понад удвічі | [Krisp blog](https://krisp.ai/blog/improving-turn-taking-of-ai-voice-agents-with-background-voice-cancellation/) |
| TP v3 та IP v1 | Цифри наведено вище | [Krisp blog](https://krisp.ai/blog/voice-ai-turn-taking-interruption-prediction/) |

Два агрегати VI 2.5 арифметично узгоджені кожен сам по собі, тож це два різні зведення, а не одрук; модель NVIDIA в тесті не названо. Друга група — конкурент: ai-coustics пише, що Krisp NC «raised WER by over 10pp on English competing speech», але тестувалося звичайне шумозаглушення, а не VIVA-ізоляція, тож проти VI це не доказ ([ai-coustics](https://ai-coustics.com/blog/comparing-krisp-and-ai-coustics-real-time-audio-enhancement-which-is-best-for-you)). Третя група — спільнота, чиї сигнали стосуються надмірного придушення BVCTelephony, тихого вимкнення після зміни ABI і попиту на IP ([agents#6033](https://github.com/livekit/agents/issues/6033), [pipecat#4994](https://github.com/pipecat-ai/pipecat/issues/4994)). Для Nemotron і Sortformer вирішальні метрики — хибні VAD і barge-in, recall backchannel і помилки діаризації — не публікує жоден вендор.

## Проти Voice Focus і Speaker Focus Krisp виграє turn-taking, а не ізоляцією

| Критерій | Krisp VIVA | ai-coustics Voice Focus 2.2 | NVIDIA AFX Speaker Focus |
|---|---|---|---|
| Як обирає мовця | Близькість і рівень, без enrollment; незгасний стан `pnc` | Акустичний передній план, «signal-based… without locking onto a single voice» ([docs](https://docs.ai-coustics.com/guides/speech-enhancement-for-asr)) | «Prominent speaker», без enrollment ([NVIDIA](https://docs.nvidia.com/maxine/afx/latest/AboutTheEffects/AboutSpeakerFocusEffect.html)) |
| Актуальні моделі | VI-tel v2.1, VI 2.5 / lite (портал); у LiveKit — BVC 2025 року | `quail_vf_l/s` (VF 2.2) у репозиторії | `speaker_focus_{16,48}k.trtpkg` |
| Затримка | 15 мс (VI 2.5, заява); за конфігом 15–30 мс | ~30 мс (заява, [VF 2.1](https://ai-coustics.com/blog/quail-voice-focus-2.1)) | Не опублікована |
| CPU / GPU | CPU; ≈10% ядра на потік (вимір на BVC-класі) | CPU; RTF не опубліковано | Лише датацентровий GPU |
| Mac dev / Linux prod | arm64 / x86_64; aarch64 Python не підтверджено; лише cp312 | arm64 / x86_64 і aarch64 | Немає / x86_64 з GPU |
| Телефонія 8 кГц | tel v2.1 «8–16 kHz», VI 2.5 narrowband | Заявлено 8 і 16 кГц | Немає |
| Моделі для turn-taking | **IP v1 (backchannel), TP v3, VAD v2, TTS Detector** | VAD Voice Focus, аналізатор Tyto | Немає |
| Інтеграція з LiveKit 1.8.3 | Плагін у `krisp_license`; IP/TP — власне перенесення | Готовий плагін, уже в репозиторії | Власний sidecar |
| Рантайм без мережі | Асинхронна перевірка ліцензії + UAR; після grace поведінка невідома | Стоп через 10 с / 5 хв без offline-ліцензії | Ліцензійних викликів немає |
| Ціна | ~$0.001–0.0015/хв (треті сторони) | $149–599 на місяць | $4 500 за GPU на рік |
| Статус і докази | GA; лише вендорські дані, серед STT є NVIDIA | GA; вендорські дані, відкритий Dawn Chorus | Early Access четвертий рік; даних немає |

Спільне в цих трьох рішеннях важливіше за відмінності. Кожне обирає «передній план» за акустикою, тож кожне ризикує пропустити телевізор, коли абонент мовчить, і придушити легітимного другого мовця. Тому voiceprint-гейт на слотах Sortformer лишається обов'язковим за будь-якого вибору.

**В ізоляції** Krisp має дві реальні переваги над Voice Focus: моделі `tel`, налаштовані на 8–16 кГц, і м'якший режим відмови ліцензії. Проти нього — продаж лише через відділ продажів, вимога Python 3.12, UAR, пропрієтарний `krisp-internal` у плагіні і те, що VF вже інтегровано. Тож Krisp VI має сенс лише за помітної переваги на B і C.

**У turn-taking** Krisp не має конкурентів серед локальних рішень. IP v1 — єдина комерційна модель, явно навчена відрізняти backchannel від перебивання, яка працює без хмари. Її аналог у LiveKit існує лише в Cloud, а MaAI поки не перевірений на реальній моделі. Це і є вирішальний аргумент на користь пілоту (висновок).

## Двадцять два питання, три етапи вимірювань і шість воріт

### Питання до Krisp (sales та engineering), письмово

| № | Питання | Навіщо |
|---|---|---|
| 1 | Які точно `.kef` (назви, версії, дати) відповідають VI v3, VI 2.5, VI lite 2.5 і `vi-tel-v2.1`? «v3» і «2.5» — одна модель? | Конфлікт назв |
| 2 | Яку VI-модель ви радите для вхідних SIP 8 кГц і WebRTC 48 кГц, якщо ASR працює на 16 кГц? Чи є нативна narrowband-модель? | Вибір `tel` проти `pro` |
| 3 | Яка алгоритмічна затримка і look-ahead у кожної VI-моделі, а також в IP і TP? | Бюджет ≤40 мс |
| 4 | Скільки CPU (мкс на кадр) і пам'яті на сесію потребують VI tel/lite, IP, TP і VAD на x86 AVX2, Apple M і Graviton? Скільки потоків на ядро? | Sizing |
| 5 | Як VI обирає мовця? Що вона робить, коли єдиний голос — телевізор, і чи «захоплює» перший голос на старті? Чи є reset API сесії? | Головний сценарій хибних barge-in |
| 6 | Що означає `blocked.laughter`? Чи зберігаються сміх і тихі backchannel? Який рівень придушення ви радите для STT і для VAD? | Recall «угу» |
| 7 | IP v1.1: мови, внутрішній крок кадру (40 мс?), поріг 0.4 чи 0.5, криві precision/recall на телефонії, поведінка на ехо агента, чи осмислений холодний старт із префіксом 1 с, семантика VAD-аргументу, чи несе `.kef` власний VAD | Дизайн для bargein-сервера |
| 8 | TP v3: що означає третій аргумент `TtFloat.process(frame, is_speech, False)`, чи є reset, які мови і скільки CPU? | Адаптер `_StreamingTurnDetector` |
| 9 | Які хости і порти контактує `globalInit`? Як часто повторна перевірка, скільки триває grace-період, що після нього (обробка, сирий звук, тиша, виняток), які коди повертає callback? | Поведінка без мережі |
| 10 | Що саме відправляє UAR? Чи є non-UAR Python-збірка і offline/air-gapped ліцензійний файл, і скільки вони коштують? | «Нічого назовні» |
| 11 | Чи працює перевірка ліцензії через наш HTTP-проксі або allowlist IP? | Egress-політика проду |
| 12 | Письмове підтвердження, що жодні аудіо чи похідні метадані не залишають хост, плюс DPA | Приватність абонентів |
| 13 | Точна матриця wheel: Python 3.11/3.12/3.13 (abi3?), manylinux aarch64, тег glibc, мінімальна macOS, вимоги до AVX2 | Образи dev і prod |
| 14 | Чи приймає nanobind-`process()` Python-int як рівень? Чи потокобезпечний `process()` для різних сесій у різних потоках? Контракт `globalInit`/`globalDestroy`? | Сумісність із плагіном LiveKit |
| 15 | Модель ціни для self-hosted: поминутна чи фіксована за сервер або рік, мінімальні платежі, умови trial (строк, ліміт, чи можна в прод) | Бюджет |
| 16 | Які моделі входять у ліцензію: VI (tel/pro/2.5/lite), IP, TP, VAD, TTS? | Права на моделі |
| 17 | Як рахуються хвилини без UAR? Чи є права на аудит? | Облік |
| 18 | Чи дозволено ставити SDK на N власних Linux-серверів, dev-Mac, CI-раннери і в приватні образи контейнерів? | Обсяг розгортання |
| 19 | Чи можна проводити внутрішні бенчмарки проти ai-coustics і NVIDIA і показувати результати партнерам? | Пункт про бенчмарки |
| 20 | Підтримка: SLA, час реакції, доступність ліцензійного сервера, повідомлення про несумісні зміни, строк підтримки версій | Експлуатація |
| 21 | Чи підтримує Krisp license-режим `livekit-plugins-krisp`? Чи потрібен і чи дозволений `livekit-plugins-krisp-internal`, якщо використовується лише license-режим (те саме — до LiveKit)? Чи плануєте офіційні IP/TP для LiveKit (agents#6033)? | Юридична чистота плагіна |
| 22 | Звіт SOC 2 Type II; підтвердження ISO 27001 | Безпека |

### План вимірювань на корпусі A/B/C

Нагадаємо корпус: **A** — лише абонент, **B** — лише фон, **C** — суміш, плюс `C_mix.agent.jsonl` із таймлайном агента.

**Етап 0 — доступ і smoke.** Ліцензія, wheel і `.kef` встановлюються на Mac і на прод-хост, після чого виконуються чотири перевірки. Smoke-тест підтверджує, що вихід відрізняється від входу на шумній мові, licensing-callback чистий, а лічильник пропусків дорівнює нулю. Прогін із заблокованим egress у мережевому namespace із захопленням трафіку показує, що відбувається до й після grace-періоду і чи видно це в логах. Далі йдуть 100 циклів teardown без SIGSEGV і перевірка детермінізму — два прогони і diff, як уже заведено в репозиторії.

**Етап 1 — мікробенчмарки.** Затримка міряється крос-кореляцією вхід/вихід (GCC-PHAT, ±200 мс) на чистих WAV з A. CPU — як p50/p99 `_process` і `IpFloat.process` на кадр на M-серії і на прод-CPU, окремо для VI-tel v2.1, VI 2.5 і lite. Окремо фіксуються час `globalInit` і створення сесії, RSS на сесію, а також лаг event loop при 1 і N одночасних job.

**Етап 2 — ізоляція на A/B/C.** Прогін наявними `replay_stt`, `vad_scores` і `replay_policy` з однаковими кадрами 16 кГц / 20 мс.

| Код | STT отримує | VAD, turn і barge-in отримують | Навіщо |
|---|---|---|---|
| R0 | Сирий | Сирий | Базова лінія |
| VF* | Найкраща конфігурація Voice Focus з попереднього плану | Відповідно | **Чинний кандидат, якого треба перемогти** |
| K-tel@{60, 75, 100} | VI-tel v2.1 або VI 2.5 | Те саме | Повна ізоляція і крива рівня |
| K-lite | VI lite 2.5 | Те саме | Дешевший варіант |
| K-v2 | Старий `tel-v2` | Те саме | Ефект покоління, перевірка виправлення v2 → v2.1 |
| K-E2 | Сирий | `IsolatedVAD` з VI-tel | Схема, яку радять ASR-вендори |
| K-vad | Сирий | Krisp VAD v2 (через адаптер у стилі `AicVAD`) на ізольованому | Внесок власного VAD Krisp |

Метрики беруться з попередніх планів: WER абонента на A з парними дельтами і bootstrap-95% CI; recall коротких реплік і backchannel; слова витоку, старти VAD і хибні EOU за хвилину на B; хибні barge-in на B і C; на C — помилки на словах абонента (S+D) окремо від вставок із фону; DER і кількість ID Sortformer разом із `primary_speaker_switches`. До них додаються метрики саме для Krisp, що б'ють у його задокументовані слабкості: співвідношення енергії вихід/вхід на A за рівнів −10…−30 dBFS (тихий абонент), енергія на кожному backchannel і на сміху, згасання B у дБ, коли абонент мовчить, частка 500-мс вікон на C, де вихід корелює з B сильніше, ніж з A, і час «захоплення» мовця в сумішах, де TV випереджає абонента.

**Етап 3 — IP і TP.** Спершу потрібна розмітка сегментів користувача, що перекриваються з мовою агента, на `backchannel` / `barge_in` / `background` / `noise` — це ≈1–2 дні ручної роботи. Далі пишеться новий інструмент `tools/krisp_ip_scores.py` за зразком `maai_scores.py`. Він розбиває WAV 16 кГц на 20-мс кадри, рахує VAD-прапорець через Krisp VAD v2 або Silero, подає **кожен** кадр в `IpFloat.process(frame, vad)` і пише JSONL `{"kind":"krisp_ip","t","audio_pos_s","p_int","vad"}`, а `*.meta.json` фіксує версію SDK, sha256 `.kef`, θ і sha256 WAV. `replay_policy.merge` отримує порядок `{"agent":0,"maai":1,"krisp_ip":2,"stt":3}` і прапорець `--krisp`, а `PolicyRunner.krisp(t, p)` — вікно читання. Обрізання логу не повинно змінювати попередніх рішень. Окремий `bargein_replay` будує вікна в стилі LiveKit (префікс 1 с, крок 0.1 с, до 3 с) з таймлайну агента і проганяє `_analyse` сервера. Так варіант «вікна» порівнюється з варіантом «безперервний tap» на тому самому аудіо. Контрольна точка: `demo_interrupt_prediction.py` Krisp на тих самих файлах має дати ту саму поведінку.

| Код | Політика | Front-end |
|---|---|---|
| P0 | Чинна: лексикон + MaAI (`text_filter` / `interruption_classifier`) | R0, VF*, K-tel |
| P1 | Лише лексикон | Те саме |
| IP@{0.3, 0.4, 0.5} | Лише Krisp IP | Те саме |
| IP+L | IP як основний сигнал + лексикон як override (правила вище) | Те саме |
| IP+L+M | IP + MaAI + лексикон | Те саме |

Метрики етапу 3 — частка розмічених backchannel, що спричинили перебивання (Krisp заявляє <6%), recall справжніх barge-in, латентність рішення від початку мови на p50/p90 (Krisp заявляє «sub-second»), хибні спрацювання на B за хвилину мови агента, а також окремо кейси «do not stop» і відповіді на запитання агента. Для TP v3 ведеться shadow-лог ймовірностей `v1-mini` і TP v3 на кожному кінці VAD на A і C проти розмічених кінців реплік, а метрикою є частка передчасних EOT за однакової латентності.

### Ворота go/no-go і вартість

| Ворота | Умова проходу | Якщо не пройдено |
|---|---|---|
| K0. Комерція і право | Письмові відповіді на питання 9–12 і 15–21; ціна ≤ ~$0.0015/хв або фіксована ставка, порівнянна з VF; IP і TP у ліцензії; non-UAR/offline або погоджений egress лише до ліцензійного хоста; контракт називає власні сервери, Mac і CI | No-go або очікування |
| K1. Платформа й експлуатація | Wheel працює на macOS arm64 і на архітектурі проду під Python 3.12; поведінка при втраті ліцензії виміряна і має алерт; нуль пропусків на корпусі; жодного SIGSEGV за 100 циклів | No-go до виправлення |
| K2. Затримка і CPU | Лаг VI ≤30 мс, увесь front-end ≤40 мс; VI + IP ≤ ~20% ядра на потік на прод-CPU; p99 лагу event loop зростає не більше ніж на 10 мс | Лише офлайн або E2 |
| K3. Безпека абонента (A) | ΔWER проти R0 ≤ +0.5 п.п. (95% CI); recall коротких реплік і backchannel не нижчий за R0 і VF*; енергія тихого абонента на −30 dBFS не гірша, ніж у VF* | No-go для VI на шляху STT |
| K4. Виграш ізоляції (B/C) | Слова витоку і хибні barge-in за хвилину **щонайменше на 20% нижчі, ніж у VF*** | VI не йде в прод; лишається VF |
| K5. Виграш IP | Частка backchannel, що перебили агента, **щонайменше на 30% відносно нижча, ніж у P0**, за recall barge-in ≥ P0 і медіанної латентності рішення ≤ P0; на B хибних не більше | IP не йде в прод |

Пороги 20% і 30% — наш вибір, а не галузева норма. Для VI поріг нижчий, ніж 30% у звіті про Speaker Focus, бо Krisp працює на CPU, має готовий плагін і статус GA. Для IP поріг вищий, бо лексикон + MaAI вже є, а IP додає пропрієтарну залежність і приватні протоколи LiveKit.

| Стаття | Оцінка (етапи 0–3) | Інтеграція в прод | Прод, на рік |
|---|---|---|---|
| Ліцензія | Просити безкоштовний eval; умови невідомі | — | ≈$1.2–9 тис. за 100–500 тис. хв/міс за оцінками третіх сторін; мінімальні платежі невідомі; у варіанті «лише IP» — поверх $1.8–7.2 тис. за ai-coustics |
| Інженерія | Етапи 0–2 (`krisp.py`, інструменти, тести, прогони): ≈4–6 днів; етап 3 (`krisp_ip_scores`, `replay_policy`, розмітка, `bargein_replay`): ≈1–1.5 тижня | IP у `bargein_server` ≈3–5 днів; tap у PolicyRunner ≈3–5 днів; shadow-адаптер TP ≈3 дні; моніторинг і пін ≈2–3 дні — разом ≈2–3 тижні | ≈2–3 дні на повторну валідацію кожного релізу SDK чи `.kef` |
| Інфраструктура | Наявні Mac і Linux, лише CPU | +≈10% ядра на потік на кожну модель (переміряти); образ на Python 3.12; +≈106 МБ `krisp-internal`, якщо лишається плагін | — |
| Ризик | Для проду нульовий | Приватні протоколи LiveKit (`/bargein`, `_StreamingTurnDetector`), тож 1.8.3 треба закріпити | Залежність від ліцензійного сервера Krisp; несумісні релізи; прив'язка до вендора |

Можливих результатів три:

| Результат | Коли настає | Що далі |
|---|---|---|
| **No-go** | Не пройдено K0 чи K1, або ні K4, ні K5 | Лишаються Voice Focus, лексикон і MaAI. До Krisp варто повернутися, якщо з'являться offline-Python або офіційні IP/TP у LiveKit |
| **Go «лише IP»** | Пройдено K5, не пройдено K4 | Krisp IP стає сигналом у `bargein_server` і PolicyRunner, ізоляцією лишається VF |
| **Повний go** | Пройдено і K4, і K5 | VI-tel + IP; VF як резерв |

Ми вважаємо найімовірнішим «лише IP» або no-go (висновок). Причина: VI має ту саму сліпу пляму, що й VF, і навряд чи випередить його на B на 20%. Натомість IP атакує проблему, для якої в репозиторії поки немає перевіреної аудіомоделі.

## Висновок

Бренд «VIVA» приховує, що в найпоширенішій інтеграції — LiveKit Cloud — під цією назвою досі працює BVC 2025 року, тож оцінювати треба не «Krisp» загалом, а конкретний `.kef`, названий у контракті; поради й відгуки про «VIVA в LiveKit» до VI-tel v2.1 і VI 2.5 відношення не мають. Головніша зміна в розумінні полягає в тому, що цінність Krisp для цього агента лежить у Interruption Prediction, а не в ізоляції. Три ізолятори на ринку реалізують ту саму евристику «акустичного переднього плану», тоді як локальний класифікатор «backchannel чи перебивання» є лише в Krisp, а лексикон репозиторію вже сильніший за еталонний fallback Pipecat. Отже, найкращий результат дасть не заміна наявних механізмів, а IP як ранній сигнал без ASR під контролем лексикону, і порівняння з MaAI на тому самому корпусі одночасно відповість, чи потрібен пропрієтарний IP узагалі.

Друга практична річ стосується залежності від хмари. У Krisp у хмару йде не аудіо, а ліцензія: асинхронна перевірка, UAR і невизначений grace-період. Разом із тим, що кожна відмова плагіна дає сирий звук, це означає, що лічильник «оброблено / пропущено» і тест без egress потрібні ще до першого прогону корпусу — інакше A/B-тест може непомітно порівнювати сирий звук із сирим.
