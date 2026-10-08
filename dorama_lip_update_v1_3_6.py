from pathlib import Path
import re
p=Path('app/src/main/java/com/dorama/avatar/MainActivity.kt')
if not p.exists(): raise SystemExit('Запустите из корня репозитория')
s=p.read_text(encoding='utf-8')
if 'V1.3.6: alignment preview' in s: raise SystemExit('Патч уже установлен')
if 'private inner class FullscreenLipsEditor' not in s or 'val controls=LinearLayout(this)' not in s:
    raise SystemExit('Требуется установленная V1.3.5.1 с закреплённой панелью')
needle='''        private val matrix = Matrix()'''
addition='''        // V1.3.6: alignment preview (original pixels, NOT AI generated lips).
        var showAlignmentPreview = false
        var previewShiftX = 0
        var previewShiftY = 0
        var previewAngle = 0
        var previewScale = 100
        private val previewPaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
        private val matrix = Matrix()'''
assert needle in s
s=s.replace(needle,addition,1)
needle='''            canvas.drawBitmap(photo,matrix,imagePaint)
            val cx=lipX*photo.width; val cy=lipY*photo.height'''
addition='''            canvas.drawBitmap(photo,matrix,imagePaint)
            if (showAlignmentPreview) {
                // Approximate alignment: use original photo pixels to preview position,
                // rotation and scale before costly ONNX generation.
                val centerX=lipX*photo.width; val centerY=lipY*photo.height
                val rX=lipRx*photo.width; val rY=lipRy*photo.height
                val sc=fitScale*zoom
                val center=toScreen(centerX,centerY)
                val clip=Path().apply {
                    addOval(RectF(-rX*sc,-rY*sc,rX*sc,rY*sc),Path.Direction.CW)
                }
                val generatedTransform=Matrix().apply {
                    postScale(previewScale/100f,previewScale/100f,centerX,centerY)
                    postRotate(previewAngle.toFloat(),centerX,centerY)
                    // The actual renderer uses face-crop dimensions; estimate here.
                    postTranslate(previewShiftX*rX*3f/100f,previewShiftY*rY*5f/100f)
                }
                val combined=Matrix(matrix).apply { preConcat(generatedTransform) }
                canvas.save()
                canvas.translate(center.x,center.y)
                canvas.rotate(lipRotation)
                canvas.clipPath(clip)
                canvas.translate(-center.x,-center.y)
                canvas.drawBitmap(photo,combined,previewPaint)
                canvas.restore()
            }
            val cx=lipX*photo.width; val cy=lipY*photo.height'''
assert needle in s
s=s.replace(needle,addition,1)
needle='''        controls.addView(buttons)
        // Keep controls above gesture/navigation bar on Android 10+.'''
