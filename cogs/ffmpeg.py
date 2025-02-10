import discord
from discord.ext import commands
from discord import app_commands
import time
import os
import aiohttp
import shlex
from urllib.parse import urlparse
from pathlib import Path
import asyncio


class FFmpeg(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    

    @commands.hybrid_command(name="ffmpeg", description="Use FFmpeg as if its a CLI!")
    @app_commands.describe(args="FFmpeg arguments.")
    @app_commands.user_install()
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ffmpeg_command(self, ctx: commands.Context, *, args: str):
        
        await ctx.typing()

        try:
            start_time = time.time()

            processing_dir = 'vids'
            
            input_files = []

            
            
            split_args = shlex.split(args)
            for idx, arg in enumerate(split_args):
                if arg == "-i" and idx + 1 < len(split_args):
                    input_url = split_args[idx + 1]
                    if self.is_valid_url(input_url):
                        filename = self.get_filename(input_url)
                        file_path = os.path.join(processing_dir, filename)
                        file_downloaded = await self.download_file(input_url, file_path)
                        if file_downloaded:
                            input_files.append(file_path)
                            split_args[idx + 1] = file_path
                        else:
                            await ctx.send(f"Failed to download the media from `{input_url}`")
                            return
            filter_options = ["-filter_complex", "-vf", "-af"]
            for option in filter_options:
                if option in split_args:
                    idx = split_args.index(option)
                    if idx + 1 < len(split_args):
                        filter_value = split_args[idx + 1]
                        if filter_value.startswith('"') and filter_value.endswith('"'):
                            split_args[idx + 1] = filter_value[1:-1]
            
            cmd = ["ffmpeg"] + split_args

            

            process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            
            output_task = asyncio.create_task(self.read_output(process.stdout))
            error_task = asyncio.create_task(self.read_stderr(process.stderr))


            await asyncio.gather(output_task, error_task)
            await process.wait()

            output = await output_task
            error_output = await error_task

            if process.returncode != 0:
                error_message = error_output
                if len(error_message) > 2000:
                    error_file_path = os.path.join(processing_dir, "ffmpeg_error.txt")
                    with open(error_file_path, 'w') as f:
                        f.write(error_message)
                    await ctx.send("FFmpeg encountered an error.", file=discord.File(error_file_path))
                    os.remove(error_file_path)
                else:
                    await ctx.send(f"FFmpeg encountered an error: ```{error_message}```")
                return


            output_file = [arg for arg in split_args if not arg.startswith("-")][-1]
            if os.path.exists(output_file):
                elapsed_time = time.time() - start_time
                await ctx.send(f"-# FFmpeg processing completed in {elapsed_time:.2f} seconds.", file=discord.File(output_file))
                os.remove(output_file)
            else:
                await ctx.send("FFmpeg processing completed, but the output file could not be found.")
            
            for file in input_files:
                os.remove(file)

        except Exception as e:
            raise commands.CommandError(f"An error occurred: `{e}`")


    async def read_output(self, stream):
            output = []
            while True:
                chunk = await stream.read(4096)
                if not chunk:
                    break
                decoded_chunk = chunk.decode('utf-8', errors='ignore').strip()
                print(decoded_chunk)
                output.append(decoded_chunk)
            return '\n'.join(output)
    
    async def read_stderr(self, stream):
            error_output = []
            while True:
                chunk = await stream.read(4096)
                if not chunk:
                    break
                decoded_chunk = chunk.decode('utf-8', errors='ignore').strip()
                print(decoded_chunk)
                error_output.append(decoded_chunk)
            return '\n'.join(error_output)

    async def download_file(self, url: str, file_path: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        with open(file_path, 'wb') as f:
                            f.write(await resp.read())
                        return True
                    else:
                        return False
        except Exception as e:
            print(f"Error downloading the media from {url}: {e}")
            return False

    def is_valid_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)

    def get_filename(self, url: str) -> str:
        parsed_url = urlparse(url)
        filename = Path(parsed_url.path).name
        return filename

async def setup(bot):
    await bot.add_cog(FFmpeg(bot))