#!/usr/bin/env python3
from pathlib import Path
import re
src=Path('app/src/main/java/com/dorama/avatar/MainActivity.kt')
gradle=Path('app/build.gradle.kts')
if not src.exists() or not gradle.exists():
    raise SystemExit('Run in the repository root')
s=src.read_text(encoding='utf-8')
g=gradle.read_text(encoding='utf-8')
if 'V141_DIRECT_INVERSE_RENDER' in s:
    raise SystemExit('Already patched')
assert 'val mappedFace = unalignEdtalkFace(face, aligned, crop)' in s
old='''        val generatedScaled = Bitmap.createScaledBitmap(generated96, c.width, c.height, true)
        val generated = if (generated96.width <= 96) {
            val sharp = sharpenGenerated(generatedScaled)
            generatedScaled.recycle()
            sharp
        } else {
            // V1.3.7: localized detail enhancement. The generated face is only
            // inserted through the lip mask, so original skin stays untouched.
            // Keep sharpening mild: EDTalk cannot reconstruct missing detail.
            val enhanced = sharpenGenerated(generatedScaled, 0.24f)
            generatedScaled.recycle()
            enhanced
        }'''
assert old in s
new='''        // V141_DIRECT_INVERSE_RENDER: EDTalk is already inverse-mapped to crop
        // coordinates. Do not rescale or sharpen it a second time.
        val generated = if (generated96.width == c.width && generated96.height == c.height) {
            generated96.copy(Bitmap.Config.ARGB_8888, false)
        } else {
            val scaled = Bitmap.createScaledBitmap(generated96, c.width, c.height, true)
            val sharp = sharpenGenerated(scaled, if (generated96.width <= 96) 0.48f else 0.24f)
            scaled.recycle()
            sharp
        }'''
s=s.replace(old,new,1)
# Note: for Wav2Lip, image dimensions differ from crop, so old processing is retained.
# EDTalk retains alpha-transparent outside inverse warp.
needle='''                            savePng(mappedFace, "V140_03_inverse_mapped_${stamp}.png")'''
assert needle in s
s=s.replace(needle,needle+'''
                            savePng(mappedFace, "V141_01_direct_inverse_no_rescale_${stamp}.png")''',1)
needle2='''                            savePng(composed, "V140_04_composite_before_encoder_${stamp}.png")'''
assert needle2 in s
s=s.replace(needle2,needle2+'''
                            savePng(composed, "V141_02_composite_no_double_scale_${stamp}.png")''',1)
assert 'versionName = "1.4.0"' in g
g=g.replace('versionName = "1.4.0"','versionName = "1.4.1"',1)
g=re.sub(r'versionCode\s*=\s*(\d+)',lambda m:'versionCode = '+str(max(25,int(m.group(1))+1)),g,count=1)
src.write_text(s,encoding='utf-8')
gradle.write_text(g,encoding='utf-8')
print('Applied V1.4.1. EDTalk avoids redundant scaling/sharpening; Wav2Lip path unchanged.')
