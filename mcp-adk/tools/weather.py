import requests, os
from dotenv import load_dotenv


def get_weather(city: str) -> str:
    """
    Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city (e.g., "Beijing", "Shanghai").
                   Note: For cities in China, use the city's English name (e.g., "Beijing").

    Returns:
        dict: A dictionary containing the weather information.
              Includes a 'status' key ('success' or 'error').
              If 'success', includes a 'report' key with weather details.
              If 'error', includes an 'error_message' key.
    """
    # Step 1.构建请求
    url = "https://api.openweathermap.org/data/2.5/weather"

    # Step 2.设置查询参数
    params = {
        "q": city,
        "appid": os.getenv("OPENWEATHER_API_KEY"),  # 输入自己的API key
        "units": "metric",  # 使用摄氏度而不是华氏度
        "lang": "zh_cn",  # 输出语言为简体中文
    }

    # Step 3.发送GET请求
    response = requests.get(url, params=params)

    # Step 4.解析响应
    data = response.json()
    city = data.get("name", "未知")
    country = data.get("sys", {}).get("country", "未知")
    temp = data.get("main", {}).get("temp", "N/A")
    humidity = data.get("main", {}).get("humidity", "N/A")
    wind_speed = data.get("wind", {}).get("speed", "N/A")
    weather_list = data.get("weather", [{}])
    description = weather_list[0].get("description", "未知")

    return (
        f"🌍 {city}, {country}\n"
        f"🌡 温度: {temp}°C\n"
        f"💧 湿度: {humidity}%\n"
        f"🌬 风速: {wind_speed} m/s\n"
        f"🌤 天气: {description}\n"
    )


if __name__ == "__main__":
    load_dotenv()
    result = get_weather(city="Beijing")
    print(result)
