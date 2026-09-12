from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("books", "0007_book_embedding_hnsw_index")]

    operations = [
        migrations.AddField(
            model_name="book", name="work_id",
            field=models.CharField(max_length=64, blank=True, default="", db_index=True),
        ),
        migrations.AddField(
            model_name="book", name="language_code",
            field=models.CharField(max_length=32, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="book", name="source_format",
            field=models.CharField(max_length=255, blank=True, default=""),
        ),
    ]
