# Báo cáo đóng góp cá nhân — Hà Anh Tuấn

- Mã học viên: **Chưa được cung cấp; thành viên tự bổ sung trước khi nộp.**
- Nhóm: Happy · Repository/branch: `K4-L3B-RAG-Pipeline` / `main`

## Phần việc có thể đối chiếu

| Phần việc | Bằng chứng | Trạng thái |
|---|---|---|
| Task 10: tạo câu trả lời có trích dẫn và từ chối khi thiếu bằng chứng | `src/task10_generation.py`, commit `8f557ab` | Đã triển khai |
| Giao diện chat Streamlit hiển thị câu trả lời và nguồn | `app.py`, commit `8f557ab` | Đã triển khai |

Quyết định kỹ thuật thể hiện trong code: sắp lại các đoạn tài liệu trước khi gửi model, gắn nhãn nguồn trong context và trả câu từ chối an toàn khi không lấy được bằng chứng hoặc model lỗi. Các sửa lỗi cache embedding, thứ tự citation và kiểm tra độ tin cậy ngày 25/09/2026 là phần hoàn thiện chung sau commit trên, không tính vào đóng góp cá nhân của Tuấn.

## Kiểm thử và giới hạn

- Sau khi tích hợp, bộ test dự án đạt **20/20**; demo Gemini trả lời câu tuyển sinh có citation và từ chối câu ngoài chủ đề.
- PageIndex chưa được kiểm chứng qua API thật vì chưa có `PAGEINDEX_API_KEY`.
- Mã học viên và xác nhận cá nhân của Tuấn cần Tuấn tự bổ sung; nội dung ở đây chỉ dựa trên file/commit có thể kiểm tra.
