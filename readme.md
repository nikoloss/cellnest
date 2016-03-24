Cell Nest
===
##Introduction
构建分布式的巢状http服务。一个请求的过程如下：

1.gateway利用tornado框架来分析http请求中的参数和路径，并绑定全局唯一request_id，接着投递给router，

2.router通过匹配url转发表确定出一个cell service(backend)，将来源(gateway)同时写入数据包，并将数据包投递给backend

3.backend启动之时会向router汇报url转发表，同时通过心跳维护与router的连接，backend在接受router的请求之后以多线程模型展开
业务处理，处理完毕之后回复router

4.router拆数据包得到原始gateway信息从而确定是哪个gateway节点来源，于是将报文回复给gateway节点

5.gateway接收router回复的response，通过数据包中的request_id来回复具体的socket fd，自此 一个完整的请求流程处理完毕

##Quick Start
部署之前需要tornado, futures, zmq模块，先安装依赖
然后依次启动gateway, route, backend。backend是重点需要关注的，一个backend也就是一个nest cell。
首先进入backend目录，然后

1.在“biz”目录中创建一个py文件，文件名任意但最好不要跟第三方库冲突

2.使用 "Router.routine" 装饰器注册函数到路由表中，仿造示例即可

3.到主目录下，使用命令"python serv.py" 启动工程，用浏览器访问步骤二中注册的路径可看到效果(例如访问demo的路径就是http://localhost:8888/api/hello/billy?age=12)


## License
Due to benefit from zeromq, licensed under the GNU Lesser
General Public License V3 plus, respect.

## Feedback
* mailto(rowland.lan@163.com) or (rowland.lancer@gmail.com)
* QQ(623135465)
* 知乎(http://www.zhihu.com/people/luo-ran-22)
