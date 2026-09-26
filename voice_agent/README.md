# Local voice agent: NeMo-Speech.cpp + LiveKit Agents 1.8.3

Повністю локальний англомовний голосовий агент із відсіканням фонових мовців і
двома варіантами обробки backchannel («uh-huh», «yeah» не перебивають агента).

```
 мікрофон ─► LiveKit (room / console)
              │
              ├─► Silero VAD + TurnDetector v1-mini (локально)
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
| Логіка фільтра, словника, класифікатора, обгортки MaAI | 45 unit-тестів (`pytest`) |
| Опція 1 всередині справжнього `AgentSession` 1.8.3 | 5 сценаріїв у тест-харнесі livekit/agents (`livekit_harness/run.sh`): без фільтра «Mhm.» перебиває агента, з фільтром — ні; «Stop!» і повне речення перебивають; шум без слів — ні |
| Опція 2: справжній клієнт `AdaptiveInterruptionDetector` 1.8.3 ↔ наш сервер | unit-тести протоколу + 2 наскрізні сценарії в `AgentSession`: «mhm» не перебиває, «stop please» перебиває через ~0.35 с; сервер відповідає за < 1 мс |
| `riva_server` на Mac (Metal + gRPC), реальні Nemotron/Sortformer | **не перевірено** — у середовищі розробки не було Mac/GPU і доступу до HuggingFace |
| MaAI з реальною моделлю | **не перевірено** (ваги з HuggingFace); перевірено лише обв'язку з фейковою моделлю |
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

Поки агент говорить (і `FILTER_GRACE_S` після), транскрипт:
1. з самих backchannel-слів чи фраз («mhm», «yeah», «I see») — **відкидається**;
2. зі словом-перебиванням («stop», «wait», «no», «sorry», «actually»…) — **проходить одразу**;
3. проміжний (interim), коротший за `INTERIM_MIN_WORDS` значущих слів, — **чекає фіналу**.
   Мітки Sortformer бувають лише у фіналах, тому короткий interim ще не можна
   приписати основному мовцю;
4. з MaAI (`MAAI_ENABLED=1`): коротке (≤ 2 слів) незнайоме слово або помилка розпізнавання
   («but high» замість «uh-huh») відкидається, якщо MaAI `bc_det` бачить backchannel.
   MaAI отримує обидва канали: користувача (з `stt_node`) і агента (з `tts_node`).

`interruption.min_words = 1` забороняє VAD перебивати агента без жодного слова,
тож кашель, сміх і шум не перебивають. Фонові мовці відсікаються раніше, у `MultiSpeakerAdapter`.

Словник і налаштування — у `backchannel/lexicon.py`. «yes» навмисно не вважається
backchannel: «так» часто є відповіддю.

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

**Ризик:** протокол недокументований. Моделі повідомлень імпортуються з самого
livekit-agents, тож зміна протоколу проявиться помилкою, а не тихим збоєм.
Тримайте `livekit-agents==1.8.3` і проганяйте `livekit_harness/run.sh` після кожного оновлення.

## Тести

```bash
pytest                            # 45 unit-тестів, секунди
./livekit_harness/run.sh          # клонує livekit/agents@1.8.3 і проганяє 7 сценаріїв у AgentSession
```

## Налаштування

| Змінна | За замовчуванням | Що робить |
|---|---|---|
| `INTERRUPTION_MODE` | `filters` | `filters` / `adaptive_local` / `vad` (для A/B) |
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