addition='''        // V1.3.6: adjustment controls inside the editor, live approximate preview.
        val previewToggle=CheckBox(this).apply {
            text="Предпросмотр совмещения (без ИИ)"
            setTextColor(Color.WHITE)
            isChecked=true
            editor.showAlignmentPreview=true
            setOnCheckedChangeListener { _, checked ->
                editor.showAlignmentPreview=checked
                editor.invalidate()
            }
        }
        controls.addView(previewToggle)
        val calibrationPrefs=getSharedPreferences("dorama_avatar_calibration",MODE_PRIVATE)
        fun adjustment(label:String,min:Int,max:Int,initial:Int,unit:String,onUpdate:(Int)->Unit) {
            val line=LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL }
            val title=TextView(this).apply {
                setTextColor(Color.WHITE)
                textSize=12f
                text="$label: $initial$unit"
                gravity=android.view.Gravity.CENTER_VERTICAL
            }
            line.addView(title,LinearLayout.LayoutParams((105*resources.displayMetrics.density).toInt(),-2))
            val bar=SeekBar(this).apply {
                this.max=max-min
                progress=(initial-min).coerceIn(0,max-min)
                setOnSeekBarChangeListener(object:SeekBar.OnSeekBarChangeListener {
                    override fun onProgressChanged(b:SeekBar?,v:Int,fromUser:Boolean) {
                        val value=v+min
                        title.text="$label: $value$unit"
                        onUpdate(value)
                        editor.invalidate()
                    }
                    override fun onStartTrackingTouch(b:SeekBar?) {}
                    override fun onStopTrackingTouch(b:SeekBar?) {}
                })
            }
            line.addView(bar,LinearLayout.LayoutParams(0,-2,1f))
            controls.addView(line)
        }
        editor.previewShiftX=mouthOffsetXPercent
        editor.previewShiftY=mouthOffsetYPercent
        editor.previewAngle=mouthAngleDeg
        editor.previewScale=mouthScalePercent
        adjustment("Сдвиг X",-20,20,mouthOffsetXPercent,"%") {
            mouthOffsetXPercent=it;editor.previewShiftX=it
        }
        adjustment("Сдвиг Y",-15,15,mouthOffsetYPercent,"%") {
            mouthOffsetYPercent=it;editor.previewShiftY=it
        }
        adjustment("Поворот",-12,12,mouthAngleDeg,"°") {
            mouthAngleDeg=it;editor.previewAngle=it
        }
        adjustment("Масштаб",85,115,mouthScalePercent,"%") {
            mouthScalePercent=it;editor.previewScale=it
        }
        val hint=TextView(this).apply {
            text="Предпросмотр показывает сдвиг исходного фото, не результат нейросети"
            setTextColor(Color.LTGRAY);textSize=10f
        }
        controls.addView(hint)
        // Keep save/cancel buttons last and visible.
        controls.removeView(buttons)
        controls.addView(buttons)
        // Keep controls above gesture/navigation bar on Android 10+.'''
assert needle in s
s=s.replace(needle,addition,1)
# Need ensure editor controls do not obscure entire image on small screens: scroll only adjustment block by replacing with ScrollView wrapper? panel is ~400dp; add a max height relative to screen and scroll controls.
needle='''        root.addView(controls,FrameLayout.LayoutParams(-1,-2,android.view.Gravity.BOTTOM))'''
replacement='''        val scroller=ScrollView(this).apply {
            isFillViewport=false
            addView(controls)
        }
        val maxPanel=(resources.displayMetrics.heightPixels*0.55f).toInt()
        root.addView(scroller,FrameLayout.LayoutParams(-1,maxPanel,android.view.Gravity.BOTTOM))'''
assert needle in s
s=s.replace(needle,replacement,1)
# Save calibration and restore on cancel, plus editor labels refreshed when reopening main screen via seekbar refs.
needle='''        val old=floatArrayOf(lipX,lipY,lipRx,lipRy,lipRotation)'''
replacement='''        val old=floatArrayOf(lipX,lipY,lipRx,lipRy,lipRotation)
        val oldCalibration=intArrayOf(mouthOffsetXPercent,mouthOffsetYPercent,mouthAngleDeg,mouthScalePercent)
        fun restoreCalibration() {
            mouthOffsetXPercent=oldCalibration[0];mouthOffsetYPercent=oldCalibration[1]
            mouthAngleDeg=oldCalibration[2];mouthScalePercent=oldCalibration[3]
        }
        fun refreshMainCalibration() {
            findViewById<SeekBar>(R.id.mouthOffsetXSeek)?.progress=(mouthOffsetXPercent+20).coerceIn(0,40)
            findViewById<SeekBar>(R.id.mouthOffsetYSeek)?.progress=(mouthOffsetYPercent+15).coerceIn(0,30)
            findViewById<SeekBar>(R.id.mouthAngleSeek)?.progress=(mouthAngleDeg+12).coerceIn(0,24)
            findViewById<SeekBar>(R.id.mouthScaleSeek)?.progress=(mouthScalePercent-85).coerceIn(0,30)
        }'''
assert needle in s
s=s.replace(needle,replacement,1)
s=s.replace('''            dialog.dismiss()
        }}
        val save=Button''','''            restoreCalibration();dialog.dismiss()
        }}
        val save=Button''',1)
