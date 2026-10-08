#!/usr/bin/env python3
# Dorama Avatar LipSync V1.3.2 — ORIGINAL FACE / LIPS ONLY
# Run from /workspaces/dorama_lip AFTER V1.3.1.
from pathlib import Path
import sys
root=Path.cwd()
if root.name!='dorama_lip':
    print(f'ОШИБКА: сейчас открыта папка {root}')
    print('Перейди в /workspaces/dorama_lip и запусти файл ещё раз.')
    sys.exit(2)
main_path=root/'app/src/main/java/com/dorama/avatar/MainActivity.kt'
gradle_path=root/'app/build.gradle.kts'
layout_path=root/'app/src/main/res/layout/activity_main.xml'
workflow_path=root/'.github/workflows/build-apk.yml'
readme_path=root/'README_RU.txt'
for p in (main_path,gradle_path,layout_path,workflow_path):
    if not p.exists(): print(f'ОШИБКА: не найден {p}'); sys.exit(3)
def rep(s,a,b,label):
    if a not in s: print(f'ОШИБКА PATCH: не найдено {label}'); sys.exit(4)
    return s.replace(a,b,1)
print('Dorama Avatar LipSync — V1.3.2 ORIGINAL FACE / LIPS ONLY')
g=gradle_path.read_text(encoding='utf-8')
g=rep(g,'versionCode = 14\n        versionName = "1.3.1"','versionCode = 15\n        versionName = "1.3.2"','version V1.3.1')
if 'signingConfigs.create("stable")' not in g: print('ОШИБКА: stable signing не найден'); sys.exit(5)
gradle_path.write_text(g,encoding='utf-8')
m=main_path.read_text(encoding='utf-8')
if 'edtalk_facefusion_256.onnx' not in m: print('ОШИБКА: EDTalk 256 не найден'); sys.exit(6)
# Tight lips-only ellipse: generated pixels are allowed only around lips and immediate lower-lip skin.
m=rep(m,
'''                // V1.3.1: narrow mouth-local mask. Preserve original face detail.\n                val dx = (fx - 0.50f) / 0.255f\n                val dy = (fy - 0.735f) / 0.125f''',
'''                // V1.3.2: lips-only mask. Everything outside this compact ellipse is original photo.\n                val dx = (fx - 0.50f) / 0.205f\n                val dy = (fy - 0.742f) / 0.090f''','V1.3.1 mouth mask')
m=rep(m,'smoothStep(0.36f, 1.00f, d2)','smoothStep(0.22f, 1.00f, d2)','V1.3.1 feather')
# Remove V1.3.1 sharpen/reblend. Keep EDTalk native result; original base is preserved by the mask.
old='''        val generated = if (generated96.width <= 96) {\n            val sharp = sharpenGenerated(generatedScaled)\n            generatedScaled.recycle()\n            sharp\n        } else {\n            // V1.3.1: EDTalk 256 gets only a light detail recovery.\n            // Do not sharpen the original face; this bitmap is used only under mouth mask.\n            val sharp = sharpenGenerated(generatedScaled)\n            val detail = Bitmap.createBitmap(generatedScaled.width, generatedScaled.height, Bitmap.Config.ARGB_8888)\n            val canvas = Canvas(detail)\n            val pBase = Paint(Paint.ANTI_ALIAS_FLAG).apply { alpha = 209 } // 82%\n            val pSharp = Paint(Paint.ANTI_ALIAS_FLAG).apply { alpha = 46 } // 18%\n            canvas.drawBitmap(generatedScaled, 0f, 0f, pBase)\n            canvas.drawBitmap(sharp, 0f, 0f, pSharp)\n            sharp.recycle()\n            generatedScaled.recycle()\n            detail\n        }'''
new='''        val generated = if (generated96.width <= 96) {\n            val sharp = sharpenGenerated(generatedScaled)\n            generatedScaled.recycle()\n            sharp\n        } else {\n            // V1.3.2: keep EDTalk 256 native. No full-face blur/sharpen/reblend pass.\n            // compositeMouth keeps the base photograph and admits these pixels only under lips mask.\n            generatedScaled\n        }'''
m=rep(m,old,new,'V1.3.1 EDTalk detail blend')
for a,b in [('V131_01_','V132_01_'),('V131_02_','V132_02_'),('V131_03_','V132_03_'),('✓ V1.3.1 ГОТОВА','✓ V1.3.2 ГОТОВА'),('V1.3.1: $engineLabel — MP4 готов','V1.3.2: $engineLabel — MP4 готов'),('Ошибка V1.3.1 ${activeModelLabel()}: ','Ошибка V1.3.2 ${activeModelLabel()}: '),('v131_${System.currentTimeMillis()}.mp4','v132_${System.currentTimeMillis()}.mp4'),('DoramaAvatar_V131_','DoramaAvatar_V132_')]: m=m.replace(a,b)
main_path.write_text(m,encoding='utf-8')
layout=layout_path.read_text(encoding='utf-8').replace('Dorama Avatar • V1.3.1 EDTalk 256','Dorama Avatar • V1.3.2 EDTalk 256').replace('V1.3.1: EDTalk 256 + LOCAL MOUTH BLEND. Исходная резкость лица сохраняется.','V1.3.2: ORIGINAL FACE + LIPS ONLY. EDTalk меняет только компактную зону губ.')
layout_path.write_text(layout,encoding='utf-8')
wf=workflow_path.read_text(encoding='utf-8'); wf=rep(wf,'DoramaAvatarLipSync-v1.3.1-stable','DoramaAvatarLipSync-v1.3.2-stable','workflow V1.3.1 artifact'); workflow_path.write_text(wf,encoding='utf-8')
readme_path.write_text('''Dorama Avatar LipSync V1.3.2 — ORIGINAL FACE / LIPS ONLY\n\nОснова: V1.3.1 + EDTalk 256x256.\n\nЦель V1.3.2: убрать дополнительное размытие лица.\n- исходная фотография остаётся базовым кадром;\n- EDTalk допускается только в компактной зоне губ;\n- глаза, нос, щёки, лоб и большая часть подбородка остаются исходными;\n- удалён 18% sharpen/reblend из V1.3.1;\n- EDTalk 256 используется в нативном виде внутри маски;\n- мягкий край маски сохранён;\n- X/Y/Angle/Scale сохранены;\n- Wav2Lip 96 остаётся fallback;\n- stable signing не меняется;\n- модель EDTalk повторно скачивать не нужно.\n\nТестировать на том же PNG/WAV и X=+15%, Y=-6%, Angle=+3°, Scale=89%.\n''',encoding='utf-8')
checks=[(gradle_path,'versionName = "1.3.2"'),(gradle_path,'versionCode = 15'),(main_path,'0.205f'),(main_path,'0.090f'),(main_path,'smoothStep(0.22f, 1.00f, d2)'),(main_path,'V1.3.2: keep EDTalk 256 native'),(workflow_path,'DoramaAvatarLipSync-v1.3.2-stable')]
failed=[f'{p.relative_to(root)} -> {x}' for p,x in checks if x not in p.read_text(encoding='utf-8')]
if failed:
    print('\nОШИБКА ПРОВЕРКИ V1.3.2:'); [print(' -',x) for x in failed]; sys.exit(20)
print('\n✓ V1.3.2 ORIGINAL FACE / LIPS ONLY применена')
print('✓ EDTalk 256 сохранён')
print('✓ генерация ограничена компактной зоной губ')
print('✓ 18% sharpen/reblend V1.3.1 удалён')
print('✓ остальное лицо остаётся исходной фотографией')
print('✓ stable signing НЕ менялся')
print('✓ модель повторно скачивать НЕ нужно')
print('\nСначала выполни только: git status')
