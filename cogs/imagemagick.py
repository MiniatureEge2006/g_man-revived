import discord
from discord import app_commands
from discord.ext import commands
import os
import time
import subprocess
import shlex
import aiohttp
from urllib.parse import urlparse
from pathlib import Path

class ImageMagick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.hybrid_command(name="imagemagick", description="Use ImageMagick as if its a CLI!", aliases=["magick"])
    @app_commands.describe(args="ImageMagick arguments.")
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def imagemagick(self, ctx: commands.Context, *, args: str):
        if ctx.interaction:
            await ctx.defer()
        else:
            await ctx.typing()
        

        try:
            start_time = time.time()

            processing_dir = 'vids'

            split_args = shlex.split(args)

            if len(split_args) < 2:
                await ctx.send("You must provide at least an input file and an output file.")
                return
            input_file = split_args[0]
            output_file = split_args[-1]

            if is_valid_url(input_file):
                filename = get_filename(input_file)
                async with aiohttp.ClientSession() as session:
                    async with session.get(input_file) as resp:
                        if resp.status == 200:
                            local_input_file = os.path.join(processing_dir, filename)
                            with open(local_input_file, 'wb') as f:
                                f.write(await resp.read())
                            split_args[0] = local_input_file
                        else:
                            await ctx.send("Failed to download the input image.")
                            return
            
            cmd = ["magick"] + split_args

            print("Executing ImageMagick command:", " ".join(cmd))

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                error_message = result.stderr
                await ctx.send(f"ImageMagick failed: ```{error_message}```")
                return
            
            if os.path.exists(output_file):
                elapsed_time = time.time() - start_time
                await ctx.send(f"-# ImageMagick completed in {elapsed_time:.2f} seconds.", file=discord.File(output_file))
                os.remove(output_file)
            else:
                await ctx.send("ImageMagick completed, but no output file was created.")
            
            if "local_input_file" in locals() and os.path.exists(local_input_file):
                os.remove(local_input_file)
        
        except Exception as e:
            await ctx.send(f"An error occurred: `{e}`")


def is_valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return bool(parsed.scheme and parsed.netloc)

def get_filename(url: str) -> str:
    parsed_url = urlparse(url)
    filename = Path(parsed_url.path).name
    return filename


async def setup(bot):
    await bot.add_cog(ImageMagick(bot))