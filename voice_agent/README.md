# Local voice agent: NeMo-Speech.cpp + LiveKit Agents 1.8.3

Повністю локальний англомовний голосовий агент із відсіканням фонових мовців і
двома варіантами обробки backchannel («uh-huh», «yeah» не перебивають агента).

```
 мікрофон ─► LiveKit (room / console)
              │
              ├─► [ai-coustics покращення] ─► VAD (Silero або ai-coustics) + TurnDetector v1-mini
              │
              └─► stt_node ──► nvidia.STT ──gRPC──► riva_server (NeMo-Speech.cpp, Metal/CUDA)
                     │            │                   ├─ Nemotron-Speech EN 0.6B (streaming RNNT)
                     │            │                   ├─ Streaming Sortformer (мітки мовців)
                     │            │                   └─ endpointing (+ опційно Silero VAD masking)
                     │            └─► MultiSpeakerAdapter: відкидає фінали фонових мовців
                     │
                     ├─ опція 1 (filters): словник backchannel + утримання коротких interim + MaAI
                     └─ опція 2 (adaptive_local): AdaptiveInterruptionDetector ─WS─► bargein server
                                                                                  (цей каталог)
 LLM: будь-який OpenAI-сумісний (Ollama за замовчуванням)
 TTS: будь-який OpenAI-сумісний (VibeVoice API з цього репо за замовчуванням)
```

## Що перевірено, а що ні

| Частина | Статус |
|---|---|
| Логіка фільтра, словника, класифікатора, обгортки MaAI, інструменти оцінки | 104 unit-тести (`pytest`) |
| `replay_stt` через справжній плагін `nvidia` і `MultiSpeakerAdapter` | проти скриптованого gRPC-сервера Riva (`tests/fake_riva.py`) |
| Опція 1 всередині справжнього `AgentSession` 1.8.3 | 5 сценаріїв у тест-харнесі livekit/agents (`livekit_harness/run.sh`): без фільтра «Mhm.» перебиває агента, з фільтром — ні; «Stop!» і повне речення перебивають; шум без слів — ні |
| Shadow у справжньому `AgentSession` | поведінка і таймінг станів ідентичні контрольному прогону без фільтра; журнал відтворюється в ті самі рішення |
| Опція 2: справжній клієнт `AdaptiveInterruptionDetector` 1.8.3 ↔ наш сервер | unit-тести протоколу + 2 наскрізні сценарії в `AgentSession`: «mhm» не перебиває, «stop please» перебиває через ~0.35 с; сервер відповідає за < 1 мс |
| `riva_server` на Mac (Metal + gRPC), реальні Nemotron/Sortformer | **не перевірено** — у середовищі розробки не було Mac/GPU і доступу до HuggingFace |
| MaAI з реальною моделлю | **не перевірено** (ваги з HuggingFace); перевірено лише обв'язку з фейковою моделлю |
| ai-coustics: реальний плагін з неправильним ключем | перевірено: пропускає аудіо без змін і логує причину |
| ai-coustics: `AicVAD`, VAD улучшувача, `vad_scores`, `replay_stt --enhance` | перевірено з фейковим `aic_sdk` і фейковим улучшувачем |
| ai-coustics з вашим ключем і реальними моделями | **не перевірено**: немає ключа, CDN моделей недоступний із середовища розробки |
| VibeVoice TTS через `openai.TTS` | **не перевірено**; див. «Обмеження» |

## Встановлення на Mac (Apple Silicon)

### 1. Інструменти

```bash
xcode-select --install   # якщо ще немає
brew install cmake ninja sentencepiece abseil grpc protobuf
brew install portaudio   # лише для MaAI (pyaudio)
brew install livekit     # лише для режиму dev (локальний LiveKit server)
```

### 2. NeMo-Speech.cpp: готовий CLI і моделі

Готова збірка (`macos-aarch64-metal`) дає CLI і HTTP-сервер, але **не** `riva_server`:

