import re
from typing import Dict, Any
from utils.emojis import (
    EMOJI_BAN, EMOJI_PIN, EMOJI_POINT_DOWN, EMOJI_CHART,
    EMOJI_WARN, EMOJI_CHANNEL, EMOJI_SHIELD, EMOJI_WAVE, EMOJI_HOURGLASS,
    EMOJI_START_GREETING, EMOJI_START_ROBOT, EMOJI_START_GEAR,
    EMOJI_START_LOCK, EMOJI_START_PEOPLE, EMOJI_START_TROPHY,
    EMOJI_START_WAVE, EMOJI_START_CAPTCHA, EMOJI_START_LANG,
    EMOJI_FLAG_UZ, EMOJI_FLAG_QR, EMOJI_FLAG_RU, EMOJI_FLAG_EN, EMOJI_START_BROOM, EMOJI_START_ROCKET,
    EMOJI_NUM_1, EMOJI_NUM_2, EMOJI_NUM_3, EMOJI_CROWN, EMOJI_DOT, EMOJI_BOOK
)

# Tillarni aniqlash: 'qr', 'uz', 'ru', 'en'
def get_user_lang(lang_code: str | None) -> str:
    if not lang_code:
        return "qr"
    code = lang_code.lower()
    if code.startswith("ru"):
        return "ru"
    elif code.startswith("en"):
        return "en"
    elif code.startswith("uz"):
        return "uz"
    elif code.startswith("qr") or code.startswith("kaa"):
        return "qr"
    return "qr"

