from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from storage import load_json, save_json

CONFIG_FILE = "welcomer_config.json"


def get_config(guild_id: int) -> dict:
    data = load_json(CONFIG_FILE, {})
    return data.get(str(guild_id), {})


def set_config(guild_id: int, config: dict) -> None:
    data = load_json(CONFIG_FILE, {})
    data[str(guild_id)] = config
    save_json(CONFIG_FILE, data)


class Welcomer(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="welcomer-setup",
        description="Configure the welcome system for this server.",
    )
    @app_commands.describe(
        channel="Channel where welcome messages will be sent",
        message="Welcome message. Use {user}, {server}, {membercount}",
        image_url="Optional image URL for the welcome embed",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcomer_setup(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        message: str,
        image_url: str | None = None,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        config = {
            "channel_id": channel.id,
            "message": message,
            "image_url": image_url,
            "enabled": True,
        }
        set_config(interaction.guild.id, config)

        embed = discord.Embed(
            title="Welcomer configured",
            color=discord.Color.green(),
            description=f"Welcome messages will be sent to {channel.mention}.",
        )
        embed.add_field(name="Message", value=message[:1024], inline=False)
        if image_url:
            embed.set_image(url=image_url)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="welcomer-disable",
        description="Disable the welcome system for this server.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def welcomer_disable(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        config = get_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message(
                "Welcomer is not configured.", ephemeral=True
            )
            return

        config["enabled"] = False
        set_config(interaction.guild.id, config)
        await interaction.response.send_message(
            "Welcomer disabled.", ephemeral=True
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return

        config = get_config(member.guild.id)
        if not config or not config.get("enabled"):
            return

        channel_id = config.get("channel_id")
        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        raw = config.get("message", "Welcome {user} to {server}!")
        text = (
            raw.replace("{user}", member.mention)
            .replace("{server}", member.guild.name)
            .replace("{membercount}", str(member.guild.member_count))
        )

        embed = discord.Embed(
            description=text,
            color=discord.Color.blurple(),
        )
        embed.set_author(
            name=str(member),
            icon_url=member.display_avatar.url,
        )
        embed.set_thumbnail(url=member.display_avatar.url)

        image_url = config.get("image_url")
        if image_url:
            embed.set_image(url=image_url)

        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Welcomer(bot))
