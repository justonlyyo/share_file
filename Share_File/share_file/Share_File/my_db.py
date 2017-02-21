# -*- encoding: utf-8 -*-
# 数据库连接模块
# __author__ = 'Administrator'

import pymysql
import time
import redis
import string
import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

"""配置数据库相关参数"""
sql_host = "120.76.145.87"  # 生产用数据库地址
user = "root"  # 生产用数据库账户
password = "QWEasd123"  # 生产用数据库密码
database = "share_file"  # 数据库名称
charset = "utf8"  # 数据库字符集
pool_size = 5  # 数据库连接池
max_overflow = 2  # 数据库连接溢出数
pool_recycle = 3600  # 数据库连接超时回收时间


def get_conn(host='127.0.0.1', user=user, password=password, database=database, charset=charset):
    """返回mysql数据库连接"""
    flag = True
    while flag:
        try:
            conn = pymysql.connect(host, user, password, database, charset=charset)
            flag = False
        except:
            print("数据库连接失败，请等待重试...")
            flag = True
            time.sleep(3)
    return conn


class MyRedis:
    """获取redis的客户端"""

    def __init__(self):
        """注意，数据的存储方式都是：表名+_+主键"""
        pass

    def __new__(cls, *args, **kwargs):
        """获取连接池的初始化方法，单例模式，因为redis会自己管理连接池"""
        if not hasattr(cls, 'instance'):
            obj = super(MyRedis, cls).__new__(cls)
            pool = redis.ConnectionPool(host='localhost', port=6379, db=0, password='')
            client = redis.Redis(connection_pool=pool)
            obj.client = client
            cls.instance = obj
        return cls.instance

    def get_redis_client(self):
        """返回一个Redis对象的实例"""
        return self.client

    def get_redis_pipe(self):
        """返回一个Redis的管道化实例，这在批量操作时会有更好的性能,但和Redis实例比，
        要多一个execute的动作"""
        return self.client.pipeline()

    def get_redis_pubsub(self):
        """返回一个pubsub的实例。注意，这个实例对象是用来订阅消息的。
        如果你需要发送或者发送+订阅消息，你需要的是一个Redis的实例对象"""
        return self.client.pubsub()

    @staticmethod
    def redis_client():
        """返回一个Redis对象的实例的静态方法"""
        return MyRedis().get_redis_client()

    @staticmethod
    def redis_pubsub():
        """返回一个pubsub的实例的静态方法。注意，这个实例对象是用来订阅消息的。
        如果你需要发送或者发送+订阅消息，你需要的是一个Redis的实例对象"""
        return MyRedis().get_redis_pubsub()

    @staticmethod
    def redis_pipe():
        """返回一个Redis的管道化实例的静态方法，这在批量操作时会有更好的性能,但和Redis实例比，
        要多一个execute的动作"""
        return MyRedis().get_redis_pipe()


def structure_sql(the_type, table_name, query_terms=None, **kwargs):
    """
    构造对数据库的添加，删除，修改 功能的sql语句。
    第一个参数是the_type，表示操作的类型：add,delete,edit
    第二个参数是要操作的表名。
    第三个参数是是查询的条件的sql语句部分，包括where order by等，
    例如：query_terms='where sn=123 and name like '%张%'order by create_date desc'
    **kwargs表示关键字参数，是user_info的表的列名和值组成的字典。例如：
    {"user_name":username,....,"user_password":user_password}
    """
    if the_type == "add":
        """生成insert语句"""
        data = kwargs
        sql = "insert into {}".format(table_name)
        keys = "("
        values = "values("
        for k, v in data.items():
            keys += "{},".format(k)
            values += "'{}',".format(v) if isinstance(v, str) else "{},".format(v)
        keys = keys.rstrip(",")
        values = values.rstrip(",")
        keys += ") "
        values += ")"
        sql += keys + values
        return sql
    elif the_type == 'edit':
        """生成update语句"""
        data = kwargs
        sql = "update {} set ".format(table_name)
        part = ""
        for k, v in data.items():
            part += "{0}={1},".format(k, "'{}'".format(v) if isinstance(v, str) else v)
        part = part.rstrip(",")
        if query_terms is None:
            raise ValueError("编辑时，筛选条件不能为空")
        else:
            return sql + part + " " + query_terms
    elif the_type == "delete":
        """生成delete语句"""
        sql = "delete from {0} ".format(table_name)
        if query_terms is None:
            raise ValueError("删除时，筛选条件不能为空")
        else:
            return sql + query_terms
    else:
        raise KeyError("未知的操作类型")


