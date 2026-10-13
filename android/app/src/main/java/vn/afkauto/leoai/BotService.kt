package vn.afkauto.leoai

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.accessibilityservice.GestureDescription.StrokeDescription
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.Path
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.os.SystemClock
import android.view.Display
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import org.opencv.android.Utils
import org.opencv.core.Mat
import org.opencv.imgcodecs.Imgcodecs
import org.opencv.imgproc.Imgproc
import vn.afkauto.leoai.vision.BoMau
import vn.afkauto.leoai.vision.Box
import vn.afkauto.leoai.vision.NhanDien
import vn.afkauto.leoai.vision.REF_W
import java.io.File
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.concurrent.Executors
import kotlin.coroutines.resume

// Hệ thống có lúc không bao giờ trả lời yêu cầu chụp màn hình / thao tác (ví dụ khi lớp "Chống chạm nhầm" của Samsung
// đang che màn hình). Quá hạn thì coi là thất bại thay vì chờ mãi.
private const val SCREENSHOT_TIMEOUT = 5000L
private const val GESTURE_TIMEOUT_EXTRA = 2000L     // cộng thêm vào thời lượng cử chỉ
const val SCREENSHOT_NO_RESPONSE = -1               // mã lỗi riêng: hệ thống không trả lời yêu cầu chụp
private const val OVERLAY_HIDE_WAIT = 80L           // ẩn bảng nổi rồi chờ bấy nhiêu ms cho màn hình vẽ lại trước khi chụp

private const val MAX_DEBUG_IMAGES = 100            // ~3MB/ảnh trên máy 1600x2560
private val FILE_TIME = DateTimeFormatter.ofPattern("yyyyMMdd-HHmmss-SSS")

// Dải trống phía trên màn hình (toạ độ máy gốc rộng 1600, bám mép trên): không mẫu nhận diện nào của game nằm ở đây
// (ô lọc Thành Tích, đồng hồ trận, tiêu đề màn đội hình ở y < 150; thanh thẻ Thành Tích từ y 357). Bảng nổi nằm gọn
// trong dải này thì chụp thẳng, lấn ra ngoài thì ẩn tạm khi chụp.
val DAI_AN_TOAN = Box(100, 150, 1300, 330)

const val GAME_PACKAGE = "com.farlightgames.igame.gp.vn"

/** Bot tự dừng hẳn (đạt điều kiện dừng, kẹt, không thể làm tiếp); reason hiện cho người dùng. */
class StopBot(val reason: String) : Exception(reason)

class ScreenshotFailed(val code: Int) : RuntimeException("chụp màn hình lỗi (mã $code)")

/** Dịch vụ Trợ năng thay cho ADB: chụp màn hình bằng takeScreenshot(), chạm/vuốt bằng dispatchGesture(). */
class BotService : AccessibilityService() {
    companion object {
        @Volatile
        var instance: BotService? = null
            private set
    }

    val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    lateinit var nd: NhanDien
        private set
    lateinit var prefs: Prefs
        private set
    lateinit var leo: Leo
        private set
    private var overlay: Overlay? = null
    private val shotExecutor = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private var job: Job? = null

    /** App đang ở trên cùng màn hình (theo sự kiện đổi cửa sổ, bỏ qua chính app này), "" nếu chưa biết. */
    @Volatile
    var foregroundPackage = ""
        private set

    /** Gọi trên luồng chính với tên tác vụ đang chạy, null khi rảnh. */
    var onJobChanged: (String?) -> Unit = {}

    override fun onServiceConnected() {
        nd = NhanDien(BoMau.load(
            read = { name -> assets.open(name).use { it.readBytes() } },
            list = { dir -> assets.list(dir).orEmpty().toList() },
        ))
        prefs = Prefs(this)
        leo = Leo(this)
        overlay = Overlay(this).also { it.show() }
        applyOverlayVisibility()
        instance = this
        AppLog.i("Đã bật dịch vụ Trợ năng. Mở game ở Màn AFK rồi bấm ▶ trên bảng nổi.")
        if (prefs.running && !prefs.overlayClosed) {
            AppLog.i("Tiếp tục chạy (dịch vụ vừa khởi động lại).")
            startBot()
        } else {
            BotStatus.set("Sẵn sàng · ${prefs.todayText()}")
        }
    }

    // ---------------------------------------------------------------- Tác vụ

    /** ▶ Chạy: leo liên tục; nhớ trạng thái để dịch vụ khởi động lại thì chạy tiếp. */
    fun startBot() {
        prefs.running = true
        runJob("Leo ải") { leo.chay(Leo.CheDoChay.LEO) }
    }

    /** Đánh đúng 1 trận rồi dừng (thử). */
    fun startOneBattle() = runJob("Đánh 1 trận") { leo.chay(Leo.CheDoChay.MOT_TRAN) }

    /** Bài thử: mở Thành Tích, đọc danh sách đội rồi dừng (không đánh, không chép). */
    fun startReadRecords() = runJob("Đọc Thành Tích") { leo.chay(Leo.CheDoChay.XEM_THANH_TICH) }

