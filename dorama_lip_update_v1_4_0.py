#!/usr/bin/env python3
from pathlib import Path
import re
p=Path('app/src/main/java/com/dorama/avatar/MainActivity.kt')
g=Path('app/build.gradle.kts')
if not p.exists() or not g.exists(): raise SystemExit('Run from repository root')
s=p.read_text(encoding='utf-8'); b=g.read_text(encoding='utf-8')
if 'V140_01_aligned_input_256' in s: raise SystemExit('Already patched')
a='savePng(aligned.bitmap, "V139_01_aligned_input.png")'
assert s.count(a)==1, 'Expected V1.3.9 code missing'
s=s.replace(a,a+'\n                    savePng(aligned.bitmap, "V140_01_aligned_input_256.png")',1)
a='''                            savePng(face, "V132_02_edtalk256_face_${stamp}.png")
                            savePng(mappedFace, "V139_02_inverse_mapped_${stamp}.png")'''
assert s.count(a)==1, 'Expected EDTalk diagnostic block missing'
bb='''                            savePng(face, "V132_02_edtalk256_face_${stamp}.png")
                            if (savePng(face, "V140_02_raw_model_output_256_${stamp}.png") == null) {
                                android.util.Log.e("DoramaAvatar", "V140 raw PNG save failed")
                            }
                            savePng(mappedFace, "V139_02_inverse_mapped_${stamp}.png")
                            savePng(mappedFace, "V140_03_inverse_mapped_${stamp}.png")
                            savePng(composed, "V140_04_composite_before_encoder_${stamp}.png")'''
s=s.replace(a,bb,1)
assert re.search(r'versionName\s*=\s*"1\.3\.9"',b), 'Expected version 1.3.9'
b=re.sub(r'versionName\s*=\s*"1\.3\.9"','versionName = "1.4.0"',b,count=1)
m=re.search(r'versionCode\s*=\s*(\d+)',b); assert m
b=b[:m.start(1)]+str(max(24,int(m.group(1))+1))+b[m.end(1):]
p.write_text(s,encoding='utf-8');g.write_text(b,encoding='utf-8')
print('Patched EDTalk diagnostics and APK version 1.4.0. No inference changes.')
