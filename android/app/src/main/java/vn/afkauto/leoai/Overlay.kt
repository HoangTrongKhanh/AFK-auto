package vn.afkauto.leoai

import android.annotation.SuppressLint
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.InsetDrawable
import android.text.TextUtils
import android.text.method.ScrollingMovementMethod
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import android.view.WindowManager
import android.widget.CheckBox
import android.widget.CompoundButton
import android.widget.LinearLayout
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.TextView
import vn.afkauto.leoai.vision.Box
import kotlin.math.abs
import kotlin.math.roundToInt

/** Bảng nổi thu gọn; các bài thử và nhật ký nằm trong Nâng cao của phần mở rộng. */
class Overlay(private val svc: BotService) {
    private val wm = svc.getSystemService(WindowManager::class.java)
    private val density = svc.resources.displayMetrics.density
    private fun dp(v: Int) = (v * density).roundToInt()
    private val ink = svc.getColor(R.color.ui_ink)
    private val green = 0xFF27694F.toInt()
    private val accent = svc.getColor(R.color.ui_accent)
    private val params = WindowManager.LayoutParams(
        minOf(dp(260), svc.screenWidth() - dp(16)), WindowManager.LayoutParams.WRAP_CONTENT,
        WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
        PixelFormat.TRANSLUCENT,
    ).apply {
        gravity = Gravity.TOP or Gravity.START
        x = svc.prefs.overlayX.takeIf { it >= 0 } ?: svc.safeBand().x0
        y = svc.prefs.overlayY.takeIf { it >= 0 } ?: svc.safeBand().y0
    }
    private val root = LinearLayout(svc)
    private val options = LinearLayout(svc)
    private val advanced = LinearLayout(svc)
    private val statusView = TextView(svc)
    private val logView = TextView(svc)
    private val cheDo = RadioGroup(svc)
    private val nutCheDo = mutableMapOf<String, RadioButton>()
    private val leoHo = CheckBox(svc)
    private val tuDong = CheckBox(svc)
    private lateinit var runButton: TextView
    private lateinit var expandButton: TextView
    private lateinit var advancedButton: TextView
    private val actions = mutableListOf<TextView>()
    private var expanded = false
    private var advancedShown = false
    private var syncing = false
    private var running = false
    private val statusListener: () -> Unit = { statusView.text = BotStatus.text }
    private val logListener: () -> Unit = {
        logView.text = AppLog.recent(30).joinToString("\n")
        logView.post {
            val layout = logView.layout
            if (layout != null) logView.scrollTo(0, maxOf(0, layout.height - logView.height + logView.totalPaddingTop + logView.totalPaddingBottom))
        }
    }
    init {
        root.orientation = LinearLayout.VERTICAL
        root.background = rounded(svc.getColor(R.color.ui_surface), true)
        root.setPadding(dp(4), dp(3), dp(4), dp(3))
        val row = line()
        row.addView(chip("⠿") {}.apply { setOnTouchListener(DragToMove()) })
        statusView.apply { textSize = 11f; setTextColor(ink); maxLines = 1; ellipsize = TextUtils.TruncateAt.END }
        row.addView(statusView, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        runButton = chip("▶ Chạy") { if (running) svc.stopJob() else svc.startBot() }.also { it.setTextColor(Color.WHITE); it.background = rounded(green); row.addView(it) }
        expandButton = chip("⌄") { setExpanded(!expanded) }.also {
            it.contentDescription = "Mở hoặc thu gọn bảng nổi"
            it.background = rounded(svc.getColor(R.color.ui_background), true)
            row.addView(it, LinearLayout.LayoutParams(dp(40), dp(24)).apply { leftMargin = dp(6) })
        }
        row.addView(chip("×") { svc.closeOverlay() }.apply {
            contentDescription = "Đóng bảng nổi và dừng bot"
            setTextColor(svc.getColor(R.color.ui_danger))
            background = rounded(svc.getColor(R.color.ui_background), true)
        }, LinearLayout.LayoutParams(dp(28), dp(24)).apply { leftMargin = dp(8) })
        statusView.setOnClickListener { setExpanded(!expanded) }
        root.addView(row)
        options.orientation = LinearLayout.VERTICAL
        options.setPadding(dp(4), dp(4), dp(4), 0)
        cheDo.orientation = RadioGroup.HORIZONTAL
        for ((ma, ten) in listOf("ca_hai" to "Cả hai", "afk" to "Ải AFK")) {
            val b = RadioButton(svc).apply { id = View.generateViewId(); text = ten; styleCheck(this) }
            nutCheDo[ma] = b
            cheDo.addView(b, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        }
        cheDo.setOnCheckedChangeListener { _, id -> if (!syncing) nutCheDo.entries.firstOrNull { it.value.id == id }?.let { svc.prefs.cheDo = it.key } }
        options.addView(cheDo)
        leoHo.apply { text = "Leo hộ"; styleCheck(this); setOnCheckedChangeListener { _, v -> if (!syncing) svc.prefs.leoHo = v } }
        tuDong.apply { text = "Tự động"; styleCheck(this); setOnCheckedChangeListener { _, v -> if (!syncing) svc.prefs.tuDong = v } }
        options.addView(line().apply {
            addView(leoHo, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            addView(tuDong, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
        })
        // Trạng thái giữ sáng xem trong app; không thêm hàng chiếm chỗ trên game.
        advancedButton = chip("Nâng cao ▾") { advancedShown = !advancedShown; updateExpansion() }
        options.addView(advancedButton)
        advanced.orientation = LinearLayout.VERTICAL
        val probes = listOf("Leo 1 trận" to svc::startOneBattle, "Nhận diện" to svc::startRecognize,
            "Thành Tích" to svc::startReadRecords, "Khung tướng" to svc::startReadHeroes)
        for (pair in probes.chunked(2)) {
            val r = line()
            for ((label, action) in pair) {
                val b = chip(label) { action() }.apply { background = rounded(svc.getColor(R.color.ui_background), true) }
                actions.add(b)
                r.addView(b, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f).apply { setMargins(dp(2), dp(2), dp(2), dp(2)) })
            }
            advanced.addView(r)
        }
        logView.apply { textSize = 11f; setTextColor(ink); setLines(4); setPadding(dp(8), dp(8), dp(8), dp(8)); background = rounded(svc.getColor(R.color.ui_background), true); movementMethod = ScrollingMovementMethod() }
        advanced.addView(logView)
        options.addView(advanced)
        root.addView(options)
        svc.onJobChanged = ::showState
        refreshOptions()
        showState(null)
        updateExpansion()
    }
    private fun line() = LinearLayout(svc).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
    private fun rounded(color: Int, border: Boolean = false) = GradientDrawable().apply { setColor(color); cornerRadius = dp(8).toFloat(); if (border) setStroke(dp(1), svc.getColor(R.color.ui_border)) }
    private fun chip(label: String, action: () -> Unit) = TextView(svc).apply {
        text = label; textSize = 12f; setTextColor(ink); gravity = Gravity.CENTER
        includeFontPadding = false
        minHeight = dp(24); setPadding(dp(6), dp(2), dp(6), dp(2)); setOnClickListener { action() }
    }
    private fun styleCheck(b: CompoundButton) = b.apply {
        textSize = 12f; setTextColor(ink); includeFontPadding = false
        buttonDrawable?.let { original ->
            buttonDrawable = object : InsetDrawable(original, 0) {
                override fun getIntrinsicWidth() = dp(20)
                override fun getIntrinsicHeight() = dp(20)
            }
        }
        buttonTintList = ColorStateList.valueOf(accent)
        minHeight = dp(26); minimumHeight = dp(26); setPadding(0, 0, 0, 0)
    }
    fun refreshOptions() {
        syncing = true
        try {
            // Chế độ chỉ Huyền Linh cũ vẫn chỉnh được trong app; không hiển thị nhầm thành Cả hai.
            cheDo.check(nutCheDo[svc.prefs.cheDo]?.id ?: -1)
            leoHo.isChecked = svc.prefs.leoHo
            tuDong.isChecked = svc.prefs.tuDong
        } finally { syncing = false }
    }
    private fun showState(name: String?) {
        running = name != null
        if (running) setExpanded(false)
        runButton.text = if (running) "■ Dừng" else "▶ Chạy"
        for (b in actions) { b.isEnabled = !running; b.alpha = if (running) 0.4f else 1f }
        for (b in nutCheDo.values) { b.isEnabled = !running; b.alpha = if (running) 0.4f else 1f }
        leoHo.isEnabled = !running
    }
    /** Chỉ giữ sáng trong lúc có tác vụ; tắt ngay cả khi coroutine chưa kết thúc hủy. */
    fun setKeepingScreenOn(active: Boolean) {
        val flag = WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
        params.flags = if (active) params.flags or flag else params.flags and flag.inv()
        if (root.isAttachedToWindow) wm.updateViewLayout(root, params)
    }
    private fun setExpanded(value: Boolean) { expanded = value; updateExpansion() }
    private fun updateExpansion() {
        params.width = minOf(dp(if (expanded) 280 else 260), svc.screenWidth() - dp(16))
        options.visibility = if (expanded) View.VISIBLE else View.GONE
        advanced.visibility = if (advancedShown) View.VISIBLE else View.GONE
        expandButton.text = if (expanded) "⌃" else "⌄"
        advancedButton.text = if (advancedShown) "Nâng cao ▴" else "Nâng cao ▾"
        if (root.isAttachedToWindow) wm.updateViewLayout(root, params)
    }
    fun show() {
        wm.addView(root, params)
        AppLog.addListener(logListener); BotStatus.addListener(statusListener)
        logListener(); statusListener(); setKeepingScreenOn(false)
    }
    fun boundsOnScreen(): Box? {
        if (!root.isAttachedToWindow || root.height == 0 || root.visibility != View.VISIBLE) return null
        val p = IntArray(2); root.getLocationOnScreen(p)
        return Box(p[0], p[1], p[0] + root.width, p[1] + root.height)
    }
    fun setVisible(visible: Boolean) { root.visibility = if (visible) View.VISIBLE else View.GONE }
    fun hide() { setKeepingScreenOn(false); AppLog.removeListener(logListener); BotStatus.removeListener(statusListener); runCatching { wm.removeView(root) } }
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
                    setExpanded(!expanded)
                } else {
                    svc.prefs.overlayX = params.x
                    svc.prefs.overlayY = params.y
                }
            }
            return true
        }
    }
}
