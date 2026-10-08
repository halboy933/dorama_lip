from pathlib import Path
import re
p=Path('app/src/main/java/com/dorama/avatar/MainActivity.kt')
if not p.exists(): raise SystemExit('Запускайте из корня репозитория')
s=p.read_text(encoding='utf-8')
if 'V1.3.7: localized detail enhancement' in s: raise SystemExit('V1.3.7 уже установлена')
if 'V1.3.6: alignment preview' not in s: raise SystemExit('Сначала установите V1.3.6')
old='''            // V1.3.2: keep EDTalk 256 native. No full-face blur/sharpen/reblend pass.
            // compositeMouth keeps the base photograph and admits these pixels only under lips mask.
            generatedScaled'''
new='''            // V1.3.7: localized detail enhancement. The generated face is only
            // inserted through the lip mask, so original skin stays untouched.
            // Keep sharpening mild: EDTalk cannot reconstruct missing detail.
            val enhanced = sharpenGenerated(generatedScaled, 0.24f)
            generatedScaled.recycle()
            enhanced'''
if old not in s: raise SystemExit('Не найдена ветка EDTalk — исходник отличается')
s=s.replace(old,new,1)
old='''(1f - smoothStep(0.22f, 1.00f, d2)) * 255f'''
new='''(1f - smoothStep(0.62f, 1.00f, d2)) * 255f'''
if old not in s: raise SystemExit('Не найдена формула мягкой маски')
s=s.replace(old,new,1)
needle='''        val maskRadians = Math.toRadians(lipRotation.toDouble())'''
if needle not in s: raise SystemExit('Не найдена маска губ')
s=s.replace(needle,'''        // V1.3.7: localized detail enhancement and a narrower feather band.
        // No movement of the selected ellipse or alignment settings.
'''+needle,1)
s=s.replace('V1.3.6 ГОТОВА','V1.3.7 ГОТОВА').replace('V1.3.6: $engineLabel','V1.3.7: $engineLabel')
g=Path('app/build.gradle.kts'); w=Path('.github/workflows/build-apk.yml')
if g.exists():
 t=g.read_text(encoding='utf-8'); t,n=re.subn(r'versionName\s*=\s*"1\.3\.6"','versionName = "1.3.7"',t,count=1)
 if n: t=re.sub(r'(versionCode\s*=\s*)(\d+)',lambda m:m.group(1)+str(int(m.group(2))+1),t,count=1)
 g.write_text(t,encoding='utf-8')
if w.exists():
 t=w.read_text(encoding='utf-8').replace('DoramaAvatarLipSync-v1.3.6-preview','DoramaAvatarLipSync-v1.3.7-lips-quality')
 w.write_text(t,encoding='utf-8')
p.write_text(s,encoding='utf-8')
print('OK: V1.3.7 — EDTalk local sharpening 0.24; mask feather 0.62..1.0; saved alignment preserved')
