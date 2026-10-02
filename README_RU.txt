Dorama Avatar LipSync v0.5 — диагностическая версия

Цель: отделить качество Wav2Lip/paste-back от ошибок Android H.264 encoder.

Что нового:
1) сохраняет первый input crop PNG;
2) сохраняет первый raw Wav2Lip face PNG;
3) сохраняет composite frame PNG ДО кодирования;
4) размер MP4 выравнивается до кратного 16 без растяжения — добавляется только чёрный padding справа/снизу при необходимости;
5) приложение определяет AVC encoder и выбирает реально заявленный YUV420 ByteBuffer format;
6) для SemiPlanar подаётся NV12, для Planar/Flexible — I420;
7) в финальном статусе показываются codec, color format и размер MP4.

Диагностические PNG: Pictures/DoramaAvatar
Видео: Movies/DoramaAvatar

Если V05_03_composite_before_encoder выглядит правильно, а MP4 повреждён — проблема точно в MediaCodec/YUV.
Если уже V05_02/V05_03 неправильные — исправляем Wav2Lip crop/paste-back, не трогая encoder.
