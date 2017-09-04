import feedparser
import requests
import json
import rpfti.shared_config
import random
import re
import datetime
from .core_addon import BotCommand, BotAddon, BotTask
from .rss_wiki import read_todays_events

rss_art = "https://backend.deviantart.com/rss.xml?q=boost%3Apopular+max_age%3A72h+in%3Aphotography&type=deviation"

rss_nudes = "https://backend.deviantart.com/rss.xml?q=boost%3Apopular+max_age%3A72h"\
            "+in%3Aphotography%2Fpeople%2Fnude&type=deviation"

rss_filter = "https://backend.deviantart.com/rss.xml?q=boost%3Apopular+max_age%3A72h%FILTER%&type=deviation"

api_url = "https://www.googleapis.com/urlshortener/v1/url?key={}".format(
    rpfti.shared_config.GOO_GL)
headers = {'content-type': 'application/json'}

rss_list = ["https://news.yandex.ru/Tajikistan/index.rss",
            "http://breakingmad.me/ru/rss",
            "http://batenka.ru/rss/",
            "http://orthodoxy.cafe/index.php?PHPSESSID=ssfp967ein7mpt6dklev0ko1b6&action=.xml;board=65;type=rss",
            "http://orthodoxy.cafe/index.php?PHPSESSID=ssfp967ein7mpt6dklev0ko1b6&action=.xml;board=66;type=rss",
            "http://ren.tv/export/feed.xml",
            ]

drama_list = ["https://www.galya.ru/sitemap/rss20export.xml",
              "http://www.woman.ru/forum/rss/"]


def make_short(url):
    payload = {'longUrl': url}
    r = requests.post(api_url, data=json.dumps(payload), headers=headers)
    return r.json()["id"]


def get_drama(cmd, user, chat, message, cmd_args):
    bot = cmd.addon.bot
    try:
        out_msg = "Немного важных драм, {}\n".format(user.first_name)
        r = feedparser.parse(random.choice(drama_list))
        n = random.choice(r["entries"])
        out_msg += "Вот, например, \"{}\" из категории \"{}\"\n\n{}\n\n{}".format(
            n["title"], n["category"], n["description"], n["guid"])
        bot.send_message(chat, out_msg, origin_user=user, disable_preview=True)
    except Exception as e:
        print(e)
        bot.send_message(
            chat, "Не удалось что-то с драмами...", origin_user=user)


def get_day(cmd, user, chat, message, cmd_args):
    bot = cmd.addon.bot
    try:
        date_match = re.search("(\d+).(\d+)", cmd_args)
        if not date_match:
            out_string = read_todays_events()
        else:
            dd = datetime.datetime.utcnow().replace(day=int(date_match.group(1)), month=int(date_match.group(2)))
            out_string = read_todays_events(dd)
        bot.send_message(chat, out_string, origin_user=user, parse_mode="HTML")
    except Exception as e:
        print(e)
        bot.send_message(
            chat, "Не удалось что-то с датами...", origin_user=user)


def get_news(cmd, user, chat, message, cmd_args):
    bot = cmd.addon.bot
    try:
        out_msg = "Вот тебе новостей, {}\n".format(user.first_name)
        for i in range(3):
            r = feedparser.parse(random.choice(rss_list))
            n = random.choice(r["entries"])
            print(n)
            slink = make_short(n["link"])
            title = n["title"]
            feed_title = r["feed"]["title"]
            if "published" in n:
                pubdate = n["published"]
            elif "pubDate" in n:
                pubdate = n["pubDate"]
            elif "updated" in n:
                pubdate = n["updated"]
            else:
                pubdate = "хер его знает, когда"
            out_msg += "---\n{}\n{}\n({}, опубликовано: {})\n".format(
                title, slink, feed_title, pubdate)
        bot.send_message(chat, out_msg, origin_user=user, disable_preview=True)
    except Exception as e:
        print(e)
        bot.send_message(
            chat, "Не удалось что-то с новостями...", origin_user=user)


def art_getter(count=1, url=rss_art):
    r = feedparser.parse(url)
    if len(r["entries"]) == 0:
        return None
    res = []
    for i in range(count):
        ent = random.choice(r["entries"])
        r["entries"].remove(ent)
        pht = ent["media_content"][0]["url"]
        slink = make_short(pht)
        author_link = ent["link"]
        res.append((ent["title"], pht, slink, author_link))
    return res


def get_art(cmd, user, chat, message, cmd_args):
    bot = cmd.addon.bot
    try:
        arg_match = re.search("(\S+)", cmd_args)
        if not arg_match:
            link = rss_art
        else:
            link_filter = ""
            for g in arg_match.groups():
                link_filter += "+" + g
            link = rss_filter.replace("%FILTER%", link_filter)

        res = art_getter(url=link)[0]
        if res is None:
            bot.send_message(chat, "Картинок не нашлось", origin_user=user)
            return
        payload = {}
        payload["PHOTO"] = {}
        payload["PHOTO"]["title"] = "{} (страница: {})".format(res[0], res[3])
        payload["PHOTO"]["file"] = res[1]
        bot.send_message(chat, res[2], origin_user=user, payload=payload,
                         disable_preview=True)
    except Exception as e:
        bot.send_message(
            chat, "Не удалось что-то с картинками...", origin_user=user)
        print(e)


def get_nudes(cmd, user, chat, message, cmd_args):
    bot = cmd.addon.bot
    try:
        res = art_getter(url=rss_nudes)[0]
        if res is None:
            bot.send_message(chat, "Картинок не нашлось", origin_user=user)
            return
        payload = {}
        payload["PHOTO"] = {}
        payload["PHOTO"]["title"] = "{} (страница: {})".format(res[0], res[3])
        payload["PHOTO"]["file"] = res[1]
        bot.send_message(chat, res[2], origin_user=user, payload=payload,
                         disable_preview=True)
    except Exception as e:
        bot.send_message(
            chat, "Не удалось что-то с картинками...", origin_user=user)
        print(e)


