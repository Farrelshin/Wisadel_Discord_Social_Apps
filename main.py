import os
from dotenv import load_dotenv
import json
import discord
import aiohttp # [BARU] Import aiohttp untuk HTTP request
from discord.ext import commands
from discord import app_commands

# [BARU] Masukkan URL Webhook Production n8n kamu di sini
N8N_WEBHOOK_URL = "https://ptilopsis.app.n8n.cloud/webhook/11a19b0a-b7a7-4b59-80db-070377cdc1ba"

# 1. Mengatur intents (hak akses) default untuk bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# 2. Inisialisasi bot
client = commands.Bot(
    command_prefix="w",
    intents=intents,
    case_insensitive=True,
    help_command=None,
)

MY_GUILD = discord.Object(id=1202785633895194716)

@client.event
async def on_ready():
    print(f'Logged on as {client.user}!')
    try:
        client.tree.clear_commands(guild=MY_GUILD)
        await client.tree.sync(guild=MY_GUILD)
        synced = await client.tree.sync()
        print(f'Synced {len(synced)} global command(s).')
    except Exception as e:
        print(f'Error syncing commands: {e}')

# ==========================================
# --- PENYIMPANAN PER-SERVER (MULTI-GUILD) ---
# ==========================================
ALLOWED_FILE = "allowed_channels.json"
DISCOHOOK_FILE = "backups-2026-10-22.json"

