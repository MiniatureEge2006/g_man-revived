import discord
from discord import app_commands
from discord.ext import commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.color = discord.Color.og_blurple()
    

    @commands.hybrid_command(name="help", description="Get a list of my commands.", aliases=["h", "commands", "c", "cmds", "pleasehelpme"])
    @app_commands.describe(command_or_category="The command or category in which you want to see.")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def help(self, ctx: commands.Context, *, command_or_category: str = None):
        if command_or_category is None:
            embed = self.get_general_help(ctx)
        else:
            embed = self.get_detailed_help(ctx, command_or_category)
        
        await ctx.send(embed=embed)

    def get_general_help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Help - Command Categories",
            description=f"Use `{ctx.prefix}help <command>` or `{ctx.prefix}help <category>` for more details.",
            color=self.color
        )

        for cog_name, cog in self.bot.cogs.items():
            commands_list = [cmd.name for cmd in cog.get_commands() if not cmd.hidden]
            if commands_list:
                embed.add_field(
                    name=f"**{cog_name}**",
                    value=", ".join(f"`{cmd}`" for cmd in commands_list),
                    inline=False
                )
        
        uncategorized = [cmd.name for cmd in self.bot.commands if cmd.cog is None and not cmd.hidden]
        if uncategorized:
            embed.add_field(
                name="**Uncategorized**",
                value=", ".join(f"`{cmd}`" for cmd in uncategorized),
                inline=False
            )
        
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        return embed
    
    def get_detailed_help(self, ctx: commands.Context, query):
        cog = self.bot.get_cog(query)
        if cog:
            return self.get_cog_help(ctx, cog)
        
        cmd = self.bot.get_command(query)
        if cmd:
            return self.get_command_help(ctx, cmd)
        
        embed = discord.Embed(
            title="Error",
            description=f"No command or category found for `{query}`",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        return embed
    
    def get_cog_help(self, ctx: commands.Context, cog):
        embed = discord.Embed(
            title=f"Category: {cog.qualified_name}",
            description=cog.description or "No description available.",
            color=self.color
        )

        def recursively_add_commands(cmds, level=0):
            fields = []
            for cmd in cmds:
                if cmd.hidden:
                    continue
                indent = '  ' * level
                name = f"{indent}- `{cmd.name}`"
                value = cmd.description or "No description available."
                fields.append((name, value))
                if isinstance(cmd, commands.Group):
                    fields.extend(recursively_add_commands(cmd.commands, level + 1))
            return fields

        all_fields = recursively_add_commands(cog.get_commands())

        if all_fields:
            for name, value in all_fields:
                embed.add_field(name=name, value=value, inline=False)
        else:
            embed.add_field(name="Commands", value="No commands found.", inline=False)

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        return embed
    
    def get_command_help(self, ctx: commands.Context, cmd):
        embed = discord.Embed(
            title=f"Command: {cmd.name}",
            color=self.color
        )
        embed.add_field(name="Description", value=cmd.description or "No description available.", inline=False)

        aliases = ", ".join(f"`{alias}`" for alias in cmd.aliases) if cmd.aliases else "None"
        embed.add_field(name="Aliases", value=aliases, inline=False)
        embed.add_field(
            name="Usage",
            value=f"`{ctx.prefix}{cmd.qualified_name} {cmd.signature}`",
            inline=False
        )

        if isinstance(cmd, commands.HybridCommand):
            app_cmd: app_commands.Command = cmd.app_command

            if app_cmd.parameters:
                param_lines = []
                for param in app_cmd.parameters:
                    desc = param.description or "No description"
                    required = "required" if param.required else "optional"
                    param_type = param.type.name if hasattr(param.type, "name") else str(param.type)
                    param_lines.append(f"**{param.name}** ({param_type}, {required}): {desc}")

                embed.add_field(
                    name="Slash Command Parameters",
                    value="\n".join(param_lines),
                    inline=False
                )
            else:
                embed.add_field(
                    name="Slash Command Parameters",
                    value="This command has no parameters.",
                    inline=False
                )


        if isinstance(cmd, commands.Group):
            subcommands = [c for c in cmd.commands if not c.hidden]
            if subcommands:
                sub_list = "\n".join([
                    f"`{sub.name}` - {sub.description or 'No description'}"
                    for sub in subcommands
                ])
                embed.add_field(
                    name="Subcommands",
                    value=sub_list,
                    inline=False
                )
            else:
                embed.add_field(
                    name="Subcommands",
                    value="This group has no visible subcommands.",
                    inline=False
                )

        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        return embed


async def setup(bot):
    await bot.add_cog(Help(bot))