import json
import concurrent.futures

from roleplay import *
from agent import Seperate_Task_Agent, Safe_Answer_Agent, Budget_Agent, Attractions_Agent, Dining_Agent, Hotel_Agent, Traffic_Agent, Plan_Agent, Single_Agent
from utils.utils import clean_and_parse_json
from langchain_core.messages import messages_to_dict, messages_from_dict

def single_agent(origin,destination, days, budget_level, preferences, start_date):
    safe_answer_agent = Safe_Answer_Agent()
    single_agent = Single_Agent()
    user_message = f"我的出发地是{origin}，要去{destination}，计划{days}天，预算{budget_level}元，偏好{preferences}，出发时间为{start_date}"
    try:
        safety_check_result = safe_answer_agent.run(user_message)
        clean_safety_check_result = clean_and_parse_json(safety_check_result)
        safety_check_result = clean_safety_check_result if clean_safety_check_result else safety_check_result   
        try:
            safety_data = json.loads(safety_check_result) if isinstance(safety_check_result, str) else safety_check_result
        except json.JSONDecodeError:
            safety_data = safety_check_result 
        
        # Check if the input is allowed/travel-related
        is_travel_related = False
        if isinstance(safety_data, dict):
            is_allowed = safety_data.get("is_allowed", False)
            category = safety_data.get("category", "").lower()
            is_travel_related = is_allowed or "旅游" in category or "旅行" in category or "travel" in category
        elif isinstance(safety_data, str):
            is_travel_related = "旅游" in safety_data or "旅行" in safety_data or "travel" in safety_data.lower() or '"is_allowed": true' in safety_data.lower()
        
        if not is_travel_related:
            return {
                "error": "输入内容不符合旅游相关要求",
                "message": "请提供与旅游规划相关的内容",
                "safety_check_result": safety_data
            }
    except Exception as e:
        # If safety check fails, we'll still proceed with the task separation
        print(f"安全检查过程中出现错误: {str(e)}")
    llm_result = single_agent.run(user_message)
    # 将结果包装成小程序期望的格式
    if isinstance(llm_result, str):
        return {
            "content": llm_result,
            "message": llm_result
        }
    return llm_result

