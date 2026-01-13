from django.http import HttpResponse
from django.db import connection

def health_check(request):
    try:
        connection.ensure_connection()
        return HttpResponse("OK")
    except Exception:
        return HttpResponse("Database connection failed", status=503)
