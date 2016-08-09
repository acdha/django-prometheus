from django_prometheus.db.common import DatabaseWrapperMixin, ExportingCursorWrapper

from django.contrib.gis.db.backends.mysql import base
from django.db.backends.mysql.base import CursorWrapper


class DatabaseWrapper(DatabaseWrapperMixin, base.DatabaseWrapper):
    def create_cursor(self):
        cursor = self.connection.cursor()
        return ExportingCursorWrapper(CursorWrapper, self.alias, self.vendor)(cursor)
