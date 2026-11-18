# Dự báo nhu cầu và tối ưu tuyến giao hàng chặng cuối

Đây là repo đồ án MI3380 sử dụng dữ liệu giao hàng LaDe-D tại Jilin. Bài toán dự báo hỏi mỗi vùng và loại AOI sẽ **tiếp nhận bao nhiêu đơn vào ngày mai**. Kết quả đó dự kiến dùng để chia xe trước ca. Khi danh sách đơn thực tế đã có, bước định tuyến sẽ dùng OR-Tools để xếp các điểm giao vào tuyến theo tải trọng xe.

Repo hiện chạy được phần làm sạch dữ liệu, dự báo và đánh giá. Phần phân bổ xe và định tuyến có thiết kế trong [đề cương chi tiết](reports/project_proposal.md). Số liệu trên trang này là kết quả dự báo.

## Mở demo

Tải [forecast_jilin.html](outputs/forecasts/demo/forecast_jilin.html) và mở bằng trình duyệt. Demo chạy offline. Chọn tập đánh giá, ngày, vùng hoặc loại AOI để xem số đơn thực tế và dự báo. Tập validation hiển thị cả ba mô hình. Tập test hiển thị baseline đã chọn trên validation.

- [forecast_jilin_predictions.csv](outputs/forecasts/demo/forecast_jilin_predictions.csv) có 1.640 dòng. Mỗi dòng ứng với một ngày và một cặp vùng × loại AOI. Cột dự báo LightGBM và XGBoost ở tập test để trống vì hai mô hình chưa được chấm trên tập đó.
- [forecast_jilin_metrics.csv](outputs/forecasts/demo/forecast_jilin_metrics.csv) lưu MAE, RMSE và WAPE theo mô hình, tập đánh giá và cấp tổng hợp. Giá trị WAPE trong CSV ở dạng tỷ lệ, ví dụ `0.2122` tương ứng khoảng `21.22%`.

## Dữ liệu và cách đánh giá

Tệp [delivery_jl.csv](data/raw/delivery_jl.csv) có 31.415 đơn. Bước làm sạch chuyển tọa độ giữ chỗ gần (0, 0) thành giá trị thiếu và loại 8 đơn có thời lượng giao trên 24 giờ khỏi tập phân tích. Dữ liệu gốc được giữ nguyên. Tập phân tích còn 31.407 đơn và tạo ra bảng 41 chuỗi trên lịch 170 ngày. Từng chuỗi là một cặp `region_id × aoi_type`. Bảng ở cấp `aoi_id` được giữ riêng để phân tích vị trí và chuẩn bị cho bài toán tuyến. [Nhật ký loại đơn](data/processed/excluded_rows.csv) · [Kiểm tra bảng nhu cầu](data/processed/panel_audit.json)

Ngày dự báo lấy theo ngày tiếp nhận đơn `ds`. Khi thành phố có dữ liệu nhưng một chuỗi không có đơn, nhu cầu của chuỗi đó là 0. Bảy ngày thiếu bản ghi trên toàn thành phố được đánh dấu chưa quan sát. Các ngày này được bỏ qua khi chấm điểm và giữ là giá trị thiếu trong lịch sử. Tệp gốc chỉ ghi tháng và ngày, vì vậy năm 2022 là quy ước dùng khi xử lý thời gian và tạo đặc trưng thứ trong tuần.

| Cửa sổ | Train | Validation | Test | Số ngày test đủ điều kiện |
|---|---|---|---|---:|
| Cửa sổ ổn định | 27/06–23/08 | 24/08–12/09 | 13/09–02/10 | 20/20 |
| Toàn kỳ, dùng để kiểm tra độ nhạy | 12/05–21/08 | 22/08–24/09 | 25/09–28/10 | 14/34 |

*Ngày trong bảng được ghi theo thứ tự ngày/tháng và tính cả hai đầu mút.* [Mốc chia tập](data/processed/stable_period.json) · [Giao thức chấm baseline](outputs/forecasts/baseline_protocol.json)

Dự báo ngày t dùng lịch sử đã quan sát đến hết ngày t−1. Các đặc trưng gồm lịch, lag 1/7/14 ngày, thống kê trượt 7/14 ngày và các thống kê không gian. Dòng train chỉ dùng dữ liệu không gian có trước ngày dự báo. Validation dùng bảng tra không gian đã cố định ở cuối train. Cấu hình mô hình được chọn bằng WAPE cấp chuỗi trên validation. Khi chấm cấp vùng, cộng dự báo và số đơn thực tế theo vùng–ngày trước khi tính sai số. [Thiết kế đặc trưng và mô hình](docs/spatial_ml_design.md)

## Kết quả dự báo

| Tập | Mô hình | MAE cấp chuỗi | RMSE cấp chuỗi | WAPE cấp chuỗi | WAPE cấp vùng |
|---|---|---:|---:|---:|---:|
| Validation | Trung bình trượt 7 ngày | 1,3716 | 3,4199 | **21,22%** | **13,73%** |
| Validation | LightGBM | 1,6075 | 3,9034 | 24,87% | 16,05% |
| Validation | XGBoost | 1,6793 | 3,9246 | 25,98% | 16,27% |
| Test | Trung bình trượt 7 ngày | 1,3115 | 3,2093 | 22,73% | 14,94% |

