import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import bot_info
from datetime import datetime, timezone
from webcolors import hex_to_name, name_to_hex
from PIL import Image, ImageDraw
import io
import re
from math import fmod

class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @staticmethod
    def parse_gradient_input(gradient_input):
        colors = []
        positions = []
        gradient_parts = gradient_input.split(",")
        for part in gradient_parts:
            match = re.match(r"(.+)\s+(\d+)%?", part.strip())
            if match:
                color, position = match.groups()
                colors.append(color.strip())
                positions.append(int(position))
            else:
                colors.append(part.strip())
                positions.append(None)
        
        total_colors = len(colors)
        if any(pos is None for pos in positions):
            auto_positions = [round(i * 100 / (total_colors - 1)) for i in range(total_colors)]
            for i, pos in enumerate(positions):
                if pos is None:
                    positions[i] = auto_positions[i]
        
        return colors, positions
    
    def generate_gradient_image(self, colors, positions, width=800, height=100, background=(255, 255, 255)):
        gradient = Image.new("RGBA", (width, height))
        draw = ImageDraw.Draw(gradient)
        positions = [round(pos * width / 100) for pos in positions]
        for i in range(len(colors) - 1):
            start_color = self.parse_color(colors[i])
            end_color = self.parse_color(colors[i + 1])
            start_x = positions[i]
            end_x = positions[i + 1]
            for x in range(start_x, end_x):
                factor = (x - start_x) / (end_x - start_x)
                r = round(start_color[0] + factor * (end_color[0] - start_color[0]))
                g = round(start_color[1] + factor * (end_color[1] - start_color[1]))
                b = round(start_color[2] + factor * (end_color[2] - start_color[2]))
                a = round(start_color[3] + factor * (end_color[3] - start_color[3]))
                blended_r = round(r * (a / 255) + background[0] * (1 - a / 255))
                blended_g = round(g * (a / 255) + background[1] * (1 - a / 255))
                blended_b = round(b * (a / 255) + background[2] * (1 - a / 255))
                draw.line([(x, 0), (x, height)], (blended_r, blended_g, blended_b, a))
        return gradient
    
    @staticmethod
    def parse_color(color_input):
        if color_input.startswith("#"):
            color_input = color_input.lstrip("#")
            if len(color_input) == 6:
                r, g, b = int(color_input[0:2], 16), int(color_input[2:4], 16), int(color_input[4:6], 16)
                return r, g, b, 255
            elif len(color_input) == 8:
                r, g, b = int(color_input[0:2], 16), int(color_input[2:4], 16), int(color_input[4:6], 16)
                a = int(color_input[6:8], 16)
                return r, g, b, a
        else:
            raise ValueError(f"Invalid color format: {color_input}")

    @staticmethod
    def hsl_to_rgb(h, s, l):
        s /= 100
        l /= 100
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = l - c / 2

        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        r = round((r + m) * 255)
        g = round((g + m) * 255)
        b = round((b + m) * 255)
        return r, g, b
    
    @staticmethod
    def hsv_to_rgb(h, s, v):
        s /= 100
        v /= 100
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c

        if 0 <= h < 60:
            r, g, b = c, x, 0
        elif 60 <= h < 120:
            r, g, b = x, c, 0
        elif 120 <= h < 180:
            r, g, b = 0, c, x
        elif 180 <= h < 240:
            r, g, b = 0, x, c
        elif 240 <= h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        r = round((r + m) * 255)
        g = round((g + m) * 255)
        b = round((b + m) * 255)
        return r, g, b
    
    @staticmethod
    def cmyk_to_rgb(c, m, y, k):
        r = round((1 - c / 100) * (1 - k / 100) * 255)
        g = round((1 - m / 100) * (1 - k / 100) * 255)
        b = round((1 - y / 100) * (1 - k / 100) * 255)
        return r, g, b

    @staticmethod
    def hex_to_rgba(hex_color: str):
        hex_color = hex_color.lstrip("#")
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return r, g, b, 1.0
    
    @staticmethod
    def rgba_to_cmyk(r: int, g: int, b: int, a: float):
        if (r, g, b) == (0, 0, 0):
            return 0, 0, 0, 100
        c = 1 - r / 255
        m = 1 - g / 255
        y = 1 - b / 255
        k = min(c, m, y)
        c = (c - k) / (1 - k)
        m = (m - k) / (1 - k)
        y = (y - k) / (1 - k)
        return round(c * 100), round(m * 100), round(y * 100), round(k * 100)
    
    @staticmethod
    def rgba_to_hsl(r: int, g: int, b: int, a: float):
        r, g, b = r / 255, g / 255, b / 255
        max_val, min_val = max(r, g, b), min(r, g, b)
        l = (max_val + min_val) / 2
        if max_val == min_val:
            h = s = 0
        else:
            d = max_val - min_val
            s = d / (2 - max_val - min_val) if l > 0.5 else d / (max_val + min_val)
            if max_val == r:
                h = (g - b) / d + (6 if g < b else 0)
            elif max_val == g:
                h = (b - r) / d + 2
            elif max_val == b:
                h = (r - g) / d + 4
            h = fmod(h * 60, 360)
        return round(h), round(s * 100), round(l * 100), round(a * 100)
    
    @staticmethod
    def rgba_to_hsv(r: int, g: int, b: int, a: float):
        r, g, b = r / 255, g / 255, b / 255
        max_val, min_val = max(r, g, b), min(r, g, b)
        v = max_val
        d = max_val - min_val
        s = 0 if max_val == 0 else d / max_val
        if max_val == min_val:
            h = 0
        else:
            if max_val == r:
                h = (g - b) / d + (6 if g < b else 0)
            elif max_val == g:
                h = (b - r) / d + 2
            elif max_val == b:
                h = (r - g) / d + 4
            h = fmod(h * 60, 360)
        return round(h), round(s * 100), round(v * 100), round(a * 100)

    @commands.command(name="userinfo", aliases=["user", "member", "memberinfo"], description="Displays information about a user.")
    async def userinfo(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        roles = [role.mention for role in member.roles if role != ctx.guild.default_role]
        embed = discord.Embed(
            title=f"User Info - {member}",
            color=member.color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url if member.avatar else member.default_avatar)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Name", value=str(member), inline=True)
        embed.add_field(name="Created At", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.add_field(name="Roles", value=", ".join(roles) if roles else "None", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="serverinfo", aliases=["server", "guild", "guildinfo"], description="Displays information about the server.")
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        embed = discord.Embed(
            title=f"Server Info - {guild.name}",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
        embed.add_field(name="ID", value=guild.id, inline=True)
        embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="Created At", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.add_field(name="Members", value=f"{guild.member_count} members", inline=True)
        embed.add_field(name="Channels", value=f"{len(guild.channels)} total", inline=True)
        embed.add_field(name="Roles", value=f"{len(guild.roles)} roles", inline=True)
        embed.add_field(name="Boosts", value=f"{guild.premium_subscription_count} boosts", inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="channelinfo", aliases=["channel"], description="Displays information about a text channel.")
    async def channelinfo(self, ctx: commands.Context, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        embed = discord.Embed(
            title=f"Channel Info - {channel.name}",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="ID", value=channel.id, inline=True)
        embed.add_field(name="Name", value=channel.name, inline=True)
        embed.add_field(name="Type", value=str(channel.type).capitalize(), inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "None", inline=True)
        embed.add_field(name="Topic", value=channel.topic if channel.topic else "No topic", inline=False)
        embed.add_field(name="Created At", value=channel.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="voiceinfo", description="Displays information about a voice channel.")
    async def voiceinfo(self, ctx: commands.Context, channel: discord.VoiceChannel = None):
        channel = channel or ctx.author.voice.channel
        embed = discord.Embed(
            title=f"Voice Channel Info - {channel.name}",
            color=discord.Color.green(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="ID", value=channel.id, inline=True)
        embed.add_field(name="Name", value=channel.name, inline=True)
        embed.add_field(name="Category", value=channel.category.name if channel.category else "None", inline=True)
        embed.add_field(name="Bitrate", value=f"{channel.bitrate // 1000} kbps", inline=True)
        embed.add_field(name="User Limit", value=channel.user_limit or "Unlimited", inline=True)
        embed.add_field(name="Connected Members", value=", ".join([member.mention for member in channel.members]) or "None", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="threadinfo", aliases=["thread"], description="Displays information about a text channel's thread.")
    async def threadinfo(self, ctx: commands.Context, thread: discord.Thread):
        embed = discord.Embed(
            title=f"Thread Info - {thread.name}",
            color=discord.Color.purple(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="ID", value=thread.id, inline=True)
        embed.add_field(name="Owner", value=thread.owner.mention if thread.owner else "Unknown", inline=True)
        embed.add_field(name="Participants", value=", ".join([member.mention for member in thread.members]) or "None", inline=False)
        embed.add_field(name="Message Count", value=thread.message_count, inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="messageinfo", description="Displays information about a message.")
    async def messageinfo(self, ctx: commands.Context, message: discord.Message):
        embed = discord.Embed(
            title=f"Message Info - {message.id}",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="ID", value=message.id, inline=True)
        embed.add_field(name="Author", value=message.author.mention, inline=True)
        embed.add_field(name="Channel", value=message.channel.mention, inline=True)
        embed.add_field(name="Content", value=message.content or "None", inline=False)
        embed.add_field(name="Created At", value=message.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="emojiinfo", aliases=["emoji"], description="Displays information about an emoji.")
    async def emojiinfo(self, ctx: commands.Context, emoji: discord.Emoji):
        embed = discord.Embed(
            title=f"Emoji Info - {emoji.name}",
            color=discord.Color.dark_orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="ID", value=emoji.id, inline=True)
        embed.add_field(name="Type", value="Animated" if emoji.animated else "Static", inline=True)
        embed.add_field(name="Created At", value=emoji.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.add_field(name="Guild", value=emoji.guild.name if emoji.guild else "None", inline=False)
        embed.set_thumbnail(url=emoji.url)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="stickerinfo", aliases=["sticker"], description="Displays information about a sticker.")
    async def stickerinfo(self, ctx: commands.Context, sticker: discord.GuildSticker):
        embed = discord.Embed(
            title=f"Sticker Info - {sticker.name}",
            color=discord.Color.dark_green(),
            timestamp=discord.utils.utcnow()
        )

        embed.add_field(name="ID", value=sticker.id, inline=True)  
        embed.add_field(name="Guild", value=sticker.guild.name if sticker.guild else "None", inline=True)

        if sticker.description:
            embed.add_field(name="Description", value=sticker.description, inline=False)

        embed.set_image(url=sticker.url)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=embed)
    
    @commands.command(name="inviteinfo", description="Displays information about an invite code.")
    async def inviteinfo(self, ctx: commands.Context, invite: discord.Invite):
        embed = discord.Embed(
            title=f"Invite Info - {invite.code}",
            color=discord.Color.dark_purple(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Guild", value=invite.guild.name if invite.guild else "None", inline=True)
        embed.add_field(name="Channel", value=invite.channel.name, inline=True)
        embed.add_field(name="Uses", value=f"{invite.uses}/{invite.max_uses}" if invite.max_uses else "Unlimited", inline=True)
        embed.add_field(name="Expires At", value=invite.expires_at.strftime("%Y-%m-%d %H:%M:%S") if invite.expires_at else "Never", inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="permissions", aliases=["perms"], description="Displays a user's permissions in a channel.")
    async def permissions(self, ctx: commands.Context, member: discord.Member = None, channel: discord.TextChannel = None):
        member = member or ctx.author
        channel = channel or ctx.channel
        perms = channel.permissions_for(member)
        permissions = [perm.replace("_", " ").title() for perm, value in perms if value]
        embed = discord.Embed(
            title=f"Permissions Info - {member} in {channel.name}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Permissions", value=", ".join(permissions) or "None", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.command(name="roleinfo", aliases=["role"], description="Displays information about a role.")
    async def roleinfo(self, ctx: commands.Context, role: discord.Role):
        embed = discord.Embed(
            title=f"Role Info - {role.name}",
            color=role.color,
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="ID", value=role.id, inline=True)
        embed.add_field(name="Name", value=role.name, inline=True)
        embed.add_field(name="Color", value=str(role.color), inline=True)
        embed.add_field(name="Mentionable", value="Yes" if role.mentionable else "No", inline=True)
        embed.add_field(name="Created At", value=role.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=True)
        embed.add_field(name="Permissions", value=", ".join(perm[0].replace('_', ' ').title() for perm in role.permissions if perm[1]) or "None", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="baninfo", description="Displays information about a banned user.")
    @commands.has_permissions(ban_members=True)
    async def baninfo(self, ctx: commands.Context, user: discord.User):
        ban_entry = await ctx.guild.fetch_ban(user)
        embed = discord.Embed(
            title=f"Ban Info - {user}",
            color=discord.Color.dark_red(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="Reason", value=ban_entry.reason or "None", inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="botinfo", description="Displays information about the bot.")
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def botinfo(self, ctx: commands.Context):
        embed = discord.Embed(
            title=f"Bot Info - {self.bot.user.name}",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="ID", value=self.bot.user.id, inline=True)
        embed.add_field(name="Servers", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Users", value=len(set(self.bot.get_all_members())), inline=True)
        embed.add_field(name="Developers", value="[nkrasn](https://github.com/nkrasn 'Original Developer.'), [MiniatureEge2006](https://github.com/MiniatureEge2006 'Current Developer.')", inline=True)
        embed.add_field(name="Source Code", value="https://github.com/MiniatureEge2006/g_man-revived", inline=True)
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
    
    @commands.hybrid_command(name="weatherinfo", description="Displays information about the weather in a location.", aliases=["weather"])
    @app_commands.describe(location="The location for which you want to know the weather.")
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def weatherinfo(self, ctx: commands.Context, *, location: str):
        if ctx.interaction:
            await ctx.defer()
        else:
            await ctx.typing()
        api_key = bot_info.data['openweather_api_key']
        base_url = "https://api.openweathermap.org/data/2.5/weather"
        params = {"q": location, "appid": api_key, "units": "metric"}

        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    city = data["name"]
                    country = data["sys"]["country"]
                    temperature = data["main"]["temp"]
                    feels_like = data["main"]["feels_like"]
                    humidity = data["main"]["humidity"]
                    pressure = data["main"]["pressure"]
                    wind_speed = data["wind"]["speed"]
                    wind_direction = data["wind"]["deg"]
                    coordinates_lat = data["coord"]["lat"]
                    coordinates_lon = data["coord"]["lon"]
                    visibility = data["visibility"] / 1000
                    weather_description = data["weather"][0]["description"].capitalize()
                    icon = data["weather"][0]["icon"]
                    icon_url = f"http://openweathermap.org/img/w/{icon}.png"
                    sunrise = datetime.fromtimestamp(data["sys"]["sunrise"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                    sunset = datetime.fromtimestamp(data["sys"]["sunset"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

                    embed = discord.Embed(
                        title=f"Weather Info - {city}, {country}",
                        description=f"**{weather_description}**\nSunrise: {sunrise}\nSunset: {sunset}",
                        color=discord.Color.light_gray()
                    )
                    embed.add_field(name="Temperature", value=f"{temperature}°C (feels like {feels_like}°C)", inline=True)
                    embed.add_field(name="Humidity", value=f"{humidity}%", inline=True)
                    embed.add_field(name="Pressure", value=f"{pressure} hPa", inline=True)
                    embed.add_field(name="Wind", value=f"{wind_speed} m/s at {wind_direction}°", inline=True)
                    embed.add_field(name="Visibility", value=f"{visibility} km", inline=True)
                    embed.add_field(name="Coordinates", value=f"{coordinates_lat}, {coordinates_lon}", inline=True)
                    embed.set_thumbnail(url=icon_url)
                    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("Could not find weather data for the specified location.")
    
    @commands.hybrid_command(name="colorinfo", description="Displays information about a color.", aliases=["color"])
    @app_commands.describe(color="The color name or color code (HEX, RGB/A, HSL/A, HSV/A or CMYK)")
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def colorinfo(self, ctx: commands.Context, color: str):
        if ctx.interaction:
            await ctx.defer()
        else:
            await ctx.typing()
        try:
            if color.startswith("#"):
                hex_color = color
                r, g, b, a = self.hex_to_rgba(hex_color)
            elif color.lower().startswith("rgba("):
                rgba_values = list(map(float, re.findall(r"\d+\.?\d*", color)))
                r, g, b, a = rgba_values
                hex_color = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
            elif color.lower().startswith("rgb("):
                rgb_values = list(map(int, re.findall(r"\d+", color)))
                r, g, b = rgb_values
                a = 1.0
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
            elif color.lower().startswith("hsla("):
                hsla_values = list(map(float, re.findall(r"\d+\.?\d*", color)))
                h, s, l, a = hsla_values
                r, g, b = self.hsl_to_rgb(h, s, l)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
            elif color.lower().startswith("hsl("):
                hsl_values = list(map(float, re.findall(r"\d+\.?\d*", color)))
                h, s, l = hsl_values
                a = 1.0
                r, g, b = self.hsl_to_rgb(h, s, l)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
            elif color.lower().startswith("hsva("):
                hsva_values = list(map(float, re.findall(r"\d+\.?\d*", color)))
                h, s, v, a = hsva_values
                r, g, b = self.hsv_to_rgb(h, s, v)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
            elif color.lower().startswith("hsv("):
                hsv_values = list(map(float, re.findall(r"\d+\.?\d*", color)))
                h, s, v = hsv_values
                a = 1.0
                r, g, b = self.hsv_to_rgb(h, s, v)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
            elif color.lower().startswith("cmyka("):
                cmyka_values = list(map(float, re.findall(r"\d+\.?\d*", color)))
                c, m, y, k, a = cmyka_values
                r, g, b = self.cmyk_to_rgb(c, m, y, k)
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
            elif color.lower().startswith("cmyk("):
                cmyk_values = list(map(float, re.findall(r"\d+\.?\d*", color)))
                c, m, y, k = cmyk_values
                r, g, b = self.cmyk_to_rgb(c, m, y, k)
                a = 1.0
                hex_color = f"#{r:02x}{g:02x}{b:02x}"
            else:
                hex_color = name_to_hex(color)
                r, g, b, a = self.hex_to_rgba(hex_color)
            
            cmyk = self.rgba_to_cmyk(r, g, b, a)
            hsl = self.rgba_to_hsl(r, g, b, a)
            hsv = self.rgba_to_hsv(r, g, b, a)
            closest_name = None
            try:
                closest_name = hex_to_name(hex_color)
            except ValueError:
                closest_name = "Unknown"
            
            img = Image.new("RGBA", (100, 100), (int(r), int(g), int(b), int(a * 255)))
            buffer = io.BytesIO()
            img.save(buffer, "PNG")
            buffer.seek(0)

            embed = discord.Embed(
                title=f"Color Info - {closest_name.capitalize()}",
                description=f"Details for the color `{color}`",
                color=int(hex_color.lstrip("#"), 16)
            )
            embed.add_field(name="HEX", value=hex_color.upper(), inline=True)
            embed.add_field(name="RGB/A", value=f"({r}, {g}, {b}, {a:.2f})", inline=True)
            embed.add_field(name="CMYK", value=f"{cmyk[0]}%, {cmyk[1]}%, {cmyk[2]}%, {cmyk[3]}%", inline=True)
            embed.add_field(name="HSL/A", value=f"{hsl[0]}°, {hsl[1]}%, {hsl[2]}%, {hsl[3]}%", inline=True)
            embed.add_field(name="HSV/A", value=f"{hsv[0]}°, {hsv[1]}%, {hsv[2]}%, {hsv[3]}%", inline=True)
            embed.set_thumbnail(url="attachment://color.png")
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed, file=discord.File(buffer, "color.png"))
        except Exception as e:
            await ctx.send(f"Invalid color format. Please provide a valid color name or color code (HEX, RGB/A, HSL/A, HSV/A or CMYK).\nError: {e}")
    
    @commands.hybrid_command(name="gradientinfo", description="Displays information about a gradient.", aliases=["gradient"])
    @app_commands.describe(colors="Comma-separated list of colors in HEX format with optional positions (e.g., '#FF0000 0%, #00FF00 50%, #0000FF 100%')")
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def gradientinfo(self, ctx: commands.Context, *, colors: str):
        if ctx.interaction:
            await ctx.defer()
        else:
            await ctx.typing()
        try:
            colors, positions = self.parse_gradient_input(colors)
            if len(colors) > 10:
                await ctx.send("You can only create a gradient with up to 10 colors.")
                return
            gradient = self.generate_gradient_image(colors, positions)
            buffer = io.BytesIO()
            gradient.save(buffer, "PNG")
            buffer.seek(0)

            embed = discord.Embed(
                title="Gradient Info",
                description="Details for the gradient",
                color=discord.Color.light_gray()
            )
            embed.add_field(name="Colors", value="\n".join(colors), inline=True)
            embed.add_field(name="Positions", value="\n".join(f"{pos}%" for pos in positions), inline=True)
            embed.set_image(url="attachment://gradient.png")
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed, file=discord.File(buffer, "gradient.png"))
        except Exception as e:
            await ctx.send(f"Invalid color format. Please provide a valid HEX/A color code.\nError: {e}")



async def setup(bot):
    await bot.add_cog(Info(bot))