def task_art(task_f, task, task_model):
    bot = task_f.addon.bot
    chat = task.chat
    res = art_getter(1, rss_art)
    bot.send_message(chat, "Ежедневная картинка с deviantart.com")
    for r in res:
        payload = {}
        payload["PHOTO"] = {}
        payload["PHOTO"]["title"] = "{} (картинка: {}, страница: {})".format(r[0], r[2], r[3])
        payload["PHOTO"]["file"] = r[1]
        bot.send_message(chat, payload=payload,
                         disable_preview=True)
    bot.reset_task(task)
    return True


def task_nudes(task_f, task, task_model):
    bot = task_f.addon.bot
    chat = task.chat
    res = art_getter(3, rss_nudes)
    bot.send_message(chat, "Ежедневные картинки ню с deviantart.com")
    for r in res:
        payload = {}
        payload["PHOTO"] = {}
        payload["PHOTO"]["title"] = "{} (картинка: {}, страница: {})".format(r[0], r[2], r[3])
        payload["PHOTO"]["file"] = r[1]
        bot.send_message(chat, payload=payload,
                         disable_preview=True)
    bot.reset_task(task)
    return True


def task_day(task_f, task, task_model):
    bot = task_f.addon.bot
    chat = task.chat
    out_string = read_todays_events()
    bot.send_message(chat, out_string, parse_mode="HTML")
    bot.reset_task(task)
    return True


def subscribe(cmd, user, chat, message, cmd_args, command_name, command_description):
    bot = cmd.addon.bot
    time_match = re.search("(\d+):(\d+)", cmd_args)
    if not time_match:
        if bot.get_task(chat, "RSS", command_name).count() > 0:
            bot.delete_task(chat, "RSS", command_name)
            bot.send_message(chat, "Подписка отменена",
                             origin_user=user, reply_to=message.message_id)
            return
        bot.send_message(chat, "Не могу понять, во сколько присылать",
                         origin_user=user, reply_to=message.message_id)
        return
    hours = int(time_match.group(1))
    mins = int(time_match.group(2))
    if hours > 23 or mins > 59:
        bot.send_message(chat, "Не понял формат времени",
                         origin_user=user, reply_to=message.message_id)
        return

    subs_date = datetime.datetime.utcnow().replace(hour=hours, minute=mins)
    if subs_date < datetime.datetime.utcnow():
        subs_date.replace(day=subs_date.day + 1)
    if bot.add_task(subs_date, chat, "RSS", command_name, command_description, user):
        bot.send_message(chat, "Отлично, подписка настроена",
                         origin_user=user, reply_to=message.message_id)
    else:
        bot.send_message(chat, "Время подписки изменено",
                         origin_user=user, reply_to=message.message_id)

def subscribe_art(cmd, user, chat, message, cmd_args):
    subscribe(cmd, user, chat, message, cmd_args, "art", "Слуайная картинка с DeviantArt")

def subscribe_nudes(cmd, user, chat, message, cmd_args):
    subscribe(cmd, user, chat, message, cmd_args, "nudes", "Три картинки ню с DeviantArt")

def subscribe_day(cmd, user, chat, message, cmd_args):
    subscribe(cmd, user, chat, message, cmd_args, "history_today", "Этот день в истории")

cmd_drama = BotCommand(
    "drama", get_drama, help_text="случайная драма про женскую долю")
cmd_news = BotCommand(
    "news", get_news, help_text="три случайных новости")
cmd_day = BotCommand(
    "history_today", get_day, help_text="день в истории")
cmd_art = BotCommand(
    "art", get_art, help_text="популярная картинка с DeviantArt")
cmd_nudes = BotCommand(
    "nudes", get_nudes, help_text="картинка в стиле ню с DeviantArt")

cmd_subscribe_art = BotCommand(
    "subscribe_art", subscribe_art,
    help_text="подписка на картинку с сайта deviantart каждый день. Время указывается в виде hh:mm в 24-часовом формате по гринвичу. " \
    "Например, /subscribe_art 7:15 для картинок в 10:15 по Московскому времени. Если подписка уже активна, она будет изменена или отменена "\
    "(в том случае, если время не указано).")

cmd_subscribe_nudes = BotCommand(
    "subscribe_nudes", subscribe_nudes,
    help_text="подписка на три картинки с неодетыми людьми с сайта deviantart каждый день. Время указывается в виде hh:mm в 24-часовом формате по гринвичу. " \
    "Например, /subscribe_art 7:15 для картинок в 10:15 по Московскому времени. Если подписка уже активна, она будет изменена или отменена "\
    "(в том случае, если время не указано).")

cmd_subscribe_day = BotCommand(
    "subscribe_history_today", subscribe_day,
    help_text="подписка на каждый день в истории по материалам википедии. Время указывается в виде hh:mm в 24-часовом формате по гринвичу. " \
    "Например, /subscribe_art 7:15 для картинок в 10:15 по Московскому времени. Если подписка уже активна, она будет изменена или отменена "\
    "(в том случае, если время не указано).")


tsk_art = BotTask("art", task_art)
tsk_nudes = BotTask("nudes", task_nudes)
tsk_day = BotTask("history_today", task_day)
rss_addon = BotAddon("RSS", "работа с RSS",
                     [cmd_news, cmd_day, cmd_art, cmd_nudes, cmd_drama, cmd_subscribe_art,
                      cmd_subscribe_nudes, cmd_subscribe_day], tasks=[tsk_art, tsk_nudes, tsk_day])