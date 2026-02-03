from langchain import tools
from langchain.tools import tool
import requests
import requests
from bs4 import BeautifulSoup
import json
import time

def time_cost(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"{func.__name__} cost time: {end - start}")
        return result
    return wrapper


# from rag import rag_system
import os

@time_cost
def get_url_content(url):
    """
    获取搜索得到的url的content内容
    """
    try:
        headers = {
            'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }
        response = requests.get(url,headers=headers,allow_redirects=True)
        response.raise_for_status()  # 检查HTTP错误
        
        # 获取纯文本
        text_content = response.text
        
        # 如果需要解析HTML获取文本
        soup = BeautifulSoup(text_content, 'html.parser')
        clean_text = soup.get_text()
        if len(clean_text) > 2000:
            clean_text = clean_text[:2000]
        return {
            'status_code': response.status_code,
            'text': text_content,
            'clean_text': clean_text,
            'encoding': response.encoding
        }
        
    except requests.RequestException as e:
        return {'error': str(e)}
@time_cost
def get_search_url(search_response):
    """
    获取搜索结果中的url和发布日期
    """
    url_data = []
    for item in search_response["data"].get("webPages", {}).get("value", []):
        url_data.append({"url":item["url"]})
    return url_data


def get_search_result(query: str):
    """
    获取搜索结果,并返回规范化结果
    """
    url = os.getenv("search_url")
    api_key = "Bearer " + os.getenv("search_api_key")
    freshness = "noLimit"
    summery = True 
    payload = json.dumps({
        "query": query,
        "freshness": freshness,
        "summery": summery
    })
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    response = requests.request("POST", url, headers=headers, data=payload)
    
    # 得到url列表
    url_data = get_search_url(response.json())
    url_data = url_data[:2] if len(url_data) > 2 else url_data
    # formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    content_list = []
    for url in url_data:
        if get_url_content(url["url"]).get("error"):
            continue
        content_list.append(get_url_content(url["url"]).get("clean_text", ""))
        
    return content_list

@tool
def get_route_plan(origin: str, destination: str, date: str):
    """
    获取从origin到destination的路线计划,并返回规范化结果
    """
    # 调用generate_travel_plan函数
    plan = generate_travel_plan(origin, destination, date)
    
    return plan

# @tool
# def get_knowledge_base_result(query: str, k: int = 3):
#     """
#     从知识库中检索相关信息并生成回答
#     
#     Args:
#         query: 搜索查询字符串
#         k: 检索的相关文档数量（默认3）
#         
#     Returns:
#         包含回答、上下文和检索文档元数据的字典
#     """
#     try:
#         result = rag_system.generate_with_context(query, k=k)
#         return result
#     except Exception as e:
#         return {"error": str(e), "answer": "知识库访问失败，请稍后重试。"}

@tool
def get_traffic_info(origin: str, destination: str, date: str):
    """
    获取从origin到destination的交通信息
    
    Args:
        origin: 出发地
        destination: 目的地
        date: 出发日期
        
    Returns:
        包含交通信息的字典
    """
    # 调用交通信息API
    traffic_info = get_traffic_data(origin, destination, date,filter='',departure_time_range='')
    
    return traffic_info

def get_traffic_data(origin: str, destination: str, date: str, filter: str = '', departure_time_range: str = ''):
    requestParams = {
    'key': os.getenv("traffic_api_key"),
    'search_type': '1',
    'departure_station': origin,
    'arrival_station': destination,
    'date': date,
    'filter': filter,
    'enable_booking': '1',
    'departure_time_range': departure_time_range,
    }

    # 发起接口网络请求
    response = requests.get(os.getenv("traffic_api_url"), params=requestParams)
    
    # 解析响应结果
    if response.status_code == 200:
        responseResult = response.json()
        # 网络请求成功。可依据业务逻辑和接口文档说明自行处理。
        print(responseResult)
    else:
        # 网络异常等因素，解析结果异常。可依据业务逻辑自行处理。
        print('请求异常')

def location_transform(origin,destination):
    """
    转换出发地和目的地的位置信息
    """
    # 调用交通信息API
    gaode_base_url = "https://restapi.amap.com/v3/geocode/geo?"
    origin_get_url = gaode_base_url + "key=" + os.getenv("gaode_api_key") + "&address=" + origin
    destination_get_url = gaode_base_url + "key=" + os.getenv("gaode_api_key") + "&address=" + destination
    # 发起接口网络请求
    origin_response = requests.get(origin_get_url)
    destination_response = requests.get(destination_get_url)
    # 解析响应结果
    if origin_response.status_code == 200 and destination_response.status_code == 200:
        origin_result = origin_response.json()
        destination_result = destination_response.json()
        if origin_result["status"] == "1" and destination_result["status"] == "1":
            origin_location = origin_result["geocodes"][0]["location"]
            destination_location = destination_result["geocodes"][0]["location"]
            origin_citycode = origin_result["geocodes"][0]["citycode"]
            destination_citycode = destination_result["geocodes"][0]["citycode"]
            return {"origin":origin_location,"destination":destination_location,"origin_citycode":origin_citycode,"destination_citycode":destination_citycode}
        else:
            print("位置信息获取失败")
            return None
    else:
        # 网络异常等因素，解析结果异常。可依据业务逻辑自行处理。
        print('请求异常')
        return None

def get_route_info(locations: dict):
    """
    获取交通信息
    
    Args:
        locations: 包含出发地和目的地位置信息的字典
        
    Returns:
        包含交通信息的字典
    """
    # 调用交通信息API
    origin = locations["origin"]
    destination = locations["destination"]
    origin_citycode = locations["origin_citycode"]
    destination_citycode = locations["destination_citycode"]
    base_url = "https://restapi.amap.com/v5/direction/transit/integrated?"
    # 发起接口网络请求
    req_url = base_url + "origin=" + origin + "&destination=" + destination + "&city1=" + origin_citycode + "&city2=" + destination_citycode+"&key=" + os.getenv("gaode_api_key")
    response = requests.get(req_url)
    # 解析响应结果
    if response.status_code == 200:
        responseResult = response.json()
        if responseResult["status"] == "1":
            return responseResult["route"].get("transits", [{}])
        else:
            print("交通信息获取失败")
            return "交通信息获取失败"
    else:
        # 网络异常等因素，解析结果异常。可依据业务逻辑自行处理。
        print('请求异常')
        return "交通信息获取失败"

@tool
def get_transport_info(messages):
    """
    获取从origin到destination的交通信息
    
    Args:
        messages: 包含出发地、目的地和日期的JSON字符串
        
    Returns:
        包含交通信息的字典s
    """
    # 调用交通信息API
    json_messages = messages
    origin = json_messages["origin"]
    destination = json_messages["destination"]
    
    location_info = location_transform(origin, destination)
    transport_info = get_route_info(location_info)  
    return transport_info

@tool
def get_single_attraction(messages):
    """
    获取单个景点或活动的详细信息
    
    Args:
        messages: 包含景点或活动名称的JSON字符串
        
    Returns:
        包含景点或活动详细信息的字典
    """
    # 调用交通信息API
    print("messages:",messages)
    json_messages = messages.get("attractions", [])
    url = os.getenv("search_url")
    api_key = "Bearer " + os.getenv("search_api_key")
    freshness = "noLimit"
    summery = True 
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    response_list = {}
    
    for item in json_messages:
        attraction_name = item["name"]
        payload = json.dumps({
        "query": f"景点：{attraction_name}开放时间地址详细信息",
        "freshness": freshness,
        "summery": summery
        })
        response = requests.request("POST", url, headers=headers, data=payload)
        print(response.json())
        url_data = get_search_url(response.json())
        url_data = url_data[:2] if len(url_data) > 2 else url_data
        content_list = []
        for data in url_data:
            if get_url_content(data["url"]).get("error"):
                continue
            content_list.append(get_url_content(data["url"]).get("clean_text", ""))
        response_list[attraction_name] = content_list[0] if content_list else "暂无信息"
    return response_list
if __name__ == "__main__":
    from dotenv import load_dotenv
# 加载 .env 文件
    load_dotenv() 
    import time  
    start = time.time()
    output= get_search_result("成都传统特色美食 麻婆豆腐 回锅肉 担担面 龙抄手 钟水饺")
    end = time.time()
    print(output)
    print("cost time:", end - start)
    
    
