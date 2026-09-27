from __future__ import annotations

import asyncio
import os
import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv

from keep_alive import keep_alive

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("ERROR: DISCORD_TOKEN environment variable is not set.", file=sys.stderr)
    sys.exit(1)

INTENTS = discord.Intents.default()
INTENTS.members = True          # required for on_member_join / role assignment
INTENTS.message_content = False  # not needed for these systems
INTENTS.guilds = True


class QTStudios(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix="!",  # fallback only; primary interface is slash
            intents=INTENTS,
            help_command=None,
        )

    async def setup_hook(self) -> None:
        await self.load_extension("welcomer")
        await self.load_extension("autoroles")
        # Sync global commands (can take up to 1h). For instant sync use guilds.
        await self.tree.sync()
        print(f"Slash commands synced. Loaded extensions: {list(self.extensions.keys())}")

    async def on_ready(self) -> None:
        if self.user:
            print(f"Logged in as {self.user} (ID: {self.user.id})")
            print(f"Guilds: {len(self.guilds)}")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="QTStudios | /welcomer-setup /autorole-setup",
            )
        )


async def main() -> None:
    keep_alive()
    bot = QTStudios()
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
