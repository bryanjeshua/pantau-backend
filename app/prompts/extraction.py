def get_extraction_prompt(document_type: str) -> str:
    if document_type in ("apbd", "spj"):
        return """Kamu adalah sistem ekstraksi data keuangan pemerintah daerah Indonesia yang presisi.
Ekstrak SEMUA line item anggaran dari dokumen ini.
Untuk setiap item identifikasi: kode rekening, nama item, nilai anggaran, nilai realisasi (jika ada),
jenis (belanja/pendapatan/pembiayaan), dan sub-jenis (pegawai/barang_jasa/modal).
Jika informasi tidak tersedia gunakan null."""
    elif document_type == "procurement":
        return """Kamu adalah sistem ekstraksi data pengadaan pemerintah daerah Indonesia.
Ekstrak SEMUA transaksi pengadaan dari dokumen ini.
Untuk setiap transaksi identifikasi: nomor kontrak, nama vendor, NPWP vendor, alamat vendor,
deskripsi item, kategori, metode pengadaan, nilai kontrak,
tanggal kontrak, tanggal mulai/selesai pekerjaan, tanggal SPJ, dan tanggal pembayaran.
Format tanggal: YYYY-MM-DD. Jika tidak tersedia gunakan null."""
    return "Ekstrak semua data keuangan dari dokumen ini dalam format JSON."


def get_extraction_schema(document_type: str) -> dict:
    if document_type in ("apbd", "spj"):
        return {
            "type": "object",
            "properties": {
                "opd_name": {"type": "string", "nullable": True},
                "fiscal_year": {"type": "integer", "nullable": True},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_code": {"type": "string", "nullable": True},
                            "item_name": {"type": "string"},
                            "budget_amount": {"type": "number", "nullable": True},
                            "realized_amount": {"type": "number", "nullable": True},
                            "item_type": {
                                "type": "string",
                                "enum": ["belanja", "pendapatan", "pembiayaan"],
                                "nullable": True,
                            },
                            "sub_type": {"type": "string", "nullable": True},
                        },
                        "required": ["item_name"],
                    },
                },
            },
            "required": ["items"],
        }
    elif document_type == "procurement":
        return {
            "type": "object",
            "properties": {
                "transactions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "contract_number": {"type": "string", "nullable": True},
                            "vendor_name": {"type": "string"},
                            "vendor_npwp": {"type": "string", "nullable": True},
                            "vendor_address": {"type": "string", "nullable": True},
                            "item_description": {"type": "string"},
                            "category": {
                                "type": "string",
                                "enum": ["konstruksi", "konsultansi", "barang", "jasa_lainnya"],
                                "nullable": True,
                            },
                            "procurement_method": {
                                "type": "string",
                                "enum": ["tender", "penunjukan_langsung", "pengadaan_langsung"],
                                "nullable": True,
                            },
                            "contract_value": {"type": "number", "nullable": True},
                            "contract_date": {"type": "string", "nullable": True},
                            "work_start_date": {"type": "string", "nullable": True},
                            "work_end_date": {"type": "string", "nullable": True},
                            "spj_date": {"type": "string", "nullable": True},
                            "payment_date": {"type": "string", "nullable": True},
                        },
                        "required": ["vendor_name", "item_description"],
                    },
                },
            },
            "required": ["transactions"],
        }
    return {"type": "object", "properties": {"data": {"type": "string"}}, "required": ["data"]}
