from pathlib import Path
import re
w=Path('app/src/main/java/com/dorama/avatar/WavUtils.kt');m=Path('app/src/main/java/com/dorama/avatar/MainActivity.kt');g=Path('app/build.gradle.kts')
if not all(p.is_file() for p in (w,m,g)): raise SystemExit('Run from repo root')
ws=w.read_text();ms=m.read_text();gs=g.read_text()
if 'V144_MEL_DIAGNOSTICS' in ws: raise SystemExit('Already applied')
if 'versionName = "1.4.3"' not in gs: raise SystemExit('Expected 1.4.3')
anchor='    fun edtalkFrame(spec: Array<FloatArray>, frameIndex: Int, fps: Int = 25): FloatArray {'
assert ws.count(anchor)==1
extra='''    // V144_MEL_DIAGNOSTICS: report-only, no inference changes.
    fun edtalkMelReport(spec: Array<FloatArray>, totalFrames: Int): String {
        val picks = listOf(0, totalFrames / 4, totalFrames / 2, 3 * totalFrames / 4, totalFrames - 1)
            .filter { it >= 0 }.distinct()
        val gain = WIN * 0.5f // Hann sum = 400 for 800 samples
        val sb = StringBuilder("EDTalk V1.4.4 mel comparison\\n")
        sb.append("Current: log10(max(raw,1e-5))*1.6+3.2, clamp [-4,4]\\n")
        sb.append("Alternative: multiply raw by 400 before log; diagnostic only\\n")
        for (f in picks) {
            val current = edtalkFrame(spec, f)
            val start = floor(f * 80.0 / 25).toInt()
            val alternative = FloatArray(N_MELS * 16)
            for (mel in 0 until N_MELS) for (i in 0 until 16) {
                val raw = spec[mel][(start + i).coerceAtMost(spec[mel].lastIndex)]
                alternative[mel * 16 + i] =
                    (log10(max(1e-5f, raw * gain).toDouble()) * 1.6 + 3.2).toFloat().coerceIn(-4f, 4f)
            }
            fun stats(label: String, a: FloatArray): String =
                "$label min=${a.minOrNull()} max=${a.maxOrNull()} mean=${a.average()} floor=${a.count { it <= -3.999f }}/${a.size}\\n"
            sb.append("frame=$f\\n")
            sb.append(stats("current", current))
            sb.append(stats("windowGain400", alternative))
        }
        return sb.toString()
    }

'''
ws=ws.replace(anchor,extra+anchor,1)
anchor2='                    val spec = WavUtils.edtalkSpectrogram(samples)'
assert ms.count(anchor2)==1
ms=ms.replace(anchor2,anchor2+'''
                    // V144_MEL_DIAGNOSTICS: exported to Downloads without ADB.
                    v143Report = WavUtils.edtalkMelReport(spec, frames)
                    val v144ReportUri = saveDiagnosticText(v143Report)
                    android.util.Log.i("DoramaAvatar", "V144 report: $v144ReportUri")''',1)
assert ms.count('                            v143Report = melReport')==1
ms=ms.replace('                            v143Report = melReport','                            v143Report += "\\n" + melReport',1)
gs=gs.replace('versionName = "1.4.3"','versionName = "1.4.4"',1)
gs=re.sub(r'versionCode\s*=\s*(\d+)',lambda z:'versionCode = '+str(max(28,int(z.group(1))+1)),gs,count=1)
w.write_text(ws);m.write_text(ms);g.write_text(gs)
print('V1.4.4 installed')
