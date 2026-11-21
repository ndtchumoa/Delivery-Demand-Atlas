# Kế hoạch triển khai

Phân tích đa chuỗi theo vùng đã có mã tái tạo và bảng kết quả. Các bước còn lại theo thứ tự triển khai được trình bày dưới đây.

| Bước | Công việc | Đầu ra kiểm tra được |
| --- | --- | --- |
| 1. Độ phủ tọa độ | Kiểm tra `lng/lat` và so sánh H3 ở độ phân giải 8 và 9. | Số và tỷ lệ đơn có thể đưa lên bản đồ, số ô có dữ liệu và tỷ lệ ô ít đơn ở từng độ phân giải. |
| 2. Dữ liệu bản đồ | Sau khi chọn độ phân giải, xuất GeoJSON và bảng số đơn theo ô, ngày, vùng và loại AOI. | Tổng theo ô khớp với tổng đơn có tọa độ hợp lệ khi áp cùng bộ lọc. |
| 3. Demo | Dùng Leaflet để hiển thị GeoJSON trên nền OpenStreetMap. Thêm bộ lọc ngày, vùng, loại AOI và biểu đồ theo ngày của ô được chọn. | Bộ lọc cập nhật lớp ô và chú giải. Kiểm tra cả ngày thiếu, tập con rỗng và phần ghi công OpenStreetMap. |
| 4. Báo cáo | Tổng hợp kết quả không gian và đa chuỗi theo hai câu hỏi nghiên cứu. | Báo cáo có nguồn dữ liệu, bảng và biểu đồ tái tạo được, hình demo và giới hạn diễn giải. |
