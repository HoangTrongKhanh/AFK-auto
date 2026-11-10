package vn.afkauto.leoai.vision

import org.opencv.core.Core
import org.opencv.core.Mat
import org.opencv.core.MatOfDouble
import org.opencv.core.Scalar
import org.opencv.imgproc.Imgproc
import kotlin.math.abs

/** Cùng thuật toán hoi_truong.py: nhãn Cấp làm mốc, nhận hai cỡ thẻ; bỏ thẻ cắt/ô trống/nút lọc che. */
fun catTheHoiTruong(img: Mat, nhanCap: Mat): List<TheDanhSach> {
    data class Hit(val score: Double, val x: Int, val y: Int, val scale: Double)
    fun median(xs: List<Double>): Double {
        val v = xs.sorted(); val n = v.size
        return if (n % 2 == 1) v[n/2] else (v[n/2-1] + v[n/2])/2
    }
    val ref = scale(img, REF_W.toDouble()/img.cols())
    val gray = Mat()
    Imgproc.cvtColor(ref, gray, Imgproc.COLOR_BGR2GRAY)
    val hits = mutableListOf<Hit>()
    val y0 = 260; val y1 = ref.rows()-470
    try {
        for (s in listOf(.95, 1.0, 1.15, 1.2, 1.25)) {
            val t = scale(nhanCap, s, Imgproc.INTER_LINEAR)
            val roi = gray.submat(y0, y1, 100, 1490)
            val r = Mat()
            Imgproc.matchTemplate(roi, t, r, Imgproc.TM_CCOEFF_NORMED)
            for (i in 0 until 80) {
                val mm = Core.minMaxLoc(r)
                if (mm.maxVal < .65) break
                val x = mm.maxLoc.x.toInt(); val y = mm.maxLoc.y.toInt()
                hits.add(Hit(mm.maxVal, x+100, y+y0, s))
                val mask = r.submat(maxOf(0,y-50), minOf(r.rows(),y+51), maxOf(0,x-50), minOf(r.cols(),x+51))
                mask.setTo(Scalar(0.0)); mask.release()
            }
            r.release(); roi.release(); t.release()
        }
        val kept = mutableListOf<Hit>()
        for (h in hits.sortedWith(compareByDescending<Hit>{it.score}.thenByDescending{it.x}.thenByDescending{it.y}.thenByDescending{it.scale})) {
            if (kept.none { abs(h.x-it.x)<65 && abs(h.y-it.y)<35 }) kept.add(h)
        }
        val rows = mutableListOf<MutableList<Hit>>()
        for (h in kept.sortedBy{it.y}) {
            val row = rows.firstOrNull { abs(median(it.map { a -> a.y.toDouble() })-h.y)<22 }
            if (row == null) rows.add(mutableListOf(h)) else row.add(h)
        }
        val out = mutableListOf<TheDanhSach>()
        for (row in rows) {
            if (row.size<2 && row[0].score<.83) continue
            val big = median(row.map{it.scale})>1.08
            val size = if (big) 1.15 else 1.0
            val top = median(row.map{it.y.toDouble()})-234*size
            if (top<y0 || top+290*size>ref.rows()-490) continue
            val centers = if(big) (0..4).map{249+268.5*it} else (0..5).map{250+218.5*it}
            val k = 130/(218*size)
            val small = scale(ref,k)
            for (cx in centers) {
                if (cx+100*size>1340 && top+290*size>ref.rows()-650) continue
                val x = (cx*k).toInt(); val y = (top*k).toInt()-15
                if (y<0 || y+205>small.rows() || x-65<0 || x+65>small.cols()) continue
                val card = small.submat(y,y+205,x-65,x+65)
                // numpy card.std() trên cả ba kênh.
                val flat = card.clone(); val one = flat.reshape(1)
                val mean = MatOfDouble(); val std = MatOfDouble()
                Core.meanStdDev(one,mean,std)
                val okStd = std.toArray()[0]>=18
                one.release(); flat.release(); mean.release(); std.release()
                if (!okStd) { card.release(); continue }
                val hsv = Mat(); Imgproc.cvtColor(card,hsv,Imgproc.COLOR_BGR2HSV)
                val px = ByteArray(205*130*3); hsv.get(0,0,px); hsv.release()
                var sat=0; var upper=0; var cream=0
                for (yy in 0 until 205) for (xx in 0 until 130) {
                    val j=(yy*130+xx)*3
                    val ss=px[j+1].toInt() and 255; val vv=px[j+2].toInt() and 255
                    if(ss>100) {sat++; if(yy in 15 until 55) upper++}
                    if(yy in 55 until 140 && xx in 21 until 109 && ss<80 && vv>180) cream++
                }
                if(sat.toDouble()/(205*130)<.15 || upper.toDouble()/(40*130)<.2 || cream.toDouble()/(85*88)>.7) {
                    card.release(); continue
                }
                out.add(TheDanhSach(card.clone(),top+145*size)); card.release()
            }
            small.release()
        }
        return out
    } finally { gray.release(); ref.release() }
}

/** Nhận phần mũ trong biểu tượng: không phụ thuộc có/không vòng tròn và dấu chấm thông báo. */
fun NhanDien.nutHoiTruong(img: Mat): Pair<Int,Int>? {
    if (grayMean(img)<LOCKED_BRIGHTNESS) return null
    val (small,k)=thuNho(img)
    try {
        val hits=listOf("ht_nut_menu","ht_nut_afk").map{tim(small,it)}
        val hit=hits.maxBy{it.diem}
        return if(hit.coViTri && hit.diem>=.8) pyRound(hit.x/k) to pyRound(hit.y/k) else null
    } finally {small.release()}
}