Validation và test của cửa sổ chính đều có 820 ô chuỗi–ngày. Tổng nhu cầu tương ứng là 5.300 và 4.732 đơn. Trung bình trượt 7 ngày có WAPE thấp nhất trên validation ở cả hai cấp. LightGBM là mô hình học máy tốt hơn trong hai cấu hình đầy đủ. Kết quả bỏ từng nhóm đặc trưng và so sánh trên cửa sổ toàn kỳ nằm trong [báo cáo validation](docs/ml_validation_results.md).

Cửa sổ ổn định được chọn sau khi quan sát toàn kỳ. Quy tắc loại đơn kéo dài cũng cần biết thời điểm giao xong. Do đó, các kết quả trên là đánh giá hồi cứu trên tập phân tích. Kiểm tra giữ đủ 8 đơn đã hoàn thành cho baseline. Độ nhạy tương ứng của LightGBM và XGBoost vẫn cần đánh giá.

## Chạy lại từ repo

Chạy các lệnh ở thư mục gốc. Môi trường dùng để ghi kết quả ML đã lưu là Python 3.12.14 trên Linux. Trên Windows, có thể tạo môi trường riêng bằng `py -3.12 -m venv .venv` rồi kích hoạt bằng `.\.venv\Scripts\Activate.ps1`. Các phiên bản thư viện dùng trong lần chạy ML được ghi trong [requirements_ml_tested.txt](requirements_ml_tested.txt) và [run_manifest.json](outputs/forecasts/ml_validation/run_manifest.json).

```bash
python -m pip install -r requirements.txt
python -m src.preprocessing
python -m src.train_forecast
python -m src.evaluate_forecast
```

`src.preprocessing` tạo cả các tệp Parquet cấp đơn được dùng khi huấn luyện. Cài các phiên bản đã ghi nếu cần đối chiếu sát môi trường thử nghiệm. Lệnh `--scenario all` chạy cửa sổ chính và toàn kỳ.

```bash
python -m pip install -r requirements_ml_tested.txt
python -m src.train_ml --scenario all
python -m src.sensitivity_keep_all_orders
python -m unittest discover -s tests -v
```

Để tạo lại demo bằng các dự báo ML đã lưu trong repo, chạy lệnh dưới đây. Script chạy lại baseline, đối chiếu khóa chuỗi–ngày và chỉ số với các bảng hiện có, rồi xuất HTML và hai CSV vào `outputs/forecasts/demo/`.

```bash
python -m src.build_forecast_demo
```

## Đọc notebook

| Tệp | Nội dung |
|---|---|
| [01_eda.ipynb](notebooks/01_eda.ipynb) | Chất lượng dữ liệu, nhu cầu, phân bố AOI và cửa sổ ổn định |
| [02_features.ipynb](notebooks/02_features.ipynb) | Đặc trưng thời gian, độ trễ và cách chia tập |
| [03_baseline_forecast.ipynb](notebooks/03_baseline_forecast.ipynb) | Kết quả và sai số của các baseline |
| [04_ml_validation.ipynb](notebooks/04_ml_validation.ipynb) | LightGBM, XGBoost, so sánh với baseline và ablation |
| [05_keep_all_orders_sensitivity.ipynb](notebooks/05_keep_all_orders_sensitivity.ipynb) | Phân tích bổ sung khi giữ 8 đơn giao trên 24 giờ |

Mã dùng chung ở `src/`, thiết lập thực nghiệm ở `configs/` và kiểm thử ở `tests/`. `data/raw/` chứa dữ liệu nguồn, `data/processed/` chứa bảng sau xử lý. `outputs/` chứa chỉ số, dự báo, mô hình đã lưu và hình vẽ. `docs/` giải thích thiết kế và kết quả chạy. `reports/` chứa đề cương và tài liệu tham khảo. [Bài báo dữ liệu LaDe](reports/lade_paper_2306.10675v3.pdf)

## Quy ước đặt tên tệp

- Tên do dự án tạo dùng từ tiếng Anh, chữ thường, chữ số và dấu gạch dưới. Phần mở rộng viết thường. Ví dụ `forecast_jilin_metrics.csv`, `spatial_ml_design.md` và `test_pipeline.py`.
- Notebook dùng `NN_<topic>.ipynb`, trong đó `NN` là số hai chữ số duy nhất theo thứ tự đọc. Các tệp khác dùng tên mô tả trực tiếp nội dung, ví dụ `<subject>_<artifact>.<ext>`.
- Khi hai lần chạy dùng cùng một giao thức nhưng khác cửa sổ dữ liệu, giữ tên tệp đầu ra giống nhau trong thư mục kịch bản riêng. Ví dụ `ml_validation/primary_stable_period/validation_metrics.csv` và `ml_validation/sensitivity_full_period/validation_metrics.csv`.
- Giữ nguyên tên chuẩn của công cụ hoặc tài liệu nguồn, như `README.md`, `.gitignore`, `delivery_jl.csv` và mã phiên bản arXiv trong tên file PDF. Khi đổi một tên do dự án tạo, cập nhật luôn lệnh, đường dẫn xuất, liên kết và tên tệp tải xuống liên quan.