def str_format(result, local=False):
    """对数据库查询的结果中的datetime和date对象进行格式化，第一个参数是查询的结果集，元组类型。
    第二个参数是是否用中文年月日表示。以list类型返回处理过的结果"""
    data = []
    for x in result:
        if isinstance(x, datetime.datetime):
            temp = x.strftime("%Y{}%m{}%d{} %H{}%M{}%S{}")
            if local:
                temp = temp.format("年", "月", "日", "时", "分", "秒")
            else:
                temp = temp.format("-", "-", "", ":", ":", "")
            data.append(temp)
        elif isinstance(x, datetime.date):
            temp = x.strftime("%Y{}%m{}%d{}")
            if local:
                temp = temp.format("年", "月", "日")
            else:
                temp = temp.format("-", "-", "")
            data.append(temp)
        else:
            data.append(x)
    return data


def current_datetime():
    """获取当前的日期和时间，以字符串类型返回，格式为：2016-12-19 14:33:03"""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def validate_arg(arg, pop_char=None):
    """检测输入参数是否被注入攻击语句的方法
    arg 是待检测的参数。
    pop_char是语句中允许包含的常见攻击字符【!"#$%&'()*+,-./:;<=>?@[\]^_`{|}】
    比如一般用户名许可下划线，那这是的pop_char='_'
    return 合法的参数返回True
    """
    pattern = string.punctuation
    if arg is None:
        raise ValueError("参数不能为None")
        return False
    elif isinstance(arg, str):
        if pop_char is None:
            pass
        else:
            chars = set(pop_char)
            for x in chars:
                pattern = pattern.replace(x, "")
        return not set(str(arg)) & set(pattern)
    else:
        raise TypeError("参数必须是str对象,而不是{}".format(str(type(arg))))
        return False


def check_phone(phone):
    """检查手机号码的合法性，合法的手机返回True"""
    if phone is None:
        return False
    elif isinstance(phone, str) or isinstance(phone, int):
        phone = str(phone).strip()
        if len(phone) == 11 and phone.startswith("1"):
            return True
        else:
            return False
    else:
        return False


"""
初始化SQLalchemy引擎,其中strategy='threadlocal' 是使用本地线程模式。其目的是为了保证
在多线程状态下的线程安全。max_overflow是指数据库连接池满了以后，还允许新建多少线程?
如果设置过大，可能触及mysql配置的底线导致mysql出错。如果设置太小，那么一点超出连接池
的话，可能会遇到获取不到数据库连接的错误。session会自己管理连接池和连接的断开情况。
pool_recycle这个参数一定要设置，这个是数据库连接的闲置超时回收时间，默认是-1，也就是永远不主动
回收数据库连接，这样的话，一旦连接的闲置时间超过数据库的默认设置（mysql默认是8个小时，也就是28800秒。）
数据库就会主动断开连接，而应用却不知道连接已断开。当前的设置是3600秒，
也就是一小时，实际设置只要小于数据库的默认闲置超时就好了，
mysql下查看相关设置可以使用
show variables like '%timeout%';
其中的wait_timeout 就是对应的值
注意url结尾的那个?charset=utf8 必须设置，否则中文插入会出问题，因为sqlalchemy默的是
latin1字符集
"""

engine = create_engine(
    "mysql+pymysql://{0}:{1}@{2}/{3}?charset={4}".format(user, password, sql_host, database, charset),
    echo=False, echo_pool=False, max_overflow=max_overflow, pool_size=pool_size, pool_recycle=pool_recycle,
    strategy='threadlocal')

"""autoflush的意思是在orm状态下，使用session的add(a)方法加入或者delete(a)方法从数据库删除
一个a对象对应的记录时，无需flush的方法即可生效，可以理解为类似conn.commit()的方法，如果你不使用orm的话，
这个设置选项无关紧要,autocommit的默认值就是False，这里设置是为了做示范"""
DB_Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def sql_session():
    """返回一个SQLalchemy.orm.session.Session 的实例"""
    return DB_Session()
