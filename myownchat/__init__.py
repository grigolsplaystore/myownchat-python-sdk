"""
MyOwnChat Python SDK & AI Agent Gateway
Connect any AI Agent to MyOwnChat simply by providing an API Key.
"""

from .client import MyOwnChatClient, Message, ChannelInfo
from .gateway import MyOwnChatGateway

__version__ = "0.1.0"
__all__ = [
    "MyOwnChatClient",
    "MyOwnChatGateway",
    "Message",
    "ChannelInfo",
]
