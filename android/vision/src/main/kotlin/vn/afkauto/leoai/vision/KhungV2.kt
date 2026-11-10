package vn.afkauto.leoai.vision

import org.json.JSONObject
import org.json.JSONArray
import org.opencv.core.*
import org.opencv.imgproc.Imgproc
import kotlin.math.*

const val KHUNG_CHUA_RO = -3 // Chỉ dùng nội bộ; JSON ghi null. -1 vẫn là chưa sở hữu.
data class Bien(val l:Int,val t:Int,val r:Int,val b:Int) {
    fun json()=JSONArray(listOf(l,t,r,b))
}
data class ChatLuongThe(var dayDu:Boolean=false,var lyDo:String="khong_tim_duoc_bien",var bien:Bien?=null,
    var chuan:Bien?=null,var tamX:Double=0.0,var tamY:Double=0.0,var supports:List<Double> = emptyList(),
    var saoDu:Boolean=false,var vienDu:Boolean=false,var kheHang:Boolean=true,var kheCot:Boolean=true) {
    fun json()=JSONObject().put("day_du",dayDu).put("ly_do",lyDo).put("bien",bien?.json()?:JSONObject.NULL)
        .put("bien_chuan",chuan?.json()?:JSONObject.NULL).put("tam_x",tamX).put("tam_y",tamY)
        .put("ho_tro_vien",JSONArray(supports)).put("vung_sao_day_du",saoDu).put("vien_day_du",vienDu)
        .put("khe_hang_tach",kheHang).put("khe_cot_tach",kheCot)
}
data class SaoV2(val diem:Double,val tyLe:Double,val hang:Boolean,val tin:Boolean)
data class KetQuaKhung(val khung:Int=KHUNG_CHUA_RO,val lyDo:String,val sao:SaoV2?=null,val learned:JSONObject?=null,val evidence:JSONObject?=null) {
    fun json()=JSONObject().put("khung",if(khung==KHUNG_CHUA_RO) JSONObject.NULL else khung).put("ly_do",lyDo)
        .put("diem_sao",sao?.diem?:JSONObject.NULL).put("sao_ty_le",sao?.tyLe?:JSONObject.NULL)
        .put("co_hang_sao",sao?.hang?:false).put("mau_khung_can",learned?:JSONObject.NULL)
        .put("bang_chung_hinh_hoc",evidence?:JSONObject.NULL)
}
internal fun bytes(m:Mat)=ByteArray((m.total()*m.channels()).toInt()).also { m.get(0,0,it) }
internal fun hsv(m:Mat):Mat=Mat().also {Imgproc.cvtColor(m,it,Imgproc.COLOR_BGR2HSV)}
internal fun gray(m:Mat):Mat=Mat().also {Imgproc.cvtColor(m,it,Imgproc.COLOR_BGR2GRAY)}
internal fun sd(m:Mat):Double {val flat=m.reshape(1);val mean=MatOfDouble();val s=MatOfDouble();Core.meanStdDev(flat,mean,s);val v=s.toArray()[0];mean.release();s.release();flat.release();return v}
internal fun roi(m:Mat,l:Int,t:Int,r:Int,b:Int)=m.submat(t,b,l,r)
internal fun median(v:List<Double>):Double {val s=v.sorted();return if(s.size%2==1)s[s.size/2] else(s[s.size/2-1]+s[s.size/2])/2}
internal fun resize(m:Mat,w:Int,h:Int,mode:Int=Imgproc.INTER_LINEAR):Mat=Mat().also {Imgproc.resize(m,it,Size(w.toDouble(),h.toDouble()),0.0,0.0,mode)}
internal fun components(mask:Mat):Pair<Mat,List<IntArray>> {
    val labels=Mat();val stats=Mat();val center=Mat();Imgproc.connectedComponentsWithStats(mask,labels,stats,center,8,CvType.CV_32S)
    val list=(1 until stats.rows()).map { i -> IntArray(5).also {stats.get(i,0,it)} };stats.release();center.release();return labels to list
}
fun saoDaTyLe(the:Mat,templates:List<Mat>):SaoV2 {
    val cut=roi(the,0,5,the.cols(),70);val g=gray(cut);cut.release()
    data class Peak(val d:Double,val x:Double,val y:Double,val w:Int)
    val peaks=mutableListOf<Peak>();var best=-1.0;var bestScale=1.0
    try {for(s in listOf(.75,.8,.85,.9,.95,1.0,1.05,1.1))for(tpl in templates) {
        val t=scale(tpl,s,if(s<1)Imgproc.INTER_AREA else Imgproc.INTER_LINEAR);val r=Mat()
        Imgproc.matchTemplate(g,t,r,Imgproc.TM_CCOEFF_NORMED);val max=Core.minMaxLoc(r).maxVal
        if(max>best || max==best && s>bestScale) {best=max;bestScale=s}
        repeat(8) {
            val m=Core.minMaxLoc(r);if(m.maxVal>=.68) {
                val x=m.maxLoc.x.toInt();val y=m.maxLoc.y.toInt();peaks.add(Peak(m.maxVal,x+t.cols()/2.0,y+t.rows()/2.0,t.cols()))
                val z=r.submat(maxOf(0,y-6),minOf(r.rows(),y+7),maxOf(0,x-6),minOf(r.cols(),x+7));z.setTo(Scalar(0.0));z.release()
            }
        };r.release();t.release()
    }} finally {g.release()}
    val kept=mutableListOf<Peak>()
    for(p in peaks.sortedWith(compareByDescending<Peak>{it.d}.thenByDescending{it.x}.thenByDescending{it.y}.thenByDescending{it.w}))
        if(kept.none{abs(p.x-it.x)<7 && abs(p.y-it.y)<7})kept.add(p)
    val pair=kept.indices.any{i -> kept.drop(i+1).any{q -> val p=kept[i];abs(p.y-q.y)<=4 && abs(p.x-q.x)>=.75*min(p.w,q.w) && abs(p.x-q.x)<=1.6*max(p.w,q.w) && max(p.d,q.d)>=.75}}
    return SaoV2(best,bestScale,pair,best>=.82 || pair)
}
class KhungV2(private val model:JSONObject,private val templates:List<Mat>) {
    private val fs=model.getJSONArray("features").let {a -> Array(a.length()){i -> a.getJSONArray(i).let {v -> FloatArray(v.length()){v.getDouble(it).toFloat()}}}}
    private val labels=model.getJSONArray("labels").let {a->IntArray(a.length()){a.getInt(it)}}
    private val ids=model.getJSONArray("ids").let {a->IntArray(a.length()){a.getInt(it)}}
    private val radius=model.getJSONArray("radius").let {a->DoubleArray(a.length()){a.getDouble(it)}}
    init {require(fs.size==labels.size && fs.size==ids.size && fs.all{it.size==70 && it.all{v->v.isFinite()}} && labels.toSet()==setOf(0,1) && radius.size==2 && radius.all{it>0 && it.isFinite()})}
    fun release() { templates.forEach { it.release() } }
    fun dacTrung(the:Mat,q:ChatLuongThe):FloatArray {
        require(q.dayDu);val b=requireNotNull(q.chuan);val crop=roi(the,b.l,b.t,b.r,b.b);val obj=resize(crop,96,144,Imgproc.INTER_AREA);crop.release();val h=hsv(obj);obj.release();val p=bytes(h);h.release();val out=mutableListOf<Float>()
        fun channel(x:Int,y:Int,c:Int)=p[(y*96+x)*3+c].toInt() and 255
        for(box in listOf(Bien(0,0,24,20),Bien(72,0,96,20),Bien(0,35,7,115),Bien(89,35,96,115))) {
            val hist=DoubleArray(12);val ss=mutableListOf<Double>();val vv=mutableListOf<Double>()
            for(y in box.t until box.b)for(x in box.l until box.r){val hu=channel(x,y,0);val s=channel(x,y,1).toDouble();hist[min(11,hu/15)]+=s/255;ss.add(s);vv.add(channel(x,y,2).toDouble())}
            hist.forEach{out.add((it/ss.size).toFloat())}
            for(v in listOf(ss,vv)){val mean=v.average();out.add((mean/255).toFloat());out.add((sqrt(v.sumOf{(it-mean).pow(2)}/v.size)/255).toFloat())}
        }
        for(k in 0..2){var cyan=0;var gold=0;for(y in 0 until 42)for(x in k*32 until (k+1)*32){val hu=channel(x,y,0);val s=channel(x,y,1);val v=channel(x,y,2);if(hu in 75..115 && s>=25 && v>=150)cyan++;if(hu in 10..38 && s>=100 && v>=150)gold++};out.add(cyan.toFloat()/(42*32));out.add(gold.toFloat()/(42*32))}
        return out.toFloatArray()
    }
    fun predict(the:Mat,q:ChatLuongThe):JSONObject {
        val f=dacTrung(the,q);val distances=fs.map { v -> v.indices.sumOf{((v[it]-f[it])*(v[it]-f[it])).toDouble()}/70 }
        val d=(0..1).map{k -> distances.indices.filter{labels[it]==k}.map{distances[it]}.sorted().take(3).average()}
        val k=if(d[1]<d[0])1 else 0;val known=d[k]<=radius[k] && d[k]<model.getDouble("ratio")*d[1-k]
        return JSONObject().put("khung",if(known)k else JSONObject.NULL).put("khoang_cach_khong",d[0]).put("khoang_cach_co",d[1])
            .put("mau_gan_nhat",ids[distances.indices.minBy{distances[it]}]).put("ty_le_mau_sao_xanh",listOf(64,66,68).map{f[it]}.average())
            .put("ly_do",if(d[k]>radius[k])"ngoai_mien_mau_can" else if(known)"mau_can_dong_thuan" else "mau_can_chua_tach_biet")
    }
    fun danhGia(the:Mat,q:ChatLuongThe):KetQuaKhung {
        if(!q.dayDu || !q.saoDu || !q.vienDu)return KetQuaKhung(lyDo="bien_bi_cat_hoac_chua_xac_minh")
        if(the.rows()!=205 || the.cols()!=130)return KetQuaKhung(lyDo="anh_khong_hop_le")
        val g=gray(the);val face=roi(g,21,55,109,140);val low=sd(g)<15 || sd(face)<12;face.release();g.release();if(low)return KetQuaKhung(lyDo="anh_it_chi_tiet")
        val star=saoDaTyLe(the,templates);val learned=predict(the,q);val b=requireNotNull(q.chuan);val crop=roi(the,b.l,b.t,b.r,b.b);val obj=resize(crop,96,144,Imgproc.INTER_AREA);crop.release();val hp=hsv(obj);val hs=bytes(hp);hp.release();val bp=bytes(obj);obj.release();val bg=the.get(0,0)
        fun gold(x:Int,y:Int):Boolean {val j=(y*96+x)*3;return (hs[j].toInt() and 255) in 10..38 && (hs[j+1].toInt() and 255)>=100 && (hs[j+2].toInt() and 255)>=140}
        var sideGold=0;var sideBg=0
        for(y in 25 until 120)for(x in (0..7)+(88..95))if(gold(x,y))sideGold++
        for(y in 25 until 120)for(x in (0..3)+(92..95)){val j=(y*96+x)*3;val dist=(0..2).sumOf{((bp[j+it].toInt() and 255)-bg[it]).pow(2)};if(sqrt(dist)<25)sideBg++}
        val corner=listOf(0,72).maxOf { xx -> (0 until 22).sumOf{y->(xx until xx+24).count{x->gold(x,y)}}.toDouble()/(22*24)}
        val cyan=ByteArray(44*96){i->val j=i*3;if((hs[j].toInt() and 255) in 75..115 && (hs[j+1].toInt() and 255)>=25 && (hs[j+2].toInt() and 255)>=150)1 else 0};val mask=Mat(44,96,CvType.CV_8U);mask.put(0,0,cyan);val (lab,stats)=components(mask);lab.release();mask.release();val pieces=stats.filter{it[2] in 3..25 && it[3] in 3..25 && it[4]>=5};val area=pieces.sumOf{it[4]}
        val sg=sideGold.toDouble()/(95*16);val sb=sideBg.toDouble()/(95*8)
        val ev=JSONObject().put("vang_canh",sg).put("nen_canh",sb).put("vang_goc",corner).put("dien_tich_sao_xanh",area).put("manh_sao_xanh",pieces.size)
        val blue=area>=20 && corner>=.10;val ornate=sb>=.25 && sg>=.20;val plain=sb<.20 && !blue && !ornate && star.diem<.85
        val k=if(learned.isNull("khung"))null else learned.getInt("khung")
        val result=when {
            k==1 -> if(plain)KHUNG_CHUA_RO to "mau_va_hinh_hoc_mau_thuan_v2" else 1 to "mau_can_dong_thuan_v2"
            k==0 -> if(blue && star.diem>=.75)KHUNG_CHUA_RO to "mau_va_sao_mau_thuan_v2" else 0 to "mau_can_dong_thuan_v2"
            blue && star.diem>=.62 -> 1 to "sao_xanh_va_vien_goc_v2"
            plain -> 0 to "the_thang_khong_co_bang_chung_sao_v2"
            ornate && star.diem>=.75 && star.tin -> 1 to "sao_va_vien_trang_tri_v2"
            else -> KHUNG_CHUA_RO to "bang_chung_v2_chua_ro"
        }
        return KetQuaKhung(result.first,result.second,star,learned,ev)
    }
}
