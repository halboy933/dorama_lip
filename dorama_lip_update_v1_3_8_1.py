from pathlib import Path
import re

root=Path(__file__).resolve().parent
main=root/'app/src/main/java/com/dorama/avatar/MainActivity.kt'
gradle=root/'app/build.gradle.kts'
if not main.exists() or not gradle.exists():
    raise SystemExit('Запусти скрипт в корне проекта dorama_lip')
s=main.read_text(encoding='utf-8')
if 'V1381_LANDMARK_RESULT' in s:
    print('Диагностика V1.3.8.1 уже установлена')
else:
    old='''            savePng(out, "V138_04_landmarks_original.png")
            out.recycle()'''
    new='''            val saved = savePng(out, "V138_04_landmarks_original.png")
            out.recycle()
            if (saved == null) throw IllegalStateException("Не удалось сохранить PNG")
            val found = points.count { (type, _) -> face.getLandmark(type) != null }
            runOnUiThread {
                Toast.makeText(this@MainActivity, "EDTalk: найдено точек $found/5; PNG сохранён", Toast.LENGTH_LONG).show()
            }'''
    if s.count(old)!=1: raise SystemExit('Не найден ожидаемый блок сохранения landmarks; исходник не изменён')
    s=s.replace(old,new)
    old='''                    try { saveFaceLandmarkDiagnostic(base) }
                    catch (e: Exception) { android.util.Log.w("DoramaAvatar", "Landmark diagnostic failed", e) }'''
    new='''                    // V1381_LANDMARK_RESULT: show diagnostic failure on screen
                    try { saveFaceLandmarkDiagnostic(base) }
                    catch (e: Exception) {
                        android.util.Log.e("DoramaAvatar", "Landmark diagnostic failed", e)
                        val reason = e.message ?: e.javaClass.simpleName
                        runOnUiThread {
                            Toast.makeText(this@MainActivity, "EDTalk диагностика: $reason", Toast.LENGTH_LONG).show()
                        }
                    }'''
    if s.count(old)!=1: raise SystemExit('Не найден вызов диагностики; исходник не изменён')
    s=s.replace(old,new)
    main.write_text(s,encoding='utf-8')
g=gradle.read_text(encoding='utf-8')
g,n1=re.subn(r'versionCode\s*=\s*\d+', 'versionCode = 22',g,count=1)
g,n2=re.subn(r'versionName\s*=\s*"[^"]+"','versionName = "1.3.8.1"',g,count=1)
if n1!=1 or n2!=1: raise SystemExit('Не найдены versionCode/versionName')
gradle.write_text(g,encoding='utf-8')
print('V1.3.8.1 готово: уведомления диагностики, проверка PNG, versionCode 22, versionName 1.3.8.1')
