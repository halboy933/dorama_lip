package com.dorama.avatar

import ai.onnxruntime.*
import android.content.ContentValues
import android.graphics.*
import android.media.*
import android.net.Uri
import android.os.Bundle
import android.os.Build
import android.os.Environment
import android.provider.MediaStore
import android.provider.OpenableColumns
import android.widget.*
import android.view.View
import android.view.MotionEvent
import android.view.ViewGroup
import android.content.Context
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.face.FaceDetection
import com.google.mlkit.vision.face.FaceDetectorOptions
import java.io.File
import java.net.URL
import java.nio.FloatBuffer
import kotlin.concurrent.thread
import kotlin.math.*

class MainActivity : AppCompatActivity() {
    private var imageUri: Uri? = null
    private var audioUri: Uri? = null
    private lateinit var status: TextView
    private lateinit var preview: ImageView
    private lateinit var progress: ProgressBar
    private lateinit var mouthOffsetXLabel: TextView
    private lateinit var mouthOffsetYLabel: TextView
    private lateinit var mouthAngleLabel: TextView
    private lateinit var mouthScaleLabel: TextView
    private var mouthOffsetXPercent: Int = 15
    private var mouthOffsetYPercent: Int = -6
    private var mouthAngleDeg: Int = 3
    private var mouthScalePercent: Int = 89
    private var engineMode: String = "edtalk256"
    // Coordinates of manually selected lips, normalized to the full source image.
    private var lipX = 0.50f
    private var lipY = 0.72f
    private var lipRx = 0.105f
    private var lipRy = 0.045f
    private var lipRotation = 0f

    private fun saveLips() {
        getSharedPreferences("dorama_avatar_lips", MODE_PRIVATE).edit()
            .putFloat("cx", lipX).putFloat("cy", lipY)
            .putFloat("rx", lipRx).putFloat("ry", lipRy)
            .putFloat("rotation", lipRotation).apply()
    }

