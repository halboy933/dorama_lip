#!/usr/bin/env python3
from pathlib import Path
import re
root=Path(__file__).resolve().parent
kt=root/'app/src/main/java/com/dorama/avatar/MainActivity.kt'
gradle=root/'app/build.gradle.kts'
workflow=root/'.github/workflows/build-apk.yml'
if not kt.exists() or not gradle.exists(): raise SystemExit('Запусти скрипт из корня репозитория dorama_lip')
s=kt.read_text()
if 'class FullscreenLipsEditor' in s: raise SystemExit('Редактор V1.3.5 уже установлен')
if 'private inner class MouthSelectionView' not in s: raise SystemExit('Ожидалась исходная V1.3.4; файлы не изменены')
start=s.index('    private inner class MouthSelectionView')
end=s.index('    private val imagePicker',start)
replacement='''    // V1.3.5: fullscreen editor. Image navigation and ellipse editing are independent.
    private inner class FullscreenLipsEditor(context: Context, private val photo: Bitmap) : View(context) {
        private val imagePaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
        private val outline = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.MAGENTA; style = Paint.Style.STROKE; strokeWidth = 3f * resources.displayMetrics.density
        }
        private val overlayFill = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = 0x44FF00FF }
        private val handlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.YELLOW }
        private val matrix = Matrix()
        private val inverse = Matrix()
        private var fitScale = 1f
        private var zoom = 1f
        private var panX = 0f
        private var panY = 0f
        private var mode = 0 // 0=pan image, 1=move ellipse, 2=width, 3=height
        private var lastX = 0f
        private var lastY = 0f
        private var pinchDistance = 0f
        private var pinchZoom = 1f
        private var pinchMidX = 0f
        private var pinchMidY = 0f
        private var pinchImageX = 0f
        private var pinchImageY = 0f
        private val density = resources.displayMetrics.density
        private fun updateMatrix() {
            val scale = fitScale * zoom
            matrix.reset()
            matrix.postScale(scale, scale)
            matrix.postTranslate((width - photo.width * scale) / 2f + panX,
                (height - photo.height * scale) / 2f + panY)
            matrix.invert(inverse)
        }
        private fun toImage(x: Float, y: Float): PointF {
            updateMatrix()
            val p = floatArrayOf(x,y)
            inverse.mapPoints(p)
            return PointF(p[0],p[1])
        }
        private fun toScreen(x: Float,y: Float): PointF {
            updateMatrix()
            val p = floatArrayOf(x,y)
            matrix.mapPoints(p)
            return PointF(p[0],p[1])
        }
        override fun onSizeChanged(w: Int,h: Int,oldw: Int,oldh: Int) {
            super.onSizeChanged(w,h,oldw,oldh)
            fitScale = min(w.toFloat()/photo.width,h.toFloat()/photo.height)
        }
        override fun onDraw(canvas: Canvas) {
            canvas.drawColor(Color.BLACK)
            updateMatrix()
            canvas.drawBitmap(photo,matrix,imagePaint)
            val cx=lipX*photo.width; val cy=lipY*photo.height
            val rx=lipRx*photo.width; val ry=lipRy*photo.height
            val center=toScreen(cx,cy)
            val sc=fitScale*zoom
            canvas.save()
            canvas.rotate(lipRotation,center.x,center.y)
            val rect=RectF(center.x-rx*sc,center.y-ry*sc,center.x+rx*sc,center.y+ry*sc)
            canvas.drawOval(rect,overlayFill)
            canvas.drawOval(rect,outline)
            canvas.drawCircle(center.x,center.y,7*density,handlePaint)
            canvas.drawCircle(center.x+rx*sc,center.y,10*density,handlePaint)
            canvas.drawCircle(center.x,center.y+ry*sc,10*density,handlePaint)
            canvas.restore()
        }
        private fun hitHandle(x: Float,y: Float): Int {
            val c=toScreen(lipX*photo.width,lipY*photo.height)
            val sc=fitScale*zoom
            val rad=Math.toRadians(lipRotation.toDouble())
            val co=cos(rad).toFloat(); val si=sin(rad).toFloat()
            val wx=c.x+lipRx*photo.width*sc*co
            val wy=c.y+lipRx*photo.width*sc*si
            val hx=c.x-lipRy*photo.height*sc*si
            val hy=c.y+lipRy*photo.height*sc*co
            val hit=32*density
            if (hypot(x-wx,y-wy)<hit) return 2
            if (hypot(x-hx,y-hy)<hit) return 3
            val dx=x-c.x; val dy=y-c.y
            val ux=dx*co+dy*si; val uy=-dx*si+dy*co
            val ex=max(12*density,lipRx*photo.width*sc)
            val ey=max(12*density,lipRy*photo.height*sc)
            if (ux*ux/(ex*ex)+uy*uy/(ey*ey)<=1.8f) return 1
            return 0
        }
        override fun onTouchEvent(event: MotionEvent): Boolean {
            when(event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    mode=hitHandle(event.x,event.y)
                    lastX=event.x;lastY=event.y
                    return true
                }
                MotionEvent.ACTION_POINTER_DOWN -> {
                    if(event.pointerCount>=2) {
                        mode=4
                        val dx=event.getX(0)-event.getX(1)
                        val dy=event.getY(0)-event.getY(1)
                        pinchDistance=max(1f,hypot(dx,dy))
                        pinchZoom=zoom
                        pinchMidX=(event.getX(0)+event.getX(1))/2f
                        pinchMidY=(event.getY(0)+event.getY(1))/2f
                        val p=toImage(pinchMidX,pinchMidY)
                        pinchImageX=p.x;pinchImageY=p.y
                    }
                    return true
                }
                MotionEvent.ACTION_MOVE -> {
                    if(mode==4 && event.pointerCount>=2) {
                        val mx=(event.getX(0)+event.getX(1))/2f
                        val my=(event.getY(0)+event.getY(1))/2f
                        zoom=(pinchZoom*hypot(event.getX(0)-event.getX(1),event.getY(0)-event.getY(1))/pinchDistance).coerceIn(1f,12f)
                        val sc=fitScale*zoom
                        panX=mx-(width-photo.width*sc)/2f-pinchImageX*sc
                        panY=my-(height-photo.height*sc)/2f-pinchImageY*sc
                    } else if(mode==0) {
                        panX+=event.x-lastX;panY+=event.y-lastY
                    } else {
                        val p=toImage(event.x,event.y)
                        val cX=lipX*photo.width;val cY=lipY*photo.height
                        if(mode==1) {
                            val prev=toImage(lastX,lastY)
                            lipX=((cX+p.x-prev.x)/photo.width).coerceIn(0f,1f)
                            lipY=((cY+p.y-prev.y)/photo.height).coerceIn(0f,1f)
                        } else {
                            val rad=Math.toRadians(lipRotation.toDouble())
                            val dx=p.x-cX;val dy=p.y-cY
                            val u=(dx*cos(rad)+dy*sin(rad)).toFloat()
                            val v=(-dx*sin(rad)+dy*cos(rad)).toFloat()
                            if(mode==2) lipRx=(abs(u)/photo.width).coerceIn(0.005f,0.45f)
                            if(mode==3) lipRy=(abs(v)/photo.height).coerceIn(0.005f,0.35f)
                        }
                    }
                    lastX=event.x;lastY=event.y
                    invalidate();return true
                }
                MotionEvent.ACTION_POINTER_UP -> {
                    mode=0
                    val remaining=if(event.actionIndex==0) 1 else 0
                    lastX=event.getX(remaining);lastY=event.getY(remaining)
                    return true
                }
                MotionEvent.ACTION_UP -> { performClick(); return true }
                MotionEvent.ACTION_CANCEL -> { return true }
            }
            return true
        }
        override fun performClick(): Boolean { super.performClick();return true }
    }

    private fun openLipsEditor() {
        val uri=imageUri ?: run {
            Toast.makeText(this,"Сначала выбери фотографию",Toast.LENGTH_SHORT).show();return
        }
        val photo=try {
            contentResolver.openInputStream(uri)?.use { BitmapFactory.decodeStream(it) }
        } catch(e:Exception) { null }
        if(photo==null) {
            Toast.makeText(this,"Не удалось открыть фотографию",Toast.LENGTH_LONG).show();return
        }
        val old=floatArrayOf(lipX,lipY,lipRx,lipRy,lipRotation)
        val dialog=android.app.Dialog(this,android.R.style.Theme_Black_NoTitleBar_Fullscreen)
        val root=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setBackgroundColor(Color.BLACK) }
        val editor=FullscreenLipsEditor(this,photo)
        root.addView(editor,LinearLayout.LayoutParams(-1,0,1f))
        val info=TextView(this).apply {
            text="Перемещай фото вне эллипса • 2 пальца — масштаб • жёлтые точки — ширина и высота"
            setTextColor(Color.WHITE);textSize=12f;setPadding(12,8,12,8)
        }
        root.addView(info)
        val rotationText=TextView(this).apply {setTextColor(Color.WHITE);text="Наклон эллипса: ${lipRotation.toInt()}°";setPadding(12,4,12,4)}
        root.addView(rotationText)
        val angle=SeekBar(this).apply {
            max=180;progress=(lipRotation+90).toInt().coerceIn(0,180)
            setOnSeekBarChangeListener(object:SeekBar.OnSeekBarChangeListener {
                override fun onProgressChanged(bar:SeekBar?,value:Int,fromUser:Boolean) {
                    lipRotation=(value-90).toFloat();rotationText.text="Наклон эллипса: ${value-90}°";editor.invalidate()
                }
                override fun onStartTrackingTouch(bar:SeekBar?) {}
                override fun onStopTrackingTouch(bar:SeekBar?) {}
            })
        }
        root.addView(angle)
        val buttons=LinearLayout(this).apply {orientation=LinearLayout.HORIZONTAL}
        val reset=Button(this).apply {text="Сброс";setOnClickListener {
            lipX=.5f;lipY=.72f;lipRx=.105f;lipRy=.045f;lipRotation=0f
            angle.progress=90;editor.invalidate()
        }}
        val cancel=Button(this).apply {text="Отмена";setOnClickListener {
            lipX=old[0];lipY=old[1];lipRx=old[2];lipRy=old[3];lipRotation=old[4]
            dialog.dismiss()
        }}
        val save=Button(this).apply {text="Сохранить";setOnClickListener {saveLips();dialog.dismiss()}}
        for(button in arrayOf(reset,cancel,save)) buttons.addView(button,LinearLayout.LayoutParams(0,-2,1f))
        root.addView(buttons)
        dialog.setContentView(root)
        dialog.setOnCancelListener {
            lipX=old[0];lipY=old[1];lipRx=old[2];lipRy=old[3];lipRotation=old[4]
        }
        dialog.setOnDismissListener { photo.recycle() }
        dialog.show()
    }

    private fun installLipSelector() {
        // Main screen preview stays non-interactive. All editing happens fullscreen.
        val parent=preview.parent as? ViewGroup ?: return
        val button=Button(this).apply {text="Настроить область губ (полный экран)";setOnClickListener {openLipsEditor()}}
        if(parent is LinearLayout) {
            val idx=parent.indexOfChild(preview)
            parent.addView(button,idx+1,LinearLayout.LayoutParams(-1,-2))
        } else {
            // Fallback: attach editor button in the root layout.
            val root=findViewById<ViewGroup>(android.R.id.content)
            val panel=root.getChildAt(0) as? LinearLayout
            panel?.addView(button)
        }
    }

'''
s=s[:start]+replacement+s[end:]
s=s.replace('private var lipSelection: MouthSelectionView? = null','private var lipRotation = 0f')
s=s.replace('.putFloat("rx", lipRx).putFloat("ry", lipRy).apply()', '.putFloat("rx", lipRx).putFloat("ry", lipRy)\n            .putFloat("rotation", lipRotation).apply()')
s=s.replace('            lipSelection?.invalidate()','')
s=s.replace('        lipRy = lipPrefs.getFloat("ry", 0.045f)','        lipRy = lipPrefs.getFloat("ry", 0.045f)\n        lipRotation = lipPrefs.getFloat("rotation", 0f)')
# apply rotation in ellipse mask, matching editor coordinates; normalized to photo
s=s.replace('                val dx = (x - mouthCx) / (base.width * lipRx).coerceAtLeast(1f)\n                val dy = (y - mouthCy) / (base.height * lipRy).coerceAtLeast(1f)', '''                val radians = Math.toRadians(lipRotation.toDouble())
                val cs = cos(radians).toFloat()
                val sn = sin(radians).toFloat()
                val relX = x - mouthCx
                val relY = y - mouthCy
                val dx = (relX * cs + relY * sn) / (base.width * lipRx).coerceAtLeast(1f)
                val dy = (-relX * sn + relY * cs) / (base.height * lipRy).coerceAtLeast(1f)''')
