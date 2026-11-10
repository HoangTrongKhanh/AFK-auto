package vn.afkauto.leoai.vision

/** Đứng yên chưa đủ: cần số tham chiếu, mốc đầu, đủ biên và các mặt khác nhau. */
fun xacMinhDanhSachNgan(cards:List<TheCan>,expected:Int?,top:Boolean):List<String>? {
    if(expected==null || expected<1 || !top || cards.size!=expected || cards.any{!it.q.dayDu})return null
    val faces=cards.map{matTheDanhSach(it.legacy)}
    return try {
        if(faces.indices.any{i -> faces.drop(i+1).any{giongMat(faces[i],it)>=CUNG_THE}})null
        else faces.map{sha256("(48, 48, 3)|u1".toByteArray()+bytes(it))}
    }finally{faces.forEach{it.release()}}
}
