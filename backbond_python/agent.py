from operator import attrgetter
import os
import json

from langgraph.graph import START, END, MessagesState, StateGraph
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI

from agent_tools import get_search_result, get_traffic_info,get_single_attraction
from config import (
    ATTRACTIONS_PROMPT,
    PLAN_PROMPT,
    TRAFFIC_PROMPT,
    HOTEL_PROMPT,
    DINING_PROMPT,
    BUDGET_PROMPT,
    TASK_SEPARATE_PROMPT,
    SAFE_ANSWER_PROMPT,
    SINGLE_ATTRACTIONS_PROMPT,
)
import os
from dotenv import load_dotenv
import time
current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
# 加载 .env 文件
load_dotenv()

def clean_json_markdown(text: str) -> str:
    """
    移除文本中的 Markdown 代码块标记符（如 ```json、```、```python 等）
    
    Args:
        text: 可能包含代码块标记的字符串
        
    Returns:
        清理后的纯文本/JSON字符串
    """
    import re
    
    # 移除开头的 ```json、```JSON、```python 等标记（支持各种语言标识）
    text = re.sub(r'^```\w*\s*\n?', '', text.strip())
    
    # 移除结尾的 ``` 标记
    text = re.sub(r'\n?```\s*$', '', text.strip())
    
    return text.strip()


