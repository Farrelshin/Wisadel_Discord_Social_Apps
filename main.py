import json
import discord
from discord.ext import commands
from discord import app_commands

# 1. Mengatur intents (hak akses) default untuk bot
intents = discord.Intents.default()
intents.message_content = True

# 2. Inisialisasi bot: prefix "w", tanpa help bawaan (kita buat whelp sendiri)
client = commands.Bot(
    command_prefix="w",
    intents=intents,
    case_insensitive=True,
    help_command=None,
)

# Masukkan ID unik Server (Guild ID)
MY_GUILD = discord.Object(id=SERVER_ID)

@client.event
async def on_ready():
    print(f'Logged on as {client.user}!')

    try:
        # Hapus command khusus server lama supaya tidak muncul dobel
        client.tree.clear_commands(guild=MY_GUILD)
        await client.tree.sync(guild=MY_GUILD)

        # Sync sebagai command global (semua server)
        synced = await client.tree.sync()
        print(f'Synced {len(synced)} global command(s).')
    except Exception as e:
        print(f'Error syncing commands: {e}')

# ==========================================
# --- PENYIMPANAN PER-SERVER (MULTI-GUILD) ---
# ==========================================
ALLOWED_FILE = "allowed_channels.json"

def load_allowed():
    try:
        with open(ALLOWED_FILE, "r") as f:
            data = json.load(f)
            # Jika file JSON lama berbentuk list (bukan dict), reset ke format kosong agar tidak error
            if isinstance(data, list):
                return {}
            # Konversi key string dari JSON ke integer (guild_id dan channel_id)
            return {int(g_id): set(c_ids) for g_id, c_ids in data.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_allowed():
    # Ubah set ke list agar bisa disimpan ke JSON
    data_to_save = {str(g_id): list(c_ids) for g_id, c_ids in ALLOWED_CHANNELS_PER_GUILD.items()}
    with open(ALLOWED_FILE, "w") as f:
        json.dump(data_to_save, f, indent=4)

ALLOWED_CHANNELS_PER_GUILD = load_allowed()


# ==========================================
# --- CEK RESTRICT CHANNEL PER SERVER ---
# ==========================================
def is_channel_allowed(guild, channel):
    """Fungsi helper untuk mengecek apakah channel diizinkan di server tersebut."""
    if not guild:
        return True # Jika di luar server (misal DM), loloskan
    
    allowed_set = ALLOWED_CHANNELS_PER_GUILD.get(guild.id, set())
    
    # Jika server ini belum pernah di-restrict, aktif di semua channel
    if not allowed_set:
        return True
        
    if channel.id in allowed_set:
        return True
        
    # Thread ikut diizinkan jika channel induknya diizinkan
    parent_id = getattr(channel, "parent_id", None)
    return parent_id in allowed_set

@client.check
async def cek_restrict(ctx):
    return is_channel_allowed(ctx.guild, ctx.channel)

@client.event
async def on_command_error(ctx, error):
    # Abaikan diam-diam: command tidak ada atau channel direstrict
    if isinstance(error, (commands.CommandNotFound, commands.CheckFailure)):
        return
    print(f'Error command: {error}')


# ==========================================
# --- BALASAN KATA KUNCI (TANPA PREFIX) ---
# ==========================================

@client.event
async def on_message(message):
    # Mencegah bot membalas pesannya sendiri atau pesan dari bot lain / DM
    if message.author.bot or not message.guild:
        return

    # --- TAMBAHAN: CEK RESTRICT CHANNEL PER SERVER UNTUK KATA KUNCI ---
    if not is_channel_allowed(message.guild, message.channel):
        return

    # Ubah isi pesan menjadi huruf kecil semua agar mudah dideteksi
    pesan = message.content.lower()

    # --- DAFTAR KATA KUNCI VARIASI ---
    kata_sapaan = ['halo wisadel', 'halo']
    kata_pujian = ['kamu hebat sekali wisadel', 'hebat sekali', 'kamu hebat']
    kata_pintar = ['sepertinya kamu sangat pintar ya wisadel', 'pintar juga kamu', 'kamu pintar sekali']
    kata_kangen = ['hai wisadel, aku baru saja ingin mencarimu', 'kamu kemana aja', 'ketemu juga kamu']

    # 1. Jika pesan mengandung salah satu kata sapaan
    if any(kata in pesan for kata in kata_sapaan):
        try:
            sticker_balasan = await client.fetch_sticker(STICKER_ID)
            await message.reply('yo dokutah, adakah yang bisa ku bantu?', stickers=[sticker_balasan])
        except discord.NotFound:
            await message.reply('yo dokutah, adakah yang bisa ku bantu? (Gagal memuat stiker)')

    # 1.1 Pujian untuk Wisadel
    elif any(kata in pesan for kata in kata_pujian):
        try:
            sticker_balasan = await client.fetch_sticker(STICKER_ID)
            await message.reply('oiya dong jelas!', stickers=[sticker_balasan])
        except discord.NotFound:
            await message.reply('oiya dong jelas!')

    # 1.2 Membuat Wisadel marah jika dipuji
    elif any(kata in pesan for kata in kata_pintar):
        try:
            sticker_balasan = await client.fetch_sticker(STICKER_ID)
            await message.reply('ugh, jangan membuatku marah dokutah!', stickers=[sticker_balasan])
        except discord.NotFound:
            await message.reply('ugh, jangan membuatku marah dokutah!')

    # 1.3 Kangen wisadel
    elif any(kata in pesan for kata in kata_kangen):
        try:
            sticker_balasan = await client.fetch_sticker(STICKER_ID)
            await message.reply('oho, apa kamu merindukanku?', stickers=[sticker_balasan])
        except discord.NotFound:
            await message.reply('oho, apa kamu merindukanku?')

    # Proses command berprefix "w" (wping, wsapa, dll.)
    await client.process_commands(message)


@client.event
async def on_reaction_add(reaction, user):
    if user.bot or not reaction.message.guild:
        return
    await reaction.message.channel.send(f'{user.name} baru saja memberikan reaksi {reaction.emoji}!')


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
    await balas_stiker(ctx, 'yo dokutah, adakah yang bisa ku bantu?', STICKER_ID)

@client.command(name="pujian")
async def wpujian(ctx):
    await balas_stiker(ctx, 'oiya dong jelas!', STICKER_ID)

@client.command(name="pintar")
async def wpintar(ctx):
    await balas_stiker(ctx, 'ugh, jangan membuatku marah dokutah!', STICKER_ID)

@client.command(name="kangen")
async def wkangen(ctx):
    await balas_stiker(ctx, 'oho, apa kamu merindukanku?', STICKER_ID)

@client.command(name="ping")
async def wping(ctx):
    latensi = round(client.latency * 1000)
    await ctx.send(f'Pong! 🏓 Latensi: `{latensi}ms`')

@client.command(name="bye")
async def wbye(ctx):
    await balas_stiker(ctx, 'ugh, ayolah main sedikit lebih lama', STICKER_ID)

@client.command(name="help")
async def whelp(ctx):
    teks_bantuan = (
        "**Command Prefix `w`:**\n"
        "- `wsapa`, `wpujian`, `wpintar`, `wkangen`\n"
        "- `wping`: Tes respon Wisadel\n"
        "- `wbye`: Mengucapkan selamat tinggal\n"
        "- `whelp`: Menampilkan pesan ini\n\n"
        "**Percakapan Biasa (tanpa prefix):**\n"
        "- Sapa Wisadel dengan: `halo` atau `halo wisadel`\n"
        "- Puji Wisadel dengan: `kamu hebat`, `hebat sekali`, dll.\n"
        "- Buat Wisadel marah dengan: `pintar juga kamu`, `kamu pintar sekali`, dll.\n"
        "- Respon kangen dari Wisadel dengan: `kamu kemana aja`, `ketemu juga kamu`, dll.\n\n"
        "**Slash Commands:**\n"
        "- `/halo`: Wisadel akan menyapa Anda\n"
        "- `/printer`: Wisadel menirukan kata-kata Anda\n"
        "- `/restrictchannel <channel_ID>`: Command `w` & kata kunci hanya aktif di channel ini (khusus server ini)\n"
        "- `/unrestrictchannel <channel_ID>`: Hapus channel dari daftar server ini\n"
        "- `/restrictlist`: Lihat daftar channel yang diizinkan di server ini"
    )
    await ctx.reply(teks_bantuan)

async def cari_channel(guild, cid):
    """Cari channel biasa ATAU thread (termasuk thread yang diarsipkan)."""
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

@client.tree.command(name="restrictchannel", description="Aktifkan command w & kata kunci di channel ini (khusus server ini)")
@app_commands.guild_only()
@app_commands.describe(channel_id="ID channel yang diizinkan")
@app_commands.default_permissions(manage_guild=True)
async def restrictchannel(interaction: discord.Interaction, channel_id: str):
    try:
        cid = int(channel_id.strip())
    except ValueError:
        await interaction.response.send_message("❌ ID channel harus berupa angka.", ephemeral=True)
        return

    channel = await cari_channel(interaction.guild, cid)
    if channel is None:
        await interaction.response.send_message("❌ Channel/thread dengan ID itu tidak ditemukan di server ini.", ephemeral=True)
        return

    g_id = interaction.guild.id
    if g_id not in ALLOWED_CHANNELS_PER_GUILD:
        ALLOWED_CHANNELS_PER_GUILD[g_id] = set()

    if cid in ALLOWED_CHANNELS_PER_GUILD[g_id]:
        await interaction.response.send_message(f"⚠️ {channel.mention} sudah ada di daftar channel yang diizinkan di server ini.", ephemeral=True)
        return

    ALLOWED_CHANNELS_PER_GUILD[g_id].add(cid)
    save_allowed()
    daftar = ", ".join(f"<#{c}>" for c in ALLOWED_CHANNELS_PER_GUILD[g_id])
    await interaction.response.send_message(
        f"🔒 Command `w` & kata kunci di server ini sekarang **hanya** aktif di: {daftar}"
    )

@client.tree.command(name="unrestrictchannel", description="Hapus channel dari daftar yang diizinkan di server ini")
@app_commands.guild_only()
@app_commands.describe(channel_id="ID channel yang dihapus dari daftar")
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
        await interaction.response.send_message("⚠️ Channel itu tidak ada di daftar channel yang diizinkan di server ini.", ephemeral=True)
        return

    guild_set.discard(cid)
    # Jika set kosong, hapus key guild dari dictionary agar bersih
    if not guild_set:
        ALLOWED_CHANNELS_PER_GUILD.pop(g_id, None)
    save_allowed()

    channel = await cari_channel(interaction.guild, cid)
    nama = channel.mention if channel else f"`{cid}`"

    updated_set = ALLOWED_CHANNELS_PER_GUILD.get(g_id, set())
    if updated_set:
        daftar = ", ".join(f"<#{c}>" for c in updated_set)
        await interaction.response.send_message(
            f"🔓 {nama} dihapus dari daftar. Command `w` & kata kunci di server ini sekarang aktif di: {daftar}"
        )
    else:
        await interaction.response.send_message(
            f"🔓 {nama} dihapus dari daftar. Tidak ada channel yang direstrict lagi untuk server ini, kembali aktif di **semua channel**."
        )

@client.tree.command(name="restrictlist", description="Lihat daftar channel yang diizinkan di server ini")
@app_commands.guild_only()
async def restrictlist(interaction: discord.Interaction):
    g_id = interaction.guild.id
    guild_set = ALLOWED_CHANNELS_PER_GUILD.get(g_id, set())
    
    if not guild_set:
        await interaction.response.send_message("📋 Tidak ada restrict untuk server ini. Aktif di semua channel.", ephemeral=True)
    else:
        daftar = "\n".join(f"- <#{c}>" for c in guild_set)
        await interaction.response.send_message(f"📋 Command `w` & kata kunci di server ini hanya aktif di:\n{daftar}", ephemeral=True)


# Inisialisasi dan jalankan bot menggunakan Token Anda
client.run('YOUR_BOT_TOKEN')
