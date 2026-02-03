from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import json
from datetime import datetime, timedelta
import random
import uuid
import threading
from route_generate import generate_travel_plan, single_agent
from utils.context_manager import ContextManager
from generate_daily_posters import DailyPosterGenerator

# Initialize context manager
context_manager = ContextManager()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Set a secret key for session management

# Enable CORS
CORS(app)

# 任务存储（生产环境建议使用 Redis）
# 结构: {task_id: {"status": "pending/completed/failed", "result": ..., "created_at": ..., "error": ...}}
tasks = {}
tasks_lock = threading.Lock()

def run_generate_plan_task(task_id, origin, destination, days, budget_level, preferences, start_date):
    """在后台线程中执行旅行计划生成任务"""
    try:
        print(f"[Task {task_id}] 开始执行...")
        result = generate_travel_plan(origin, destination, days, budget_level, preferences, start_date)
        
        # 生成海报
        print(f"[Task {task_id}] 开始生成海报...")
        with open(f"./result_{task_id}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        generator = DailyPosterGenerator(result)
        posters = generator.generate_all_posters()
        
        with tasks_lock:
            tasks[task_id]["status"] = "completed"
            tasks[task_id]["result"] = result
            tasks[task_id]["posters"] = posters
            tasks[task_id]["completed_at"] = datetime.now().isoformat()
        print(f"[Task {task_id}] 执行完成")
    except Exception as e:
        import traceback
        traceback.print_exc()
        with tasks_lock:
            tasks[task_id]["status"] = "failed"
            tasks[task_id]["error"] = str(e)
            tasks[task_id]["completed_at"] = datetime.now().isoformat()
        print(f"[Task {task_id}] 执行失败: {str(e)}")

# Route for home page
# @app.route('/')
# def home():
#     return render_template('index.html')

# API endpoint for generating travel plan (异步模式)
@app.route('/api/generate-plan', methods=['POST'], endpoint='api_generate_plan')
def api_generate_plan():
    data = request.json
    destination = data.get('destination')
    origin = data.get('origin')
    days = int(data.get('days', 3))
    budget_level = data.get('budget_level')
    preferences = data.get('preferences', [])
    start_date = data.get('start_date', datetime.now().strftime("%Y-%m-%d"))
    
    print(f"收到请求: {destination}, {days}, {budget_level}, {preferences}, {start_date}")
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 创建任务记录
    with tasks_lock:
        tasks[task_id] = {
            "status": "pending",
            "result": None,
            "posters": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "params": {
                "destination": destination,
                "origin": origin,
                "days": days,
                "budget_level": budget_level,
                "preferences": preferences,
                "start_date": start_date
            }
        }
    
    # 启动后台线程执行任务
    thread = threading.Thread(
        target=run_generate_plan_task,
        args=(task_id, origin, destination, days, budget_level, preferences, start_date),
        daemon=True
    )
    thread.start()
    
    # 立即返回任务ID
    return jsonify({
        "task_id": task_id,
        "status": "pending",
        "message": "任务已提交，正在生成旅游攻略..."
    })

# API endpoint for chat (异步模式)
@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    destination = data.get('destination')
    origin = data.get('origin')
    days = int(data.get('days', 3))
    budget_level = data.get('budget_level')
    preferences = data.get('preferences', [])
    start_date = data.get('start_date', datetime.now().strftime("%Y-%m-%d"))
    
    print(f"收到请求: {destination}, {days}, {budget_level}, {preferences}, {start_date}")
    
    # 生成任务ID
    task_id = str(uuid.uuid4())
    
    # 创建任务记录
    with tasks_lock:
        tasks[task_id] = {
            "status": "pending",
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "params": {
                "destination": destination,
                "origin": origin,
                "days": days,
                "budget_level": budget_level,
                "preferences": preferences,
                "start_date": start_date
            }
        }
    
    # 启动后台线程执行任务
    thread = threading.Thread(
        target=run_generate_plan_task,
        args=(task_id, origin, destination, days, budget_level, preferences, start_date),
        daemon=True
    )
    thread.start()
    
    # 立即返回任务ID
    return jsonify({
        "task_id": task_id,
        "status": "pending",
        "message": "任务已提交，正在生成旅游攻略..."
    })

# API endpoint for querying task status
@app.route('/api/task-status', methods=['GET'])
def api_task_status():
    task_id = request.args.get('task_id')
    
    if not task_id:
        return jsonify({"error": "缺少 task_id 参数"}), 400
    
    with tasks_lock:
        if task_id not in tasks:
            return jsonify({"error": "任务不存在"}), 404
        
        task = tasks[task_id]
        response = {
            "task_id": task_id,
            "status": task["status"],
            "created_at": task["created_at"]
        }
        
        if task["status"] == "completed":
            response["result"] = task["result"]
            response["posters"] = task.get("posters")
            response["completed_at"] = task.get("completed_at")
        elif task["status"] == "failed":
            response["error"] = task["error"]
            response["completed_at"] = task.get("completed_at")
    
    return jsonify(response)

# API endpoint for updating plan and regenerating posters
@app.route('/api/update-plan', methods=['POST'])
def api_update_plan():
    """更新行程数据并重新生成海报"""
    data = request.json
    task_id = data.get('task_id')
    daily_plans = data.get('daily_plans')
    
    if not task_id:
        return jsonify({"error": "缺少 task_id 参数"}), 400
    
    if not daily_plans:
        return jsonify({"error": "缺少 daily_plans 参数"}), 400
    
    with tasks_lock:
        if task_id not in tasks:
            return jsonify({"error": "任务不存在"}), 404
        
        task = tasks[task_id]
        
        # 更新 result 中的 daily_plans
        if task.get("result"):
            task["result"]["daily_plans"] = daily_plans
        else:
            task["result"] = {"daily_plans": daily_plans}
    
    try:
        # 重新生成海报
        print(f"[Task {task_id}] 重新生成海报...")
        generator = DailyPosterGenerator({"daily_plans": daily_plans})
        posters = generator.generate_all_posters()
        
        with tasks_lock:
            tasks[task_id]["posters"] = posters
            tasks[task_id]["updated_at"] = datetime.now().isoformat()
        
        return jsonify({
            "success": True,
            "message": "海报更新成功",
            "posters": posters
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

#定期清理过期会话的函数
@app.before_request
def cleanup_expired_sessions():
    import threading
    import time
    
    def cleanup_task():
        # 每小时清理一次过期会话（超过24小时未活动）
        while True:
            context_manager.cleanup_expired_sessions(expiration_hours=24)
            time.sleep(3600)  # 3600秒 = 1小时
    
    # 启动清理线程
    if not hasattr(app, '_cleanup_thread_started'):
        app._cleanup_thread_started = True
        thread = threading.Thread(target=cleanup_task, daemon=True)
        thread.start()

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')
