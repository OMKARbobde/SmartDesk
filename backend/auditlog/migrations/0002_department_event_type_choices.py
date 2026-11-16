from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("auditlog", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name="auditevent",
                    name="event_type",
                    field=models.CharField(
                        choices=[
                            ("TICKET_CREATED", "Ticket created"),
                            ("TICKET_UPDATED", "Ticket updated"),
                            ("TICKET_STATUS_CHANGED", "Ticket status changed"),
                            ("TICKET_PRIORITY_CHANGED", "Ticket priority changed"),
                            ("TICKET_BULK_STATUS_CHANGED", "Ticket status changed in bulk"),
                            ("TICKET_BULK_PRIORITY_CHANGED", "Ticket priority changed in bulk"),
                            ("ASSIGNMENT_CREATED", "Assignment created"),
                            ("ASSIGNMENT_REASSIGNED", "Assignment reassigned"),
                            ("ASSIGNMENT_ACCEPTED", "Assignment accepted"),
                            ("ASSIGNMENT_COMPLETED", "Assignment completed"),
                            ("TICKET_ARCHIVED", "Ticket archived"),
                            ("TICKET_RESTORED", "Ticket restored"),
                            ("DEPARTMENT_CREATED", "Department created"),
                            ("DEPARTMENT_UPDATED", "Department updated"),
                            ("DEPARTMENT_ACTIVATED", "Department activated"),
                            ("DEPARTMENT_DEACTIVATED", "Department deactivated"),
                        ],
                        db_index=True,
                        max_length=40,
                    ),
                ),
            ],
        ),
    ]
