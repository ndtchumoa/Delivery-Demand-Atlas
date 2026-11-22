# Kế hoạch triển khai

Đã tái tạo phân tích đa chuỗi theo vùng và hoàn thành kiểm tra tọa độ, so sánh H3 mức 8 và 9. Hai mức đều bảo toàn 31.415 đơn. Kết quả chi tiết nằm trong [notebook không gian](../notebooks/02_spatial_coverage.ipynb) và [bảng so sánh](../outputs/analysis/h3_resolution_comparison.csv).

| Bước | Công việc | Đầu ra kiểm tra được |
| --- | --- | --- |
| 1. Độ phân giải | Chọn mức H3 để hiển thị dựa trên độ chi tiết và tỷ lệ ô ít đơn. | Ghi mức H3 đã chọn và lý do chọn. |
| 2. Dữ liệu bản đồ | Sau khi chọn độ phân giải, xuất GeoJSON và bảng số đơn theo ô, ngày, vùng và loại AOI. | Tổng theo ô khớp với tổng đơn có tọa độ hợp lệ khi áp cùng bộ lọc. |
| 3. Demo | Dùng Leaflet để hiển thị GeoJSON trên nền OpenStreetMap. Thêm bộ lọc ngày, vùng, loại AOI và biểu đồ theo ngày của ô được chọn. | Bộ lọc cập nhật lớp ô và chú giải. Kiểm tra cả ngày thiếu, tập con rỗng và phần ghi công OpenStreetMap. |
| 4. Báo cáo | Tổng hợp kết quả không gian và đa chuỗi theo hai câu hỏi nghiên cứu. | Báo cáo có nguồn dữ liệu, bảng và biểu đồ tái tạo được, hình demo và giới hạn diễn giải. |