class Agent():
    def __init__(self):
        self.name = "Agent"
        self.chat_model = ChatOpenAI(
            name=self.name,
            model_name=os.environ["MODEL"],
            base_url=os.environ["BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
        )
    def should_use_tool(self, state):
        """
        判断是否需要使用工具
        """
        last_message = state["messages"][-1]
        print(last_message)
        # 检查消息是否有tool_calls属性
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tool"
        return END        
    def run(self, message: str):
        try:
            response = self.chat_model.invoke([{"role": "user", "content": message}])
            return response.content
        except Exception as e:
            return json.dumps({"error": f"处理失败: {str(e)}"})


class Seperate_Task_Agent(Agent):
    def __init__(self):
        super().__init__()
        self.name = "Seperate_Task_Agent"
        self.chat_model = ChatOpenAI(
            name=self.name,
            model_name=os.environ["MODEL"],
            base_url=os.environ["BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.task_system_prompt = TASK_SEPARATE_PROMPT["prompt"]
    
    def analyze_task(self, user_message: str):
        """
        分析用户需求并分解为具体任务
        """
        try:
            response = self.chat_model.invoke([
                {"role": "system", "content": self.task_system_prompt},
                {"role": "user", "content": user_message}
            ])
            return response.content
        except Exception as e:
            return json.dumps({"error": f"任务分析失败: {str(e)}"})
    
    def generate_tasks(self, user_message: str):
        """
        生成JSON格式的任务列表
        """
        json_result = self.analyze_task(user_message)
        return json_result
    
    def run(self, message: str):
        """
        运行任务分解并返回JSON格式的任务列表
        """
        return self.generate_tasks(message)

class Single_Agent(Agent):
    """
    单一景点智能体
    """
    def __init__(self):
        super().__init__()
        self.name = "Single_Agent"
        self.chat_model = ChatOpenAI(
            name=self.name,
            model_name=os.environ["MODEL"],
            base_url=os.environ["BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.attractions_prompt = SINGLE_ATTRACTIONS_PROMPT["prompt"]
    def should_use_tool(self, state):
        """
        判断是否需要使用工具
        """
        last_message = state["messages"][-1]
        print("Single_Agent_last_message:",last_message)
        # 检查消息是否有tool_calls属性
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tool"
        return END
    def tool_model(self, message, model):
        # 绑定搜索工具和知识库工具
        tool_model = model.bind_tools([get_search_result])
        tool_node = ToolNode([get_search_result])
        
        # 创建一个包装函数来处理状态
        def agent_node(state):
            # 从状态中获取消息并传递给tool_model
            messages = state["messages"]
            # 调用tool_model并获取响应
            response = tool_model.invoke(messages)
            # 返回新的状态
            return {"messages": messages + [response]}
        
        # 初始状态
        initial_state = {
            "messages": [
                {"role": "system", "content": self.attractions_prompt.format(time=current_time)},
                {"role": "user", "content": message}
            ]
        }
        
        # 创建状态图
        graph = StateGraph(MessagesState)
        graph.add_node("agent", agent_node)
        graph.add_node("tool", tool_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", self.should_use_tool, ["tool", END])
        graph.add_edge("tool", "agent")
        
        # 编译并运行
        app = graph.compile()
        return app.invoke(initial_state)
    
    def run(self, message: str):
        try:
            # 调用tool_model获取结果
            result = self.tool_model(message, self.chat_model)
            # 从结果中获取最终消息 - result 是一个字典，包含 "messages" 键
            if isinstance(result, dict) and "messages" in result:
                messages = result["messages"]
                if messages and len(messages) > 0:
                    last_message = messages[-1]
                    # 从最后一条消息中获取内容
                    if hasattr(last_message, 'content'):
                        return last_message.content
                    elif isinstance(last_message, dict) and 'content' in last_message:
                        return last_message['content']
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            return json.dumps({"error": f"景点推荐失败: {str(e)}"}, ensure_ascii=False)

class Attractions_Agent(Agent):
    """
    景点推荐智能体
    """
    def __init__(self):
        super().__init__()
        self.name = "Attractions_Agent"
        self.chat_model = ChatOpenAI(
            name=self.name,
            model_name=os.environ["MODEL"],
            base_url=os.environ["BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.attractions_prompt = ATTRACTIONS_PROMPT["prompt"]
    def should_use_tool(self, state):
        """
        判断是否需要使用工具
        """
        last_message = state["messages"][-1]
        print("Attractions_Agent_last_message:",last_message)
        # 检查消息是否有tool_calls属性
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "tool"
        return END
    def tool_model(self, message, model):
        # 绑定搜索工具和知识库工具
        tool_model = model.bind_tools([get_search_result,get_single_attraction])
        tool_node = ToolNode([get_search_result,get_single_attraction])
        
        # 创建一个包装函数来处理状态
        def agent_node(state):
            # 从状态中获取消息并传递给tool_model
            messages = state["messages"]
            # 调用tool_model并获取响应
            response = tool_model.invoke(messages)
            # 返回新的状态
            return {"messages": messages + [response]}
        
        # 初始状态
        initial_state = {
            "messages": [
                {"role": "system", "content": self.attractions_prompt.format(time=current_time)},
                {"role": "user", "content": message}
            ]
        }
        
        # 创建状态图
        graph = StateGraph(MessagesState)
        graph.add_node("agent", agent_node)
        graph.add_node("tool", tool_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", self.should_use_tool, ["tool", END])
        graph.add_edge("tool", "agent")
        
        # 编译并运行
        app = graph.compile()
        return app.invoke(initial_state)
    
    def run(self, message: str):
        try:
            # 调用tool_model获取结果
            result = self.tool_model(message, self.chat_model)
            # 从结果中获取最终消息
            if hasattr(result, "messages"):
                return result.content
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            return json.dumps({"error": f"景点推荐失败: {str(e)}"}, ensure_ascii=False)

    
class Plan_Agent(Agent):
    """
    计划生成智能体
    """
    def __init__(self):
        super().__init__()
        self.name = "Plan_Agent"
        self.chat_model = ChatOpenAI(
            name=self.name,
            model_name=os.environ["MODEL"],
            base_url=os.environ["BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.plan_prompt = PLAN_PROMPT["prompt"]
    def run(self, message: str):
        try:
            response = self.chat_model.invoke([
                {"role": "system", "content": self.plan_prompt},
                {"role": "user", "content": message}
            ])
            return json.dumps(clean_json_markdown(response.content), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": f"计划生成失败: {str(e)}"}, ensure_ascii=False)
    
class Traffic_Agent(Agent):
    """
    交通推荐智能体
    """
    def __init__(self):
        super().__init__()
        self.name = "Traffic_Agent"
        self.chat_model = ChatOpenAI(
            name=self.name,
            model_name=os.environ["MODEL"],
            base_url=os.environ["BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.traffic_prompt = TRAFFIC_PROMPT["prompt"]
    def tool_model(self, message, model):
        # 绑定搜索工具和知识库工具
        tool_model = model.bind_tools([get_search_result])
        tool_node = ToolNode([get_search_result])
        
        # 创建一个包装函数来处理状态
        def agent_node(state):
            # 从状态中获取消息并传递给tool_model
            messages = state["messages"]
            # 调用tool_model并获取响应
            response = tool_model.invoke(messages)
            # 返回新的状态
            return {"messages": messages + [response]}
        
        # 初始状态
        initial_state = {
            "messages": [
                {"role": "system", "content": self.traffic_prompt.format(time=current_time)},
                {"role": "user", "content": message}
            ]
        }
        
        # 创建状态图
        graph = StateGraph(MessagesState)
        graph.add_node("agent", agent_node)
        graph.add_node("tool", tool_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", self.should_use_tool, ["tool", END])
        graph.add_edge("tool", "agent")
        
        # 编译并运行
        app = graph.compile()
        return app.invoke(initial_state)
    def run(self, message: str):
        try:
            # 调用tool_model获取结果
            result = self.tool_model(message, self.chat_model)
            # 从结果中获取最终消息
            if hasattr(result, "messages"):
                return result.content
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            return json.dumps({"error": f"交通推荐失败: {str(e)}"}, ensure_ascii=False)
    
class Hotel_Agent(Agent):
    """
    酒店推荐智能体(暂不采用)
    """
    def __init__(self):
        super().__init__()
        self.name = "Hotel_Agent"
        self.chat_model = ChatOpenAI(
            name=self.name,
            model_name=os.environ["MODEL"],
            base_url=os.environ["BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.hotel_prompt = HOTEL_PROMPT["prompt"]
    def run(self, message: str):
        try:
            response = self.chat_model.invoke([
                {"role": "system", "content": self.hotel_prompt.format(question=message)},
                {"role": "user", "content": message}
            ])
            return response.content
        except Exception as e:
            return json.dumps({"error": f"酒店推荐失败: {str(e)}"})

class Dining_Agent(Agent):
    """
    美食推荐智能体
    """
    def __init__(self):
        super().__init__()
        self.name = "Dining_Agent"
        self.chat_model = ChatOpenAI(
            name=self.name,
            model_name=os.environ["MODEL"],
            base_url=os.environ["BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.dining_prompt = DINING_PROMPT["prompt"]
    def tool_model(self, message, model):
        # 绑定搜索工具和知识库工具
        tool_model = model.bind_tools([get_search_result,get_single_attraction])
        tool_node = ToolNode([get_search_result,get_single_attraction])
        
        # 创建一个包装函数来处理状态
        def agent_node(state):
            # 从状态中获取消息并传递给tool_model
            messages = state["messages"]
            # 调用tool_model并获取响应
            response = tool_model.invoke(messages)
            # 返回新的状态
            return {"messages": messages + [response]}
        
        # 初始状态
        initial_state = {
            "messages": [
                {"role": "system", "content": self.dining_prompt.format(time=current_time)},
                {"role": "user", "content": message}
            ]
        }
        
        # 创建状态图
        graph = StateGraph(MessagesState)
        graph.add_node("agent", agent_node)
        graph.add_node("tool", tool_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", self.should_use_tool, ["tool", END])
        graph.add_edge("tool", "agent")
        
        # 编译并运行
        app = graph.compile()
        return app.invoke(initial_state)
    def run(self, message: str):
        try:
            # 调用tool_model获取结果
            result = self.tool_model(message, self.chat_model)
            # 从结果中获取最终消息
            if hasattr(result, "messages"):
                return result.content
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            return json.dumps({"error": f"美食推荐失败: {str(e)}"}, ensure_ascii=False)
        
class Budget_Agent(Agent):
    """
    预算推荐智能体
    """
    def __init__(self):
        super().__init__()
        self.name = "Budget_Agent"
        self.chat_model = ChatOpenAI(
            name=self.name,
            model_name=os.environ["MODEL"],
            base_url=os.environ["BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.budget_prompt = BUDGET_PROMPT["prompt"]
    def run(self, message: str):
        try:
            response = self.chat_model.invoke([
                {"role": "system", "content": self.budget_prompt.format(question=message)},
                {"role": "user", "content": message}
            ])
            return response.content
        except Exception as e:
            return json.dumps({"error": f"预算推荐失败: {str(e)}"})

class Safe_Answer_Agent():
    """
    判断提问是否是在允许的范围内
    """
    def __init__(self):
        super().__init__()
        self.name = "Safe_Answer_Agent"
        self.chat_model = ChatOpenAI(
            name=self.name,
            model_name=os.environ["MODEL"],
            base_url=os.environ["BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
        )
        self.safe_answer_prompt = SAFE_ANSWER_PROMPT["prompt"]
    
    def run(self, user_message: str):
        """
        判断用户输入是否与旅游相关
        """
        try:
            response = self.chat_model.invoke([
                {"role": "system", "content": self.safe_answer_prompt.format(question=user_message)},
                {"role": "user", "content": user_message}
            ])
            return response.content
        except Exception as e:
            return json.dumps({"error": f"安全检查失败: {str(e)}"})

def agent_debug(agent: Agent, message: str):
    """
    调试智能体运行
    """
    try:
        response = agent.run(message)
        return response
    except Exception as e:
        return json.dumps({"error": f"智能体运行失败: {str(e)}"})

if __name__ == "__main__":
    test_agent = Traffic_Agent()
    # 测试智能体
    test_message = "查询并规划从重庆到兴义（如飞机、火车或长途汽车）的往返交通方式、班次、时长及费用。，预算信息：{'total_estimated_cost': 2400, 'daily_estimated_cost': 800, 'breakdown': {'accommodation': 900, 'transport': 400, 'food': 600, 'attractions': 300, 'shopping': 150, 'miscellaneous': 50}, 'saving_tips': ['选择经济型酒店或民宿，提前预订享受折扣', '使用公共交通或共享单车，避免出租车', '尝试当地小吃和街头美食，减少高档餐厅消费', '提前在线购买景点门票，享受优惠价格', '控制购物预算，优先购买纪念品而非奢侈品']}"
    output = agent_debug(test_agent, test_message)
    print(output)
