"""后台计算完成后的回写回调登记。

独立 worker 进程不经由 API 加载领域服务，故由 core.worker 在启动时显式导入
相关服务模块，触发 on_ready 装饰器登记。
"""

_ready_callbacks = {}


def on_ready(name):
    def register(func):
        _ready_callbacks[name] = func
        return func
    return register


def get(name):
    return _ready_callbacks.get(name)
