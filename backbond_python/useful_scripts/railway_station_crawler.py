import requests
import csv
import json
import re
import os
import time
from datetime import datetime

def get_railway_stations(max_retries=3, retry_delay=2):
    """
    爬取12306全国火车站名单
    
    参数:
    max_retries: 最大重试次数
    retry_delay: 重试间隔时间（秒）
    """
    # 12306车站数据文件URL
    url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"
    
    # 设置请求头，模拟浏览器访问
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # 重试机制
    for retry in range(max_retries):
        try:
            print(f"正在请求车站数据... (尝试 {retry+1}/{max_retries})")
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = "utf-8"
            
            if response.status_code != 200:
                print(f"请求失败，状态码：{response.status_code}")
                if retry < max_retries - 1:
                    print(f"{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    return None
            
            print("数据请求成功，正在解析...")
            
            # 提取JavaScript变量中的车站数据
            station_data = response.text
            
            # 验证数据是否包含车站信息
            if 'station_names' not in station_data:
                print("数据格式错误，未找到station_names变量")
                return None
            
            # 使用正则表达式提取车站信息
            # 匹配格式: @代码|车站名|电报码|拼音|拼音缩写|序号|地区代码|城市|...
            stations = []
            pattern = r'@([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)'
            matches = re.findall(pattern, station_data)
            
            if not matches:
                print("未找到车站数据，请检查正则表达式是否正确")
                return None
            
            print(f"共解析到 {len(matches)} 个车站")
            
            # 转换为结构化数据
            valid_stations = []
            for i, match in enumerate(matches):
                if len(match) < 8:
                    print(f"警告：第{i+1}个车站数据字段不完整，跳过")
                    continue
                
                station = {
                    "station_code": match[0],
                    "station_name": match[1],
                    "telecode": match[2],
                    "pinyin": match[3],
                    "pinyin_abbr": match[4],
                    "sequence": match[5],
                    "region_code": match[6],
                    "city": match[7]
                }
                valid_stations.append(station)
            
            if len(valid_stations) != len(matches):
                print(f"共跳过 {len(matches) - len(valid_stations)} 个无效车站数据")
            
            return valid_stations
            
        except requests.RequestException as e:
            print(f"网络请求异常: {e}")
            if retry < max_retries - 1:
                print(f"{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                continue
            else:
                return None
        except Exception as e:
            print(f"解析数据异常: {e}")
            return None
    
    return None

def save_to_csv(stations, filename=None):
    """
    将车站数据保存为CSV文件
    """
    if not stations:
        print("没有数据可保存")
        return False
    
    if not filename:
        # 默认文件名格式：railway_stations_YYYYMMDD_HHMMSS.csv
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"railway_stations_{now}.csv"
    
    # CSV列名
    fieldnames = ["station_code", "station_name", "telecode", "pinyin", "pinyin_abbr", "sequence", "region_code", "city"]
    
    try:
        # 验证目录是否存在
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            print(f"目录不存在，正在创建: {directory}")
            os.makedirs(directory, exist_ok=True)
        
        with open(filename, "w", newline="", encoding="utf-8-sig") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # 写入表头
            writer.writeheader()
            
            # 写入数据并验证
            written_count = 0
            for i, station in enumerate(stations):
                try:
                    # 验证车站数据是否完整
                    for field in fieldnames:
                        if field not in station:
                            print(f"警告：第{i+1}个车站缺少{field}字段，跳过")
                            raise ValueError(f"Missing field: {field}")
                    
                    writer.writerow(station)
                    written_count += 1
                except Exception as e:
                    print(f"写入第{i+1}个车站数据时出错: {e}")
                    continue
        
        print(f"数据保存完成，共写入 {written_count} 个车站信息")
        print(f"数据已成功保存到 {filename}")
        print(f"文件路径: {os.path.abspath(filename)}")
        return True
        
    except PermissionError:
        print(f"权限错误，无法写入文件: {filename}")
        return False
    except IOError as e:
        print(f"IO错误，无法写入文件: {e}")
        return False
    except Exception as e:
        print(f"保存文件异常: {e}")
        return False

def save_to_json(stations, filename=None):
    """
    将车站数据保存为JSON格式文件，并规范化字段名称
    """
    if not stations:
        print("没有数据可保存")
        return False
    
    if not filename:
        # 默认文件名格式：railway_stations_YYYYMMDD_HHMMSS.json
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"railway_stations_{now}.json"
    
    try:
        # 验证目录是否存在
        directory = os.path.dirname(filename)
        if directory and not os.path.exists(directory):
            print(f"目录不存在，正在创建: {directory}")
            os.makedirs(directory, exist_ok=True)
        
        # 规范化数据字段
        normalized_stations = []
        for i, station in enumerate(stations):
            try:
                normalized_station = {
                    "station_code": station.get("station_code", ""),
                    "station_name": station.get("station_name", ""),
                    "telecode": station.get("telecode", ""),
                    "pinyin": station.get("pinyin", ""),
                    "pinyin_abbr": station.get("pinyin_abbr", ""),
                    "sequence": station.get("sequence", ""),
                    "region_code": station.get("region_code", ""),
                    "destination": station.get("city", "")  # 规范化为destination字段
                }
                normalized_stations.append(normalized_station)
            except Exception as e:
                print(f"规范化第{i+1}个车站数据时出错: {e}")
                continue
        
        with open(filename, "w", encoding="utf-8") as jsonfile:
            json.dump(normalized_stations, jsonfile, ensure_ascii=False, indent=2)
        
        print(f"JSON数据保存完成，共写入 {len(normalized_stations)} 个车站信息")
        print(f"数据已成功保存到 {filename}")
        print(f"文件路径: {os.path.abspath(filename)}")
        return True
        
    except PermissionError:
        print(f"权限错误，无法写入文件: {filename}")
        return False
    except IOError as e:
        print(f"IO错误，无法写入文件: {e}")
        return False
    except Exception as e:
        print(f"保存JSON文件异常: {e}")
        return False

def main():
    """
    主函数
    """
    print("=== 全国火车站名单爬虫 ===")
    print("数据来源: 12306铁路客户服务中心")
    print("=" * 40)
    
    # 获取车站数据
    stations = get_railway_stations()
    
    if not stations:
        print("爬取失败，程序退出")
        return
    
    # 保存为CSV文件
    print("\n正在保存为CSV格式...")
    save_to_csv(stations)
    
    # 保存为JSON格式（带字段规范化）
    print("\n正在保存为JSON格式...")
    save_to_json(stations)
    
    # 显示前10个车站信息（使用规范化字段名）
    print("\n=== 前10个车站信息预览 ===")
    for i, station in enumerate(stations[:10]):
        print(f"{i+1}. {station['station_name']} ({station['station_code']}) - 目的地: {station['city']}")
    
    print("\n=== 爬虫程序执行完成 ===")

if __name__ == "__main__":
    main()
