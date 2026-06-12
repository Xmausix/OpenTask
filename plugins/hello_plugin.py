from __future__ import annotations

PLUGIN = {
    "name": "Hello Plugin",
    "version": "1.0.0",
    "description": "Przykładowy plugin pokazujący komunikat statusu.",
    "author": "Better Trello",
}


def register(context):
    def hello():
        context.status("Hello z pluginu — system pluginów działa ✅")

    context.add_command("Hello Plugin", hello)
