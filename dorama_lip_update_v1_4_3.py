#!/usr/bin/env python3
from pathlib import Path
import re
main=Path('app/src/main/java/com/dorama/avatar/MainActivity.kt')
gradle=Path('app/build.gradle.kts')
if not main.is_file() or not gradle.is_file(): raise SystemExit('Run from repository root')
s=main.read_text(encoding='utf-8'); g=gradle.read_text(encoding='utf-8')
if 'V143_REPORT' in s: raise SystemExit('Already installed')
if 'versionName = "1.4.2"' not in g: raise SystemExit('Expected version 1.4.2')
a='''                        if (f == 0) android.util.Log.i(
                            "DoramaAvatar",
                            "V142 EDTalk mel min=${sourceFrame.minOrNull()} max=${sourceFrame.maxOrNull()} mean=${sourceFrame.average()}"
                        )'''
b='''                            android.util.Log.i("DoramaAvatar", "V142 EDTalk mean pixel difference=${sum / inputPixels.size}")'''
c='''    private fun savePng(bitmap: Bitmap, fileName: String): Uri? {'''
for v in [a,b,c]:
    if s.count(v)!=1: raise SystemExit('Missing expected source anchor')
s=s.replace(a,'''                        if (f == 0) {
                            val melReport = "EDTalk V1.4.3\\n" +
                                "Mel shape: 1x1x80x16\\n" +
                                "Mel min: ${sourceFrame.minOrNull()}\\n" +
                                "Mel max: ${sourceFrame.maxOrNull()}\\n" +
                                "Mel mean: ${sourceFrame.average()}\\n" +
                                "RGB input: 1x3x256x256, validated 0..1\\n"
                            v143Report = melReport
                            android.util.Log.i("DoramaAvatar", melReport)
                        }''',1)
s=s.replace(b,'''                            val diffReport = "Output/input mean RGB absolute difference: ${sum / inputPixels.size}\\n"
                            v143Report += diffReport
                            v143Report += "Engine: EDTalk 256\\n"
                            val reportUri = saveDiagnosticText(v143Report)
                            android.util.Log.i("DoramaAvatar", "V143 report saved: $reportUri")
                            if (reportUri == null) android.util.Log.e("DoramaAvatar", "V143 report save failed")''',1)
# Store per-run report on activity; no requirement for PC/ADB.
needle='''class MainActivity : AppCompatActivity() {'''
assert s.count(needle)==1
s=s.replace(needle,needle+'''
    // V143_REPORT: first-frame diagnostics, exported to Downloads.
    private var v143Report: String = ""
''',1)
s=s.replace(c,'''    private fun saveDiagnosticText(content: String): Uri? {
        return try {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, "EDTalk_Diagnostic_${System.currentTimeMillis()}.txt")
                put(MediaStore.Downloads.MIME_TYPE, "text/plain")
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    put(MediaStore.Downloads.RELATIVE_PATH, "Download/DoramaAvatar")
                }
            }
            val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                ?: return null
            contentResolver.openOutputStream(uri)?.use {
                it.write(content.toByteArray(Charsets.UTF_8))
            } ?: return null
            uri
        } catch (e: Exception) {
            android.util.Log.e("DoramaAvatar", "Diagnostic export failed", e)
            null
        }
    }

'''+c,1)
g=g.replace('versionName = "1.4.2"','versionName = "1.4.3"',1)
g=re.sub(r'versionCode\s*=\s*(\d+)',lambda m:'versionCode = '+str(max(27,int(m.group(1))+1)),g,count=1)
main.write_text(s,encoding='utf-8'); gradle.write_text(g,encoding='utf-8')
print('V1.4.3: diagnostics saved in Download/DoramaAvatar')
