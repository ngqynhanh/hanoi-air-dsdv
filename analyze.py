import pandas as pd

df = pd.read_csv("hanoi_air_quality_12regions.csv")

# 1. Xem khu vực nào chất lượng không khí tệ nhất / tốt nhất trung bình
print("--- PM2.5 TRUNG BÌNH THEO KHU VỰC ---")
print(
    df.groupby("region_name")["pm2_5"]
    .mean()
    .sort_values(ascending=False)
)

# 2. Thay đổi theo Giờ trong ngày (Through the day)
print("\n--- PM2.5 TRUNG BÌNH THEO KHU VỰC & GIỜ CỦA NGÀY ---")
print(df.groupby(["region_name", "hour"])["pm2_5"].mean().unstack())

# 3. So sánh Ngày làm việc vs Cuối tuần (Through the week)
print("\n--- SO SÁNH NGÀY THƯỜNG VS CUỐI TUẦN ---")
print(df.groupby(["is_weekend"])["pm2_5"].mean())

# 4. Biến đổi theo Tháng (Through the year)
print("\n--- XU HƯỚNG THEO THÁNG ---")
print(df.groupby(["month"])["pm2_5"].mean())