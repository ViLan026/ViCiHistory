from __future__ import annotations

from app.config import settings


def build_claim_extraction_prompt(content: str) -> str:
    return f"""
Bạn là bộ trích xuất phát biểu lịch sử cho hệ thống hỗ trợ tìm nguồn sử liệu.

NHIỆM VỤ:
Phân tích nội dung đầu vào và trích xuất các phát biểu lịch sử phù hợp để dùng làm truy vấn tìm nguồn sử liệu.

Mỗi kết quả gồm:
- source_text: đoạn nguyên văn trong nội dung đầu vào làm cơ sở cho claim.
- claim: phát biểu lịch sử hoàn chỉnh, đủ ngữ cảnh và phù hợp cho semantic retrieval.

MỤC TIÊU:
Không tối ưu atomicity. Ưu tiên:
1. Faithfulness: claim phải giữ đúng ý nghĩa của nội dung đầu vào.
2. Sufficient context: claim phải giữ đủ ngữ cảnh để xác định đúng sự kiện khi truy xuất.
3. Event coherence: các thông tin cùng mô tả một sự kiện hoặc một quan hệ lịch sử nên được giữ cùng nhau.
4. Retrieval usefulness: claim phải chứa những thông tin quan trọng giúp tìm đúng đoạn sử liệu.

QUY TẮC TRÍCH XUẤT:

1. Không ép một claim chỉ chứa một fact.
Một claim có thể chứa nhiều thông tin về nhân vật, hành động, thời gian, địa điểm, lực lượng, nguyên nhân hoặc kết quả nếu các thông tin đó cùng mô tả một sự kiện hoặc một nội dung lịch sử thống nhất.

Ví dụ:
"Trần Quốc Tuấn chỉ huy quân Đại Việt đánh bại quân Nguyên tại Bạch Đằng năm 1288."

Phải giữ thành một claim hoàn chỉnh, không tách thành các fact nhỏ như:
- "Trần Quốc Tuấn chỉ huy quân Đại Việt."
- "Quân Đại Việt đánh bại quân Nguyên."
- "Trận đánh diễn ra tại Bạch Đằng."
- "Trận đánh diễn ra năm 1288."

2. Chỉ tách khi nội dung chứa các sự kiện hoặc phát biểu tương đối độc lập.
Nếu việc tách không làm mất quan hệ thời gian, nguyên nhân, kết quả hoặc ngữ cảnh quan trọng thì có thể tách.
Nếu việc tách làm mất thông tin cần thiết để xác định đúng sự kiện, phải giữ thông tin đó trong claim.

3. Giữ quan hệ giữa các câu khi cần thiết.
Nếu một câu phụ thuộc vào câu trước thông qua các từ như:
- "sau đó";
- "trước đó";
- "tiếp theo";
- "vì vậy";
- "do đó";
- "sự kiện này";
- "trận đánh đó";
- "ông";
- "ngài";
hãy đưa ngữ cảnh cần thiết từ câu trước vào claim.

Ví dụ:
Input:
"Lê Hoàn lên ngôi năm 980. Sau đó ông đem quân đánh Chiêm Thành."

Claim cho sự kiện thứ hai nên là:
"Sau khi lên ngôi năm 980, Lê Hoàn đem quân đánh Chiêm Thành."

Không được rút thành:
"Lê Hoàn đem quân đánh Chiêm Thành."

vì như vậy làm mất quan hệ thời gian có trong nội dung đầu vào.

4. Decontextualize vừa đủ.
Claim phải hiểu được khi dùng độc lập làm truy vấn.
Thay đại từ hoặc cụm phụ thuộc ngữ cảnh bằng thực thể cụ thể nếu thực thể đó được xác định rõ trong nội dung đầu vào.
Không loại bỏ các thông tin ngữ cảnh có tác dụng xác định sự kiện.

5. Không bổ sung kiến thức bên ngoài.
Không tự thêm hoặc sửa:
- nhân vật;
- thời gian;
- địa điểm;
- chức vụ;
- lực lượng;
- nguyên nhân;
- kết quả;
- quan hệ giữa các sự kiện;
nếu thông tin đó không có trong nội dung đầu vào.

6. source_text phải phản ánh đầy đủ phần văn bản dùng để tạo claim.
Nếu claim cần thông tin từ nhiều câu liên tiếp để giữ đủ ngữ cảnh, source_text có thể chứa nhiều câu liên tiếp.
source_text của các claim khác nhau được phép chồng lấp nhau.

7. source_text phải:
- được sao chép nguyên văn từ nội dung đầu vào;
- là một đoạn liên tục;
- không sửa từ;
- không viết lại;
- không decontextualize;
- không ghép các đoạn không liên tiếp.

8. Không trích xuất:
- cảm xúc;
- câu hỏi tu từ;
- nhận xét chủ quan;
- lời bình;
- các đánh giá như "vĩ đại nhất", "hào hùng nhất", "kiệt xuất nhất";
- các claim vụn hoặc hiển nhiên không có giá trị tìm nguồn.

9. Giữ thứ tự xuất hiện trong nội dung.
Không tạo claim trùng nhau.
Tối đa {settings.MAX_CLAIMS_PER_INPUT} claim.

10. Khi cân nhắc có nên tách một phát biểu hay không, hãy hỏi:
"Nếu tách ra, claim mới có mất một quan hệ lịch sử hoặc ngữ cảnh quan trọng cần thiết cho việc tìm đúng nguồn hay không?"
Nếu có, không tách.

VÍ DỤ 1:

Input:
"Trần Quốc Tuấn chỉ huy quân Đại Việt đánh bại quân Nguyên tại Bạch Đằng năm 1288."

Output:
{{
  "claims": [
    {{
      "source_text": "Trần Quốc Tuấn chỉ huy quân Đại Việt đánh bại quân Nguyên tại Bạch Đằng năm 1288.",
      "claim": "Trần Quốc Tuấn chỉ huy quân Đại Việt đánh bại quân Nguyên tại Bạch Đằng năm 1288."
    }}
  ]
}}

VÍ DỤ 2:

Input:
"Lê Hoàn lên ngôi năm 980. Sau đó ông đem quân đánh Chiêm Thành."

Output:
{{
  "claims": [
    {{
      "source_text": "Lê Hoàn lên ngôi năm 980.",
      "claim": "Lê Hoàn lên ngôi năm 980."
    }},
    {{
      "source_text": "Lê Hoàn lên ngôi năm 980. Sau đó ông đem quân đánh Chiêm Thành.",
      "claim": "Sau khi lên ngôi năm 980, Lê Hoàn đem quân đánh Chiêm Thành."
    }}
  ]
}}

VÍ DỤ 3:

Input:
"Năm 1288, quân Nguyên tiến vào Đại Việt. Trần Quốc Tuấn tổ chức trận địa trên sông Bạch Đằng và sau đó đánh bại quân Nguyên."

Output:
{{
  "claims": [
    {{
      "source_text": "Năm 1288, quân Nguyên tiến vào Đại Việt.",
      "claim": "Quân Nguyên tiến vào Đại Việt năm 1288."
    }},
    {{
      "source_text": "Năm 1288, quân Nguyên tiến vào Đại Việt. Trần Quốc Tuấn tổ chức trận địa trên sông Bạch Đằng và sau đó đánh bại quân Nguyên.",
      "claim": "Trong cuộc chiến với quân Nguyên năm 1288, Trần Quốc Tuấn tổ chức trận địa trên sông Bạch Đằng và đánh bại quân Nguyên."
    }}
  ]
}}

NỘI DUNG CẦN XỬ LÝ:
\"\"\"{content}\"\"\"

Output JSON:
"""