    /** Bài thử: nhận diện màn hình hiện tại và ghi vào nhật ký. */
    fun startRecognize() = runJob("Nhận diện màn hình") { leo.nhanDienThu() }

    /** Chạy một tác vụ; mỗi lúc chỉ một tác vụ. */
    fun runJob(name: String, block: suspend () -> Unit) {
        if (job?.isActive == true) return
        val j = scope.launch {
            AppLog.i("▶ $name")
            try {
                block()
            } catch (e: CancellationException) {
                AppLog.i("Đã dừng.")
                throw e
            } catch (e: StopBot) {
                prefs.running = false
                AppLog.i("DỪNG: ${e.reason}")
                Notifier.show(this@BotService, Notifier.ID_STOPPED, "AFK Auto đã dừng", e.reason)
            } catch (e: Exception) {
                prefs.running = false
                AppLog.e("Lỗi: ${e.message ?: e}", e)
                Notifier.show(this@BotService, Notifier.ID_STOPPED, "AFK Auto dừng vì lỗi",
                    "${e.message ?: e}. Mở app, bấm Sao chép nhật ký và gửi cho người cài app.")
            }
        }
        job = j
        onJobChanged(name)
        j.invokeOnCompletion {
            main.post {
                if (job === j) {
                    onJobChanged(null)
                    val what = if (prefs.overlayClosed) "Bảng nổi đã đóng" else "Đã dừng"
                    BotStatus.set("$what · ${prefs.todayText()}")
                }
            }
        }
    }

    /** ■: dừng tác vụ đang chạy (người dùng chủ động dừng nên không tự chạy tiếp nữa). */
    fun stopJob() {
        prefs.running = false
        job?.cancel()
    }

