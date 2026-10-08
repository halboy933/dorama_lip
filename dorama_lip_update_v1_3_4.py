from pathlib import Path
import re
p=Path('app/src/main/java/com/dorama/avatar/MainActivity.kt')
s=p.read_text(encoding='utf-8')
def replace_once(a,b):
 global s
 if s.count(a)!=1: raise RuntimeError(f'Expected one anchor, got {s.count(a)}: {a[:90]}')
 s=s.replace(a,b,1)
replace_once('import android.widget.*','import android.widget.*\nimport android.view.View\nimport android.view.MotionEvent\nimport android.view.ViewGroup\nimport android.content.Context')
replace_once('    private var engineMode: String = "edtalk256"','''    private var engineMode: String = "edtalk256"
    // Coordinates of manually selected lips, normalized to the full source image.
    private var lipX = 0.50f
    private var lipY = 0.72f
    private var lipRx = 0.105f
    private var lipRy = 0.045f
    private var lipSelection: MouthSelectionView? = null

    private fun saveLips() {
        getSharedPreferences("dorama_avatar_lips", MODE_PRIVATE).edit()
            .putFloat("cx", lipX).putFloat("cy", lipY)
            .putFloat("rx", lipRx).putFloat("ry", lipRy).apply()
    }

    private inner class MouthSelectionView(context: Context) : View(context) {
        private val line = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = Color.MAGENTA; style = Paint.Style.STROKE; strokeWidth = 4f
        }
        private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = 0x33FF00FF }
        private val handle = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.YELLOW }
        private var resizing = false
        private var lastX = 0f
        private var lastY = 0f

        private fun imagePoint(nx: Float, ny: Float): PointF {
            val d = preview.drawable ?: return PointF(width * nx, height * ny)
            val pt = floatArrayOf(nx * d.intrinsicWidth, ny * d.intrinsicHeight)
            preview.imageMatrix.mapPoints(pt)
            return PointF(pt[0] + preview.left - left, pt[1] + preview.top - top)
        }
        private fun normalizedPoint(x: Float, y: Float): PointF {
            val d = preview.drawable ?: return PointF(0.5f, 0.5f)
            val inv = Matrix()
            if (!preview.imageMatrix.invert(inv)) return PointF(0.5f, 0.5f)
            val pt = floatArrayOf(x - preview.left + left, y - preview.top + top)
            inv.mapPoints(pt)
            return PointF((pt[0] / d.intrinsicWidth).coerceIn(0f, 1f),
                (pt[1] / d.intrinsicHeight).coerceIn(0f, 1f))
        }
        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            if (preview.drawable == null) return
            val center = imagePoint(lipX, lipY)
            val a = imagePoint((lipX - lipRx).coerceAtLeast(0f), (lipY - lipRy).coerceAtLeast(0f))
            val b = imagePoint((lipX + lipRx).coerceAtMost(1f), (lipY + lipRy).coerceAtMost(1f))
            val oval = RectF(a.x, a.y, b.x, b.y)
            canvas.drawOval(oval, fill); canvas.drawOval(oval, line)
            canvas.drawCircle(center.x, center.y, 9f, handle)
            canvas.drawCircle(b.x, b.y, 13f, handle)
        }
        override fun onTouchEvent(event: MotionEvent): Boolean {
            if (preview.drawable == null) return false
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    val edge = imagePoint((lipX + lipRx).coerceAtMost(1f), (lipY + lipRy).coerceAtMost(1f))
                    resizing = hypot(event.x - edge.x, event.y - edge.y) < 75f
                    val pt = normalizedPoint(event.x, event.y)
                    if (!resizing) { lipX = pt.x; lipY = pt.y }
                    lastX = event.x; lastY = event.y
                    invalidate(); return true
                }
                MotionEvent.ACTION_MOVE -> {
                    val pt = normalizedPoint(event.x, event.y)
                    if (resizing) {
                        lipRx = abs(pt.x - lipX).coerceIn(0.015f, 0.35f)
                        lipRy = abs(pt.y - lipY).coerceIn(0.010f, 0.22f)
                    } else {
                        val prev = normalizedPoint(lastX, lastY)
                        lipX = (lipX + pt.x - prev.x).coerceIn(0f, 1f)
                        lipY = (lipY + pt.y - prev.y).coerceIn(0f, 1f)
                    }
                    lastX = event.x; lastY = event.y
                    invalidate(); return true
                }
                MotionEvent.ACTION_UP -> { saveLips(); invalidate(); performClick(); return true }
                MotionEvent.ACTION_CANCEL -> { saveLips(); return true }
            }
            return true
        }
        override fun performClick(): Boolean { super.performClick(); return true }
    }

    private fun installLipSelector() {
        val parent = preview.parent as ViewGroup
        val index = parent.indexOfChild(preview)
        val oldParams = preview.layoutParams
        parent.removeView(preview)
        val frame = FrameLayout(this)
        parent.addView(frame, index, oldParams)
        frame.addView(preview, FrameLayout.LayoutParams(-1, -1))
        lipSelection = MouthSelectionView(this).also {
            frame.addView(it, FrameLayout.LayoutParams(-1, -1))
        }
    }''')
replace_once('            preview.setImageURI(it)','            preview.setImageURI(it)\n            lipSelection?.invalidate()')
replace_once('        preview = findViewById(R.id.preview)','''        preview = findViewById(R.id.preview)
        val lipPrefs = getSharedPreferences("dorama_avatar_lips", MODE_PRIVATE)
        lipX = lipPrefs.getFloat("cx", 0.50f)
        lipY = lipPrefs.getFloat("cy", 0.72f)
        lipRx = lipPrefs.getFloat("rx", 0.105f)
        lipRy = lipPrefs.getFloat("ry", 0.045f)
        installLipSelector()''')
replace_once('''        val mouthCx = c.width * 0.50f
        val mouthCy = c.height * 0.72f''','''        // Manual ellipse center mapped from the full image into the face crop.
        val mouthCx = (base.width * lipX - c.left).coerceIn(0f, c.width.toFloat())
        val mouthCy = (base.height * lipY - c.top).coerceIn(0f, c.height.toFloat())''')
replace_once('''                val dx = (fx - 0.50f) / 0.205f
                val dy = (fy - 0.742f) / 0.090f''','''                val dx = (x - mouthCx) / (base.width * lipRx).coerceAtLeast(1f)
                val dy = (y - mouthCy) / (base.height * lipRy).coerceAtLeast(1f)''')
replace_once('''                // V1.2:''','''                // V1.2:''')
# All output labels / generated file names updated.
s=s.replace('V1.3.3','V1.3.4').replace('V133','V134').replace('v133_${','v134_${')
p.write_text(s,encoding='utf-8')
g=Path('app/build.gradle.kts')
if g.exists():
 t=g.read_text()
 t,n=re.subn(r'versionCode\s*=\s*16\b','versionCode = 17',t)
 if n!=1: raise RuntimeError('Expected versionCode 16 in app/build.gradle.kts')
 t,n=re.subn(r'versionName\s*=\s*"1\.3\.3"','versionName = "1.3.4"',t)
 if n!=1: raise RuntimeError('Expected versionName 1.3.3 in app/build.gradle.kts')
 g.write_text(t)
print('✓ V1.3.4: manual draggable/resizable mouth ellipse applied')
print('✓ Version updated to 17 / 1.3.4; EDTalk, Wav2Lip and signing untouched')
print('✓ Build via GitHub Actions; code has NOT been compiled here')
