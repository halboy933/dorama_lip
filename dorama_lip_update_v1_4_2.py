#!/usr/bin/env python3
from pathlib import Path
import re
main=Path('app/src/main/java/com/dorama/avatar/MainActivity.kt')
gradle=Path('app/build.gradle.kts')
if not main.is_file() or not gradle.is_file(): raise SystemExit('Run from repository root')
s=main.read_text(encoding='utf-8'); g=gradle.read_text(encoding='utf-8')
if 'V142_EDTALK_VALIDATION' in s: raise SystemExit('Already installed')
if 'versionName = "1.4.1"' not in g: raise SystemExit('Expected version 1.4.1')
a='val targetInput = imageTensor256(aligned.bitmap)'
b='val sourceFrame = WavUtils.edtalkFrame(spec, f)'
c='val mappedFace = unalignEdtalkFace(face, aligned, crop)'
for n in [a,b,c]:
    if s.count(n)!=1: raise SystemExit('Missing or duplicate anchor: '+n)
s=s.replace(a,'''// V142_EDTALK_VALIDATION
                    val targetInput = imageTensor256(aligned.bitmap)
                    check(targetInput.size == 3 * 256 * 256 && targetInput.all { it.isFinite() && it >= 0f && it <= 1f }) {
                        "EDTalk: invalid RGB tensor"
                    }''',1)
s=s.replace(b,'''val sourceFrame = WavUtils.edtalkFrame(spec, f)
                        check(sourceFrame.size == 80 * 16 && sourceFrame.all { it.isFinite() && it >= -4f && it <= 4f }) {
                            "EDTalk: invalid mel tensor"
                        }
                        if (f == 0) android.util.Log.i(
                            "DoramaAvatar",
                            "V142 EDTalk mel min=${sourceFrame.minOrNull()} max=${sourceFrame.maxOrNull()} mean=${sourceFrame.average()}"
                        )''',1)
s=s.replace(c,'''if (f == 0) {
                            val inputPixels = IntArray(256 * 256)
                            val outputPixels = IntArray(256 * 256)
                            aligned.bitmap.getPixels(inputPixels, 0, 256, 0, 0, 256, 256)
                            face.getPixels(outputPixels, 0, 256, 0, 0, 256, 256)
                            var sum = 0.0
                            for (i in inputPixels.indices) {
                                val a = inputPixels[i]
                                val b = outputPixels[i]
                                sum += (kotlin.math.abs(Color.red(a) - Color.red(b)) +
                                    kotlin.math.abs(Color.green(a) - Color.green(b)) +
                                    kotlin.math.abs(Color.blue(a) - Color.blue(b))) / 3.0
                            }
                            android.util.Log.i("DoramaAvatar", "V142 EDTalk mean pixel difference=${sum / inputPixels.size}")
                        }
                        val mappedFace = unalignEdtalkFace(face, aligned, crop)''',1)
g=g.replace('versionName = "1.4.1"','versionName = "1.4.2"',1)
g=re.sub(r'versionCode\s*=\s*(\d+)',lambda m:'versionCode = '+str(max(26,int(m.group(1))+1)),g,count=1)
main.write_text(s,encoding='utf-8'); gradle.write_text(g,encoding='utf-8')
print('V1.4.2 installed; generation unchanged.')
