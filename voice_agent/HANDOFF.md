# Handoff: інструменти оцінки STT і політики перебивань

Гілка `agent/laughing-lovelace-h1s3z1`, каталог `voice_agent/`. Цей документ описує дві задачі з рев'ю:
1. replay WAV через STT з подіями до і після speaker suppression;
2. shadow-режим і відтворення рішень політик.

Повна інструкція із запуском — у [README.md](README.md), розділ «Оцінка на власному корпусі».

## TL;DR

- **Задача 1:** `python -m local_voice_agent.tools.replay_stt X.wav --out X.stt.jsonl`. WAV подається в реальному темпі в той самий STT, що в агента (NeMo-Speech.cpp `riva_server` → `livekit-plugins-nvidia` → `MultiSpeakerAdapter`). За **один прогін** пишуться обидва рівні подій (`raw` і `adapter`) і `*.meta.json` з версіями й конфігом.
- **Задача 2:**
  - Наживо: `INTERRUPTION_MODE=shadow DECISION_LOG=…`. Агент поводиться як LiveKit без фільтрів і тільки логує рішення обох політик.
  - Офлайн: `python -m local_voice_agent.tools.replay_policy events.jsonl --agent agent.jsonl [--maai maai.jsonl]` дає ті самі рішення без ASR і агента.
- **Внесок MaAI окремо:** `tools.maai_scores` рахує часову шкалу MaAI з WAV. Прогін `replay_policy` з `--maai` і без нього показує, що саме додає MaAI.
- **Реальний `riva_server` і реальна MaAI тут не запускались** (не було Mac/GPU і доступу до HuggingFace). Усе інше перевірено тестами, деталі нижче.

## Як прогнати A / B / C

```bash
cd voice_agent && source .venv/bin/activate          # livekit-agents==1.8.3, див. README
riva_server --config config/asr.mac.yaml --bind 127.0.0.1:50051   # окремо

for x in A_caller B_background C_mix; do
  python -m local_voice_agent.tools.replay_stt corpus/$x.wav --out runs/$x.stt.jsonl
done

# політика на подіях C; часова шкала агента на тій самій шкалі, що audio_pos_s
python -m local_voice_agent.tools.replay_policy runs/C_mix.stt.jsonl \
    --agent corpus/C_mix.agent.jsonl --out runs/C_mix.decisions.jsonl

# опційно MaAI (extra [maai]) і повтор з ним
python -m local_voice_agent.tools.maai_scores corpus/C_mix.wav --agent-wav corpus/C_agent.wav \
    --out runs/C_mix.maai.jsonl
python -m local_voice_agent.tools.replay_policy runs/C_mix.stt.jsonl \
    --agent corpus/C_mix.agent.jsonl --maai runs/C_mix.maai.jsonl --out runs/C_mix.decisions.maai.jsonl
```

Часова шкала агента — JSONL з рядками `{"kind": "agent", "audio_pos_s": 3.2, "state": "speaking" | "listening", "text": "..."}`. Якщо `text` закінчується на «?», агент після цього чекає відповіді.

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

## Зміни політики, які впливають на порівняння

Ці зміни внесено в межах задачі 2, бо набір перевірок виявив проблеми:
1. **Continuers** («I am with you», «please proceed», «go on», «do not stop», «don't stop») тепер backchannel. Вони зіставляються **раніше** за слова-перебивання, тож «do not stop» не перебиває. «Do not stop, wait» перебиває.
2. **«yes»** додано до backchannel. Натомість **відповідь на запитання не фільтрується ніколи**: якщо остання репліка агента закінчилась «?», grace-вікно не діє (`awaiting_answer`). Раніше вікно AssemblyAI (1 с) з'їдало б швидке «Yes» після запитання.
3. **Незавершений початок фрази** в interim («do not», «I am», «please») тепер чекає фіналу: `phrase_prefix_awaits_final` / `phrase_prefix_waiting`. Без цього класифікатор опції 2 перебивав на частковому «Do not» до того, як прийде «stop».
4. **Класифікатор опції 2 на транскриптах STT.** Перекриття починається з першого транскрипту, тобто пізніше за реальний початок мовлення на латентність ASR. Тому `elapsed_overlap_s` тут занижений відносно аудіо-сервера `/bargein`. Для реплік, що приходять одним фіналом із часом слів, початок зсувається назад на тривалість мовлення.

## Оновлення: ai-coustics (VAD і покращення звуку)

Нова незалежна опція, деталі в README («Опція 3»). Для оцінки на корпусі:
- **Порівняння ASR з покращенням і без:** `replay_stt --enhance aic` подає аудіо через ai-coustics перед STT, так само як `AUDIO_ENHANCEMENT=aic` у кімнаті. У `meta.enhancement` записується модель і налаштування. Порівнюйте з прогоном без `--enhance` на тих самих A/B/C.
- **Порівняння VAD:** `tools.vad_scores X.wav --vad silero|aic|aic_enhancer [--enhance aic]` пише часову шкалу VAD. Мовлення, знайдене в B (лише фон), — хибні спрацювання; пропущене в C проти A — втрачені репліки абонента.
- **Спільний автомат.** `VAD_BACKEND=aic` використовує скінченний автомат Silero з моделлю ai-coustics, тож різниця між `silero` і `aic` — лише в моделі.
- **Потрібно:** `AIC_LICENSE_KEY`; моделі з CDN ai-coustics (або `AIC_VAD_MODEL_PATH`); сесія ліцензії активується онлайн, якщо немає offline entitlement.
- **Перевірено:** реальний плагін із неправильним ключем пропускає аудіо без змін. Решта — з фейковим SDK. Реальні моделі не запускались.

## Що свідомо не зроблено

- **Живий shadow для сервера `/bargein`.** В adaptive-режимі LiveKit повністю довіряє відповіді сервера: відповідь «не перебивати» робить агента неперебивним, а «перебивати» обриває потік аудіо для цього перекриття. Нейтральної відповіді немає. Натомість сервер має `--decision-log` зі станом ASR (`pending` / `received` / `empty` / `error` / `timeout`), MaAI і порогами, а класифікатор оцінюється в shadow/replay на подіях STT.
- **Реальні прогони** `riva_server` і MaAI — див. TL;DR.

## Перевірка

| Що | Результат |
|---|---|
| `pytest` у `voice_agent/` | 104 passed |
| `./livekit_harness/run.sh` (клон livekit/agents@1.8.3) | 8 passed |
| ruff (E, F, W, B) | чисто |

Покрито тестами:
- `replay_stt` через справжній плагін `nvidia` і `MultiSpeakerAdapter` проти фейкового gRPC Riva: обидва рівні, відкинутий фінал фонового мовця, останній фінал після кінця WAV, meta;
- `replay_policy`: детермінізм, причинність, MaAI з вікном і без, прийом виходу `replay_stt`, відтворення живого журналу;
- `maai_scores` і обв'язка MaAI з фейковою моделлю;
- журнал рішень сервера `/bargein`.

## Відкриті питання

1. Прогнати `replay_stt` на реальному `riva_server` з вашим корпусом і перевірити, що схема подій відповідає прикладу. Особливо: чи дає NeMo-Speech.cpp слова в interim і як часто `word_speaker_tags` змішані всередині одного фіналу.
2. Налаштувати `FILTER_GRACE_S`, `INTERIM_MIN_WORDS`, `stop_history_eou_ms` і пороги primary-детектора за результатами A/B/C.
3. MaAI: перевірити ліцензію ваг, потім порівняти `--maai` і без нього на однакових подіях.
