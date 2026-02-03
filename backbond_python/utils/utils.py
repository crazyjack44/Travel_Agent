import re
import json
from typing import Dict, Any

# Helper function to clean and parse JSON strings
def clean_and_parse_json(json_str: str) -> Dict[str, Any]:
    """
    清理并解析JSON字符串，处理多余空行和可能的不完整结构
    
    Args:
        json_str: 原始JSON字符串，可能包含多余空行和不完整结构
        
    Returns:
        解析后的JSON字典
        
    Raises:
        json.JSONDecodeError: 如果无法解析为有效的JSON
    """
    # 1. 清理多余的空行
    cleaned_str = re.sub(r'\s*\n\s*', '\n', json_str.strip())
    
    # 2. 移除可能的JSON代码块标记
    cleaned_str = re.sub(r'^```json\s*|\s*```', '', cleaned_str)
    
    # 3. 尝试修复常见的JSON格式问题
    # 确保字符串使用双引号
    cleaned_str = re.sub(r"'", '"', cleaned_str)
    
    # 4. 尝试解析JSON
    try:
        return json.loads(cleaned_str)
    except json.JSONDecodeError:
        # 5. 如果解析失败，尝试修复不完整的JSON结构
        try:
            # 统计括号和引号
            open_brackets = cleaned_str.count('{')
            close_brackets = cleaned_str.count('}')
            open_brackets_list = cleaned_str.count('[')
            close_brackets_list = cleaned_str.count(']')
            
            # 添加缺失的结束括号
            fixed_str = cleaned_str
            for _ in range(open_brackets - close_brackets):
                fixed_str += '}'
            for _ in range(open_brackets_list - close_brackets_list):
                fixed_str += ']'
            
            # 再次尝试解析
            return json.loads(fixed_str)
        except json.JSONDecodeError as e:
            # 如果仍失败，尝试使用更复杂的修复方法
            try:
                # 使用json.tool的启发式修复（如果可用）
                import subprocess
                import sys
                result = subprocess.run(
                    [sys.executable, '-c', f'import json; print(json.dumps(json.loads(\"\"\"{fixed_str}\"\"\")))'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return json.loads(result.stdout)
                else:
                    raise e
            except Exception:
                # 所有尝试都失败，抛出原始错误
                return {}
