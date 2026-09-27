
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from storage import load_json, save_json

CONFIG_FILE = "autorole_config.json"
PENDING_FILE = "autorole_pending.json"

# Discord High verification level requires ~10 minutes membership.
DELAY_SECONDS = 10 * 60


def get_config(guild_id: int) -> dict:
    data = load_json(CONFIG_FILE, {})
    return data.get(str(guild_id), {})


def set_config(guild_id: int, config: dict) -> None:
    data = load_json(CONFIG_FILE, {})
    data[str(guild_id)] = config
    save_json(CONFIG_FILE, data)


def get_pending() -> dict:
    return load_json(PENDING_FILE, {})


def save_pending(data: dict) -> None:
    save_json(PENDING_FILE, data)


class AutoRoles(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._check_pending.start()

    def cog_unload(self) -> None:
        self._check_pending.cancel()

    @app_commands.command(
        name="autorole-setup",
        description="Configure auto-role granted after 10 minutes in the server.",
    )
    @app_commands.describe(
        role="Role to assign after 10 minutes of membership",
    )
    @app_commands.checks.has_permissions(manage_guild=True, manage_roles=True)
    async def autorole_setup(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
    ) -> None:
        if not interaction.guild or not interaction.user:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        me = interaction.guild.me
        if me is None or role >= me.top_role:
            await interaction.response.send_message(
                "I cannot assign that role (hierarchy).", ephemeral=True
            )
            return

        if role.managed:
            await interaction.response.send_message(
                "Cannot use a managed role (bot/integration).", ephemeral=True
            )
            return

        config = {
            "role_id": role.id,
            "enabled": True,
            "delay_seconds": DELAY_SECONDS,
        }
        set_config(interaction.guild.id, config)

        embed = discord.Embed(
            title="Auto-role configured",
            color=discord.Color.green(),
            description=(
                f"Members will receive {role.mention} after "
                f"**{DELAY_SECONDS // 60} minutes** in the server."
            ),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="autorole-disable",
        description="Disable the auto-role system for this server.",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def autorole_disable(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message(
                "This command can only be used in a server.", ephemeral=True
            )
            return

        config = get_config(interaction.guild.id)
        if not config:
            await interaction.response.send_message(
                "Auto-role is not configured.", ephemeral=True
            )
            return

        config["enabled"] = False
        set_config(interaction.guild.id, config)
        await interaction.response.send_message(
            "Auto-role disabled.", ephemeral=True
        )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return

        config = get_config(member.guild.id)
        if not config or not config.get("enabled"):
            return

        pending = get_pending()
        key = f"{member.guild.id}:{member.id}"
        pending[key] = {
            "guild_id": member.guild.id,
            "user_id": member.id,
            "joined_at": datetime.now(timezone.utc).isoformat(),
        }
        save_pending(pending)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        pending = get_pending()
        key = f"{member.guild.id}:{member.id}"
        if key in pending:
            del pending[key]
            save_pending(pending)

    @tasks.loop(seconds=30)
    async def _check_pending(self) -> None:
        pending = get_pending()
        if not pending:
            return

        now = datetime.now(timezone.utc)
        to_remove: list[str] = []

        for key, entry in list(pending.items()):
            guild_id = entry["guild_id"]
            user_id = entry["user_id"]
            joined_at = datetime.fromisoformat(entry["joined_at"])

            config = get_config(guild_id)
            if not config or not config.get("enabled"):
                to_remove.append(key)
                continue

            delay = config.get("delay_seconds", DELAY_SECONDS)
            if (now - joined_at).total_seconds() < delay:
                continue

            guild = self.bot.get_guild(guild_id)
            if guild is None:
                to_remove.append(key)
                continue

            member = guild.get_member(user_id)
            if member is None:
                to_remove.append(key)
                continue

            role_id = config.get("role_id")
            role = guild.get_role(role_id) if role_id else None
            if role is None:
                to_remove.append(key)
                continue

            if role in member.roles:
                to_remove.append(key)
                continue

            me = guild.me
            if me is None or role >= me.top_role or not me.guild_permissions.manage_roles:
                continue

            try:
                await member.add_roles(role, reason="Auto-role after membership delay")
            except discord.HTTPException:
                continue

            to_remove.append(key)

        if to_remove:
            for key in to_remove:
                pending.pop(key, None)
            save_pending(pending)

    @_check_pending.before_loop
    async def _before_check(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AutoRoles(bot))
