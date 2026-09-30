"""
Unit tests for MyOwnChat Python SDK models and gateway logic.
"""

from myownchat import ChannelInfo, Message, MyOwnChatGateway


def test_message_from_dict_and_properties():
    data = {
        "id": 101,
        "channel_id": 55,
        "sender_user_id": 42,
        "type": "text",
        "text": "Hello world",
        "metadata": {
            "is_app": True,
            "bot_name": "TestBot",
            "reply_to_id": 99,
        },
    }
    msg = Message.from_dict(data)
    assert msg.id == 101
    assert msg.channel_id == 55
    assert msg.sender_user_id == 42
    assert msg.is_from_app is True
    assert msg.bot_name == "TestBot"
    assert msg.reply_to_id == 99
    assert msg.is_from_webhook is False


def test_channel_info_from_dict():
    data = {
        "id": 55,
        "name": "ai-assistant",
        "type": "app",
        "is_open": False,
        "members": 1,
        "settings": {"bot_name": "Helper"},
    }
    ch = ChannelInfo.from_dict(data)
    assert ch.id == 55
    assert ch.name == "ai-assistant"
    assert ch.type == "app"
    assert ch.settings.get("bot_name") == "Helper"


def test_gateway_loop_filtering():
    gw = MyOwnChatGateway(api_key="lb_live_dummy", bot_name="FilterBot")
    received = []

    @gw.on_message
    def handler(m: Message):
        received.append(m)

    # 1. Bot's own message -> ignored
    bot_msg = Message(
        id=1, channel_id=5, sender_app_id=1, text="I am bot", metadata={"is_app": True}
    )
    gw._dispatch_message(bot_msg)
    assert len(received) == 0

    # 2. Webhook message -> ignored
    wh_msg = Message(id=2, channel_id=5, text="Alert", metadata={"is_webhook": True})
    gw._dispatch_message(wh_msg)
    assert len(received) == 0

    # 3. System message -> ignored
    sys_msg = Message(id=3, channel_id=5, type="system", text="User joined")
    gw._dispatch_message(sys_msg)
    assert len(received) == 0

    # 4. Valid human message -> dispatched
    human_msg = Message(id=4, channel_id=5, sender_user_id=12, text="Hello bot!")
    gw._dispatch_message(human_msg)
    assert len(received) == 1
    assert received[0].text == "Hello bot!"


def test_build_persona_prompt():
    from myownchat.cli import build_persona_prompt

    prompt = build_persona_prompt(
        bot_name="SupportBot",
        model="gpt-4o",
        channel_name="support",
    )
    assert "SupportBot" in prompt
    assert "gpt-4o" in prompt
    assert "#support" in prompt
