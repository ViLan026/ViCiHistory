from __future__ import annotations

from app.config import settings



def build_claim_extraction_prompt(content: str) -> str:
    return f"""
Bạn là chuyên gia trích xuất các phát biểu lịch sử từ văn bản tiếng Việt để dùng làm truy vấn tìm nguồn sử liệu.

Mỗi kết quả gồm:

* source_text: đoạn nguyên văn trong input làm cơ sở cho claim.
* claim: phát biểu lịch sử hoàn chỉnh, đủ ngữ cảnh và phù hợp cho semantic retrieval.

QUY TẮC:

1. Đọc toàn bộ input và trích xuất đầy đủ các sự kiện lịch sử đáng kể. Không mặc định một đoạn văn chỉ tạo một claim.
2. Một đoạn có nhiều sự kiện tương đối độc lập thì phải tạo nhiều claim.
3. Không tách quá nhỏ. Các thông tin về nhân vật, thời gian, địa điểm, hành động, lực lượng, nguyên nhân hoặc kết quả có thể giữ cùng một claim nếu chúng cùng mô tả một sự kiện.
4. Nếu câu sau phụ thuộc câu trước qua các từ như "sau đó", "trước đó", "vì vậy", "sự kiện này", "ông", "vua", "họ"... phải đưa đủ ngữ cảnh cần thiết vào claim.
5. Claim phải hiểu được khi đứng độc lập. Thay đại từ bằng thực thể cụ thể nếu xác định được từ input.
6. Không bổ sung kiến thức bên ngoài hoặc tự sửa thông tin trong input.
7. source_text phải được sao chép nguyên văn, liên tục từ input. Có thể gồm nhiều câu và được phép chồng lấp giữa các claim.
8. Không trích xuất cảm xúc, câu hỏi tu từ, lời bình hoặc đánh giá chủ quan.
9. Giữ thứ tự xuất hiện, không tạo claim trùng nhau, tối đa {settings.MAX_CLAIMS_PER_INPUT} claim.

CÁCH QUYẾT ĐỊNH TÁCH:

* Nếu hai thông tin có thể được kiểm chứng độc lập và việc tách không làm mất ngữ cảnh quan trọng -> tách.
* Nếu các thông tin cùng mô tả một sự kiện và tách ra làm mất ngữ cảnh -> giữ chung.
* Trước khi trả kết quả, kiểm tra xem còn sự kiện đáng kể nào trong input chưa được tạo claim hay không.

VÍ DỤ 1:

Input:
"Lý Công Uẩn lên ngôi năm 1009. Năm 1010, ông quyết định dời đô từ Hoa Lư ra Đại La. Khi đến Đại La, nhà vua đổi tên nơi này thành Thăng Long."

Output:
{{
"claims": [
{{
"source_text": "Lý Công Uẩn lên ngôi năm 1009.",
"claim": "Lý Công Uẩn lên ngôi năm 1009."
}},
{{
"source_text": "Năm 1010, ông quyết định dời đô từ Hoa Lư ra Đại La.",
"claim": "Năm 1010, Lý Công Uẩn quyết định dời đô từ Hoa Lư ra Đại La."
}},
{{
"source_text": "Năm 1010, ông quyết định dời đô từ Hoa Lư ra Đại La. Khi đến Đại La, nhà vua đổi tên nơi này thành Thăng Long.",
"claim": "Sau khi dời đô từ Hoa Lư ra Đại La năm 1010, Lý Công Uẩn đổi tên Đại La thành Thăng Long."
}}
]
}}

VÍ DỤ 2:

Input:
"Năm 1285, quân Nguyên tiến vào Đại Việt. Trước sức tiến công của đối phương, triều đình nhà Trần rút khỏi Thăng Long. Sau đó quân Trần phản công tại Hàm Tử và Chương Dương. Các chiến thắng này góp phần buộc quân Nguyên phải rút khỏi Đại Việt."

Output:
{{
"claims": [
{{
"source_text": "Năm 1285, quân Nguyên tiến vào Đại Việt.",
"claim": "Quân Nguyên tiến vào Đại Việt năm 1285."
}},
{{
"source_text": "Năm 1285, quân Nguyên tiến vào Đại Việt. Trước sức tiến công của đối phương, triều đình nhà Trần rút khỏi Thăng Long.",
"claim": "Trước cuộc tiến công của quân Nguyên vào Đại Việt năm 1285, triều đình nhà Trần rút khỏi Thăng Long."
}},
{{
"source_text": "Sau đó quân Trần phản công tại Hàm Tử và Chương Dương.",
"claim": "Quân Trần phản công tại Hàm Tử và Chương Dương."
}},
{{
"source_text": "Sau đó quân Trần phản công tại Hàm Tử và Chương Dương. Các chiến thắng này góp phần buộc quân Nguyên phải rút khỏi Đại Việt.",
"claim": "Các chiến thắng của quân Trần tại Hàm Tử và Chương Dương góp phần buộc quân Nguyên rút khỏi Đại Việt."
}}
]
}}

VÍ DỤ 3:

Input:
"Năm 1288, Trần Quốc Tuấn bố trí cọc trên sông Bạch Đằng, nhử quân Nguyên vào trận địa rồi tổ chức tiến công khi thủy triều rút, khiến quân Nguyên thất bại."

Output:
{{
"claims": [
{{
"source_text": "Năm 1288, Trần Quốc Tuấn bố trí cọc trên sông Bạch Đằng, nhử quân Nguyên vào trận địa rồi tổ chức tiến công khi thủy triều rút, khiến quân Nguyên thất bại.",
"claim": "Năm 1288, Trần Quốc Tuấn bố trí cọc trên sông Bạch Đằng, nhử quân Nguyên vào trận địa và tổ chức tiến công khi thủy triều rút, khiến quân Nguyên thất bại."
}}
]
}}

YÊU CẦU ĐẦU RA:

* Chỉ trả về JSON hợp lệ.
* Không Markdown, không giải thích ngoài JSON.
* Nếu không có claim phù hợp, trả về {{"claims": []}}.
* Cấu trúc:
  {{
  "claims": [
  {{
  "source_text": "...",
  "claim": "..."
  }}
  ]
  }}

NỘI DUNG CẦN XỬ LÝ:
\"\"\"{content}\"\"\"

Output JSON:
"""