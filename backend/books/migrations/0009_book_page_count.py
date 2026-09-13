from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0008_book_source_metadata'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='page_count',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
