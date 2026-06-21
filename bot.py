import discord
from discord.ext import commands

# AYARLAR (Burayı kendi bilgilerine göre güncelle)
TOKEN = os.environ.get ("TOKEN")
ANA_KANAL_ID = 1518042695984087162 
active_rooms = {} 

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 1. YENİ MODAL (Limit için)
class LimitModal(discord.ui.Modal):
    def __init__(self, voice_channel):
        super().__init__(title="Kişi Sınırı Ayarla")
        self.voice_channel = voice_channel
        self.limit = discord.ui.TextInput(label="Maksimum Kişi Sayısı", placeholder="0-99 arası bir sayı gir", min_length=1, max_length=2)
        self.add_item(self.limit)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await self.voice_channel.edit(user_limit=int(self.limit.value))
            await interaction.response.send_message(f"✅ Limit {self.limit.value} olarak ayarlandı.", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Geçerli bir sayı girin!", ephemeral=True)

# 2. GÜNCELLENMİŞ VIEW (Limit ve Yönetim Eklendi)
class RoomControlView(discord.ui.View):
    def __init__(self, voice_channel):
        super().__init__(timeout=None)
        self.voice_channel = voice_channel
        self.locked = False
        self.hidden = False

    @discord.ui.button(label="Kanal Adı", style=discord.ButtonStyle.secondary, emoji="📝")
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RenameModal(self.voice_channel))

    @discord.ui.button(label="Limit Ayarı", style=discord.ButtonStyle.secondary, emoji="⬇️")
    async def limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(LimitModal(self.voice_channel))

    @discord.ui.button(label="Kilitle", style=discord.ButtonStyle.danger, emoji="🔒")
    async def lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.locked = not self.locked
        await self.voice_channel.set_permissions(interaction.guild.default_role, connect=not self.locked)
        await interaction.response.send_message("🔒 Girişler kapatıldı!" if self.locked else "🔓 Girişler açıldı!", ephemeral=True)

    @discord.ui.button(label="Gizle", style=discord.ButtonStyle.success, emoji="👁️")
    async def hide(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.hidden = not self.hidden
        await self.voice_channel.set_permissions(interaction.guild.default_role, view_channel=not self.hidden)
        await interaction.response.send_message("👁️ Kanal gizlendi!" if self.hidden else "👁️ Kanal görünür hale getirildi!", ephemeral=True)

    @discord.ui.select(placeholder="👥 Kullanıcı Yönet", options=[discord.SelectOption(label="Odadan At", value="kick")])
    async def manage_user(self, interaction: discord.Interaction, select: discord.ui.Select):
        members = [m for m in self.voice_channel.members if m != interaction.user]
        if not members:
            await interaction.response.send_message("Odada atılacak başka kimse yok!", ephemeral=True)
            return
        # Basitlik olması için odadaki son kişiyi atar
        await members[-1].move_to(None)
        await interaction.response.send_message(f"✅ {members[-1].display_name} odadan atıldı.", ephemeral=True)

    @discord.ui.button(label="Yardım", style=discord.ButtonStyle.primary, emoji="ℹ️")
    async def help_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="ℹ️ Oda Yönetim Kılavuzu", description="Butonların işlevleri:\n📝 **Kanal Adı**: Odanın ismini değiştirir.\n⬇️ **Limit Ayarı**: Kişi sınırı koyar.\n🔒 **Kilitle**: Girişleri kapatır.\n👁️ **Gizle**: Kanalı gizler.\n👥 **Kullanıcı Yönet**: Odadaki üyeyi atar.", color=discord.Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True)
# 3. EVENTLER
@bot.event
async def on_voice_state_update(member, before, after):
    # ODA OLUŞTURMA
    if after.channel and after.channel.id == ANA_KANAL_ID:
        if member.id in active_rooms: return
        guild = member.guild
        category = after.channel.category
        
        v_channel = await guild.create_voice_channel(name=f"{member.display_name}'in Odası", category=category)
        t_channel = await guild.create_text_channel(name=f"{member.display_name.lower()}-odasi", category=category)
        
        await t_channel.set_permissions(guild.default_role, read_messages=False)
        await t_channel.set_permissions(member, read_messages=True, send_messages=True)
        
        embed = discord.Embed(title="BAGIMSIZ", description="Merhaba! Burası senin odan. Aşağıdaki butonları kullanarak odanı yönetebilirsin. Nasıl kullanılır öğrenmek için Yardım butonuna bas.", color=discord.Color.dark_theme())
        await t_channel.send(content=f"{member.mention}", embed=embed, view=RoomControlView(v_channel))
        
        active_rooms[member.id] = {"voice": v_channel.id, "text": t_channel.id}
        await member.move_to(v_channel)

    # ODA SİLME
    if before.channel and member.id in active_rooms:
        data = active_rooms[member.id]
        if before.channel.id == data["voice"]:
            if len(before.channel.members) == 0:
                t_channel = before.channel.guild.get_channel(data["text"])
                if t_channel: await t_channel.delete()
                await before.channel.delete()
                del active_rooms[member.id]

bot.run(TOKEN)