TEXTS = {
    # 1-BOSQICH: Odam qo'shish talabi
    "need_members_warning": {
        "qr": (
            f"{EMOJI_BAN} {{mention}}, топарда жазыўға рухсатыңыз жоқ!\n\n"
            f"{EMOJI_PIN} Жазыў ушын <b>{{required}} дос</b> қосыўыңыз керек.\n"
            f"Ҳәзирден-ақ досларыңызды мирәт етиң! {EMOJI_POINT_DOWN}\n"
            f"{EMOJI_CHART} <b>{{added}}/{{required}}</b>\n\n"
            f"<i>{EMOJI_WARN} Қағыйда бузылғаны ушын 10 минутқа жазыў ҳуқықыңыз шекленди. "
            "Шәртти орынлап 'Мен адам қостым' түймесин басың!</i>"
        ),
        "uz": (
            f"{EMOJI_BAN} {{mention}}, guruhda yozish uchun ruxsatingiz yo'q!\n\n"
            f"{EMOJI_PIN} Yozish uchun <b>{{required}} ta do'st</b> qo'shishingiz kerak.\n"
            f"Hoziroq do'stlaringizni taklif qiling! {EMOJI_POINT_DOWN}\n"
            f"{EMOJI_CHART} <b>{{added}}/{{required}}</b>\n\n"
            f"<i>{EMOJI_WARN} Qoida buzilgani uchun 10 daqiqaga yozish huquqingiz cheklandi. "
            "Shartni bajarib 'Men odam qo'shdim' tugmasini bosing!</i>"
        ),
        "ru": (
            f"{EMOJI_BAN} {{mention}}, у вас нет разрешения писать в группе!\n\n"
            f"{EMOJI_PIN} Чтобы писать, вам необходимо добавить <b>{{required}} друзей</b>.\n"
            f"Пригласите друзей прямо сейчас! {EMOJI_POINT_DOWN}\n"
            f"{EMOJI_CHART} <b>{{added}}/{{required}}</b>\n\n"
            f"<i>{EMOJI_WARN} Из-за нарушения вы ограничены на 10 минут. "
            "Выполните условие и нажмите 'Проверить'!</i>"
        ),
        "en": (
            f"{EMOJI_BAN} {{mention}}, you do not have permission to post in this group!\n\n"
            f"{EMOJI_PIN} You must add <b>{{required}} friends</b> to write here.\n"
            f"Invite your friends now! {EMOJI_POINT_DOWN}\n"
            f"{EMOJI_CHART} <b>{{added}}/{{required}}</b>\n\n"
            f"<i>{EMOJI_WARN} You have been muted for 10 minutes. "
            "Complete the requirement and tap 'Verify'!</i>"
        )
    },
    
    # 2-BOSQICH: Kanalga obuna bo'lish talabi (Aynan rasmdagidek)
    "need_channel_sub": {
        "qr": (
            f"{EMOJI_CHANNEL} {{mention}}, <b>диққат!</b>\n\n"
            f"Топарда жазыў ушын рәсмий каналымызға ағза болыўыңыз керек {EMOJI_POINT_DOWN}\n\n"
            f"<i>{EMOJI_WARN} Қағыйда бузылғаны себепли 10 минутқа жазыў ҳуқықыңыз шекленди. "
            "Каналға ағза болып 'Обунани тексериў' түймесин басың!</i>"
        ),
        "uz": (
            f"{EMOJI_CHANNEL} {{mention}}, <b>diqqat!</b>\n\n"
            f"Guruhda yozish uchun rasmiy kanalimizga a'zo bo'lishingiz kerak {EMOJI_POINT_DOWN}\n\n"
            f"<i>{EMOJI_WARN} Qoida buzilgani sababli 10 daqiqaga yozish huquqingiz cheklandi. "
            "Kanalga a'zo bo'lib 'Obunani tekshirish' tugmasini bosing!</i>"
        ),
        "ru": (
            f"{EMOJI_CHANNEL} {{mention}}, <b>внимание!</b>\n\n"
            f"Для написания в группе необходимо подписаться на канал {EMOJI_POINT_DOWN}\n\n"
            f"<i>{EMOJI_WARN} Из-за нарушения вы ограничены на 10 минут. "
            "Подпишитесь на канал и нажмите 'Проверить подписку'!</i>"
        ),
        "en": (
            f"{EMOJI_CHANNEL} {{mention}}, <b>attention!</b>\n\n"
            f"To post in this group, you must subscribe to our official channel {EMOJI_POINT_DOWN}\n\n"
            f"<i>{EMOJI_WARN} You have been muted for 10 minutes. "
            "Subscribe to the channel and tap 'Verify subscription'!</i>"
        )
    },

    # Tugmalar
    "btn_i_added": {
        "qr": "✅ Мен адам қостым",
        "uz": "✅ Men odam qo'shdim",
        "ru": "✅ Я добавил людей",
        "en": "✅ I added members"
    },
    "btn_give_access": {
        "qr": "⭐️ Жеңиллик бериў",
        "uz": "⭐ Imtiyoz berish",
        "ru": "⭐ Дать доступ",
        "en": "⭐ Grant access"
    },
    "btn_check_sub": {
        "qr": "✅ Обунани тексериў",
        "uz": "✅ Obunani tekshirish",
        "ru": "✅ Проверить подписку",
        "en": "✅ Verify subscription"
    },
    "btn_channel_link": {
        "qr": "📢 Каналға ағза болыў",
        "uz": "📢 Kanalga a'zo bo'lish",
        "ru": "📢 Подписаться на канал",
        "en": "📢 Join channel"
    },

    # Obuna tekshiruv javoblari (Popup / Alert)
    "sub_success": {
        "qr": "✅ Қутлықлаймыз! Сиз каналымызға ағза болдыңыз. Жазыў ҳуқықыңыз толық ашылды!",
        "uz": "✅ Tabriklaymiz! Siz kanalimizga a'zo bo'ldingiz. Yozish huquqingiz to'liq ochildi!",
        "ru": "✅ Поздравляем! Вы подписались на канал. Доступ к написанию сообщений открыт!",
        "en": "✅ Congratulations! You subscribed to the channel. You can now send messages!"
    },
    "sub_failed": {
        "qr": "❌ Сиз еле каналға ағза болмадыңыз! Илтимас, каналға кириң ҳәм қайта тексериң.",
        "uz": "❌ Siz hali kanalga a'zo bo'lmadingiz! Iltimos, kanalga kiring va qayta tekshiring.",
        "ru": "❌ Вы еще не подписались на канал! Пожалуйста, перейдите в канал и нажмите проверить снова.",
        "en": "❌ You have not subscribed to the channel yet! Please join the channel first."
    },
    "add_member_remains": {
        "qr": "⏳ Сиз {added}/{required} адам қосқансыз. Және {remains} адам қосыўыңыз керек!",
        "uz": "⏳ Siz {added}/{required} ta odam qo'shgansiz. Yana {remains} ta odam qo'shishingiz kerak!",
        "ru": "⏳ Вы добавили {added}/{required} друзей. Нужно добавить еще {remains}!",
        "en": "⏳ You added {added}/{required} friends. You still need to add {remains} more!"
    },
    "add_member_success_need_channel": {
        "qr": "✅ Адам қосыў шәртин орынладыңыз! Енди каналымызға ағза болың.",
        "uz": "✅ Odam qo'shish shartini bajardingiz! Endi kanalimizga a'zo bo'ling.",
        "ru": "✅ Условие добавления выполнено! Теперь подпишитесь на наш канал.",
        "en": "✅ Member requirement fulfilled! Now please subscribe to our channel."
    },
    "admin_only_btn": {
        "qr": "⚠️ Бул түйме тек топар админлери ушын!",
        "uz": "⚠️ Bu tugma faqat guruh adminlari uchun!",
        "ru": "⚠️ Эта кнопка доступна только администраторам группы!",
        "en": "⚠️ This button is only for group administrators!"
    },

    # CAPTCHA (Xavfsizlik tekshiruvi)
    "captcha_message": {
        "qr": (
            f"{EMOJI_SHIELD} <b>Қәўипсизлик тексериўи</b>\n\n"
            f"{EMOJI_WAVE} Ассалаўма алейкум, {{mention}}!\n\n"
            "Топарда жазыў ушын робот емеслигиңизди тастыйықлаң.\n\n"
            "<b>Мисалды шешиң:</b>\n"
            "<code>{a} + {b} = ?</code>\n\n"
            f"Жуўапты таңлаң ({EMOJI_HOURGLASS} 5 минут):"
        ),
        "uz": (
            f"{EMOJI_SHIELD} <b>Xavfsizlik tekshiruvi</b>\n\n"
            f"{EMOJI_WAVE} Assalomu alaykum, {{mention}}!\n\n"
            "Guruhda yozish uchun robot emasligingizni tasdiqlang.\n\n"
            "<b>Misolni yeching:</b>\n"
            "<code>{a} + {b} = ?</code>\n\n"
            f"Javobni tanlang ({EMOJI_HOURGLASS} 5 daqiqa):"
        ),
        "ru": (
            f"{EMOJI_SHIELD} <b>Проверка безопасности</b>\n\n"
            f"{EMOJI_WAVE} Здравствуйте, {{mention}}!\n\n"
            "Подтвердите, что вы не робот, чтобы писать в группе.\n\n"
            "<b>Решите пример:</b>\n"
            "<code>{a} + {b} = ?</code>\n\n"
            f"Выберите ответ ({EMOJI_HOURGLASS} 5 минут):"
        ),
        "en": (
            f"{EMOJI_SHIELD} <b>Security Verification</b>\n\n"
            f"{EMOJI_WAVE} Hello, {{mention}}!\n\n"
            "Please confirm that you are not a robot to post in this group.\n\n"
            "<b>Solve this:</b>\n"
            "<code>{a} + {b} = ?</code>\n\n"
            f"Select the answer ({EMOJI_HOURGLASS} 5 minutes):"
        )
    },
    "captcha_success": {
        "qr": "✅ Дурыс! Робот емеслигиңиз табыслы тастыйықланды.",
        "uz": "✅ To'g'ri! Robot emasligingiz muvaffaqiyatli tasdiqlandi.",
        "ru": "✅ Правильно! Вы успешно подтвердили, что не являетесь роботом.",
        "en": "✅ Correct! You successfully verified you are human."
    },
    "captcha_wrong": {
        "qr": "❌ Надурыс жуўап! Және {attempts} имканиятыңыз қалды.",
        "uz": "❌ Noto'g'ri javob! Yana {attempts} ta imkoniyatingiz qoldi.",
        "ru": "❌ Неверный ответ! Осталось попыток: {attempts}.",
        "en": "❌ Wrong answer! Attempts left: {attempts}."
    },
    "captcha_failed_kick": {
        "qr": "❌ Сиз 3 мәрте надурыс жуўап бердиңиз ҳәм топардан шығарылып тасланасыз.",
        "uz": "❌ Siz 3 marta noto'g'ri javob berdingiz va guruhdan chiqarilasiz.",
        "ru": "❌ Вы ответили неверно 3 раза и исключаетесь из группы.",
        "en": "❌ 3 failed attempts. You are being removed from the group."
    },
    "captcha_not_for_you": {
        "qr": "⚠️ Бул тексериў тек жаңа қосылған ағза ушын!",
        "uz": "⚠️ Bu tekshiruv faqat yangi qo'shilgan a'zo uchun!",
        "ru": "⚠️ Эта проверка только для нового участника!",
        "en": "⚠️ This verification is only for the new member!"
    },

    # START XABARI (QR, UZ, RU, EN)
    "start_message": {
        "qr": (
            f"{EMOJI_START_GREETING} Сәлем, <b>{{name}}</b>! Ботымызға хош келдиңиз.\n\n"
            f"{EMOJI_START_ROBOT} Мен топар модераторы сыпатында ислеймен — каналларға жазылыў ҳәм адам қосыў миннетлемелерин басқараман.\n\n"
            f"{EMOJI_START_GEAR} <b>Имканиятлар:</b>\n"
            f"{EMOJI_START_LOCK} Каналларға мәжбүрий жазылыў\n"
            f"{EMOJI_START_PEOPLE} Мәжбүрий адам қосыў\n"
            f"{EMOJI_START_TROPHY} Ең көп қосқанлар рейтинги\n"
            f"{EMOJI_START_WAVE} Жаңа ағзаға сәлемлесиў хабары\n"
            f"{EMOJI_START_CAPTCHA} Captcha — спам-ботлардан қорғаў\n"
            f"{EMOJI_START_LANG} 4 тил: Қарақалпақ | Өзбек | Рус | Инглис\n"
            f"{EMOJI_START_BROOM} Автоматикалық тазалаў — топарда артықша хабар қалдырмайды\n\n"
            f"{EMOJI_START_ROCKET} <b>Баслаў ушын:</b>\n"
            f"<blockquote>{EMOJI_NUM_1} Ботты топарыңызға қосың\n"
            f"{EMOJI_NUM_2} Ботқа <b>admin</b> ҳуқықларын бериң\n"
            f"{EMOJI_NUM_3} <code>/set</code> буйрығын жибериң</blockquote>\n\n"
            f"Толық мағлыўмат: /help"
        ),
        "uz": (
            f"{EMOJI_START_GREETING} Salom, <b>{{name}}</b>! Botimizga xush kelibsiz.\n\n"
            f"{EMOJI_START_ROBOT} Men guruh moderatori sifatida ishlayman — kanallarga obuna va odam qo'shish majburiyatlarini boshqaraman.\n\n"
            f"{EMOJI_START_GEAR} <b>Imkoniyatlar:</b>\n"
            f"{EMOJI_START_LOCK} Kanallarga majburiy obuna\n"
            f"{EMOJI_START_PEOPLE} Majburiy odam qo'shish\n"
            f"{EMOJI_START_TROPHY} Eng ko'p qo'shganlar reytingi\n"
            f"{EMOJI_START_WAVE} Yangi a'zoga salomlashish xabari\n"
            f"{EMOJI_START_CAPTCHA} Captcha — spam-botlardan himoya\n"
            f"{EMOJI_START_LANG} 4 til: Қарақалпақ | O'zbek | Rus | Ingliz\n"
            f"{EMOJI_START_BROOM} Avtomatik tozalash — guruhda ortiqcha xabar qoldirmaydi\n\n"
            f"{EMOJI_START_ROCKET} <b>Boshlash uchun:</b>\n"
            f"<blockquote>{EMOJI_NUM_1} Botni guruhingizga qo'shing\n"
            f"{EMOJI_NUM_2} Botga <b>admin</b> huquqlarini bering\n"
            f"{EMOJI_NUM_3} <code>/set</code> yoki <code>/add</code> buyrug'ini yuboring</blockquote>\n\n"
            f"To'liq qo'llanma: /help"
        ),
        "ru": (
            f"{EMOJI_START_GREETING} Здравствуйте, <b>{{name}}</b>! Добро пожаловать.\n\n"
            f"{EMOJI_START_ROBOT} Я бот-модератор групп — управляю обязательной подпиской на каналы и добавлением участников.\n\n"
            f"{EMOJI_START_GEAR} <b>Возможности:</b>\n"
            f"{EMOJI_START_LOCK} Обязательная подписка на каналы\n"
            f"{EMOJI_START_PEOPLE} Обязательное добавление участников\n"
            f"{EMOJI_START_TROPHY} Рейтинг пригласивших\n"
            f"{EMOJI_START_WAVE} Приветственное сообщение новым участникам\n"
            f"{EMOJI_START_CAPTCHA} Капча — защита от спам-ботов\n"
            f"{EMOJI_START_LANG} 4 языка: Каракалпакский | Узбекский | Русский | Английский\n"
            f"{EMOJI_START_BROOM} Автоматическая очистка лишних сообщений\n\n"
            f"{EMOJI_START_ROCKET} <b>Как начать:</b>\n"
            f"<blockquote>{EMOJI_NUM_1} Добавьте бота в вашу группу\n"
            f"{EMOJI_NUM_2} Выдайте боту права <b>администратора</b>\n"
            f"{EMOJI_NUM_3} Отправьте команду <code>/set</code> или <code>/add</code></blockquote>\n\n"
            f"Полное руководство: /help"
        ),
        "en": (
            f"{EMOJI_START_GREETING} Hello, <b>{{name}}</b>! Welcome.\n\n"
            f"{EMOJI_START_ROBOT} I am a group moderator bot — managing mandatory channel subscriptions and member invites.\n\n"
            f"{EMOJI_START_GEAR} <b>Features:</b>\n"
            f"{EMOJI_START_LOCK} Mandatory channel subscriptions\n"
            f"{EMOJI_START_PEOPLE} Mandatory member invites\n"
            f"{EMOJI_START_TROPHY} Top inviter leaderboard\n"
            f"{EMOJI_START_WAVE} Welcome greeting for new members\n"
            f"{EMOJI_START_CAPTCHA} Captcha — anti-spam bot protection\n"
            f"{EMOJI_START_LANG} 4 languages: Karakalpak | Uzbek | Russian | English\n"
            f"{EMOJI_START_BROOM} Auto-clean service messages\n\n"
            f"{EMOJI_START_ROCKET} <b>Getting started:</b>\n"
            f"<blockquote>{EMOJI_NUM_1} Add bot to your group\n"
            f"{EMOJI_NUM_2} Grant <b>admin</b> rights to the bot\n"
            f"{EMOJI_NUM_3} Send <code>/set</code> or <code>/add</code> command</blockquote>\n\n"
            f"Full guide: /help"
        )
    },

    # Tugmalar (icon_custom_emoji_id orqali premium custom emoji bilan ko'rinadi)
    "btn_add_group": {
        "qr": "Топарға қосыў",
        "uz": "Guruhga qo'shish",
        "ru": "Добавить в группу",
        "en": "Add to group"
    },
    "btn_my_stats": {
        "qr": "Мениң статистикам",
        "uz": "Mening statistikam",
        "ru": "Моя статистика",
        "en": "My statistics"
    },
    "btn_change_lang": {
        "qr": "Тилди таңлаў",
        "uz": "Tilni tanlash",
        "ru": "Выбрать язык",
        "en": "Choose language"
    },
    "btn_help": {
        "qr": "Қолланба",
        "uz": "Qo'llanma",
        "ru": "Руководство",
        "en": "Guide"
    },

    # Til tanlash xabarlari
    "choose_lang_title": {
        "qr": f"{EMOJI_START_LANG} <b>Илтимас, тилди таңлаң:\nIltimos, tilni tanlang:\nПожалуйста, выберите язык:\nPlease select a language:</b>",
        "uz": f"{EMOJI_START_LANG} <b>Iltimos, tilni tanlang:\nИлтимас, тилди таңлаң:\nПожалуйста, выберите язык:\nPlease select a language:</b>",
        "ru": f"{EMOJI_START_LANG} <b>Пожалуйста, выберите язык:\nИлтимас, тилди таңлаң:\nIltimos, tilni tanlang:\nPlease select a language:</b>",
        "en": f"{EMOJI_START_LANG} <b>Please select a language:\nИлтимас, тилди таңлаң:\nIltimos, tilni tanlang:\nПожалуйста, выберите язык:</b>"
    },
    "lang_changed_success": {
        "qr": "✅ Тил табыслы Қарақалпақшаға өзгертилди!",
        "uz": "✅ Til muvaffaqiyatli O'zbekchaga o'zgartirildi!",
        "ru": "✅ Язык успешно изменен на Русский!",
        "en": "✅ Language successfully changed to English!"
    },
    "group_lang_title": {
        "qr": f"{EMOJI_START_LANG} <b>Топар ушын тийкарғы тилди таңлаң:</b>\n<i>(Барлық ескертиўлер ҳәм түймелер усы тилде көринеди)</i>",
        "uz": f"{EMOJI_START_LANG} <b>Guruh uchun asosiy tilni tanlang:</b>\n<i>(Barcha ogohlantirishlar va tugmalar ushbu tilda chiqadi)</i>",
        "ru": f"{EMOJI_START_LANG} <b>Выберите основной язык для группы:</b>\n<i>(Все предупреждения и кнопки будут на этом языке)</i>",
        "en": f"{EMOJI_START_LANG} <b>Choose default language for the group:</b>\n<i>(All warnings and buttons will be in this language)</i>"
    },
    "group_lang_success": {
        "qr": "✅ Топар тили табыслы өзгертилди: Қарақалпақша",
        "uz": "✅ Guruh tili muvaffaqiyatli o'zgartirildi: O'zbekcha",
        "ru": "✅ Язык группы успешно изменен: Русский",
        "en": "✅ Group language successfully changed: English"
    },

    # Guruhda /help buyrug'i javoblari
    "help_group_user": {
        "qr": (
            f"{EMOJI_START_ROBOT} <b>Qorıqshı bot қолланбасы:</b>\n\n"
            f"Топарда хабар жазыў ушын админ тәрепинен белгиленген шәртлерди орынлаң:\n"
            f"1. Белгиленген сандағы досларыңызды мирәт етиң.\n"
            f"2. Егер канал көрсетилген болса, каналға ағза болың.\n\n"
            f"📊 Қанша адам қосқаныңызды билиў ушын: <code>/my</code>"
        ),
        "uz": (
            f"{EMOJI_START_ROBOT} <b>Qorıqshı bot qo'llanmasi:</b>\n\n"
            f"Guruhda xabar yozish uchun admin tomonidan belgilangan shartlarni bajaring:\n"
            f"1. Belgilangan sondagi do'stlaringizni taklif qiling.\n"
            f"2. Agar kanal ko'rsatilgan bo'lsa, kanalga a'zo bo'ling.\n\n"
            f"📊 Nechta odam qo'shganingizni bilish uchun: <code>/my</code>"
        ),
        "ru": (
            f"{EMOJI_START_ROBOT} <b>Руководство Qorıqshı bot:</b>\n\n"
            f"Чтобы писать в группе, выполните условия администратора:\n"
            f"1. Пригласите необходимое количество друзей.\n"
            f"2. Подпишитесь на обязательный канал, если он установлен.\n\n"
            f"📊 Чтобы узнать ваш счет: <code>/my</code>"
        ),
        "en": (
            f"{EMOJI_START_ROBOT} <b>Qorıqshı bot guide:</b>\n\n"
            f"To send messages in this group, please fulfill requirements:\n"
            f"1. Invite the required number of friends.\n"
            f"2. Join the official channel if required.\n\n"
            f"📊 To check your count: <code>/my</code>"
        )
    },
    "help_group_admin": {
        "qr": (
            f"{EMOJI_BOOK} <b>Топар Админлери ушын буйрықлар:</b>\n\n"
            f"{EMOJI_DOT} <code>/set 5</code> — Ағзаларға 5 адам қосыў шәртин қойыў (өшириў: <code>/set 0</code>)\n"
            f"{EMOJI_DOT} <code>/setchannel @kanal</code> — Мәжбүрий канал жалғаў\n"
            f"{EMOJI_DOT} <code>/delchannel</code> — Мәжбүрий каналды өшириў\n"
            f"{EMOJI_DOT} <code>/lang</code> — Топар тилин өзгертиў (QR / UZ / RU / EN)\n"
            f"{EMOJI_DOT} <code>/captcha on/off</code> — Математикалық Captchani қосыў/өшириў\n"
            f"{EMOJI_DOT} <code>/anticheat on/off</code> — Шығып кеткенлер есаптан алынсын ба\n"
            f"{EMOJI_DOT} <code>/status</code> — Топардың толық параметрлери ҳәм статистикасы\n"
            f"{EMOJI_DOT} <code>/top</code> — Ең көп адам қосқанлар ТОП-10\n"
            f"{EMOJI_DOT} <code>/check @username</code> — Ағза кимлерди қосқанын тексериў\n"
            f"{EMOJI_DOT} <code>/imtiyoz</code> — Пайдаланыўшыға шеклеўсиз жазыў ҳуқықын бериў\n"
            f"{EMOJI_DOT} <code>/taqiq</code> — Берилген жеңилликти бийкарлаў\n"
            f"{EMOJI_DOT} <code>/reset</code> — Пайдаланыўшы есаплағышын нольлеў\n"
            f"{EMOJI_DOT} <code>/reset_all</code> — Пүткил топарды нольлеў"
        ),
        "uz": (
            f"{EMOJI_BOOK} <b>Guruh Adminlari uchun buyruqlar:</b>\n\n"
            f"{EMOJI_DOT} <code>/set 5</code> — A'zolarga 5 ta odam qo'shish shartini qo'yish (o'chirish: <code>/set 0</code>)\n"
            f"{EMOJI_DOT} <code>/setchannel @kanal</code> — Majburiy kanal ulash\n"
            f"{EMOJI_DOT} <code>/delchannel</code> — Majburiy kanalni o'chirish\n"
            f"{EMOJI_DOT} <code>/lang</code> — Guruh tilini o'zgartirish (UZ / RU / EN)\n"
            f"{EMOJI_DOT} <code>/captcha on/off</code> — Matematik Captchani yoqish/o'chirish\n"
            f"{EMOJI_DOT} <code>/anticheat on/off</code> — Chiqib ketganlar hisobdan ayirilsinmi\n"
            f"{EMOJI_DOT} <code>/status</code> — Guruhning to'liq sozlamalari va statistikasi\n"
            f"{EMOJI_DOT} <code>/top</code> — Eng ko'p odam qo'shganlar TOP-10\n"
            f"{EMOJI_DOT} <code>/check @username</code> — A'zo kimlarni qo'shganini tekshirish\n"
            f"{EMOJI_DOT} <code>/imtiyoz</code> — Foydalanuvchiga cheklovsiz yozish huquqini berish\n"
            f"{EMOJI_DOT} <code>/taqiq</code> — Berilgan imtiyozni bekor qilish\n"
            f"{EMOJI_DOT} <code>/reset</code> — Foydalanuvchi hisoblagichini nollash\n"
            f"{EMOJI_DOT} <code>/reset_all</code> — Butun guruhni nollash"
        ),
        "ru": (
            f"{EMOJI_BOOK} <b>Команды для администраторов группы:</b>\n\n"
            f"{EMOJI_DOT} <code>/set 5</code> — Обязать добавить 5 участников (отключение: <code>/set 0</code>)\n"
            f"{EMOJI_DOT} <code>/setchannel @канал</code> — Установить обязательный канал\n"
            f"{EMOJI_DOT} <code>/delchannel</code> — Удалить обязательный канал\n"
            f"{EMOJI_DOT} <code>/lang</code> — Изменить язык группы (UZ / RU / EN)\n"
            f"{EMOJI_DOT} <code>/captcha on/off</code> — Вкл/выкл математическую капчу\n"
            f"{EMOJI_DOT} <code>/anticheat on/off</code> — Снимать ли баллы при выходе приглашенных\n"
            f"{EMOJI_DOT} <code>/status</code> — Настройки и статистика группы\n"
            f"{EMOJI_DOT} <code>/top</code> — ТОП-10 участников\n"
            f"{EMOJI_DOT} <code>/check @username</code> — Проверить приглашения участника\n"
            f"{EMOJI_DOT} <code>/imtiyoz</code> — Выдать иммунитет (белый список)\n"
            f"{EMOJI_DOT} <code>/taqiq</code> — Отозвать иммунитет\n"
            f"{EMOJI_DOT} <code>/reset</code> — Сбросить счетчик участника\n"
            f"{EMOJI_DOT} <code>/reset_all</code> — Сбросить счетчики группы"
        ),
        "en": (
            f"{EMOJI_BOOK} <b>Group Administrator Commands:</b>\n\n"
            f"{EMOJI_DOT} <code>/set 5</code> — Require 5 invites to chat (disable: <code>/set 0</code>)\n"
            f"{EMOJI_DOT} <code>/setchannel @channel</code> — Set mandatory channel\n"
            f"{EMOJI_DOT} <code>/delchannel</code> — Remove mandatory channel\n"
            f"{EMOJI_DOT} <code>/lang</code> — Change group language (UZ / RU / EN)\n"
            f"{EMOJI_DOT} <code>/captcha on/off</code> — Toggle math captcha\n"
            f"{EMOJI_DOT} <code>/anticheat on/off</code> — Deduct points when members leave\n"
            f"{EMOJI_DOT} <code>/status</code> — Group settings and stats\n"
            f"{EMOJI_DOT} <code>/top</code> — TOP-10 leaderboard\n"
            f"{EMOJI_DOT} <code>/check @username</code> — Inspect user invites\n"
            f"{EMOJI_DOT} <code>/imtiyoz</code> — Grant whitelist exemption\n"
            f"{EMOJI_DOT} <code>/taqiq</code> — Revoke exemption\n"
            f"{EMOJI_DOT} <code>/reset</code> — Reset user counter\n"
            f"{EMOJI_DOT} <code>/reset_all</code> — Reset entire group"
        )
    }
}


def tr(key: str, lang: str = "qr", **kwargs) -> str:
    """Matnni til bo'yicha olish va formatlash"""
    text_dict = TEXTS.get(key, {})
    template = text_dict.get(lang, text_dict.get("qr", text_dict.get("uz", "")))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template


def clean_alert_text(text: str) -> str:
    """
    Telegram callback.answer (popup/toast) larda HTML teglari va custom emojilar (<tg-emoji>)
    ishlamaydi va xom kod sifatida ko'rinib qoladi.
    Ushbu funksiya barcha HTML teglarni tozalab, sof matn va oddiy emojilarni qoldiradi.
    """
    if not text:
        return ""
    # <tg-emoji ...>...</tg-emoji> ichidagi fallback emojini saqlab qolamiz:
    clean = re.sub(r'<tg-emoji[^>]*>(.*?)</tg-emoji>', r'\1', text)
    # Boshqa barcha HTML teglarini (<b>, <i>, <code> va h.k.) tozalaymiz:
    clean = re.sub(r'<[^>]+>', '', clean)
    return clean.strip()
