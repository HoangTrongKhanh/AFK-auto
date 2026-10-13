package vn.afkauto.leoai

import android.annotation.SuppressLint
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.text.TextUtils
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import android.view.WindowManager
import android.widget.LinearLayout
import android.widget.TextView
import vn.afkauto.leoai.vision.Box
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.roundToInt

private const val HANDLE_COLOR = 0xFF37474F.toInt()
private const val LOG_LINES = 4

/** Bảng nổi gọn 1 hàng (≡ ▶ ■ trạng thái ⋯ ✕) nằm trong dải trống phía trên màn hình game (DAI_AN_TOAN), nơi không
 *  có mẫu nhận diện nào, nên lọt vào ảnh chụp cũng không sao. Mở nhật ký (chạm ≡) hoặc các bài thử (⋯) làm bảng lấn
 *  ra ngoài dải: khi đó dịch vụ ẩn tạm bảng trong lúc chụp. Là cửa sổ Trợ năng nên không cần quyền "hiển thị trên ứng
 *  dụng khác". Giữ màn hình luôn sáng khi đang hiện (FLAG_KEEP_SCREEN_ON). */
class Overlay(private val svc: BotService) {
    private val wm = svc.getSystemService(WindowManager::class.java)
    private val density = svc.resources.displayMetrics.density
    private val params = WindowManager.LayoutParams(
        WindowManager.LayoutParams.WRAP_CONTENT,
        WindowManager.LayoutParams.WRAP_CONTENT,
        WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON or
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
        PixelFormat.TRANSLUCENT,
    ).apply {
        gravity = Gravity.TOP or Gravity.START
        x = svc.prefs.overlayX.takeIf { it >= 0 } ?: defaultX()
        y = svc.prefs.overlayY.takeIf { it >= 0 } ?: defaultY()
    }
    private val root = LinearLayout(svc)
    private val handle = TextView(svc)
    private val statusView = TextView(svc)
    private val logView = TextView(svc)
    private lateinit var moreButton: TextView
    private val probeRow = LinearLayout(svc)
    private val actions = mutableListOf<TextView>()     // các nút bắt đầu tác vụ: tắt khi đang chạy
    private lateinit var stopButton: TextView
    private var logShown = false
    private var probesShown = false
    private val logListener: () -> Unit = {
        logView.text = AppLog.recent(8).joinToString("\n") { it.substringAfter(' ').trim() }   // bỏ giờ cho gọn
        logView.post { scrollLogToEnd() }
    }

    /** Ô nhật ký cao cố định LOG_LINES dòng; dòng dài xuống hàng thì cuộn để luôn thấy dòng mới nhất. */
    private fun scrollLogToEnd() {
        val layout = logView.layout ?: return
        val visible = logView.height - logView.totalPaddingTop - logView.totalPaddingBottom
        val overflow = layout.height - visible
        if (overflow <= 0) return logView.scrollTo(0, 0)
        var first = layout.getLineForVertical(overflow)
        if (layout.getLineTop(first) < overflow) first++
        logView.scrollTo(0, layout.getLineTop(first))
    }

    private val statusListener: () -> Unit = { statusView.text = BotStatus.text }

    private fun dp(v: Int) = (v * density).roundToInt()

    // Vị trí mặc định: góc trên-trái của dải an toàn.
    private fun defaultX() = svc.safeBand().x0 + dp(2)
    private fun defaultY() = svc.safeBand().y0 + dp(2)

    init {
        root.orientation = LinearLayout.VERTICAL
        val row = LinearLayout(svc).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        handle.apply {
            text = "≡"
            textSize = 14f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            background = rounded(HANDLE_COLOR)
            setPadding(dp(9), dp(4), dp(9), dp(4))
            setOnTouchListener(DragToMove())
        }
        row.addView(handle, margins())
        actions += chip("▶ Chạy", 0xFF2E7D32.toInt()) { svc.startBot() }.also { row.addView(it, margins()) }
        stopButton = chip("■", 0xFFC62828.toInt()) { svc.stopJob() }.also { row.addView(it, margins()) }
        statusView.apply {
            textSize = 11f
            typeface = Typeface.DEFAULT_BOLD
            setTextColor(Color.WHITE)
            maxLines = 1
            ellipsize = TextUtils.TruncateAt.END
            maxWidth = max(dp(60), svc.safeBand().width - dp(200))
            setPadding(dp(6), dp(4), dp(6), dp(4))
            background = rounded(0xE0263238.toInt())
        }
        row.addView(statusView, margins())
        moreButton = chip("⋯", 0xFF455A64.toInt()) { setProbesShown(!probesShown) }.also { row.addView(it, margins()) }
        row.addView(chip("✕", 0xFF455A64.toInt()) { svc.closeOverlay() }, margins())
        root.addView(row)

        // Các bài thử (dùng khi cài lên máy mới hoặc tra lỗi), ẩn sau nút ⋯.
        probeRow.orientation = LinearLayout.HORIZONTAL
        for ((label, action) in listOf(
            "1 trận" to svc::startOneBattle,
            "Nhận diện" to svc::startRecognize,
            "Thành Tích" to svc::startReadRecords,
        )) {
            actions += chip(label, 0xFF455A64.toInt()) { action() }.also { probeRow.addView(it, margins()) }
        }
        root.addView(probeRow)
        logView.apply {
            textSize = 10f
            setTextColor(Color.WHITE)
            setLines(LOG_LINES)
            setPadding(dp(6), dp(3), dp(6), dp(3))
            background = rounded(0xCC000000.toInt())
        }
        root.addView(logView, LinearLayout.LayoutParams(dp(300), LinearLayout.LayoutParams.WRAP_CONTENT).apply {
            setMargins(dp(1), dp(1), dp(1), dp(1))
        })
        svc.onJobChanged = ::showState
        showState(null)
        setLogShown(false)
        setProbesShown(false)
        refreshOptions()
    }

