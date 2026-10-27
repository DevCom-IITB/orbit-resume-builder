from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resumes", "0007_securityevent_usersecuritystate"),
    ]

    operations = [
        migrations.AddField(
            model_name="sectionentry",
            name="improvement_suggestion",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="sectionentry",
            name="improvement_example",
            field=models.TextField(blank=True, default=""),
        ),
    ]
