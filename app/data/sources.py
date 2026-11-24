from __future__ import annotations


HISTORICAL_SOURCES = {
    "Đại Việt Sử Ký Toàn Thư": {
        "source_id": "dvsk",
        "object_key": "books/DVSK.pdf",
    },
    "Khâm Định Việt Sử Thông Giám Cương Mục": {
        "source_id": "kdvstgcm",
        "object_key": "books/KDVSTGCM.pdf",
    },
    "Việt Sử Toàn Thư": {
        "source_id": "vstt",
        "object_key": "books/VSTT.pdf",
    },
    # "Vương Triều Trần (1226-1400)": {
    #     "source_id": "vtt",
    #     "object_key": "books/VTT.pdf",
    #     "offset": 2,
    # },
    "LỊCH SỪ VIỆT NAM - TẬP 1": {
        "source_id": "lsvn01",
        "object_key": "books/LSVN_01.pdf",
        "offset": 2,
    },
    "LỊCH SỪ VIỆT NAM - TẬP 2": {
        "source_id": "lsvn02",
        "object_key": "books/LSVN_02.pdf",
        "offset": -1,
    },
    "LỊCH SỪ VIỆT NAM - TẬP 3": {
        "source_id": "lsvn03",
        "object_key": "books/LSVN_03.pdf",
    },
    "LỊCH SỪ VIỆT NAM - TẬP 4": {
        "source_id": "lsvn04",
        "object_key": "books/LSVN_04.pdf",
        "offset": 1,
    },
    "LỊCH SỪ VIỆT NAM - TẬP 5": {
        "source_id": "lsvn05",
        "object_key": "books/LSVN_05.pdf",
        "offset": 1,
    },
    "LỊCH SỪ VIỆT NAM - TẬP 6": {
        "source_id": "lsvn06",
        "object_key": "books/LSVN_06.pdf",
        "offset": 1,
    },
    "LỊCH SỪ VIỆT NAM - TẬP 7": {
        "source_id": "lsvn07",
        "object_key": "books/LSVN_07.pdf",
    },
    "LỊCH SỪ VIỆT NAM - TẬP 8": {
        "source_id": "lsvn08",
        "object_key": "books/LSVN_08.pdf",
    },
    "LỊCH SỪ VIỆT NAM - TẬP 9": {
        "source_id": "lsvn09",
        "object_key": "books/LSVN_09.pdf",
    },
    "LỊCH SỪ VIỆT NAM - TẬP 10": {
        "source_id": "lsvn10",
        "object_key": "books/LSVN_10.pdf",
    },
    "LỊCH SỪ VIỆT NAM - TẬP 11": {
        "source_id": "lsvn11",
        "object_key": "books/LSVN_11.pdf",
    },
    "LỊCH SỪ VIỆT NAM - TẬP 12": {
        "source_id": "lsvn12",
        "object_key": "books/LSVN_12.pdf",
        "offset": 2,
    },
    "LỊCH SỪ VIỆT NAM - TẬP 13": {
        "source_id": "lsvn13",
        "object_key": "books/LSVN_13.pdf",
        "offset": 2,
    },
    "LỊCH SỪ VIỆT NAM - TẬP 14": {
        "source_id": "lsvn14",
        "object_key": "books/LSVN_14.pdf",
        "offset": 2,
    },
    "LỊCH SỪ VIỆT NAM - TẬP 15": {
        "source_id": "lsvn15",
        "object_key": "books/LSVN_15.pdf",
        "offset": 2,
    }
    }


SOURCE_BY_ID = {
    source["source_id"]: source
    for source in HISTORICAL_SOURCES.values()
}


def map_source_pages_to_pdf_pages(
    pages: list[int],
    source_id: str | None = None,
    book_name: str | None = None,
) -> list[int]:
    source = SOURCE_BY_ID.get(source_id) if source_id else None

    if source is None and book_name:
        source = HISTORICAL_SOURCES.get(book_name)

    if source is None:
        return []

    offset = int(source.get("offset", 0))
    return [page + offset for page in pages if page + offset >= 1]