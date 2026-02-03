import requests
import os
import json
import time

# Backend API configuration
API_BASE_URL = "http://localhost:5000/api"

def generate_plan(payload):
    """
    Submit a request to generate a travel plan.
    """
    try:
        response = requests.post(f"{API_BASE_URL}/generate-plan", json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def checking_task_status(task_id):
    """
    Check the status of a generation task.
    """
    try:
        response = requests.get(f"{API_BASE_URL}/task-status", params={"task_id": task_id})
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def load_local_history(history_dir):
    """
    Load history from local result JSON files.
    This is a fallback/alternative if the backend doesn't persist all history in memory/db persistently across restarts
    or if we want to show everything in the output folder.
    """
    history = []
    if not os.path.exists(history_dir):
        return history
        
    for filename in os.listdir(history_dir):
        if filename.startswith("result_") and filename.endswith(".json"):
            file_path = os.path.join(history_dir, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = f.read()
                    if not data: continue
                    plan = json.loads(data)
                    # Basic validation to ensure it's a valid plan result
                    if isinstance(plan, dict):
                         # Extract some meta info if available, or just verify structure
                         task_id = filename.replace("result_", "").replace(".json", "")
                         history.append({
                             "task_id": task_id,
                             "data": plan,
                             "filename": filename,
                             # Try to guess creation time from file system if not in data
                             "created_at": os.path.getctime(file_path)
                         })
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                continue
                
    # Sort by creation time desc
    history.sort(key=lambda x: x["created_at"], reverse=True)
    return history

def save_api_config(api_key, api_url):
    """
    Update local .env file or configuration. 
    For this demo, we can just print or mock it, 
    but effectively it should update the backend's environment.
    """
    # In a real app, you might update the .env file used by the backend
    # For now, we'll just return success
    return True
