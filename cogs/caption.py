import discord
from discord import app_commands
from discord.ext import commands
import os
import aiohttp
from urllib.parse import urlparse
import asyncio

DEFAULTS = {
    "font": "Futura Condensed Extra Bold.otf",
    "font_color": "#000000",
    "font_size": 24,
    "padding_color": "#FFFFFF",
    "padding_size": 24,
    "border_width": 0,
    "border_color": "#000000",
    "position": "center"
}


class Caption(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def download_file(self, url: str, save_path: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(save_path, 'wb') as f:
                        f.write(await resp.read())
                else:
                    raise ValueError("Failed to download the file.")
    
    def construct_filter_graph(self, text: str, font: str, font_color: str, font_size: int, padding_color: str, padding_size: int, border_width: int, border_color: str, position: str = "center"):
        horizontal, vertical = "center", "center"
        if position in {"top", "bottom", "center", "left", "right"}:
            vertical = position
        elif "," in position:
            try:
                horizontal, vertical = position.split(",")
            except ValueError:
                raise ValueError("Invalid position format. Use 'left,top', 'center,center', etc.")
        
        if vertical == "top":
            y = "0"
        elif vertical == "center":
            y = f"{padding_size}/2-(th/2)"
        elif vertical == "bottom":
            y = f"{padding_size}-th"
        else:
            raise ValueError("Invalid vertical position: must be 'top', 'center', or 'bottom'.")
        
        if horizontal == "left":
            x = "0"
        elif horizontal == "center":
            x = "(w-tw)/2"
        elif horizontal == "right":
            x = "w-tw"
        else:
            raise ValueError("Invalid horizontal position: must be 'left', 'center', or 'right'.")
        
        pad_filter = f"pad=width=iw:height=ih+{padding_size}:x=0:y={padding_size}:color={padding_color}"
        drawtext_filter = f"drawtext=text='{text}':fontfile=fonts/{font}:fontcolor={font_color}:fontsize={font_size}:x={x}:y={y}:borderw={border_width}:bordercolor={border_color}"

        return f"{pad_filter},{drawtext_filter}"
    
    async def apply_caption(self, input_path: str, output_path: str, filter_graph: str):
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-vf", filter_graph,
            output_path
        ]
        result = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await result.communicate()
        if result.returncode != 0:
            raise ValueError(f"Failed to apply caption: {stderr}")
    
    @commands.hybrid_command(name="caption", description="Caption media.")
    @app_commands.describe(url="Input URL to caption.", text="Text to caption the media with.", font="The font to use. (Default Futura Condensed Extra Bold.otf)", font_color="The font color to use. (Default #000000)", font_size="The font size to use. (Default 24)", padding_color="The padding color to use. (Default #FFFFFF)", padding_size="The padding size to use. (Default 24)", border_width="The border width to use. (Default 0)", border_color="The border color to use. (Default #000000)", position="The position to use. (Default center)")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def caption(self, ctx: commands.Context, url: str, text: str, font: str = DEFAULTS["font"], font_color: str = DEFAULTS["font_color"], font_size: int = DEFAULTS["font_size"], padding_color: str = DEFAULTS["padding_color"], padding_size: int = DEFAULTS["padding_size"], border_width: int = DEFAULTS["border_width"], border_color: str = DEFAULTS["border_color"], position: str = DEFAULTS["position"]):
        await ctx.typing()
        
        try:
            file_name = os.path.basename(urlparse(url).path)
            input_path = f"vids/{file_name}"
            output_path = f"vids/caption-{file_name}"

            await self.download_file(url, input_path)

            filter_graph = self.construct_filter_graph(
                text, font, font_color, font_size, padding_color, padding_size, border_width, border_color, position
            )

            await self.apply_caption(input_path, output_path, filter_graph)

            await ctx.send(file=discord.File(output_path))

        
        except Exception as e:
            error_message = str(e)
            if len(error_message) > 2000:
                with open("vids/error.txt", "w") as f:
                    f.write(error_message)
                await ctx.send("Error:", file=discord.File("vids/error.txt"))
                os.remove("vids/error.txt")
            else:
                await ctx.send(f"Error: {error_message}")

        finally:
            if os.path.exists(input_path):
                os.remove(input_path)
            if os.path.exists(output_path):
                os.remove(output_path)

async def setup(bot):
    await bot.add_cog(Caption(bot))