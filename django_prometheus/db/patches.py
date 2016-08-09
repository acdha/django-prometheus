# encoding: utf-8
from __future__ import absolute_import, division, print_function

from functools import wraps

from django.db.backends.signals import connection_created
from django_prometheus.db import connections_total

from .metrics import (errors_total, execute_many_total, execute_total,
                      query_time)


def patch_cursor_method(cursor, func_name, alias, vendor, counter):
    func = getattr(cursor, func_name)

    # Avoid calling labels on every invocation:
    counter_f = counter.labels(alias, vendor)
    query_timer = query_time.labels(alias, vendor)

    @wraps(func)
    def timed_func(*args, **kwargs):
        counter_f.inc()

        with query_timer.time():
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                errors_total.labels(alias, vendor, type(exc).__name__).inc()
                raise

    setattr(cursor, func_name, timed_func)


def connection_creation_listener(sender, connection, *args, **kwargs):
    connections_total.labels(connection.alias, connection.vendor).inc()

    # For each connection, we'll hook create_cursor to instrument future
    # execute and executemany calls:

    real_create_cursor = connection.create_cursor

    @wraps(connection.create_cursor)
    def instrumented_create_cursor(*args, **kwargs):
        cursor = real_create_cursor(*args, **kwargs)

        patch_cursor_method(cursor, 'execute', connection.alias, connection.vendor, execute_total)
        patch_cursor_method(cursor, 'executemany', connection.alias, connection.vendor, execute_many_total)

        return cursor

    connection.create_cursor = instrumented_create_cursor


def install_db_patches():
    connection_created.connect(connection_creation_listener)
