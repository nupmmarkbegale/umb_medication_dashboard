import datetime
from django.db import models
from .participant_model_manager import ParticipantModelManager

class DoseHistoryManager(ParticipantModelManager):
    def dates_with_dose_changes_last_week(self, participant_id):
        cursor = self.participant_db_cursor(participant_id)
        sql = self.__select_dates_with_dose_changes_last_week_sql()

        return self.fetch_results(cursor, sql) 

    def __select_dates_with_dose_changes_last_week_sql(self):
        select = 'SELECT "id", "eventDateTime" FROM "doseHistory"'
        today = datetime.date.today()

        return 'SELECT "eventDateTime" '\
            'FROM (SELECT ROW_NUMBER() OVER (PARTITION BY "eventDateTime"::date) AS row, '\
            '"t"."eventDateTime"::date FROM (%s) t) x '\
            'WHERE x.row = 1 AND "x"."eventDateTime" < \'%s\' AND "x"."eventDateTime" >= \'%s\';' % \
            (select, today, today - datetime.timedelta(days=7))

class DoseHistory(models.Model):
    id = models.TextField(primary_key=True)
    eventDateTime = models.DateTimeField()
    doses = models.TextField()

    objects = DoseHistoryManager()

    class Meta:
        db_table = 'doseHistory'
        managed = False
