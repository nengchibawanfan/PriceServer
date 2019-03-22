#coding: utf-8
import os
import logging.config,logging.handlers
import traceback
import types
ERROR = 40

def error(self, msg, *args, **kwargs):
    if self.isEnabledFor(ERROR):
        self._log(ERROR,msg,args,**kwargs)
        tb=traceback.format_exc()
        self._log(ERROR,tb,{})

# 设置logging
def getLog(name='info'):
    rootPath = os.path.realpath(os.path.split(__file__)[0] + '/../')
    os.makedirs(rootPath+'/logs/info', exist_ok=True)
    os.makedirs(rootPath + '/logs/stat', exist_ok=True)
    os.makedirs(rootPath+'/logs/error',exist_ok=True)
    LOGGING_DIC = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '%(asctime)s %(filename)s[%(lineno)-3d]-%(levelname)-5s(%(funcName)s): %(message)s',
                'datefmt': '%y-%m-%d %H:%M:%S'
            },
        },
        'filters': {
            'filter_by_name': {
                'class': 'logging.Filter',
                'name': 'logger_for_filter_name'
            },
        },
        'handlers': {
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'simple',
                'stream':'ext://sys.stdout'
            },
            'info': {
                'level': 'DEBUG',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'filename': rootPath+'/logs/info/logs',
                'when': 'midnight',
                'backupCount': 5,
                'formatter': 'simple',
                'encoding': 'utf-8',
            },
            'stat': {
                'level': 'DEBUG',
                'class': 'logging.handlers.TimedRotatingFileHandler',
                'filename': rootPath + '/logs/stat/logs',
                'when': 'midnight',
                'backupCount': 5,
                'formatter': 'simple',
                'encoding': 'utf-8',
            },
            'error':{
                'level':'DEBUG',
                'class':'logging.handlers.TimedRotatingFileHandler',
                'filename':rootPath+'/logs/error/logs',
                'when':'midnight',
                'backupCount':5,
                'formatter':'simple',
                'encoding':'utf-8',
            }
        },
        'loggers': {
            'info': {
                'handlers': ['info', 'console'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'stat': {
                'handlers': ['stat', 'console'],
                'level': 'DEBUG',
                'propagate': False,
            },
            'error':{
                'handlers':['error','console'],
                'level':'DEBUG',
                'propagate':False,
            },
        },
    }
    logging.config.dictConfig(LOGGING_DIC)  # 导入上面定义的配置
    log = logging.getLogger(name)
    log.error = types.MethodType(error,log)
    return log

if __name__ == '__main__':
    def pr():
        l = getLog('error')
        try:
            raise ValueError('test')
        except Exception as e:
            l.error(e)
    pr()