```bash
curl -fsSL https://github.com/NVIDIA/NeMo-Speech.cpp/raw/main/scripts/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

nemo-speech pull nemotron-en     # nvidia/nemotron-speech-streaming-en-0.6b
nemo-speech pull sortformer      # diar_streaming_sortformer_4spk-v2
# альтернатива: nemo-speech pull nemotron-3-diarization  (V3, до 8 мовців)

# швидка перевірка з мікрофона, з мітками мовців:
nemo-speech transcribe --live --model nemotron-en --diarize --diar-model sortformer
```

Моделі лягають у `~/Library/Caches/NeMoSpeech/models`.

### 3. Збірка `riva_server` (Metal + gRPC)

```bash
git clone https://github.com/NVIDIA/NeMo-Speech.cpp && cd NeMo-Speech.cpp
git submodule update --init ggml third_party/cpp-httplib llama.cpp proto/riva-common
scripts/configure.sh metal-server -DNEMO_SPEECH_BUILD_GRPC=ON
cmake --build --preset metal-server
find build/metal-server -name riva_server -type f
```

`configure.sh` перевіряє сабмодулі і скаже, якого бракує. gRPC береться з Homebrew
(`find_package(gRPC CONFIG)` + ціль `gRPC::grpc++_unsecure`). Якщо збірка gRPC на
Mac не вдасться, розпізнавання можна тримати на Linux-сервері з CUDA (пресет
`cuda-full` вже містить gRPC), а агента запускати на Mac: змінюється лише `RIVA_SERVER`.

### 4. (Опційно) Silero VAD для NeMo-Speech.cpp

Маскує не-мову до енкодера: менше «слів» із шуму і точніший endpointing.

```bash
cd NeMo-Speech.cpp   # у venv за docs/model-conversion.md
pip install "silero-vad==6.2.0"
python3 convert_model.py silero --outfile models/silero-v6.2.0.gguf
```

Потім у `config/asr.mac.yaml`: `vad.model_path: <абсолютний шлях>`,
`vad.masker.mask_enable: true`, `endpointing.vad_based: true`.

### 5. Запуск `riva_server`

```bash
/path/to/riva_server --config config/asr.mac.yaml --bind 127.0.0.1:50051
```

gRPC тут без TLS: слухайте тільки `127.0.0.1` або ставте TLS-проксі.

### 6. LLM і TTS

- **LLM:** наприклад `brew install ollama && ollama pull qwen3:8b`. Підходить будь-який
  OpenAI-сумісний сервер (`LLM_BASE_URL`, `LLM_MODEL`).
- **TTS:** VibeVoice API з кореня цього репо
  (`python -m vibevoice_api.server --model_path vibevoice/VibeVoice-1.5B --port 8000`)
  або будь-який інший OpenAI-сумісний TTS (`TTS_BASE_URL`, `TTS_MODEL`, `TTS_VOICE`).

### 7. Python-оточення агента

```bash
cd voice_agent
uv venv && source .venv/bin/activate
uv pip install -e ".[test]"
uv pip install -e ".[maai]"      # опційно, важке: torch + transformers + onnxruntime
cp .env.example .env              # і відредагуйте
python -m livekit.agents download-files            # файли встановлених плагінів LiveKit
```

Для офлайн-роботи запустіть агента один раз з інтернетом: частина ваг (зокрема
локального TurnDetector v1-mini, ~108 MB) може підтягуватися при першому використанні.

### 8. Запуск

**Найпростіше: console.** Мікрофон і динаміки Mac, LiveKit server не потрібен.
Беріть **навушники**, інакше агент чутиме сам себе.

```bash
python -m local_voice_agent.agent console
```

**Через кімнату LiveKit:**

```bash
livekit-server --dev                        # ws://127.0.0.1:7880, devkey / secret
python -m local_voice_agent.agent dev
```

