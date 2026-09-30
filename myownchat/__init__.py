"""
MyOwnChat Python SDK & AI Agent Gateway
Connect any AI Agent to MyOwnChat simply by providing an API Key.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .client import ChannelInfo, Message, MyOwnChatClient
    from .gateway import MyOwnChatGateway

__version__ = "0.1.0"
__all__ = [
    "MyOwnChatClient",
    "MyOwnChatGateway",
    "Message",
    "ChannelInfo",
]


def __getattr__(name: str):
    if name in ("MyOwnChatClient", "Message", "ChannelInfo"):
        from . import client

        return getattr(client, name)
    if name == "MyOwnChatGateway":
        from . import gateway

        return getattr(gateway, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    return sorted(__all__ + ["__version__", "__doc__"])
