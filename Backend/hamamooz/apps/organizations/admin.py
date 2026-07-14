from django.contrib import admin

from .models import AcademicYear, ClassSection, GradeLevel, Organization, School, Term

admin.site.register(Organization)
admin.site.register(School)
admin.site.register(AcademicYear)
admin.site.register(Term)
admin.site.register(GradeLevel)
admin.site.register(ClassSection)
