from datetime import datetime
import time
import pandas as pd
import requests

# ==============================================================================
# 1. DANH SÁCH 12 KHU VỰC ĐẠI DIỆN TẠI HÀ NỘI
# ==============================================================================
SUB_REGIONS = {
    # Vùng lõi lịch sử & hành chính
    "Hoàn Kiếm": {
        "lat": 21.0285,
        "lon": 105.8542,
        "type": "Lõi lịch sử / Mật độ dân cư cao",
    },
    "Ba Đình": {
        "lat": 21.0341,
        "lon": 105.8239,
        "type": "Hành chính / Đô thị cổ",
    },
    # Vùng đô thị mật độ giao thông lớn
    "Cầu Giấy": {
        "lat": 21.0313,
        "lon": 105.7942,
        "type": "Đô thị mới / Văn phòng / Giao thông cao",
    },
    "Thanh Xuân": {
        "lat": 20.9986,
        "lon": 105.8111,
        "type": "Trục giao thông huyết mạch",
    },
    "Đống Đa": {
        "lat": 21.0125,
        "lon": 105.8283,
        "type": "Mật độ dân cư rất cao",
    },
    # Vùng cửa ngõ / Công nghiệp / Đô thị hóa
    "Hà Đông": {
        "lat": 20.9705,
        "lon": 105.7766,
        "type": "Cửa ngõ Tây Nam / Tốc độ đô thị hóa nhanh",
    },
    "Hoàng Mai": {
        "lat": 20.9772,
        "lon": 105.8533,
        "type": "Cửa ngõ Nam / Gần KCN & bến xe",
    },
    "Long Biên": {
        "lat": 21.0439,
        "lon": 105.8953,
        "type": "Cửa ngõ Đông / Giao thông liên tỉnh",
    },
    "Bắc Từ Liêm": {
        "lat": 21.0628,
        "lon": 105.7485,
        "type": "Đang phát triển / Nhiều công trình",
    },
    # Vùng sinh thái / Mặt nước
    "Tây Hồ": {
        "lat": 21.0686,
        "lon": 105.8189,
        "type": "Mặt nước lớn / Điều hòa không khí",
    },
    # Vùng ngoại thành / Nông nghiệp / KCN
    "Gia Lâm": {
        "lat": 21.0167,
        "lon": 105.9333,
        "type": "Ngoại thành phía Đông / Làng nghề & KCN",
    },
    "Đông Anh": {
        "lat": 21.1372,
        "lon": 105.8458,
        "type": "Ngoại thành phía Bắc / KCN Bắc Thăng Long",
    },
}


# ==============================================================================
# 2. HÀM CRAWL DỮ LIỆU TỪ OPEN-METEO AIR QUALITY API
# ==============================================================================
def fetch_open_meteo_air_quality(
    start_date: str, end_date: str, output_csv: str = "hanoi_air_openmeteo.csv"
):
    """Crawl dữ liệu lịch sử chất lượng không khí từ Open-Meteo

    :param start_date: Ngày bắt đầu (Format: YYYY-MM-DD)
    :param end_date: Ngày kết thúc (Format: YYYY-MM-DD)
    :param output_csv: Tên file CSV xuất ra
    """
    all_records = []
    # Các thông số cần lấy từ Open-Meteo
    hourly_params = "pm2_5,pm10,nitrogen_dioxide,ozone,sulphur_dioxide,carbon_monoxide,us_aqi"

    print(
        f"==> Bắt đầu crawl dữ liệu Open-Meteo cho {len(SUB_REGIONS)} khu vực Hà Nội..."
    )
    print(f"--> Khoảng thời gian: từ {start_date} đến {end_date}\n")

    for region_name, info in SUB_REGIONS.items():
        lat, lon = info["lat"], info["lon"]
        region_type = info["type"]

        # Endpoint API lịch sử của Open-Meteo Air Quality
        url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality?"
            f"latitude={lat}&longitude={lon}&"
            f"start_date={start_date}&end_date={end_date}&"
            f"hourly={hourly_params}&timezone=Asia%2FBangkok"
        )

        try:
            response = requests.get(url)
            data = response.json()

            if response.status_code == 200 and "hourly" in data:
                hourly = data["hourly"]
                times = hourly["time"]
                count = len(times)

                print(
                    f" [✓] {region_name:<12} | Lấy thành công {count} giờ dữ liệu."
                )

                for i in range(count):
                    dt = pd.to_datetime(times[i])

                    record = {
                        "region_name": region_name,
                        "region_type": region_type,
                        "latitude": lat,
                        "longitude": lon,
                        "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
                        "year": dt.year,
                        "month": dt.month,
                        "day": dt.day,
                        "hour": dt.hour,
                        "day_of_week": dt.day_name(),
                        "is_weekend": 1 if dt.dayofweek >= 5 else 0,
                        "us_aqi": hourly["us_aqi"][i],
                        "pm2_5": hourly["pm2_5"][i],
                        "pm10": hourly["pm10"][i],
                        "no2": hourly["nitrogen_dioxide"][i],
                        "o3": hourly["ozone"][i],
                        "so2": hourly["sulphur_dioxide"][i],
                        "co": hourly["carbon_monoxide"][i],
                    }
                    all_records.append(record)
            else:
                print(
                    f" [X] {region_name:<12} | Lỗi API: {data.get('reason', 'Lỗi không xác định')}"
                )

        except Exception as e:
            print(f" [X] {region_name:<12} | Lỗi kết nối: {e}")

        # Nghỉ nhẹ giữa các request
        time.sleep(0.1)

    if all_records:
        df = pd.DataFrame(all_records)
        df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        print(
            f"\nHoàn tất! Tổng cộng {len(df)} bản ghi đã xuất ra file '{output_csv}'."
        )
    else:
        print("\nKhông lấy được dữ liệu. Vui lòng kiểm tra lại kết nối nét!")


# ==============================================================================
# 3. THỰC THI (MAIN)
# ==============================================================================
if __name__ == "__main__":
    # Chọn khoảng thời gian bạn muốn crawl (Ví dụ: Từ 01/01/2026 đến 01/06/2026)
    START_DATE = "2026-01-01"
    END_DATE = "2026-06-01"

    fetch_open_meteo_air_quality(
        START_DATE, END_DATE, "hanoi_air_quality_openmeteo.csv"
    )