    /** Lưu ảnh vào files/debug/ (nếu bật trong màn hình chính); giữ tối đa MAX_DEBUG_IMAGES ảnh mới nhất. */
    fun saveImage(img: Mat, name: String, force: Boolean = false) {
        if (!prefs.saveImages && !force) return
        val copy = img.clone()
        scope.launch(Dispatchers.IO) {
            val dir = File(getExternalFilesDir(null), "debug").apply { mkdirs() }
            Imgcodecs.imwrite(File(dir, "${LocalDateTime.now().format(FILE_TIME)}-$name.png").path, copy)
            copy.release()
            dir.listFiles()?.sortedByDescending { it.name }?.drop(MAX_DEBUG_IMAGES)?.forEach { it.delete() }
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val pkg = event?.packageName?.toString() ?: return
        if (event.eventType == AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED && pkg != packageName) foregroundPackage = pkg
    }

    override fun onInterrupt() {}

    override fun onUnbind(intent: Intent?): Boolean {
        shutdown()
        return super.onUnbind(intent)
    }

    override fun onDestroy() {
        shutdown()
        super.onDestroy()
    }

    private fun shutdown() {
        if (instance == null) return
        instance = null
        scope.cancel()
        overlay?.hide()
        overlay = null
        shotExecutor.shutdown()
        AppLog.i("Đã tắt dịch vụ Trợ năng.")
    }

    // ---------------------------------------------------------------- Bảng nổi

    private var appScreenOpen = false       // màn hình chính của app đang mở: ẩn bảng nổi để không che nội dung
    private var hiddenForShot = false       // ẩn tạm trong lúc chụp màn hình

    private fun applyOverlayVisibility() {
        overlay?.setVisible(!prefs.overlayClosed && !appScreenOpen && !hiddenForShot)
    }

    fun setAppScreenOpen(open: Boolean) {
        appScreenOpen = open
        applyOverlayVisibility()
    }

    /** Nút ✕: đóng bảng nổi. Bảng nổi giữ màn hình sáng cho bot nên đóng nó thì dừng bot luôn. */
    fun closeOverlay() {
        if (job?.isActive == true) stopJob()
        AppLog.i("Đã đóng bảng nổi. Mở lại bằng nút Hiện bảng nổi trong app.")
        prefs.overlayClosed = true
        applyOverlayVisibility()
        BotStatus.set("Bảng nổi đã đóng · ${prefs.todayText()}")
    }

    /** Nút Hiện bảng nổi trong app. */
    fun reopenOverlay() {
        prefs.overlayClosed = false
        applyOverlayVisibility()
        BotStatus.set("Sẵn sàng · ${prefs.todayText()}")
    }

    fun refreshOverlay() {
        overlay?.refreshOptions()
    }

    fun screenWidth(): Int = getSystemService(WindowManager::class.java).maximumWindowMetrics.bounds.width()

    /** Dải an toàn cho bảng nổi trên màn hình này (px màn hình). */
    fun safeBand(): Box {
        val s = screenWidth().toDouble() / REF_W
        return Box((DAI_AN_TOAN.x0 * s).toInt(), (DAI_AN_TOAN.y0 * s).toInt(), (DAI_AN_TOAN.x1 * s).toInt(), (DAI_AN_TOAN.y1 * s).toInt())
    }

    /** Bảng nổi đang hiện và lấn ra ngoài dải an toàn (sẽ lọt vào vùng nhận diện của ảnh chụp). */
    private fun overlayInTheWay(): Boolean {
        val b = overlay?.boundsOnScreen() ?: return false
        val safe = safeBand()
        return !(b.x0 >= safe.x0 && b.y0 >= safe.y0 && b.x1 <= safe.x1 && b.y1 <= safe.y1)
    }

    // ---------------------------------------------------------------- Chụp màn hình

    /** Ảnh chụp màn hình (BGR). Người gọi giải phóng ảnh. */
    suspend fun screenshot(): Mat {
        val hide = overlayInTheWay()
        if (hide) {
            hiddenForShot = true
            applyOverlayVisibility()
            delay(OVERLAY_HIDE_WAIT)
        }
        try {
            var retries = 0
            while (true) {
                val result = withTimeoutOrNull(SCREENSHOT_TIMEOUT) { requestScreenshot() } ?: SCREENSHOT_NO_RESPONSE
                if (result is ScreenshotResult) return withContext(Dispatchers.Default) { toMat(result) }
                val code = result as Int
                // Hệ thống giới hạn số lần chụp mỗi giây: chờ một chút rồi chụp lại.
                if (code == ERROR_TAKE_SCREENSHOT_INTERVAL_TIME_SHORT && retries < 100) {
                    retries++
                    delay(40)
                    continue
                }
                throw ScreenshotFailed(code)
            }
        } finally {
            if (hide) {
                hiddenForShot = false
                applyOverlayVisibility()
            }
        }
    }

    /** ScreenshotResult nếu chụp được, mã lỗi (Int) nếu không. */
    private suspend fun requestScreenshot(): Any = suspendCancellableCoroutine { cont ->
        takeScreenshot(Display.DEFAULT_DISPLAY, shotExecutor, object : TakeScreenshotCallback {
            override fun onSuccess(result: ScreenshotResult) {
                if (cont.isActive) cont.resume(result) else result.hardwareBuffer.close()
            }

            override fun onFailure(errorCode: Int) {
                if (cont.isActive) cont.resume(errorCode)
            }
        })
    }

    private fun toMat(result: ScreenshotResult): Mat {
        val buffer = result.hardwareBuffer
        try {
            val hw = Bitmap.wrapHardwareBuffer(buffer, result.colorSpace)
                ?: throw IllegalStateException("không đọc được ảnh chụp màn hình")
            val bmp = hw.copy(Bitmap.Config.ARGB_8888, false)
            hw.recycle()
            val rgba = Mat()
            Utils.bitmapToMat(bmp, rgba)
            bmp.recycle()
            val bgr = Mat()
            Imgproc.cvtColor(rgba, bgr, Imgproc.COLOR_RGBA2BGR)
            rgba.release()
            return bgr
        } finally {
            buffer.close()
        }
    }

    // ---------------------------------------------------------------- Thao tác

    /** Thực hiện cử chỉ; false nếu bị huỷ hoặc hệ thống không trả lời trong thời lượng cử chỉ + GESTURE_TIMEOUT_EXTRA. */
    private suspend fun dispatch(gesture: GestureDescription): Boolean {
        val duration = (0 until gesture.strokeCount).maxOf { gesture.getStroke(it).let { s -> s.startTime + s.duration } }
        val result = withTimeoutOrNull(duration + GESTURE_TIMEOUT_EXTRA) {
            suspendCancellableCoroutine { cont ->
                val callback = object : GestureResultCallback() {
                    override fun onCompleted(d: GestureDescription?) {
                        if (cont.isActive) cont.resume(true)
                    }

                    override fun onCancelled(d: GestureDescription?) {
                        if (cont.isActive) cont.resume(false)
                    }
                }
                if (!dispatchGesture(gesture, callback, null)) cont.resume(false)
            }
        }
        if (result == null) AppLog.i("  Hệ thống không phản hồi thao tác chạm (màn hình đang bị che?).")
        return result == true
    }

    private fun line(x0: Int, y0: Int, x1: Int, y1: Int) = Path().apply {
        moveTo(x0.toFloat(), y0.toFloat())
        if (x1 != x0 || y1 != y0) lineTo(x1.toFloat(), y1.toFloat())
    }

    suspend fun tap(x: Int, y: Int) =
        dispatch(GestureDescription.Builder().addStroke(StrokeDescription(line(x, y, x, y), 0, 60)).build())

    suspend fun swipe(x0: Int, y0: Int, x1: Int, y1: Int, ms: Long) =
        dispatch(GestureDescription.Builder().addStroke(StrokeDescription(line(x0, y0, x1, y1), 0, ms)).build())

    // ---------------------------------------------------------------- Trạng thái máy

    fun screenOn() = getSystemService(PowerManager::class.java).isInteractive

    fun uptime() = SystemClock.uptimeMillis()
}
