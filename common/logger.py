import logging  # python自带的日志记录库
import os
import time


class DycLogger:
    """
    实现把日志输出到控制台以及把对应日志保存到指定文件
    """

    def __init__(self, name="addsubtitle", logger_level='INFO', stream_level='INFO', file_level='INFO'):
        # 记录器logger -> 从代码中收集对应等级的日志；
        # 处理器Handler -> 把logger收集到的日志展示到对应的平台（控制台/指定文件目录）
        # 把日志输出到控制台
        # 1.创建日志的记录器logger
        self.__logger = logging.getLogger(name)  # 参数name用于定义这个记录器的名称，如果不显示指定name则默认调用root根记录器
        # 2.设置日志记录器的等级 -> 只有高于等于这个等级的日志才会记录
        self.__logger.setLevel(
            logger_level)  # 日志的等级从低->高：logging.DEBUG->logging.INFO->logging.WARNING->logging.ERROR ->logging.CRITICAL
        # 3.创建处理器handler(StreamHandler, FileHandler)
        sh = logging.StreamHandler()  # 创建流处理器用于把日志输出到控制台
        # 4.设置处理器handler的日志等级
        sh.setLevel(stream_level)
        # 5.定义日志的输出格式
        fmt = logging.Formatter('%(asctime)s - %(filename)s:[%(lineno)s] - [%(levelname)s] - %(message)s',
                                datefmt="%Y%m%d %H:%M:%S")
        # 6.添加fmt到Handler处理器,及根据fmt设置Handler的输出格式
        sh.setFormatter(fmt)
        # 7.创建FileHandler处理器
        curr_time = time.strftime("%Y-%m_%d")  # 按年－月－日获取当前时间
        py_path = os.path.abspath(__file__)  # 获取当前py文件的绝对路径
        dir_common = os.path.dirname(py_path)  # 基于这个绝对路径推上一层目录
        dir_frame = os.path.dirname(dir_common)  # 基于dir_common获取上层目录（项目目录）
        Log_path = dir_common + "//Logs//"
        # 加入传入的路径不存在，则创建该路径
        if not os.path.exists(Log_path):
            os.makedirs(Log_path)  # makedirs方法创建指定路径
        file_path = Log_path + curr_time + ".log"  # 获取到根目录后进行目录的拼接
        fh = logging.FileHandler(file_path, mode='a', encoding='utf-8')
        # 8.设置fh等级
        fh.setLevel(file_level)
        # 9. 设置fh的输出格式
        fh.setFormatter(fmt)
        # 把设置好的Handler处理器，添加到记录器logger中
        if not self.__logger.handlers:
            self.__logger.addHandler(sh)
            self.__logger.addHandler(fh)

    def get_logger(self):
        return self.__logger


logger = DycLogger().get_logger()