# hoist trig outside nested pixel loops
s=s.replace('        for (y in 0 until c.height) {\n            val fy', '        val maskRadians = Math.toRadians(lipRotation.toDouble())\n        val maskCos = cos(maskRadians).toFloat()\n        val maskSin = sin(maskRadians).toFloat()\n        for (y in 0 until c.height) {\n            val fy',1)
s=s.replace('                val radians = Math.toRadians(lipRotation.toDouble())\n                val cs = cos(radians).toFloat()\n                val sn = sin(radians).toFloat()\n','')
s=s.replace('relX * cs + relY * sn','relX * maskCos + relY * maskSin').replace('-relX * sn + relY * cs','-relX * maskSin + relY * maskCos')
s=s.replace('V1.3.4','V1.3.5').replace('V134_','V135_').replace('v134_','v135_')
# fix pre-existing odd behavior: cancel resets state but no persisted change
# validate structural changes before writing
assert 'private inner class FullscreenLipsEditor' in s and 'lipSelection' not in s
assert 'maskCos' in s and 'lipRotation' in s
b=gradle.read_text()
if not re.search(r'versionCode\s*=\s*17\b',b) or 'versionName = "1.3.4"' not in b:
    raise SystemExit('Ожидалась версия 1.3.4 (code 17); файлы не изменены')
b=re.sub(r'versionCode\s*=\s*17\b','versionCode = 18',b,count=1).replace('versionName = "1.3.4"','versionName = "1.3.5"',1)
kt.write_text(s)
gradle.write_text(b)
if workflow.exists():
    w=workflow.read_text()
    w=re.sub(r'DoramaAvatarLipSync-v1\.3\.[34][\w-]*','DoramaAvatarLipSync-v1.3.5-fullscreen-lips',w)
    workflow.write_text(w)
print('✓ V1.3.5 fullscreen lips editor применён')
print('✓ Эллипс: центр, ширина, высота, угол; масштаб/панорамирование фото')
print('✓ Маска генерации учитывает поворот эллипса')
print('✓ versionCode 18 / versionName 1.3.5')
print('Дальше: git diff --stat; commit/push; GitHub Actions')
