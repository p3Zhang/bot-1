import inspect
from pathlib import Path

from discord import Embed
from discord.ext import commands

from bot.bot import Bot
from bot.constants import URLs
from bot.converters import SourceConverter
from bot.exts.info.tags import TagIdentifier

SourceType = commands.HelpCommand | commands.Command | commands.Cog | TagIdentifier | commands.ExtensionNotLoaded


class BotSource(commands.Cog):
    """Displays information about the bot's source code."""

    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="source", aliases=("src",))
    async def source_command(
        self,
        ctx: commands.Context,
        *,
        source_item: SourceConverter = None,  # noqa: RUF013
    ) -> None:
        """Display information and a GitHub link to the source code of a command, tag, or cog."""
        if not source_item:
            embed = Embed(title="Bot's GitHub Repository")
            embed.add_field(name="Repository", value=f"[Go to GitHub]({URLs.github_bot_repo})")
            embed.set_thumbnail(url="https://avatars1.githubusercontent.com/u/9919")
            await ctx.send(embed=embed)
            return

        embed = await self.build_embed(source_item)
        await ctx.send(embed=embed)

    def get_source_link(self, source_item: SourceType) -> tuple[str, str, int | None]:
        """
        Build GitHub link of source item, return this link, file location and first line number.

        Raise BadArgument if `source_item` is a dynamically-created object (e.g. via internal eval).
        """
        if isinstance(source_item, commands.Command):
            source_item = inspect.unwrap(source_item.callback)
            src = source_item.__code__
            filename = src.co_filename
        elif isinstance(source_item, TagIdentifier):
            tags_cog = self.bot.get_cog("Tags")
            filename = tags_cog.tags[source_item].file_path
        else:
            src = type(source_item)
            try:
                filename = inspect.getsourcefile(src)
            except TypeError:
                raise commands.BadArgument("Cannot get source for a dynamically-created object.")

        if not isinstance(source_item, TagIdentifier):
            try:
                lines, first_line_no = inspect.getsourcelines(src)
            except OSError:
                raise commands.BadArgument("Cannot get source for a dynamically-created object.")

            lines_extension = f"#L{first_line_no}-L{first_line_no+len(lines)-1}"
        else:
            first_line_no = None
            lines_extension = ""

        # Handle tag file location differently than others to avoid errors in some cases
        if not first_line_no:
            file_location = Path(filename).relative_to("bot/")
        else:
            file_location = Path(filename).relative_to(Path.cwd()).as_posix()

        url = f"{URLs.github_bot_repo}/blob/main/{file_location}{lines_extension}"

        return url, file_location, first_line_no or None

    async def build_embed(self, source_object: SourceType) -> Embed | None:
        """Build embed based on source object."""
        url, location, first_line = self.get_source_link(source_object)

        if isinstance(source_object, commands.HelpCommand):
            title = "Help Command"
            description = source_object.__doc__.splitlines()[1]
        elif isinstance(source_object, commands.Command):
            description = source_object.short_doc
            title = f"Command: {source_object.qualified_name}"
        elif isinstance(source_object, TagIdentifier):
            title = f"Tag: {source_object}"
            description = ""
        else:
            title = f"Cog: {source_object.qualified_name}"
            description = source_object.description.splitlines()[0]

        embed = Embed(title=title, description=description)
        embed.add_field(name="Source Code", value=f"[Go to GitHub]({url})")
        line_text = f":{first_line}" if first_line else ""
        embed.set_footer(text=f"{location}{line_text}")

        return embed


async def setup(bot: Bot) -> None:
    """Load the BotSource cog."""
    await bot.add_cog(BotSource(bot))
