# Đề cương chi tiết MI3380

**Tên đề tài**  
Trực quan hóa nhu cầu giao hàng chặng cuối tại Jilin trên OpenStreetMap và phân tích đa chuỗi thời gian theo vùng

**English title**  
Visualizing Last-Mile Delivery Demand in Jilin on OpenStreetMap and Analyzing Regional Time Series

## 1. Bối cảnh và mục tiêu

Đề tài phân tích phân bố điểm giao và biến động số đơn tiếp nhận theo ngày ở bốn vùng của Jilin. Sản phẩm gồm bản đồ tương tác và quy trình phân tích có thể tái tạo từ dữ liệu LaDe-D.

| Câu hỏi nghiên cứu | Sản phẩm dùng để trả lời |
| --- | --- |
| RQ1. Đơn giao tập trung ở đâu và phân bố thay đổi thế nào giữa các khoảng thời gian được chọn? | Bản đồ số đơn theo ô H3 trên nền OpenStreetMap, có bộ lọc ngày, vùng và loại AOI. |
| RQ2. Nhu cầu ở bốn vùng biến động cùng nhau đến mức nào? | Biểu đồ bốn chuỗi theo ngày, thống kê mô tả từng vùng và hai ma trận tương quan cho sáu cặp vùng. |

## 2. Dữ liệu và phạm vi

- Tập con LaDe-D Jilin có 31.415 đơn trong tệp `data/raw/delivery_jl.csv`. Đơn vị quan sát là một đơn với khóa `order_id`. Nhu cầu được đo bằng số đơn tiếp nhận trong dữ liệu, phân ngày theo `ds` và phân vùng theo mã gốc `region_id`.
- Tọa độ điểm giao `lng/lat` dùng để tổng hợp theo ô địa lý. Các trường GPS của người giao ghi vị trí tại thời điểm thao tác. Bài báo LaDe ghi nhận tọa độ đã được nhiễu để bảo vệ riêng tư.
- Chuỗi chính dùng bốn mã vùng `31`, `53`, `129` và `165`. Mã vùng dùng để tổng hợp và lọc, còn đa giác hiển thị được tạo từ lưới H3.
- Lịch từ 12/05 đến 28/10 có 170 ngày, trong đó 163 ngày có bản ghi. Repo dùng 2022 làm năm kỹ thuật vì nguồn chỉ cung cấp tháng và ngày. Phân tích chính dùng thứ tự ngày.
- Đếm đơn có ngày tiếp nhận hợp lệ, bao gồm những đơn có thời gian giao quá 24 giờ. Đơn thiếu tọa độ hợp lệ vẫn được đếm trong thống kê vùng. Với ngày có dữ liệu thành phố, vùng không có đơn ghi nhận được gán 0. Bảy ngày thiếu quan sát cấp thành phố được giữ là thiếu.
- Mẫu LaDe-D chỉ gồm các đơn được ghi nhận của nhóm người giao được quan sát. Thay đổi số người giao trong mẫu có thể làm thay đổi số đơn ghi nhận theo ngày. Phân tích độ trễ là phần mở rộng.

## 3. Phương pháp

### 3.1. Chuẩn hóa dữ liệu và kiểm tra phạm vi quan sát

Kiểm tra tính duy nhất của `order_id`, ngày theo `ds` trùng với ngày tiếp nhận, mã vùng và mức độ đầy đủ của tọa độ. Ghi nhận số đơn trước và sau từng bước. Dựng lịch ngày đầy đủ trước khi xử lý ngày thiếu và tính thay đổi số đơn. Đối chiếu tổng theo vùng với tổng cấp thành phố. Khi làm bản đồ, đối chiếu tổng theo ô với tổng đơn hợp lệ về tọa độ.

### 3.2. Trực quan hóa không gian

