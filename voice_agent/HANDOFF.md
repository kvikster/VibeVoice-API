# Handoff: оцінка STT, політики перебивань і ai-coustics

Гілка `agent/laughing-lovelace-h1s3z1`, каталог `voice_agent/`. Три частини роботи:
1. **Replay WAV через STT** з подіями до і після speaker suppression (задача 1 з рев'ю).
2. **Shadow-режим і відтворення рішень** політик перебивань (задача 2).
3. **Опція ai-coustics:** очищення звуку (Quail / Voice Focus) і VAD, плюс інструменти, щоб оцінити їх на тому самому корпусі.

Повна інструкція із запуском — у [README.md](README.md): розділи «Опція 3» та «Оцінка на власному корпусі».

## TL;DR

- **STT:** `tools.replay_stt X.wav` подає WAV у реальному темпі в той самий STT, що в агента (NeMo-Speech.cpp `riva_server` → `livekit-plugins-nvidia` → `MultiSpeakerAdapter`). За **один прогін** пишуться обидва рівні подій (`raw` і `adapter`) і `*.meta.json`. З `--enhance aic` перед STT стоїть очищення ai-coustics.
- **Політика:**
  - наживо — `INTERRUPTION_MODE=shadow DECISION_LOG=…`: агент поводиться як LiveKit без фільтрів і лише логує рішення;
  - офлайн — `tools.replay_policy` дає ті самі рішення без ASR і агента.
- **VAD:** `tools.vad_scores X.wav --vad silero|aic|aic_enhancer [--enhance aic]` пише часову шкалу VAD. Так на B (лише фон) видно хибні спрацювання, а на C — пропущену мову абонента.
- **Окремий внесок MaAI:** `tools.maai_scores`, потім `replay_policy` з `--maai` і без нього.
- **Що не запускалось на реальних моделях** (не було Mac/GPU, ключа ai-coustics і доступу до HuggingFace та CDN ai-coustics): `riva_server`, MaAI, ai-coustics. Решту перевірено тестами, деталі в розділі «Перевірка».

## Налаштування

```bash
cd voice_agent && uv venv && source .venv/bin/activate
uv pip install -e ".[test]"          # livekit-agents==1.8.3
uv pip install -e ".[aic]"           # ai-coustics: aic-sdk 3.2.0 + livekit-plugins-ai-coustics 0.3.2
uv pip install -e ".[maai]"          # опційно, важке (torch, transformers)
cp .env.example .env                 # AIC_LICENSE_KEY=... (ключ з developers.ai-coustics.com; не комітьте)
riva_server --config config/asr.mac.yaml --bind 127.0.0.1:50051   # окремо, див. README
```

## Як прогнати A / B / C

```bash
# 1. STT без очищення і з ним
for x in A_caller B_background C_mix; do
  python -m local_voice_agent.tools.replay_stt corpus/$x.wav --out runs/$x.stt.jsonl
  python -m local_voice_agent.tools.replay_stt corpus/$x.wav --enhance aic --out runs/$x.aic.stt.jsonl
done

# 2. VAD: Silero проти ai-coustics, окремо і після очищення
for x in A_caller B_background C_mix; do
  for v in silero aic; do
    python -m local_voice_agent.tools.vad_scores corpus/$x.wav --vad $v --out runs/$x.vad.$v.jsonl
  done
  python -m local_voice_agent.tools.vad_scores corpus/$x.wav --enhance aic --vad aic_enhancer \
      --out runs/$x.vad.aic_enhancer.jsonl
done

# 3. Політика на подіях C (і на C з очищенням); часова шкала агента — на шкалі audio_pos_s
for s in stt aic.stt; do
  python -m local_voice_agent.tools.replay_policy runs/C_mix.$s.jsonl \
      --agent corpus/C_mix.agent.jsonl --out runs/C_mix.$s.decisions.jsonl
done

# 4. Опційно MaAI
python -m local_voice_agent.tools.maai_scores corpus/C_mix.wav --agent-wav corpus/C_agent.wav \
    --out runs/C_mix.maai.jsonl
python -m local_voice_agent.tools.replay_policy runs/C_mix.stt.jsonl \
    --agent corpus/C_mix.agent.jsonl --maai runs/C_mix.maai.jsonl --out runs/C_mix.decisions.maai.jsonl
```

Часова шкала агента — JSONL з рядками `{"kind": "agent", "audio_pos_s": 3.2, "state": "speaking" | "listening", "text": "..."}`. Якщо `text` закінчується на «?», агент після цього чекає відповіді.

**Що з чим порівнювати:**

| Питання | Що дивитись |
|---|---|
| Слова абонента губить ASR чи suppression? | фінали `layer: "raw"` проти `layer: "adapter"` у C; `adapter_action: "dropped"` на словах абонента |
| Допомагає ASR очищення ai-coustics? | `C.aic.stt` проти `C.stt`: слова абонента, `word_speaker_tags`, перемикання primary speaker |
| Voice Focus прибирає фон ще до діаризації? | у `B.aic.stt` фіналів фонових мовців має бути менше, ніж у `B.stt` (чи взагалі нуль) |
| Скільки чекати на текст? | `t` проти `audio_pos_s` і `end_time_s` фіналів |
| Коли primary speaker перемикається на фон? | `meta.summary.primary_speaker_switches` і `primary_speaker_before` |
| Хибні спрацювання VAD? | `start_of_speech` у `B.vad.*` (лише фон) |
| Пропущена мова абонента? | інтервали мовлення в `C.vad.*` проти `A.vad.*` |
| Що забирає / блокує політика? | `C.*.decisions`: `action`, `reason`, `interruption` |

## Задача 1: `tools/replay_stt.py`

**Що відповідає на питання «слова втрачає ASR чи suppression»:**
- Рядок `layer: "raw"` — подія, як вона дійшла до `MultiSpeakerAdapter`. Поле `adapter_action`: `passed` / `modified` / `dropped`.
- Рядок `layer: "adapter"` — що отримав би агент; `source_seq` посилається на raw-подію.
- Коли фінал фонового мовця відкидається, агент отримує порожній фінал (`cleared_suppressed_final: true`). Так поводиться сам адаптер LiveKit.
- **Primary speaker:** `primary_speaker` після кожної raw-події. `primary_speaker_before` з'являється, коли основний мовець змінився. У `meta.summary.primary_speaker_switches` — список усіх перемикань.
- **Затримка тексту:** `t` (монотонний час отримання від старту) проти `audio_pos_s` (скільки аудіо вже подано), плюс `start_time_s` / `end_time_s` слів у фіналах.
- **Мітки мовців по словах:** `word_speaker_tags` — сирі мітки Sortformer до мажоритарного голосування плагіна. Плагін `nvidia` зводить їх до одного `speaker_id` на весь фінал, тож у змішаних фрагментах тут видно, що саме він зробив.
- **Відсутні дані не підставляються.** В interim у NeMo немає `speaker_id`, `words` і `word_speaker_tags` — ключі просто відсутні.
- **Кінець WAV.** Після нього подається `--tail-silence` (1 с), потім `end_input()`. `riva_server` віддає останні фінали, скрипт чекає закриття потоку (`summary.drained`).
- **`--enhance aic`.** Кожен кадр проходить через той самий FrameProcessor ai-coustics, що й на вході кімнати. У `meta.enhancement` пишуться модель, рівень, утримання VAD і чутливість.
- **Meta:**
  - версії SDK і моделі;
  - `stt_options` (що реально пішло в плагін) і `adapter_options` (пороги primary-детектора);
  - `server_config` від `GetRivaSpeechRecognitionConfig`, або причина, чому він недоступний;
  - знімок `config/asr.mac.yaml` із sha256;
  - sha256 WAV, git-коміт.
- **Приклад:** `examples/replay_stt.sample.jsonl` і `.meta.json`, 14 рядків. Згенеровано на **скриптованому фейковому** Riva-сервері (`tests/fake_riva.py`), не на реальній моделі; схема та сама.
- **Застереження:**
  - скрипт підключається до двох приватних місць livekit-agents 1.8.3 (`MultiSpeakerAdapterWrapper._detector`, `_convert_to_speech_data` у стрімі NVIDIA), лише читає;
  - плагін NVIDIA віддає час слів у мілісекундах (`start_ms` / `end_ms`), а час фіналу — у секундах;
  - `START_OF_SPEECH` плагін шле один раз на потік.

## Задача 2: shadow + replay

**Одна реалізація для live і replay:** `policy_runner.PolicyRunner`.
- Годинник він не читає, а вхід із часом, меншим за попередній, відкидає з помилкою. Тому відтворення детерміноване і не бачить майбутнього.
- Живий фільтр (`backchannel/filter.py`) у режимах `enforce` і `shadow` викликає той самий runner.
- Рішення текстового фільтра — чиста функція `backchannel/policy.py::decide_text`.

**На кожну подію STT — два записи:**

| | `text_filter` (опція 1) | `interruption_classifier` (опція 2 на транскриптах STT) |
|---|---|---|
| вердикт | `action` pass/hold/drop + окремо `interruption` interrupt/no_interrupt/not_applicable | `decision` interrupt/wait/no_interrupt/not_applicable |
| причина | `reason` (interrupt_token, backchannel_*, continuer_phrase, maai_backchannel, short_interim_awaits_final, phrase_prefix_awaits_final, awaiting_answer, …) | `reason` (overlap_too_short, interrupt_token, content_words, maai_backchannel, phrase_prefix_waiting, asr_pending/empty/error/timeout, no_user_utterance, …) + `detail` |
| контекст | `t`, `type`, `text`, `agent.state`, `agent.since_speaking_s`, `agent.awaiting_answer` | те саме + `signals.elapsed_overlap_s` |
| сигнали | токени, фрази, кількість значущих слів, `maai` | `asr.status` / `asr.text`, `maai`, кількість слів |
| пороги | `thresholds` | `thresholds` |

`maai` завжди присутнє: або `{"status": "unavailable"}`, або `p_bc`, `evaluated_at`, `window_s`, `clock`.

**Гарантії та як їх перевірено:**
- **Shadow нічого не видаляє, не затримує і не перериває.** Перевірено у справжньому `AgentSession` livekit/agents 1.8.3 (`livekit_harness/test_zz_local_filter.py`): стани агента й моменти перебивання збігаються з контрольним прогоном без фільтра до 10 мс.
- **Відтворення журналу дає те саме.** Живий журнал відтворюється в записані рішення один в один (той самий тест і `tests/test_replay_policy.py`). Два прогони одного журналу дають однаковий вихід; обрізання журналу не змінює попередніх рішень (тест на кожну точку обрізання).
- **Набір перевірок** (`tests/test_policy_cases.py`, `examples/policy_cases.*.jsonl`), у двох контекстах, без MaAI:

| Фраза | Агент говорить: фільтр / класифікатор | Агент спитав і чекає |
|---|---|---|
| I am with you | drop continuer_phrase / no_interrupt | pass awaiting_answer |
| Please proceed | drop continuer_phrase / no_interrupt | pass awaiting_answer |
| Yes | drop backchannel_tokens / no_interrupt | pass awaiting_answer |
| Okay | drop backchannel_tokens / no_interrupt | pass awaiting_answer |
| Stop | pass interrupt_token → interrupt / interrupt | pass awaiting_answer |
| Do not stop | drop continuer_phrase / no_interrupt | pass awaiting_answer |

### Зміни політики, які впливають на порівняння

Ці зміни внесено в межах задачі 2, бо набір перевірок виявив проблеми:
1. **Continuers** («I am with you», «please proceed», «go on», «do not stop», «don't stop») тепер backchannel. Вони зіставляються **раніше** за слова-перебивання, тож «do not stop» не перебиває. «Do not stop, wait» перебиває.
2. **«yes»** додано до backchannel. Натомість **відповідь на запитання не фільтрується ніколи**: якщо остання репліка агента закінчилась «?», grace-вікно не діє (`awaiting_answer`). Раніше вікно AssemblyAI (1 с) з'їдало б швидке «Yes» після запитання.
3. **Незавершений початок фрази** в interim («do not», «I am», «please») тепер чекає фіналу: `phrase_prefix_awaits_final` / `phrase_prefix_waiting`. Без цього класифікатор опції 2 перебивав на частковому «Do not» до того, як прийде «stop».
4. **Класифікатор опції 2 на транскриптах STT.** Перекриття починається з першого транскрипту, тобто пізніше за реальний початок мовлення на латентність ASR. Тому `elapsed_overlap_s` тут занижений відносно аудіо-сервера `/bargein`. Для реплік, що приходять одним фіналом із часом слів, початок зсувається назад на тривалість мовлення.

## Опція ai-coustics: очищення звуку і VAD

Незалежна від `INTERRUPTION_MODE`, код у `local_voice_agent/aic.py`.

| Змінна | Значення | Що робить |
|---|---|---|
| `AUDIO_ENHANCEMENT` | `aic` | очищення на вході кімнати, до STT, VAD і TurnDetector. Модель `AIC_ENHANCER_MODEL`: `quail_vf_l` (за замовчуванням) і `quail_vf_s` — Voice Focus, прибирають шум **і фонові голоси**; `quail_l` і `rook_s` — лише шум |
| `VAD_BACKEND` | `silero` | як раніше |
| | `aic` | `AicVAD`: VAD-модель ai-coustics (`vad-2.1-xxs-16khz`) у скінченному автоматі Silero |
| | `aic_enhancer` | прапорець мовлення, який рахує очищувач на вихідному сигналі (`ai_coustics.VAD()`); потрібен `AUDIO_ENHANCEMENT=aic` |

**Як влаштовано:**
- Очищення — офіційний `livekit-plugins-ai-coustics` 0.3.2 з `Auth.ai_coustics_api(license_key)`, тобто з вашим ключем і без LiveKit Cloud.
- `AicVAD` — адаптер `aic_sdk.Vad` під інтерфейс моделі Silero. Пороги, мінімальна мова і тиша, префікс і експоненційне згладжування (α 0.35) ті самі, що в Silero, тож різниця між `silero` і `aic` — лише в моделі.

**`tools/vad_scores.py`** пише записи `kind: "vad"` на шкалі WAV:
- `type: "inference"` з `p_speech` і `speaking`. VAD очищувача віддає лише булевий прапорець, тому в нього тільки `speaking`;
- `type: "start_of_speech"` / `"end_of_speech"` з тривалостями.

У `*.meta.json` — модель, опції автомата, `prediction_delay_samples` (на скільки передбачення ai-coustics відстає від аудіо; час подій на це **не** зсувається), налаштування очищення і версії.

**Що важливо знати:**
- **Режим кімнати.** LiveKit застосовує очищення лише в режимі кімнати (`dev` / `start`). У `console` доступний тільки `VAD_BACKEND=aic`. Інструменти оцінки очищення застосовують самі, їм кімната не потрібна.
- **Мережа й ліцензія.**
  - Аудіо з машини не виходить.
  - SDK активує сесію і звітує про використання на сервери ai-coustics, якщо в ліцензії немає offline entitlement.
  - Моделі при першому використанні тягнуться з CDN ai-coustics. Для VAD є `AIC_VAD_MODEL_PATH`. Як моделі отримує бінарник плагіна, я перевірити не зміг.
  - `AIC_TELEMETRY=0` (за замовчуванням) вимикає OpenTelemetry-експорт і ставить `DO_NOT_TRACK=1`. Ключ у `repr` налаштувань не потрапляє.
- **Неправильний ключ.** Перевірено на реальному бінарнику плагіна: плагін логує `License key format is invalid…`, вимикає очищення до кінця сесії і далі пропускає аудіо без змін. Агент не падає.
- **TurnDetector.** Потоковий `TurnDetector` вимагає від VAD `min_silence_duration` ≥ 0.25 с. `AicVAD` бере 0.55 с, як Silero.
- **Утримання тиші у VAD очищувача.** `AIC_ENHANCER_VAD_HOLD_S` = 0.55 с за замовчуванням. Це моє припущення за аналогією з Silero; його треба підібрати на корпусі.
- **Діаризація бачить уже очищений сигнал.** Voice Focus стоїть до Sortformer. Фонові голоси можуть зникнути до діаризації: це і мета, і ризик, якщо модель прийме абонента за фон.

## Що свідомо не зроблено

- **Живий shadow для сервера `/bargein`.** В adaptive-режимі LiveKit повністю довіряє відповіді сервера: відповідь «не перебивати» робить агента неперебивним, а «перебивати» обриває потік аудіо для цього перекриття. Нейтральної відповіді немає. Натомість сервер має `--decision-log` зі станом ASR (`pending` / `received` / `empty` / `error` / `timeout`), MaAI і порогами, а класифікатор оцінюється в shadow/replay на подіях STT.
- **Компенсація затримки передбачення ai-coustics.** Затримка записується в meta, але час подій на неї не зсувається.
- **Реальні прогони** `riva_server`, MaAI і ai-coustics — див. TL;DR.

## Перевірка

| Що | Результат |
|---|---|
| `pytest` у `voice_agent/` | 104 passed |
| `./livekit_harness/run.sh` (клон livekit/agents@1.8.3) | 8 passed |
| ruff (E, F, W, B) | чисто |

Покрито тестами:
- `replay_stt` через справжній плагін `nvidia` і `MultiSpeakerAdapter` проти фейкового gRPC Riva: обидва рівні, відкинутий фінал фонового мовця, останній фінал після кінця WAV, meta; із `--enhance` — кожен кадр проходить через очищувач до STT;
- `replay_policy`: детермінізм, причинність, MaAI з вікном і без, прийом виходу `replay_stt`, відтворення живого журналу;
- ai-coustics:
  - `AicVAD` на фейковому SDK: автомат Silero дає початок мови ~0.5 с і кінець ~2.05 с на тоні 0.5–1.5 с; ключ, вимкнена телеметрія, завантаження моделі або локальний файл;
  - VAD очищувача на кадрах із прапорцем;
  - Silero через той самий `vad_scores`;
  - реальний бінарник плагіна з неправильним ключем;
  - валідація налаштувань;
- `maai_scores` і обв'язка MaAI з фейковою моделлю;
- журнал рішень сервера `/bargein`.

## Відкриті питання

1. **Реальний `riva_server`.** Прогнати `replay_stt` на вашому корпусі й перевірити, що схема подій відповідає прикладу. Особливо: чи дає NeMo-Speech.cpp слова в interim і як часто `word_speaker_tags` змішані всередині одного фіналу.
2. **Параметри політики.** Налаштувати `FILTER_GRACE_S`, `INTERIM_MIN_WORDS`, `stop_history_eou_ms` і пороги primary-детектора за результатами A/B/C.
3. **ai-coustics із ключем:**
   - чи потрібна ліцензія з offline entitlement, якщо машини без інтернету;
   - яку модель очищення брати (`quail_vf_l` проти `quail_vf_s` проти `quail_l`) — за `C.aic.stt` і діаризацією;
   - підібрати `AIC_VAD_THRESHOLD` і `AIC_ENHANCER_VAD_HOLD_S` за `vad_scores` на A/B/C;
   - чи не зрізає Voice Focus абонента в змішаних фрагментах.
4. **MaAI.** Перевірити ліцензію ваг, потім порівняти `--maai` і без нього на однакових подіях.
