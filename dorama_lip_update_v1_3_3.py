#!/usr/bin/env python3
"""V1.3.3: separate fixed mouth mask from adjustable generated-image transform."""
from pathlib import Path
import sys
root=Path.cwd()
p=root/'app/src/main/java/com/dorama/avatar/MainActivity.kt'
g=root/'app/build.gradle.kts'
w=root/'.github/workflows/build-apk.yml'
layout=root/'app/src/main/res/layout/activity_main.xml'
readme=root/'README_RU.txt'
for f in [p,g,w,layout]:
    if not f.is_file(): sys.exit(f'Не найден {f}')
s=p.read_text()
if 'V1.3.3 fixed-mouth mask' in s: sys.exit('V1.3.3 уже применён')
old='''        // Та же Matrix двигает сам "кружок".
        val transformedMask = Bitmap.createBitmap(
            c.width, c.height, Bitmap.Config.ARGB_8888
        )
        Canvas(transformedMask).drawBitmap(
            baseMask,
            transform,
            Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
        )'''
new='''        // V1.3.3 fixed-mouth mask: X/Y/Angle/Scale move ONLY generated pixels.
        // The destination lips region stays fixed on the original photograph.
        val transformedMask = baseMask.copy(Bitmap.Config.ARGB_8888, false)'''
if s.count(old)!=1: sys.exit('ОШИБКА: не найден ожидаемый блок маски V1.3.2; ничего не изменено')
s=s.replace(old,new)
# Set offsets to zero on first launch of this version, because prior calibration referred to moving the mask too.
anchor='''        mouthScalePercent = prefs.getInt("mouth_scale", 89)'''
replace=anchor+'''
        // V1.3.3: old X/Y values had different meaning (they moved the mask).
        if (!prefs.getBoolean("v133_calibration_reset", false)) {
            mouthOffsetXPercent = 0
            mouthOffsetYPercent = 0
            mouthAngleDeg = 0
            mouthScalePercent = 100
            prefs.edit().putInt("mouth_x", 0).putInt("mouth_y", 0)
                .putInt("mouth_angle", 0).putInt("mouth_scale", 100)
                .putBoolean("v133_calibration_reset", true).apply()
        }'''
if s.count(anchor)!=1: sys.exit('ОШИБКА: не найден блок настроек; ничего не изменено')
s=s.replace(anchor,replace)
s=s.replace('V1.3.2 ГОТОВА','V1.3.3 ГОТОВА').replace('Ошибка V1.3.2','Ошибка V1.3.3').replace('"V1.3.2:','"V1.3.3:').replace('DoramaAvatar_V132_','DoramaAvatar_V133_').replace('"v132_','"v133_')
gs=g.read_text(); ls=layout.read_text(); ws=w.read_text()
if 'versionName = "1.3.2"' not in gs: sys.exit('ОШИБКА: требуется V1.3.2 в Gradle')
if 'versionCode = 15' not in gs: sys.exit('ОШИБКА: неожиданный versionCode; ничего не изменено')
gs=gs.replace('versionName = "1.3.2"','versionName = "1.3.3"').replace('versionCode = 15','versionCode = 16')
ls=ls.replace('V1.3.2','V1.3.3')
ws=ws.replace('v1.3.2','v1.3.3').replace('V1.3.2','V1.3.3')
p.write_text(s);g.write_text(gs);layout.write_text(ls);w.write_text(ws)
readme.write_text(readme.read_text()+'''\nV1.3.3 FIXED MOUTH MASK\n- Маска губ остаётся неподвижной; X/Y/Angle/Scale трансформируют только генерацию.\n- Калибровка сбрасывается ОДИН РАЗ к X=0,Y=0,Angle=0,Scale=100.\n- EDTalk 256 и stable signing не изменены.\n- Это промежуточная геометрическая коррекция, НЕ детектор точек губ.\n''')
print('✓ V1.3.3 fixed-mouth mask применена')
print('✓ При первом запуске калибровка сбросится к 0/0/0/100')
print('✓ Модель и подпись не затронуты')
print('Теперь: git status; НЕ делайте commit до проверки.')
