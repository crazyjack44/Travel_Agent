import yaml

PROMPT_PATH = "./roleplay"


with open(f"{PROMPT_PATH}/plan_prompt.yaml", "r", encoding="utf-8") as f:
    PLAN_PROMPT = yaml.safe_load(f)
with open(f"{PROMPT_PATH}/traffic_prompt.yaml", "r", encoding="utf-8") as f:
    TRAFFIC_PROMPT = yaml.safe_load(f)
with open(f"{PROMPT_PATH}/hotel_prompt.yaml", "r", encoding="utf-8") as f:
    HOTEL_PROMPT = yaml.safe_load(f)
with open(f"{PROMPT_PATH}/budget_prompt.yaml", "r", encoding="utf-8") as f:
    BUDGET_PROMPT = yaml.safe_load(f)
with open(f"{PROMPT_PATH}/dining_prompt.yaml", "r", encoding="utf-8") as f:
    DINING_PROMPT = yaml.safe_load(f)
with open(f"{PROMPT_PATH}/task_seperate_prompt.yaml", "r", encoding="utf-8") as f:
    TASK_SEPARATE_PROMPT = yaml.safe_load(f)
with open(f"{PROMPT_PATH}/attractions_prompt.yaml", "r", encoding="utf-8") as f:
    ATTRACTIONS_PROMPT = yaml.safe_load(f)
with open(f"{PROMPT_PATH}/safe_answer_prompt.yaml", "r", encoding="utf-8") as f:
    SAFE_ANSWER_PROMPT = yaml.safe_load(f)
with open(f"{PROMPT_PATH}/single_attraction_prompt.yaml", "r", encoding="utf-8") as f:
    SINGLE_ATTRACTIONS_PROMPT = yaml.safe_load(f)
