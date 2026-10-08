from pathlib import Path
p=Path('app/src/main/java/com/dorama/avatar/MainActivity.kt')
if not p.exists():
    raise SystemExit('Не найден MainActivity.kt — запустите из корня репозитория')
s=p.read_text(encoding='utf-8')
old='''        val root=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setBackgroundColor(Color.BLACK) }
        val editor=FullscreenLipsEditor(this,photo)
        root.addView(editor,LinearLayout.LayoutParams(-1,0,1f))'''
new='''        // V1.3.5.1: fullscreen image, controls anchored independently at bottom.
        val root=FrameLayout(this).apply { setBackgroundColor(Color.BLACK) }
        val editor=FullscreenLipsEditor(this,photo)
        root.addView(editor,FrameLayout.LayoutParams(-1,-1))
        val controls=LinearLayout(this).apply {
            orientation=LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(24,24,24))
            val d=resources.displayMetrics.density
            setPadding((8*d).toInt(),(6*d).toInt(),(8*d).toInt(),(6*d).toInt())
        }'''
if old not in s: raise SystemExit('Ожидаемая структура V1.3.5 не найдена; изменений нет')
s=s.replace(old,new,1)
for a,b in [('root.addView(info)','controls.addView(info)'),('root.addView(rotationText)','controls.addView(rotationText)'),('root.addView(angle)','controls.addView(angle)'),('root.addView(buttons)','controls.addView(buttons)')]:
    if a not in s: raise SystemExit('Не найдено '+a)
    s=s.replace(a,b,1)
needle='''        controls.addView(buttons)
        dialog.setContentView(root)'''
replacement='''        controls.addView(buttons)
        // Keep controls above gesture/navigation bar on Android 10+.
        controls.setOnApplyWindowInsetsListener { view, insets ->
            val d=resources.displayMetrics.density
            val bottom=if (Build.VERSION.SDK_INT >= 30) {
                insets.getInsets(android.view.WindowInsets.Type.navigationBars()).bottom
            } else {
                @Suppress("DEPRECATION")
                insets.systemWindowInsetBottom
            }
            view.setPadding((8*d).toInt(),(6*d).toInt(),(8*d).toInt(),(6*d).toInt()+bottom)
            insets
        }
        root.addView(controls,FrameLayout.LayoutParams(-1,-2,android.view.Gravity.BOTTOM))
        dialog.setContentView(root)'''
if needle not in s: raise SystemExit('Не найдена точка установки панели')
s=s.replace(needle,replacement,1)
s=s.replace('V1.3.5 ГОТОВА','V1.3.5.1 ГОТОВА').replace('V1.3.5: $engineLabel','V1.3.5.1: $engineLabel')
p.write_text(s,encoding='utf-8')
g=Path('app/build.gradle.kts')
if g.exists():
    t=g.read_text(encoding='utf-8')
    import re
    t,n=re.subn(r'versionName\s*=\s*"1\.3\.5"','versionName = "1.3.5.1"',t,count=1)
    t=re.sub(r'(versionCode\s*=\s*)(\d+)',lambda m:m.group(1)+str(int(m.group(2))+1),t,count=1) if n else t
    g.write_text(t,encoding='utf-8')
w=Path('.github/workflows/build-apk.yml')
if w.exists():
    t=w.read_text(encoding='utf-8').replace('DoramaAvatarLipSync-v1.3.5-stable','DoramaAvatarLipSync-v1.3.5.1-stable').replace('DoramaAvatarLipSync-v1.3.5-manual-lips','DoramaAvatarLipSync-v1.3.5.1-stable')
    w.write_text(t,encoding='utf-8')
print('OK: V1.3.5.1 — нижняя панель закреплена; сохранение доступно внизу')