    /** Áp dụng lại cài đặt từ màn hình chính (hiện/ẩn nút ⋯). */
    fun refreshOptions() {
        moreButton.visibility = if (svc.prefs.showProbes) View.VISIBLE else View.GONE
        if (!svc.prefs.showProbes) setProbesShown(false)
    }

    private fun rounded(color: Int) = GradientDrawable().apply {
        setColor(color)
        cornerRadius = dp(6).toFloat()
    }

    private fun margins() = LinearLayout.LayoutParams(
        LinearLayout.LayoutParams.WRAP_CONTENT, LinearLayout.LayoutParams.WRAP_CONTENT,
    ).apply { setMargins(dp(1), dp(1), dp(1), dp(1)) }

    private fun chip(label: String, color: Int, onClick: () -> Unit) = TextView(svc).apply {
        text = label
        textSize = 12f
        setTextColor(Color.WHITE)
        gravity = Gravity.CENTER
        background = rounded(color)
        setPadding(dp(8), dp(4), dp(8), dp(4))
        setOnClickListener { onClick() }
    }

    private fun showState(running: String?) {
        for (b in actions) {
            b.isEnabled = running == null
            b.alpha = if (running == null) 1f else 0.4f
        }
        stopButton.isEnabled = running != null
        stopButton.alpha = if (running != null) 1f else 0.4f
    }

    private fun setLogShown(shown: Boolean) {
        logShown = shown
        logView.visibility = if (shown) View.VISIBLE else View.GONE
    }

    private fun setProbesShown(shown: Boolean) {
        probesShown = shown
        probeRow.visibility = if (shown) View.VISIBLE else View.GONE
    }

    fun show() {
        wm.addView(root, params)
        AppLog.addListener(logListener)
        BotStatus.addListener(statusListener)
        logListener()
        statusListener()
    }

    /** Toàn bộ bảng nổi trên màn hình (null nếu đang ẩn). */
    fun boundsOnScreen(): Box? {
        if (!root.isAttachedToWindow || root.height == 0 || root.visibility != View.VISIBLE) return null
        val loc = IntArray(2)
        root.getLocationOnScreen(loc)
        return Box(loc[0], loc[1], loc[0] + root.width, loc[1] + root.height)
    }

    fun setVisible(visible: Boolean) {
        root.visibility = if (visible) View.VISIBLE else View.GONE
    }

    fun hide() {
        AppLog.removeListener(logListener)
        BotStatus.removeListener(statusListener)
        runCatching { wm.removeView(root) }
    }

    /** Kéo nút ≡ để di chuyển bảng nổi; chạm (không kéo) để mở/đóng nhật ký. */
    private inner class DragToMove : View.OnTouchListener {
        private val slop = ViewConfiguration.get(svc).scaledTouchSlop
        private var downX = 0f
        private var downY = 0f
        private var startX = 0
        private var startY = 0
        private var moved = false

        @SuppressLint("ClickableViewAccessibility")
        override fun onTouch(v: View, e: MotionEvent): Boolean {
            when (e.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    downX = e.rawX
                    downY = e.rawY
                    startX = params.x
                    startY = params.y
                    moved = false
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = e.rawX - downX
                    val dy = e.rawY - downY
                    if (abs(dx) > slop || abs(dy) > slop) moved = true
                    if (moved) {
                        params.x = startX + dx.roundToInt()
                        params.y = startY + dy.roundToInt()
                        wm.updateViewLayout(root, params)
                    }
                }
                MotionEvent.ACTION_UP -> if (!moved) {
                    setLogShown(!logShown)
                } else {
                    svc.prefs.overlayX = params.x
                    svc.prefs.overlayY = params.y
                }
            }
            return true
        }
    }
}