def load_allowed():
    try:
        with open(ALLOWED_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {}
            return {int(g_id): set(c_ids) for g_id, c_ids in data.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_allowed():
    data_to_save = {str(g_id): list(c_ids) for g_id, c_ids in ALLOWED_CHANNELS_PER_GUILD.items()}
    with open(ALLOWED_FILE, "w") as f:
        json.dump(data_to_save, f, indent=4)

ALLOWED_CHANNELS_PER_GUILD = load_allowed()

def is_channel_allowed(guild, channel):
    if not guild:
        return True
    
    allowed_set = ALLOWED_CHANNELS_PER_GUILD.get(guild.id, set())
    if not allowed_set:
        return True
        
    if channel.id in allowed_set:
        return True
        
    parent_id = getattr(channel, "parent_id", None)
    return parent_id in allowed_set

@client.check
async def cek_restrict(ctx):
    return is_channel_allowed(ctx.guild, ctx.channel)

@client.event
async def on_command_error(ctx, error):
    if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
        return
    print(f'Error command: {error}')


# ==========================================
# --- SISTEM INTEGRASI DISCOHOOK JSON ---
# ==========================================
def get_discohook_backup(backup_name):
    """Membaca file JSON Discohook dan mengambil Embeds & Components berdasarkan nama backup."""
    try:
        with open(DISCOHOOK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for backup in data.get("backups", []):
                if backup.get("name") == backup_name:
                    msg_data = backup["messages"][0]["data"]
                    
                    # 1. Konversi raw JSON Embed menjadi discord.Embed
                    embeds = [discord.Embed.from_dict(e) for e in msg_data.get("embeds", [])]
                    
                    # 2. Ambil data komponen (untuk tombol)
                    components = msg_data.get("components", [])
                    return embeds, components
    except Exception as e:
        print(f"Error membaca {DISCOHOOK_FILE}: {e}")
    return None, None

class DiscohookView(discord.ui.View):
    """Mengubah format komponen JSON Discohook menjadi View & Tombol interaktif discord.py."""
    def __init__(self, components_data):
        super().__init__(timeout=None)
        
        # Loop semua baris aksi (ActionRow / type 1)
        for action_row in components_data:
            if action_row.get("type") == 1:
                # Loop semua tombol di dalam baris tersebut
                for btn in action_row.get("components", []):
                    # Hanya memproses tombol berupa Link (type 2, style 5)
                    if btn.get("type") == 2 and btn.get("style") == 5:
                        emoji_obj = None
                        if "emoji" in btn:
                            e_id = int(btn["emoji"]["id"]) if btn["emoji"].get("id") else None
                            emoji_obj = discord.PartialEmoji(
                                name=btn["emoji"].get("name"),
                                id=e_id,
                                animated=btn["emoji"].get("animated", False)
                            )
                        
                        # Tambahkan tombol ke dalam View
                        self.add_item(discord.ui.Button(
                            label=btn.get("label"), 
                            url=btn.get("url"), 
                            emoji=emoji_obj
                        ))


class PanduanDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Role Utama", description="Informasi mengenai role utama di server ini.", emoji="🛡️"),
            discord.SelectOption(label="Leveling Role", description="Informasi mengenai grinding level role.", emoji="📈"),
            discord.SelectOption(label="UMA Familia", description="Informasi mengenai UMA Familia di server ini.", emoji="🐎"),
            discord.SelectOption(label="Server Map", description="Informasi mengenai category dan channel di server ini.", emoji="🗺️"),
            discord.SelectOption(label="Useful Links", description="Informasi tentang link serbaguna di server ini.", emoji="🔗"),
        ]
        super().__init__(placeholder="Pengen tau apa nih di server kita?", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        pilihan = self.values[0]
        
        # Mapping nama opsi di Dropdown ke nama Backup di Discohook JSON
        backup_map = {
            "Role Utama": "Role Utama",
            "Leveling Role": "Leveling roles",
            "UMA Familia": "UMA FAMILIA",
            "Server Map": "Server map",
            "Useful Links": "Useful links"
        }
        
        target_backup = backup_map.get(pilihan)
        
        # Ambil data dinamis dari file JSON
        embeds, components_data = get_discohook_backup(target_backup)
        
        if embeds:
            # Jika ada data tombol (seperti di Useful Links), buat View-nya
            view = DiscohookView(components_data) if components_data else None
            
            # Kirim Embed (dan tombol jika ada) secara ephemeral
            if view and len(view.children) > 0:
                await interaction.response.send_message(embeds=embeds, view=view, ephemeral=True)
            else:
                await interaction.response.send_message(embeds=embeds, ephemeral=True)
        else:
            await interaction.response.send_message("❌ Gagal memuat data dari file Discohook.", ephemeral=True)

class PanduanView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PanduanDropdown())


# ==========================================
# --- BALASAN KATA KUNCI (TANPA PREFIX) ---
# ==========================================
@client.event
async def on_message(message):
    # 1. Abaikan pesan dari bot lain (termasuk dirinya sendiri)
    if message.author.bot:
        return

    # 2. Jika pesan berasal dari Server (Guild), terapkan filter Restrict Channel
    # Jika pesan dari DM (message.guild adalah None), filter ini otomatis dilewati
    if message.guild:
        if not is_channel_allowed(message.guild, message.channel):
            return

    pesan = message.content.lower()
    kata_sapaan = ['halo wisadel', 'halo']
    kata_pujian = ['kamu hebat sekali wisadel', 'hebat sekali', 'kamu hebat']
    kata_pintar = ['sepertinya kamu sangat pintar ya wisadel', 'pintar juga kamu', 'kamu pintar sekali']
    kata_kangen = ['hai wisadel, aku baru saja ingin mencarimu', 'kamu kemana aja', 'ketemu juga kamu']

    # --- 1. CEK KATA KUNCI HARDCODE (STIKER) ---
    if any(kata in pesan for kata in kata_sapaan):
        try:
            sticker_balasan = await client.fetch_sticker(1562303852437569536)
            await message.reply('yo dokutah, adakah yang bisa ku bantu?', stickers=[sticker_balasan])
        except discord.NotFound:
            pass
    elif any(kata in pesan for kata in kata_pujian):
        try:
            sticker_balasan = await client.fetch_sticker(1562304055647150201)
            await message.reply('oiya dong jelas!', stickers=[sticker_balasan])
        except discord.NotFound:
            pass
    elif any(kata in pesan for kata in kata_pintar):
        try:
            sticker_balasan = await client.fetch_sticker(1562304321788313630)
            await message.reply('ugh, jangan membuatku marah dokutah!', stickers=[sticker_balasan])
        except discord.NotFound:
            pass
    elif any(kata in pesan for kata in kata_kangen):
        try:
            sticker_balasan = await client.fetch_sticker(1562303915045945395)
            await message.reply('oho, apa kamu merindukanku?', stickers=[sticker_balasan])
        except discord.NotFound:
            pass

    # --- 2. INTEGRASI N8N AI (Aktif saat di-mention ATAU lewat jalur DM) ---
    elif not message.guild or client.user in message.mentions:
        # Menerjemahkan semua mention di dalam pesan
        pertanyaan = message.content
        for user_mentioned in message.mentions:
            if user_mentioned.id == client.user.id:
                # Hapus mention ke Wisadel agar tidak masuk ke prompt AI
                pertanyaan = pertanyaan.replace(f'<@{client.user.id}>', '')
            else:
                # Ubah mention ID user lain menjadi nama tampilan (display name) mereka
                pertanyaan = pertanyaan.replace(f'<@{user_mentioned.id}>', user_mentioned.display_name)
        
        pertanyaan = pertanyaan.strip()
        
        if pertanyaan:
            async with message.channel.typing():
                # Memisahkan ID memori berdasarkan lokasi obrolan
                if message.guild:
                    id_memori = f"{message.author.id}-server-{message.guild.id}"
                else:
                    id_memori = f"{message.author.id}-dm"

                payload = {
                    "sessionId": id_memori, 
                    "chatInput": pertanyaan
                }
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(N8N_WEBHOOK_URL, json=payload) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                jawaban = data.get("output", "Maaf, format balasan n8n tidak sesuai ekspektasi.")
                                await message.reply(jawaban)
                            else:
                                await message.reply(f"Hmph! Koneksiku ke otak utama lagi error nih. (Status HTTP: {resp.status})")
                except Exception as e:
                    await message.reply("Ugh, sistem n8n ku sedang bermasalah atau mati!")
        return 

    await client.process_commands(message)

# ==========================================
# --- DAFTAR MESSAGE COMMANDS (PREFIX "w") ---
# ==========================================
async def balas_stiker(ctx, teks, sticker_id):
    try:
        sticker = await client.fetch_sticker(sticker_id)
        await ctx.reply(teks, stickers=[sticker])
    except discord.NotFound:
        await ctx.reply(teks)

@client.command(name="sapa")
async def wsapa(ctx):
    await balas_stiker(ctx, 'yo dokutah, adakah yang bisa ku bantu?', 1562303852437569536)

@client.command(name="pujian")
async def wpujian(ctx):
    await balas_stiker(ctx, 'oiya dong jelas!', 1562304055647150201)

@client.command(name="pintar")
async def wpintar(ctx):
    await balas_stiker(ctx, 'ugh, jangan membuatku marah dokutah!', 1562304321788313630)

@client.command(name="kangen")
async def wkangen(ctx):
    await balas_stiker(ctx, 'oho, apa kamu merindukanku?', 1562303915045945395)

@client.command(name="ping")
async def wping(ctx):
    latensi = round(client.latency * 1000)
    await ctx.send(f'Pong! 🏓 Latensi: `{latensi}ms`')

@client.command(name="bye")
async def wbye(ctx):
    await balas_stiker(ctx, 'ugh, ayolah main sedikit lebih lama', 1562304121996841001)

@client.command(name="help")
async def whelp(ctx):
    embed = discord.Embed(
        title="📖 Panduan Perintah Wisadel",
        description="Halo Dokutah! Berikut adalah daftar perintah dan fitur interaktif yang tersedia untukku:",
        color=discord.Color.red()
    )
    embed.add_field(
        name="💬 Command Prefix `w`",
        value="- `wsapa`, `wpujian`, `wpintar`, `wkangen`\n- `wping`, `wbye`\n- `wfarm <id>` : Cek drop rate material Arknights\n- `witemlist` : Lihat daftar ID material",
        inline=False
    )
    embed.add_field(
        name="⚡ Slash Commands",
        value="- `/halo` , `/printer`\n- `/kirim-panduan` : Kirim menu panduan server\n- `/restrictchannel`, `/unrestrictchannel`, `/restrictlist`",
        inline=False
    )
    await ctx.reply(embed=embed)

async def cari_channel(guild, cid):
    ch = guild.get_channel_or_thread(cid)
    if ch is None:
        try:
            ch = await guild.fetch_channel(cid)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return None
    return ch

# ==========================================
# --- DAFTAR SLASH COMMANDS ---
# ==========================================
@client.tree.command(name="halo", description="Bot akan menyapa Anda")
async def say_hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"halo juga dokutah {interaction.user.mention}!")

@client.tree.command(name="printer", description="Saya akan mencetak kata-kata yang Anda berikan")
async def printer(interaction: discord.Interaction, teks_masukan: str):
    await interaction.response.send_message(teks_masukan)

@client.tree.command(name="kirim-panduan", description="Kirim pesan panduan server interaktif")
@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
async def kirim_panduan(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Welcome to ┋ 🪩 ⁞ panduan-server!",
        description="Silakan gunakan menu *dropdown* di bawah untuk memilih informasi panduan server yang ingin kamu ketahui!",
        color=discord.Color.blurple()
    )
    await interaction.channel.send(embed=embed, view=PanduanView())
    await interaction.response.send_message("✅ Pesan panduan berhasil dikirim!", ephemeral=True)

@client.tree.command(name="restrictchannel", description="Aktifkan command w & kata kunci di channel ini (khusus server ini)")
@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
async def restrictchannel(interaction: discord.Interaction, channel_id: str):
    try:
        cid = int(channel_id.strip())
    except ValueError:
        await interaction.response.send_message("❌ ID channel harus berupa angka.", ephemeral=True)
        return
    channel = await cari_channel(interaction.guild, cid)
    if channel is None:
        await interaction.response.send_message("❌ Channel tidak ditemukan.", ephemeral=True)
        return

    g_id = interaction.guild.id
    if g_id not in ALLOWED_CHANNELS_PER_GUILD:
        ALLOWED_CHANNELS_PER_GUILD[g_id] = set()

    if cid in ALLOWED_CHANNELS_PER_GUILD[g_id]:
        await interaction.response.send_message("⚠️ Sudah diizinkan.", ephemeral=True)
        return

    ALLOWED_CHANNELS_PER_GUILD[g_id].add(cid)
    save_allowed()
    await interaction.response.send_message(f"🔒 Diaktifkan di <#{cid}>")

@client.tree.command(name="unrestrictchannel", description="Hapus channel dari daftar yang diizinkan di server ini")
@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
async def unrestrictchannel(interaction: discord.Interaction, channel_id: str):
    try:
        cid = int(channel_id.strip())
    except ValueError:
        await interaction.response.send_message("❌ ID channel harus berupa angka.", ephemeral=True)
        return

    g_id = interaction.guild.id
    guild_set = ALLOWED_CHANNELS_PER_GUILD.get(g_id, set())
    if cid not in guild_set:
        await interaction.response.send_message("⚠️ Tidak ada dalam daftar.", ephemeral=True)
        return

    guild_set.discard(cid)
    if not guild_set:
        ALLOWED_CHANNELS_PER_GUILD.pop(g_id, None)
    save_allowed()
    await interaction.response.send_message(f"🔓 <#{cid}> dihapus dari daftar.")

@client.tree.command(name="restrictlist", description="Lihat daftar channel yang diizinkan di server ini")
@app_commands.guild_only()
async def restrictlist(interaction: discord.Interaction):
    g_id = interaction.guild.id
    guild_set = ALLOWED_CHANNELS_PER_GUILD.get(g_id, set())
    if not guild_set:
        await interaction.response.send_message("📋 Aktif di semua channel.", ephemeral=True)
    else:
        daftar = "\n".join(f"- <#{c}>" for c in guild_set)
        await interaction.response.send_message(f"📋 Aktif di:\n{daftar}", ephemeral=True)

@client.tree.command(name="inforole", description="Melihat daftar member yang memiliki role tertentu")
@app_commands.describe(role="Pilih role yang ingin dicek")
async def inforole(interaction: discord.Interaction, role: discord.Role):
    # Mengambil daftar member dari role tersebut
    anggota = role.members
    
    if not anggota:
        await interaction.response.send_message(f"Cih, role {role.mention} kosong! Nggak ada membernya sama sekali.", ephemeral=True)
        return

    # Menggabungkan nama-nama member (maksimal 2000 karakter untuk Discord)
    daftar_nama = [f"- {member.mention} ({member.display_name})" for member in anggota]
    deskripsi = "\n".join(daftar_nama)
    
    # Memotong teks jika terlalu panjang (Discord membatasi deskripsi embed max 4096 karakter)
    if len(deskripsi) > 4000:
        deskripsi = deskripsi[:3990] + "\n...dan masih banyak lagi."

    embed = discord.Embed(
        title=f"📋 Daftar Member Role: {role.name} ({len(anggota)} orang)",
        description=deskripsi,
        color=role.color
    )
    embed.set_footer(text="Nih datanya. Jangan bilang aku nggak pernah bantuin kamu, Dokutah.")
    
    await interaction.response.send_message(embed=embed)

# ==========================================
# --- FITUR FARMING ARKNIGHTS (PENGUIN STATS) ---
# ==========================================
async def fetch_penguin_matrix(item_id: str, server: str = "US"):
    url = "https://penguin-stats.io/PenguinStats/api/v2/result/matrix"
    params = {"server": server, "itemFilter": item_id}
    
    # aiohttp sudah di-import di bagian atas file
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("matrix", [])
            return None

@client.command(name="farm")
async def wfarm(ctx, item_id: str):
    async with ctx.typing():
        matrix_data = await fetch_penguin_matrix(item_id)
        
        if not matrix_data:
            await ctx.reply("Hah? Servernya sedang bermasalah atau item ID itu tidak valid!")
            return

        # Sortir stage berdasarkan probabilitas drop tertinggi (minimal 500 run)
        sorted_stages = sorted(
            [d for d in matrix_data if d.get("times", 0) > 500],
            key=lambda x: x.get("quantity", 0) / x.get("times", 1), 
            reverse=True
        )
        
        if not sorted_stages:
            await ctx.reply("Tidak ada data drop rate yang cukup untuk material itu. Cari sendiri sana!")
            return

        best_stage = sorted_stages[0]
        drop_rate = (best_stage["quantity"] / best_stage["times"]) * 100

        embed = discord.Embed(
            title="📊 Laporan Farming Material", 
            description="Hmph, ini data drop ratenya. Jangan harap aku mau repot-repot mencarinya lagi untukmu, Dokutah!",
            color=0xFF5733
        )
        embed.add_field(name="Stage Terbaik", value=best_stage["stageId"], inline=True)
        embed.add_field(name="Drop Rate", value=f"{drop_rate:.1f}%", inline=True)
        embed.add_field(name="Total Sampel", value=f"{best_stage['times']} run", inline=True)
        embed.set_footer(text="Data bersumber dari Penguin Statistics")

        await ctx.reply(embed=embed)

@client.command(name="itemlist")
async def witemlist(ctx):
    embed = discord.Embed(
        title="📦 Daftar ID Material Arknights",
        description="Ugh, kalian ini merepotkan sekali! Ini daftar ID material yang paling sering di-farming. Jangan suruh aku mengulangnya lagi, Dokutah!",
        color=discord.Color.dark_purple()
    )
    
    # Kategori 1: Material Dasar
    dasar = (
        "🪨 **Orirock Cube:** `30012`\n"
        "🍬 **Sugar Pack:** `30022`\n"
        "🧵 **Polyester Pack:** `30032`\n"
        "🔩 **Oriron Cluster:** `30042`\n"
        "🧪 **Aketon Halif:** `30052`"
    )
    embed.add_field(name="Material Dasar (T3)", value=dasar, inline=False)
    
    # Kategori 2: Material Lanjutan
    lanjutan = (
        "🍺 **Loxic Kohl:** `30062`\n"
        "🪚 **Grindstone:** `30073`\n"
        "🧲 **Manganese Ore:** `30083`\n"
        "🦔 **RMA70-12:** `30103`\n"
        "💎 **Incandescent Alloy:** `30113`\n"
        "🍮 **Coagulating Gel:** `30123`"
    )
    embed.add_field(name="Material Lanjutan (T3)", value=lanjutan, inline=False)
    
    # Kategori 3: Material Baru (Chapter 9+)
    baru = (
        "💧 **Compound Cutting Fluid:** `30133`\n"
        "🧂 **Salt:** `30143`\n"
        "🪵 **Cyclic Hydrocarbon:** `30153`"
    )
    embed.add_field(name="Material Baru (T3)", value=baru, inline=False)

    embed.set_footer(text="Gunakan wfarm <id> untuk mengecek drop rate!")
    
    await ctx.reply(embed=embed)

# ==========================================
# --- INISIALISASI & JALANKAN BOT ---
# ==========================================
# Memuat variabel lingkungan dari file .env
load_dotenv()

# Mengambil token dan menjalankan bot
TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN is None:
    print("Error: DISCORD_TOKEN tidak ditemukan. Pastikan file .env sudah dibuat!")
else:
    client.run(TOKEN)
