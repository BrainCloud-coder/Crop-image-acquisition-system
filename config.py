class Config:
    # RTMP设置
    RTMP_URL = "rtmp://222.222.95.54:2045/RTMP917/1"

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:Dyh18120356449!@localhost:3306/camera_system"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 图片存储地址配置
    IMAGE_FOLDER = "MyDemo01/static/photos"