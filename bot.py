import re
import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.utils import get_random_id
from config import Token, Group_id
import time
from datetime import date

emoji_pattern = re.compile(r"^[\U00010000-\U0010ffff\s]+")
siege_participants = {}

def forward(sender, message, reply_to):
        """Функция отправки ответа """
        peer_id = 2000000000 + sender
        print(f"Отправка ответа в чат {sender}: {message}, reply_to: {reply_to}")
        auth.method("messages.send", {
            "peer_id": peer_id,
            "message": message,
            "random_id": get_random_id(),
            "forward" : f"""{{
                            "peer_id": {peer_id},
                            "conversation_message_ids": [{reply_to[0]}, {reply_to[1]}],
                            "is_reply": false
}}"""
        })

def send_reply(sender, message, reply_to):
        """Функция отправки ответа """
        peer_id = 2000000000 + sender
        print(f"Отправка ответа в чат {sender}: {message}, reply_to: {reply_to}")
        auth.method("messages.send", {
            "peer_id": peer_id,
            "message": message,
            "random_id": get_random_id(),
            "forward" : f"""{{
                            "peer_id": {peer_id},
                            "conversation_message_ids": [{reply_to}],
                            "is_reply": true
}}"""
        })


def equipment_need(event):
    message_id = event.message.get("conversation_message_id")
    sender = event.chat_id  # ID беседы
    lines = message.strip().split("\n")
    reply_message = event.message.get("reply_message")  
    original_message_id = None
    if reply_message:
        original_message_id = reply_message.get("conversation_message_id")
    if reply_message.get("text") != "#осада":
        forward(sender, "что-то тут не чисто", original_message_id)
    else:
        if lines:
            item_name = lines[-1].strip()
            item_name = emoji_pattern.sub("", item_name).strip() 
            response_message = f"передать {item_name}"
            forward( sender, response_message, [original_message_id, message_id])



def entry_siege(event, match):
    reply_message = event.message.get("reply_message")
    sender = reply_message["from_id"]
    original_message_id = reply_message["conversation_message_id"]
    guild = match.group(1)
    role = match.group(2)  
    power = match.group(3)  
    stat = match.group(4)
    siege_participants[sender] = {
                "guild" : guild,
                "role": role,
                "power": int(power),
                "stat": stat,
                "items": 0
            }
    response_message = (
                f"Информация принята. О вашем участии в осаде {date.today()} известно:\n"
                f"Сторона: {guild}\n"
                f"Ваша роль: {role} (+{power}{stat})"
            )
    send_reply(event.chat_id, response_message, original_message_id)
    print(siege_participants)


def seige_item(event, match_item):
    reply_message = event.message.get("reply_message")
    sender = reply_message["from_id"]
    original_message_id = reply_message["conversation_message_id"]
    item_power = int(match_item.group(1))
    siege_participants[sender]["items"] += item_power
    total_power = siege_participants[sender]["power"]
    extra_power = siege_participants[sender]["items"]
    response_message = (
        f"Информация принята. О вашем участии в осаде {date.today()} известно:\n"
        f"Сторона: {siege_participants[sender]['guild']}\n"
        f"Ваша роль: {siege_participants[sender]['role']} (+{siege_participants[sender]['power']}{siege_participants[sender]['stat']})\n"
        f"Доп. вложение +{extra_power}{siege_participants[sender]['stat']}\n"
        f"общая сила: +{total_power+extra_power}{siege_participants[sender]['stat']}\n"
    )
    send_reply(event.chat_id, response_message, original_message_id)

def get_siege_summary():
    total_players = len(siege_participants)  # Количество участников
    total_stats = {"⚡": 0, "❤": 0, "⚔": 0}  # Общая сила осады
    player_details = []  # Список участников с их силой

    # Подсчет общей силы и данных по каждому игроку
    for user_id, player in siege_participants.items():
        total_stats[player["stat"]] += player["power"] + player["items"]
        name = get_user_name(user_id)
        player_power = player["power"] + player["items"]
        player_details.append(f"👤 {name} — {player['role']} (+{player_power}{player['stat']})")

    # Формируем два отдельных блока
    siege_power_summary = (
        f"⚔️ В осаде участвует {total_players} игроков.\n"
        f"🔺 Общая сила осады:\n"
        f"⚡ {total_stats['⚡']}\n"
        f"❤ {total_stats['❤']}\n"
        f"⚔ {total_stats['⚔']}"
    )

    player_list_summary = "📜 Список участников:\n" + "\n".join(player_details)

    return siege_power_summary, player_list_summary

def get_user_name(user_id):
    """Получает имя и фамилию пользователя по его ID."""
    try:
        user_info = vk.users.get(user_ids=user_id)[0]
        return f"{user_info['first_name']} {user_info['last_name']}"
    except:
        return f"ID {user_id}"  # Если ошибка или профиль закрыт

auth = vk_api.VkApi(token=Token)
vk = auth.get_api()
longPoll = VkBotLongPoll(auth, group_id=Group_id)  
if __name__ == "__main__":
    print("Бот запущен и ждет сообщения...")
    for event in longPoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW and event.from_chat:
            message = event.message.get("text")
            if "Осадный лагерь нуждается в следующей экипировке:" in message:
                equipment_need(event)
            
            siege_entry_pattern = re.compile(
                                                r"✅Вы успешно присоединились к осадному лагерю гильдии (.+?)!\s*"
                                                r"👤Ваша роль: (.+?) \(\+(\d+)(⚡|❤|⚔)\)"
                                            )
            item_transfer_pattern = re.compile(
                                                r"✅Предмет успешно передан осадному лагерю \(\+(\d+)(⚡|❤|⚔)\)"
                                                )
            match = siege_entry_pattern.match(message)
            if match:
                entry_siege(event, match)
            match_item = item_transfer_pattern.search(message)
            if match_item:
                seige_item(event, match_item)
            if message.lower() == "сила_осады":
                siege_power = get_siege_summary()[0]
                send_reply(event.chat_id, siege_power, event.message["conversation_message_id"])
            if message.lower() == "игроки_осады":
                siege_power = get_siege_summary()[1]
                send_reply(event.chat_id, siege_power, event.message["conversation_message_id"])
            if message.lower() == "шиза":
                send_reply(event.chat_id, "на месте", event.message["conversation_message_id"])