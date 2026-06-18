import discord

from core.loggers import log_commands


class ManageQuestionsSelect(discord.ui.Select):
    def __init__(self, ticket_info, ticket_category, ticket) -> None:
        self.ticket_info = ticket_info
        self.ticket_category = ticket_category
        self.ticket = ticket
        questions = ticket_info.get(ticket_category, {}).get(ticket, {}).get("Questions", [])
        labels = [question.get("Label", "None") for question in questions if isinstance(question, dict)]
        if labels:
            options = [discord.SelectOption(label=label) for label in labels[:25]]
            placeholder = "Select a question to manage..."
        else:
            options = [discord.SelectOption(label="No questions yet", value="__none__")]
            placeholder = "No questions configured"
        super().__init__(placeholder=placeholder, options=options, custom_id="manage_questions_pick")

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.values[0] == "__none__":
            await interaction.response.send_message(
                "Use **Add Question** to create the first question for this ticket type.",
                ephemeral=True,
            )
            return
        try:
            from ui.views.manage_question_view import ManageQuestionView

            question = self.values[0]
            await interaction.response.defer()
            view = ManageQuestionView(self.ticket_info, self.ticket_category, self.ticket, question)
            await view.update_embed(interaction)
            if interaction.message is not None:
                await interaction.message.edit(view=view)
        except Exception as exc:
            log_commands.error(f"Failed to select question: {exc}")
