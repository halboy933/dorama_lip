Dorama Avatar LipSync V1.3 — EDTalk 256 QUALITY ENGINE

Главное:
- добавлен EDTalk 256×256 из FaceFusion assets;
- Wav2Lip GAN 96×96 оставлен как быстрый резерв;
- основной режим по умолчанию: EDTalk 256.

EDTalk 256:
- модель ~258 МБ;
- файл: edtalk_facefusion_256.onnx;
- скачивается один раз и хранится в filesDir;
- при обычных обновлениях приложения не удаляется;
- вход target: RGB CHW 256×256;
- source: 80×16 audio frame;
- weight: 0.5;
- output: RGB 256×256.

Audio path EDTalk повторяет FaceFusion:
- 16 kHz mono;
- peak normalize;
- pre-emphasis 0.97;
- STFT 800 / hop 200;
- HTK mel 80, 55..7600 Hz;
- log10 * 1.6 + 3.2, clip [-4, 4].

Сохранено:
- X / Y / Angle / Scale;
- SharedPreferences;
- moving mask;
- MP4 H.264 + AAC;
- stable signing key;
- обновление поверх V1.2;
- старая 96px модель остаётся на телефоне как fallback.

Стартовый ориентир текущего аватара:
X=+15%, Y=-6%, Angle=+3°, Scale=89%.

Диагностика:
- V13_01_input_crop
- V13_02_edtalk256_face (или wav2lip96_face)
- V13_03_composite_before_encoder
- DoramaAvatar_V13_*.mp4

EDTalk metadata in FaceFusion: vendor tanshuai0219, Apache-2.0.
Wav2Lip weights оставлены только как технический некоммерческий fallback.