s=s.replace('''val save=Button(this).apply {text="Сохранить";setOnClickListener {saveLips();dialog.dismiss()}}''','''val save=Button(this).apply {text="Сохранить";setOnClickListener {
            saveLips()
            calibrationPrefs.edit().putInt("mouth_x",mouthOffsetXPercent)
                .putInt("mouth_y",mouthOffsetYPercent)
                .putInt("mouth_angle",mouthAngleDeg)
                .putInt("mouth_scale",mouthScalePercent).apply()
            refreshMainCalibration()
            dialog.dismiss()
        }}''',1)
# Kotlin local variable calibrationPrefs declared after save lambda; local capture before declaration invalid. Move declaration earlier.
s=s.replace('''        val oldCalibration=intArrayOf''','''        val calibrationPrefs=getSharedPreferences("dorama_avatar_calibration",MODE_PRIVATE)
        val oldCalibration=intArrayOf''',1)
s=s.replace('''        val calibrationPrefs=getSharedPreferences("dorama_avatar_calibration",MODE_PRIVATE)
        fun adjustment''','''        fun adjustment''',1)
s=s.replace('''        dialog.setOnCancelListener {
            lipX=old[0];lipY=old[1];lipRx=old[2];lipRy=old[3];lipRotation=old[4]
        }''','''        dialog.setOnCancelListener {
            lipX=old[0];lipY=old[1];lipRx=old[2];lipRy=old[3];lipRotation=old[4]
            restoreCalibration()
        }''',1)
# Keep save buttons anchored: scrollview issue, move buttons out of scroll and use bottom stack.
s=s.replace('''        controls.removeView(buttons)
        controls.addView(buttons)''','''        controls.removeView(buttons)''',1)
s=s.replace('''        root.addView(scroller,FrameLayout.LayoutParams(-1,maxPanel,android.view.Gravity.BOTTOM))''','''        val bottomPanel=LinearLayout(this).apply {
            orientation=LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(24,24,24))
        }
        bottomPanel.addView(scroller,LinearLayout.LayoutParams(-1,maxPanel-(58*resources.displayMetrics.density).toInt()))
        bottomPanel.addView(buttons,LinearLayout.LayoutParams(-1,-2))
        root.addView(bottomPanel,FrameLayout.LayoutParams(-1,-2,android.view.Gravity.BOTTOM))''',1)
# move insets to bottomPanel rather than scroll controls
s=s.replace('''        controls.setOnApplyWindowInsetsListener { view, insets ->''','''        // Insets applied to bottom panel after it is created.
        /* controls.setOnApplyWindowInsetsListener { view, insets ->''',1)
s=s.replace('''            insets
        }
        val scroller''','''            insets
        } */
        val scroller''',1)
s=s.replace('''        root.addView(bottomPanel,FrameLayout.LayoutParams(-1,-2,android.view.Gravity.BOTTOM))''','''        bottomPanel.setOnApplyWindowInsetsListener { view, insets ->
            val bottom=if(Build.VERSION.SDK_INT>=30)
                insets.getInsets(android.view.WindowInsets.Type.navigationBars()).bottom
            else insets.systemWindowInsetBottom
            view.setPadding(0,0,0,bottom)
            insets
        }
        root.addView(bottomPanel,FrameLayout.LayoutParams(-1,-2,android.view.Gravity.BOTTOM))''',1)
p.write_text(s,encoding='utf-8')
g=Path('app/build.gradle.kts')
if g.exists():
 t=g.read_text(encoding='utf-8')
 t=re.sub(r'versionName\s*=\s*"1\.3\.5(?:\.1)?"','versionName = "1.3.6"',t,count=1)
 t=re.sub(r'(versionCode\s*=\s*)(\d+)',lambda m:m.group(1)+str(int(m.group(2))+1),t,count=1)
 g.write_text(t,encoding='utf-8')
w=Path('.github/workflows/build-apk.yml')
if w.exists():
 t=w.read_text(encoding='utf-8')
 t=re.sub(r'DoramaAvatarLipSync-v1\.3\.5(?:\.1)?[^\s"\']*','DoramaAvatarLipSync-v1.3.6-preview',t)
 w.write_text(t,encoding='utf-8')
print('OK: V1.3.6 preview; model and encoding unchanged')
