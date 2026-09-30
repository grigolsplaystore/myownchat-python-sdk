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


def test_build_chat_context():
    from myownchat.cli import build_chat_context

    sys_prompt = "You are a helpful assistant."

    # 1. Single user turn
    history = [{"role": "user", "content": "Tell me about yourself"}]
    ctx = build_chat_context(sys_prompt, history, max_turns=10)
    assert len(ctx) == 2
    assert ctx[0] == {"role": "system", "content": sys_prompt}
    assert ctx[1] == {"role": "user", "content": "Tell me about yourself"}

    # 2. Leading assistant turn from slice is dropped
    history_with_leading_assistant = [
        {"role": "assistant", "content": "Earlier bot reply"},
        {"role": "user", "content": "New question"},
    ]
    ctx2 = build_chat_context(sys_prompt, history_with_leading_assistant, max_turns=10)
    assert len(ctx2) == 2
    assert ctx2[0]["role"] == "system"
    assert ctx2[1] == {"role": "user", "content": "New question"}

    # 3. Empty strings / whitespace filtered out
    history_with_empty = [
        {"role": "user", "content": "   "},
        {"role": "assistant", "content": ""},
        {"role": "user", "content": "Valid query"},
    ]
    ctx3 = build_chat_context(sys_prompt, history_with_empty, max_turns=10)
    assert len(ctx3) == 2
    assert ctx3[1] == {"role": "user", "content": "Valid query"}

    # 4. Truncation respects max_turns and ensures user starts
    long_history = [
        {"role": "user", "content": "1"},
        {"role": "assistant", "content": "2"},
        {"role": "user", "content": "3"},
        {"role": "assistant", "content": "4"},
        {"role": "user", "content": "5"},
    ]
    ctx4 = build_chat_context(sys_prompt, long_history, max_turns=3)
    assert len(ctx4) == 4  # 1 system + user(3) + assistant(4) + user(5)
    assert ctx4[0]["role"] == "system"
    assert ctx4[1] == {"role": "user", "content": "3"}
    assert ctx4[2] == {"role": "assistant", "content": "4"}
    assert ctx4[3] == {"role": "user", "content": "5"}
