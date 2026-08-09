import requests
from django.conf import settings
from django.utils import timezone

GOOGLE_BOOKS_API_URL = "https://www.googleapis.com/books/v1/volumes"

def enrich_book(book):
    """
    Look up a book on Google Books by ISBN and fill in cover_url/description
    if found. Always marks enriched_at, whether or not a match was found,
    so we never repeatedly retry the same book on every view.
    """
    if book.enriched_at is not None:
        return book

    if not book.isbn:
        book.enriched_at = timezone.now()
        book.save(update_fields=["enriched_at"])
        return book

    try:
        response = requests.get(
            GOOGLE_BOOKS_API_URL,
            params={"q": f"isbn:{book.isbn}", "key": settings.GOOGLE_BOOKS_API_KEY},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return book

    items = data.get("items")
    if items:
        volume_info = items[0].get("volumeInfo", {})
        image_links = volume_info.get("imageLinks", {})

        if not book.cover_url and image_links.get("thumbnail"):
            book.cover_url = image_links["thumbnail"]
        if not book.description and volume_info.get("description"):
            book.description = volume_info["description"]
        if not book.google_books_id:
            book.google_books_id = items[0].get("id", "")

    book.enriched_at = timezone.now()
    book.save()
    return book