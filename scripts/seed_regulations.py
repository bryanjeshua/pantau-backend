"""
Seed regulation chunks into pgvector.
Run: cd backend && py -m scripts.seed_regulations
"""
import asyncio
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.services.gemini_service import embed_text

REGULATIONS = [
    {
        "peraturan_number": "PP Nomor 12 Tahun 2019",
        "full_title": "Pengelolaan Keuangan Daerah",
        "category": "keuangan_daerah",
        "effective_date": "2019-03-12",
        "chunks": [
            {
                "pasal": "Pasal 3",
                "content": (
                    "Keuangan Daerah dikelola secara tertib, taat pada peraturan perundang-undangan, "
                    "efisien, ekonomis, efektif, transparan, dan bertanggung jawab dengan memperhatikan "
                    "rasa keadilan, kepatutan, manfaat untuk masyarakat, serta taat pada ketentuan "
                    "peraturan perundang-undangan."
                ),
                "topic_tags": ["prinsip umum", "tata kelola keuangan", "transparansi"],
            },
            {
                "pasal": "Pasal 51",
                "content": (
                    "Pengguna Anggaran/Kuasa Pengguna Anggaran wajib menyelenggarakan penatausahaan "
                    "atas penerimaan dan/atau pengeluaran yang telah dianggarkan dalam APBD. "
                    "SPJ disusun berdasarkan bukti-bukti transaksi yang sah dan lengkap. "
                    "Dokumen SPJ harus disampaikan paling lambat tanggal 10 bulan berikutnya."
                ),
                "topic_tags": ["SPJ", "penatausahaan", "pengguna anggaran", "pertanggungjawaban"],
            },
            {
                "pasal": "Pasal 55",
                "content": (
                    "Setiap pengeluaran belanja atas beban APBD harus didukung dengan bukti yang lengkap "
                    "dan sah. Bukti sebagaimana dimaksud harus mendapat pengesahan oleh pejabat yang "
                    "berwenang dan bertanggung jawab atas kebenaran material yang timbul dari penggunaan "
                    "bukti yang bersangkutan. Pengeluaran tanpa bukti yang sah diklasifikasikan sebagai "
                    "pengeluaran tidak dapat dipertanggungjawabkan."
                ),
                "topic_tags": ["bukti pengeluaran", "SPJ", "belanja daerah", "akuntabilitas"],
            },
            {
                "pasal": "Pasal 98",
                "content": (
                    "Belanja Daerah dipergunakan dalam rangka mendanai pelaksanaan urusan pemerintahan "
                    "yang menjadi kewenangan daerah. Belanja Daerah diklasifikasikan menurut urusan "
                    "pemerintahan daerah, organisasi, program, kegiatan, sub kegiatan, jenis belanja, "
                    "objek belanja, dan rincian objek belanja sesuai dengan ketentuan peraturan "
                    "perundang-undangan di bidang pengelolaan keuangan negara."
                ),
                "topic_tags": ["belanja daerah", "klasifikasi anggaran", "APBD"],
            },
            {
                "pasal": "Pasal 100",
                "content": (
                    "Belanja pegawai merupakan belanja kompensasi dalam bentuk gaji dan tunjangan, "
                    "serta penghasilan lainnya yang diberikan kepada Kepala Daerah, DPRD, serta "
                    "Pegawai ASN yang ditetapkan sesuai dengan ketentuan peraturan perundang-undangan. "
                    "Belanja pegawai tidak boleh melebihi 30% dari total belanja APBD kecuali dengan "
                    "persetujuan Menteri Dalam Negeri."
                ),
                "topic_tags": ["belanja pegawai", "gaji", "tunjangan", "ASN"],
            },
            {
                "pasal": "Pasal 104",
                "content": (
                    "Belanja Barang dan Jasa digunakan untuk menganggarkan pengadaan barang/jasa yang "
                    "nilai manfaatnya kurang dari 12 (dua belas) bulan, termasuk barang atau jasa yang "
                    "akan diserahkan atau dijual kepada masyarakat/pihak ketiga dalam rangka "
                    "melaksanakan program dan kegiatan pemerintah daerah. Belanja ini mencakup belanja "
                    "bahan habis pakai, jasa kantor, premi asuransi, perawatan kendaraan, sewa, "
                    "perjalanan dinas, dan honorarium."
                ),
                "topic_tags": ["belanja barang jasa", "pengadaan", "anggaran operasional"],
            },
        ],
    },
    {
        "peraturan_number": "Perpres Nomor 16 Tahun 2018",
        "full_title": "Pengadaan Barang/Jasa Pemerintah",
        "category": "pengadaan",
        "effective_date": "2018-03-22",
        "chunks": [
            {
                "pasal": "Pasal 4",
                "content": (
                    "Pengadaan Barang/Jasa bertujuan untuk: menghasilkan barang/jasa yang tepat dari "
                    "setiap uang yang dibelanjakan diukur dari aspek kualitas, jumlah, waktu, biaya, "
                    "lokasi, dan penyedia; meningkatkan penggunaan produk dalam negeri; meningkatkan "
                    "peran serta Usaha Mikro, Usaha Kecil, dan Usaha Menengah; mendorong pemerataan "
                    "ekonomi; mendorong Pengadaan Berkelanjutan."
                ),
                "topic_tags": ["tujuan pengadaan", "prinsip pengadaan", "UMKM"],
            },
            {
                "pasal": "Pasal 38 ayat 1",
                "content": (
                    "Pengadaan Langsung Barang/Pekerjaan Konstruksi/Jasa Lainnya dilakukan oleh "
                    "1 (satu) Pejabat Pengadaan. Pengadaan Langsung dapat dilakukan terhadap Pengadaan "
                    "Barang/Jasa yang bernilai paling banyak Rp200.000.000 (dua ratus juta rupiah). "
                    "Pengadaan yang nilainya melebihi Rp200 juta WAJIB dilakukan melalui mekanisme "
                    "tender/seleksi dan tidak dapat dipecah untuk menghindari tender."
                ),
                "topic_tags": ["pengadaan langsung", "batas nilai", "threshold", "Rp200 juta"],
            },
            {
                "pasal": "Pasal 38 ayat 2",
                "content": (
                    "Pengadaan Langsung Jasa Konsultansi dilakukan oleh 1 (satu) Pejabat Pengadaan "
                    "dan dapat dilakukan terhadap Pengadaan Jasa Konsultansi yang bernilai paling "
                    "banyak Rp100.000.000 (seratus juta rupiah). Jasa Konsultansi dengan nilai di "
                    "atas Rp100 juta harus dilakukan melalui mekanisme seleksi."
                ),
                "topic_tags": ["pengadaan langsung", "jasa konsultansi", "batas nilai", "Rp100 juta"],
            },
            {
                "pasal": "Pasal 38 ayat 3",
                "content": (
                    "Penunjukan Langsung dilakukan terhadap 1 (satu) Penyedia dalam kondisi tertentu. "
                    "Kondisi tertentu meliputi: keadaan darurat; pekerjaan yang hanya dapat dilakukan "
                    "oleh 1 penyedia karena kompleksitas atau keahlian khusus; pekerjaan yang bersifat "
                    "rahasia negara; barang/jasa yang harganya telah ditetapkan pemerintah. "
                    "Penunjukan langsung di luar kondisi tersebut merupakan pelanggaran."
                ),
                "topic_tags": ["penunjukan langsung", "kondisi darurat", "monopoli", "pelanggaran pengadaan"],
            },
            {
                "pasal": "Pasal 45",
                "content": (
                    "Tender/Seleksi dilakukan untuk Pengadaan Barang/Pekerjaan Konstruksi/Jasa Lainnya "
                    "yang bernilai di atas Rp200.000.000 (dua ratus juta rupiah) dan Jasa Konsultansi "
                    "yang bernilai di atas Rp100.000.000 (seratus juta rupiah). Tender wajib dilakukan "
                    "melalui Sistem Pengadaan Secara Elektronik (SPSE). Pokja Pemilihan bertanggung "
                    "jawab atas proses tender yang transparan dan akuntabel."
                ),
                "topic_tags": ["tender", "seleksi", "SPSE", "batas nilai tender", "Pokja"],
            },
            {
                "pasal": "Pasal 67",
                "content": (
                    "Pelaku Usaha yang terbukti melakukan persekongkolan dengan sesama Pelaku Usaha "
                    "dan/atau dengan Pejabat Pengadaan dalam Pengadaan Barang/Jasa dapat dikenakan "
                    "sanksi: pembatalan kontrak; pembayaran denda; pencantuman dalam Daftar Hitam "
                    "LKPP; gugatan perdata; pelaporan pidana. Persekongkolan meliputi pengaturan harga, "
                    "dokumen penawaran yang dibuat oleh pihak yang sama, dan hubungan afiliasi vendor."
                ),
                "topic_tags": ["persekongkolan", "kolusi", "sanksi", "daftar hitam", "afiliasi vendor"],
            },
            {
                "pasal": "Pasal 25",
                "content": (
                    "Pemecahan paket Pengadaan Barang/Jasa dilarang dengan maksud untuk menghindari "
                    "Tender/Seleksi. Indikasi pemecahan paket antara lain: beberapa paket memiliki "
                    "spesifikasi yang sama; kontrak dibuat dalam waktu berdekatan; total nilai paket-"
                    "paket tersebut melebihi threshold tender. PA/KPA yang melakukan pemecahan paket "
                    "untuk menghindari tender dapat dikenai sanksi administratif."
                ),
                "topic_tags": ["pemecahan paket", "split contract", "menghindari tender", "pelanggaran"],
            },
        ],
    },
    {
        "peraturan_number": "Permendagri Nomor 77 Tahun 2020",
        "full_title": "Pedoman Teknis Pengelolaan Keuangan Daerah",
        "category": "keuangan_daerah",
        "effective_date": "2020-12-31",
        "chunks": [
            {
                "pasal": "Pasal 1 angka 9",
                "content": (
                    "Surat Pertanggungjawaban (SPJ) adalah dokumen yang menjelaskan penggunaan dana "
                    "yang bersumber dari APBD. SPJ harus dilampiri dengan bukti-bukti yang sah meliputi "
                    "kuitansi, nota/faktur, Surat Perintah Perjalanan Dinas (SPPD), berita acara "
                    "serah terima, dan dokumen pendukung lainnya yang ditetapkan oleh pejabat "
                    "pengelola keuangan daerah."
                ),
                "topic_tags": ["SPJ", "pertanggungjawaban", "bukti transaksi", "kuitansi"],
            },
            {
                "pasal": "Pasal 119",
                "content": (
                    "Standar Harga Satuan Regional (SHSR) merupakan batas tertinggi harga satuan yang "
                    "ditetapkan oleh Gubernur untuk digunakan sebagai acuan dalam penyusunan RKA-SKPD "
                    "dan pelaksanaan pengadaan barang/jasa di lingkungan pemerintah daerah. Pengadaan "
                    "yang harga satuannya melebihi SHSR dianggap tidak wajar dan harus mendapatkan "
                    "persetujuan khusus disertai justifikasi tertulis. Pelanggaran SHSR merupakan "
                    "indikasi kerugian keuangan daerah."
                ),
                "topic_tags": ["SHSR", "standar harga satuan", "harga wajar", "markup harga"],
            },
            {
                "pasal": "Pasal 166",
                "content": (
                    "Perjalanan Dinas dalam kota dan luar kota dianggarkan dalam belanja SKPD. "
                    "Biaya Perjalanan Dinas meliputi: uang harian, biaya transport, biaya penginapan, "
                    "dan biaya representasi sesuai standar yang ditetapkan Kepala Daerah. Perjalanan "
                    "Dinas harus dilengkapi SPPD yang ditandatangani pejabat berwenang. Perjalanan "
                    "Dinas fiktif atau kelebihan pembayaran merupakan kerugian keuangan negara."
                ),
                "topic_tags": ["perjalanan dinas", "SPPD", "uang harian", "perjalanan fiktif"],
            },
            {
                "pasal": "Pasal 168",
                "content": (
                    "Pembayaran honorarium kepada ASN hanya dapat diberikan kepada pegawai yang "
                    "secara nyata terlibat dan melaksanakan kegiatan. Pembayaran harus berdasarkan SK "
                    "pejabat yang berwenang dan tidak boleh diberikan untuk kegiatan yang merupakan "
                    "tugas pokok dan fungsi (tupoksi) pegawai. Besaran honorarium mengacu pada standar "
                    "biaya yang ditetapkan oleh Kepala Daerah. Pembayaran honorarium ganda untuk "
                    "kegiatan yang sama dilarang."
                ),
                "topic_tags": ["honorarium", "ASN", "tupoksi", "pembayaran ganda", "standar biaya"],
            },
            {
                "pasal": "Pasal 200",
                "content": (
                    "Pengadaan barang/jasa yang tidak melalui mekanisme yang ditetapkan merupakan "
                    "pelanggaran prinsip akuntabilitas dan transparansi. Setiap penyimpangan harus "
                    "dilaporkan kepada Aparat Pengawas Intern Pemerintah (APIP). APIP wajib menindak-"
                    "lanjuti setiap laporan penyimpangan dalam pengelolaan keuangan daerah."
                ),
                "topic_tags": ["pelanggaran pengadaan", "APIP", "akuntabilitas", "pelaporan"],
            },
            {
                "pasal": "Pasal 145",
                "content": (
                    "Realisasi belanja yang melebihi pagu anggaran yang ditetapkan dalam DPA-SKPD "
                    "merupakan pengeluaran tidak sah. Kelebihan realisasi belanja harus segera "
                    "disetorkan ke Kas Daerah. PA/KPA yang menyetujui pengeluaran melebihi pagu "
                    "anggaran bertanggung jawab secara pribadi atas kelebihan tersebut."
                ),
                "topic_tags": ["realisasi belanja", "pagu anggaran", "kelebihan belanja", "DPA"],
            },
        ],
    },
]


