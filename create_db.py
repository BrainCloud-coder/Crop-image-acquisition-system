from app import create_app
from db_model import db

app = create_app()

with app.app_context():
    # 确保数据库连接已配置
    if not hasattr(app, 'extensions') or 'sqlalchemy' not in app.extensions:
        db.init_app(app)
    
    # 创建所有表
    db.create_all()
    print("数据库表创建成功！")