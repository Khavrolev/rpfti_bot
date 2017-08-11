
# TODO:
# Repeated CB check
# Control UI
# Sysmon
# Art
# Chat statistics

import datetime
import logging
import telebot

# Bot command class
# Contains command text (as typed by user, but without slashes),
# callback function to process request, help text (description)
# and acceptable roles: basically, these are the following:
# ADMIN as a top role
# EDIT as an editor (content-creator)
# MOD as moderator (rules enforcer)
# USER as a simple default user
# BAN as a blocked user
# Latter can be used to prohibit bot using for certain users
# Acceptable roles should be explicitly set
# By default, command is accessible by anyone, excluding banned ones


class BotCore:

    all_bots = []

    def get_activity(self, chat_id):
        chat = self.models["Chats"].objects.filter(bot__name=self.name,
                                                   telegram_id=chat_id)[0]
        return chat.is_active

    def set_activity(self, chat_id, activity):
        chat = self.models["Chats"].objects.filter(bot__name=self.name,
                                                   telegram_id=chat_id)[0]
        chat.is_active = activity
        chat.save()

    def get_command(self, cmd_name):
        for a in self.addons:
            for c in a.commands:
                if c.name == cmd_name:
                    return (c, a)
        return None

    def insert_addon(self, addon):
        new_cmd_list = []
        for c in addon.commands:
            if self.get_command(c.name) is not None:
                logging.warning("{} is already in command list")
            else:
                new_cmd_list.append(c)
                self.commands_cache.append(c.name)
        addon.commands = new_cmd_list
        self.addons.append(addon)
        addon.bot = self

    def bind(self):
        self.bot.remove_webhook()
        self.bot.set_webhook(url=self.WEBHOOK_URL_BASE,
                             certificate=open(self.WEBHOOK_SSL_CERT,
                                              'r'))
        self.start_time = datetime.datetime.now()
        logging.info("Bot {} binded to webhook".format(self.name))

    def get_activity_global(self):
        bot_db = self.models["Bots"].objects.filter(name=self.name)[0]
        return bot_db.is_active

    def set_activity_global(self, activity):
        bot_db = self.models["Bots"].objects.filter(name=self.name)[0]
        bot_db.is_active = activity
        bot_db.save()

    def __init__(self, models, settings, preset_roles):
        self.declared = False
        self.preset_roles = preset_roles
        self.commands_cache = []
        self.addons = []
        self.models = models
        self.WEBHOOK_URL_BASE = settings["url"]
        self.WEBHOOK_SSL_CERT = settings["cert"]
        self.bot = telebot.TeleBot(settings["token"], threaded=False)
        self.name = settings["name"]
        try:
            db_bot = models["Bots"].objects.get(name__exact=self.name)
        except models["Bots"].DoesNotExist:
            db_bot = models["Bots"](name=self.name)
            db_bot.is_active = False
            db_bot.description = settings["description"]
            db_bot.start_time = datetime.datetime.utcnow()
            db_bot.save()
        self.declare()
        self.all_bots.append(self)

    def _log_message(self, message, origin_user):
        new_msg = self.models["Messages"]()
        new_msg.bot = self.models["Bots"].objects.filter(name=self.name)[0]
        new_msg.chat = self.models["Chats"].objects.filter(
            bot__name=self.name,
            telegram_id=message.chat.id)[0]
        new_msg.to_user = origin_user
        new_msg.date = datetime.datetime.fromtimestamp(message.date)
        new_msg.text = message.text
        new_msg.message_id = message.message_id
        if message.sticker is not None:
            new_msg.content = "STICKER"
            new_msg.content_id = message.sticker.file_id
        elif message.audio is not None:
            new_msg.content = "AUDIO"
            new_msg.content_id = message.audio.file_id
        elif message.voice is not None:
            new_msg.content = "VOICE"
            new_msg.content_id = message.voice.file_id
        elif message.photo is not None:
            new_msg.content = "PHOTO"
            photos = []
            for p in message.photo:
                photos.append(p.file_id)
            new_msg.content_id = ",".join(photos)
        elif message.location is not None:
            new_msg.content = "LOCATION"
            new_msg.content_id = str(
                message.location.latitude) + "/" + str(
                message.location.longitude)
        elif message.document is not None:
            new_msg.content = "DOCUMENT"
            new_msg.content_id = message.document.file_id
        elif message.video is not None:
            new_msg.content = "VIDEO"
            new_msg.content_id = message.video.file_id
        elif message.contact is not None:
            new_msg.content = "CONTACT"
            new_msg.content_id = "{} {} - {}, id: {}".format(
                message.contact.first_name, message.contact.last_name,
                message.contact.phone_number, message.contact.user_id)
        else:
            new_msg.content = "PLAIN"
        new_msg.save()

    def send_message(self, chat, text=None, origin_user=None, reply_to=None,
                     markup=None, disable_preview=False,
                     payload={}, force=False, mute=False):
        if not force and not (self.get_activity(chat.telegram_id) and
                              self.get_activity_global()):
            logging.warning(
                "Trying to send message to an incative chat and/or bot")
            return
        if text is not None:
            sent = self.bot.send_message(
                chat.telegram_id, text,
                disable_web_page_preview=disable_preview,
                reply_markup=markup,
                reply_to_message_id=reply_to,
                disable_notification=mute)
            self._log_message(sent, origin_user)
        if "STICKER" in payload:
            sent = self.bot.send_sticker(chat.telegram_id,
                                         payload["STICKER"]["id"],
                                         reply_markup=markup,
                                         reply_to_message_id=reply_to,
                                         disable_notification=mute)
            self._log_message(sent, origin_user)
        if "AUDIO" in payload:
            sent = self.bot.send_audio(chat.telegram_id,
                                       payload["AUDIO"]["file"],
                                       title=payload["AUDIO"]["title"],
                                       performer=payload[
                                           "AUDIO"]["performer"],
                                       reply_markup=markup,
                                       reply_to_message_id=reply_to,
                                       disable_notification=mute)
            self._log_message(sent, origin_user)
        if "VOICE" in payload:
            sent = self.bot.send_voice(chat.telegram_id,
                                       payload["VOICE"]["file"],
                                       caption=payload["VOICE"]["title"],
                                       reply_markup=markup,
                                       reply_to_message_id=reply_to,
                                       disable_notification=mute)
            self._log_message(sent, origin_user)
        if "PHOTO" in payload:
            sent = self.bot.send_photo(chat.telegram_id,
                                       payload["PHOTO"]["file"],
                                       caption=payload["PHOTO"]["title"],
                                       reply_markup=markup,
                                       reply_to_message_id=reply_to,
                                       disable_notification=mute)
            self._log_message(sent, origin_user)
        if "LOCATION" in payload:
            sent = self.bot.send_location(chat.telegram_id, latitude=payload[
                "LOCATION"]["lat"],
                longitude=payload["LOCATION"]["long"],
                reply_markup=markup,
                reply_to_message_id=reply_to,
                disable_notification=mute)
            self._log_message(sent, origin_user)
        if "DOCUMENT" in payload:
            sent = self.bot.send_document(chat.telegram_id,
                                          payload["DOCUMENT"]["file"],
                                          caption=payload["DOCUMENT"]["title"],
                                          reply_markup=markup,
                                          reply_to_message_id=reply_to,
                                          disable_notification=mute)
            self._log_message(sent, origin_user)
        if "VIDEO" in payload:
            if payload["VIDEO"]["type"] == "note":
                sent = self.bot.send_video_note(chat.telegram_id, payload[
                    "VIDEO"]["file"],
                    reply_markup=markup,
                    reply_to_message_id=reply_to,
                    disable_notification=mute)
            else:
                sent = self.bot.send_video(chat.telegram_id,
                                           payload["VIDEO"]["file"],
                                           caption=payload["VIDEO"]["title"],
                                           reply_markup=markup,
                                           reply_to_message_id=reply_to,
                                           disable_notification=mute)
            self._log_message(sent, origin_user)
        if "CONTACT" in payload:
            sent = self.bot.send_sticker(chat.telegram_id,
                                         payload["CONTACT"]["phone"],
                                         payload["CONTACT"]["first"],
                                         payload["CONTACT"]["last"],
                                         reply_markup=markup,
                                         reply_to_message_id=reply_to,
                                         disable_notification=mute)
            self._log_message(sent, origin_user)

    def get_user(self, user):
        try:
            db_user = self.models["Users"].objects.get(
                bot__name=self.name, telegram_id=user.id)
        except self.models["Users"].DoesNotExist:
            db_user = self.models["Users"]()
            db_user.bot = self.models["Bots"].objects.get(name=self.name)
            db_user.telegram_id = user.id
            db_user.first_name = user.first_name
            db_user.last_name = user.last_name
            db_user.user_name = user.username
            db_user.init_date = datetime.datetime.utcnow()
            db_user.lang = user.language_code
            if user.username in self.preset_roles:
                db_user.role = self.preset_roles[user.username]
            else:
                db_user.role = "USER"
            db_user.save()
        return db_user

    def get_chat(self, chat):
        try:
            db_chat = self.models["Chats"].objects.get(
                bot__name=self.name, telegram_id=chat.id)
        except self.models["Chats"].DoesNotExist:
            db_chat = self.models["Chats"]()
            db_chat.bot = self.models["Bots"].objects.get(name=self.name)
            db_chat.telegram_id = chat.id
            db_chat.chat_type = chat.type
            if db_chat.chat_type == "private":
                db_chat.first_name = chat.first_name
                db_chat.last_name = chat.last_name
            else:
                db_chat.title = chat.title
            db_chat.user_name = chat.username
            db_chat.is_active = False
            db_chat.init_date = datetime.datetime.utcnow()
            db_chat.save()
        return db_chat

    def check_user_and_chat(self, message):
        db_user = self.get_user(message.from_user)
        db_chat = self.get_chat(message.chat)
        return db_chat, db_user

    def declare(self):

        self.declared = True

        # Receiving commands
        @self.bot.message_handler(commands=self.commands_cache)
        def process_commands(message):
            db_chat, db_user = self.check_user_and_chat(message)
            for ent in message.entities:
                if ent.type == "bot_command":
                    offs = ent.offset
                    ln = ent.length
                if (ln is not None) and (offs is not None):
                    cmd = message.text[offs + 1:ln].split('@')[0]
                    logging.info(
                        "User {} {} ({}) triggered a {} command".format(
                            db_user.first_name, db_user.last_name,
                            db_user.telegram_id, cmd))
                    break
            command, addon = self.get_command(cmd)
            if command is None:
                logging.error("{} was triggered but not found".format(cmd))
                return False
            command.call(db_user, db_chat, message)
            return True

        @self.bot.callback_query_handler(func=lambda call: True)
        def process_callback(call):
            for a in self.addons:
                for c in a.callbacks:
                    if c.cb == call.data:
                        c.call(self.get_user(call.from_user),
                               self.get_chat(call.message.chat),
                               call)
                        return True
            logging.error(
                "{} callback was received but not found".format(call.data))
            return False