def _vec_str(embedding: list[float]) -> str:
    return f"[{','.join(str(x) for x in embedding)}]"


async def seed():
    async with AsyncSessionLocal() as db:
        for reg in REGULATIONS:
            # Check if regulation already exists
            result = await db.execute(
                text("SELECT id FROM regulations WHERE peraturan_number = :pn"),
                {"pn": reg["peraturan_number"]},
            )
            existing = result.fetchone()

            if existing:
                regulation_id = str(existing.id)
                print(f"Skipping {reg['peraturan_number']} (already exists)")
            else:
                result = await db.execute(
                    text("""
                        INSERT INTO regulations
                            (id, peraturan_number, full_title, category, effective_date)
                        VALUES
                            (gen_random_uuid(), :pn, :title, :cat, :eff)
                        RETURNING id
                    """),
                    {
                        "pn": reg["peraturan_number"],
                        "title": reg["full_title"],
                        "cat": reg["category"],
                        "eff": date.fromisoformat(reg["effective_date"]),
                    },
                )
                regulation_id = str(result.fetchone().id)
                await db.commit()
                print(f"Created regulation: {reg['peraturan_number']} (id={regulation_id})")

            # Delete existing chunks for this regulation (for idempotency)
            await db.execute(
                text("DELETE FROM regulation_chunks WHERE regulation_id = :rid"),
                {"rid": regulation_id},
            )
            await db.commit()

            # Insert chunks with embeddings
            chunks = reg["chunks"]
            for i, chunk in enumerate(chunks, 1):
                print(f"  Embedding {chunk['pasal']} ({i}/{len(chunks)})...")
                embedding = embed_text(chunk["content"], task_type="retrieval_document")

                await db.execute(
                    text(
                        "INSERT INTO regulation_chunks "
                        "(id, regulation_id, peraturan_number, pasal, content, embedding, topic_tags) "
                        "VALUES (gen_random_uuid(), :rid, :pn, :pasal, :content, CAST(:emb AS vector), :tags)"
                    ),
                    {
                        "rid": regulation_id,
                        "pn": reg["peraturan_number"],
                        "pasal": chunk["pasal"],
                        "content": chunk["content"],
                        "emb": _vec_str(embedding),
                        "tags": chunk["topic_tags"],
                    },
                )

            # Update chunk_count
            await db.execute(
                text("""
                    UPDATE regulations
                    SET chunk_count = :count, indexed_at = now()
                    WHERE id = :rid
                """),
                {"count": len(chunks), "rid": regulation_id},
            )
            await db.commit()
            print(f"  Indexed {len(chunks)} chunks for {reg['peraturan_number']}")

    print("\nDone! Regulation seeding complete.")


if __name__ == "__main__":
    asyncio.run(seed())
