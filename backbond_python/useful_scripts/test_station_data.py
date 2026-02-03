import requests

# 12306车站数据文件URL
url = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js"

try:
    response = requests.get(url)
    response.encoding = "utf-8"
    
    print("请求成功！")
    print("状态码:", response.status_code)
    print("\n文件内容前500字符:")
    print(response.text[:500])
    
    # 保存文件内容以便分析
    with open("station_data.txt", "w", encoding="utf-8") as f:
        f.write(response.text)
    
    print("\n完整内容已保存到 station_data.txt 文件")
    
except Exception as e:
    print("请求失败:", str(e))
