# Kế hoạch triển khai

Đã lưu mốc dự báo, cập nhật đề cương và hoàn thành phần thống kê đa chuỗi. Bước tiếp theo là kiểm tra độ phủ tọa độ và chọn độ phân giải H3 để xây bản đồ.

| Bước | Việc thực hiện | Kết quả kiểm tra được |
| --- | --- | --- |
| 1. Chuyển phạm vi | Lưu mốc dự báo `forecast-v1`, cập nhật đề cương và README, rút các thư mục trống dành cho VRP khỏi hướng phát triển hiện tại. | Có thể mở kết quả dự báo từ mốc Git. Đề cương mới có hai câu hỏi nghiên cứu và tiêu chí nghiệm thu. |
| 2. Thống kê đa chuỗi | Dựng bảng `region_id × ngày` từ dữ liệu nguồn, tính thống kê theo vùng và tương quan của mức số đơn và sai phân. Chạy trên toàn kỳ và đối chiếu cửa sổ 27/06–02/10. | Đếm bảo toàn tổng đơn, kiểm tra bảy ngày thiếu, tái tạo được bảng và biểu đồ. |
| 3. Tổng hợp địa lý | Rà soát `lng/lat`, đo độ phủ tọa độ, so H3 mức 8 và 9, chốt độ phân giải và xuất hình học GeoJSON cùng số liệu tổng hợp. | Có báo cáo số đơn được vẽ, tỷ lệ ô thưa và các phép đối chiếu tổng theo bộ lọc. |
| 4. Tích hợp OpenStreetMap | Dùng Leaflet để tô màu GeoJSON, xây bộ lọc ngày, vùng và AOI, đưa biểu đồ ngày vào thông tin ô được chọn và kiểm tra ghi công. | Demo chạy từ dữ liệu đã tổng hợp. Kiểm tra giao diện khi lọc ra một ngày thiếu hoặc một tập con rỗng. |
| 5. Báo cáo và trình diễn | Cập nhật kết quả theo hai câu hỏi nghiên cứu, hình chụp demo và hướng dẫn chạy. | Báo cáo có đầu ra tái tạo được và giải thích sự khác nhau giữa tương quan theo mức và theo biến động. |

## Tổ chức mã và notebook

| Vị trí | Vai trò |
| --- | --- |
| `data/raw/delivery_jl.csv` | Dữ liệu LaDe-D nguyên gốc ở Jilin. |
| `src/regional_time_series.py` | Chuẩn hóa bảng vùng–ngày, thống kê mô tả và tương quan. |
| `src/spatial_aggregation.py` | Kiểm tra tọa độ, gán ô H3, xuất lớp bản đồ ở bước 3. |
| `notebooks/01_eda.ipynb` | Tham chiếu cho chất lượng dữ liệu và phạm vi quan sát từ giai đoạn trước. |
| `notebooks/02_regional_time_series.ipynb` | Diễn giải biểu đồ và kết quả tương quan theo vùng, gọi hàm dùng chung. |
| `notebooks/03_spatial_coverage.ipynb` | Đối chiếu độ phủ tọa độ và độ phân giải sau bước tổng hợp địa lý. |
| `outputs/analysis/` | Kết quả mô tả và tương quan đã xuất. |
| `demo/` | Giao diện và dữ liệu cho bản đồ ở bước 4. |

Tên tệp mới dùng tiếng Anh và `snake_case`. Notebook dùng `NN_topic.ipynb`. Chuỗi lệnh và đầu ra của đề tài dự báo được ghi tại mốc `forecast-v1`.
