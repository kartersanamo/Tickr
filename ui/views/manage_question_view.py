from typing import Any
import discord

from services.manage_tickets_auth import require_ticket_editor
from services.ticket_types_editor import remove_question
from services.guild_config_service import GuildConfigService
from services.guild_helpers import embed_color
from services.ticket_types_store import load_raw, reload_tickets, save_raw
from ui.views.manage_tickets_support import ManageTicketsSupport
from core.loggers import log_commands


class ManageQuestionView(discord.ui.View):
    def __init__(self, ticket_info, ticket_category, ticket, question) -> None:
        self.ticket_info = ticket_info
        self.ticket_category = ticket_category
        self.ticket = ticket
        self.question = question
        self.mapping = {
            "Label": {
                "Description": "*This is the label of the question that appears above the text box. The max length on a modal title is 45 characters.*",
                "Image": "https://i.imgur.com/GrYinyp.png",
            },
            "Placeholder": {
                "Description": "*This message will be in the text box before the user types anything in. Usually, this is where directions go about what to enter into the text box. The max length of a modal's placeholder is 100 characters.*",
                "Image": "https://i.imgur.com/Ad07AYo.png",
            },
        }
        super().__init__(timeout=None)

    async def update_embed(self, interaction: discord.Interaction):
        try:
            self.ticket_info = await reload_tickets(interaction.guild_id)
            questions = (
                self.ticket_info.get(self.ticket_category, {})
                .get(self.ticket, {})
                .get("Questions")
                or []
            )
            question_info = next(
                (
                    question
                    for question in questions
                    if question.get("Label") == self.question
                ),
                None,
            )
            if question_info is None:
                return
            embed = discord.Embed(
                title="Manage Ticket Questions",
                color=embed_color(
                    await GuildConfigService.for_guild(interaction.guild_id)
                ),
                description=self.ticket_category + " » " + self.ticket,
            )
            embed.add_field(name="Question", value=question_info.get("Label", "None"))
            embed.add_field(
                name="Placeholder", value=question_info.get("Placeholder", "None")
            )
            embed.add_field(name="Length", value=question_info.get("Length", "None"))
            await interaction.edit_original_response(embed=embed)
        except Exception as e:
            log_commands.error(f"Failed to update embed {e}")

    async def change_value(self, interaction: discord.Interaction, value: str):
        try:
            if not await require_ticket_editor(interaction):
                return
            guild = interaction.guild
            if guild is None:
                return await interaction.response.send_message(
                    content="You must be in a server to do this!", ephemeral=True
                )
            await interaction.response.defer()
            await self.update_embed(interaction)
            if (
                interaction.message is None
                or interaction.message.embeds is None
                or len(interaction.message.embeds) == 0
            ):
                return
            top_embed = interaction.message.embeds[0]
            if top_embed is None:
                return
            description, image = list[Any](self.mapping.get(value, {}).values())
            embed = discord.Embed(
                title=f"Enter the new {value.lower()} below",
                color=embed_color(
                    await GuildConfigService.for_guild(interaction.guild_id)
                ),
                description=description,
            )
            embed.set_image(url=image)
            await interaction.message.edit(embeds=[top_embed, embed], view=None)

            def check(m):
                if value == "Label":
                    if len(m.content) > 45:
                        return False
                else:
                    if len(m.content) > 100:
                        return False
                if m.channel == interaction.channel and m.author == interaction.user:
                    return True
                return False

            new_value = await interaction.client.wait_for("message", check=check)
            if interaction.guild_id is None:
                return
            info = await load_raw(interaction.guild_id)
            questions = (
                info.get(self.ticket_category, {}).get(self.ticket, {}).get("Questions")
                or []
            )
            index = next(
                (
                    i
                    for i, question in enumerate(questions)
                    if question.get("Label") == self.question
                ),
                None,
            )
            if index is None:
                return
            popped = questions.pop(index)
            popped[value] = new_value.content
            questions.insert(index, popped)
            info[self.ticket_category][self.ticket]["Questions"] = questions
            await save_raw(interaction.guild_id, info)
            self.ticket_info = info
            if value == "Label":
                self.question = new_value.content
            await new_value.delete()
            view = ManageQuestionView(
                self.ticket_info, self.ticket_category, self.ticket, self.question
            )
            await view.update_embed(interaction)
            await interaction.message.edit(view=view)
            await ManageTicketsSupport.update_msg(interaction)
            log_commands.info(
                f"{interaction.user} ({interaction.user.id}) has changed {value} to {new_value} for {self.ticket_category} {self.ticket}"
            )
        except Exception as e:
            log_commands.error(f"Failed to change the value of {value} {e}")

    @discord.ui.button(
        label="|<",
        style=discord.ButtonStyle.red,
        custom_id="go_back_type",
        row=0,
        disabled=False,
    )
    async def go_back_type(
        self, interaction: discord.Interaction, Button: discord.ui.Button
    ):
        try:
            from ui.views.manage_type_view import ManageTypeView

            await interaction.response.defer()
            view = ManageTypeView(self.ticket_info, self.ticket_category, self.ticket)
            await view.update_embed(interaction)
            if interaction.message is not None:
                await interaction.message.edit(view=view)
        except Exception as e:
            log_commands.error(
                f"{interaction.user} ({interaction.user.id}) has failed to go back {e}"
            )

    @discord.ui.button(
        label="Change Label",
        style=discord.ButtonStyle.grey,
        custom_id="change_question",
        row=0,
        disabled=False,
    )
    async def change_question(
        self, interaction: discord.Interaction, Button: discord.ui.Button
    ):
        await self.change_value(interaction, "Label")

    @discord.ui.button(
        label="Change Placeholder",
        style=discord.ButtonStyle.grey,
        custom_id="change_placeholder",
        row=0,
        disabled=False,
    )
    async def change_placeholder(
        self, interaction: discord.Interaction, Button: discord.ui.Button
    ):
        await self.change_value(interaction, "Placeholder")

    @discord.ui.button(
        label="Delete Question",
        style=discord.ButtonStyle.danger,
        custom_id="delete_question",
        row=1,
    )
    async def delete_question(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        try:
            if not await require_ticket_editor(interaction):
                return
            await interaction.response.defer()
            if interaction.guild_id is None:
                return
            info = await load_raw(interaction.guild_id)
            info = remove_question(
                info, self.ticket_category, self.ticket, self.question
            )
            await save_raw(interaction.guild_id, info)
            from ui.views.manage_type_view import ManageTypeView

            view = ManageTypeView(info, self.ticket_category, self.ticket)
            await view.update_embed(interaction)
            if interaction.message is not None:
                await interaction.message.edit(view=view)
            await ManageTicketsSupport.update_msg(interaction)
            await interaction.followup.send(
                content=f"`✅` Deleted question **{self.question}**.",
                ephemeral=True,
            )
        except ValueError as exc:
            await interaction.followup.send(f"`❌` {exc}", ephemeral=True)
        except Exception as exc:
            log_commands.error(f"Failed to delete question: {exc}")

    @discord.ui.button(
        label="Change Length",
        style=discord.ButtonStyle.grey,
        custom_id="change_length",
        row=0,
        disabled=False,
    )
    async def change_length(
        self, interaction: discord.Interaction, Button: discord.ui.Button
    ):
        try:
            if not await require_ticket_editor(interaction):
                return
            await interaction.response.defer()
            if interaction.guild_id is None:
                return
            info = await load_raw(interaction.guild_id)
            questions = (
                info.get(self.ticket_category, {}).get(self.ticket, {}).get("Questions")
                or []
            )
            index = next(
                (
                    i
                    for i, question in enumerate(questions)
                    if question.get("Label") == self.question
                ),
                None,
            )
            if index is None:
                return
            popped = questions.pop(index)
            new_length = "Short" if popped["Length"] == "Long" else "Long"
            popped["Length"] = new_length
            questions.insert(index, popped)
            info[self.ticket_category][self.ticket]["Questions"] = questions
            await save_raw(interaction.guild_id, info)
            self.ticket_info = info
            view = ManageQuestionView(
                self.ticket_info, self.ticket_category, self.ticket, self.question
            )
            await view.update_embed(interaction)
            if interaction.message is not None:
                await interaction.message.edit(view=view)
            await interaction.followup.send(
                content="Successfully changed the length.", ephemeral=True
            )
            await ManageTicketsSupport.update_msg(interaction)
            log_commands.info(
                f"{interaction.user} ({interaction.user.id}) has changed the length of {self.ticket_category} {self.ticket} question {self.question} to {new_length}"
            )
        except Exception as e:
            log_commands.error(
                f"{interaction.user} ({interaction.user.id}) has failed to change the length {e}"
            )