Під'єднатися можна будь-яким клієнтом LiveKit, наприклад self-hosted
[agents-playground](https://github.com/livekit/agents-playground) з токеном від `lk token create`.

## Опція 1: `INTERRUPTION_MODE=filters`

`local_voice_agent/backchannel/filter.py` — порт `BackchannelSTTFilterMixin` з
[AssemblyAI livekit-interruption-filters](https://github.com/AssemblyAI-Solutions/livekit-interruption-filters)
(MIT), адаптований під NeMo-Speech.cpp. Він обгортає публічний `Agent.stt_node`,
приватних атрибутів LiveKit не чіпає.

Правила діють, поки агент говорить, і ще `FILTER_GRACE_S` після того, як замовк.
**Виняток:** якщо остання репліка агента закінчилась «?», відповідь («Yes») не фільтрується.
Транскрипт:
1. з самих backchannel-слів, фраз («mhm», «yeah», «yes», «I see») або continuers
   («I am with you», «please proceed», «do not stop») — **відкидається**;
2. зі словом-перебиванням («stop», «wait», «no», «sorry», «actually»…) — **проходить одразу**.
   Continuer-фрази зіставляються раніше, тому «do not stop» не перебиває;
3. проміжний (interim), коротший за `INTERIM_MIN_WORDS` значущих слів або ще не дописаний
   початок фрази («do not», «I am»), — **чекає фіналу**. Мітки Sortformer бувають лише у
   фіналах, тому короткий interim ще не можна приписати основному мовцю;
4. з MaAI (`MAAI_ENABLED=1`): коротке (≤ 2 слів) незнайоме слово або помилка розпізнавання
   («but high» замість «uh-huh») відкидається, якщо MaAI `bc_det` бачить backchannel.
   MaAI отримує обидва канали: користувача (з `stt_node`) і агента (з `tts_node`).

`interruption.min_words = 1` забороняє VAD перебивати агента без жодного слова,
тож кашель, сміх і шум не перебивають. Фонові мовці відсікаються раніше, у `MultiSpeakerAdapter`.

Правила — чиста функція `backchannel/policy.py::decide_text`, словник — `backchannel/lexicon.py`.

## Опція 2: `INTERRUPTION_MODE=adaptive_local`

Вбудована adaptive-обробка перебивань у LiveKit (`AdaptiveInterruptionDetector`)
ходить у LiveKit Cloud за адресою `{LIVEKIT_INFERENCE_URL}/bargein`.
`local_voice_agent/bargein_server` реалізує цей **приватний** протокол локально,
тож LiveKit сам тримає перебивання, `backchannel_boundary` і відновлення мовлення,
а рішення «перебивання чи backchannel» ухвалює наш сервер.

```bash
python -m local_voice_agent.bargein_server        # 127.0.0.1:8765, --maai, -v
INTERRUPTION_MODE=adaptive_local python -m local_voice_agent.agent console
```

Сервер отримує кожні ~100 мс вікно до 3 с аудіо користувача і повинен відповісти
швидше за 0.7 с. Інакше LiveKit вимикає детектор до кінця сесії й повертається до VAD.
Тому рішення ніколи не чекає ASR чи MaAI:

- **Транскрипт перекриття.** NeMo-Speech.cpp `Recognize` через той самий `riva_server`
  перезапускається фоном при прирості перекриття на 0.2 с і класифікується тим самим словником.
- **MaAI `bc_det_mono`** (`--maai`). LiveKit надсилає лише аудіо користувача, тому тут
  працює одноканальна модель, вона менш точна.
- Правила — у `bargein_server/classifier.py`. Без слів (шум, кашель) перебивання немає.
  `BARGEIN_THRESHOLD` (або `threshold` від клієнта) відсікає менш упевнені рішення.

`--decision-log path.jsonl` (або `BARGEIN_DECISION_LOG`) записує кожне рішення з причиною,
станом ASR (`pending` / `received` / `empty` / `error` / `timeout`), оцінкою MaAI і порогами.

**Ризик:** протокол недокументований. Моделі повідомлень імпортуються з самого
livekit-agents, тож зміна протоколу проявиться помилкою, а не тихим збоєм.
Тримайте `livekit-agents==1.8.3` і проганяйте `livekit_harness/run.sh` після кожного оновлення.

## Опція 3: ai-coustics — VAD і очищення звуку

Незалежна від `INTERRUPTION_MODE`: поєднується з будь-якою з опцій вище. Два перемикачі:

| Змінна | Значення | Що робить |
|---|---|---|
| `AUDIO_ENHANCEMENT` | `none` / `aic` | покращення звуку ai-coustics на вході кімнати, до STT, VAD і TurnDetector. `quail_vf_l` / `quail_vf_s` (Voice Focus) прибирає і шум, і **фонові голоси**; `quail_l` / `rook_s` — лише шум |
| `VAD_BACKEND` | `silero` | Silero, як було |
| | `aic` | окрема VAD-модель ai-coustics (`vad-2.1-xxs-16khz`, `aic_sdk.Vad`) у скінченному автоматі Silero: пороги, мінімальна тиша й префікс такі самі, змінюється лише ймовірність мовлення. Працює і в `console` |
| | `aic_enhancer` | прапорець мовлення, який улучшувач рахує на **вихідному** сигналі (`ai_coustics.VAD()`). Потрібен `AUDIO_ENHANCEMENT=aic` |

**Рекомендована зв'язка** (режим кімнати: `dev` / `start`):

```bash
uv pip install -e ".[aic]"
# .env: AIC_LICENSE_KEY=...   (ключ з developers.ai-coustics.com; не комітьте)
AUDIO_ENHANCEMENT=aic AIC_ENHANCER_MODEL=quail_vf_l VAD_BACKEND=aic_enhancer \
  python -m local_voice_agent.agent dev
```

**У `console`** LiveKit не застосовує `noise_cancellation`, тож працює лише `VAD_BACKEND=aic`.

**Як влаштовано:**
- Покращення — офіційний `livekit-plugins-ai-coustics` 0.3.2 з `Auth.ai_coustics_api(license_key)`, тобто без LiveKit Cloud.
- `AicVAD` — ~40 рядків (`local_voice_agent/aic.py`): адаптер `aic_sdk.Vad` під інтерфейс моделі Silero.
- **З неправильним ключем** плагін пише `License key format is invalid…`, вимикає покращення і далі пропускає аудіо без змін; агент не падає (перевірено на реальному бінарнику).

**Мережа і ліцензія:**
- Аудіо з машини не виходить.
- SDK активує сесію і звітує про використання на сервери ai-coustics, якщо у ліцензії немає offline entitlement.
- Моделі при першому запуску тягнуться з `artifacts.ai-coustics.io`. Для офлайну вкажіть `AIC_VAD_MODEL_PATH`. Як моделі отримує плагін, закрито в його бінарнику; я не перевіряв.
- `AIC_TELEMETRY=0` (за замовчуванням) вимикає OpenTelemetry-експорт і ставить `DO_NOT_TRACK=1` для звітів про помилки SDK.

**Нюанси:**
- **Сумісність із TurnDetector.** Потоковий `TurnDetector` вимагає від VAD `min_silence_duration` ≥ 0.25 с. `AicVAD` бере 0.55 с, як Silero. Для VAD улучшувача утримання тиші задається `AIC_ENHANCER_VAD_HOLD_S` (0.55 за замовчуванням). Це моє припущення, його варто підлаштувати на корпусі.
- **STT отримує вже покращений звук.** Voice Focus може прибрати фоновий голос до того, як його побачить Sortformer, тож фінали фонових мовців можуть просто зникнути. Це варто перевірити на A/B/C:
  ```bash
  python -m local_voice_agent.tools.replay_stt C_mix.wav --enhance aic --out runs/C.aic.stt.jsonl
  python -m local_voice_agent.tools.vad_scores B_background.wav --vad aic --out runs/B.vad.aic.jsonl
  python -m local_voice_agent.tools.vad_scores B_background.wav --vad silero --out runs/B.vad.silero.jsonl
  python -m local_voice_agent.tools.vad_scores C_mix.wav --enhance aic --vad aic_enhancer --out runs/C.vad.enh.jsonl
  ```
  `vad_scores` пише ймовірність мовлення на кожен крок і події початку/кінця мовлення. Мовлення, яке VAD знаходить у B (лише фон), — хибне спрацювання.

## Оцінка на власному корпусі (без повного агента)

Три CLI, яким не потрібні LiveKit room, LLM чи TTS (ні Ollama, ні VibeVoice):

| Інструмент | Що робить |
|---|---|
| `tools.replay_stt` | WAV → той самий STT, що в агента (riva_server + `MultiSpeakerAdapter`) у реальному темпі → JSONL подій **до і після** speaker suppression з одного прогону |
| `tools.replay_policy` | JSONL подій (+ часова шкала агента, + опційно MaAI) → рішення обох політик із поясненнями; без ASR |
| `tools.maai_scores` | WAV абонента (+ опційно WAV агента) → оцінки MaAI `bc_det` на кожні 80 мс |
| `tools.vad_scores` | WAV → часова шкала VAD (Silero / ai-coustics / VAD улучшувача, опційно після покращення) |

### 1. `replay_stt`: чи втрачає слова ASR, чи їх прибирає suppression

```bash
python -m local_voice_agent.tools.replay_stt A_caller.wav --out runs/A.stt.jsonl
python -m local_voice_agent.tools.replay_stt B_background.wav --out runs/B.stt.jsonl
python -m local_voice_agent.tools.replay_stt C_mix.wav --out runs/C.stt.jsonl
#   --riva host:port  --speed 1.0  --tail-silence 1.0  --no-suppress  --max-speakers 4
```

Кожна подія STT записується двічі:
- `layer: "raw"` — як вона дійшла до `MultiSpeakerAdapter`, плюс `adapter_action` (`passed` / `modified` / `dropped`) і `primary_speaker` після неї (`primary_speaker_before`, якщо він щойно змінився);
- `layer: "adapter"` — що отримав би агент, з посиланням `source_seq` на raw-подію.

Спільні поля:
- `t` — монотонний час отримання від старту;
- `audio_pos_samples` / `audio_pos_s` — скільки аудіо вже подано;
- `type` (`interim` / `final` / `start_of_speech` / `end_of_speech`);
- `text`, `speaker_id`, `start_time_s` / `end_time_s`, `words` (`start_ms` / `end_ms`) і `word_speaker_tags` (мітки Sortformer по словах, до мажоритарного голосування плагіна) — **лише коли STT їх віддає**. В interim їх немає, і ключі тоді просто відсутні.

Кінець WAV (і `--tail-silence`) закриває потік, і `riva_server` віддає останні фінали. Поруч пишеться
`*.meta.json` з версіями SDK, параметрами STT і адаптера, конфігом моделі від сервера
(`GetRivaSpeechRecognitionConfig`), знімком `config/asr.mac.yaml`, sha256 WAV і підсумком:
кількість подій за рівнями й діями, перемикання primary speaker, чи потік догнано до кінця.

Приклад: [`examples/replay_stt.sample.jsonl`](examples/replay_stt.sample.jsonl) +
[`.meta.json`](examples/replay_stt.sample.meta.json). Його отримано на скриптованому фейковому
сервері з `tests/fake_riva.py`, не на реальній моделі; схема та сама. У ньому фінал фонового
мовця `S2` має `adapter_action: "dropped"`, а агент замість нього отримує порожній фінал
(`cleared_suppressed_final`).

Для спостереження скрипт підключається до двох приватних місць livekit-agents 1.8.3:
`MultiSpeakerAdapterWrapper._detector` і `_convert_to_speech_data` у стрімі NVIDIA. Дані він не змінює.

### 2. Shadow-режим і відтворення рішень

**Наживо:** `INTERRUPTION_MODE=shadow DECISION_LOG=logs/{room}-{ts}.jsonl`. Агент поводиться
рівно як `vad`, тобто як LiveKit без фільтрів: події STT не видаляються, не затримуються і
аудіо не перериваються. У журнал пишуться стани агента, всі події STT, оцінки MaAI і рішення
обох політик. `DECISION_LOG` працює і в режимі `filters`.

**Офлайн:**

```bash
python -m local_voice_agent.tools.replay_policy runs/C.stt.jsonl \
    --agent runs/C.agent.jsonl [--maai runs/C.maai.jsonl] --out runs/C.decisions.jsonl
python -m local_voice_agent.tools.replay_policy logs/room-….jsonl --layer all --out …   # живий журнал
```

- **Часова шкала агента** — рядки `{"kind": "agent", "audio_pos_s": 3.2, "state": "speaking", "text": "…?"}`.
  `?` у кінці тексту означає «агент чекає відповіді».
- **Час.** Береться `audio_pos_s`, якщо поле є, інакше `t`. Усі файли мають бути на одній шкалі.
- **Детермінізм і причинність.** Той самий журнал дає ті самі рішення. Рішення використовує
  лише входи до свого часу, тож обрізання журналу не змінює попередніх рішень (є тести на обидва).
- **Живий журнал** відтворюється в точно ті рішення, що були записані наживо (перевірено в `AgentSession`).

Кожне рішення — два записи на подію:

| Поле | `policy: "text_filter"` (опція 1) | `policy: "interruption_classifier"` (опція 2) |
|---|---|---|
| вердикт | `action`: `pass` / `hold` / `drop` + окремо `interruption`: `interrupt` / `no_interrupt` / `not_applicable` | `decision`: `interrupt` / `wait` / `no_interrupt` / `not_applicable` |
| причина | `reason`: `interrupt_token`, `backchannel_tokens`, `backchannel_phrase`, `continuer_phrase`, `maai_backchannel`, `short_interim_awaits_final`, `phrase_prefix_awaits_final`, `awaiting_answer`, `agent_not_speaking`, `content_words`, `empty_transcript`, `non_transcript` | `reason`: `overlap_too_short`, `interrupt_token`, `continuer_phrase`, `content_words`, `maai_backchannel`, `single_word_held` / `_waiting`, `phrase_prefix_waiting`, `asr_pending` / `_empty` / `_error` / `_timeout`, `agent_not_speaking`, `no_user_utterance` |
| контекст | `t`, `type`, `text`, `agent` (`state`, `since_speaking_s`, `awaiting_answer`) | те саме + `signals.elapsed_overlap_s` |
| сигнали | `signals`: токени, фрази, кількість значущих слів, `maai` | `signals`: `asr` (`status`, `text`), `maai`, кількість слів, токени |
| пороги | `thresholds` | `thresholds` |

- **`maai`** — або `{"status": "unavailable"}`, або `{"status": "available", "p_bc", "evaluated_at", "window_s", "clock"}`.
  Без MaAI текстові правила працюють як є, тож внесок MaAI видно, якщо прогнати з `--maai` і без.
- **Класифікатор опції 2 у replay** застосовується до транскриптів STT, а не до аудіо.
  Перекриття тут починається з першого транскрипту, тобто на латентність ASR пізніше, ніж у сервера.
  Тому `elapsed_overlap_s` занижений. Якщо репліка приходить одним фіналом із часом слів, початок
  зсувається назад на тривалість мовлення. Живий shadow для самого сервера `/bargein` не робив:
  в adaptive-режимі LiveKit повністю довіряє відповіді сервера, тож «нейтральної» відповіді не
  існує. Для сервера є `--decision-log` у звичайному режимі.

**Набір перевірок** — [`examples/policy_cases.events.jsonl`](examples/policy_cases.events.jsonl) →
[`examples/policy_cases.decisions.jsonl`](examples/policy_cases.decisions.jsonl),
тести в `tests/test_policy_cases.py`. Значення нижче — рішення на фінальному транскрипті:

| Фраза | Агент говорить: фільтр | Агент говорить: класифікатор | Агент спитав і чекає: обидва |
|---|---|---|---|
| I am with you | drop · continuer_phrase | no_interrupt | pass · awaiting_answer / not_applicable |
| Please proceed | drop · continuer_phrase | no_interrupt | pass · awaiting_answer / not_applicable |
| Yes | drop · backchannel_tokens | no_interrupt | pass · awaiting_answer / not_applicable |
| Okay | drop · backchannel_tokens | no_interrupt | pass · awaiting_answer / not_applicable |
| Stop | pass · interrupt_token → interrupt | interrupt | pass · awaiting_answer / not_applicable |
| Do not stop | drop · continuer_phrase | no_interrupt | pass · awaiting_answer / not_applicable |

### 3. `maai_scores`: окремий внесок MaAI

```bash
python -m local_voice_agent.tools.maai_scores C_mix.wav --agent-wav C_agent.wav --out runs/C.maai.jsonl
```

- З `--agent-wav` працює двоканальна модель, як в опції 1; без нього — моно, як у сервері `/bargein`.
- Кадр на момент `t` використовує лише аудіо до `t`.
- Потрібен extra `[maai]`, WAV 16 кГц.

## Тести

```bash
pytest                            # 104 unit-тести, ~10 с
./livekit_harness/run.sh          # клонує livekit/agents@1.8.3 і проганяє 8 сценаріїв у AgentSession
```

## Налаштування

| Змінна | За замовчуванням | Що робить |
|---|---|---|
| `INTERRUPTION_MODE` | `filters` | `filters` / `shadow` / `adaptive_local` / `vad` (для A/B) |
| `VAD_BACKEND` / `AUDIO_ENHANCEMENT` | `silero` / `none` | ai-coustics, див. «Опція 3» |
| `DECISION_LOG` | — | журнал для `replay_policy` (`{room}`, `{ts}` підставляються) |
| `SUPPRESS_BACKGROUND_SPEAKER` | `1` | відкидати фінали не-основних мовців |
| `ASR_MAX_SPEAKERS` | `4` | для Sortformer v2 максимум 4 |
| `FILTER_GRACE_S` | `1.0` | скільки фільтрувати після того, як агент замовк |
| `INTERIM_MIN_WORDS` | `3` | з якого розміру interim перебиває одразу |
| `MAAI_ENABLED` / `MAAI_THRESHOLD` | `0` / `0.45` | MaAI у опції 1 (0.45 — робоча точка авторів) |
| `stop_history_eou_ms` в `asr.mac.yaml` | `700` | тиша, після якої NeMo віддає фінал |

## Обмеження

- `MultiSpeakerAdapter` обирає основного мовця за гучністю, і першим основним стає той,
  хто першим отримав фінал. На гучному зв'язку в шумній кімнаті він може помилитися.
- Проміжні результати не мають міток мовця. Довгий фоновий interim (≥ `INTERIM_MIN_WORDS`)
  може перебити агента до того, як фінал відкинуть; тоді агент продовжить через
  `resume_false_interruption`. В опції 2 транскрипт перекриття теж не знає мовця.
- VibeVoice API цього репо віддає `pcm` цілим файлом, а потоково — лише mp3/opus/aac
  через `stream_format`, якого `openai.TTS` у LiveKit не передає. Отже затримка TTS
  дорівнює часу синтезу речення. Для низької затримки беріть потоковий OpenAI-сумісний TTS.
- MaAI: перевірте ліцензію ваг на картці моделі. `transformers==5.5.3` у його залежностях
  може конфліктувати з іншими пакетами, тоді ставте його в окреме оточення разом із bargein-сервером.
- Ліцензії моделей: Nemotron-Speech EN — NVIDIA Open Model License,
  Sortformer v2 — CC-BY-4.0, Nemotron-3-Diarization — OpenMDW-1.1.
