# Kết quả validation LightGBM/XGBoost

Ngày 17/11/2026. Chưa chấm test ML. Đây là kết quả phát triển trên validation, không phải kết luận tổng quát về mô hình.

## Kết quả hai cửa sổ

| Cửa sổ | Mô hình full / baseline chọn trên validation | MAE | RMSE | WAPE chuỗi | WAPE region |
|---|---|---:|---:|---:|---:|
| primary_stable_period | rolling_mean_7 | 1.3716 | 3.4199 | 21.22% | 13.73% |
| primary_stable_period | lightgbm_full | 1.6075 | 3.9034 | 24.87% | 16.05% |
| primary_stable_period | xgboost_full | 1.6793 | 3.9246 | 25.98% | 16.27% |
| sensitivity_full_period | rolling_mean_7 | 1.3043 | 3.0972 | 20.72% | 13.21% |
| sensitivity_full_period | lightgbm_full | 1.5547 | 3.6019 | 24.70% | 14.58% |
| sensitivity_full_period | xgboost_full | 1.6007 | 3.6058 | 25.43% | 15.08% |

Cửa sổ chính: 1.804 dòng train đủ lịch sử (44 ngày × 41 chuỗi), 820 ô validation (20 ngày × 41 chuỗi, tổng 5.300 đơn). Cửa sổ toàn kỳ: 2.952 dòng train đủ lịch sử và 1.394 ô validation. Không loại chuỗi thưa.

LightGBM là bản ML full được chọn ở cả hai cửa sổ, nhưng rolling 7 ngày vẫn tốt hơn. Ở cửa sổ chính, ML có WAPE cao hơn baseline khoảng 3,65 điểm phần trăm. Chưa có căn cứ kết luận ML cải thiện dự báo so với baseline tốt nhất; đây vẫn là kết quả nghiên cứu hợp lệ.

Lưu ý: mô hình ML cố định sau train, còn rolling baseline cập nhật nhu cầu thực đến t−1 mỗi ngày. Cả hai tuân thủ giao thức rolling one-day-ahead; dữ liệu validation có thể khác phân bố train. Đây là giả thuyết cần kiểm tra thêm, chưa phải nguyên nhân đã chứng minh.

## Cấu hình full được chọn

| Cửa sổ | Họ mô hình | Cấu hình chọn bằng validation |
|---|---|---|
| primary_stable_period | lightgbm | `{"num_leaves": 15, "min_child_samples": 50, "n_estimators": 100}` |
| primary_stable_period | xgboost | `{"max_depth": 2, "min_child_weight": 20, "n_estimators": 100}` |
| sensitivity_full_period | lightgbm | `{"num_leaves": 15, "min_child_samples": 50, "n_estimators": 100}` |
| sensitivity_full_period | xgboost | `{"max_depth": 4, "min_child_weight": 5, "n_estimators": 100}` |

Learning rate 0,05; seed 2026; squared-error; không refit validation. Mỗi biến thể chọn từ 8 ứng viên; tổng 160 lượt fit cho hai cửa sổ.

## Ablation cửa sổ chính

| Họ mô hình | Bỏ nhóm | WAPE | Thay đổi so với full (điểm %) |
|---|---|---:|---:|
| lightgbm | calendar | 24.84% | -0.031 |
| lightgbm | lag | 25.12% | +0.249 |
| lightgbm | rolling | 25.31% | +0.442 |
| lightgbm | spatial | 24.43% | -0.442 |
| xgboost | calendar | 26.01% | +0.029 |
| xgboost | lag | 25.10% | -0.881 |
| xgboost | rolling | 26.20% | +0.217 |
| xgboost | spatial | 26.17% | +0.189 |

Delta dương nghĩa là bỏ nhóm làm tăng sai số; delta âm nghĩa là bỏ nhóm giúp giảm sai số trên validation. LightGBM bỏ spatial cải thiện khoảng 0,442 điểm %, XGBoost bỏ lag cải thiện khoảng 0,881 điểm %. Các hiệu ứng nhỏ và khác nhau theo họ mô hình/cửa sổ, nên chưa thể khẳng định một nhóm luôn hữu ích hoặc vô ích. Ablation tốt nhất ở đây cũng chưa vượt rolling 7 ngày.

## Kiểm soát chất lượng và giới hạn

- Các ô code của notebook được thực thi tuần tự trực tiếp bằng Python và đã lưu output; môi trường hiện tại không cho mở socket để chạy kernel Jupyter.
- 16 kiểm thử đạt trên Linux/Python 3.12.14. Chưa chạy ML trên Windows/Python 3.13.
- Kiểm tra bảo toàn region gốc, fallback, biến đổi tương lai và train tại ngày t; test targets không tham gia chọn cấu hình.
- Lưu và đọc lại mô hình native cho hai thư viện cho dự báo khớp; seed lặp lại cho kết quả khớp trong môi trường hiện tại.
- Native gain mô tả mô hình, không xác lập nhân quả; ablation dùng validation đã tham gia tuning nên chỉ mang tính khám phá.
- Cửa sổ toàn kỳ không thay cho A/B giữ đủ tám đơn. A/B ML là việc tiếp theo.
- Không mở rộng grid hoặc chấm test để tìm kết quả đẹp hơn trong đợt này.

## Công việc tiếp theo

1. Rà soát giao thức, đường học train/validation và sai số theo chuỗi/ngày để kiểm tra khả năng overfit hoặc thay đổi mức nhu cầu.
2. Chạy A/B giữ đủ đơn cho ML theo cấu hình đã ghi; báo cáo cả kết quả không cải thiện.
3. Nếu mở rộng loss hoặc mô hình residual quanh rolling mean, ghi thành thí nghiệm validation phiên bản mới trước khi chạy.
4. Chốt giao thức test và vai trò của baseline/ML trong S2; sau đó chuẩn bị depot chung từ train, vùng phân bổ, F/Q và CVRP.

Chi tiết thiết kế và lệnh tái lập: [spatial_ml_design.md](spatial_ml_design.md).
