from django.contrib import admin

from .models import MetricScore, MonthlyEvaluation

admin.site.register(MonthlyEvaluation)
admin.site.register(MetricScore)
