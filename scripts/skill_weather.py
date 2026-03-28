#!/usr/bin/env python3
"""
天气查询 Skill — Open-Meteo API (免费,无需API Key)

功能:
- 城市名→经纬度 (Open-Meteo Geocoding API)
- 经纬度→当前天气+未来3天预报 (Open-Meteo Forecast API)
- 用户城市偏好记忆 (JSON文件持久化)

用法:
  from skill_weather import WeatherSkill
  skill = WeatherSkill()
  result = skill.query("深圳")           # 直接查询
  result = skill.query_smart("今日天气", user_id="user123")  # 智能查询(含偏好)
"""
import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

import requests

log = logging.getLogger("skill_weather")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREFS_FILE = PROJECT_ROOT / "data" / "user_city_prefs.json"

# WMO天气代码→中文描述
WMO_CODES = {
    0: "晴", 1: "大部晴", 2: "多云", 3: "阴天",
    45: "雾", 48: "霜雾",
    51: "小毛毛雨", 53: "中毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻小雨", 67: "冻大雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "小阵雨", 81: "中阵雨", 82: "大阵雨",
    85: "小阵雪", 86: "大阵雪",
    95: "雷阵雨", 96: "雷阵雨+小冰雹", 99: "雷阵雨+大冰雹",
}

# 中文城市→英文映射(常见城市加速)
CITY_ALIASES = {
    "北京": "Beijing", "上海": "Shanghai", "广州": "Guangzhou",
    "深圳": "Shenzhen", "杭州": "Hangzhou", "成都": "Chengdu",
    "武汉": "Wuhan", "南京": "Nanjing", "重庆": "Chongqing",
    "天津": "Tianjin", "苏州": "Suzhou", "西安": "Xi'an",
    "长沙": "Changsha", "厦门": "Xiamen", "青岛": "Qingdao",
    "大连": "Dalian", "宁波": "Ningbo", "郑州": "Zhengzhou",
    "沈阳": "Shenyang", "哈尔滨": "Harbin", "昆明": "Kunming",
    "福州": "Fuzhou", "济南": "Jinan", "合肥": "Hefei",
    "太原": "Taiyuan", "南昌": "Nanchang", "贵阳": "Guiyang",
    "东莞": "Dongguan", "佛山": "Foshan", "珠海": "Zhuhai",
    "香港": "Hong Kong", "台北": "Taipei", "澳门": "Macau",
}


