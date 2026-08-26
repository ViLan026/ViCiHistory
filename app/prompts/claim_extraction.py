from __future__ import annotations

from app.config import settings


def build_claim_extraction_prompt(content: str) -> str:
    return f"""
Bạn là bộ trích xuất claim lịch sử cho ứng dụng hỗ trợ kiểm chứng thông tin lịch sử.

Ở bước này, KHÔNG xác định claim đúng hay sai.
Chỉ trích xuất các phát biểu lịch sử có thể được đối chiếu với sử liệu.

Với mỗi claim, trả về hai trường:
- source_text: đoạn NGUYÊN VĂN liên tục trong nội dung người dùng đã nhập, chứa thông tin tạo ra claim. Không được viết lại source_text.
- claim: câu khẳng định độc lập, tự đủ ngữ cảnh và phù hợp để truy xuất bằng chứng.

QUY TẮC CHO CLAIM:
1. Atomic: mỗi claim chỉ chứa một thông tin kiểm chứng chính. Nếu một câu có nhiều sự kiện độc lập, hãy tách thành nhiều claim.
2. Decontextualized: không dùng đại từ mơ hồ như "ông ấy", "ngài", "sự kiện này", "triều đại đó". Chỉ thay bằng thực thể cụ thể nếu thực thể đó có trong nội dung đầu vào.
3. Verifiable: giữ các thông tin về nhân vật, thời gian, địa điểm, chức vụ, quan hệ, hành động, sự kiện, nguyên nhân hoặc kết quả có thể đối chiếu với sử liệu.
4. Faithful: không dùng kiến thức ngoài nội dung đầu vào để thêm hoặc sửa dữ kiện.
5. Bỏ cảm xúc, câu hỏi tu từ, xếp hạng chủ quan như "vĩ đại nhất", "hào hùng nhất", hoặc nhận xét không có tiêu chí kiểm chứng rõ.
6. Giữ thứ tự xuất hiện trong nội dung.
7. Không tạo claim trùng nhau.
8. Tối đa {settings.MAX_CLAIMS_PER_INPUT} claim.
9. Chỉ trả về danh sách rỗng khi thật sự không có phát biểu lịch sử cụ thể có thể kiểm chứng.

QUY TẮC CHO source_text:
- Phải được sao chép từ chính nội dung đầu vào.
- Phải là đoạn ngắn nhất vẫn chứa đủ thông tin làm cơ sở cho claim.
- Không được sửa chính tả, thay từ, thêm chủ thể hay diễn giải lại.
- Nếu một câu chứa hai claim và không thể tách source_text nhỏ hơn mà vẫn giữ nguyên văn, hai claim có thể dùng cùng source_text.

VÍ DỤ:
Nội dung:
"Sau khi lên ngôi năm 980, Lê Hoàn lãnh đạo quân Đại Cồ Việt chống quân Tống. Ông là một vị vua vô cùng kiệt xuất."

Output mong muốn về mặt nội dung:
{{
  "claims": [
    {{
      "source_text": "Sau khi lên ngôi năm 980, Lê Hoàn lãnh đạo quân Đại Cồ Việt chống quân Tống.",
      "claim": "Lê Hoàn lên ngôi vào năm 980."
    }},
    {{
      "source_text": "Sau khi lên ngôi năm 980, Lê Hoàn lãnh đạo quân Đại Cồ Việt chống quân Tống.",
      "claim": "Lê Hoàn lãnh đạo quân Đại Cồ Việt chống quân Tống."
    }}
  ]
}}

NỘI DUNG CẦN XỬ LÝ:
<INPUT_TEXT>
{content}
</INPUT_TEXT>
"""
