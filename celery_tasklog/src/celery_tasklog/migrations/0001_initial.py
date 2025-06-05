from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='TaskLogLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_id', models.CharField(db_index=True, max_length=255)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('stream', models.CharField(choices=[('stdout', 'stdout'), ('stderr', 'stderr')], max_length=10)),
                ('message', models.TextField()),
            ],
            options={'ordering': ['id']},
        ),
    ]
