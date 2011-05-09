from django.db import models
from django.core.management.base import NoArgsCommand
import settings
import core.series_manager

class Command(NoArgsCommand):
    help = """Executes the daily update of series: 
    archives previous day[s] data and trims current data."""

    def handle_noargs(self, **options):        
        core.series_manager.del_series_today({"archive":"1"})