class WeatherSkill:
    """天气查询技能"""

    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = 10
        self._prefs = self._load_prefs()

    # ── 用户偏好 ──

    def _load_prefs(self) -> Dict:
        if PREFS_FILE.exists():
            try:
                return json.loads(PREFS_FILE.read_text())
            except Exception:
                pass
        return {}

    def _save_prefs(self):
        PREFS_FILE.parent.mkdir(parents=True, exist_ok=True)
        PREFS_FILE.write_text(json.dumps(self._prefs, ensure_ascii=False, indent=2))

    def set_user_city(self, user_id: str, city: str):
        """保存用户默认城市"""
        self._prefs[user_id] = {"city": city, "updated_at": datetime.now().isoformat()}
        self._save_prefs()

    def get_user_city(self, user_id: str) -> Optional[str]:
        """获取用户默认城市"""
        return self._prefs.get(user_id, {}).get("city")

    # ── 地理编码 ──

    def geocode(self, city_name: str) -> Optional[Dict]:
        """城市名→经纬度"""
        search_name = CITY_ALIASES.get(city_name, city_name)
        try:
            resp = self.session.get(self.GEOCODING_URL, params={
                "name": search_name, "count": 1, "language": "zh", "format": "json"
            })
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                r = results[0]
                return {
                    "name": r.get("name", city_name),
                    "country": r.get("country", ""),
                    "admin1": r.get("admin1", ""),
                    "lat": r["latitude"],
                    "lon": r["longitude"],
                }
        except Exception as e:
            log.warning(f"Geocoding失败({city_name}): {e}")
        return None

    # ── 天气查询 ──

    def get_forecast(self, lat: float, lon: float) -> Optional[Dict]:
        """经纬度→天气数据"""
        try:
            resp = self.session.get(self.FORECAST_URL, params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                           "weather_code,wind_speed_10m,wind_direction_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                         "precipitation_sum,wind_speed_10m_max,sunrise,sunset",
                "timezone": "auto",
                "forecast_days": 3,
            })
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            log.warning(f"Forecast失败({lat},{lon}): {e}")
        return None

    # ── 格式化 ──

    def format_weather(self, city: str, geo: Dict, data: Dict) -> str:
        """格式化天气数据为可读文本"""
        lines = []
        loc = f"{city}"
        if geo.get("admin1"):
            loc = f"{geo['admin1']}·{city}"

        # 当前天气
        cur = data.get("current", {})
        wcode = cur.get("weather_code", 0)
        weather_desc = WMO_CODES.get(wcode, f"代码{wcode}")
        temp = cur.get("temperature_2m", "?")
        feels = cur.get("apparent_temperature", "?")
        humidity = cur.get("relative_humidity_2m", "?")
        wind = cur.get("wind_speed_10m", "?")

        lines.append(f"📍 {loc} 实时天气")
        lines.append(f"  {weather_desc} | {temp}°C (体感{feels}°C)")
        lines.append(f"  湿度 {humidity}% | 风速 {wind}km/h")

        # 未来3天预报
        daily = data.get("daily", {})
        dates = daily.get("time", [])
        maxs = daily.get("temperature_2m_max", [])
        mins = daily.get("temperature_2m_min", [])
        codes = daily.get("weather_code", [])
        rains = daily.get("precipitation_sum", [])

        if dates:
            lines.append("")
            lines.append("📅 未来3天预报:")
            weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            for i, d in enumerate(dates[:3]):
                try:
                    dt = datetime.strptime(d, "%Y-%m-%d")
                    wd = weekdays[dt.weekday()]
                except Exception:
                    wd = d
                desc = WMO_CODES.get(codes[i] if i < len(codes) else 0, "?")
                hi = maxs[i] if i < len(maxs) else "?"
                lo = mins[i] if i < len(mins) else "?"
                rain = rains[i] if i < len(rains) else 0
                rain_str = f" 降水{rain}mm" if rain and rain > 0 else ""
                lines.append(f"  {d} ({wd}) {desc} {lo}~{hi}°C{rain_str}")

        # 日出日落
        sunrises = daily.get("sunrise", [])
        sunsets = daily.get("sunset", [])
        if sunrises and sunsets:
            sr = sunrises[0].split("T")[1] if "T" in sunrises[0] else sunrises[0]
            ss = sunsets[0].split("T")[1] if "T" in sunsets[0] else sunsets[0]
            lines.append(f"\n🌅 日出 {sr} | 日落 {ss}")

        lines.append("\n(数据来源: Open-Meteo)")
        return "\n".join(lines)

    # ── 主查询接口 ──

    def query(self, city: str) -> Dict:
        """查询指定城市天气"""
        geo = self.geocode(city)
        if not geo:
            return {"success": False, "error": f"找不到城市「{city}」，请检查城市名"}

        forecast = self.get_forecast(geo["lat"], geo["lon"])
        if not forecast:
            return {"success": False, "error": f"获取{city}天气数据失败"}

        text = self.format_weather(city, geo, forecast)
        return {"success": True, "text": text, "city": city, "geo": geo}

    def query_smart(self, user_msg: str, user_id: str = "") -> Dict:
        """
        智能天气查询:
        - 消息中提取城市名 → 查询并记住
        - 无城市名但有偏好 → 用偏好城市
        - 无城市名无偏好 → 返回需要询问
        """
        city = self._extract_city(user_msg)

        if city:
            if user_id:
                self.set_user_city(user_id, city)
            return self.query(city)

        # 尝试用户偏好
        if user_id:
            pref_city = self.get_user_city(user_id)
            if pref_city:
                return self.query(pref_city)

        return {
            "success": False,
            "need_city": True,
            "text": "请告诉我你所在的城市，例如：「深圳天气」或「我在北京」，我就能查询实时天气了。"
        }

    def _extract_city(self, msg: str) -> Optional[str]:
        """从消息中提取城市名"""
        import re
        # 直接匹配已知城市
        for cn in CITY_ALIASES:
            if cn in msg:
                return cn

        # 模式匹配: "XX天气" "XX的天气" "我在XX"
        patterns = [
            r'(\w{2,5}?)(?:的)?天气',
            r'我在(\w{2,5})',
            r'(\w{2,5}?)(?:今天|明天|后天)',
        ]
        for pat in patterns:
            m = re.search(pat, msg)
            if m:
                candidate = m.group(1).strip()
                # 过滤掉非城市词
                if candidate and len(candidate) >= 2 and candidate not in (
                    '今日', '今天', '明天', '后天', '本周', '这周', '查询', '查看', '怎么'
                ):
                    return candidate
        return None


# ── 命令行测试 ──
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    skill = WeatherSkill()
    city = sys.argv[1] if len(sys.argv) > 1 else "深圳"
    result = skill.query(city)
    if result["success"]:
        print(result["text"])
    else:
        print(f"错误: {result['error']}")
