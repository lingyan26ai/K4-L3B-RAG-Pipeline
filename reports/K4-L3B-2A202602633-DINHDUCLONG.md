# Individual contribution report

---

## Thông tin

- Họ và tên: Đinh Đức Long
- Mã học viên: 2A202602633
- Nhóm: Happy
- Repository/branch: `K4-L3B-RAG-Pipeline` / `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 7: Reranking (RRF) | Cài đặt thuật toán Reciprocal Rank Fusion (RRF) theo công thức `sum(1 / (k + rank))` với rank từ 1; fuse kết quả dense và BM25, deduplicate ID, chuẩn hóa score và đánh dấu retrieval_method="hybrid". | `src/task7_reranking.py` | Done |
| Task 8: PageIndex fallback | Cài đặt vectorless fallback qua PageIndex SDK, lưu/đọc cache document ID, xử lý ngoại lệ an toàn và mapping kết quả sang SearchResult chuẩn. | `src/task8_pageindex_vectorless.py` | Done |
| Task 9: Retrieval Pipeline & Fallback | Ghép nối toàn diện pipeline `retrieve()`: chạy dense + BM25, fuse RRF đúng 1 lần, kiểm tra điểm cosine gốc với fallback threshold; chịu lỗi provider bên ngoài không làm chatbot crash. | `src/task9_retrieval_pipeline.py` | Done |
| Calibration Threshold | Thiết kế kịch bản và thực nghiệm đo điểm cosine dense trên câu hỏi in-domain và out-of-domain để hiệu chỉnh ngưỡng fallback `SCORE_THRESHOLD = 0.55`. | `calibrate_threshold.py`, `calibration_result.json`, `.env` | Done |

## Quyết định kỹ thuật quan trọng

1. **Quyết định:** Sử dụng điểm cosine gốc từ dense search (thay vì RRF score) để kích hoạt fallback sang PageIndex.  
   **Lý do/evidence:** RRF score chỉ phản ánh thứ hạng tương đối giữa các danh sách sau khi fuse (`sum(1 / (k + rank))`) và bị chi phối bởi số lượng danh sách tham gia, không phản ánh độ tương đồng ngữ nghĩa thực sự giữa truy vấn và tài liệu. Điểm cosine gốc của dense search phản ánh trực tiếp độ tương đồng vector trong không gian nhúng. Thực nghiệm đo lường thực tế trên bộ câu hỏi in-domain cho điểm cosine trung bình là `0.7254` (thấp nhất `0.6203`), trong khi out-of-domain chỉ đạt trung bình `0.3943` (cao nhất `0.4799`). Ngưỡng `0.55` tạo ra ranh giới phân tách tuyệt đối giữa 2 nhóm.  
   **Trade-off:** Cần giữ lại điểm cosine gốc của kết quả dense đầu tiên trước khi hợp nhất RRF, nhưng đảm bảo fallback chỉ kích hoạt khi thực sự cần thiết, tránh gọi API ngoài gây tốn chi phí và tăng độ trễ.

2. **Quyết định:** Xây dựng cơ chế fail-safe cho PageIndex fallback và đảm bảo RRF chỉ fuse một lần duy nhất.  
   **Lý do/evidence:** PageIndex là dịch vụ đám mây bên thứ ba có nguy cơ gặp sự cố mạng, rate limit hoặc timeout. Tất cả các lời gọi đến PageIndex đều được bọc trong khối try-catch an toàn. Khi dịch vụ gặp sự cố hoặc thiếu API key, hàm `retrieve()` tự động trả về kết quả hybrid đã tính toán từ trước thay vì throw exception làm sập ứng dụng Streamlit (`app.py`). Đồng thời, RRF chỉ chạy duy nhất 1 lần để tối ưu thời gian phản hồi.  
   **Trade-off:** Khi fallback gặp sự cố, hệ thống sẽ sử dụng kết quả hybrid nội bộ (hoặc tầng generation sẽ thực hiện safe refusal nếu không đủ bằng chứng), chấp nhận thông tin có thể hạn chế hơn nhưng đảm bảo tính khả dụng (high availability) 100% của hệ thống.

## Kiểm thử và kết quả

- **Test hoặc query tôi đã dùng:**
  - Bộ unit/contract test: `pytest tests/test_contracts.py -v`. 15/15 bài test đều PASSED 100%, trong đó trực tiếp phụ trách và vượt qua:
    + `test_rrf_uses_rank_deduplicates_and_marks_hybrid`
    + `test_retrieve_uses_dense_score_for_fallback`
    + `test_retrieve_fuses_once_when_dense_is_confident`
    + `test_retrieve_survives_fallback_provider_error`
  - Thực nghiệm hiệu chỉnh fallback threshold với 7 câu hỏi in-domain (tuyển sinh, học bổng, biểu phí, điều kiện tiếng Anh VinUni) và 7 câu hỏi out-of-domain (công thức làm bánh, thủ tục cấp hộ chiếu, thể thao, địa lý...).
- **Kết quả trước/sau nếu có:**
  - *Trước:* Các file Task 7, 8, 9 chứa stub `NotImplementedError`, chạy test contract thất bại, chatbot chưa thể tích hợp luồng tìm kiếm lai (hybrid).
  - *Sau:* 15/15 contract tests pass thành công.
  - *Số liệu calibration thực nghiệm:*
    + In-domain: min = 0.6203, avg = 0.7254, max = 0.8120.
    + Out-of-domain: min = 0.3170, avg = 0.3943, max = 0.4799.
    + Ngưỡng tối ưu xác định: `SCORE_THRESHOLD = 0.55` (100% in-domain >= 0.62 > 0.55; 100% out-of-domain <= 0.48 < 0.55).
- **Lỗi đã phát hiện và cách xử lý:**
  - Lỗi tương thích bảng mã hiển thị tiếng Việt trên môi trường Windows (`cp1258` codec error) khi chạy calibration: đã cấu hình lại encoding stream sang UTF-8 và trích xuất dữ liệu đo đạc có cấu trúc ra file JSON.
  - Lỗi sập ứng dụng khi dịch vụ fallback bên ngoài bị gián đoạn: đã cô lập exception của dịch vụ ngoài, bổ sung xử lý trả kết quả an toàn.

## Điều còn hạn chế

- Một hạn chế cụ thể của phần tôi làm: Tính năng fallback PageIndex hiện phụ thuộc vào API key bên thứ ba. Nếu không có key hoặc tài liệu chưa được upload lên PageIndex, fallback sẽ trả về rỗng và dựa vào hybrid nội bộ.
- Nếu có thêm thời gian, thay đổi đầu tiên tôi sẽ thực hiện: Tích hợp thêm mô hình Cross-Encoder Re-ranker (ví dụ `bge-reranker-base`) chạy cục bộ sau bước RRF để so sánh độ chính xác và đánh giá sự cải thiện về thứ hạng tài liệu liên quan.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc của mình và có thể giải thích hoặc chạy lại trong buổi demo.

- Ngày: 25/09/2026
- Tên thành viên: Đinh Đức Long
