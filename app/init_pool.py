"""
初始化邮箱池：向数据库中预填 200 个空闲邮箱前缀
"""
import sys
import os

# 将当前目录加入路径以便导入 models
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Session, EmailRoute, init_db

def init_pool(count=200):
    init_db()
    db = Session()
    try:
        # 检查是否已有数据
        total = db.query(EmailRoute).count()
        if total > 0:
            print(f"数据库中已有 {total} 条记录，跳过初始化。")
            return

        print(f"正在生成 {count} 个邮箱前缀...")
        for i in range(1, count + 1):
            local_part = f"mail{1000 + i}"  # mail1001, mail1002...
            db.add(EmailRoute(
                local_part=local_part,
                order_id=None,  # None 表示空闲
                active=False
            ))
        
        db.commit()
        print(f"成功初始化 {count} 个预览邮箱点位。")
    except Exception as e:
        print(f"初始化失败: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_pool(200)
