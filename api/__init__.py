"""Opcjonalny lokalny backend REST FastAPI dla Better Trello.

Aplikacja ASGI znajduje się w `api.app:app`.
Ten plik celowo nie importuje `app`, żeby samo `import api` nie wymagało
zainstalowanego FastAPI. Eksportujemy natomiast moduł `schemas`, bo jest lekki
i pomaga IDE poprawnie rozpoznawać `api.schemas`.
"""

from . import schemas

__all__ = ["schemas"]
