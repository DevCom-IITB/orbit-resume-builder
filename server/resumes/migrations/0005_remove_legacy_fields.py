import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("resumes", "0004_data_migration"),
    ]

    operations = [
        # Remove legacy fields from Section
        migrations.RemoveField(model_name="section", name="section_type_legacy"),
        migrations.RemoveField(model_name="section", name="content"),

        # Remove legacy fields from Resume
        migrations.RemoveField(model_name="resume", name="header_type"),
        migrations.RemoveField(model_name="resume", name="resume_type"),
        migrations.RemoveField(model_name="resume", name="meta"),

        # Make FKs non-nullable now that data migration has populated them
        migrations.AlterField(
            model_name="resume",
            name="template",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="resumes",
                to="resumes.resumetemplate",
            ),
        ),
        migrations.AlterField(
            model_name="resume",
            name="visual_theme",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="resumes",
                to="resumes.visualtheme",
            ),
        ),
        migrations.AlterField(
            model_name="section",
            name="section_type",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="instances",
                to="resumes.sectiontypedefinition",
            ),
        ),

        # Add unique_together constraint on Section
        migrations.AlterUniqueTogether(
            name="section",
            unique_together={("resume", "section_type")},
        ),
    ]
