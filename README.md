# 🛡 Qorıqshı Bot (@qoriqshibot) — Telegram Guruh Himoyachisi

Telegram guruhlarini spamlardan, botlardan va firibgarlikdan himoya qiluvchi, a'zo qo'shish va rasmiy kanallarga a'zo bo'lish majburiyatini boshqaruvchi yuqori unumdorlikdagi asinxron bot.

Asosiy va birlamchi til: **Qoraqalpoqcha (`Qaraqalpaqsha`)** 🇺🇿. Qo'shimcha tillar: **O'zbekcha** 🇺🇿, **Русский** 🇷🇺, **English** 🇬🇧.

---

## 🌟 Imkoniyatlar va Funksiyalar

1. 🔒 **Majburiy a'zo qo'shish limiti (`/set 5`)**:
   - Yangi a'zolar guruhda yozishi uchun admin belgilagan miqdorda do'stlarini qo'shishi shart.
   - Bajarilmaguncha a'zoga xabar yozish cheklanadi, ammo odam qo'shish huquqi ochiq qoladi.
2. 📢 **Kanalga majburiy a'zolik (`/setchannel @kanal`)**:
   - Guruhda yozish uchun rasmiy kanalga a'zo bo'lish talabi. Bot avtomatik a'zolikni tekshiradi.
3. 🧩 **Matematik Captcha (`/captcha on/off`)**:
   - Yangi qo'shilgan a'zolarga matematik misol chiqaradi (4 ta variantli tugma, 3 ta urinish, 5 daqiqalik taymer).
   - Robotlar va spam-botlardan 100% himoya.
4. 🛡 **Anti-Cheat tizimi (`/anticheat on/off`)**:
   - Taklif qilingan a'zo guruhdan chiqib ketsa, uni taklif qilgan a'zoning hisobidan avtomatik ball ayiriladi.
5. 🚫 **Takroriy qo'shishlardan himoya**:
   - Bitta a'zo qayta-qayta qo'shilganda yangi ball berilmaydi.
6. 🧹 **Xizmat xabarlarini tozalash (`/service_msg on/off`)**:
   - Guruhga a'zo qo'shildi / chiqib ketdi kabi xizmat xabarlarini avtomatik o'chirib tozalab turadi.
7. 🏆 **Reyting va statistika (`/top`, `/status`, `/my`)**:
   - Eng faol TOP-10 a'zolar ro'yxati, guruhning to'liq parametrlari va shaxsiy takliflar tarixi.
8. ⭐ **Imtiyoz tizimi (`/imtiyoz`, `/taqiq`)**:
   - Tanlangan a'zoga hech qanday cheklovlarsiz yozish imtiyozini berish yoki bekor qilish.
9. 🌐 **Ko'p tilli interfeys (`/lang`)**:
   - Qoraqalpoq, O'zbek, Rus va Ingliz tillarini to'liq qo'llab-quvvatlaydi.

---

## 📜 Buyruqlar Ro'yxati

| Buyruq | Kim uchun | Tavsif |
|---|---|---|
| `/set 5` | Admin | Guruhda yozish uchun a'zoga 5 ta odam qo'shish talabini qo'yish (o'chirish: `/set 0`) |
| `/setchannel @kanal` | Admin | Guruhga majburiy a'zo bo'lish kanalini ulash |
| `/delchannel` | Admin | Ulangan majburiy kanalni o'chirish |
| `/channel` | Hamma | Guruhga ulangan kanal haqida ma'lumot |
| `/captcha on/off` | Admin | Matematik Captcha himoyasini yoqish/o'chirish |
| `/anticheat on/off` | Admin | Chiqib ketgan a'zolar uchun ball ayirish tizimi |
| `/service_msg on/off` | Admin | Xizmat xabarlarini (kirdi/chiqdi) tozalash |
| `/status` | Admin | Guruh sozlamalari va umumiy statistikasi |
| `/top` | Hamma | Guruhda eng ko'p odam qo'shgan TOP-10 a'zo |
| `/check @user` | Admin | A'zo kimlarni qo'shganini batafsil tekshirish |
| `/imtiyoz` | Admin | Foydalanuvchiga cheklovsiz yozish imtiyozini berish |
| `/taqiq` | Admin | Berilgan imtiyozni bekor qilish |
| `/reset` | Admin | Foydalanuvchi hisoblagichini 0 ga tushirish |
| `/reset_all` | Admin | Butun guruh statistikasini nollash |
| `/lang` | Admin | Guruhning asosiy tilini tanlash |
| `/my` / `/mymembers` | Hamma | O'z statistikasini va qo'shgan a'zolarini ko'rish |
| `/help` | Hamma | Qo'llanma va buyruqlar ro'yxati |

---

## 🛠 Mahalliy Ishga Tushirish (Local Run)

1. **Repozitoriyani yuklab oling va papkaga kiring**:
   ```bash
   cd esapshibot
   ```

2. **Virtual muhit yarating va faollashtiring**:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux / macOS:
   source venv/bin/activate
   ```

3. **Kutubxonalarni o'rnating**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Muhit o'zgaruvchilarini sozlang**:
   `.env.example` faylidan nusxa olib `.env` faylini yarating:
   ```env
   BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
   ADMINS=12345678,87654321
   DB_PATH=database/bot.db
   ```

5. **Botni ishga tushiring**:
   ```bash
   python bot.py
   ```

---

## 🚀 Railway Serverga Joylash (Railway Deployment)

Ushbu bot **Railway** platformasida to'xtovsiz (24/7) ishlash uchun to'liq moslashtirilgan.

### 1-qadam: GitHub-ga joylash
```bash
git init
git add .
git commit -m "Initial commit: Qoriqshi bot ready for production"
git branch -M main
git remote add origin https://github.com/USERNAME/REPO_NAME.git
git push -u origin main
```
*(Eslatma: `.gitignore` avtomatik tarzda `.env` va `bot.db` fayllarini GitHub-ga chiqib ketishidan himoya qiladi).*

### 2-qadam: Railway-da loyiha yaratish
1. [Railway.app](https://railway.app) ga kiring va tizimga kiring.
2. **"New Project"** -> **"Deploy from GitHub repo"** ni bosing va repozitoriyangizni tanlang.
3. Loyiha avtomatik `Dockerfile` orqali yig'iladi.

### 3-qadam: Muhit o'zgaruvchilarini (Variables) kiritish
Railway boshqaruv panelida loyihangiz ustiga bosing va **Variables** bo'limiga o'ting:
- `BOT_TOKEN` = Sizning bot tokeningiz (`@BotFather` dan olingan)
- `ADMINS` = Sizning Telegram ID raqamingiz
- `DB_PATH` = `/data/bot.db`

### 4-qadam: Ma'lumotlar bazasi xotirasini saqlash (Volume)
Bot qayta ishga tushganda yoki yangilanganda ma'lumotlar o'chib ketmasligi uchun:
1. Railway Dashboard-da **"+ New"** -> **"Volume"** tugmasini bosing.
2. Mount Path sifatida `/data` deb kiriting.
3. Shunda SQLite bazasi doimiy xotirada xavfsiz saqlanadi.

Bot avtomatik tarzda ishga tushadi va 24/7 rejimda guruhlarni himoya qiladi!
