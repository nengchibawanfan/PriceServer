import multiprocessing

# 监听内网端口5000
bind = '0.0.0.0:5000'
backlog = 2048

# 并行工作进程数
workers = multiprocessing.cpu_count() * 2 + 1

# 指定每个工作者的线程数
threads = 2

# 工作模式协程
worker_class = "gevent"

# 设置最大并发量
worker_connections = 1000
# 守护进程方式运行，后台
daemon = False

debug = True
proc_name = 'new_price_server'

# 设置进程文件目录
pidfile = './logs/gunicorn.pid'

# 设置守护进程,将进程交给supervisor管理
# daemon = 'false'

# 设置访问日志和错误信息日志路径
accesslog = './logs/gunicorn_acess.log'
errorlog = './logs/gunicorn_error.log'
# 设置日志记录水平
loglevel = 'warning'