    // V1.3.5: fullscreen editor. Image navigation and ellipse editing are independent.
    private inner class FullscreenLipsEditor(context: Context, private val photo: Bitmap) : View(context) {
        private val imagePaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
        private val outline = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.MAGENTA; style = Paint.Style.STROKE; strokeWidth = 3f * resources.displayMetrics.density
        }
        private val overlayFill = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = 0x44FF00FF }
        private val handlePaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.YELLOW }
        // V1.3.6: alignment preview (original pixels, NOT AI generated lips).
        var showAlignmentPreview = false
        var previewShiftX = 0
        var previewShiftY = 0
        var previewAngle = 0
        var previewScale = 100
        private val previewPaint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
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
        val calibrationPrefs=getSharedPreferences("dorama_avatar_calibration",MODE_PRIVATE)
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
        }
        val dialog=android.app.Dialog(this,android.R.style.Theme_Black_NoTitleBar_Fullscreen)
        // V1.3.5.1: fullscreen image, controls anchored independently at bottom.
        val root=FrameLayout(this).apply { setBackgroundColor(Color.BLACK) }
        val editor=FullscreenLipsEditor(this,photo)
        root.addView(editor,FrameLayout.LayoutParams(-1,-1))
        val controls=LinearLayout(this).apply {
            orientation=LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(24,24,24))
            val d=resources.displayMetrics.density
            setPadding((8*d).toInt(),(6*d).toInt(),(8*d).toInt(),(6*d).toInt())
        }
        val info=TextView(this).apply {
            text="Перемещай фото вне эллипса • 2 пальца — масштаб • жёлтые точки — ширина и высота"
            setTextColor(Color.WHITE);textSize=12f;setPadding(12,8,12,8)
        }
        controls.addView(info)
        val rotationText=TextView(this).apply {setTextColor(Color.WHITE);text="Наклон эллипса: ${lipRotation.toInt()}°";setPadding(12,4,12,4)}
        controls.addView(rotationText)
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
        controls.addView(angle)
        val buttons=LinearLayout(this).apply {orientation=LinearLayout.HORIZONTAL}
        val reset=Button(this).apply {text="Сброс";setOnClickListener {
            lipX=.5f;lipY=.72f;lipRx=.105f;lipRy=.045f;lipRotation=0f
            angle.progress=90;editor.invalidate()
        }}
        val cancel=Button(this).apply {text="Отмена";setOnClickListener {
            lipX=old[0];lipY=old[1];lipRx=old[2];lipRy=old[3];lipRotation=old[4]
            restoreCalibration();dialog.dismiss()
        }}
        val save=Button(this).apply {text="Сохранить";setOnClickListener {
            saveLips()
            calibrationPrefs.edit().putInt("mouth_x",mouthOffsetXPercent)
                .putInt("mouth_y",mouthOffsetYPercent)
                .putInt("mouth_angle",mouthAngleDeg)
                .putInt("mouth_scale",mouthScalePercent).apply()
            refreshMainCalibration()
            dialog.dismiss()
        }}
        for(button in arrayOf(reset,cancel,save)) buttons.addView(button,LinearLayout.LayoutParams(0,-2,1f))
        // V1.3.6: adjustment controls inside the editor, live approximate preview.
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
        // Keep controls above gesture/navigation bar on Android 10+.
        // Insets applied to bottom panel after it is created.
        /* controls.setOnApplyWindowInsetsListener { view, insets ->
            val d=resources.displayMetrics.density
            val bottom=if (Build.VERSION.SDK_INT >= 30) {
                insets.getInsets(android.view.WindowInsets.Type.navigationBars()).bottom
            } else {
                @Suppress("DEPRECATION")
                insets.systemWindowInsetBottom
            }
            view.setPadding((8*d).toInt(),(6*d).toInt(),(8*d).toInt(),(6*d).toInt()+bottom)
            insets
        } */
        val scroller=ScrollView(this).apply {
            isFillViewport=false
            addView(controls)
        }
        val maxPanel=(resources.displayMetrics.heightPixels*0.55f).toInt()
        val bottomPanel=LinearLayout(this).apply {
            orientation=LinearLayout.VERTICAL
            setBackgroundColor(Color.rgb(24,24,24))
        }
        bottomPanel.addView(scroller,LinearLayout.LayoutParams(-1,maxPanel-(58*resources.displayMetrics.density).toInt()))
        bottomPanel.addView(buttons,LinearLayout.LayoutParams(-1,-2))
        bottomPanel.setOnApplyWindowInsetsListener { view, insets ->
            val bottom=if(Build.VERSION.SDK_INT>=30)
                insets.getInsets(android.view.WindowInsets.Type.navigationBars()).bottom
            else insets.systemWindowInsetBottom
            view.setPadding(0,0,0,bottom)
            insets
        }
        root.addView(bottomPanel,FrameLayout.LayoutParams(-1,-2,android.view.Gravity.BOTTOM))
        dialog.setContentView(root)
        dialog.setOnCancelListener {
            lipX=old[0];lipY=old[1];lipRx=old[2];lipRy=old[3];lipRotation=old[4]
            restoreCalibration()
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

    private val imagePicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { u ->
        u?.let {
            imageUri = it
            preview.setImageURI(it)

            status.text = "✓ Картинка: ${name(it)}"
        }
    }
    private val audioPicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { u ->
        u?.let {
            audioUri = it
            status.text = "✓ WAV: ${name(it)}"
        }
    }

    override fun onCreate(b: Bundle?) {
        super.onCreate(b)
        setContentView(R.layout.activity_main)
        status = findViewById(R.id.status)
        preview = findViewById(R.id.preview)
        val lipPrefs = getSharedPreferences("dorama_avatar_lips", MODE_PRIVATE)
        lipX = lipPrefs.getFloat("cx", 0.50f)
        lipY = lipPrefs.getFloat("cy", 0.72f)
        lipRx = lipPrefs.getFloat("rx", 0.105f)
        lipRy = lipPrefs.getFloat("ry", 0.045f)
        lipRotation = lipPrefs.getFloat("rotation", 0f)
        installLipSelector()
        progress = findViewById(R.id.progress)
        mouthOffsetXLabel = findViewById(R.id.mouthOffsetXLabel)
        mouthOffsetYLabel = findViewById(R.id.mouthOffsetYLabel)
        mouthAngleLabel = findViewById(R.id.mouthAngleLabel)
        mouthScaleLabel = findViewById(R.id.mouthScaleLabel)

        val prefs = getSharedPreferences("dorama_avatar_calibration", MODE_PRIVATE)
        mouthOffsetXPercent = prefs.getInt("mouth_x", 15)
        mouthOffsetYPercent = prefs.getInt("mouth_y", -6)
        mouthAngleDeg = prefs.getInt("mouth_angle", 3)
        mouthScalePercent = prefs.getInt("mouth_scale", 89)
        // V1.3.5: old X/Y values had different meaning (they moved the mask).
        if (!prefs.getBoolean("v133_calibration_reset", false)) {
            mouthOffsetXPercent = 0
            mouthOffsetYPercent = 0
            mouthAngleDeg = 0
            mouthScalePercent = 100
            prefs.edit().putInt("mouth_x", 0).putInt("mouth_y", 0)
                .putInt("mouth_angle", 0).putInt("mouth_scale", 100)
                .putBoolean("v133_calibration_reset", true).apply()
        }

        engineMode = prefs.getString("lip_engine", "edtalk256") ?: "edtalk256"
        val engineGroup = findViewById<RadioGroup>(R.id.engineGroup)
        findViewById<RadioButton>(
            if (engineMode == "wav2lip96") R.id.engine96 else R.id.engine256
        ).isChecked = true

        engineGroup.setOnCheckedChangeListener { _, checkedId ->
            engineMode = if (checkedId == R.id.engine96) "wav2lip96" else "edtalk256"
            prefs.edit().putString("lip_engine", engineMode).apply()
            status.text = if (engineMode == "edtalk256") {
                "✓ Выбран EDTalk 256×256 — качество"
            } else {
                "✓ Выбран Wav2Lip GAN 96×96 — быстрый резерв"
            }
        }

        val mouthOffsetXSeek = findViewById<SeekBar>(R.id.mouthOffsetXSeek)
        val mouthOffsetYSeek = findViewById<SeekBar>(R.id.mouthOffsetYSeek)
        val mouthAngleSeek = findViewById<SeekBar>(R.id.mouthAngleSeek)
        val mouthScaleSeek = findViewById<SeekBar>(R.id.mouthScaleSeek)

        mouthOffsetXSeek.progress = (mouthOffsetXPercent + 20).coerceIn(0, 40)
        mouthOffsetYSeek.progress = (mouthOffsetYPercent + 15).coerceIn(0, 30)
        mouthAngleSeek.progress = (mouthAngleDeg + 12).coerceIn(0, 24)
        mouthScaleSeek.progress = (mouthScalePercent - 85).coerceIn(0, 30)

        fun signed(v: Int): String = if (v > 0) "+$v" else "$v"

        fun refreshCalibrationLabels() {
            val xDir = when {
                mouthOffsetXPercent < 0 -> "влево"
                mouthOffsetXPercent > 0 -> "вправо"
                else -> "центр"
            }
            val yDir = when {
                mouthOffsetYPercent < 0 -> "вверх"
                mouthOffsetYPercent > 0 -> "вниз"
                else -> "центр"
            }
            mouthOffsetXLabel.text = "X: ${signed(mouthOffsetXPercent)}% ($xDir)"
            mouthOffsetYLabel.text = "Y: ${signed(mouthOffsetYPercent)}% ($yDir)"
            mouthAngleLabel.text = "Угол: ${signed(mouthAngleDeg)}°"
            mouthScaleLabel.text = "Размер: ${mouthScalePercent}%"
        }

        fun saveCalibration() {
            prefs.edit()
                .putInt("mouth_x", mouthOffsetXPercent)
                .putInt("mouth_y", mouthOffsetYPercent)
                .putInt("mouth_angle", mouthAngleDeg)
                .putInt("mouth_scale", mouthScalePercent)
                .apply()
        }

        refreshCalibrationLabels()

        mouthOffsetXSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, value: Int, fromUser: Boolean) {
                mouthOffsetXPercent = value - 20
                refreshCalibrationLabels()
                if (fromUser) saveCalibration()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        mouthOffsetYSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, value: Int, fromUser: Boolean) {
                mouthOffsetYPercent = value - 15
                refreshCalibrationLabels()
                if (fromUser) saveCalibration()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        mouthAngleSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, value: Int, fromUser: Boolean) {
                mouthAngleDeg = value - 12
                refreshCalibrationLabels()
                if (fromUser) saveCalibration()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })

        mouthScaleSeek.setOnSeekBarChangeListener(object : SeekBar.OnSeekBarChangeListener {
            override fun onProgressChanged(seekBar: SeekBar?, value: Int, fromUser: Boolean) {
                mouthScalePercent = 85 + value
                refreshCalibrationLabels()
                if (fromUser) saveCalibration()
            }
            override fun onStartTrackingTouch(seekBar: SeekBar?) {}
            override fun onStopTrackingTouch(seekBar: SeekBar?) {}
        })
        findViewById<Button>(R.id.imageButton).setOnClickListener { imagePicker.launch(arrayOf("image/*")) }
        findViewById<Button>(R.id.audioButton).setOnClickListener { audioPicker.launch(arrayOf("audio/*")) }
        findViewById<Button>(R.id.modelButton).setOnClickListener { downloadModel() }
        findViewById<Button>(R.id.generateButton).setOnClickListener { generate() }
    }

    private fun wav2lipModelFile() = File(filesDir, "wav2lip_facefusion_gan96.onnx")
    private fun edtalkModelFile() = File(filesDir, "edtalk_facefusion_256.onnx")

    private fun activeModelFile(): File =
        if (engineMode == "edtalk256") edtalkModelFile() else wav2lipModelFile()

    private fun activeModelLabel(): String =
        if (engineMode == "edtalk256") "EDTalk 256×256" else "Wav2Lip GAN 96×96"

    private fun activeModelUrl(): String =
        if (engineMode == "edtalk256") {
            "https://github.com/facefusion/facefusion-assets/releases/download/models-3.3.0/edtalk_256.onnx"
        } else {
            "https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/wav2lip_gan_96.onnx"
        }

    private fun activeModelMinBytes(): Long =
        if (engineMode == "edtalk256") 250_000_000L else 100_000_000L

    private fun downloadModel() {
        val file = activeModelFile()
        val label = activeModelLabel()

        if (file.exists() && file.length() > activeModelMinBytes()) {
            status.text = "✓ $label уже есть: ${file.length() / 1024 / 1024} МБ"
            return
        }

        thread {
            try {
                runOnUiThread {
                    status.text = "Скачиваю $label…"
                    progress.progress = 0
                }

                val c = URL(activeModelUrl()).openConnection()
                val total = c.contentLengthLong

                c.getInputStream().use { input ->
                    file.outputStream().use { output ->
                        val buf = ByteArray(262144)
                        var n: Int
                        var done = 0L

                        while (input.read(buf).also { n = it } > 0) {
                            output.write(buf, 0, n)
                            done += n
                            if (total > 0) {
                                runOnUiThread {
                                    progress.progress = (done * 100 / total).toInt()
                                }
                            }
                        }
                    }
                }

                if (file.length() <= activeModelMinBytes()) {
                    throw RuntimeException("Файл модели слишком маленький: ${file.length()} байт")
                }

                runOnUiThread {
                    progress.progress = 100
                    status.text = "✓ $label готова (${file.length() / 1024 / 1024} МБ)"
                }
            } catch (e: Throwable) {
                file.delete()
                runOnUiThread {
                    status.text = "Ошибка модели $label: ${e.message}"
                }
            }
        }
    }

    private data class FaceCrop(
        val bitmap: Bitmap,
        val left: Int,
        val top: Int,
        val width: Int,
        val height: Int
    )

    private fun detectFace(b: Bitmap): Rect {
        val d = FaceDetection.getClient(
            FaceDetectorOptions.Builder()
                .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_ACCURATE)
                .build()
        )
        val task = d.process(InputImage.fromBitmap(b, 0))
        while (!task.isComplete) Thread.sleep(20)
        if (!task.isSuccessful) throw task.exception ?: RuntimeException("Face detector")
        val faces = task.result ?: emptyList()
        if (faces.isEmpty()) throw RuntimeException("Лицо не найдено")
        return faces.maxBy { it.boundingBox.width() * it.boundingBox.height() }.boundingBox
    }

    /*
     * V0.7: не берём огромный квадрат 1.5x вокруг лица.
     * Используем сам face box с небольшими полями, как ближе к пайплайну Wav2Lip.
     */
    // V138_FACE_LANDMARK_DIAGNOSTIC: diagnostics only; does not modify inference.
    private fun saveFaceLandmarkDiagnostic(base: Bitmap) {
        val detector = FaceDetection.getClient(
            FaceDetectorOptions.Builder()
                .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_ACCURATE)
                .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_ALL)
                .build()
        )
        try {
            val task = detector.process(InputImage.fromBitmap(base, 0))
            while (!task.isComplete) Thread.sleep(20)
            if (!task.isSuccessful) throw task.exception ?: RuntimeException("Landmark detection failed")
            val face = (task.result ?: emptyList()).maxByOrNull {
                it.boundingBox.width() * it.boundingBox.height()
            } ?: return
            val out = base.copy(Bitmap.Config.ARGB_8888, true)
            val canvas = Canvas(out)
            val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.GREEN
                style = Paint.Style.STROKE
                strokeWidth = 3f
            }
            val label = Paint(Paint.ANTI_ALIAS_FLAG).apply {
                color = Color.YELLOW
                textSize = 22f
                strokeWidth = 2f
            }
            val points = listOf(
                com.google.mlkit.vision.face.FaceLandmark.LEFT_EYE to "L eye",
                com.google.mlkit.vision.face.FaceLandmark.RIGHT_EYE to "R eye",
                com.google.mlkit.vision.face.FaceLandmark.NOSE_BASE to "Nose",
                com.google.mlkit.vision.face.FaceLandmark.MOUTH_LEFT to "L mouth",
                com.google.mlkit.vision.face.FaceLandmark.MOUTH_RIGHT to "R mouth"
            )
            for ((type, name) in points) {
                val pt = face.getLandmark(type)?.position ?: continue
                canvas.drawCircle(pt.x, pt.y, 7f, paint)
                canvas.drawText(name, pt.x + 9f, pt.y - 8f, label)
            }
            val rect = face.boundingBox
            canvas.drawRect(rect, paint)
            val saved = savePng(out, "V138_04_landmarks_original.png")
            out.recycle()
            if (saved == null) throw IllegalStateException("Не удалось сохранить PNG")
            val found = points.count { (type, _) -> face.getLandmark(type) != null }
            runOnUiThread {
                Toast.makeText(this@MainActivity, "EDTalk: найдено точек $found/5; PNG сохранён", Toast.LENGTH_LONG).show()
            }
        } finally {
            detector.close()
        }
    }

    // V139_EDTALK_ALIGNMENT: affine alignment using eyes and mouth landmarks.
    // Forward matrix maps full-image coordinates to 256x256 model coordinates.
    private data class EdtalkAligned(val bitmap: Bitmap, val forward: Matrix)

    private fun alignEdtalkFace(base: Bitmap): EdtalkAligned {
        val detector = FaceDetection.getClient(
            FaceDetectorOptions.Builder()
                .setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_ACCURATE)
                .setLandmarkMode(FaceDetectorOptions.LANDMARK_MODE_ALL)
                .build()
        )
        try {
            val task = detector.process(InputImage.fromBitmap(base, 0))
            while (!task.isComplete) Thread.sleep(20)
            if (!task.isSuccessful) throw task.exception ?: RuntimeException("EDTalk landmark detection failed")
            val face = (task.result ?: emptyList()).maxByOrNull {
                it.boundingBox.width() * it.boundingBox.height()
            } ?: throw RuntimeException("EDTalk: face not found")
            fun landmark(type: Int): PointF = face.getLandmark(type)?.position
                ?: throw RuntimeException("EDTalk: missing landmark $type")
            val left = landmark(com.google.mlkit.vision.face.FaceLandmark.LEFT_EYE)
            val right = landmark(com.google.mlkit.vision.face.FaceLandmark.RIGHT_EYE)
            val ml = landmark(com.google.mlkit.vision.face.FaceLandmark.MOUTH_LEFT)
            val mr = landmark(com.google.mlkit.vision.face.FaceLandmark.MOUTH_RIGHT)
            val mouthX = (ml.x + mr.x) / 2f
            val mouthY = (ml.y + mr.y) / 2f
            val source = floatArrayOf(left.x, left.y, right.x, right.y, mouthX, mouthY)
            val destination = floatArrayOf(82f, 96f, 174f, 96f, 128f, 174f)
            val forward = Matrix()
            check(forward.setPolyToPoly(source, 0, destination, 0, 3)) {
                "EDTalk: unable to align landmarks"
            }
            val aligned = Bitmap.createBitmap(256, 256, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(aligned)
            canvas.drawColor(Color.BLACK)
            canvas.drawBitmap(base, forward, Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG))
            return EdtalkAligned(aligned, forward)
        } finally {
            detector.close()
        }
    }

    // Map the generated aligned face back into the ORIGINAL face crop.
    // This preserves the existing manual ellipse and X/Y/rotation/scale compositor.
    private fun unalignEdtalkFace(generated: Bitmap, alignment: EdtalkAligned, crop: FaceCrop): Bitmap {
        val inverse = Matrix()
        check(alignment.forward.invert(inverse)) { "EDTalk: alignment matrix not invertible" }
        inverse.postTranslate(-crop.left.toFloat(), -crop.top.toFloat())
        val out = Bitmap.createBitmap(crop.width, crop.height, Bitmap.Config.ARGB_8888)
        Canvas(out).drawBitmap(generated, inverse, Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG))
        return out
    }

    private fun cropInfo(b: Bitmap, r: Rect): FaceCrop {
        // Ближе к оригинальному Wav2Lip: face box + только нижний pad 10 px.
        val left = r.left.coerceIn(0, b.width - 2)
        val right = r.right.coerceIn(left + 2, b.width)
        val top = r.top.coerceIn(0, b.height - 2)
        val bottom = (r.bottom + 10).coerceIn(top + 2, b.height)
        val w = (right - left).coerceAtLeast(2)
        val h = (bottom - top).coerceAtLeast(2)
        val raw = Bitmap.createBitmap(b, left, top, w, h)
        return FaceCrop(raw, left, top, w, h)
    }

    /*
     * Критическая ошибка V0.3 была здесь:
     * Wav2Lip ожидает, что у masked-копии занулена НИЖНЯЯ половина лица.
     * В V0.3 была занулена верхняя половина, поэтому верх кадра превращался в мусор.
     */
    /*
     * Оригинальный Wav2Lip получает изображения через OpenCV (BGR),
     * затем NHWC -> NCHW. Поэтому в Android явно подаём B,G,R.
     */
    private fun imageTensor96(source: Bitmap): FloatArray {
        val b = Bitmap.createScaledBitmap(source, 96, 96, true)
        val pix = IntArray(96 * 96)
        b.getPixels(pix, 0, 96, 0, 0, 96, 96)
        val out = FloatArray(6 * 96 * 96)

        for (y in 0 until 96) {
            for (x in 0 until 96) {
                val p = pix[y * 96 + x]
                val bgr = floatArrayOf(
                    Color.blue(p) / 255f,
                    Color.green(p) / 255f,
                    Color.red(p) / 255f
                )
                for (c in 0..2) {
                    val value = bgr[c]
                    out[c * 96 * 96 + y * 96 + x] = if (y >= 48) 0f else value
                    out[(c + 3) * 96 * 96 + y * 96 + x] = value
                }
            }
        }

        b.recycle()
        return out
    }

    private fun imageTensor256(source: Bitmap): FloatArray {
        val b = Bitmap.createScaledBitmap(source, 256, 256, true)
        val pix = IntArray(256 * 256)
        b.getPixels(pix, 0, 256, 0, 0, 256, 256)
        val out = FloatArray(3 * 256 * 256)

        for (y in 0 until 256) {
            for (x in 0 until 256) {
                val p = pix[y * 256 + x]
                out[0 * 256 * 256 + y * 256 + x] = Color.red(p) / 255f
                out[1 * 256 * 256 + y * 256 + x] = Color.green(p) / 255f
                out[2 * 256 * 256 + y * 256 + x] = Color.blue(p) / 255f
            }
        }

        b.recycle()
        return out
    }

    /*
     * V0.7: не предполагаем layout выхода ONNX заранее.
     * Поддерживаем [1,3,96,96] (NCHW) и [1,96,96,3] (NHWC).
     * Каналы модели BGR, Bitmap ожидает RGB.
     */
    private fun outputBitmap(v: Any): Bitmap {
        val batch = v as? Array<*> ?: throw RuntimeException("ONNX output: не Array")
        val first = batch.firstOrNull() as? Array<*> ?: throw RuntimeException("ONNX output: пустой batch")
        val out = Bitmap.createBitmap(96, 96, Bitmap.Config.ARGB_8888)
        val pix = IntArray(96 * 96)

        if (first.size == 3) {
            // NCHW: [1][3][96][96]
            for (y in 0 until 96) for (x in 0 until 96) {
                fun ch(k: Int): Int {
                    val row = (first[k] as Array<*>)[y] as FloatArray
                    return (row[x].coerceIn(0f, 1f) * 255f).roundToInt()
                }
                pix[y * 96 + x] = Color.rgb(ch(2), ch(1), ch(0))
            }
        } else if (first.size == 96) {
            // NHWC: [1][96][96][3]
            for (y in 0 until 96) {
                val row = first[y] as Array<*>
                for (x in 0 until 96) {
                    val bgr = row[x] as FloatArray
                    val b = (bgr[0].coerceIn(0f, 1f) * 255f).roundToInt()
                    val g = (bgr[1].coerceIn(0f, 1f) * 255f).roundToInt()
                    val r = (bgr[2].coerceIn(0f, 1f) * 255f).roundToInt()
                    pix[y * 96 + x] = Color.rgb(r, g, b)
                }
            }
        } else {
            throw RuntimeException("Неизвестный ONNX output layout: first=${first.size}")
        }
        out.setPixels(pix, 0, 96, 0, 0, 96, 96)
        return out
    }

    private fun outputBitmap256(v: Any): Bitmap {
        val batch = v as? Array<*> ?: throw RuntimeException("EDTalk output: не Array")
        val first = batch.firstOrNull() as? Array<*>
            ?: throw RuntimeException("EDTalk output: пустой batch")

        val out = Bitmap.createBitmap(256, 256, Bitmap.Config.ARGB_8888)
        val pix = IntArray(256 * 256)

        if (first.size == 3) {
            for (y in 0 until 256) for (x in 0 until 256) {
                fun ch(k: Int): Int {
                    val row = (first[k] as Array<*>)[y] as FloatArray
                    return (row[x].coerceIn(0f, 1f) * 255f).roundToInt()
                }
                pix[y * 256 + x] = Color.rgb(ch(0), ch(1), ch(2))
            }
        } else if (first.size == 256) {
            for (y in 0 until 256) {
                val row = first[y] as Array<*>
                for (x in 0 until 256) {
                    val rgb = row[x] as FloatArray
                    val r = (rgb[0].coerceIn(0f, 1f) * 255f).roundToInt()
                    val g = (rgb[1].coerceIn(0f, 1f) * 255f).roundToInt()
                    val b = (rgb[2].coerceIn(0f, 1f) * 255f).roundToInt()
                    pix[y * 256 + x] = Color.rgb(r, g, b)
                }
            }
        } else {
            throw RuntimeException("Неизвестный EDTalk output layout: first=${first.size}")
        }

        out.setPixels(pix, 0, 256, 0, 0, 256, 256)
        return out
    }

    private fun smoothStep(edge0: Float, edge1: Float, x: Float): Float {
        if (edge1 <= edge0) return if (x >= edge1) 1f else 0f
        val t = ((x - edge0) / (edge1 - edge0)).coerceIn(0f, 1f)
        return t * t * (3f - 2f * t)
    }

    /*
     * V1.2 QUALITY:
     * лёгкая unsharp-маска после растягивания 96x96 на размер face crop.
     * Усиливаем края губ, но не применяем резкость ко всему исходному кадру.
     */
    private fun sharpenGenerated(src: Bitmap, amount: Float = 0.48f): Bitmap {
        val w = src.width
        val h = src.height
        if (w < 3 || h < 3) return src.copy(Bitmap.Config.ARGB_8888, true)

        val input = IntArray(w * h)
        val output = IntArray(w * h)
        src.getPixels(input, 0, w, 0, 0, w, h)

        // Края оставляем как есть.
        input.copyInto(output)

        fun sharpenChannel(center: Int, blur: Int): Int {
            return (center + amount * (center - blur))
                .roundToInt()
                .coerceIn(0, 255)
        }

        for (y in 1 until h - 1) {
            for (x in 1 until w - 1) {
                val i = y * w + x
                val c = input[i]
                val l = input[i - 1]
                val r = input[i + 1]
                val u = input[i - w]
                val d = input[i + w]

                // Быстрый мягкий blur: центр имеет больший вес.
                val br = (
                    Color.red(c) * 4 +
                    Color.red(l) + Color.red(r) +
                    Color.red(u) + Color.red(d)
                ) / 8
                val bg = (
                    Color.green(c) * 4 +
                    Color.green(l) + Color.green(r) +
                    Color.green(u) + Color.green(d)
                ) / 8
                val bb = (
                    Color.blue(c) * 4 +
                    Color.blue(l) + Color.blue(r) +
                    Color.blue(u) + Color.blue(d)
                ) / 8

                output[i] = Color.argb(
                    Color.alpha(c),
                    sharpenChannel(Color.red(c), br),
                    sharpenChannel(Color.green(c), bg),
                    sharpenChannel(Color.blue(c), bb)
                )
            }
        }

        return Bitmap.createBitmap(output, w, h, Bitmap.Config.ARGB_8888)
    }

    /*
     * V0.7: вставляем только нижнюю часть сгенерированного лица.
     * Глаза/волосы/фон остаются из оригинала. По краям мягкое feather-смешивание.
     */
    private fun compositeMouth(
        base: Bitmap,
        generated96: Bitmap,
        c: FaceCrop,
        offsetXPercent: Int,
        offsetYPercent: Int,
        angleDeg: Int,
        scalePercent: Int
    ): Bitmap {
        val out = base.copy(Bitmap.Config.ARGB_8888, true)
        // V141_DIRECT_INVERSE_RENDER: EDTalk is already inverse-mapped to crop
        // coordinates. Do not rescale or sharpen it a second time.
        val generated = if (generated96.width == c.width && generated96.height == c.height) {
            generated96.copy(Bitmap.Config.ARGB_8888, false)
        } else {
            val scaled = Bitmap.createScaledBitmap(generated96, c.width, c.height, true)
            val sharp = sharpenGenerated(scaled, if (generated96.width <= 96) 0.48f else 0.24f)
            scaled.recycle()
            sharp
        }

        // Manual ellipse center mapped from the full image into the face crop.
        val mouthCx = (base.width * lipX - c.left).coerceIn(0f, c.width.toFloat())
        val mouthCy = (base.height * lipY - c.top).coerceIn(0f, c.height.toFloat())
        val shiftX = c.width * offsetXPercent / 100f
        val shiftY = c.height * offsetYPercent / 100f
        val scale = scalePercent / 100f

        // ВАЖНО: одна Matrix и для изображения, и для маски.
        val transform = Matrix().apply {
            postScale(scale, scale, mouthCx, mouthCy)
            postRotate(angleDeg.toFloat(), mouthCx, mouthCy)
            postTranslate(shiftX, shiftY)
        }

        val transformedFace = Bitmap.createBitmap(
            c.width, c.height, Bitmap.Config.ARGB_8888
        )
        Canvas(transformedFace).drawBitmap(
            generated,
            transform,
            Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
        )

        // Исходная мягкая маска рта.
        val baseMask = Bitmap.createBitmap(
            c.width, c.height, Bitmap.Config.ARGB_8888
        )
        val maskPixels = IntArray(c.width * c.height)

        // V1.3.7: localized detail enhancement and a narrower feather band.
        // No movement of the selected ellipse or alignment settings.
        val maskRadians = Math.toRadians(lipRotation.toDouble())
        val maskCos = cos(maskRadians).toFloat()
        val maskSin = sin(maskRadians).toFloat()
        for (y in 0 until c.height) {
            val fy = y.toFloat() / max(1, c.height - 1)
            for (x in 0 until c.width) {
                val fx = x.toFloat() / max(1, c.width - 1)
                // V1.2: маска уже, чтобы не размягчать щёки/нос/подбородок.
                // Центр тот же, поэтому выставленные X/Y/Angle/Scale не "съезжают".
                // V1.3.2: lips-only mask. Everything outside this compact ellipse is original photo.
                val relX = x - mouthCx
                val relY = y - mouthCy
                val dx = (relX * maskCos + relY * maskSin) / (base.width * lipRx).coerceAtLeast(1f)
                val dy = (-relX * maskSin + relY * maskCos) / (base.height * lipRy).coerceAtLeast(1f)
                val d2 = dx * dx + dy * dy

                // В центре рот остаётся полностью сгенерированным,
                // feather короче и заканчивается раньше.
                val alpha = (
                    (1f - smoothStep(0.62f, 1.00f, d2)) * 255f
                ).roundToInt().coerceIn(0, 255)

                maskPixels[y * c.width + x] =
                    Color.argb(alpha, 255, 255, 255)
            }
        }

        baseMask.setPixels(
            maskPixels, 0, c.width, 0, 0, c.width, c.height
        )

        // V1.3.5 fixed-mouth mask: X/Y/Angle/Scale move ONLY generated pixels.
        // The destination lips region stays fixed on the original photograph.
        val transformedMask = baseMask.copy(Bitmap.Config.ARGB_8888, false)

        val original = IntArray(c.width * c.height)
        val facePixels = IntArray(c.width * c.height)
        val mask = IntArray(c.width * c.height)

        out.getPixels(
            original, 0, c.width,
            c.left, c.top, c.width, c.height
        )
        transformedFace.getPixels(
            facePixels, 0, c.width,
            0, 0, c.width, c.height
        )
        transformedMask.getPixels(
            mask, 0, c.width,
            0, 0, c.width, c.height
        )

        for (i in original.indices) {
            val alpha = Color.alpha(mask[i]) / 255f
            if (alpha <= 0f) continue

            val g = facePixels[i]
            if (Color.alpha(g) == 0) continue

            val a = original[i]

            fun mix(ca: Int, cg: Int): Int =
                (ca * (1f - alpha) + cg * alpha)
                    .roundToInt()
                    .coerceIn(0, 255)

            original[i] = Color.rgb(
                mix(Color.red(a), Color.red(g)),
                mix(Color.green(a), Color.green(g)),
                mix(Color.blue(a), Color.blue(g))
            )
        }

        out.setPixels(
            original, 0, c.width,
            c.left, c.top, c.width, c.height
        )

        transformedMask.recycle()
        baseMask.recycle()
        transformedFace.recycle()
        generated.recycle()

        return out
    }

    private fun generate() {
        if (imageUri == null || audioUri == null) {
            status.text = "Сначала выбери картинку и WAV."
            return
        }

        val model = activeModelFile()
        if (!model.exists() || model.length() <= activeModelMinBytes()) {
            status.text = "Сначала скачай выбранную модель: ${activeModelLabel()}."
            return
        }

        thread {
            try {
                val started = System.currentTimeMillis()
                val engineAtStart = engineMode
                val engineLabel = if (engineAtStart == "edtalk256") {
                    "EDTalk 256×256"
                } else {
                    "Wav2Lip GAN 96×96"
                }

                runOnUiThread {
                    status.text = "Ищу лицо… ($engineLabel)"
                    progress.progress = 1
                }

                val src = contentResolver.openInputStream(imageUri!!)!!.use {
                    BitmapFactory.decodeStream(it)
                }
                val base = scaleEven(src, 720)
                val rect = detectFace(base)
                val crop = cropInfo(base, rect)
                if (engineAtStart == "edtalk256") {
                    // V1381_LANDMARK_RESULT: show diagnostic failure on screen
                    try { saveFaceLandmarkDiagnostic(base) }
                    catch (e: Exception) {
                        android.util.Log.e("DoramaAvatar", "Landmark diagnostic failed", e)
                        val reason = e.message ?: e.javaClass.simpleName
                        runOnUiThread {
                            Toast.makeText(this@MainActivity, "EDTalk диагностика: $reason", Toast.LENGTH_LONG).show()
                        }
                    }
                }


                val wav = contentResolver.openInputStream(audioUri!!)!!.use {
                    WavUtils.readPcm16(it)
                }
                val samples = wav.samples.copyOf(min(wav.samples.size, 16000 * 5))
                val frames = min(125, max(1, (samples.size / 16000f * 25).toInt()))

                val env = OrtEnvironment.getEnvironment()
                val session = env.createSession(model.absolutePath, OrtSession.SessionOptions())
                val names = session.inputNames.toList()

                val rendered = ArrayList<Bitmap>(frames)

                if (engineAtStart == "edtalk256") {
                    val spec = WavUtils.edtalkSpectrogram(samples)
                    val aligned = alignEdtalkFace(base)
                    savePng(aligned.bitmap, "V139_01_aligned_input.png")
                    savePng(aligned.bitmap, "V140_01_aligned_input_256.png")
                    // V142_EDTALK_VALIDATION
                    val targetInput = imageTensor256(aligned.bitmap)
                    check(targetInput.size == 3 * 256 * 256 && targetInput.all { it.isFinite() && it >= 0f && it <= 1f }) {
                        "EDTalk: invalid RGB tensor"
                    }

                    val sourceName = names.firstOrNull {
                        it.equals("source", true) || it.contains("audio", true)
                    } ?: names[0]

                    val targetName = names.firstOrNull {
                        it.equals("target", true) || it.contains("image", true) ||
                            it.contains("frame", true) || it.contains("face", true)
                    } ?: names.getOrElse(1) { names.last() }

                    val weightName = names.firstOrNull {
                        it.equals("weight", true) || it.contains("weight", true)
                    } ?: names.last()

                    for (f in 0 until frames) {
                        val sourceFrame = WavUtils.edtalkFrame(spec, f)
                        check(sourceFrame.size == 80 * 16 && sourceFrame.all { it.isFinite() && it >= -4f && it <= 4f }) {
                            "EDTalk: invalid mel tensor"
                        }
                        if (f == 0) android.util.Log.i(
                            "DoramaAvatar",
                            "V142 EDTalk mel min=${sourceFrame.minOrNull()} max=${sourceFrame.maxOrNull()} mean=${sourceFrame.average()}"
                        )

                        val face = OnnxTensor.createTensor(
                            env,
                            FloatBuffer.wrap(sourceFrame),
                            longArrayOf(1, 1, 80, 16)
                        ).use { sourceTensor ->
                            OnnxTensor.createTensor(
                                env,
                                FloatBuffer.wrap(targetInput),
                                longArrayOf(1, 3, 256, 256)
                            ).use { targetTensor ->
                                OnnxTensor.createTensor(
                                    env,
                                    FloatBuffer.wrap(floatArrayOf(0.5f)),
                                    longArrayOf(1)
                                ).use { weightTensor ->
                                    session.run(
                                        mapOf(
                                            sourceName to sourceTensor,
                                            targetName to targetTensor,
                                            weightName to weightTensor
                                        )
                                    ).use { result ->
                                        outputBitmap256(result[0].value)
                                    }
                                }
                            }
                        }

                        if (f == 0) {
                            val inputPixels = IntArray(256 * 256)
                            val outputPixels = IntArray(256 * 256)
                            aligned.bitmap.getPixels(inputPixels, 0, 256, 0, 0, 256, 256)
                            face.getPixels(outputPixels, 0, 256, 0, 0, 256, 256)
                            var sum = 0.0
                            for (i in inputPixels.indices) {
                                val a = inputPixels[i]
                                val b = outputPixels[i]
                                sum += (kotlin.math.abs(Color.red(a) - Color.red(b)) +
                                    kotlin.math.abs(Color.green(a) - Color.green(b)) +
                                    kotlin.math.abs(Color.blue(a) - Color.blue(b))) / 3.0
                            }
                            android.util.Log.i("DoramaAvatar", "V142 EDTalk mean pixel difference=${sum / inputPixels.size}")
                        }
                        val mappedFace = unalignEdtalkFace(face, aligned, crop)
                        val composed = compositeMouth(
                            base, mappedFace, crop,
                            mouthOffsetXPercent,
                            mouthOffsetYPercent,
                            mouthAngleDeg,
                            mouthScalePercent
                        )

                        if (f == 0) {
                            val stamp = System.currentTimeMillis()
                            savePng(crop.bitmap, "V132_01_input_crop_${stamp}.png")
                            savePng(face, "V132_02_edtalk256_face_${stamp}.png")
                            if (savePng(face, "V140_02_raw_model_output_256_${stamp}.png") == null) {
                                android.util.Log.e("DoramaAvatar", "V140 raw PNG save failed")
                            }
                            savePng(mappedFace, "V139_02_inverse_mapped_${stamp}.png")
                            savePng(mappedFace, "V140_03_inverse_mapped_${stamp}.png")
                            savePng(mappedFace, "V141_01_direct_inverse_no_rescale_${stamp}.png")
                            savePng(composed, "V140_04_composite_before_encoder_${stamp}.png")
                            savePng(composed, "V141_02_composite_no_double_scale_${stamp}.png")
                            savePng(composed, "V132_03_composite_before_encoder_${stamp}.png")
                        }

                        rendered.add(composed)
                        mappedFace.recycle()
                        face.recycle()

                        if (f % 2 == 0) {
                            runOnUiThread {
                                progress.progress = 1 + f * 75 / frames
                                status.text = "EDTalk 256: ${f + 1}/$frames кадров"
                            }
                        }
                    }
                } else {
                    val mel = WavUtils.melSpectrogram(samples)
                    val imageInput = imageTensor96(crop.bitmap)

                    val melName = names.firstOrNull {
                        it.contains("mel", true) || it.contains("audio", true) ||
                            it.contains("source", true)
                    } ?: names[0]

                    val imgName = names.firstOrNull {
                        it.contains("video", true) || it.contains("frame", true) ||
                            it.contains("img", true) || it.contains("face", true) ||
                            it.contains("target", true)
                    } ?: names.last()

                    for (f in 0 until frames) {
                        val mi = (f * 80.0 / 25.0).toInt()
                            .coerceAtMost(max(0, mel[0].size - 16))
                        val mf = FloatArray(80 * 16)

                        for (y in 0 until 80) for (x in 0 until 16) {
                            mf[y * 16 + x] =
                                mel[y][(mi + x).coerceAtMost(mel[y].lastIndex)]
                        }

                        val face = OnnxTensor.createTensor(
                            env,
                            FloatBuffer.wrap(mf),
                            longArrayOf(1, 1, 80, 16)
                        ).use { mt ->
                            OnnxTensor.createTensor(
                                env,
                                FloatBuffer.wrap(imageInput),
                                longArrayOf(1, 6, 96, 96)
                            ).use { img ->
                                session.run(mapOf(melName to mt, imgName to img)).use { r ->
                                    outputBitmap(r[0].value)
                                }
                            }
                        }

                        val composed = compositeMouth(
                            base, face, crop,
                            mouthOffsetXPercent,
                            mouthOffsetYPercent,
                            mouthAngleDeg,
                            mouthScalePercent
                        )

                        if (f == 0) {
                            val stamp = System.currentTimeMillis()
                            savePng(crop.bitmap, "V132_01_input_crop_${stamp}.png")
                            savePng(face, "V132_02_wav2lip96_face_${stamp}.png")
                            savePng(composed, "V132_03_composite_before_encoder_${stamp}.png")
                        }

                        rendered.add(composed)
                        face.recycle()

                        if (f % 3 == 0) {
                            runOnUiThread {
                                progress.progress = 1 + f * 75 / frames
                                status.text = "Wav2Lip 96: ${f + 1}/$frames кадров"
                            }
                        }
                    }
                }

                session.close()

                val tmp = File(cacheDir, "v135_${System.currentTimeMillis()}.mp4")
                val encoderInfo = encodeMp4(rendered, samples, tmp)
                rendered.forEach { it.recycle() }
                saveMovie(tmp)

                val sec = (System.currentTimeMillis() - started) / 1000.0

                runOnUiThread {
                    progress.progress = 100
                    status.text =
                        "✓ V1.3.5.1 ГОТОВА\n" +
                        "✓ Движок: $engineLabel\n" +
                        "✓ PNG: Pictures/DoramaAvatar\n" +
                        "✓ MP4: ${encoderInfo.width}x${encoderInfo.height}\n" +
                        "✓ $frames кадров / H.264 + AAC\n" +
                        "⏱ ${"%.1f".format(sec)} сек\n" +
                        "📁 Movies/DoramaAvatar\n\n" +
                        "X: ${mouthOffsetXPercent}% • Y: ${mouthOffsetYPercent}% • " +
                        "Angle: ${mouthAngleDeg}° • Scale: ${mouthScalePercent}%"

                    Toast.makeText(
                        this,
                        "V1.3.5.1: $engineLabel — MP4 готов",
                        Toast.LENGTH_LONG
                    ).show()
                }

                crop.bitmap.recycle()
            } catch (e: Throwable) {
                runOnUiThread {
                    status.text =
                        "Ошибка V1.3.5 ${activeModelLabel()}: " +
                        "${e.javaClass.simpleName}: ${e.message}"
                }
            }
        }
    }

    private fun scaleEven(b: Bitmap, maxSide: Int): Bitmap {
        val k = min(1f, maxSide.toFloat() / max(b.width, b.height))
        var w = (b.width * k).toInt().coerceAtLeast(2)
        var h = (b.height * k).toInt().coerceAtLeast(2)
        w -= w % 2; h -= h % 2
        return Bitmap.createScaledBitmap(b, w, h, true)
    }

    private data class Sample(val data: ByteArray, val info: MediaCodec.BufferInfo)
    private data class EncoderInfo(val codec: String, val colorFormat: Int, val width: Int, val height: Int)

    private fun align16(v: Int): Int = ((v + 15) / 16) * 16

    private fun padToSize(src: Bitmap, w: Int, h: Int): Bitmap {
        if (src.width == w && src.height == h) return src
        val out = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val c = Canvas(out)
        c.drawColor(Color.BLACK)
        c.drawBitmap(src, 0f, 0f, Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG))
        return out
    }

    private fun chooseAvcEncoder(): Pair<MediaCodecInfo, Int> {
        val infos = MediaCodecList(MediaCodecList.REGULAR_CODECS).codecInfos
        val codec = infos.firstOrNull { info ->
            info.isEncoder && info.supportedTypes.any { it.equals(MediaFormat.MIMETYPE_VIDEO_AVC, true) }
        } ?: throw RuntimeException("AVC encoder не найден")
        val colors = codec.getCapabilitiesForType(MediaFormat.MIMETYPE_VIDEO_AVC).colorFormats.toSet()
        val chosen = when {
            colors.contains(MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar) -> MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar
            colors.contains(MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Planar) -> MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Planar
            colors.contains(MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible) -> MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420Flexible
            else -> throw RuntimeException("Нет поддерживаемого ByteBuffer YUV420. Форматы: ${colors.joinToString()}")
        }
        return codec to chosen
    }

    private fun encodeMp4(frames: List<Bitmap>, audio: FloatArray, out: File): EncoderInfo {
        val width = align16(frames[0].width)
        val height = align16(frames[0].height)
        val (codecInfo, colorFormat) = chooseAvcEncoder()

        val vf = MediaFormat.createVideoFormat(MediaFormat.MIMETYPE_VIDEO_AVC, width, height)
        vf.setInteger(MediaFormat.KEY_COLOR_FORMAT, colorFormat)
        vf.setInteger(MediaFormat.KEY_BIT_RATE, 2_500_000)
        vf.setInteger(MediaFormat.KEY_FRAME_RATE, 25)
        vf.setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
        val v = MediaCodec.createByCodecName(codecInfo.name)
        v.configure(vf, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        v.start()

        val af = MediaFormat.createAudioFormat(MediaFormat.MIMETYPE_AUDIO_AAC, 16000, 1)
        af.setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
        af.setInteger(MediaFormat.KEY_BIT_RATE, 64000)
        val a = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
        a.configure(af, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        a.start()

        val mux = MediaMuxer(out.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        var vt = -1; var at = -1; var muxStarted = false
        val pendingV = ArrayList<Sample>(); val pendingA = ArrayList<Sample>()

        fun drain(codec: MediaCodec, isVideo: Boolean, eos: Boolean) {
            val info = MediaCodec.BufferInfo()
            var idle = 0
            while (true) {
                val ix = codec.dequeueOutputBuffer(info, if (eos) 10000 else 0)
                if (ix == MediaCodec.INFO_TRY_AGAIN_LATER) {
                    if (!eos) break
                    if (++idle > 300) throw RuntimeException("Encoder EOS timeout")
                    continue
                }
                idle = 0
                if (ix == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    if (isVideo) vt = mux.addTrack(codec.outputFormat) else at = mux.addTrack(codec.outputFormat)
                    if (vt >= 0 && at >= 0 && !muxStarted) {
                        mux.start(); muxStarted = true
                        for (s in pendingV) mux.writeSampleData(vt, java.nio.ByteBuffer.wrap(s.data), s.info)
                        for (s in pendingA) mux.writeSampleData(at, java.nio.ByteBuffer.wrap(s.data), s.info)
                        pendingV.clear(); pendingA.clear()
                    }
                    continue
                }
                if (ix >= 0) {
                    val ob = codec.getOutputBuffer(ix)!!
                    if (info.size > 0 && (info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG) == 0) {
                        ob.position(info.offset); ob.limit(info.offset + info.size)
                        val bytes = ByteArray(info.size); ob.get(bytes)
                        val cp = MediaCodec.BufferInfo(); cp.set(0, bytes.size, info.presentationTimeUs, info.flags)
                        if (muxStarted) mux.writeSampleData(if (isVideo) vt else at, java.nio.ByteBuffer.wrap(bytes), cp)
                        else (if (isVideo) pendingV else pendingA).add(Sample(bytes, cp))
                    }
                    val end = (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0
                    codec.releaseOutputBuffer(ix, false)
                    if (end) break
                }
            }
        }

        for ((i, src) in frames.withIndex()) {
            val frame = padToSize(src, width, height)
            val yuv = when (colorFormat) {
                MediaCodecInfo.CodecCapabilities.COLOR_FormatYUV420SemiPlanar -> toNv12(frame)
                else -> toI420(frame)
            }
            if (frame !== src) frame.recycle()
            var ix = v.dequeueInputBuffer(10000)
            while (ix < 0) { drain(v, true, false); ix = v.dequeueInputBuffer(10000) }
            val buf = v.getInputBuffer(ix)!!
            if (buf.capacity() < yuv.size) throw RuntimeException("Video input buffer ${buf.capacity()} < ${yuv.size}")
            buf.clear(); buf.put(yuv)
            v.queueInputBuffer(ix, 0, yuv.size, i * 40000L, 0)
            drain(v, true, false)
        }
        var vix = v.dequeueInputBuffer(10000)
        while (vix < 0) { drain(v, true, false); vix = v.dequeueInputBuffer(10000) }
        v.queueInputBuffer(vix, 0, 0, frames.size * 40000L, MediaCodec.BUFFER_FLAG_END_OF_STREAM)

        var pos = 0; val chunk = 1024
        while (pos < audio.size) {
            var ai = a.dequeueInputBuffer(10000)
            while (ai < 0) { drain(a, false, false); ai = a.dequeueInputBuffer(10000) }
            val n = min(chunk, audio.size - pos); val bb = a.getInputBuffer(ai)!!; bb.clear()
            for (j in 0 until n) {
                val smp = (audio[pos + j].coerceIn(-1f, 1f) * 32767).toInt().toShort()
                bb.put((smp.toInt() and 255).toByte()); bb.put(((smp.toInt() shr 8) and 255).toByte())
            }
            a.queueInputBuffer(ai, 0, n * 2, pos * 1_000_000L / 16000, 0)
            pos += n; drain(a, false, false)
        }
        var aix = a.dequeueInputBuffer(10000)
        while (aix < 0) { drain(a, false, false); aix = a.dequeueInputBuffer(10000) }
        a.queueInputBuffer(aix, 0, 0, pos * 1_000_000L / 16000, MediaCodec.BUFFER_FLAG_END_OF_STREAM)

        drain(v, true, true); drain(a, false, true)
        v.stop(); a.stop(); v.release(); a.release()
        if (muxStarted) mux.stop()
        mux.release()
        return EncoderInfo(codecInfo.name, colorFormat, width, height)
    }

    private fun rgbToYuv(c: Int): IntArray {
        val r = Color.red(c); val g = Color.green(c); val b = Color.blue(c)
        val y = (((66 * r + 129 * g + 25 * b + 128) shr 8) + 16).coerceIn(0, 255)
        val u = (((-38 * r - 74 * g + 112 * b + 128) shr 8) + 128).coerceIn(0, 255)
        val v = (((112 * r - 94 * g - 18 * b + 128) shr 8) + 128).coerceIn(0, 255)
        return intArrayOf(y, u, v)
    }

    private fun toI420(b: Bitmap): ByteArray {
        val w = b.width; val h = b.height
        val p = IntArray(w * h); b.getPixels(p, 0, w, 0, 0, w, h)
        val out = ByteArray(w * h * 3 / 2)
        var yi = 0; var ui = w * h; var vi = ui + w * h / 4
        for (y in 0 until h) for (x in 0 until w) {
            val yy = rgbToYuv(p[y * w + x]); out[yi++] = yy[0].toByte()
            if (y % 2 == 0 && x % 2 == 0) { out[ui++] = yy[1].toByte(); out[vi++] = yy[2].toByte() }
        }
        return out
    }

    private fun toNv12(b: Bitmap): ByteArray {
        val w = b.width; val h = b.height
        val p = IntArray(w * h); b.getPixels(p, 0, w, 0, 0, w, h)
        val out = ByteArray(w * h * 3 / 2)
        var yi = 0; var uvi = w * h
        for (y in 0 until h) for (x in 0 until w) {
            val yy = rgbToYuv(p[y * w + x]); out[yi++] = yy[0].toByte()
            if (y % 2 == 0 && x % 2 == 0) { out[uvi++] = yy[1].toByte(); out[uvi++] = yy[2].toByte() }
        }
        return out
    }

    private fun savePng(bitmap: Bitmap, fileName: String): Uri? {
        return try {
            val values = ContentValues().apply {
                put(MediaStore.Images.Media.DISPLAY_NAME, fileName)
                put(MediaStore.Images.Media.MIME_TYPE, "image/png")
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    put(MediaStore.Images.Media.RELATIVE_PATH, "Pictures/DoramaAvatar")
                }
            }
            val uri = contentResolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values) ?: return null
            contentResolver.openOutputStream(uri)!!.use { bitmap.compress(Bitmap.CompressFormat.PNG, 100, it) }
            uri
        } catch (_: Throwable) { null }
    }

    private fun saveMovie(f: File): Uri {
        val cv = ContentValues().apply {
            put(MediaStore.Video.Media.DISPLAY_NAME, "DoramaAvatar_V135_${System.currentTimeMillis()}.mp4")
            put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
            put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/DoramaAvatar")
        }
        val u = contentResolver.insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, cv)
            ?: throw RuntimeException("Не удалось создать MP4")
        contentResolver.openOutputStream(u)!!.use { o -> f.inputStream().use { it.copyTo(o) } }
        f.delete(); return u
    }

    private fun name(u: Uri): String {
        contentResolver.query(u, null, null, null, null)?.use { c ->
            val i = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (c.moveToFirst() && i >= 0) return c.getString(i)
        }
        return u.lastPathSegment ?: "file"
    }
}
