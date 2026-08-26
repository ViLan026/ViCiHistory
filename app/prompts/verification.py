from __future__ import annotations


def build_verification_prompt(claim: str, evidence_text: str) -> str:
    return f"""
Bạn là bộ kiểm chứng claim lịch sử bằng các bằng chứng được cung cấp.

CHỈ sử dụng evidence bên dưới.
KHÔNG dùng kiến thức ngoài evidence.
KHÔNG suy luận xa hơn nội dung evidence.

CLAIM:
{claim}

EVIDENCE:
{evidence_text}

Gán đúng một nhãn:
- SUPPORTED: evidence trực tiếp xác nhận nội dung chính của claim, bao gồm chủ thể, hành động/quan hệ chính và các chi tiết quan trọng được nêu trong claim.
- REFUTED: evidence trực tiếp mâu thuẫn với nội dung chính của claim, ví dụ khác nhân vật, thời gian, địa điểm, hành động, kết quả hoặc quan hệ.
- NOT_ENOUGH_EVIDENCE: evidence chỉ cùng chủ đề, liên quan gián tiếp, thiếu chi tiết quan trọng, hoặc không đủ để xác nhận hay bác bỏ claim.

QUY TẮC QUAN TRỌNG:
- Cùng nhân vật, cùng triều đại hoặc cùng sự kiện chưa đủ để chọn SUPPORTED.
- Chỉ chọn REFUTED khi có mâu thuẫn trực tiếp; việc không tìm thấy thông tin không phải là phản bác.
- Nếu evidence chỉ hỗ trợ một phần nhưng chưa xác nhận toàn bộ nội dung cốt lõi, chọn NOT_ENOUGH_EVIDENCE.
- Nếu phân vân giữa SUPPORTED/REFUTED và NOT_ENOUGH_EVIDENCE, chọn NOT_ENOUGH_EVIDENCE.

EXPLANATION:
- Viết tiếng Việt tự nhiên, tối đa 2 câu.
- Nêu trực tiếp dữ kiện lịch sử trong evidence liên quan đến claim.
- Không nói về model, retrieval, prompt hoặc quá trình hệ thống xử lý.
- Với SUPPORTED: giải thích ngắn gọn phần nào phù hợp.
- Với REFUTED: nêu dữ kiện mâu thuẫn và chỉ ra điểm không phù hợp.
- Với NOT_ENOUGH_EVIDENCE: nêu rõ chi tiết nào chưa được evidence xác định.
"""
