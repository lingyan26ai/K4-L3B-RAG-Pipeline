# Individual contribution report

## Thông tin

- Họ và tên: Võ Công Danh
- Mã học viên: 2A202602739
- Nhóm: Happy
- Repository/branch: `K4-L3B-RAG-Pipeline` / `main`

## Phần việc đã thực hiện

| Module/deliverable | Việc tôi trực tiếp làm | File/commit/PR | Trạng thái |
|---|---|---|---|
| Task 4–6 | Chia tài liệu thành chunks, index vào ChromaDB; xây dựng semantic search và BM25 trên cùng corpus. | `src/task4_chunking_indexing.py`, `src/task5_semantic_search.py`, `src/task6_lexical_search.py`; commit `f3ff594` | Done |

## Quyết định kỹ thuật quan trọng

- Dùng `BAAI/bge-m3` cục bộ và giữ ID, nguồn cho mỗi chunk; không cần API key. Đổi lại, embedding trên CPU mất thời gian.

## Kiểm thử và kết quả

- 4 contract test tập trung đã pass; index 224 chunks từ 8 tài liệu.
- Query `VinUni scholarship financial aid support`: semantic search và BM25 đều trả 3 kết quả hợp lệ (`top_k=3`).

## Điều còn hạn chế

- BM25 dựng lại index mỗi lượt hỏi; có thể cache để giảm độ trễ. Chưa đánh giá chất lượng trên toàn bộ golden dataset.

## Xác nhận đóng góp

Tôi xác nhận nội dung trên phản ánh đúng phần việc Task 4–6 của mình.

- Ngày: 25/9/2026
- Tên thành viên: Võ Công Danh
