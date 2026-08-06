import os
import disnake
from disnake.ext import commands
from disnake.ui import StringSelect, View, Modal, TextInput
import gspread
from google.oauth2.service_account import Credentials

intents = disnake.Intents.default()
intents.members = True
bot = commands.InteractionBot(intents=intents)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "ЧС Сервера")

def get_sheet():
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file('credentials.json', scopes=scopes)
    client = gspread.authorize(creds)
    return client.open(GOOGLE_SHEET_NAME).sheet1

def add_to_sheet(nickname, position, discord_id, reason, amnesty):
    try:
        sheet = get_sheet()
        sheet.append_row([str(nickname), str(position), str(discord_id), str(reason), str(amnesty)])
        return True
    except Exception as e:
        print(f"[Google Sheets Error] Ошибка записи: {e}")
        return False

def find_in_sheet(search_id):
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        for row in records:
            if str(row.get("Discord ID")) == str(search_id):
                return row
        return None
    except Exception as e:
        print(f"[Google Sheets Error] Ошибка поиска: {e}")
        return None

def remove_from_sheet(unban_id):
    try:
        sheet = get_sheet()
        cells = sheet.findall(str(unban_id))
        for cell in cells:
            if cell.col == 3:  # Колонка C (Discord ID)
                sheet.delete_rows(cell.row)
                return True
        return False
    except Exception as e:
        print(f"[Google Sheets Error] Ошибка удаления: {e}")
        return False

def get_blacklist_embed():
    embed = disnake.Embed(color=0x1a1c23)
    embed.set_author(name="YSW", icon_url="https://cdn.discordapp.com/emojis/1524861838737543339.png")
    
    static_text = (
        "Логирование Администрации\n\n"
        "<:GoogleForms:1524860446702702712> Заполняем строго по форме\n"
        "<:blocked_IDS:1524860941479448666> При каких либо ошибках обращаться к <@1263892996928045091>"
    )
    
    try:
        sheet = get_sheet()
        records = sheet.get_all_records()
        
        if not records:
            description = f"{static_text}\n\n------------------------------------------------------------\n---------------------\n\n<:emojigg_els:1524861049268994190> **Список ЧС сервера пуст.**"
        else:
            elements = []
            for r in records:
                nick = r.get("Никнейм", "Неизвестно")
                pos = r.get("Должность", "—")
                discord_id = r.get("Discord ID", "")
                elements.append(f"<:skull_clown:1524861429599961279> **{nick}** [{pos}] — <@{discord_id}>")
                
            description = f"{static_text}\n\n------------------------------------------------------------\n---------------------\n\n" + "\n".join(elements)
    except Exception as e:
        description = f"{static_text}\n\n❌ Ошибка подключения к Google Таблице: {e}"

    embed.description = description
    return embed

@bot.event
async def on_ready():
    print(f'=== БОТ ЗАПУЩЕН ({bot.user}) ===')

