# Kế hoạch triển khai

Đã tái tạo phân tích đa chuỗi theo vùng và hoàn thành kiểm tra tọa độ, so sánh H3 mức 8 và 9. Hai mức đều bảo toàn 31.415 đơn. Bản đồ dùng H3 mức 8 để giữ các cụm chính dễ đọc ở góc nhìn toàn vùng. Kết quả chi tiết nằm trong [notebook không gian](../notebooks/02_spatial_coverage.ipynb) và [bảng so sánh](../outputs/analysis/h3_resolution_comparison.csv).

| Bước | Công việc | Đầu ra kiểm tra được |
| --- | --- | --- |
| 1. Độ phân giải | Đã kiểm tra độ phủ và chọn H3 mức 8. | Có bảng so sánh mức 8 và 9. |
| 2. Dữ liệu bản đồ | Đã xuất đa giác và số đơn theo ô, ngày tiếp nhận, vùng và loại AOI. | Các tệp nằm trong [demo/data](../demo/data). Tổng số đơn khớp dữ liệu nguồn khi áp cùng bộ lọc. |
| 3. Demo | Dùng Leaflet để hiển thị GeoJSON trên nền OpenStreetMap. Thêm bộ lọc ngày, vùng, loại AOI và biểu đồ theo ngày của ô được chọn. | Bộ lọc cập nhật lớp ô và chú giải. Kiểm tra cả ngày thiếu, tập con rỗng và phần ghi công OpenStreetMap. |
| 4. Báo cáo | Tổng hợp kết quả không gian và đa chuỗi theo hai câu hỏi nghiên cứu. | Báo cáo có nguồn dữ liệu, bảng và biểu đồ tái tạo được, hình demo và giới hạn diễn giải. |
