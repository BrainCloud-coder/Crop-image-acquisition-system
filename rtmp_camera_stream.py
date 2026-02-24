"""
CameraStream类用于从RTMP流采集图像帧，并以MJPEG流的方式推送给前端。
支持帧队列、线程采集、图片解码、定时保存等功能。
"""

import cv2 
import threading # 线程
import time
from queue import Queue, Empty # 队列
import logging
import os
from datetime import datetime
import numpy as np

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RtmpCameraStream:
    def __init__(self, url, save_folder, save_interval_minutes=10):
        """
        初始化RTMP摄像头流对象

        参数:
            url (str): RTMP流地址（例如：rtmp://server/live/stream）
            save_folder (str): 保存图像的文件夹路径
            save_interval_minutes (int): 保存图像的间隔时间（分钟）
        
        属性:
            url: RTMP流地址
            cap: OpenCV视频捕获对象
            frame_queue: 帧队列，用于存储编码为JPEG的帧数据
            running: 控制采集线程的运行标志
            last_frame: 保存最后一帧用于错误恢复
            last_save_time: 上一次保存图像的时间戳
            save_folder: 保存图像的文件夹路径
            save_interval: 保存图像的间隔时间（秒）
            thread: 采集线程对象
        """
        self.url = url  # RTMP流地址
        self.cap = None 
        self.frame_queue = Queue(maxsize=5)  # 稍微增大队列大小以减少丢帧
        self.running = True  # 控制采集线程的运行
        self.last_frame = None  # 保存最后一帧用于错误恢复
        self.last_save_time = time.time()  # 上一次保存图像的时间
        self.save_folder = save_folder  # 保存图像的文件夹
        self.save_interval = save_interval_minutes * 60  # 转换为秒
        
        # 创建保存文件夹
        self._create_save_folder()
        
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)  # 采集线程
        self._init_capture()  # 初始化视频捕获
        self.thread.start()  # 启动采集线程

    def _create_save_folder(self):
        """创建保存图像的文件夹"""
        try:
            if not os.path.exists(self.save_folder):
                os.makedirs(self.save_folder)
                logger.info(f"创建保存文件夹: {self.save_folder}")
        except Exception as e:
            logger.error(f"创建文件夹失败: {e}")

    def _init_capture(self):
        """
        初始化视频捕获对象
        尝试打开RTMP流并设置相关参数：
        - 设置缓冲区大小为1以减少延迟
        - 检查流是否成功打开
        
        返回:
            bool: 初始化成功返回True，否则返回False
        """
        if self.cap is not None:
            self.cap.release()  # 释放之前的捕获对象
        
        self.cap = cv2.VideoCapture(self.url)  # 创建新的视频捕获对象
        # 设置缓冲区大小，减少延迟
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # 设置帧率（如果知道RTMP流的帧率）
        # self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        if not self.cap.isOpened():
            logger.error(f"无法打开RTMP流: {self.url}")
            return False
        return True

    def _capture_loop(self):
        """
        采集线程主循环，不断从RTMP流获取最新帧，编码为JPEG后放入队列
        
        处理逻辑：
        1. 检查捕获对象是否有效，无效则尝试重新初始化
        2. 读取帧，如果失败则增加错误计数，连续错误超过阈值时重新连接
        3. 成功读取帧后重置错误计数，将帧编码为JPEG格式
        4. 保存最后一帧用于错误恢复
        5. 维护帧队列，确保只保留最新帧以避免延迟
        6. 检查是否到达保存间隔时间，如果是则保存当前帧
        """
        consecutive_errors = 0  # 连续错误计数
        max_errors = 5  # 最大连续错误次数
        
        while self.running:  # 主循环，直到running标志为False
            try:
                # 检查捕获对象是否有效
                if not self.cap or not self.cap.isOpened():
                    if not self._init_capture():  # 尝试重新初始化
                        time.sleep(1)  # 等待一秒后重试
                        continue
                
                # 从RTMP流读取一帧
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    logger.warning("读取RTMP帧失败")
                    consecutive_errors += 1
                    # 连续错误超过阈值时重新连接
                    if consecutive_errors > max_errors:
                        logger.error("连续读取失败，尝试重新连接")
                        self.cap.release()
                        self.cap = None
                        consecutive_errors = 0
                    time.sleep(0.1)  # 短暂等待后重试
                    continue
                
                consecutive_errors = 0  # 重置错误计数
                
                # 检查是否到达保存间隔时间
                current_time = time.time()
                if current_time - self.last_save_time >= self.save_interval:
                    self._save_frame(frame)  # 保存当前帧
                    self.last_save_time = current_time  # 更新保存时间
                
                # 将帧编码为JPEG格式，质量为80%
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not ret:
                    logger.warning("JPEG编码失败")
                    continue
                
                # 转换为字节数据
                frame_data = jpeg.tobytes()
                self.last_frame = frame_data  # 保存最后一帧用于错误恢复
                
                # 维护帧队列，只保留最新帧
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()  # 丢弃最旧的帧
                    except Empty:
                        pass  # 队列为空时忽略异常
                
                self.frame_queue.put(frame_data)  # 将新帧加入队列
                
            except Exception as e:
                logger.error(f"采集线程发生错误: {e}")
                time.sleep(0.1)  # 错误后短暂等待

    def _save_frame(self, frame):
        """
        保存当前帧到指定文件夹
        
        参数:
            frame: 要保存的图像帧
        """
        try:
            # 生成文件名：时间戳格式
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"frame_{timestamp}.jpg"
            filepath = os.path.join(self.save_folder, filename)
            
            # 保存图像
            cv2.imwrite(filepath, frame)
            logger.info(f"已保存帧图像: {filepath}")
            
        except Exception as e:
            logger.error(f"保存帧图像失败: {e}")

    def stream(self, fps=30):
        """
        MJPEG流生成器，供Flask Response使用
        
        参数:
            fps (int): 目标帧率，默认30fps
            
        返回:
            generator: 生成MJPEG格式的帧数据
            
        处理逻辑：
        1. 计算每帧的时间间隔以控制帧率
        2. 尝试从队列获取最新帧，若无新帧则使用最后一帧
        3. 按照MJPEG格式封装帧数据
        4. 通过sleep控制输出帧率
        """
        interval = 1.0 / fps  # 计算每帧间隔时间
        
        while True:
            try:
                # 尝试获取最新帧，如果没有新帧则使用最后一帧
                try:
                    frame = self.frame_queue.get(timeout=0.1)
                except Empty:
                    frame = self.last_frame
                
                if frame:
                    # 生成MJPEG流格式（包含HTTP头部和帧数据）
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                
                time.sleep(interval)  # 控制输出帧率
                
            except Exception as e:
                logger.error(f"流生成器发生错误: {e}")
                # 发生错误时返回最后一帧
                if self.last_frame:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + self.last_frame + b'\r\n')
                time.sleep(interval)

    def stop(self):
        """
        停止采集线程，安全退出
        
        处理逻辑：
        1. 设置running标志为False以终止采集循环
        2. 等待采集线程结束（最多等待1秒）
        3. 释放视频捕获对象
        """
        self.running = False  # 设置标志以终止采集循环
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)  # 等待线程结束
        if hasattr(self, 'cap') and self.cap and self.cap.isOpened():
            self.cap.release()  # 释放视频捕获资源

    def save_current_frame(self, filepath=None):
        """
        手动保存当前帧到指定路径
        
        参数:
            filepath (str): 保存路径，如果为None则使用默认命名
            
        返回:
            bool: 保存成功返回True，否则返回False
        """
        try:
            if self.last_frame is None:
                logger.warning("没有可用的帧可以保存")
                return False
            
            # 如果没有指定路径，使用时间戳命名
            if filepath is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = os.path.join(self.save_folder, f"manual_{timestamp}.jpg")
            
            # 将JPEG字节数据转换回图像并保存
            jpeg_array = np.frombuffer(self.last_frame, dtype=np.uint8)
            frame = cv2.imdecode(jpeg_array, cv2.IMREAD_COLOR)
            cv2.imwrite(filepath, frame)
            logger.info(f"手动保存帧图像: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"手动保存帧图像失败: {e}")
            return False

    def set_save_interval(self, minutes):
        """
        设置保存间隔时间
        
        参数:
            minutes (int): 保存间隔时间（分钟）
        """
        self.save_interval = minutes * 60
        logger.info(f"保存间隔时间已设置为: {minutes}分钟")

    def get_save_info(self):
        """
        获取保存相关信息
        
        返回:
            dict: 包含保存文件夹路径、间隔时间等信息
        """
        return {
            'save_folder': self.save_folder,
            'save_interval_minutes': self.save_interval // 60,
            'next_save_time': self.last_save_time + self.save_interval
        }