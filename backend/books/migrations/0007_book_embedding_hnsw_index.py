from django.contrib.postgres.operations import AddIndexConcurrently
from pgvector.django import HnswIndex
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0006_alter_book_similar_books'),
    ]

    atomic = False

    operations = [
        AddIndexConcurrently(
            model_name='book',
            index=HnswIndex(
                name='book_embedding_hnsw_idx',
                fields=['embedding'],
                m=16,
                ef_construction=64,
                opclasses=['vector_cosine_ops'],
            ),
        ),
    ]