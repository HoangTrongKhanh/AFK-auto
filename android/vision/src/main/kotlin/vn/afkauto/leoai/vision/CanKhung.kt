package vn.afkauto.leoai.vision

import org.opencv.core.*
import org.opencv.imgproc.Imgproc
import kotlin.math.*

internal fun maskVien(img:Mat):Mat {
    val h=hsv(img);val p=bytes(h);h.release();val a=ByteArray(img.rows()*img.cols()) {i -> val j=i*3;val hue=p[j].toInt() and 255;val s=p[j+1].toInt() and 255;val v=p[j+2].toInt() and 255;if(s>65 || v<180 || hue in 120..175 && s>=25)1 else 0}
    return Mat(img.rows(),img.cols(),CvType.CV_8U).also {it.put(0,0,a)}
}
internal fun canvas(ref:Mat,box:Bien,bgRoi:Mat):Pair<Mat,Bien> {
    val bw=box.r-box.l;val bh=box.b-box.t;val k=min(122.0/bw,189.0/bh);val tw=pyRound(bw*k);val th=pyRound(bh*k);val ox=(130-tw)/2;val oy=(205-th)/2
    val hh=hsv(bgRoi);val hp=bytes(hh);hh.release();val bp=bytes(bgRoi);val eligible=(0 until bgRoi.rows()*bgRoi.cols()).filter{(hp[it*3+1].toInt() and 255)<60 && (hp[it*3+2].toInt() and 255)>200}
    val bg=if(eligible.isEmpty())doubleArrayOf(220.0,234.0,243.0) else DoubleArray(3){c->val vals=eligible.map{(bp[it*3+c].toInt() and 255).toDouble()};median(vals).toInt().toDouble()}
    val out=Mat(205,130,CvType.CV_8UC3,Scalar(bg[0],bg[1],bg[2]));val cut=roi(ref,box.l,box.t,box.r,box.b);val small=resize(cut,tw,th,Imgproc.INTER_AREA);cut.release();val target=roi(out,ox,oy,ox+tw,oy+th);small.copyTo(target);target.release();small.release()
    return out to Bien(ox,oy,ox+tw,oy+th)
}
fun canKhung(ref:Mat,cx:Double,top:Double,size:Double,visibleTop:Double,visibleBottom:Double):Pair<Mat?,ChatLuongThe> {
    val xa=max(0,(cx-142*size).toInt());val xb=min(ref.cols(),(cx+142*size).toInt());val ya=max(0,(top-50*size).toInt());val yb=min(ref.rows(),(top+350*size).toInt());val q=ChatLuongThe()
    if(xb<=xa || yb<=ya)return null to q
    val raw=roi(ref,xa,ya,xb,yb);val h=hsv(raw);val hp=bytes(h);h.release();val mw=raw.cols();val mh=raw.rows();val initial=maskVien(raw);val a=bytes(initial);initial.release()
    for(y in 0 until mh)for(x in 0 until mw){val j=(y*mw+x)*3;if((hp[j].toInt() and 255) in 35..85 && (hp[j+1].toInt() and 255)>70 && y+ya<top+25*size && x+xa>cx+45*size)a[y*mw+x]=0}
    fun profileX():DoubleArray {val ys=max(0,(top+65*size).toInt()-ya);val ye=min(mh,(top+245*size).toInt()-ya);return DoubleArray(mw){x->if(ye<=ys)0.0 else (ys until ye).count{a[it*mw+x].toInt()!=0}.toDouble()/(ye-ys)}}
    val p=profileX();val cuts=mutableListOf<Int>();var columns=true
    for(v in listOf(Triple(-125,-75,-98),Triple(100,141,123))) {
        val xs=(max(0,(cx+v.first*size).toInt()-xa) until min(mw,(cx+v.second*size).toInt()-xa)).toList()
        if(xs.isEmpty()){raw.release();return null to q}
        val c=xs.minWith(compareBy<Int>{p[it]}.thenBy{abs(it+xa-(cx+v.third*size))});cuts.add(c);columns=columns && p[c]<.15
    }
    for(y in 0 until mh)for(x in 0 until mw)if(x<cuts[0] || x>=cuts[1])a[y*mw+x]=0
    var split=true
    if(size==1.0){val l=max(0,(cx-95).toInt()-xa);val r=min(mw,(cx+123).toInt()-xa);val py=DoubleArray(mh){y->if(r<=l)0.0 else(l until r).count{a[y*mw+it].toInt()!=0}.toDouble()/(r-l)};val cy=mutableListOf<Int>()
        for(v in listOf(Triple(-35,-5,-18),Triple(280,307,296))){val ys=(max(0,(top+v.first).toInt()-ya) until min(mh,(top+v.second).toInt()-ya)).toList();if(ys.isEmpty()){raw.release();return null to q};val c=ys.minWith(compareBy<Int>{py[it]}.thenBy{abs(it+ya-(top+v.third))});cy.add(c);split=split && py[c]<.15}
        for(y in 0 until mh)if(y<cy[0] || y>=cy[1])java.util.Arrays.fill(a,y*mw,(y+1)*mw,0.toByte())
    }
    val mask=Mat(mh,mw,CvType.CV_8U);mask.put(0,0,a);val (labels,stats)=components(mask);mask.release()
    val cand=stats.withIndex().filter {(_,v)->val x=v[0]+xa;val y=v[1]+ya;val w=v[2];val hh=v[3];w>=160*size && w<=262*size && hh>=240*size && hh<=365*size && abs(x+w/2.0-cx)<=35*size && y>=top-48*size && y<=top+25*size && y+hh>=top+250*size && y+hh<=top+340*size}.maxWithOrNull(compareBy<IndexedValue<IntArray>>{it.value[4]}.thenBy{it.index})
    if(cand==null){labels.release();raw.release();return null to q}
    val v=cand.value;val b=Bien(xa+v[0],ya+v[1],xa+v[0]+v[2],ya+v[1]+v[3]);q.bien=b
    if(!columns || !split || b.l<=xa || b.r>=xb || b.t<=ya || b.b>=yb || b.t<visibleTop || b.b>visibleBottom){q.lyDo="bien_bi_cat_hoac_che";labels.release();raw.release();return null to q}
    val lab=IntArray(mw*mh);labels.get(0,0,lab);labels.release();val bw=b.r-b.l;val bh=b.b-b.t;val side=max(4,pyRound(bw*.06));val ys=pyRound(bh*.25);val ye=pyRound(bh*.85)
    val supports=listOf(0,bw-side).map{xx->(ys until ye).count {y->(xx until xx+side).any{x->lab[(b.t-ya+y)*mw+b.l-xa+x]==cand.index+1}}.toDouble()/(ye-ys)}
    q.supports=supports;q.saoDu=true;q.vienDu=supports.min()>=.2
    if(!q.vienDu){q.lyDo="chua_xac_minh_hai_vien";raw.release();return null to q}
    val (out,chuan)=canvas(ref,b,raw);raw.release();q.chuan=chuan;q.dayDu=true;q.lyDo="bien_day_du";q.kheCot=columns;q.kheHang=split
    return out to q
}
