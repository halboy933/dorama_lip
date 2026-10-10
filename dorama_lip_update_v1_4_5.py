#!/usr/bin/env python3
from pathlib import Path
import re
m=Path('app/src/main/java/com/dorama/avatar/MainActivity.kt'); w=Path('app/src/main/java/com/dorama/avatar/WavUtils.kt'); g=Path('app/build.gradle.kts')
if not all(p.exists() for p in (m,w,g)): raise SystemExit('Run from repo root')
s=m.read_text(); t=w.read_text(); b=g.read_text()
if 'V145_AUDIO_AB' in s: raise SystemExit('Already patched')
if 'versionName = "1.4.4"' not in b: raise SystemExit('Expected V1.4.4')
anchors=['    private var engineMode: String = "edtalk256"','        val engineGroup = findViewById<RadioGroup>(R.id.engineGroup)','                val engineAtStart = engineMode','                        val sourceFrame = WavUtils.edtalkFrame(spec, f)','                    v143Report = WavUtils.edtalkMelReport(spec, frames)']
assert all(s.count(x)==1 for x in anchors)
needle='    fun edtalkFrame(spec: Array<FloatArray>, frameIndex: Int, fps: Int = 25): FloatArray {'
assert t.count(needle)==1
t=t.replace(needle,'''    // V145_AUDIO_AB: undo Hann-window sum normalization in experimental mode.
    fun edtalkFrameExperimental(spec: Array<FloatArray>, frameIndex: Int, fps: Int = 25): FloatArray {
        val start = floor(frameIndex * 80.0 / fps).toInt()
        val out = FloatArray(N_MELS * 16)
        for (m in 0 until N_MELS) for (x in 0 until 16) {
            val raw = spec[m][(start + x).coerceAtMost(spec[m].lastIndex)]
            out[m * 16 + x] = (log10(max(1e-5f, raw * 400f).toDouble()) * 1.6 + 3.2)
                .toFloat().coerceIn(-4f, 4f)
        }
        return out
    }

'''+needle,1)
s=s.replace(anchors[0],anchors[0]+'\n    // V145_AUDIO_AB\n    private var experimentalAudio = false',1)
s=s.replace(anchors[1],'''        experimentalAudio = prefs.getBoolean("edtalk_experimental_audio", false)
        val audioToggle = CheckBox(this).apply {
            text = "EDTalk: экспериментальный звук (×400)"
            isChecked = experimentalAudio
            setOnCheckedChangeListener { _, checked ->
                experimentalAudio = checked
                prefs.edit().putBoolean("edtalk_experimental_audio", checked).apply()
            }
        }
        // Insert immediately below engine selection; no XML changes required.
        val engineGroup = findViewById<RadioGroup>(R.id.engineGroup)
        (engineGroup.parent as? ViewGroup)?.let { parent ->
            val index = parent.indexOfChild(engineGroup)
            parent.addView(audioToggle, index + 1)
        }''',1)
s=s.replace(anchors[2],anchors[2]+'\n                val experimentalAudioAtStart = experimentalAudio',1)
s=s.replace(anchors[3],'''                        val sourceFrame = if (experimentalAudioAtStart) {
                            WavUtils.edtalkFrameExperimental(spec, f)
                        } else {
                            WavUtils.edtalkFrame(spec, f)
                        }''',1)
s=s.replace(anchors[4],'''                    v143Report = "V1.4.5 selected mode: " +
                        (if (experimentalAudioAtStart) "experimental x400" else "original") + "\\n" +
                        WavUtils.edtalkMelReport(spec, frames)''',1)
b=b.replace('versionName = "1.4.4"','versionName = "1.4.5"',1)
b=re.sub(r'versionCode\s*=\s*(\d+)',lambda x:'versionCode = '+str(max(29,int(x.group(1))+1)),b,count=1)
m.write_text(s);w.write_text(t);g.write_text(b)
print('V1.4.5 applied. Select audio mode in checkbox; compare two videos.')
