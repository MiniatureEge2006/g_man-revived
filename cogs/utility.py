import asyncio
from genericpath import isfile
import discord
from discord.ext import commands
from discord import app_commands
import database as db
import ffmpeg
import filter_helper
import media_cache
import os
import re
import requests
import subprocess
import video_creator

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    async def _download(self, ctx, vstream, astream, kwargs):
        return vstream, astream, {}
    @commands.command()
    async def download(self, ctx):
        await video_creator.apply_filters_and_send(ctx, self._download, {})
    @commands.command()
    async def fix(self, ctx):
        await self.download(ctx)
    @commands.command()
    async def dl(self, ctx):
        await self.download(ctx)

    async def _gif(self, ctx, vstream, astream, kwargs):
        fps = kwargs['fps']
        vstream = vstream.filter('fps', fps=fps).split()
        palette = vstream[1].filter('palettegen')
        vstream = ffmpeg.filter([vstream[0], palette], 'paletteuse')
        return vstream, astream, {}
    @commands.command()
    async def gif(self, ctx, fps : int = 24):
        fps = max(1, min(fps, 24))
        await video_creator.apply_filters_and_send(ctx, self._gif, {'is_gif':True, 'fps':fps})

    @commands.command()
    async def vid2img(self, ctx):
        await video_creator.set_progress_bar(ctx.message, 0)
        input_filepath = media_cache.get_from_cache(str(ctx.message.channel.id))[-1]
        output_filename = 'vids/discord-' + str(ctx.message.id) + '.png'
        await video_creator.set_progress_bar(ctx.message, 1)

        await video_creator.set_progress_bar(ctx.message, 2)
        subprocess.run([
            'ffmpeg',
            '-i', f'{input_filepath}',
            '-frames:v', '1',
            output_filename
        ])
        await video_creator.set_progress_bar(ctx.message, 3)
        if(os.path.isfile(output_filename)):
            await ctx.send(file=discord.File(output_filename))
            os.remove(output_filename)
        else:
            await ctx.send(f'There was an error converting the video (`{input_filepath}`) to an image.')
        await ctx.message.clear_reactions()

    # TODO: make this automatic in video_creator.py
    @commands.command()
    async def img2vid(self, ctx):
        await video_creator.set_progress_bar(ctx.message, 0)
        input_filepath = media_cache.get_from_cache(str(ctx.message.channel.id))[-1]
        output_filename = 'vids/discord-' + str(ctx.message.id) + '.mp4'
        await video_creator.set_progress_bar(ctx.message, 1)

        await video_creator.set_progress_bar(ctx.message, 2)
        subprocess.run([
            'ffmpeg',
            '-loop', '1',
            '-i', f'{input_filepath}',
            '-t', '1',
            output_filename
        ])
        await video_creator.set_progress_bar(ctx.message, 3)
        if(os.path.isfile(output_filename)):
            await ctx.send(file=discord.File(output_filename))
            os.remove(output_filename)
        else:
            await ctx.send(f'There was an error converting the image (`{input_filepath}`) to a video.')
        await ctx.message.clear_reactions()


    @commands.command()
    async def link(self, ctx):
        vid_link = media_cache.get_from_cache(str(ctx.message.channel.id))[0]
        await ctx.send(f'`{vid_link}`')


    
    async def _mp3(self, ctx, vstream, astream, kwargs):
        return (vstream, astream, {})
    @commands.command()
    async def mp3(self, ctx):
        await video_creator.apply_filters_and_send(ctx, self._mp3, {'is_mp3':True})
    

    @commands.command()
    async def swap(self, ctx):
        channel_id = str(ctx.channel.id)
        vids = list(db.vids.find({'channel':channel_id}).sort('_id', -1).limit(2))
        if(len(vids) < 2):
            await ctx.send("I don't see two videos to swap.")
            return
        new_vid, old_vid = vids

        await ctx.send(old_vid['url'])
        old_vid_msg = await ctx.fetch_message(int(old_vid['message_id']))
        
    
    async def _timestamp(self, ctx, vstream, astream, kwargs):
        speed_change = kwargs['speed_change']
        vstream = (
            vstream
            .filter('fps', fps=100)
            .filter('scale', w=480, h=-2)
            .drawtext(
                text="%{pts}",
                #x="main_w/2 - tw/2", y="main_h/2 - th/2",
                x="15", y="main_h - th*2 - 35",
                fontsize=40, fontcolor="white", fontfile="fonts/arial.ttf", borderw=2, bordercolor="black",
                escape_text=False
            )
        )
        if(speed_change != 1.0):
            vstream, astream = filter_helper.apply_speed(vstream, astream, speed_change)
        return vstream, astream, {}
    @commands.command()
    async def timestamp(self, ctx, speed_change : float = 1.0):
        await video_creator.apply_filters_and_send(ctx, self._timestamp, {'is_ignored_mp4':True, 'speed_change':speed_change})
    @commands.command()
    async def time(self, ctx, speed_change : float = 1.0):
        await self.timestamp(ctx, speed_change)

    
    @commands.command()
    async def undo(self, ctx):
        # Limiting to 2 so that you don't undo/delete the last video gman can use
        vid_msg_id = list(db.vids.find({'channel':str(ctx.channel.id)}).sort('_id', -1).limit(2))
        #await ctx.send(vid_msg_id)
        if(len(vid_msg_id) <= 1):
            await ctx.send("Out of undos!")
            return
        vid_msg_id = vid_msg_id[0]['message_id']
        
        vid_to_undo = await ctx.fetch_message(int(vid_msg_id))
        await vid_to_undo.delete()
        await ctx.message.delete()
        db.vids.delete_one({'message_id': vid_msg_id})
    


async def setup(bot):
    await bot.add_cog(Utility(bot))