class AddBlacklistModal(Modal):
    def __init__(self):
        components = [
            TextInput(label="Никнейм", placeholder="Введите никнейм", custom_id="nickname"),
            TextInput(label="Должность", placeholder="Введите должность", custom_id="position"),
            TextInput(label="Discord ID", placeholder="Введите Discord ID аккаунта", custom_id="discord_id"),
            TextInput(label="Причина", placeholder="Укажите причину внесения в ЧС", custom_id="reason", style=disnake.TextInputStyle.paragraph),
            TextInput(label="Амнистия", placeholder="Без амнистии / Срок амнистии", custom_id="amnesty")
        ]
        super().__init__(title="➕ Добавление в ЧС", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        
        nickname = inter.text_values["nickname"]
        position = inter.text_values["position"]
        discord_id = inter.text_values["discord_id"]
        reason = inter.text_values["reason"]
        amnesty = inter.text_values["amnesty"]
        
        success = add_to_sheet(nickname, position, discord_id, reason, amnesty)
        
        if success:
            await inter.edit_original_message(content="✅ Пользователь успешно добавлен!")
            try:
                await inter.message.edit(embed=get_blacklist_embed())
            except Exception:
                pass
        else:
            await inter.edit_original_message(content="❌ Ошибка записи в Google Таблицу.")

class CheckBlacklistModal(Modal):
    def __init__(self):
        components = [
            TextInput(label="Discord ID", placeholder="Введите Discord ID для проверки", custom_id="search_id")
        ]
        super().__init__(title="🔎 Проверка по ЧС", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        search_id = inter.text_values["search_id"]
        
        row = find_in_sheet(search_id)
        
        if not row:
            return await inter.edit_original_message(content="🧬 **Пользователь с таким Discord ID не найден.**")

        embed = disnake.Embed(title="🛸 Запись из Базы ЧС", color=0x1a1c23)
        embed.add_field(name="<:KirbyManFace:1524862903910666353> Пользователь", value=f"**{row.get('Никнейм')}**\nДискорд: <@{row.get('Discord ID')}> (`{row.get('Discord ID')}`)", inline=False)
        embed.add_field(name="💼 Должность", value=row.get("Должность", "—"), inline=False)
        embed.add_field(name="📝 Причина", value=row.get("Причина", "—"), inline=False)
        embed.add_field(name="<:Timer:1524862754207563967> Амнистия", value=row.get("Амнистия", "—"), inline=False)
        
        await inter.edit_original_message(embed=embed)

class UnbanBlacklistModal(Modal):
    def __init__(self):
        components = [
            TextInput(label="Discord ID", placeholder="Введите Discord ID для амнистии", custom_id="unban_id")
        ]
        super().__init__(title="🔓 Амнистия (Удаление из ЧС)", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)
        unban_id = inter.text_values["unban_id"]
        
        success = remove_from_sheet(unban_id)
        
        if success:
            await inter.edit_original_message(content=f"🔓 Пользователь с Discord ID `{unban_id}` удален!")
            try:
                await inter.message.edit(embed=get_blacklist_embed())
            except Exception:
                pass
        else:
            await inter.edit_original_message(content="❌ Пользователь с таким Discord ID не найден.")

class BlacklistDropdown(StringSelect):
    def __init__(self):
        options = [
            disnake.SelectOption(label="Check (Проверить ID)", value="menu_check", description="Поиск по Discord ID", emoji="<:search:1524862195790381147>"),
            disnake.SelectOption(label="Add (Добавить в ЧС)", value="menu_add", description="Внести нарушителя в ЧС", emoji="<:Plus:1524862314640314712>"),
            disnake.SelectOption(label="Unban (Амнистировать)", value="menu_unban", description="Удалить из ЧС по Discord ID", emoji="<:emojigg_els:1524861049268994190>"),
            disnake.SelectOption(label="Refresh (Обновить список)", value="menu_refresh", description="Перезагрузить список", emoji="<a:lding:1524862506970120264>")
        ]
        super().__init__(custom_id="blacklist_control", placeholder="⚙️ Управление ЧС", min_values=1, max_values=1, options=options)

    async def callback(self, inter: disnake.MessageInteraction):
        value = self.values[0]
        
        if value == "menu_refresh":
            await inter.response.edit_message(embed=get_blacklist_embed())
        elif value == "menu_check":
            await inter.response.send_modal(modal=CheckBlacklistModal())
        elif value == "menu_add":
            if not inter.permissions.administrator:
                return await inter.response.send_message("👑 У вас нет прав Администратора!", ephemeral=True)
            await inter.response.send_modal(modal=AddBlacklistModal())
        elif value == "menu_unban":
            if not inter.permissions.administrator:
                return await inter.response.send_message("👑 У вас нет прав Администратора!", ephemeral=True)
            await inter.response.send_modal(modal=UnbanBlacklistModal())

class BlacklistDropdownView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(BlacklistDropdown())

@bot.slash_command(name="list", description="Вывести панель ЧС")
async def list_cmd(inter):
    embed = get_blacklist_embed()
    view = BlacklistDropdownView()
    await inter.response.send_message(embed=embed, view=view)

@bot.slash_command(name="unban", description="Амнистировать по Discord ID")
@commands.has_permissions(administrator=True)
async def unban_cmd(inter, discord_id: str):
    success = remove_from_sheet(discord_id)
    if success:
        await inter.response.send_message(f"🔓 Пользователь с Discord ID `{discord_id}` успешно амнистирован!", ephemeral=True)
    else:
        await inter.response.send_message(f"❌ Пользователь с Discord ID `{discord_id}` не найден.", ephemeral=True)

bot.run(BOT_TOKEN)