Gán mỗi điểm giao hợp lệ vào một ô H3, sau đó tổng hợp số đơn theo ô, ngày, vùng và loại AOI. So sánh thử H3 độ phân giải 8 và 9 dựa trên số ô có dữ liệu, tỷ lệ ô ít đơn và mức phân biệt khu vực trong demo. Chốt một độ phân giải để hiển thị. Xuất hình học GeoJSON và số liệu tổng hợp cho Leaflet, hiển thị ghi công OpenStreetMap trên bản đồ.

Bản đồ có bộ lọc khoảng ngày, vùng, loại AOI, chú giải số đơn và thông tin khi chọn ô. Khi so sánh hai giai đoạn bằng mắt, dùng thang màu chung và ghi số ngày có dữ liệu, vì tổng đơn phụ thuộc vào độ dài khoảng chọn.

### 3.3. Thống kê đa chuỗi thời gian

Với mỗi vùng, tính tổng, trung bình, trung vị, độ lệch chuẩn và số ngày bằng 0 trên tập ngày có quan sát. Vẽ bốn chuỗi trên cùng lịch ngày. Với mỗi cặp vùng, tính hệ số tương quan Pearson và số quan sát ghép cặp trên hai đại lượng.

1. **Mức số đơn cùng ngày** để mô tả các ngày nhu cầu cùng cao hoặc cùng thấp.
2. **Sai phân ngày liên tiếp** để mô tả mức đồng biến trong thay đổi số đơn. Chỉ tính sai phân nếu cả ngày hiện tại và ngày lịch liền trước đều có số liệu.

Đọc hai ma trận cùng biểu đồ, ghi rõ mẫu số và kiểm tra độ nhạy bằng cửa sổ 27/06–02/10 từng được dùng ở giai đoạn dự báo. Các hệ số mô tả mức liên hệ tuyến tính và có thể phản ánh biến động chung cấp thành phố.

## 4. Tiêu chí nghiệm thu

| Hợp phần | Tiêu chí kiểm tra |
| --- | --- |
| Bảng vùng–ngày | Một dòng mỗi cặp vùng–ngày, đủ bốn vùng và lịch liên tục. Tổng đơn vùng bằng tổng đơn được xác thực. Ngày thiếu quan sát có giá trị trống. |
| So sánh chuỗi | Sáu cặp vùng cho mỗi cách đo, kèm số ngày ghép. Sai phân trống ở ngày thiếu và ngày ngay sau khoảng thiếu. Notebook tái tạo được hình và bảng từ mã nguồn chung. |
| Dữ liệu bản đồ | Mỗi đơn có tọa độ hợp lệ thuộc một ô tại độ phân giải đã chọn. Tổng trên bản đồ khớp với tổng đơn đủ điều kiện khi áp cùng bộ lọc. |
| Demo | Đổi bộ lọc cập nhật lớp ô, chú giải và thông tin ô. Có trạng thái riêng cho khoảng lọc thiếu dữ liệu. Ghi công OSM hiển thị trực tiếp trên bản đồ. |

## 5. Tài liệu nền

- Wu và cộng sự, *LaDe: The First Comprehensive Last-mile Delivery Dataset from Industry*. [Bài báo và mô tả dữ liệu](https://arxiv.org/html/2306.10675v3).
- Hyndman và Athanasopoulos, *Forecasting: Principles and Practice*, mục Stationarity and differencing. [Giáo trình mở](https://otexts.com/fpp3/stationarity.html).
- H3, *API Quick Reference for Python* và *Tables of Cell Statistics Across Resolutions*. [API Python](https://uber.github.io/h3-py/api_quick.html) · [Độ phân giải](https://h3geo.org/docs/core-library/restable/).
- Leaflet, *Using GeoJSON with Leaflet*. [Hướng dẫn](https://leafletjs.com/examples/geojson/).
- OpenStreetMap Foundation, *Tile Usage Policy*. [Điều kiện sử dụng và ghi công](https://operations.osmfoundation.org/policies/tiles/).