# Function to generate travel plan
def generate_travel_plan(origin,destination, days, budget_level, preferences, start_date):
    # Initialize all agents once for efficiency
    safe_answer_agent = Safe_Answer_Agent()
    task_seperate_agent = Seperate_Task_Agent()
    attractions_agent = Attractions_Agent()
    traffic_agent = Traffic_Agent()
    hotel_agent = Hotel_Agent()
    dining_agent = Dining_Agent()
    budget_agent = Budget_Agent()
    plan_agent = Plan_Agent()
    
    # Create user message
    user_message = f"出发地是{origin}，我要去{destination}，计划{days}天，预算{budget_level}，偏好{preferences}"
    
    # Step 1: Check if input is travel-related using Safe_Answer_Agent
    try:
        safety_check_result = safe_answer_agent.run(user_message)
        clean_safety_check_result = clean_and_parse_json(safety_check_result)
        safety_check_result = clean_safety_check_result if clean_safety_check_result else safety_check_result
        try:
            safety_data = json.loads(safety_check_result) if isinstance(safety_check_result, str) else safety_check_result
        except json.JSONDecodeError:
            safety_data = safety_check_result
        
        # Check if the input is allowed/travel-related
        is_travel_related = False
        if isinstance(safety_data, dict):
            is_allowed = safety_data.get("is_allowed", False)
            category = safety_data.get("category", "").lower()
            is_travel_related = is_allowed or "旅游" in category or "旅行" in category or "travel" in category
        elif isinstance(safety_data, str):
            is_travel_related = "旅游" in safety_data or "旅行" in safety_data or "travel" in safety_data.lower() or '"is_allowed": true' in safety_data.lower()
        
        if not is_travel_related:
            return {
                "error": "输入内容不符合旅游相关要求",
                "message": "请提供与旅游规划相关的内容",
                "safety_check_result": safety_data
            }
    except Exception as e:
        # If safety check fails, we'll still proceed with the task separation
        print(f"安全检查过程中出现错误: {str(e)}")
    
    # Step 2: Analyze and separate tasks
    try:
        tasks_response = task_seperate_agent.analyze_task(user_message)
        
        try:
            tasks = json.loads(tasks_response) if isinstance(tasks_response, str) else tasks_response
        except json.JSONDecodeError:
            tasks = tasks_response
        
        if isinstance(tasks, dict):
            tasks = tasks.get("tasks", [])
        else:
            tasks = []
        
        # Debug: Print generated tasks
        print(f"Generated tasks: {tasks}")
    except Exception as e:
        return {"error": f"任务分析失败: {str(e)}"}
    
    # Step 2: Collect outputs from all agents
    agent_outputs = {
        "attractions": None,
        "traffic": None,
        #"hotel": None,
        "dining": None,
        "budget": None
    }
    clean_budget = ""
    
    # Step 2.1: First process budget tasks to get budget information
    budget_tasks = [task for task in tasks if task["type"] == "budget"]
    if budget_tasks:
        budget_task = budget_tasks[0]
        try:
            budget_result = budget_agent.run(budget_task["description"])
            clean_budget = clean_and_parse_json(budget_result)
            agent_outputs["budget"] = clean_budget if clean_budget else budget_result
            print(f"Budget result: {clean_budget}")
        except Exception as e:
            print(f"处理预算任务时出错: {str(e)}")
    
    # Step 2.2: Process other tasks in parallel
    other_tasks = [task for task in tasks if task["type"] != "budget"]
    
    # Helper function to process each task with budget information
    def process_task(task):
        task_type_str = task["type"]
        try:
            if task_type_str == "attraction":
                # Pass budget information as a properly formatted string
                budget_info = f"，预算信息：{clean_budget}" if clean_budget else ""
                attraction_result = attractions_agent.run(task["description"] + budget_info)
                clean_attraction = attraction_result
                return "attractions", clean_attraction if clean_attraction else attraction_result
            elif task_type_str == "traffic":
                budget_info = f"，预算信息：{clean_budget}" if clean_budget else ""
                traffic_result = traffic_agent.run(task["description"] + budget_info)
                clean_traffic = traffic_result
                return "traffic", clean_traffic if clean_traffic else traffic_result
            # elif task_type_str == "hotel":
            #     hotel_result = hotel_agent.run(task["description"])
            #     clean_hotel = clean_and_parse_json(hotel_result)
            #     return "hotel", clean_hotel if clean_hotel else hotel_result
            elif task_type_str == "dining":
                budget_info = f"，预算信息：{clean_budget}" if clean_budget else ""
                dining_result = dining_agent.run(task["description"] + budget_info)
                clean_dining = dining_result
                return "dining", clean_dining if clean_dining else dining_result
            else:
                # Handle unknown task types
                print(f"未处理任务类型: {task_type_str}")
                return task_type_str, None
        except Exception as e:
            print(f"处理{task_type_str}任务时出错: {str(e)}")
            return task_type_str, None
    
    # Process other tasks in parallel
    if other_tasks:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(other_tasks), 3)) as executor:
            # Submit all tasks to the executor
            future_to_task = {executor.submit(process_task, task): task for task in other_tasks}
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_task):
                task_type, result = future.result()
                if result is not None:
                    agent_outputs[task_type] = result
    
    # Step 3: Generate comprehensive plan using Plan_Agent
    # Format all agent outputs as a single message for Plan_Agent
    plan_input = {
        "destination": destination,
        "days": days,
        "budget_level": budget_level,
        "preferences": preferences,
        "start_date": start_date,
        "agents_data": agent_outputs
    }
    
    try:
        plan_result = plan_agent.run(str(plan_input))
        with open("plan_result.json", "w", encoding="utf-8") as f:
            f.write(plan_result)
        
        # 清理并解析 JSON，处理可能的 markdown 代码块或格式问题
        clean_result = clean_and_parse_json(plan_result)
        if clean_result:
            plan_result = clean_result
        
        # 解析 JSON
        if isinstance(plan_result, str):
            plan_data = json.loads(plan_result)
        else:
            plan_data = plan_result
        
        # 处理双重序列化的情况（LLM 返回的 JSON 字符串被再次序列化）
        if isinstance(plan_data, str):
            plan_data = json.loads(plan_data)
        
        # 确保返回的是字典且包含 daily_plans
        if not isinstance(plan_data, dict):
            return {"error": "计划数据格式错误"}
        
        return plan_data
        # Extract necessary data from plan_agent result
        daily_plans = plan_data.get("daily_plans", [])
        total_cost = plan_data.get("total_cost", 0)
        acc_cost = plan_data.get("accommodation_cost", 0)
        attractions = plan_data.get("attractions", [])
        transport = plan_data.get("transport", {})
        
        # Generate summary
        summary = f"# {destination}{days}日游规划\n\n"
        summary += f"**出发日期**: {start_date}\n"
        summary += f"**预算等级**: {budget_level}\n"
        summary += f"**旅游偏好**: {', '.join(preferences) if preferences else '无特殊偏好'}\n"
        summary += f"**总预算**: ¥{total_cost:.0f}\n"
        summary += f"**日均预算**: ¥{total_cost/days:.0f}\n\n"
        
        # Generate detailed plan
        detailed_plan = "## 详细行程安排\n\n"
        for day_plan in daily_plans:
            detailed_plan += f"### 第{day_plan['day']}天 ({day_plan['date']})\n\n"
            detailed_plan += f"**当日预算**: ¥{day_plan['total_day_cost']:.0f}\n\n"
            for activity in day_plan['activities']:
                detailed_plan += f"- **{activity['time']}**: {activity['activity']} ({activity['location']})\n"
                # Add attraction description if available
                if activity['activity'] in [attr['name'] for attr in attractions]:
                    attr_desc = next((attr['description'] for attr in attractions if attr['name'] == activity['activity']), '')
                    if attr_desc:
                        detailed_plan += f"  - 描述: {attr_desc}\n"
                detailed_plan += f"  - 耗时: {activity['duration']}小时\n"
                if int(activity['cost']) > 0:
                    detailed_plan += f"  - 费用: ¥{activity['cost']}\n"
            detailed_plan += "\n"
        
        # Generate budget breakdown
        budget_breakdown = "## 预算明细\n\n"
        budget_breakdown += f"- **住宿费用**: ¥{acc_cost:.0f} ({days-1}晚)\n"
        transport_total = sum(day.get('transport_cost', 0) for day in daily_plans)
        budget_breakdown += f"- **交通费用**: ¥{transport_total:.0f}\n"
        food_total = sum(day.get('food_cost', 0) for day in daily_plans)
        budget_breakdown += f"- **餐饮费用**: ¥{food_total:.0f}\n"
        attraction_total = total_cost - acc_cost - transport_total - food_total
        budget_breakdown += f"- **景点门票**: ¥{max(0, attraction_total):.0f}\n"
        budget_breakdown += f"- **总费用**: ¥{total_cost:.0f}\n"
        
        # # Generate travel tips
        # tips = "## 旅游小贴士\n\n"
        # tips += f"1. 当地交通建议: {transport.get('local', '请参考行程中的交通安排')}\n"
        # expensive_attractions = [attr['name'] for attr in attractions if attr.get('price', 0) > 200]
        # if expensive_attractions:
        #     tips += f"2. 建议提前预订门票，尤其是热门景点如{'、'.join(expensive_attractions)}\n"
        # # Add destination-specific food recommendation
        # if destination == '北京':
        #     tips += "3. 当地特色美食推荐: 北京烤鸭\n"
        # elif destination == '上海':
        #     tips += "3. 当地特色美食推荐: 小笼包\n"
        # elif destination == '重庆' or destination == '成都':
        #     tips += "3. 当地特色美食推荐: 火锅\n"
        # else:
        #     tips += "3. 当地特色美食推荐: 请参考行程中的餐饮安排\n"
        # tips += "4. 请随身携带身份证件\n"
        # tips += "5. 关注天气变化，合理安排行程\n"
        
        return {
            "summary": summary,
            "detailed": detailed_plan,
            "budget": budget_breakdown,
            #"tips": tips,
            "daily_plans": daily_plans,
            "total_cost": total_cost
        }
    except Exception as e:
        return {"error": f"行程生成失败: {str(e)}"}

def agent_test():
    """
    测试agent
    """
    # 测试数据
    result = generate_travel_plan(
        origin="重庆",
        destination="兴义",
        days=3,
        start_date="2026-2-11",
        budget_level="中等",
        preferences=["休闲", "美食"]
    )
    # 打印结果
    print(result)

if __name__ == "__main__":
    import time
    start = time.time()
    agent_test()
    end = time.time()
    print("cost time:", end - start)
