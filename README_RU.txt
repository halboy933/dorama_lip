Dorama Avatar LipSync V0.7

Цель V0.7: убрать неопределённость вокруг ONNX-модели.

Изменения:
1) вместо bluefoxcreation wav2lip.onnx загружается FaceFusion wav2lip_gan_96.onnx из официального facefusion-assets release;
2) файл модели имеет новое имя, поэтому старая модель V0.6 не переиспользуется;
3) crop приближен к оригинальному Wav2Lip: без бокового/верхнего расширения, только +10 px снизу;
4) выход ONNX автоматически распознаётся как NCHW или NHWC;
5) сохраняются V07_01 input crop, V07_02 raw model output, V07_03 composite;
6) MP4 остаётся H.264 + AAC до 5 секунд.

Wav2Lip weights используются только как технический некоммерческий тест.
