# encoding: UTF-8
import ssl
import json
import sys
import time
import hashlib
import traceback
from datetime import datetime
from threading import Lock, Thread

import websocket
from retrying import retry
from priceserver.common.logger import getLog
from wssExchange.base.basesub import BaseSub

logErr = getLog('error')

# 常量定义
class BaseWss(BaseSub):
    """
    关于ping：
    在调用start()之后，该类每60s会自动发送一个ping帧至服务器。
    """
    # ----------------------------------------------------------------------
    def __init__(self, config={}):
        """Constructor"""
        self._ws_lock=Lock()
        self._ws=None  # type: websocket.WebSocket

        self._workerThread=None  # type: Thread
        self._daemonThread=None  # type: Thread
        self._active=False

        # for debugging:
        self._lastSentText=None
        self._lastReceivedText=None

        self._onConnected=None
        self._noDataWait = config.get('noDataWait')
        self._lastCallback=time.time()
        super().__init__()

    # ----------------------------------------------------------------------
    def init(self,host):
        self.wssUrl=host

    # ----------------------------------------------------------------------
    def start(self, onConnected=None):
        """
        启动
        :note 注意：启动之后不能立即发包，需要等待websocket连接成功。
        websocket连接成功之后会响应onConnected函数
        """
        if not self._active:
            self._onConnected=onConnected
            if self._connect():
                self._active=True
                self._workerThread=Thread(target=self._run)
                self._workerThread.start()
                self._daemonThread=Thread(target=self.__runDeamon)
                self._daemonThread.start()

    # ----------------------------------------------------------------------
    def stop(self):
        """
        关闭
        @note 不能从工作线程，也就是websocket的回调中调用
        """
        self._active=False
        self._disconnect()

    # ----------------------------------------------------------------------
    def join(self):
        """
        等待所有工作线程退出
        正确调用方式：先stop()后join()
        """
        if self._daemonThread:
            self._daemonThread.join()
        if self._workerThread:
            self._workerThread.join()

    # ----------------------------------------------------------------------
    def sendJson(self,dictObj):  # type: (dict)->None
        """发出请求:相当于sendText(json.dumps(dictObj))"""
        text=json.dumps(dictObj)
        self._recordLastSentText(text)
        return self._getWs().send(text,opcode=websocket.ABNF.OPCODE_TEXT)

    # ----------------------------------------------------------------------
    def sendText(self,text):  # type: (str)->None
        """发送文本数据"""
        return self._getWs().send(text,opcode=websocket.ABNF.OPCODE_TEXT)

    # ----------------------------------------------------------------------
    def sendBinary(self,data):  # type: (bytes)->None
        """发送字节数据"""
        return self._getWs().send_binary(data)

    # ----------------------------------------------------------------------
    def _reconnect(self):
        """重连"""
        try:
            logErr.info('%s 重连websocket %s'%(self.__class__.__name__,self.wssUrl))
            self._disconnect()
            self._connect()
            self.resubscribe()
            return True
        except Exception as e:
            logErr.error(f'行情服务器重连失败：{e}')
            return False

    # ----------------------------------------------------------------------
    def _createConnection(self,*args,**kwargs):
        return websocket.create_connection(*args,**kwargs)

    # ----------------------------------------------------------------------
    @retry(stop_max_attempt_number=5, wait_fixed=3)
    def _connect(self):
        try:
            logErr.info('%s try to create connection to %s  ...'%(self.__class__.__name__,self.wssUrl))
            self._ws = self._createConnection(self.wssUrl,sslopt={'cert_reqs':ssl.CERT_NONE},timeout=120)
            logErr.info('socket connected')
            self.onConnected()
            return True
        except Exception as e:
            logErr.error(f'行情服务器连接失败：{e}')
            raise e

    # ----------------------------------------------------------------------
    def _disconnect(self):
        """
        断开连接
        """
        with self._ws_lock:
            if self._ws:
                self._ws.close()
                self._ws = None

    # ----------------------------------------------------------------------
    def _getWs(self):
        with self._ws_lock:
            return self._ws

    # ----------------------------------------------------------------------
    def _run(self):
        """
        运行，直到stop()被调用
        """
        while self._active:
            try:
                ws = self._getWs()
                if ws:
                    data=ws.recv()
                    if not data:  # recv在阻塞的时候ws被关闭
                        self._reconnect()
                        continue
                    self._recordLastReceivedText(data)
                    self.onMessage(data)
            except websocket.WebSocketException as e:  # websocket错误，重新连接websocket
                logErr.error(e)
                result = self._reconnect()
                if not result:
                    logErr.info(f'等待10秒后再次重连')
                    time.sleep(10)
                else:
                    logErr.info(f'行情服务器重连成功')
            except:  # Python内部错误（onPacket内出错）
                et,ev,tb=sys.exc_info()
                self.onError(et,ev,tb)

# ----------------------------------------------------------------------
    def __runDeamon(self):
        while self._active:
            for i in range(60):
                if not self._active:
                    break
                time.sleep(1)
            try:
                # has no data to callback for 5 minutes, reconnect
                if self._active:
                    if self._noDataWait and time.time()-self._lastCallback>self._noDataWait:
                        logErr.info(f'websocket sub {self.subDict} recv no data for 5 minutes, try to reconnect...')
                        self._reconnect()
                        self._lastCallback = time.time()
                    self.onHeartBeat()
            except:
                et,ev,tb=sys.exc_info()
                # todo: just log this, notifying user is not necessary
                self.onError(et,ev,tb)
                self._reconnect()

    # ----------------------------------------------------------------------
    def onHeartBeat(self):
        pass
        # ws=self._getWs()
        # if ws:
        #     ws.send('ping',websocket.ABNF.OPCODE_PING)

    # ----------------------------------------------------------------------
    def onConnected(self):
        """
        连接成功回调
        """
        if self._onConnected:
            self._onConnected()

    # ----------------------------------------------------------------------
    def onDisconnected(self):
        """
        连接断开回调
        """
        pass

    # ----------------------------------------------------------------------
    def onMessage(self, data):
        """
        数据回调。
        @:param data: dict
        @:return:
        """
        pass

    def callback(self, symbol, type, params):
        self._lastCallback = time.time()
        super().callback(symbol,type,params)

    # ----------------------------------------------------------------------
    def onError(self,exceptionType,exceptionValue,tb):
        logErr.error(self.exceptionDetail(exceptionType,exceptionValue,tb))

    # ----------------------------------------------------------------------
    def exceptionDetail(self,exceptionType,exceptionValue,tb):
        """打印详细的错误信息"""
        text="[{}]: Unhandled WebSocket Error:{}\n".format(datetime.now().isoformat(),exceptionType)
        text+="LastSentText:\n{}\n".format(self._lastSentText)
        text+="LastReceivedText:\n{}\n".format(self._lastReceivedText)
        text+="Exception trace: \n"
        text+="".join(traceback.format_exception(exceptionType,exceptionValue,tb,))
        return text

    # ----------------------------------------------------------------------
    def _recordLastSentText(self,text):
        """
        用于Debug： 记录最后一次发送出去的text
        """
        self._lastSentText=text[:1000]

    # ----------------------------------------------------------------------
    def _recordLastReceivedText(self,text):
        """
        用于Debug： 记录最后一次发送出去的text
        """
        self._lastReceivedText=text[:1000]

    # ----------------------------------------------------------------------
    def subTopic(self,topic):
        """订阅主题"""
        id=hashlib.sha1(json.dumps(topic).encode('utf-8')).hexdigest()
        if id in self.subDict:
            return
        self.subDict[id]=topic
        self.sendJson(topic)
